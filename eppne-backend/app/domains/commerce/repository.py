# app/domains/commerce/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.orm import selectinload, load_only
from typing import Optional, List, Any, cast
from datetime import datetime
import json

from app.domains.commerce.schemas import (
    ProductResponse, 
    AddressResponse, 
    OrderResponse, 
    CommissionResponse
)
from app.domains.commerce.models import *
from app.domains.identity.models import User  # ✅ إضافة الاستيراد المفقود
from app.core.errors import NotFoundError
from app.core.pagination import PaginatedResponse


class CommerceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ========== Store ==========
    async def create_store(self, **kwargs) -> StoreProfile:
        store = StoreProfile(**kwargs)
        self.db.add(store)
        await self.db.commit()
        await self.db.refresh(store)
        return store

    async def get_store_by_tenant(self, tenant_id: int) -> StoreProfile | None:
        result = await self.db.execute(select(StoreProfile).where(StoreProfile.tenant_id == tenant_id))
        return result.scalar_one_or_none()

    async def get_store(self, store_id: int, tenant_id: int) -> StoreProfile | None:
        result = await self.db.execute(
            select(StoreProfile).where(
                and_(StoreProfile.id == store_id, StoreProfile.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()

    # ========== Categories ==========
    async def create_category(self, **kwargs) -> ProductCategory:
        cat = ProductCategory(**kwargs)
        self.db.add(cat)
        await self.db.commit()
        await self.db.refresh(cat)
        return cat

    # ========== Products ==========
    async def create_product(self, **kwargs) -> Product:
        product = Product(**kwargs)
        self.db.add(product)
        await self.db.flush()
        return product

    async def create_variant(self, **kwargs) -> ProductVariant:
        variant = ProductVariant(**kwargs)
        self.db.add(variant)
        await self.db.flush()
        return variant

    async def get_product(self, product_id: int) -> Product | None:
        result = await self.db.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

    async def get_variant(self, variant_id: int) -> ProductVariant | None:
        result = await self.db.execute(select(ProductVariant).where(ProductVariant.id == variant_id))
        return result.scalar_one_or_none()

    async def get_variant_for_update(self, variant_id: int) -> ProductVariant | None:
        result = await self.db.execute(
            select(ProductVariant).where(ProductVariant.id == variant_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def update_product(self, product_id: int, **kwargs) -> Product:
        await self.db.execute(update(Product).where(Product.id == product_id).values(**kwargs))
        await self.db.commit()
        product = await self.get_product(product_id)
        if not product:
            raise NotFoundError("Product not found")
        return product

    async def get_products_by_store(
        self,
        store_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 20,
        only_published: bool = True
    ) -> PaginatedResponse[ProductResponse]:
        store = await self.get_store(store_id, tenant_id)
        if not store:
            raise NotFoundError("المتجر غير موجود أو لا يخص هذا المستأجر")
        
        query = select(Product).where(Product.store_id == store_id)
        if only_published:
            query = query.where(Product.is_published == True)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        paginated_query = query.offset(skip).limit(limit)
        result = await self.db.execute(paginated_query)
        items = result.scalars().all()
        
        schema_items = [ProductResponse.model_validate(item) for item in items]

        return PaginatedResponse(data=schema_items, total=total, skip=skip, limit=limit)

    # ========== Address ==========
    async def create_address(self, **kwargs) -> Address:
        addr = Address(**kwargs)
        self.db.add(addr)
        await self.db.commit()
        await self.db.refresh(addr)
        return addr

    async def get_user_addresses(self, user_id: int, skip: int = 0, limit: int = 20) -> PaginatedResponse[AddressResponse]:
        query = select(Address).where(Address.user_id == user_id)
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        paginated_query = query.offset(skip).limit(limit)
        result = await self.db.execute(paginated_query)
        items = result.scalars().all()
        
        schema_items = [AddressResponse.model_validate(item) for item in items]
        return PaginatedResponse(data=schema_items, total=total, skip=skip, limit=limit)

    # ========== Orders ==========
    async def get_order_by_idempotency_key(self, idempotency_key: str, tenant_id: int) -> Order | None:
        result = await self.db.execute(
            select(Order).where(
                and_(Order.idempotency_key == idempotency_key, Order.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()

    async def create_order(self, tenant_id: int, **kwargs) -> Order:
        order = Order(tenant_id=tenant_id, **kwargs)
        self.db.add(order)
        await self.db.flush()
        return order

    async def create_order_item(self, **kwargs) -> OrderItem:
        item = OrderItem(**kwargs)
        self.db.add(item)
        await self.db.flush()
        return item

    async def get_order(self, order_id: int, tenant_id: int) -> Order | None:
        result = await self.db.execute(
            select(Order).where(and_(Order.id == order_id, Order.tenant_id == tenant_id))
        )
        return result.scalar_one_or_none()

    async def update_order_status(self, order_id: int, tenant_id: int, status: str) -> Order:
        await self.db.execute(
            update(Order)
            .where(and_(Order.id == order_id, Order.tenant_id == tenant_id))
            .values(status=status)
        )
        await self.db.commit()
        return await self.get_order(order_id, tenant_id)

    async def get_user_orders(
        self,
        user_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> PaginatedResponse[OrderResponse]:
        query = (
            select(Order)
            .where(and_(Order.customer_id == user_id, Order.tenant_id == tenant_id))
            .options(
                load_only(
                    "id", "total_amount_mrusdt", "status", "settlement_type", "created_at"
                )
            )
            .order_by(Order.created_at.desc())
        )

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        paginated_query = query.offset(skip).limit(limit)
        result = await self.db.execute(paginated_query)
        items = result.scalars().all()
        
        schema_items = [OrderResponse.model_validate(item) for item in items]
        return PaginatedResponse(data=schema_items, total=total, skip=skip, limit=limit)

    # ========== Affiliate ==========
    async def get_affiliate_tree(self, user_id: int, tenant_id: int) -> AffiliateTree | None:
        result = await self.db.execute(
            select(AffiliateTree)
            .join(User, User.id == AffiliateTree.user_id)
            .where(
                and_(AffiliateTree.user_id == user_id, User.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()

    async def create_affiliate_tree(self, **kwargs) -> AffiliateTree:
        tree = AffiliateTree(**kwargs)
        self.db.add(tree)
        await self.db.commit()
        await self.db.refresh(tree)
        return tree

    async def get_sponsor_chain(self, user_id: int, tenant_id: int, max_depth: int = 10):
        chain = []
        current = await self.get_affiliate_tree(user_id, tenant_id)
        while current and len(chain) < max_depth:
            sponsor_id = cast(int, current.sponsor_id)
            chain.append(sponsor_id)
            current = await self.get_affiliate_tree(sponsor_id, tenant_id)
        return chain

    # ========== Commissions ==========
    async def create_commission(self, **kwargs) -> CommissionRecord:
        comm = CommissionRecord(**kwargs)
        self.db.add(comm)
        await self.db.commit()
        await self.db.refresh(comm)
        return comm

    async def get_pending_commissions(self, beneficiary_id: int, tenant_id: int, skip: int = 0, limit: int = 20) -> PaginatedResponse[CommissionResponse]:
        query = select(CommissionRecord).where(
            CommissionRecord.beneficiary_id == beneficiary_id,
            CommissionRecord.status == "PENDING"
        )
        query = query.join(User, User.id == CommissionRecord.beneficiary_id).where(User.tenant_id == tenant_id)
        
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        paginated_query = query.offset(skip).limit(limit)
        result = await self.db.execute(paginated_query)
        items = result.scalars().all()
        
        schema_items = [CommissionResponse.model_validate(item) for item in items]
        return PaginatedResponse(data=schema_items, total=total, skip=skip, limit=limit)

    async def release_commission(self, commission_id: int, tx_hash: str) -> CommissionRecord:
        # WARNING: هذا الـcommit() بيغطي كمان كتابة finance.transfer() جوه
        # service.release_commissions (اللي فيها flush() بس، بلا commit مستقل خاص بيها) —
        # لا تحوّل الـcommit() ده لـflush() بدون إضافة commit() صريح لـrelease_commissions أولًا.
        await self.db.execute(
            update(CommissionRecord).where(CommissionRecord.id == commission_id).values(
                status="RELEASED", release_date=func.now(), release_tx_hash=tx_hash
            )
        )
        await self.db.commit()
        return await self.get_commission(commission_id)

    async def get_commission(self, commission_id: int) -> CommissionRecord | None:
        result = await self.db.execute(select(CommissionRecord).where(CommissionRecord.id == commission_id))
        return result.scalar_one_or_none()

    # ========== Affiliate Config ==========
    async def get_affiliate_config(self, tenant_id: int) -> AffiliateConfig | None:
        result = await self.db.execute(select(AffiliateConfig).where(AffiliateConfig.tenant_id == tenant_id))
        return result.scalar_one_or_none()

    async def create_or_update_config(self, tenant_id: int, **kwargs) -> AffiliateConfig:
        config = await self.get_affiliate_config(tenant_id)
        if config:
            for key, value in kwargs.items():
                setattr(config, key, value)
        else:
            config = AffiliateConfig(tenant_id=tenant_id, **kwargs)
            self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    # ========== Payment Requests ==========
    async def get_payment_request_by_idempotency_key(self, idempotency_key: str, tenant_id: int) -> PaymentRequest | None:
        result = await self.db.execute(
            select(PaymentRequest).where(
                and_(PaymentRequest.idempotency_key == idempotency_key, PaymentRequest.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()

    async def create_payment_request(self, tenant_id: int, **kwargs) -> PaymentRequest:
        pr = PaymentRequest(tenant_id=tenant_id, **kwargs)
        self.db.add(pr)
        await self.db.commit()
        await self.db.refresh(pr)
        return pr

    async def get_payment_request_by_order(self, order_id: int, payment_method: str, tenant_id: int) -> PaymentRequest | None:
        result = await self.db.execute(
            select(PaymentRequest).where(
                and_(
                    PaymentRequest.order_id == order_id,
                    PaymentRequest.payment_method == payment_method,
                    PaymentRequest.tenant_id == tenant_id
                )
            ).order_by(PaymentRequest.id.desc())
        )
        return result.scalar_one_or_none()

    async def get_payment_request_by_agent_code(self, agent_code: str, tenant_id: int) -> PaymentRequest | None:
        result = await self.db.execute(
            select(PaymentRequest).where(
                and_(PaymentRequest.agent_code == agent_code, PaymentRequest.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()

    async def update_payment_request(self, payment_request_id: int, tenant_id: int, **kwargs) -> PaymentRequest:
        await self.db.execute(
            update(PaymentRequest)
            .where(and_(PaymentRequest.id == payment_request_id, PaymentRequest.tenant_id == tenant_id))
            .values(**kwargs)
        )
        await self.db.commit()
        return await self.get_payment_request(payment_request_id, tenant_id)

    async def get_payment_request(self, pr_id: int, tenant_id: int) -> PaymentRequest | None:
        result = await self.db.execute(
            select(PaymentRequest).where(and_(PaymentRequest.id == pr_id, PaymentRequest.tenant_id == tenant_id))
        )
        return result.scalar_one_or_none()

    # ============================================================
    # 🆕 دوال Celery
    # ============================================================

    async def get_pending_orders_older_than(self, cutoff_time: datetime, tenant_id: int) -> List[Order]:
        result = await self.db.execute(
            select(Order)
            .where(
                Order.status.in_(['PENDING_PAYMENT', 'PENDING']),
                Order.created_at < cutoff_time,
                Order.tenant_id == tenant_id
            )
            .order_by(Order.created_at)
        )
        return list(result.scalars().all())

    async def get_order_items(self, order_id: int) -> List[OrderItem]:
        result = await self.db.execute(select(OrderItem).where(OrderItem.order_id == order_id))
        return list(result.scalars().all())

    async def update_product_stock(self, product_id: int, new_stock: int) -> None:
        await self.db.execute(update(Product).where(Product.id == product_id).values(stock_quantity=new_stock))
        await self.db.commit()

    async def get_paid_orders_since(
        self,
        start_time: datetime,
        tenant_id: Optional[int] = None
    ) -> List[Order]:
        query = select(Order).where(
            Order.status == "PAID",
            Order.created_at >= start_time
        )
        if tenant_id is not None:
            query = query.where(Order.tenant_id == tenant_id)
        query = query.order_by(Order.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_failed_payment_requests(self, tenant_id: int) -> List[PaymentRequest]:
        result = await self.db.execute(
            select(PaymentRequest)
            .where(
                PaymentRequest.status == "FAILED",
                PaymentRequest.tenant_id == tenant_id
            )
            .order_by(PaymentRequest.created_at)
        )
        return list(result.scalars().all())

    async def increment_payment_retry_count(self, payment_request_id: int, tenant_id: int) -> None:
        pr = await self.get_payment_request(payment_request_id, tenant_id)
        if pr:
            # ✅ التأكد من أن gateway_response هو dict
            metadata = cast(dict, pr.gateway_response) or {}
            retry_count = metadata.get('retry_count', 0) + 1
            metadata['retry_count'] = retry_count
            await self.db.execute(
                update(PaymentRequest)
                .where(and_(PaymentRequest.id == payment_request_id, PaymentRequest.tenant_id == tenant_id))
                .values(gateway_response=metadata)
            )
            await self.db.commit()