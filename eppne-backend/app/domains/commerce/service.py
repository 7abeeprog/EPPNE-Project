# app/domains/commerce/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func
from decimal import Decimal
import uuid
import random
import json

from app.domains.commerce.repository import CommerceRepository
from app.domains.commerce.models import StoreProfile, Product, Order, PaymentRequest, CommerceAuditLog
from app.domains.commerce.schemas import ProductCreate, CheckoutRequest
from app.domains.finance.service import FinanceService
from app.core.errors import InsufficientBalanceError, NotFoundError, PermissionDeniedError, ValidationError
from app.core.logging_conf import logger

class CommerceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CommerceRepository(db)
        self.finance = FinanceService(db)

    # ==========================================
    # 1. Store Management
    # ==========================================
    async def get_or_create_store(self, tenant_id: int, name: str = None) -> StoreProfile:
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

    # ==========================================
    # 2. Product Management
    # ==========================================
    async def create_product(self, store_id: int, data: ProductCreate, creator_id: int) -> Product:
        product_data = data.model_dump(exclude={"variants"})
        product = await self.repo.create_product(**product_data, store_id=store_id)

        for var_data in data.variants:
            await self.repo.create_variant(product_id=product.id, **var_data.model_dump())

        await self.db.commit()

        await self._create_audit_log(
            user_id=creator_id,
            action="PRODUCT_CREATED",
            details={"product_id": product.id, "title": product.title}
        )

        return product

    # ==========================================
    # 3. Checkout (مع Idempotency وحماية المخزون)
    # ==========================================
    async def checkout(self, customer_id: int, checkout_data: CheckoutRequest, ip: str = None, ua: str = None):
        if not checkout_data.idempotency_key:
            raise ValidationError("Idempotency key is required")

        existing_order = await self.repo.get_order_by_idempotency_key(checkout_data.idempotency_key)
        if existing_order:
            logger.info(f"Duplicate checkout blocked: {checkout_data.idempotency_key}")
            return existing_order

        store = await self.repo.get_store(checkout_data.store_id)
        if not store or not store.is_active:
            raise NotFoundError("المتجر غير موجود أو غير نشط")

        if store.tenant_id != checkout_data.tenant_id:
            raise PermissionDeniedError("لا يمكن الشراء من متجر خارج نطاق المستأجر")

        total = Decimal(0)
        items_data = []
        order_items = []

        for cart_item in checkout_data.items:
            variant = await self.repo.get_variant_for_update(cart_item.variant_id)
            if not variant:
                raise NotFoundError(f"المتغير {cart_item.variant_id} غير موجود")

            product = await self.repo.get_product(variant.product_id)
            if not product or not product.is_published:
                raise NotFoundError(f"المنتج {variant.product_id} غير منشور")

            if variant.stock_quantity < cart_item.quantity:
                raise ValidationError(
                    f"الكمية المطلوبة من {variant.sku} غير متوفرة. المتاح: {variant.stock_quantity}"
                )

            variant.stock_quantity -= cart_item.quantity
            await self.db.flush()

            unit_price = variant.price_mrusdt
            if variant.is_wholesale_enabled and variant.wholesale_min_qty and cart_item.quantity >= variant.wholesale_min_qty:
                unit_price = variant.wholesale_price_mrusdt or unit_price

            line_total = unit_price * cart_item.quantity
            total += line_total

            order_items.append({
                "product_id": product.id,
                "variant_id": variant.id,
                "quantity": cart_item.quantity,
                "unit_price_mrusdt": unit_price,
                "total_price_mrusdt": line_total
            })

        payment_tx_hash = None
        if checkout_data.settlement_type == "WALLET_DEDUCTION":
            tx = await self.finance.transfer(
                sender_id=customer_id,
                receiver_email=store.owner_email,
                currency="MR_USDT",
                amount=total,
                idempotency_key=checkout_data.idempotency_key,
                notes=f"Order checkout for store {store.id}"
            )
            payment_tx_hash = tx.tx_hash

        order = await self.repo.create_order(
            store_id=store.id,
            customer_id=customer_id,
            idempotency_key=checkout_data.idempotency_key,
            total_amount_mrusdt=total,
            discount_applied=0,
            tax_amount=0,
            shipping_fee=0,
            shipping_address_id=checkout_data.shipping_address_id,
            status="PAID" if payment_tx_hash else "PENDING_PAYMENT",
            settlement_type=checkout_data.settlement_type,
            affiliate_code_used=checkout_data.affiliate_code
        )

        for item in order_items:
            await self.repo.create_order_item(order_id=order.id, **item)

        await self.db.commit()

        await self._create_audit_log(
            user_id=customer_id,
            order_id=order.id,
            action="CHECKOUT",
            details={
                "store_id": store.id,
                "total": float(total),
                "settlement_type": checkout_data.settlement_type,
                "idempotency_key": checkout_data.idempotency_key
            },
            ip=ip,
            ua=ua
        )

        if checkout_data.affiliate_code and store.is_affiliate_enabled:
            from app.tasks.commerce import distribute_commissions_task
            distribute_commissions_task.delay(
                order_id=order.id,
                affiliate_code=checkout_data.affiliate_code,
                order_total=float(total)
            )

        return order

    # ==========================================
    # 4. Affiliate Commissions
    # ==========================================
    async def distribute_commissions(self, order_id: int, affiliate_code: str, order_total: Decimal):
        sponsor_id = int(affiliate_code) if affiliate_code.isdigit() else None
        if not sponsor_id:
            return

        chain = await self.repo.get_sponsor_chain(sponsor_id, max_depth=10)
        if not chain:
            return

        config = await self.repo.get_affiliate_config(1)
        if not config or not config.is_active:
            return

        for level, beneficiary_id in enumerate(chain, start=1):
            if level > 10:
                break

            pct = getattr(config, f"level_{level}_pct", 0)
            if pct <= 0:
                continue

            amount = order_total * Decimal(pct) / Decimal(100)
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

    async def register_affiliate(self, user_id: int, sponsor_code: str):
        sponsor_id = int(sponsor_code) if sponsor_code.isdigit() else None
        if not sponsor_id or sponsor_id == user_id:
            raise PermissionDeniedError("كود الداعي غير صالح")

        sponsor_tree = await self.repo.get_affiliate_tree(sponsor_id)
        depth = sponsor_tree.network_depth + 1 if sponsor_tree else 1

        return await self.repo.create_affiliate_tree(
            user_id=user_id,
            sponsor_id=sponsor_id,
            network_depth=depth
        )

    async def release_commissions(self, beneficiary_id: int):
        commissions = await self.repo.get_pending_commissions(beneficiary_id)
        for comm in commissions:
            await self.finance.transfer(
                sender_id=1,  # حساب النظام
                receiver_email=await self._get_user_email(beneficiary_id),
                currency=comm.currency,
                amount=comm.amount,
                notes=f"Commission release for order {comm.order_id}"
            )
            await self.repo.release_commission(comm.id, f"REL-{uuid.uuid4().hex[:12].upper()}")

    # ==========================================
    # 5. Payment Requests 
    # ==========================================
    async def create_payment_request(self, order_id: int, payment_method: str, idempotency_key: str = None) -> PaymentRequest:
        if idempotency_key:
            existing = await self.repo.get_payment_request_by_idempotency_key(idempotency_key)
            if existing:
                return existing

        order = await self.repo.get_order(order_id)
        if not order:
            raise NotFoundError("الطلب غير موجود")

        if order.status != "PENDING_PAYMENT":
            raise PermissionDeniedError("لا يمكن طلب دفع لطلب غير معلق")

        existing = await self.repo.get_payment_request_by_order(order_id, payment_method)
        if existing and existing.status == "PENDING":
            raise PermissionDeniedError(f"يوجد طلب دفع معلق بالفعل عبر {payment_method}")

        pr_data = {
            "order_id": order_id,
            "payment_method": payment_method,
            "amount": order.total_amount_mrusdt,
            "currency": "MR_USDT",
            "status": "PENDING",
            "idempotency_key": idempotency_key or f"PR-{uuid.uuid4().hex[:12].upper()}"
        }

        if payment_method == "AGENT":
            pr_data["agent_code"] = f"AG-{random.randint(100000, 999999)}"
        elif payment_method == "VISA":
            pr_data["gateway_transaction_id"] = f"VISA-{uuid.uuid4().hex[:12].upper()}"

        payment_request = await self.repo.create_payment_request(**pr_data)

        if payment_method == "CASH_ON_DELIVERY":
            await self.confirm_cash_on_delivery(payment_request.id)

        return payment_request

    async def confirm_agent_payment(self, agent_code: str, agent_user_id: int, idempotency_key: str = None) -> Order:
        if idempotency_key:
            existing_audit = await self.repo.get_audit_log_by_details("idempotency_key", idempotency_key)
            if existing_audit:
                return await self.repo.get_order(existing_audit.order_id) 

        pr = await self.repo.get_payment_request_by_agent_code(agent_code)
        if not pr or pr.payment_method != "AGENT" or pr.status != "PENDING":
            raise NotFoundError("طلب الدفع غير موجود أو تم إنجازه مسبقاً")
            
        await self.repo.update_payment_request(
            pr.id, 
            status="PAID", 
            agent_id=agent_user_id,
            agent_confirmed_at=func.now(), 
            paid_at=func.now()
        )

        order = await self.repo.update_order_status(pr.order_id, "PAID")

        await self._create_audit_log(
            user_id=agent_user_id,
            order_id=pr.order_id,
            action="AGENT_PAYMENT_CONFIRMED",
            details={"payment_request_id": pr.id, "idempotency_key": idempotency_key}
        )
        return order

    async def confirm_cash_on_delivery(self, payment_request_id: int):
        pr = await self.repo.get_payment_request(payment_request_id)
        if not pr or pr.payment_method != "CASH_ON_DELIVERY":
            return
            
        await self.repo.update_payment_request(pr.id, status="PAID", paid_at=func.now())
        await self.repo.update_order_status(pr.order_id, "PAID")

    async def handle_visa_webhook(self, payload: dict, signature: str = None, idempotency_key: str = None) -> Order:
        if idempotency_key:
            existing_audit = await self.repo.get_audit_log_by_details("idempotency_key", idempotency_key)
            if existing_audit:
                return await self.repo.get_order(existing_audit.order_id)

        transaction_id = payload.get("transaction_id")
        order_id = payload.get("order_id")
        status = payload.get("status")

        pr = await self.repo.get_payment_request_by_order(order_id, "VISA")
        if not pr:
            raise NotFoundError("لا يوجد طلب دفع فيزا لهذا الطلب")

        if status == "SUCCESS":
            await self.repo.update_payment_request(pr.id, status="PAID", paid_at=func.now(), gateway_response=payload)
            order = await self.repo.update_order_status(order_id, "PAID")
        else:
            await self.repo.update_payment_request(pr.id, status="FAILED", gateway_response=payload)
            raise PermissionDeniedError("فشلت عملية الدفع عبر الفيزا")

        await self._create_audit_log(
            user_id=0,
            order_id=order_id,
            action="VISA_WEBHOOK_PROCESSED",
            details={"status": status, "idempotency_key": idempotency_key}
        )
        return order

    async def get_payment_status(self, order_id: int) -> dict:
        order = await self.repo.get_order(order_id)
        if not order:
            raise NotFoundError("الطلب غير موجود")
            
        payment_methods = ["AGENT", "VISA", "CASH_ON_DELIVERY"]
        statuses = {}
        for method in payment_methods:
            pr = await self.repo.get_payment_request_by_order(order_id, method)
            if pr:
                statuses[method] = pr.status
                
        return {
            "order_id": order_id,
            "order_status": order.status,
            "payment_requests": statuses
        }

    # ==========================================
    # 6. Audit & Utilities
    # ==========================================
    async def _create_audit_log(self, user_id: int, action: str, details: dict, order_id: int = None, ip: str = None, ua: str = None):
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

    async def _get_user_email(self, user_id: int) -> str:
        return f"user_{user_id}@eppne.com"