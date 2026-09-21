# app/tasks/saas_tasks.py
"""
مهام Celery لإدارة اشتراكات SaaS.
تدعم: التجديد التلقائي، توليد الفواتير الشهرية، والتحقق من انتهاء الفترات التجريبية.
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

# 🔥 استيراد التطبيق المركزي والاتصال الموحّد بقاعدة البيانات
from app.core.celery_app import celery_app
from app.core.database import SessionLocal  # ✅ استخدام SessionLocal بدلاً من async_session
from app.core.logging_conf import logger
from app.domains.saas.service import SaaSControlService


# ============================================================
# 1. أداة تشغيل آمنة للـ Async (تمنع تسرب الذاكرة)
# ============================================================
def _run_async(coro):
    """
    تشغيل دالة غير متزامنة (Async) بطريقة آمنة داخل Celery.
    - تخلق حلقة أحداث جديدة لكل مهمة لضمان العزل.
    - تغلق الحلقة تلقائياً بعد الانتهاء لمنع تسرب الذاكرة.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        # 🔥 تنظيف الموارد وإغلاق الحلقة
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        finally:
            loop.close()


# ============================================================
# 2. مهمة تجديد الاشتراكات التلقائية
# ============================================================
@celery_app.task(
    name="saas.process_auto_renewals",
    bind=True,
    max_retries=3,
    default_retry_delay=3600,        # ساعة واحدة بين المحاولات (لأنها مهمة يومية)
    acks_late=True,                   # 🔥 تأكيد بعد التنفيذ
    time_limit=1800,                  # 30 دقيقة كحد أقصى
    soft_time_limit=1500,             # 25 دقيقة إنذار
)
def process_auto_renewals_task(self):
    """
    مهمة تجديد الاشتراكات التلقائية (تُنفذ يومياً في الساعة 2 صباحاً).
    - تتحقق من الاشتراكات المنتهية صلاحيتها وتجددها تلقائياً.
    - تنشئ فواتير جديدة لكل تجديد.
    - تدعم إعادة المحاولة في حال فشل الاتصال بالخدمات المالية.
    """
    try:
        async def _run():
            async with SessionLocal() as db:  # ✅ استخدام SessionLocal
                # [2026-09-08] كان SaaSControlService(db) بلا tenant_id — TypeError مؤكَّد
                # حيًا في كل تنفيذ (راجع backlog-process-auto-renewals-task-constructor-
                # typeerror في PROGRESS_LOG.md). tenant_id=0 نفس نمط
                # check_past_due_subscriptions_task/router.py:273 الإداري.
                service = SaaSControlService(db, 0)
                # 🔥 استدعاء خدمة التجديد مع إعادة النتائج المفصلة
                # [2026-09-08] tenant_id=None صراحةً = كل التينانتات (process_auto_renewals
                # بقت بتمررها مباشرة لـget_subscriptions_for_renewal بلا fallback لـ
                # self.tenant_id=0 — راجع backlog-process-auto-renewals-task-tenant-zero-noop).
                results = await service.process_auto_renewals(tenant_id=None)
                await db.commit()
                
                # تحليل النتائج لتوليد تقرير مفصل
                total = len(results)
                successful = sum(1 for r in results if r.get("status") == "success")
                failed = sum(1 for r in results if r.get("status") == "failed")
                skipped = sum(1 for r in results if r.get("status") == "skipped")
                
                logger.info(
                    f"✅ Auto-renewals processed: "
                    f"Total: {total}, Successful: {successful}, Failed: {failed}, Skipped: {skipped}"
                )
                
                return {
                    "status": "success",
                    "total": total,
                    "successful": successful,
                    "failed": failed,
                    "skipped": skipped,
                    "details": results[:10]  # أول 10 نتائج فقط (لتجنب الحجم الكبير)
                }

        result = _run_async(_run())
        logger.info("✅ Auto-renewals task finished successfully.")
        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"❌ Auto-renewals task failed: {str(e)}")
        raise self.retry(exc=e, countdown=3600)


