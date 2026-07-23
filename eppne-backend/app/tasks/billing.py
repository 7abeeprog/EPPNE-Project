# app/tasks/billing.py
"""
مهام الفوترة المجدولة (Celery) – توليد فواتير الـ AI الشهرية ومعالجة اشتراكات التوأم الرقمي.
تدعم: المعالجة المتوازية، نقاط التفتيش، إعادة المحاولة، والحدود الزمنية.
"""
import asyncio
from typing import List, Optional
from datetime import datetime
import uuid
from decimal import Decimal
from typing import cast

# 🔥 استيراد التطبيق المركزي والاتصال الموحّد بقاعدة البيانات
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.logging_conf import logger

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai_agents.service import AIAgentsService
from app.domains.ai_agents.repository import AIAgentsRepository
from app.domains.digital_twin.service import DigitalTwinService
from app.domains.digital_twin.repository import DigitalTwinRepository
from app.domains.academy.models import AcademyTenant
from app.domains.saas.models import SaaSSubscription


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
# 2. دوال مساعدة لجلب المستأجرين النشطين
# ============================================================
async def _get_active_tenants(db: AsyncSession, limit: int = 1000) -> List[AcademyTenant]:
    """جلب المستأجرين النشطين الذين لديهم اشتراك SaaS نشط مع ميزة AI أو Digital Twin."""
    stmt = (
        select(AcademyTenant)
        .join(SaaSSubscription, SaaSSubscription.tenant_id == AcademyTenant.id)
        .where(
            AcademyTenant.is_active == True,
            SaaSSubscription.status == "ACTIVE",
            (SaaSSubscription.features['ai_agents'].astext == 'true') |
            (SaaSSubscription.features['digital_twin'].astext == 'true')
        )
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


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
    return list(result.scalars().all())


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
    return list(result.scalars().all())


# ============================================================
# 3. مهمة توليد فواتير الـ AI الشهرية
# ============================================================
@celery_app.task(
    name="billing.generate_monthly_ai_invoices",
    bind=True,
    max_retries=3,
    default_retry_delay=600,        # 10 دقائق بين المحاولات
    acks_late=True,                  # 🔥 تأكيد بعد التنفيذ
    time_limit=7200,                 # ساعتان كحد أقصى (معالجة آلاف المستأجرين)
    soft_time_limit=6000,            # 100 دقيقة إنذار
)
def generate_monthly_ai_invoices(self):
    """توليد فواتير الـ AI الشهرية."""
    try:
        result = _run_async(_generate_invoices_with_checkpoints())
        logger.info("✅ Monthly AI invoice generation task finished successfully.")
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"❌ Monthly AI invoice generation task failed: {e}")
        raise self.retry(exc=e, countdown=600)


# ============================================================
# 4. مهمة معالجة اشتراكات التوأم الرقمي
# ============================================================
@celery_app.task(
    name="billing.process_twin_subscriptions",
    bind=True,
    max_retries=3,
    default_retry_delay=600,
    acks_late=True,
    time_limit=7200,
    soft_time_limit=6000,
)
def process_twin_subscriptions(self):
    """معالجة اشتراكات التوأم الرقمي الشهرية."""
    try:
        result = _run_async(_process_twin_subscriptions_with_checkpoints())
        logger.info("✅ Digital Twin subscription processing task finished successfully.")
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"❌ Digital Twin subscription processing task failed: {e}")
        raise self.retry(exc=e, countdown=600)


# ============================================================
# 5. المنطق الفعلي لفوترة الـ AI
# ============================================================
async def _generate_invoices_with_checkpoints():
    """توليد الفواتير مع نقاط تفتيش وحد أقصى للمعالجة."""
    async with SessionLocal() as db:
        tenants = await _get_active_tenants_for_ai(db, limit=1000)

    if not tenants:
        logger.info("ℹ️ No active tenants with AI subscriptions found.")
        return {"total_tenants": 0, "successful": 0, "failed": 0}

    start_time = datetime.utcnow()
    successful = 0
    failed = 0
    failed_tenants = []
    total_tenants = len(tenants)

    logger.info(f"🚀 Starting AI billing cycle for {total_tenants} tenants.")

    semaphore = asyncio.Semaphore(10)  # حد أقصى 10 عمليات متزامنة

    async def limited_task(tenant):
        async with semaphore:
            try:
                async with SessionLocal() as tenant_db:
                    result = await _generate_invoices_for_tenant(tenant_db, tenant.id)
                    return {"tenant_id": tenant.id, "success": True, "result": result}
            except Exception as e:
                logger.error(f"❌ Failed to generate invoice for tenant {tenant.id}: {e}")
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
        f"✅ AI billing cycle completed. "
        f"Total: {total_tenants}, Successful: {successful}, Failed: {failed}, "
        f"Failed tenants: {failed_tenants}, Duration: {duration}"
    )

    if failed > 5:
        logger.error(f"⚠️ High failure rate in AI billing: {failed} out of {total_tenants} tenants failed.")

    return {
        "total_tenants": total_tenants,
        "successful": successful,
        "failed": failed,
        "failed_tenants": failed_tenants,
        "duration_seconds": duration.total_seconds()
    }


