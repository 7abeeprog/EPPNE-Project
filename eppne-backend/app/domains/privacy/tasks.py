# app/domains/privacy/tasks.py
"""
مهام Celery لقطاع الخصوصية (Privacy).
تدعم: إلغاء تثبيت البيانات من IPFS وحرق التوكنات على البلوكشين.
"""
import asyncio
from typing import Optional

# 🔥 استيراد التطبيق المركزي والاتصال الموحّد بقاعدة البيانات
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.logging_conf import logger
from app.domains.privacy.service import PrivacyService


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
# 2. مهمة إلغاء تثبيت البيانات من IPFS
# ============================================================
@celery_app.task(
    bind=True, 
    name="privacy.tasks.unpin_from_ipfs",
    max_retries=5, 
    default_retry_delay=60,
    acks_late=True,                    # 🔥 تأكيد بعد التنفيذ
    time_limit=600,                    # 10 دقائق كحد أقصى (IPFS قد يبطئ)
    soft_time_limit=480,               # 8 دقائق إنذار
)
def unpin_from_ipfs(self, user_id: int, module: str):
    """
    مهمة خلفية لإلغاء تثبيت بيانات المستخدم من الـ IPFS.
    - تُستدعى عند طلب حذف البيانات (امتثالاً لـ PDPL/GDPR).
    - تحاول إزالة البيانات من شبكة IPFS اللامركزية.
    - سياسة إعادة المحاولة: 1m, 2m, 4m, 8m, 16m
    """
    try:
        async def _run():
            async with SessionLocal() as db:
                service = PrivacyService(db)
                await service._async_unpin_ipfs(user_id, module)
                logger.info(f"✅ IPFS unpin completed for user {user_id}, module: {module}")
                return {"status": "success", "user_id": user_id, "module": module}

        result = _run_async(_run())
        logger.info(f"✅ IPFS unpin task finished for user {user_id}")
        return result

    except Exception as exc:
        logger.error(f"❌ IPFS Unpin failed for user {user_id}, module {module}: {exc}")
        # سياسة إعادة المحاولة التصاعدية
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 60)


# ============================================================
# 3. مهمة حرق التوكنات على البلوكشين
# ============================================================
@celery_app.task(
    bind=True, 
    name="privacy.tasks.burn_tokens",
    max_retries=5, 
    default_retry_delay=30,
    acks_late=True,                    # 🔥 تأكيد بعد التنفيذ
    time_limit=300,                    # 5 دقائق (البلوكشين أسرع من IPFS)
    soft_time_limit=240,
)
def burn_tokens(self, user_id: int, receipt_tx: str, tenant_id: int):
    """
    مهمة خلفية لحرق التوكنات على البلوكشين.
    - تُستدعى عند طلب حذف الحساب أو تحويل الأصول.
    - تُحرق التوكنات المرتبطة بالمستخدم نهائياً.
    - سياسة إعادة المحاولة: 30s, 1m, 2m, 4m, 8m
    """
    try:
        async def _run():
            async with SessionLocal() as db:
                service = PrivacyService(db)
                await service._async_burn_tokens(user_id, receipt_tx, tenant_id)
                logger.info(f"✅ Tokens burned for user {user_id}, tx: {receipt_tx}")
                return {
                    "status": "success",
                    "user_id": user_id,
                    "receipt_tx": receipt_tx
                }

        result = _run_async(_run())
        logger.info(f"✅ Token burn task finished for user {user_id}")
        return result

    except Exception as exc:
        logger.error(f"❌ Blockchain burn failed for user {user_id}, tx {receipt_tx}: {exc}")
        # سياسة إعادة المحاولة التصاعدية
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)