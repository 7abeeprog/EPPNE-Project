# app/tasks/affiliate_tasks.py
from celery import shared_task
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from decimal import Decimal
import asyncio

from app.core.config import settings
from app.domains.affiliate.service import AffiliateService
from app.core.logging import logger

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _distribute_commissions_async(order_id: int, tenant_id: int):
    """توزيع العمولات بشكل غير متزامن"""
    async with AsyncSessionLocal() as db:
        service = AffiliateService(db)
        commissions = await service.distribute_commissions(order_id, tenant_id)
        await db.commit()
        logger.info(f"Distributed {len(commissions)} commissions for order {order_id}")
        return commissions


@shared_task(
    name="affiliate.distribute_commissions",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def distribute_commissions_task(self, order_id: int, tenant_id: int):
    """
    ✅ توزيع العمولات بشكل غير متزامن عبر Celery.
    - acks_late=True يضمن عدم ضياع المهمة في حال فشل Worker.
    - إعادة محاولة تلقائية مع تأخير 60 ثانية.
    """
    try:
        asyncio.run(_distribute_commissions_async(order_id, tenant_id))
        logger.info(f"Commissions distributed successfully for order {order_id}")
    except Exception as e:
        logger.error(f"Failed to distribute commissions for order {order_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)


async def _release_commissions_async(user_id: int, idempotency_key: str):
    """تحرير العمولات المعلقة للمستخدم"""
    async with AsyncSessionLocal() as db:
        service = AffiliateService(db)
        result = await service.release_commissions(user_id, idempotency_key)
        await db.commit()
        logger.info(f"Released commissions for user {user_id}: {result['count']} commissions")
        return result


@shared_task(
    name="affiliate.release_commissions",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    acks_late=True,
)
def release_commissions_task(self, user_id: int, idempotency_key: str):
    """
    ✅ تحرير العمولات المعلقة للمستخدم.
    - acks_late=True يضمن عدم ضياع المهمة في حال فشل Worker.
    - إعادة محاولة تلقائية مع تأخير 120 ثانية (لمعالجة المعاملات المالية).
    """
    try:
        asyncio.run(_release_commissions_async(user_id, idempotency_key))
        logger.info(f"Commissions released successfully for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to release commissions for user {user_id}: {str(e)}")
        raise self.retry(exc=e, countdown=120)