async def _generate_invoices_for_tenant(db: AsyncSession, tenant_id: int) -> Optional[dict]:
    """توليد فاتورة لمستأجر واحد."""
    service = AIAgentsService(db)
    repo = AIAgentsRepository(db)

    # 1. التحقق من آخر تاريخ فوترة (Checkpoint)
    last_billed_month = await repo.get_last_billed_month(tenant_id)
    current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if last_billed_month and last_billed_month >= current_month:
        logger.info(f"⏭️ Tenant {tenant_id} already billed for this month. Skipping.")
        return None

    # 2. توليد الفاتورة (باستخدام الدالة الجديدة)
    try:
        invoice = await service.generate_monthly_invoice(tenant_id)
        if invoice:
            # 3. تحديث نقطة التفتيش
            await repo.update_last_billed_month(tenant_id, current_month)
            logger.info(f"✅ Invoice generated for tenant {tenant_id}: {invoice.id}, amount: {invoice.amount}")
            return {
                "tenant_id": tenant_id,
                "invoice_id": invoice.id,
                "amount": float(invoice.amount)
            }
        else:
            logger.info(f"ℹ️ No AI usage for tenant {tenant_id}, skipping invoice.")
            return None
    except Exception as e:
        logger.error(f"❌ Failed to generate invoice for tenant {tenant_id}: {e}")
        raise


# ============================================================
# 6. المنطق الفعلي لاشتراكات التوأم الرقمي
# ============================================================
async def _process_twin_subscriptions_with_checkpoints():
    """معالجة اشتراكات التوأم الرقمي مع نقاط تفتيش."""
    async with SessionLocal() as db:
        tenants = await _get_active_tenants_for_twin(db, limit=1000)

    if not tenants:
        logger.info("ℹ️ No active tenants with Digital Twin subscriptions found.")
        return {
            "total_tenants": 0,
            "successful_tenants": 0,
            "total_processed": 0,
            "total_successful": 0,
            "total_failed": 0
        }

    start_time = datetime.utcnow()
    successful_tenants = 0
    failed_tenants = 0
    total_tenants = len(tenants)
    total_processed = 0
    total_successful = 0
    total_failed = 0

    logger.info(f"🚀 Starting Digital Twin billing cycle for {total_tenants} tenants.")

    semaphore = asyncio.Semaphore(10)

    async def limited_task(tenant):
        async with semaphore:
            try:
                async with SessionLocal() as tenant_db:
                    result = await _process_twin_subscription_for_tenant(tenant_db, tenant.id)
                    return {"tenant_id": tenant.id, "success": True, "result": result}
            except Exception as e:
                logger.error(f"❌ Failed to process twin subscriptions for tenant {tenant.id}: {e}")
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
        f"✅ Digital Twin billing cycle completed. "
        f"Tenants: Total: {total_tenants}, Successful: {successful_tenants}, Failed: {failed_tenants}. "
        f"Twins: Processed: {total_processed}, Successful: {total_successful}, Failed: {total_failed}. "
        f"Duration: {duration}"
    )

    if failed_tenants > 5:
        logger.error(f"⚠️ High failure rate in Digital Twin billing: {failed_tenants} out of {total_tenants} tenants failed.")

    return {
        "total_tenants": total_tenants,
        "successful_tenants": successful_tenants,
        "failed_tenants": failed_tenants,
        "total_processed": total_processed,
        "total_successful": total_successful,
        "total_failed": total_failed,
        "duration_seconds": duration.total_seconds()
    }


async def _process_twin_subscription_for_tenant(db: AsyncSession, tenant_id: int) -> dict:
    """معالجة اشتراكات التوأم الرقمي لمستأجر واحد."""
    service = DigitalTwinService(db)

    # ✅ استخدام الدالة الجديدة list_active_twins
    twin_repo = DigitalTwinRepository(db)
    twins = await twin_repo.list_active_twins(tenant_id)

    if not twins:
        logger.info(f"ℹ️ No active digital twins for tenant {tenant_id}.")
        return {"tenant_id": tenant_id, "processed": 0, "successful": 0, "failed": 0}

    processed = 0
    successful = 0
    failed = 0

    for twin in twins:
        # 🔥 استخدام cast لحل مشاكل الأنواع
        monthly_fee = cast(Decimal, twin.subscription_monthly_mrusdt)
        if monthly_fee > 0:
            processed += 1
            try:
                idempotency_key = f"twin_subscription_{twin.id}_{uuid.uuid4().hex[:8]}"
                # 🔥 استخدام cast لتحويل user_id و amount
                await service.finance.transfer(
                    sender_id=cast(int, twin.user_id),
                    receiver_email="system@eppne.com",
                    currency="MR_USDT",
                    amount=monthly_fee,
                    notes=f"Monthly subscription for Digital Twin (User: {twin.user_id})",
                    idempotency_key=idempotency_key
                )
                successful += 1
                logger.info(f"✅ Subscription fee collected for twin {twin.id} (User: {twin.user_id})")
            except Exception as e:
                failed += 1
                logger.error(f"❌ Failed to collect subscription for twin {twin.id}: {e}")

    return {
        "tenant_id": tenant_id,
        "processed": processed,
        "successful": successful,
        "failed": failed
    }