# ============================================================
# 3. مهمة إنشاء فواتير الشهر الجديد
# ============================================================
@celery_app.task(
    name="saas.generate_monthly_invoices",
    bind=True,
    max_retries=3,
    default_retry_delay=3600,
    acks_late=True,
    time_limit=3600,                  # ساعة واحدة (عدد كبير من المستأجرين)
    soft_time_limit=3000,             # 50 دقيقة إنذار
)
def generate_monthly_invoices_task(self):
    """
    إصدار فواتير الفوترة الشهرية اليدوية (تُنفذ في أول كل شهر).
    - تخص فقط الاشتراكات ACTIVE بـauto_renew=False (عملاء الدفع اليدوي)
      — بعكس process_auto_renewals_task اللي تخص auto_renew=True.
    - تُصدر فاتورة PENDING بلا أي خصم فوري؛ الدفع يحصل لاحقًا عبر
      pay_invoice.
    """
    try:
        async def _run():
            async with SessionLocal() as db:  # ✅ استخدام SessionLocal
                # [2026-09-09] نفس نمط process_auto_renewals_task/
                # check_expired_trials_task — tenant_id=0 كـsentinel إداري،
                # generate_monthly_invoices بتفحص كل tenant عبر sub.tenant_id
                # مش self.tenant_id، فمش متأثرة بالقيمة دي.
                service = SaaSControlService(db, 0)
                issued_count = await service.generate_monthly_invoices()
                await db.commit()

                logger.info(f"✅ Monthly invoices generated: {issued_count} invoices issued.")
                return {
                    "status": "success",
                    "issued_count": issued_count,
                    "generated_at": datetime.utcnow().isoformat()
                }

        result = _run_async(_run())
        logger.info("✅ Monthly invoices generation task finished successfully.")
        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"❌ Monthly invoices generation task failed: {str(e)}")
        raise self.retry(exc=e, countdown=3600)


# ============================================================
# 4. مهمة التحقق من انتهاء الفترات التجريبية
# ============================================================
@celery_app.task(
    name="saas.check_expired_trials",
    bind=True,
    max_retries=2,
    default_retry_delay=1800,         # 30 دقيقة
    acks_late=True,
    time_limit=900,                   # 15 دقيقة
    soft_time_limit=600,              # 10 دقائق إنذار
)
def check_expired_trials_task(self):
    """
    التحقق من انتهاء الفترات التجريبية وتعطيل الخدمات.
    - تُنفذ يومياً في الساعة 4 صباحاً.
    - تُرسل تنبيهات للمستخدمين قبل انتهاء الفترة التجريبية بيومين.
    """
    try:
        async def _run():
            async with SessionLocal() as db:  # ✅ استخدام SessionLocal
                # [2026-09-08] نفس نمط process_auto_renewals_task/
                # check_past_due_subscriptions_task — tenant_id=0 كـsentinel
                # إداري، check_and_expire_trials بتفحص كل tenant عبر
                # sub.tenant_id مش self.tenant_id، فمش متأثرة بالقيمة دي.
                service = SaaSControlService(db, 0)
                expired_count = await service.check_and_expire_trials()
                await db.commit()
                
                logger.info(f"✅ Expired trials checked: {expired_count} subscriptions expired.")
                return {
                    "status": "success",
                    "expired_count": expired_count,
                    "checked_at": datetime.utcnow().isoformat()
                }

        result = _run_async(_run())
        logger.info("✅ Expired trials check task finished successfully.")
        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"❌ Expired trials check task failed: {str(e)}")
        raise self.retry(exc=e, countdown=1800)


# ============================================================
# 5. مهمة إرسال تذكيرات انتهاء الفترة التجريبية
# ============================================================
@celery_app.task(
    name="saas.send_trial_expiry_reminders",
    bind=True,
    max_retries=2,
    default_retry_delay=3600,
    acks_late=True,
    time_limit=600,
    soft_time_limit=480,
)
def send_trial_expiry_reminders_task(self):
    """
    إرسال تذكيرات للمستخدمين قبل انتهاء الفترة التجريبية بيومين.
    - تُنفذ يومياً.
    - تُرسل إشعارات In-App بس — قناة EMAIL في CommunicationsService لسه
      stub فاضي (backlog منفصل)، ممنوع استخدامها هنا.
    """
    try:
        async def _run():
            async with SessionLocal() as db:  # ✅ استخدام SessionLocal
                # [2026-09-09] نفس نمط check_past_due_subscriptions_task —
                # tenant_id=0 كـsentinel إداري، send_trial_expiry_reminders
                # بتفحص كل tenant عبر sub.tenant_id مش self.tenant_id، فمش
                # متأثرة بالقيمة دي (راجع send-trial-expiry-reminders-task-
                # fix-session-log.md).
                service = SaaSControlService(db, 0)
                reminders_sent = await service.send_trial_expiry_reminders()
                await db.commit()
                
                logger.info(f"✅ Trial expiry reminders sent: {reminders_sent} notifications.")
                return {
                    "status": "success",
                    "reminders_sent": reminders_sent,
                    "sent_at": datetime.utcnow().isoformat()
                }

        result = _run_async(_run())
        logger.info("✅ Trial expiry reminders task finished successfully.")
        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"❌ Trial expiry reminders task failed: {str(e)}")
        raise self.retry(exc=e, countdown=3600)


