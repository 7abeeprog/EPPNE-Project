from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

# ========== Store ==========
# ========== Store ==========
class StoreCreate(BaseModel):
    name: str
    currency: str = "MR_USDT"
    tax_rate: Decimal = 0
    settlement_type: str = "WEB2_FIAT"
    owner_email: Optional[str] = None      # <-- تمت الإضافة هنا
    is_affiliate_enabled: bool = True      # <-- تمت الإضافة هنا

class StoreResponse(StoreCreate):
    id: int
    tenant_id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
# ========== Category ==========
class CategoryCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None
    description: Optional[str] = None

class CategoryResponse(CategoryCreate):
    id: int
    store_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Product & Variant ==========
class ProductVariantCreate(BaseModel):
    sku: str
    attributes: Dict[str, Any] = {}
    price_mrusdt: Decimal
    discount_price: Optional[Decimal] = None
    discount_end_date: Optional[datetime] = None
    stock_quantity: int = 0
    is_wholesale_enabled: bool = False
    wholesale_min_qty: Optional[int] = None
    wholesale_price_mrusdt: Optional[Decimal] = None

class ProductVariantResponse(ProductVariantCreate):
    id: int
    product_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ProductCreate(BaseModel):
    title: str
    description: Optional[str] = None
    product_type: str = "PHYSICAL"
    category_id: Optional[int] = None
    base_price_mrusdt: Decimal
    seo_metadata: Dict[str, Any] = {}
    media_gallery: List[str] = []
    is_affiliate_eligible: bool = True
    affiliate_model: str = "FLAT_RATE"
    affiliate_reward_percentage: Decimal = 0
    max_affiliate_tiers: int = 1
    custom_affiliate_tiers: Optional[Dict[str, float]] = None
    variants: List[ProductVariantCreate] = []

class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    base_price_mrusdt: Optional[Decimal] = None
    is_published: Optional[bool] = None
    is_active: Optional[bool] = None

class ProductResponse(BaseModel):
    id: int
    store_id: int
    title: str
    description: Optional[str]
    product_type: str
    base_price_mrusdt: Decimal
    is_published: bool
    is_active: bool
    is_affiliate_eligible: bool
    variants: List[ProductVariantResponse] = []
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Address ==========
class AddressCreate(BaseModel):
    country: str
    city: str
    state: Optional[str] = None
    postal_code: Optional[str] = None
    street_line1: str
    street_line2: Optional[str] = None
    is_default: bool = False

class AddressResponse(AddressCreate):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Order ==========
class CartItem(BaseModel):
    variant_id: int
    quantity: int = Field(..., gt=0)

class CheckoutRequest(BaseModel):
    store_id: int
    items: List[CartItem]
    shipping_address_id: Optional[int] = None
    settlement_type: str = "WALLET_DEDUCTION"
    affiliate_code: Optional[str] = None

class OrderResponse(BaseModel):
    id: int
    store_id: int
    customer_id: int
    total_amount_mrusdt: Decimal
    discount_applied: Decimal
    tax_amount: Decimal
    shipping_fee: Decimal
    status: str
    settlement_type: str
    created_at: datetime
    items: List[Dict[str, Any]] = []
    model_config = ConfigDict(from_attributes=True)

# ========== Affiliate ==========
class AffiliateConfigResponse(BaseModel):
    id: int
    tenant_id: int
    is_active: bool
    levels: Dict[str, float]  # {"1": 10.0, "2": 5.0, ...}
    system_fee_pct: float
    model_config = ConfigDict(from_attributes=True)

class AffiliateTreeResponse(BaseModel):
    user_id: int
    sponsor_id: int
    network_depth: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CommissionResponse(BaseModel):
    id: int
    beneficiary_id: int
    order_id: int
    level_earned: int
    amount: float
    currency: str
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
    # ========== طرق الدفع ==========
class PaymentRequestCreate(BaseModel):
    order_id: int
    payment_method: str  # AGENT, VISA, CASH_ON_DELIVERY

class PaymentRequestResponse(BaseModel):
    id: int
    order_id: int
    payment_method: str
    amount: float
    currency: str
    agent_code: Optional[str] = None
    agent_confirmed_at: Optional[datetime] = None
    gateway_transaction_id: Optional[str] = None
    status: str
    paid_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AgentConfirmPayment(BaseModel):
    agent_code: str

class VisaWebhookPayload(BaseModel):
    transaction_id: str
    order_id: int
    amount: float
    currency: str
    status: str  # SUCCESS, FAILED
    gateway_reference: str
    signature: str  # لتأكيد صحة الـ webhook