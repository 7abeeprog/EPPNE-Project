# app/domains/commerce/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, cast

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, require_subscription, get_current_tenant
from app.domains.identity.models import User
from app.domains.academy.models import AcademyTenant

from app.domains.commerce.service import CommerceService
from app.domains.commerce.schemas import *

router = APIRouter(prefix="/commerce", tags=["Sovereign Commerce"])


# ============================================================
# 1. المتجر (Store)
# ============================================================

@router.post("/stores", response_model=StoreResponse, status_code=201)
async def create_store(
    data: StoreCreate,
    current_user: User = Depends(get_current_active_user),
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = CommerceService(db)
    store = await service.get_or_create_store(
        tenant_id=cast(int, tenant.id),
        name=data.name
    )
    return store


# ============================================================
# 2. المنتجات (Products)
# ============================================================

@router.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(
    data: ProductCreate,
    current_user: User = Depends(get_current_active_user),
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = CommerceService(db)
    product = await service.create_product(
        tenant_id=cast(int, tenant.id),
        data=data,
        creator_id=cast(int, current_user.id)
    )
    return product


@router.get("/products", response_model=List[ProductResponse])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    only_published: bool = True,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommerceService(db)
    result = await service.list_products(
        tenant_id=cast(int, tenant.id),
        skip=skip,
        limit=limit,
        only_published=only_published
    )
    return result.data


# ============================================================
# 3. الطلبات (Orders)
# ============================================================

@router.post("/checkout", response_model=OrderResponse, status_code=201)
async def checkout(
    data: CheckoutRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommerceService(db)
    order = await service.checkout(
        customer_id=cast(int, current_user.id),
        checkout_data=data
    )
    return order


@router.get("/orders/me", response_model=List[OrderResponse])
async def get_my_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommerceService(db)
    result = await service.get_user_orders(
        user_id=cast(int, current_user.id),
        skip=skip,
        limit=limit
    )
    return result.data


# ============================================================
# 4. الإحالات (Affiliate)
# ============================================================

@router.post("/affiliate/link", response_model=AffiliateTreeResponse)
async def set_affiliate_sponsor(
    sponsor_code: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommerceService(db)
    tree = await service.register_affiliate(
        user_id=cast(int, current_user.id),
        sponsor_code=sponsor_code
    )
    return tree


@router.get("/affiliate/commissions", response_model=List[CommissionResponse])
async def get_my_commissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommerceService(db)
    result = await service.get_user_commissions(
        user_id=cast(int, current_user.id),
        skip=skip,
        limit=limit
    )
    return result.data


@router.post("/affiliate/commissions/release")
async def release_my_commissions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommerceService(db)
    await service.release_commissions(beneficiary_id=cast(int, current_user.id))
    return {"message": "تم تحرير العمولات المعلقة بنجاح"}


# ============================================================
# 5. طرق الدفع (Payment Methods)
# ============================================================

@router.post("/payment-request", response_model=PaymentRequestResponse)
async def create_payment_request(
    data: PaymentRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommerceService(db)
    pr = await service.create_payment_request(
        order_id=data.order_id,
        payment_method=data.payment_method,
        user_id=cast(int, current_user.id),
        idempotency_key=data.idempotency_key
    )
    return pr


@router.post("/payment/agent/confirm", response_model=OrderResponse)
async def confirm_agent_payment(
    data: AgentConfirmPayment,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommerceService(db)
    order = await service.confirm_agent_payment(
        agent_code=data.agent_code,
        agent_user_id=cast(int, current_user.id),
        idempotency_key=data.idempotency_key
    )
    return order


@router.post("/payment/visa/webhook")
async def visa_webhook(
    payload: dict,
    signature: str = Header(...),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db)
):
    """Webhook من بوابة الفيزا (Stripe/Paymob) – يجب حمايته بتوقيع"""
    service = CommerceService(db)
    try:
        order = await service.handle_visa_webhook(payload, signature, idempotency_key)
        return {"status": "success", "order_id": order.id}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/payment/status/{order_id}")
async def get_payment_status(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommerceService(db)
    status_data = await service.get_payment_status(
        order_id=order_id,
        user_id=cast(int, current_user.id)
    )
    return status_data