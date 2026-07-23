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
                service = SaaSControlService(db)
                # 🔥 استدعاء خدمة التجديد مع إعادة النتائج المفصلة
                results = await service.process_auto_renewals()
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
    إنشاء فواتير الشهر الجديد (تُنفذ في أول كل شهر).
    - تولد فواتير لجميع المستأجرين النشطين.
    - تُرسل إشعارات للمستخدمين بالفواتير الجديدة.
    """
    try:
        async def _run():
            async with SessionLocal() as db:  # ✅ استخدام SessionLocal
                service = SaaSControlService(db)
                # 🔥 ملاحظة: تأكد من وجود دالة generate_monthly_invoices في SaaSControlService
                result = await service.generate_monthly_invoices()  # type: ignore[attr-defined]
                await db.commit()
                
                logger.info(f"✅ Monthly invoices generated: {result}")
                return result

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
                service = SaaSControlService(db)
                # 🔥 ملاحظة: تأكد من وجود دالة check_and_expire_trials في SaaSControlService
                expired_count = await service.check_and_expire_trials()  # type: ignore[attr-defined]
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
    - تُرسل إشعارات In-App وبريد إلكتروني.
    """
    try:
        async def _run():
            async with SessionLocal() as db:  # ✅ استخدام SessionLocal
                service = SaaSControlService(db)
                # 🔥 ملاحظة: تأكد من وجود دالة send_trial_expiry_reminders في SaaSControlService
                reminders_sent = await service.send_trial_expiry_reminders()  # type: ignore[attr-defined]
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
    تنظيف الاشتراكات الملغاة (حذف البيانات المؤقتة، إلغاء الموارد).
    - تُنفذ أسبوعياً.
    - تحذف بيانات المستخدمين وفقاً لسياسة الخصوصية (GDPR/PDPL).
    """
    try:
        async def _run():
            async with SessionLocal() as db:  # ✅ استخدام SessionLocal
                service = SaaSControlService(db)
                # 🔥 ملاحظة: تأكد من وجود دالة cleanup_cancelled_subscriptions في SaaSControlService
                cleaned_count = await service.cleanup_cancelled_subscriptions()  # type: ignore[attr-defined]
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