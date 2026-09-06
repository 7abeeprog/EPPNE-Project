# app/tasks/affiliate.py
"""
مهام Celery الموحّدة لقطاع الإحالات (Affiliate).
تم دمج affiliate.py و affiliate_tasks.py في ملف واحد.
يدعم: توزيع العمولات، تحرير العمولات المعلقة، وتنظيف الروابط المنتهية.
"""
import asyncio
from datetime import datetime, timezone, timedelta  # 🔥 إضافة timedelta
from decimal import Decimal
from typing import Dict, Any, Optional

# 🔥 استيراد التطبيق المركزي والاتصال الموحّد بقاعدة البيانات
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.domains.affiliate.service import AffiliateService
from app.domains.affiliate.repository import AffiliateRepository
from app.core.logging_conf import logger


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
# 2. مهمة توزيع العمولات (بعد إتمام الطلب)
# ============================================================
@celery_app.task(
    name="affiliate.distribute_commissions",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,          # 🔥 تأكيد بعد التنفيذ (يمنع فقدان المهمة)
    time_limit=300,          # 5 دقائق كحد أقصى
    soft_time_limit=240,     # 4 دقائق إنذار
)
def distribute_commissions_task(self, order_id: int, tenant_id: int):
    """
    توزيع العمولات بشكل غير متزامن عبر Celery.
    تُستدعى تلقائياً بعد إتمام الطلب في قطاع التجارة.
    """
    try:
        async def _run():
            async with SessionLocal() as db:
                service = AffiliateService(db, tenant_id)
                commissions = await service.distribute_commissions_for_order(order_id)
                await db.commit()
                logger.info(f"✅ Distributed {len(commissions)} commissions for order {order_id}")
                return {"status": "success", "count": len(commissions)}
        
        result = _run_async(_run())
        logger.info(f"Commissions distributed successfully for order {order_id}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to distribute commissions for order {order_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)


# ============================================================
# 3. مهمة تحرير العمولات المعلقة (للمستخدم)
# ============================================================
@celery_app.task(
    name="affiliate.release_commissions",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    acks_late=True,          # 🔥 تأكيد بعد التنفيذ
    time_limit=600,          # 10 دقائق (لأنها تشمل تحويلات مالية)
    soft_time_limit=480,     # 8 دقائق إنذار
)
def release_commissions_task(self, user_id: int, tenant_id: int, idempotency_key: str):
    """
    تحرير العمولات المعلقة للمستخدم.
    - تتحقق من Idempotency لمنع الدفع المزدوج.
    - تحول المبلغ الإجمالي إلى محفظة المستخدم.
    """
    try:
        async def _run():
            async with SessionLocal() as db:
                service = AffiliateService(db, tenant_id)
                result = await service.release_commissions(user_id, idempotency_key=idempotency_key)
                await db.commit()
                logger.info(f"✅ Released commissions for user {user_id}: {result.get('count', 0)} commissions")
                return result

        result = _run_async(_run())
        logger.info(f"Commissions released successfully for user {user_id}")
        return result

    except Exception as e:
        logger.error(f"❌ Failed to release commissions for user {user_id}: {str(e)}")
        raise self.retry(exc=e, countdown=120)


# ============================================================
# 4. مهمة تنظيف الروابط المنتهية (جدولة دورية)
# ============================================================
@celery_app.task(
    name="affiliate.clean_expired_links",
    bind=True,
    max_retries=2,
    default_retry_delay=3600,  # ساعة واحدة
    acks_late=True,
    time_limit=300,
    soft_time_limit=240,
)
def clean_expired_links_task(self):
    """
    تنظيف روابط الدعوة المنتهية الصلاحية — لكل الـtenants النشطين.
    تُستدعى بشكل دوري (مثلاً يومياً) عبر جدولة Celery Beat.

    ملاحظة (migration 045 / Phase 8): `delete_expired_invitations`
    تتطلب `tenant_id` إجباريًا (لا يوجد "كل الـtenants" على مستوى
    الـrepository) — هذا أول نمط "loop عبر كل الـtenants" بالمشروع
    لمهمة Celery دورية (لا سابقة مماثلة في saas_tasks.py/agritech.py
    وقت كتابة هذا الكود، راجع تقرير الجلسة §3).
    """
    try:
        async def _run():
            async with SessionLocal() as db:
                from sqlalchemy import select
                from app.domains.academy.models import AcademyTenant

                repo = AffiliateRepository(db)
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)

                tenant_ids_result = await db.execute(
                    select(AcademyTenant.id).where(AcademyTenant.is_active.is_(True))
                )
                tenant_ids = [row[0] for row in tenant_ids_result.all()]

                total_deleted = 0
                for tid in tenant_ids:
                    total_deleted += await repo.delete_expired_invitations(cutoff_date, tid)

                await db.commit()
                logger.info(
                    f"🧹 Cleaned {total_deleted} expired affiliate links "
                    f"across {len(tenant_ids)} active tenants"
                )
                return {
                    "status": "success",
                    "deleted_count": total_deleted,
                    "tenants_processed": len(tenant_ids),
                }

        result = _run_async(_run())
        logger.info("✅ Expired affiliate links cleaned successfully.")
        return result

    except Exception as e:
        logger.error(f"❌ Failed to clean expired affiliate links: {str(e)}")
        raise self.retry(exc=e, countdown=3600)