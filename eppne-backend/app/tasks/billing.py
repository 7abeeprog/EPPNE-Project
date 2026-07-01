# app/tasks/billing.py
"""
مهام الفوترة المجدولة (Celery) – توليد فواتير الـ AI الشهرية ومعالجة اشتراكات التوأم الرقمي.
"""
import asyncio
from typing import List, Optional
from datetime import datetime
from celery import Celery
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.domains.ai_agents.service import AIAgentsService
from app.domains.ai_agents.repository import AIAgentsRepository
from app.domains.digital_twin.service import DigitalTwinService
from app.domains.digital_twin.repository import DigitalTwinRepository
from app.domains.academy.models import AcademyTenant
from app.domains.saas.models import SaaSSubscription
from app.core.logging import logger
from app.core.config import settings

# ============================================================
# تهيئة Celery مع إعدادات من البيئة
# ============================================================
celery_app = Celery(
    "billing",
    broker=settings.CELERY_BROKER_URL or "redis://localhost:6379/0",
    backend=settings.CELERY_RESULT_BACKEND or "redis://localhost:6379/1"
)
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,          # حد أقصى ساعة واحدة
    task_soft_time_limit=3000,     # 50 دقيقة
)


# ============================================================
# دوال مساعدة لجلب المستأجرين النشطين (للاشتراكات المختلفة)
# ============================================================

