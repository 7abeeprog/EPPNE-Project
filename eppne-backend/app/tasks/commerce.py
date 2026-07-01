# app/tasks/commerce.py
from celery import shared_task
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from decimal import Decimal
import asyncio
import json

from app.core.config import settings
from app.domains.commerce.service import CommerceService
from app.domains.commerce.repository import CommerceRepository
from app.core.logging import logger

# إنشاء اتصال بقاعدة البيانات للمهام (يُفضل استخدام اتصال مستقل)
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _distribute_commissions_async(order_id: int, affiliate_code: str, order_total: float):
    """الدالة غير المتزامنة الفعلية لتوزيع العمولات"""
    async with AsyncSessionLocal() as db:
        service = CommerceService(db)
        await service.distribute_commissions(
            order_id=order_id,
            affiliate_code=affiliate_code,
            order_total=Decimal(str(order_total))
        )
        await db.commit()


@shared_task(name="commerce.distribute_commissions", bind=True, max_retries=3, default_retry_delay=60)
def distribute_commissions_task(self, order_id: int, affiliate_code: str, order_total: float):
    """
    مهمة توزيع العمولات (تعمل عبر Celery Worker).
    🔥 معالج غير متزامن لمنع إبطاء عملية Checkout.
    🔥 إعادة محاولة تلقائية في حال فشل الاتصال بقاعدة البيانات.
    """
    try:
        # تشغيل الدالة غير المتزامنة داخل حلقة الأحداث
        asyncio.run(_distribute_commissions_async(order_id, affiliate_code, order_total))
        logger.info(f"Commissions distributed for order {order_id}")
    except Exception as e:
        logger.error(f"Failed to distribute commissions for order {order_id}: {str(e)}")
        # إعادة المحاولة تلقائياً (Celery Retry)
        raise self.retry(exc=e, countdown=60)