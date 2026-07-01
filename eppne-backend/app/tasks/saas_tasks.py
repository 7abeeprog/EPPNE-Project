# app/tasks/saas_tasks.py
from celery import shared_task
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import asyncio

from app.core.config import settings
from app.domains.saas.service import SaaSControlService
from app.core.logging import logger

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _process_auto_renewals_async():
    async with AsyncSessionLocal() as db:
        service = SaaSControlService(db)
        results = await service.process_auto_renewals()
        await db.commit()
        return results


@shared_task(name="saas.process_auto_renewals", bind=True, max_retries=3, default_retry_delay=3600)
def process_auto_renewals_task(self):
    """مهمة تجديد الاشتراكات التلقائية (تُنفذ يومياً في الساعة 2 صباحاً)"""
    try:
        results = asyncio.run(_process_auto_renewals_async())
        logger.info(f"Auto-renewals processed: {len(results)} subscriptions")
        return results
    except Exception as e:
        logger.error(f"Auto-renewals failed: {str(e)}")
        raise self.retry(exc=e, countdown=3600)


async def _generate_monthly_invoices_async():
    async with AsyncSessionLocal() as db:
        service = SaaSControlService(db)
        await service.generate_monthly_invoices()
        await db.commit()


@shared_task(name="saas.generate_monthly_invoices", bind=True, max_retries=3, default_retry_delay=3600)
def generate_monthly_invoices_task(self):
    """إنشاء فواتير الشهر الجديد (تُنفذ في أول كل شهر)"""
    try:
        asyncio.run(_generate_monthly_invoices_async())
        logger.info("Monthly invoices generated successfully")
    except Exception as e:
        logger.error(f"Monthly invoices generation failed: {str(e)}")
        raise self.retry(exc=e, countdown=3600)


async def _check_expired_trials_async():
    async with AsyncSessionLocal() as db:
        service = SaaSControlService(db)
        await service.check_and_expire_trials()
        await db.commit()


@shared_task(name="saas.check_expired_trials", bind=True, max_retries=2, default_retry_delay=1800)
def check_expired_trials_task(self):
    """التحقق من انتهاء الفترات التجريبية وتعطيل الخدمات"""
    try:
        asyncio.run(_check_expired_trials_async())
        logger.info("Expired trials checked successfully")
    except Exception as e:
        logger.error(f"Expired trials check failed: {str(e)}")
        raise self.retry(exc=e, countdown=1800)