# app/tasks/commerce.py
"""
مهام Celery لقطاع التجارة (Commerce).
تدعم: توزيع العمولات، معالجة الطلبات المعلقة، تحديث المخزون، وإنشاء تقارير المبيعات، وإعادة محاولة المدفوعات الفاشلة.
"""
import asyncio
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime

# 🔥 استيراد التطبيق المركزي والاتصال الموحّد بقاعدة البيانات
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.logging_conf import logger
from app.domains.commerce.service import CommerceService


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
    name="commerce.distribute_commissions",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,                    # 🔥 تأكيد بعد التنفيذ
    time_limit=300,                    # 5 دقائق كحد أقصى
    soft_time_limit=240,               # 4 دقائق إنذار
)
def distribute_commissions_task(
    self,
    order_id: int,
    affiliate_code: str,
    order_total: float
):
    """
    توزيع العمولات على المحالين (Affiliates) بعد إتمام الطلب.
    - تُستدعى تلقائياً بعد نجاح عملية الدفع.
    - تحسب العمولات حسب نسب الإحالة.
    - تُسجل العمولات في جدول `AffiliateCommission`.
    """
    try:
        async def _run():
            async with SessionLocal() as db:
                service = CommerceService(db)
                total = Decimal(str(order_total))
                result = await service.distribute_commissions(
                    order_id=order_id,
                    affiliate_code=affiliate_code,
                    order_total=total
                )
                await db.commit()
                if result is None:
                    result = {"count": 0, "total": 0}
                logger.info(
                    f"✅ Commissions distributed for order {order_id}: "
                    f"{result.get('count', 0)} commissions, total: {result.get('total', 0)}"
                )
                return result

        result = _run_async(_run())
        logger.info(f"✅ Distribute commissions task completed for order {order_id}")
        return {
            "status": "success",
            "order_id": order_id,
            "result": result
        }

    except Exception as e:
        logger.error(f"❌ Failed to distribute commissions for order {order_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)


# ============================================================
# 3. مهمة معالجة الطلبات المعلقة (Pending Orders)
# ============================================================
@celery_app.task(
    name="commerce.process_pending_orders",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    acks_late=True,
    time_limit=600,                    # 10 دقائق
    soft_time_limit=480,
)
def process_pending_orders_task(self):
    """
    معالجة الطلبات المعلقة (غير المدفوعة أو قيد المراجعة).
    - تُنفذ كل ساعة.
    - تُرسل تذكيرات للعملاء بالطلبات المعلقة.
    - تُلغي الطلبات التي تجاوزت المهلة الزمنية (48 ساعة).
    """
    try:
        async def _run():
            async with SessionLocal() as db:
                service = CommerceService(db)
                result = await service.process_pending_orders()
                await db.commit()
                if result is None:
                    result = {"reminded": 0, "cancelled": 0}
                logger.info(
                    f"✅ Pending orders processed: "
                    f"{result.get('reminded', 0)} reminded, "
                    f"{result.get('cancelled', 0)} cancelled"
                )
                return result

        result = _run_async(_run())
        logger.info("✅ Process pending orders task completed successfully.")
        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"❌ Failed to process pending orders: {str(e)}")
        raise self.retry(exc=e, countdown=120)


# ============================================================
# 4. مهمة تحديث المخزون (Inventory Sync)
# ============================================================
@celery_app.task(
    name="commerce.update_inventory",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    time_limit=300,
    soft_time_limit=240,
)
def update_inventory_task(self, product_id: int, quantity_change: int):
    """
    تحديث المخزون بعد عملية شراء أو إرجاع.
    - تُستدعى عند كل عملية شراء ناجحة أو إرجاع.
    - تُحدث الكمية الفعلية في قاعدة البيانات.
    - تُسجل حركة المخزون في جدول `InventoryTransaction`.
    """
    try:
        async def _run():
            async with SessionLocal() as db:
                service = CommerceService(db)
                result = await service.update_inventory(
                    product_id=product_id,
                    quantity_change=quantity_change
                )
                await db.commit()
                if result is None:
                    result = {"new_quantity": 0}
                logger.info(
                    f"✅ Inventory updated for product {product_id}: "
                    f"change={quantity_change}, new_quantity={result.get('new_quantity')}"
                )
                return result

        result = _run_async(_run())
        logger.info(f"✅ Update inventory task completed for product {product_id}")
        return {
            "status": "success",
            "product_id": product_id,
            "result": result
        }

    except Exception as e:
        logger.error(f"❌ Failed to update inventory for product {product_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)


# ============================================================
# 5. مهمة إنشاء تقرير المبيعات اليومي
# ============================================================
@celery_app.task(
    name="commerce.generate_daily_sales_report",
    bind=True,
    max_retries=2,
    default_retry_delay=600,
    acks_late=True,
    time_limit=1800,                   # 30 دقيقة
    soft_time_limit=1500,
)
def generate_daily_sales_report_task(self, tenant_id: Optional[int] = None):
    """
    إنشاء تقرير المبيعات اليومي.
    - تُنفذ في نهاية كل يوم (الساعة 23:59).
    - تُرسل التقرير إلى بريد المدير التنفيذي.
    - تتضمن: إجمالي المبيعات، عدد الطلبات، المنتجات الأكثر مبيعاً.
    """
    try:
        async def _run():
            async with SessionLocal() as db:
                service = CommerceService(db)
                report = await service.generate_daily_sales_report(tenant_id)
                await db.commit()
                if report is None:
                    report = {"message": "No data for today"}
                target = tenant_id or "ALL"
                logger.info(f"📊 Daily sales report generated for tenant: {target}")
                return report

        result = _run_async(_run())
        logger.info("✅ Daily sales report task completed successfully.")
        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"❌ Failed to generate daily sales report: {str(e)}")
        raise self.retry(exc=e, countdown=600)


# ============================================================
# 6. مهمة إعادة محاولة المدفوعات الفاشلة
# ============================================================
@celery_app.task(
    name="commerce.retry_failed_payments",
    bind=True,
    max_retries=5,
    default_retry_delay=600,           # 10 دقائق
    acks_late=True,
    time_limit=3600,                   # ساعة واحدة
    soft_time_limit=3000,
)
def retry_failed_payments_task(self):
    """
    إعادة محاولة المدفوعات الفاشلة (بسبب انقطاع الشبكة أو خطأ مؤقت).
    - تُنفذ كل ساعة.
    - تحاول إعادة معالجة الطلبات التي فشل دفعها.
    - تُرسل إشعارات للعملاء بنجاح الدفع أو فشله النهائي.
    """
    try:
        async def _run():
            async with SessionLocal() as db:
                service = CommerceService(db)
                result = await service.retry_failed_payments()
                await db.commit()
                if result is None:
                    result = {"successful": 0, "failed": 0}
                logger.info(
                    f"✅ Failed payments retried: "
                    f"{result.get('successful', 0)} succeeded, "
                    f"{result.get('failed', 0)} failed permanently"
                )
                return result

        result = _run_async(_run())
        logger.info("✅ Retry failed payments task completed successfully.")
        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"❌ Failed to retry payments: {str(e)}")
        raise self.retry(exc=e, countdown=600)