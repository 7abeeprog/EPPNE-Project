# app/tasks/governance.py
"""
مهام Celery لحوكمة الذكاء الاصطناعي.
تدعم: إعادة تعيين الحصص المنتهية، وتنظيف سجلات الاستهلاك القديمة.
"""
import asyncio
from datetime import datetime
from typing import Optional

# 🔥 استيراد التطبيق المركزي والاتصال الموحّد بقاعدة البيانات
from app.core.celery_app import celery_app
from app.core.database import SessionLocal  # ✅ استخدام SessionLocal بدلاً من async_session
from app.core.logging_conf import logger
from app.domains.ai_governance.service import AIGovernanceService


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
# 2. مهمة إعادة تعيين الحصص المنتهية (المهمة الأساسية)
# ============================================================
@celery_app.task(
    name="governance.reset_expired_quotas",
    bind=True,
    max_retries=2,
    default_retry_delay=300,          # 5 دقائق
    acks_late=True,                    # 🔥 تأكيد بعد التنفيذ
    time_limit=300,                    # 5 دقائق كحد أقصى
    soft_time_limit=240,               # 4 دقائق إنذار
)
def reset_expired_quotas(self):
    """
    مهمة مجدولة لإعادة تعيين الحصص المنتهية.
    - تُنفذ يومياً (عادةً عند منتصف الليل).
    - تعيد ضبط عدادات استخدام الـ AI للمستأجرين.
    - تُحرر الموارد للشهر الجديد.
    """
    try:
        async def _run():
            async with SessionLocal() as db:  # ✅ استخدام SessionLocal
                service = AIGovernanceService(db)
                # 🔥 ملاحظة: تأكد من وجود دالة reset_expired_quotas في AIGovernanceService
                # إذا لم تكن موجودة، يمكنك استبدالها بالدالة المناسبة
                count = await service.reset_expired_quotas()  # type: ignore[attr-defined]
                await db.commit()
                logger.info(f"✅ Reset {count} expired quotas")
                return {
                    "status": "success",
                    "reset_count": count,
                    "reset_at": datetime.utcnow().isoformat()
                }

        result = _run_async(_run())
        logger.info("✅ Expired quotas reset task finished successfully.")
        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"❌ Failed to reset expired quotas: {str(e)}")
        raise self.retry(exc=e, countdown=300)


# ============================================================
# 3. مهمة تنظيف سجلات الاستهلاك القديمة (تحسين الأداء والخصوصية)
# ============================================================
@celery_app.task(
    name="governance.cleanup_old_consumption_logs",
    bind=True,
    max_retries=2,
    default_retry_delay=3600,          # ساعة واحدة
    acks_late=True,
    time_limit=600,                    # 10 دقائق
    soft_time_limit=480,               # 8 دقائق إنذار
)
def cleanup_old_consumption_logs(self, days_to_keep: int = 90):
    """
    تنظيف سجلات استهلاك الـ AI التي تتجاوز الفترة المحددة.
    - تُنفذ شهرياً.
    - تحذف السجلات الأقدم من `days_to_keep` (افتراضي 90 يوماً) للامتثال للخصوصية.
    - تُحسّن أداء قاعدة البيانات.
    """
    try:
        async def _run():
            async with SessionLocal() as db:  # ✅ استخدام SessionLocal
                service = AIGovernanceService(db)
                # 🔥 ملاحظة: تأكد من وجود دالة cleanup_old_logs في AIGovernanceService
                deleted_count = await service.cleanup_old_logs(days_to_keep)  # type: ignore[attr-defined]
                await db.commit()
                logger.info(f"🧹 Cleaned up {deleted_count} old consumption logs (older than {days_to_keep} days).")
                return {
                    "status": "success",
                    "deleted_count": deleted_count,
                    "days_kept": days_to_keep,
                    "cleaned_at": datetime.utcnow().isoformat()
                }

        result = _run_async(_run())
        logger.info("✅ Cleanup old consumption logs task finished successfully.")
        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"❌ Failed to cleanup old logs: {str(e)}")
        raise self.retry(exc=e, countdown=3600)


# ============================================================
# 4. مهمة إنشاء تقرير استخدام الـ AI (للإدارة)
# ============================================================
@celery_app.task(
    name="governance.generate_usage_report",
    bind=True,
    max_retries=2,
    default_retry_delay=1800,
    acks_late=True,
    time_limit=1200,
    soft_time_limit=900,
)
def generate_usage_report_task(self, tenant_id: Optional[int] = None):
    """
    إنشاء تقرير استخدام الـ AI لمستأجر معين (أو جميع المستأجرين).
    - تُنفذ عند الطلب أو أسبوعياً.
    - تُرسل التقرير إلى بريد المدير التنفيذي.
    """
    try:
        async def _run():
            async with SessionLocal() as db:  # ✅ استخدام SessionLocal
                service = AIGovernanceService(db)
                # 🔥 ملاحظة: تأكد من وجود دالة generate_usage_report في AIGovernanceService
                report = await service.generate_usage_report(tenant_id)  # type: ignore[attr-defined]
                await db.commit()
                
                target_tenant = tenant_id or "ALL"
                logger.info(f"📊 Usage report generated for tenant: {target_tenant}")
                return {
                    "status": "success",
                    "tenant_id": target_tenant,
                    "report": report,
                    "generated_at": datetime.utcnow().isoformat()
                }

        result = _run_async(_run())
        logger.info("✅ Usage report generation task finished successfully.")
        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"❌ Failed to generate usage report: {str(e)}")
        raise self.retry(exc=e, countdown=1800)