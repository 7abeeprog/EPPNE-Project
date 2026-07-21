# app/domains/commerce/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload, load_only
from typing import Optional, List

# ✅ تم استيراد جميع الـ Schemas المطلوبة للـ Pagination
from app.domains.commerce.schemas import (
    ProductResponse, 
    AddressResponse, 
    OrderResponse, 
    CommissionResponse
)
from app.domains.commerce.models import *
from app.core.errors import NotFoundError
from app.core.pagination import PaginatedResponse

class CommerceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- Store ----------
    async def create_store(self, **kwargs) -> StoreProfile:
        store = StoreProfile(**kwargs)
        self.db.add(store)
        await self.db.commit()
        await self.db.refresh(store)
        return store

    async def get_store_by_tenant(self, tenant_id: int) -> StoreProfile | None:
        result = await self.db.execute(select(StoreProfile).where(StoreProfile.tenant_id == tenant_id))
        return result.scalar_one_or_none()

    async def get_store(self, store_id: int) -> StoreProfile | None:
        result = await self.db.execute(select(StoreProfile).where(StoreProfile.id == store_id))
        return result.scalar_one_or_none()

    # ---------- Categories ----------
    async def create_category(self, **kwargs) -> ProductCategory:
        cat = ProductCategory(**kwargs)
        self.db.add(cat)
        await self.db.commit()
        await self.db.refresh(cat)
        return cat

    # ---------- Products ----------
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
        """✅ جلب المتغير مع قفل (للتحديث الذري)"""
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
        skip: int = 0,
        limit: int = 20,
        only_published: bool = True
    ) -> PaginatedResponse[ProductResponse]:
        """✅ جلب المنتجات مع Pagination وتحويلها إلى Schema"""
        query = select(Product).where(Product.store_id == store_id)
        if only_published:
            query = query.where(Product.is_published == True)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        paginated_query = query.offset(skip).limit(limit)
        result = await self.db.execute(paginated_query)
        items = result.scalars().all()
        
        # تحويل كائنات قاعدة البيانات إلى Pydantic
        schema_items = [ProductResponse.model_validate(item) for item in items]

        return PaginatedResponse(data=schema_items, total=total, skip=skip, limit=limit)

    # ---------- Address ----------
    async def create_address(self, **kwargs) -> Address:
        addr = Address(**kwargs)
        self.db.add(addr)
        await self.db.commit()
        await self.db.refresh(addr)
        return addr

    async def get_user_addresses(self, user_id: int, skip: int = 0, limit: int = 20) -> PaginatedResponse[AddressResponse]:
        """✅ جلب العناوين مع Pagination وتحويلها إلى Schema"""
        query = select(Address).where(Address.user_id == user_id)
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        paginated_query = query.offset(skip).limit(limit)
        result = await self.db.execute(paginated_query)
        items = result.scalars().all()
        
        schema_items = [AddressResponse.model_validate(item) for item in items]
        return PaginatedResponse(data=schema_items, total=total, skip=skip, limit=limit)

    # ---------- Orders (مع Pagination) ----------
    async def get_order_by_idempotency_key(self, idempotency_key: str) -> Order | None:
        result = await self.db.execute(select(Order).where(Order.idempotency_key == idempotency_key))
        return result.scalar_one_or_none()

    async def create_order(self, **kwargs) -> Order:
        order = Order(**kwargs)
        self.db.add(order)
        await self.db.flush()
        return order

    async def create_order_item(self, **kwargs) -> OrderItem:
        item = OrderItem(**kwargs)
        self.db.add(item)
        await self.db.flush()
        return item

    async def get_order(self, order_id: int) -> Order | None:
        result = await self.db.execute(select(Order).where(Order.id == order_id))
        return result.scalar_one_or_none()

    async def update_order_status(self, order_id: int, status: str) -> Order:
        await self.db.execute(update(Order).where(Order.id == order_id).values(status=status))
        await self.db.commit()
        return await self.get_order(order_id)

    async def get_user_orders(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> PaginatedResponse[OrderResponse]:
        """✅ جلب طلبات المستخدم مع Pagination و Schema"""
        query = (
            select(Order)
            .where(Order.customer_id == user_id)
            .options(
                load_only(
                    Order.id,  # type: ignore
                    Order.total_amount_mrusdt,  # type: ignore
                    Order.status,  # type: ignore
                    Order.settlement_type,  # type: ignore
                    Order.created_at,  # type: ignore
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

    # ---------- Affiliate ----------
    async def get_affiliate_tree(self, user_id: int) -> AffiliateTree | None:
        result = await self.db.execute(select(AffiliateTree).where(AffiliateTree.user_id == user_id))
        return result.scalar_one_or_none()

    async def create_affiliate_tree(self, **kwargs) -> AffiliateTree:
        tree = AffiliateTree(**kwargs)
        self.db.add(tree)
        await self.db.commit()
        await self.db.refresh(tree)
        return tree

    async def get_sponsor_chain(self, user_id: int, max_depth: int = 10):
        chain = []
        current = await self.get_affiliate_tree(user_id)
        while current and len(chain) < max_depth:
            chain.append(current.sponsor_id)
            current = await self.get_affiliate_tree(current.sponsor_id)  # type: ignore
        return chain

    # ---------- Commissions ----------
    async def create_commission(self, **kwargs) -> CommissionRecord:
        comm = CommissionRecord(**kwargs)
        self.db.add(comm)
        await self.db.commit()
        await self.db.refresh(comm)
        return comm

    async def get_pending_commissions(self, beneficiary_id: int, skip: int = 0, limit: int = 20) -> PaginatedResponse[CommissionResponse]:
        """✅ جلب العمولات المعلقة مع Schema"""
        query = select(CommissionRecord).where(
            CommissionRecord.beneficiary_id == beneficiary_id,
            CommissionRecord.status == "PENDING"
        )
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        paginated_query = query.offset(skip).limit(limit)
        result = await self.db.execute(paginated_query)
        items = result.scalars().all()
        
        schema_items = [CommissionResponse.model_validate(item) for item in items]
        return PaginatedResponse(data=schema_items, total=total, skip=skip, limit=limit)

    async def release_commission(self, commission_id: int, tx_hash: str) -> CommissionRecord:
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

    # ---------- Affiliate Config ----------
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

    # ---------- Payment Requests (مع Idempotency) ----------
    async def get_payment_request_by_idempotency_key(self, idempotency_key: str) -> PaymentRequest | None:
        result = await self.db.execute(
            select(PaymentRequest).where(PaymentRequest.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def create_payment_request(self, **kwargs) -> PaymentRequest:
        pr = PaymentRequest(**kwargs)
        self.db.add(pr)
        await self.db.commit()
        await self.db.refresh(pr)
        return pr

    async def get_payment_request_by_order(self, order_id: int, payment_method: str) -> PaymentRequest | None:
        result = await self.db.execute(
            select(PaymentRequest).where(
                PaymentRequest.order_id == order_id,
                PaymentRequest.payment_method == payment_method
            ).order_by(PaymentRequest.id.desc())
        )
        return result.scalar_one_or_none()

    async def get_payment_request_by_agent_code(self, agent_code: str) -> PaymentRequest | None:
        result = await self.db.execute(select(PaymentRequest).where(PaymentRequest.agent_code == agent_code))
        return result.scalar_one_or_none()

    async def update_payment_request(self, payment_request_id: int, **kwargs) -> PaymentRequest:
        await self.db.execute(update(PaymentRequest).where(PaymentRequest.id == payment_request_id).values(**kwargs))
        await self.db.commit()
        return await self.get_payment_request(payment_request_id)

    async def get_payment_request(self, pr_id: int) -> PaymentRequest | None:
        result = await self.db.execute(select(PaymentRequest).where(PaymentRequest.id == pr_id))
        return result.scalar_one_or_none()