# ============================================================
# 6. مهمة تنظيف الاشتراكات الملغاة
# ============================================================
@celery_app.task(
    name="saas.cleanup_cancelled_subscriptions",
    bind=True,
    max_retries=2,
    default_retry_delay=3600,
    acks_late=True,
    time_limit=1200,
    soft_time_limit=900,
)
def cleanup_cancelled_subscriptions_task(self):
    """
    تنظيف الاشتراكات الملغاة — المرحلة أ فقط حاليًا: تعطيل
    TenantServiceAccess.is_active بعد 30 يوم من الإلغاء (cancelled_at).
    - تُنفذ أسبوعياً (غير مجدولة تلقائيًا في beat_schedule حاليًا).
    - نطاق ضيق متعمَّد [2026-09-09]: بلا أي حذف أو تعمية لبيانات شخصية —
      ده مؤجَّل عمدًا لجلسة تصميم منفصلة تراجع دومين privacy (راجع
      .claude/reports/cleanup-cancelled-subscriptions-task-fix-session-log.md).
      "cleaned_count" هنا = عدد صفوف service access المُعطَّلة فعليًا،
      مش عدد اشتراكات "منظَّفة" بالمعنى الكامل للـdocstring القديم.
    """
    try:
        async def _run():
            async with SessionLocal() as db:  # ✅ استخدام SessionLocal
                # [2026-09-09] نفس نمط الباقي — SaaSControlService(db, 0)،
                # tenant_id=0 كـsentinel إداري، cleanup_cancelled_subscriptions
                # بتفحص كل tenant عبر sub.tenant_id مش self.tenant_id.
                service = SaaSControlService(db, 0)
                cleaned_count = await service.cleanup_cancelled_subscriptions()
                await db.commit()

                logger.info(f"✅ Cancelled subscriptions cleaned: {cleaned_count} subscriptions.")
                return {
                    "status": "success",
                    "cleaned_count": cleaned_count,
                    "cleaned_at": datetime.utcnow().isoformat()
                }

        result = _run_async(_run())
        logger.info("✅ Cleanup cancelled subscriptions task finished successfully.")
        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"❌ Cleanup cancelled subscriptions task failed: {str(e)}")
        raise self.retry(exc=e, countdown=3600)


# ============================================================
# 7. مهمة فحص الاشتراكات المتأخرة (PAST_DUE) وتنبيهات فترة السماح
# ============================================================
@celery_app.task(
    name="saas.check_past_due_subscriptions",
    bind=True,
    max_retries=3,
    default_retry_delay=3600,        # ساعة واحدة بين المحاولات (لأنها مهمة يومية)
    acks_late=True,                   # 🔥 تأكيد بعد التنفيذ
    time_limit=1800,                  # 30 دقيقة كحد أقصى
    soft_time_limit=1500,             # 25 دقيقة إنذار
)
def check_past_due_subscriptions_task(self):
    """
    فحص كل اشتراكات PAST_DUE وإرسال تنبيهات فترة السماح المرحلية
    (تُنفذ يومياً في الساعة 3 صباحاً، بعد process_auto_renewals بساعة).
    - يوم الدخول لـPAST_DUE: تنبيه ببداية فترة السماح (3 أيام).
    - قبل يوم واحد من انتهاء الفترة: تذكير أخير.
    - عند انتهاء الفترة: تنبيه بالإيقاف + تحويل الاشتراك إلى EXPIRED.
    - عبر كل المستأجرين (tenant_id=0 مؤقتاً عند إنشاء الـservice، بنفس
      نمط SaaSControlService(db, 0) الإداري في saas/router.py:273 —
      check_past_due_subscriptions نفسها بتفحص كل tenant عبر
      sub.tenant_id مش self.tenant_id، فمش متأثرة بالقيمة دي).
    """
    try:
        async def _run():
            async with SessionLocal() as db:  # ✅ استخدام SessionLocal
                service = SaaSControlService(db, 0)
                results = await service.check_past_due_subscriptions()
                await db.commit()

                total = len(results)
                notified = sum(1 for r in results if r.get("status") == "NOTIFIED")
                failed = sum(1 for r in results if r.get("status") == "FAILED")

                logger.info(
                    f"✅ Past-due subscriptions checked: "
                    f"Total: {total}, Notified: {notified}, Failed: {failed}"
                )

                return {
                    "status": "success",
                    "total": total,
                    "notified": notified,
                    "failed": failed,
                    "details": results[:10]  # أول 10 نتائج فقط (لتجنب الحجم الكبير)
                }

        result = _run_async(_run())
        logger.info("✅ Past-due subscriptions check task finished successfully.")
        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"❌ Past-due subscriptions check task failed: {str(e)}")
        raise self.retry(exc=e, countdown=3600)