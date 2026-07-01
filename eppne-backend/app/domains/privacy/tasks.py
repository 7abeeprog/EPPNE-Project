# app/domains/privacy/tasks.py
import asyncio
from app.core.celery_app import celery_app
from app.domains.privacy.service import PrivacyService
from app.core.database import SessionLocal
# 🔥 الاستيراد المباشر للـ logger بعد إصلاح الملف
from app.core.logging_conf import logger 

@celery_app.task(
    bind=True, 
    name="privacy.tasks.unpin_from_ipfs",
    max_retries=5, 
    default_retry_delay=60
)
def unpin_from_ipfs(self, user_id: int, module: str):
    # ... باقي الكود كما هو    """مهمة خلفية لإلغاء تثبيت بيانات المستخدم من الـ IPFS"""
    
    async def run_task():
        # استخدام async with مع SessionLocal المعرفة في database.py
        async with SessionLocal() as db:
            service = PrivacyService(db)
            await service._async_unpin_ipfs(user_id, module)

    try:
        # تشغيل المهمة غير المتزامنة داخل الـ Worker
        asyncio.run(run_task())
    except Exception as exc:
        logger.error(f"IPFS Unpin failed for user {user_id}: {exc}")
        # سياسة إعادة المحاولة: 1m, 2m, 4m, 8m, 16m
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 60)

@celery_app.task(
    bind=True, 
    name="privacy.tasks.burn_tokens",
    max_retries=5, 
    default_retry_delay=30
)
def burn_tokens(self, user_id: int, receipt_tx: str):
    """مهمة خلفية لحرق التوكنات على البلوكشين"""
    
    async def run_task():
        async with SessionLocal() as db:
            service = PrivacyService(db)
            await service._async_burn_tokens(user_id, receipt_tx)

    try:
        asyncio.run(run_task())
    except Exception as exc:
        logger.error(f"Blockchain burn failed for user {user_id}: {exc}")
        # سياسة إعادة المحاولة: 30s, 1m, 2m, 4m, 8m
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)