# app/tasks/affiliate.py
from celery import shared_task
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from decimal import Decimal
import asyncio

from app.core.config import settings
from app.domains.affiliate.service import AffiliateService
from app.domains.finance.service import FinanceService
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


@shared_task(name="affiliate.distribute_commissions", bind=True, max_retries=3, default_retry_delay=60)
def distribute_commissions_task(self, order_id: int, tenant_id: int):
    """توزيع العمولات بشكل غير متزامن عبر Celery"""
    try:
        result = asyncio.run(_distribute_commissions_async(order_id, tenant_id))
        return {"status": "success", "count": len(result)}
    except Exception as e:
        logger.error(f"Failed to distribute commissions for order {order_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)


async def _release_commissions_async(user_id: int):
    """إفراج العمولات المعلقة"""
    async with AsyncSessionLocal() as db:
        service = AffiliateService(db)
        finance = FinanceService(db)

        # جلب العمولات المعلقة
        repo = service.repo
        commissions = await repo.get_pending_commissions(user_id)
        if not commissions:
            return {"status": "no_pending", "count": 0}

        # حساب الإجمالي
        total = sum(c.commission_amount for c in commissions)

        # التحويل إلى المحفظة
        tx = await finance.transfer(
            sender_id=1,
            receiver_id=user_id,
            amount=total,
            currency="MR_USDT",
            notes=f"إفراج عمولات للمستخدم {user_id}",
            idempotency_key=f"RELEASE-{user_id}-{datetime.now().timestamp()}",
        )

        # تحديث حالة العمولات
        for commission in commissions:
            await repo.update_commission_status(
                commission.id,
                status="CONFIRMED",
                paid_at=datetime.now(timezone.utc),
                paid_tx_hash=tx.tx_hash,
            )

        await db.commit()
        logger.info(f"Released {len(commissions)} commissions for user {user_id}, total: {total}")
        return {"status": "success", "count": len(commissions), "total": float(total)}


@shared_task(name="affiliate.release_commissions", bind=True, max_retries=3, default_retry_delay=120)
def release_commissions_task(self, user_id: int):
    """إفراج العمولات المعلقة بشكل غير متزامن"""
    try:
        result = asyncio.run(_release_commissions_async(user_id))
        return result
    except Exception as e:
        logger.error(f"Failed to release commissions for user {user_id}: {str(e)}")
        raise self.retry(exc=e, countdown=120)


@shared_task(name="affiliate.clean_expired_links", bind=True)
def clean_expired_links_task(self):
    """تنظيف روابط الدعوة المنتهية الصلاحية (اختياري)"""
    # تنفيذ منطق التنظيف حسب الحاجة
    pass