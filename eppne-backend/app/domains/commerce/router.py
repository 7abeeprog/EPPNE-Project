# app/domains/commerce/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, require_subscription
from app.domains.identity.models import User

from app.domains.commerce.service import CommerceService
from app.domains.commerce.repository import CommerceRepository
from app.domains.commerce.schemas import *

router = APIRouter(prefix="/commerce", tags=["Sovereign Commerce"])

# ---------- Store ----------
@router.post(
    "/stores",
    response_model=StoreResponse,
    status_code=201,
    dependencies=[Depends(require_subscription("commerce"))],
)
async def create_store(
    data: StoreCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = CommerceService(db)
    return await service.create_store(data, current_user.id)

# ---------- Products ----------
@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=201,
    dependencies=[Depends(require_subscription("commerce"))],
)
async def create_product(
    data: ProductCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = CommerceService(db)
    return await service.create_product(data, current_user.id)

@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    store_id: int,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    repo = CommerceRepository(db)
    products = await repo.get_products_by_store(store_id, skip, limit)
    return products

# ---------- Checkout ----------
@router.post(
    "/checkout",
    response_model=OrderResponse,
    status_code=201,
    dependencies=[Depends(require_subscription("commerce"))],
)
async def checkout(
    data: CheckoutRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = CommerceService(db)
    return await service.checkout(data, current_user.id)

@router.get("/orders/me", response_model=list[OrderResponse])
async def get_my_orders(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = CommerceRepository(db)
    orders = await repo.get_user_orders(current_user.id)
    return orders

# ---------- Affiliate ----------
@router.post("/affiliate/link", response_model=AffiliateTreeResponse)
async def set_affiliate_sponsor(
    sponsor_code: str,  # يمكن أن يكون user_id أو كود فريد
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommerceService(db)
    tree = await service.register_affiliate(current_user.id, sponsor_code)
    return tree

@router.get("/affiliate/commissions", response_model=list[CommissionResponse])
async def get_my_commissions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = CommerceRepository(db)
    commissions = await repo.get_pending_commissions(current_user.id)
    return commissions

@router.post("/affiliate/commissions/release")
async def release_my_commissions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommerceService(db)
    await service.release_commissions(current_user.id)
    return {"message": "تم تحرير العمولات المعلقة بنجاح"}

# ========== طرق الدفع الإضافية ==========
@router.post("/payment-request", response_model=PaymentRequestResponse)
async def create_payment_request(
    data: PaymentRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommerceService(db)
    # التحقق من أن المستخدم هو صاحب الطلب
    order = await service.repo.get_order(data.order_id)
    if not order or order.customer_id != current_user.id:
        raise HTTPException(403, "ليس لديك صلاحية لهذا الطلب")
    pr = await service.create_payment_request(data.order_id, data.payment_method)
    return pr

@router.post("/payment/agent/confirm", response_model=OrderResponse)
async def confirm_agent_payment(
    data: AgentConfirmPayment,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommerceService(db)
    order = await service.confirm_agent_payment(data.agent_code, current_user.id)
    return order

@router.post("/payment/visa/webhook")
async def visa_webhook(
    payload: dict,
    signature: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """Webhook من بوابة الفيزا (Stripe/Paymob) – يجب حمايته بتوقيع"""
    service = CommerceService(db)
    try:
        order = await service.handle_visa_webhook(payload, signature)
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
    # التحقق من أن المستخدم هو صاحب الطلب أو أدمن
    order = await service.repo.get_order(order_id)
    if not order or (order.customer_id != current_user.id and current_user.system_role not in ["ADMIN", "EXECUTIVE_DIRECTOR"]):
        raise HTTPException(403, "غير مصرح")
    return await service.get_payment_status(order_id)