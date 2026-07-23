# app/domains/commerce/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func
from decimal import Decimal
import uuid
import random
import json
from typing import Optional, List, Dict, Any, cast
from datetime import datetime, timedelta

from app.domains.commerce.repository import CommerceRepository
from app.domains.commerce.models import StoreProfile, Product, Order, PaymentRequest, CommerceAuditLog
from app.domains.commerce.schemas import ProductCreate, CheckoutRequest
from app.domains.finance.service import FinanceService
from app.core.errors import InsufficientBalanceError, NotFoundError, PermissionDeniedError, ValidationError
from app.core.logging_conf import logger
from app.core.idempotency import get_idempotency_result, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client


class CommerceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CommerceRepository(db)
        self.finance = FinanceService(db)
        self.event_bus = EventBus(redis_client)  # type: ignore

    # ============================================================
    # دوال مساعدة
    # ============================================================

    async def _get_user_email(self, user_id: int) -> str:
        """جلب بريد المستخدم (محاكاة)"""
        return f"user_{user_id}@eppne.com"

    async def _create_audit_log(
        self,
        user_id: int,
        action: str,
        details: dict,
        order_id: Optional[int] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ):
        log = CommerceAuditLog(
            user_id=user_id,
            order_id=order_id,
            action=action,
            details=details,
            ip_address=ip,
            user_agent=ua
        )
        self.db.add(log)
        await self.db.flush()

    async def get_or_create_store(self, tenant_id: int, name: Optional[str] = None) -> StoreProfile:
        store = await self.repo.get_store_by_tenant(tenant_id)
        if not store:
            store = await self.repo.create_store(
                tenant_id=tenant_id,
                name=name or f"Store_{tenant_id}",
                currency="MR_USDT",
                owner_email=f"tenant_{tenant_id}@eppne.com",
                is_affiliate_enabled=True
            )
        return store

    # ============================================================
    # 1. إدارة المتجر والمنتجات
    # ============================================================

    async def create_product(self, tenant_id: int, data: ProductCreate, creator_id: int) -> Product:
        """إنشاء منتج جديد مع المتغيرات"""
        store = await self.get_or_create_store(tenant_id)

        product_data = data.model_dump(exclude={"variants"})
        product = await self.repo.create_product(**product_data, store_id=store.id)

        for var_data in data.variants:
            await self.repo.create_variant(product_id=product.id, **var_data.model_dump())

        await self.db.commit()

        await self._create_audit_log(
            user_id=creator_id,
            action="PRODUCT_CREATED",
            details={"product_id": product.id, "title": product.title}
        )

        return product

    async def list_products(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 50,
        only_published: bool = True
    ):
        """جلب قائمة المنتجات للمستأجر"""
        store = await self.get_or_create_store(tenant_id)
        return await self.repo.get_products_by_store(cast(int, store.id), skip, limit, only_published)

    # ============================================================
    # 2. الطلبات (Checkout)
    # ============================================================

    async def checkout(
        self,
        customer_id: int,
        checkout_data: CheckoutRequest,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> Order:
        """إنشاء طلب جديد مع خصم المخزون والدفع"""
        if not checkout_data.idempotency_key:
            raise ValidationError("Idempotency key is required")

        # التحقق من Idempotency
        existing_order = await self.repo.get_order_by_idempotency_key(checkout_data.idempotency_key)
        if existing_order:
            logger.info(f"Duplicate checkout blocked: {checkout_data.idempotency_key}")
            return existing_order

        store = await self.repo.get_store(checkout_data.store_id)
        if not store or not store.is_active:  # type: ignore
            raise NotFoundError("المتجر غير موجود أو غير نشط")

        total = Decimal(0)
        order_items = []

        # 🔥 معاملة ذرية لحجز المخزون وإنشاء الطلب
        async with self.db.begin_nested():
            for cart_item in checkout_data.items:
                variant = await self.repo.get_variant_for_update(cart_item.variant_id)
                if not variant:
                    raise NotFoundError(f"المتغير {cart_item.variant_id} غير موجود")

                product = await self.repo.get_product(cast(int, variant.product_id))
                if not product or not cast(Any, product.is_published):
                    raise NotFoundError(f"المنتج {variant.product_id} غير منشور")

                if cast(int, variant.stock_quantity) < cart_item.quantity:
                    raise ValidationError(
                        f"الكمية المطلوبة من {variant.sku} غير متوفرة. المتاح: {variant.stock_quantity}"
                    )

                # تحديث المخزون
                variant.stock_quantity = cast(int, variant.stock_quantity) - cart_item.quantity  # type: ignore
                await self.db.flush()

                unit_price = cast(Decimal, variant.price_mrusdt)
                if cast(Any, variant.is_wholesale_enabled) and cast(Any, variant.wholesale_min_qty) and cart_item.quantity >= cast(int, variant.wholesale_min_qty):
                    unit_price = cast(Decimal, variant.wholesale_price_mrusdt) or unit_price

                line_total = unit_price * cart_item.quantity
                total += line_total

                order_items.append({
                    "product_id": product.id,
                    "variant_id": variant.id,
                    "quantity": cart_item.quantity,
                    "unit_price_mrusdt": unit_price,
                    "total_price_mrusdt": line_total
                })

            # الدفع عبر المحفظة (إن كان)
            payment_tx_hash = None
            if checkout_data.settlement_type == "WALLET_DEDUCTION":
                # توليد Idempotency Key للدفع
                payment_idempotency = f"payment-{checkout_data.idempotency_key}"
                tx = await self.finance.transfer(
                    sender_id=customer_id,
                    receiver_email=cast(str, store.owner_email) or "admin@eppne.com",
                    currency="MR_USDT",
                    amount=cast(Decimal, total),
                    idempotency_key=payment_idempotency,
                    notes=f"Order checkout for store {store.id}"
                )
                payment_tx_hash = tx.tx_hash

            # إنشاء الطلب
            order = await self.repo.create_order(
                store_id=store.id,
                customer_id=customer_id,
                idempotency_key=checkout_data.idempotency_key,
                total_amount_mrusdt=total,
                discount_applied=Decimal(0),
                tax_amount=Decimal(0),
                shipping_fee=Decimal(0),
                shipping_address_id=checkout_data.shipping_address_id,
                status="PAID" if cast(Any, payment_tx_hash) else "PENDING_PAYMENT",
                settlement_type=checkout_data.settlement_type,
                affiliate_code_used=checkout_data.affiliate_code
            )

            for item in order_items:
                await self.repo.create_order_item(order_id=order.id, **item)

        # سجل التدقيق
        await self._create_audit_log(
            user_id=customer_id,
            order_id=cast(int, order.id),
            action="CHECKOUT",
            details={
                "store_id": cast(int, store.id),
                "total": float(cast(Decimal, total)),
                "settlement_type": checkout_data.settlement_type,
                "idempotency_key": checkout_data.idempotency_key
            },
            ip=ip,
            ua=ua
        )

        # توزيع العمولات (خارج المعاملة الأساسية)
        if checkout_data.affiliate_code and cast(Any, store.is_affiliate_enabled):
            # يمكن استدعاء Celery task هنا، لكننا ننفذها مباشرة للتجربة
            await self.distribute_commissions(cast(int, order.id), checkout_data.affiliate_code, cast(Decimal, total))

        return order

    async def get_user_orders(self, user_id: int, skip: int = 0, limit: int = 20):
        """جلب طلبات المستخدم"""
        return await self.repo.get_user_orders(user_id, skip, limit)

    # ============================================================
    # 3. نظام الإحالة (Affiliate)
    # ============================================================

    async def register_affiliate(self, user_id: int, sponsor_code: str):
        """تسجيل مستخدم كداعي تحت راعي معين"""
        sponsor_id = int(sponsor_code) if sponsor_code.isdigit() else None
        if not sponsor_id or sponsor_id == user_id:
            raise PermissionDeniedError("كود الداعي غير صالح")

        sponsor_tree = await self.repo.get_affiliate_tree(sponsor_id)
        depth = sponsor_tree.network_depth + 1 if sponsor_tree else 1  # type: ignore

        return await self.repo.create_affiliate_tree(
            user_id=user_id,
            sponsor_id=sponsor_id,
            network_depth=depth
        )

    async def distribute_commissions(self, order_id: int, affiliate_code: str, order_total: Decimal):
        """توزيع العمولات على سلسلة الداعين"""
        sponsor_id = int(affiliate_code) if affiliate_code.isdigit() else None
        if not sponsor_id:
            return

        chain = await self.repo.get_sponsor_chain(sponsor_id, max_depth=10)
        if not chain:
            return

        config = await self.repo.get_affiliate_config(1)  # tenant_id مؤقت
        if not config or not config.is_active:  # type: ignore
            return

        for level, beneficiary_id in enumerate(chain, start=1):
            if level > 10:
                break

            pct = getattr(config, f"level_{level}_pct", Decimal(0))  # type: ignore
            if pct <= 0:
                continue

            amount = order_total * Decimal(str(pct)) / Decimal(100)
            if amount <= 0:
                continue

            await self.repo.create_commission(
                beneficiary_id=beneficiary_id,
                order_id=order_id,
                level_earned=level,
                amount=amount,
                currency="MR_USDT",
                status="PENDING"
            )

        await self._create_audit_log(
            user_id=sponsor_id,
            order_id=order_id,
            action="COMMISSION_DISTRIBUTED",
            details={"levels": len(chain)}
        )

    async def get_user_commissions(self, user_id: int, skip: int = 0, limit: int = 20):
        """جلب العمولات المعلقة للمستخدم"""
        return await self.repo.get_pending_commissions(user_id, skip, limit)

    async def release_commissions(self, beneficiary_id: int):
        """تحرير العمولات المعلقة (تحويلها إلى المحفظة)"""
        commissions = await self.repo.get_pending_commissions(beneficiary_id)
        for item in commissions:
            comm = cast(Any, item)
            idempotency_key = f"release-{comm.id}-{uuid.uuid4().hex[:12]}"
            await self.finance.transfer(
                sender_id=1,  # حساب النظام
                receiver_email=await self._get_user_email(beneficiary_id),
                currency=comm.currency,
                amount=comm.amount,
                idempotency_key=idempotency_key,
                notes=f"Commission release for order {comm.order_id}"
            )
            await self.repo.release_commission(cast(int, comm.id), f"REL-{uuid.uuid4().hex[:12].upper()}")

    # ============================================================
    # 4. طرق الدفع
    # ============================================================

    async def create_payment_request(
        self,
        order_id: int,
        payment_method: str,
        user_id: int,
        idempotency_key: Optional[str] = None
    ) -> PaymentRequest:
        """إنشاء طلب دفع جديد"""
        # التحقق من Idempotency
        if idempotency_key:
            existing = await self.repo.get_payment_request_by_idempotency_key(idempotency_key)
            if existing:
                return existing

        order = await self.repo.get_order(order_id)
        if not order:
            raise NotFoundError("الطلب غير موجود")

        # التحقق من ملكية الطلب
        if order.customer_id != user_id:  # type: ignore
            raise PermissionDeniedError("ليس لديك صلاحية لهذا الطلب")

        if order.status != "PENDING_PAYMENT":  # type: ignore
            raise PermissionDeniedError("لا يمكن طلب دفع لطلب غير معلق")

        existing = await self.repo.get_payment_request_by_order(order_id, payment_method)
        if existing and existing.status == "PENDING":  # type: ignore
            raise PermissionDeniedError(f"يوجد طلب دفع معلق بالفعل عبر {payment_method}")

        pr_data = {
            "order_id": order_id,
            "payment_method": payment_method,
            "amount": order.total_amount_mrusdt,  # type: ignore
            "currency": "MR_USDT",
            "status": "PENDING",
            "idempotency_key": idempotency_key or f"PR-{uuid.uuid4().hex[:12].upper()}"
        }

        if payment_method == "AGENT":
            pr_data["agent_code"] = f"AG-{random.randint(100000, 999999)}"
        elif payment_method == "VISA":
            pr_data["gateway_transaction_id"] = f"VISA-{uuid.uuid4().hex[:12].upper()}"

        payment_request = await self.repo.create_payment_request(**pr_data)

        # الدفع عند الاستلام يتم تأكيده فوراً
        if payment_method == "CASH_ON_DELIVERY":
            await self.confirm_cash_on_delivery(cast(int, payment_request.id))

        return payment_request

    async def confirm_cash_on_delivery(self, payment_request_id: int):
        """تأكيد الدفع عند الاستلام (تحديث الحالة)"""
        pr = await self.repo.get_payment_request(payment_request_id)
        if not pr or pr.payment_method != "CASH_ON_DELIVERY":  # type: ignore
            return

        await self.repo.update_payment_request(cast(int, pr.id), status="PAID", paid_at=func.now())
        await self.repo.update_order_status(pr.order_id, "PAID")  # type: ignore

    async def confirm_agent_payment(
        self,
        agent_code: str,
        agent_user_id: int,
        idempotency_key: Optional[str] = None
    ) -> Order:
        """تأكيد دفع وكيل (AGENT)"""
        if idempotency_key:
            # التحقق من Idempotency على مستوى سجل التدقيق
            # نستخدم طريقة بسيطة: البحث عن Audit Log بنفس المفتاح
            # (يمكن تحسينها لاحقاً)
            pass

        pr = await self.repo.get_payment_request_by_agent_code(agent_code)
        if not pr or pr.payment_method != "AGENT" or pr.status != "PENDING":  # type: ignore
            raise NotFoundError("طلب الدفع غير موجود أو تم إنجازه مسبقاً")

        await self.repo.update_payment_request(
            cast(int, pr.id),
            status="PAID",
            agent_id=agent_user_id,
            agent_confirmed_at=func.now(),
            paid_at=func.now()
        )

        order = await self.repo.update_order_status(cast(int, pr.order_id), "PAID")

        await self._create_audit_log(
            user_id=agent_user_id,
            order_id=cast(int, pr.order_id),
            action="AGENT_PAYMENT_CONFIRMED",
            details={"payment_request_id": cast(int, pr.id), "idempotency_key": idempotency_key}
        )
        return order

    async def handle_visa_webhook(
        self,
        payload: dict,
        signature: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Order:
        """معالجة Webhook من بوابة الفيزا"""
        if idempotency_key:
            # التحقق من Idempotency (يمكن استخدام جدول منفصل)
            pass

        transaction_id = payload.get("transaction_id")
        order_id = cast(int, payload.get("order_id"))
        status = payload.get("status")

        pr = await self.repo.get_payment_request_by_order(order_id, "VISA")
        if not pr:
            raise NotFoundError("لا يوجد طلب دفع فيزا لهذا الطلب")

        if status == "SUCCESS":
            await self.repo.update_payment_request(cast(int, pr.id), status="PAID", paid_at=func.now(), gateway_response=payload)
            order = await self.repo.update_order_status(order_id, "PAID")
        else:
            await self.repo.update_payment_request(cast(int, pr.id), status="FAILED", gateway_response=payload)
            raise PermissionDeniedError("فشلت عملية الدفع عبر الفيزا")

        await self._create_audit_log(
            user_id=0,
            order_id=order_id,
            action="VISA_WEBHOOK_PROCESSED",
            details={"status": status, "idempotency_key": idempotency_key}
        )
        return order

    async def get_payment_status(self, order_id: int, user_id: int) -> dict:
        """جلب حالة الدفع للطلب مع التحقق من الصلاحية"""
        order = await self.repo.get_order(order_id)
        if not order:
            raise NotFoundError("الطلب غير موجود")

        if order.customer_id != user_id:  # type: ignore
            # يمكن إضافة صلاحية للمشرفين هنا
            pass

        payment_methods = ["AGENT", "VISA", "CASH_ON_DELIVERY"]
        statuses = {}
        for method in payment_methods:
            pr = await self.repo.get_payment_request_by_order(order_id, method)
            if pr:
                statuses[method] = pr.status  # type: ignore

        return {
            "order_id": order_id,
            "order_status": order.status,  # type: ignore
            "payment_requests": statuses
        }

    # ============================================================
    # 5. 🆕 دوال جديدة لمهام Celery (تم إضافتها)
    # ============================================================

    async def process_pending_orders(self) -> Dict[str, int]:
        """
        معالجة الطلبات المعلقة (غير المدفوعة أو قيد المراجعة).
        - تُرسل تذكيرات للعملاء بالطلبات المعلقة.
        - تُلغي الطلبات التي تجاوزت المهلة الزمنية (48 ساعة).
        - تُستدعى من مهمة Celery.
        """
        # جلب الطلبات المعلقة منذ أكثر من 48 ساعة
        cutoff_time = datetime.utcnow() - timedelta(hours=48)
        pending_orders = await self.repo.get_pending_orders_older_than(cutoff_time)

        reminded = 0
        cancelled = 0

        for order in pending_orders:
            order_id = cast(int, order.id)
            # إرسال تذكير (محاكاة)
            logger.info(f"Reminding customer about pending order {order_id}")
            reminded += 1

            # 🔥 تحويل created_at إلى datetime باستخدام cast
            created_at = cast(datetime, order.created_at)
            # إلغاء الطلبات التي تجاوزت 72 ساعة
            if created_at < datetime.utcnow() - timedelta(hours=72):
                await self.repo.update_order_status(order_id, "CANCELLED")
                # إعادة المخزون
                await self._restore_inventory(order_id)
                cancelled += 1
                logger.info(f"Cancelled order {order_id} due to timeout")

        return {"reminded": reminded, "cancelled": cancelled}

    async def _restore_inventory(self, order_id: int) -> None:
        """
        إعادة المخزون للطلب الملغى.
        """
        order_items = await self.repo.get_order_items(order_id)
        for item in order_items:
            variant_id = cast(int, item.variant_id)
            quantity = cast(int, item.quantity)
            variant = await self.repo.get_variant(variant_id)
            if variant:
                variant.stock_quantity = cast(int, variant.stock_quantity) + quantity  # type: ignore
                await self.db.flush()
        await self.db.commit()

    async def update_inventory(self, product_id: int, quantity_change: int) -> Dict[str, Any]:
        """
        تحديث المخزون بعد عملية شراء أو إرجاع.
        - quantity_change: قيمة موجبة للإضافة (إرجاع)، سالبة للخصم (شراء).
        - تُستدعى من مهمة Celery.
        """
        product = await self.repo.get_product(product_id)
        if not product:
            raise NotFoundError(f"Product {product_id} not found")

        # تحديث المخزون الأساسي (إذا كان المنتج يدعم المخزون المركزي)
        current_stock = cast(int, product.stock_quantity) or 0
        new_stock = current_stock + quantity_change

        if new_stock < 0:
            raise ValidationError(f"Insufficient stock for product {product_id}. Current: {current_stock}, Change: {quantity_change}")

        await self.repo.update_product_stock(product_id, new_stock)

        return {
            "product_id": product_id,
            "old_quantity": current_stock,
            "new_quantity": new_stock,
            "change": quantity_change
        }

    async def generate_daily_sales_report(self, tenant_id: Optional[int] = None) -> Dict[str, Any]:
        """
        إنشاء تقرير المبيعات اليومي.
        - تُستدعى من مهمة Celery في نهاية كل يوم.
        - تتضمن: إجمالي المبيعات، عدد الطلبات، المنتجات الأكثر مبيعاً.
        """
        today = datetime.utcnow().date()
        start_of_day = datetime.combine(today, datetime.min.time())

        # جلب الطلبات المدفوعة لهذا اليوم
        orders = await self.repo.get_paid_orders_since(start_of_day, tenant_id)

        if not orders:
            logger.info(f"No paid orders found for {today}")
            return {
                "date": today.isoformat(),
                "total_orders": 0,
                "total_revenue": 0,
                "top_products": [],
                "message": "No sales data for today"
            }

        total_orders = len(orders)
        total_revenue = sum(cast(Decimal, order.total_amount_mrusdt) for order in orders)

        # حساب المنتجات الأكثر مبيعاً
        product_sales = {}
        for order in orders:
            items = await self.repo.get_order_items(cast(int, order.id))
            for item in items:
                product_id = cast(int, item.product_id)
                quantity = cast(int, item.quantity)
                product_sales[product_id] = product_sales.get(product_id, 0) + quantity

        # جلب أسماء المنتجات
        top_products = []
        for product_id, quantity in sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:5]:
            product = await self.repo.get_product(product_id)
            if product:
                top_products.append({
                    "product_id": product_id,
                    "name": product.title,
                    "quantity_sold": quantity
                })

        report = {
            "date": today.isoformat(),
            "total_orders": total_orders,
            "total_revenue": float(total_revenue),
            "average_order_value": float(total_revenue / total_orders) if total_orders > 0 else 0,
            "top_products": top_products,
        }

        # 🔥 تصحيح استدعاء audit_log (إزالة tenant_id و resource_id)
        await audit_log(
            user_id=0,
            action="DAILY_SALES_REPORT",
            details=report,
        )

        return report

    async def retry_failed_payments(self) -> Dict[str, int]:
        """
        إعادة محاولة المدفوعات الفاشلة (بسبب انقطاع الشبكة أو خطأ مؤقت).
        - تُستدعى من مهمة Celery كل ساعة.
        - تحاول إعادة معالجة الطلبات التي فشل دفعها.
        """
        # جلب طلبات الدفع الفاشلة
        failed_payment_requests = await self.repo.get_failed_payment_requests()

        successful = 0
        failed = 0

        for pr in failed_payment_requests:
            pr_id = cast(int, pr.id)
            order_id = cast(int, pr.order_id)

            # محاولة إعادة الدفع (محاكاة)
            try:
                order = await self.repo.get_order(order_id)
                if not order:
                    continue

                # محاولة استدعاء خدمة الدفع مرة أخرى
                payment_idempotency = f"retry-payment-{pr.id}-{uuid.uuid4().hex[:8]}"
                tx = await self.finance.transfer(
                    sender_id=cast(int, order.customer_id),
                    receiver_email="admin@eppne.com",
                    currency="MR_USDT",
                    amount=cast(Decimal, order.total_amount_mrusdt),
                    idempotency_key=payment_idempotency,
                    notes=f"Retry payment for order {order_id}"
                )

                # تحديث حالة طلب الدفع
                await self.repo.update_payment_request(
                    pr_id,
                    status="PAID",
                    paid_at=func.now(),
                    gateway_response={"retry": True, "tx_hash": tx.tx_hash}
                )
                await self.repo.update_order_status(order_id, "PAID")
                successful += 1
                logger.info(f"✅ Retry payment succeeded for order {order_id}")

            except Exception as e:
                # تحديث عدد المحاولات
                await self.repo.increment_payment_retry_count(pr_id)
                failed += 1
                logger.warning(f"❌ Retry payment failed for order {order_id}: {e}")

        return {"successful": successful, "failed": failed}