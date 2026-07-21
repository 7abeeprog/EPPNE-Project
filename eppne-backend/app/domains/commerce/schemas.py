# app/domains/commerce/schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


# ========== Store ==========
class StoreCreate(BaseModel):
    name: str = Field(description="اسم المتجر")
    currency: str = Field(default="MR_USDT", description="العملة الأساسية")
    tax_rate: Decimal = Field(default=Decimal("0.0"), description="نسبة الضريبة")
    settlement_type: str = Field(default="WEB2_FIAT", description="نوع التسوية")
    owner_email: Optional[str] = Field(default=None, description="البريد الإلكتروني للمالك")
    is_affiliate_enabled: bool = Field(default=True, description="تفعيل نظام الإحالة")


class StoreResponse(StoreCreate):
    id: int
    tenant_id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========== Category ==========
class CategoryCreate(BaseModel):
    name: str = Field(description="اسم التصنيف")
    parent_id: Optional[int] = Field(default=None, description="معرف التصنيف الأب")
    description: Optional[str] = Field(default=None, description="وصف التصنيف")


class CategoryResponse(CategoryCreate):
    id: int
    store_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========== Product & Variant ==========
class ProductVariantCreate(BaseModel):
    sku: str = Field(description="رمز المخزون")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="خصائص المتغير")
    price_mrusdt: Decimal = Field(description="السعر")
    discount_price: Optional[Decimal] = Field(default=None, description="سعر الخصم")
    discount_end_date: Optional[datetime] = Field(default=None, description="تاريخ انتهاء الخصم")
    stock_quantity: int = Field(default=0, description="الكمية المتاحة")
    is_wholesale_enabled: bool = Field(default=False, description="تفعيل السعر بالجملة")
    wholesale_min_qty: Optional[int] = Field(default=None, description="الحد الأدنى للجملة")
    wholesale_price_mrusdt: Optional[Decimal] = Field(default=None, description="سعر الجملة")


class ProductVariantResponse(ProductVariantCreate):
    id: int
    product_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    title: str = Field(description="عنوان المنتج")
    description: Optional[str] = Field(default=None, description="وصف المنتج")
    product_type: str = Field(default="PHYSICAL", description="نوع المنتج")
    category_id: Optional[int] = Field(default=None, description="معرف التصنيف")
    base_price_mrusdt: Decimal = Field(description="السعر الأساسي")
    seo_metadata: Dict[str, Any] = Field(default_factory=dict, description="بيانات SEO")
    media_gallery: List[str] = Field(default_factory=list, description="معرض الصور")
    is_affiliate_eligible: bool = Field(default=True, description="صلاحية الإحالة")
    affiliate_model: str = Field(default="FLAT_RATE", description="نموذج الإحالة")
    affiliate_reward_percentage: Decimal = Field(default=Decimal("0.0"), description="نسبة مكافأة الإحالة")
    max_affiliate_tiers: int = Field(default=1, description="أقصى مستويات الإحالة")
    custom_affiliate_tiers: Optional[Dict[str, float]] = Field(default=None, description="مستويات مخصصة")
    variants: List[ProductVariantCreate] = Field(default_factory=list, description="المتغيرات")


class ProductUpdate(BaseModel):
    title: Optional[str] = Field(default=None, description="عنوان المنتج")
    description: Optional[str] = Field(default=None, description="وصف المنتج")
    base_price_mrusdt: Optional[Decimal] = Field(default=None, description="السعر الأساسي")
    is_published: Optional[bool] = Field(default=None, description="هل منشور؟")
    is_active: Optional[bool] = Field(default=None, description="هل نشط؟")


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
    variants: List[ProductVariantResponse] = Field(default_factory=list)
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========== Address ==========
class AddressCreate(BaseModel):
    country: str = Field(description="الدولة")
    city: str = Field(description="المدينة")
    state: Optional[str] = Field(default=None, description="الولاية")
    postal_code: Optional[str] = Field(default=None, description="الرمز البريدي")
    street_line1: str = Field(description="الشارع الأول")
    street_line2: Optional[str] = Field(default=None, description="الشارع الثاني")
    is_default: bool = Field(default=False, description="هل هو العنوان الافتراضي؟")


class AddressResponse(AddressCreate):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========== Order ==========
class CartItem(BaseModel):
    variant_id: int = Field(description="معرف المتغير")
    quantity: int = Field(..., gt=0, description="الكمية")


class CheckoutRequest(BaseModel):
    store_id: int = Field(description="معرف المتجر")
    items: List[CartItem] = Field(description="عناصر السلة")
    shipping_address_id: Optional[int] = Field(default=None, description="معرف عنوان الشحن")
    settlement_type: str = Field(default="WALLET_DEDUCTION", description="نوع التسوية")
    affiliate_code: Optional[str] = Field(default=None, description="كود الإحالة")
    idempotency_key: Optional[str] = Field(default=None, description="مفتاح عدم التكرار")


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
    items: List[Dict[str, Any]] = Field(default_factory=list)
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
    order_id: int = Field(description="معرف الطلب")
    payment_method: str = Field(description="طريقة الدفع (AGENT, VISA, CASH_ON_DELIVERY)")
    idempotency_key: Optional[str] = Field(default=None, description="مفتاح عدم التكرار")


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
    agent_code: str = Field(description="رمز الوكيل")
    idempotency_key: Optional[str] = Field(default=None, description="مفتاح عدم التكرار")


class VisaWebhookPayload(BaseModel):
    transaction_id: str
    order_id: int
    amount: float
    currency: str
    status: str  # SUCCESS, FAILED
    gateway_reference: str
    signature: str  # لتأكيد صحة الـ webhook
    idempotency_key: Optional[str] = Field(default=None, description="مفتاح عدم التكرار")