async def _get_active_tenants(db: AsyncSession, limit: int = 1000) -> List[AcademyTenant]:
    """
    جلب المستأجرين النشطين الذين لديهم اشتراك SaaS نشط مع ميزة AI أو Digital Twin.
    """
    stmt = (
        select(AcademyTenant)
        .join(SaaSSubscription, SaaSSubscription.tenant_id == AcademyTenant.id)
        .where(
            AcademyTenant.is_active == True,
            SaaSSubscription.status == "ACTIVE",
            # نبحث عن أي من الميزتين (ai_agents أو digital_twin) لتشغيل الفوترة
            (SaaSSubscription.features['ai_agents'].astext == 'true') |
            (SaaSSubscription.features['digital_twin'].astext == 'true')
        )
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def _get_active_tenants_for_ai(db: AsyncSession, limit: int = 1000) -> List[AcademyTenant]:
    """جلب المستأجرين الذين لديهم ميزة AI مفعلة."""
    stmt = (
        select(AcademyTenant)
        .join(SaaSSubscription, SaaSSubscription.tenant_id == AcademyTenant.id)
        .where(
            AcademyTenant.is_active == True,
            SaaSSubscription.status == "ACTIVE",
            SaaSSubscription.features['ai_agents'].astext == 'true'
        )
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def _get_active_tenants_for_twin(db: AsyncSession, limit: int = 1000) -> List[AcademyTenant]:
    """جلب المستأجرين الذين لديهم ميزة Digital Twin مفعلة."""
    stmt = (
        select(AcademyTenant)
        .join(SaaSSubscription, SaaSSubscription.tenant_id == AcademyTenant.id)
        .where(
            AcademyTenant.is_active == True,
            SaaSSubscription.status == "ACTIVE",
            SaaSSubscription.features['digital_twin'].astext == 'true'
        )
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


# ============================================================
# 1. مهمة توليد فواتير الـ AI (الموجودة سابقاً)
# ============================================================

async def _generate_invoices_for_tenant(db: AsyncSession, tenant_id: int) -> Optional[dict]:
    """
    توليد فاتورة لمستأجر واحد (تُستدعى بشكل متوازٍ أو متسلسل).
    """
    service = AIAgentsService(db)
    repo = AIAgentsRepository(db)

    # 1. التحقق من آخر تاريخ فوترة (Checkpoint)
    last_billed_month = await repo.get_last_billed_month(tenant_id)
    current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if last_billed_month and last_billed_month >= current_month:
        logger.info(f"Tenant {tenant_id} already billed for this month. Skipping.")
        return None

    # 2. توليد الفاتورة
    try:
        invoice = await service.generate_monthly_invoice(tenant_id)
        if invoice:
            # 3. تحديث نقطة التفتيش
            await repo.update_last_billed_month(tenant_id, current_month)
            logger.info(f"Invoice generated for tenant {tenant_id}: {invoice.id}, amount: {invoice.amount}")
            return {"tenant_id": tenant_id, "invoice_id": invoice.id, "amount": float(invoice.amount)}
        else:
            logger.info(f"No AI usage for tenant {tenant_id}, skipping invoice.")
            return None
    except Exception as e:
        logger.error(f"Failed to generate invoice for tenant {tenant_id}: {e}")
        raise


async def _generate_invoices_with_checkpoints():
    """
    توليد الفواتير مع نقاط تفتيش وحد أقصى للمعالجة (1000 مستأجر).
    """
    async with async_session() as db:
        tenants = await _get_active_tenants_for_ai(db, limit=1000)

    if not tenants:
        logger.info("No active tenants with AI subscriptions found.")
        return

    start_time = datetime.utcnow()
    successful = 0
    failed = 0
    failed_tenants = []
    total_tenants = len(tenants)

    logger.info(f"Starting AI billing cycle for {total_tenants} tenants.")

    semaphore = asyncio.Semaphore(10)

    async def limited_task(tenant):
        async with semaphore:
            try:
                async with async_session() as tenant_db:
                    result = await _generate_invoices_for_tenant(tenant_db, tenant.id)
                    return {"tenant_id": tenant.id, "success": True, "result": result}
            except Exception as e:
                return {"tenant_id": tenant.id, "success": False, "error": str(e)}

    tasks = [limited_task(tenant) for tenant in tenants]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for res in results:
        if isinstance(res, dict) and res.get("success"):
            successful += 1
        else:
            failed += 1
            if isinstance(res, dict):
                failed_tenants.append(res.get("tenant_id"))
            else:
                failed_tenants.append("UNKNOWN")

    duration = datetime.utcnow() - start_time
    logger.info(
        f"AI billing cycle completed. "
        f"Total: {total_tenants}, Successful: {successful}, Failed: {failed}, "
        f"Failed tenants: {failed_tenants}, Duration: {duration}"
    )

    if failed > 5:
        logger.error(f"⚠️ High failure rate in AI billing: {failed} out of {total_tenants} tenants failed.")


# ============================================================
# 2. مهمة معالجة اشتراكات التوأم الرقمي (الجديدة)
# ============================================================

async def _process_twin_subscription_for_tenant(db: AsyncSession, tenant_id: int) -> dict:
    """
    معالجة اشتراكات التوأم الرقمي لمستأجر واحد.
    """
    service = DigitalTwinService(db)
    twin_repo = DigitalTwinRepository(db)

    # جلب جميع التوائم النشطة في هذا المستأجر
    twins = await twin_repo.list_active_twins(tenant_id)
    if not twins:
        logger.info(f"No active digital twins for tenant {tenant_id}.")
        return {"tenant_id": tenant_id, "processed": 0, "successful": 0, "failed": 0}

    processed = 0
    successful = 0
    failed = 0

    for twin in twins:
        if twin.subscription_monthly_mrusdt > 0:
            processed += 1
            try:
                # خصم المبلغ من محفظة المالك
                await service.finance.transfer(
                    sender_id=twin.user_id,
                    receiver_email="system@eppne.com",
                    currency="MR_USDT",
                    amount=twin.subscription_monthly_mrusdt,
                    notes=f"Monthly subscription for Digital Twin (User: {twin.user_id})"
                )
                successful += 1
                logger.info(f"Subscription fee collected for twin {twin.id} (User: {twin.user_id})")
            except Exception as e:
                failed += 1
                logger.error(f"Failed to collect subscription for twin {twin.id}: {e}")

    return {
        "tenant_id": tenant_id,
        "processed": processed,
        "successful": successful,
        "failed": failed
    }


async def _process_twin_subscriptions_with_checkpoints():
    """
    معالجة اشتراكات التوأم الرقمي مع نقاط تفتيش وحد أقصى للمعالجة (1000 مستأجر).
    """
    async with async_session() as db:
        tenants = await _get_active_tenants_for_twin(db, limit=1000)

    if not tenants:
        logger.info("No active tenants with Digital Twin subscriptions found.")
        return

    start_time = datetime.utcnow()
    successful_tenants = 0
    failed_tenants = 0
    total_tenants = len(tenants)
    total_processed = 0
    total_successful = 0
    total_failed = 0

    logger.info(f"Starting Digital Twin billing cycle for {total_tenants} tenants.")

    semaphore = asyncio.Semaphore(10)

    async def limited_task(tenant):
        async with semaphore:
            try:
                async with async_session() as tenant_db:
                    result = await _process_twin_subscription_for_tenant(tenant_db, tenant.id)
                    return {"tenant_id": tenant.id, "success": True, "result": result}
            except Exception as e:
                return {"tenant_id": tenant.id, "success": False, "error": str(e)}

    tasks = [limited_task(tenant) for tenant in tenants]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for res in results:
        if isinstance(res, dict) and res.get("success"):
            successful_tenants += 1
            data = res.get("result", {})
            total_processed += data.get("processed", 0)
            total_successful += data.get("successful", 0)
            total_failed += data.get("failed", 0)
        else:
            failed_tenants += 1

    duration = datetime.utcnow() - start_time
    logger.info(
        f"Digital Twin billing cycle completed. "
        f"Tenants: Total: {total_tenants}, Successful: {successful_tenants}, Failed: {failed_tenants}. "
        f"Twins: Processed: {total_processed}, Successful: {total_successful}, Failed: {total_failed}. "
        f"Duration: {duration}"
    )

    if failed_tenants > 5:
        logger.error(f"⚠️ High failure rate in Digital Twin billing: {failed_tenants} out of {total_tenants} tenants failed.")


# ============================================================
# نقاط الدخول المجدولة (Celery Tasks)
# ============================================================

@celery_app.task(name="billing.generate_monthly_ai_invoices")
def generate_monthly_ai_invoices():
    """توليد فواتير الـ AI الشهرية."""
    try:
        asyncio.run(_generate_invoices_with_checkpoints())
        logger.info("Monthly AI invoice generation task finished successfully.")
    except Exception as e:
        logger.error(f"Monthly AI invoice generation task failed: {e}")
        raise


@celery_app.task(name="billing.process_twin_subscriptions")
def process_twin_subscriptions():
    """معالجة اشتراكات التوأم الرقمي الشهرية."""
    try:
        asyncio.run(_process_twin_subscriptions_with_checkpoints())
        logger.info("Digital Twin subscription processing task finished successfully.")
    except Exception as e:
        logger.error(f"Digital Twin subscription processing task failed: {e}")
        raise