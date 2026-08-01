# app/domains/saas/schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


# ==========================================
# 1. الخدمات (Services)
# ==========================================

class ServiceCatalogBase(BaseModel):
    name: str = Field(description="اسم الخدمة")
    code: str = Field(description="الكود الفريد للخدمة")
    description: Optional[str] = Field(default=None, description="وصف الخدمة")
    icon: Optional[str] = Field(default=None, description="أيقونة الخدمة")


class ServiceCatalogCreate(ServiceCatalogBase):
    pass


class ServiceCatalogResponse(ServiceCatalogBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 2. خطط التسعير (Plans)
# ==========================================

class ServicePlanBase(BaseModel):
    service_id: int = Field(description="معرف الخدمة")
    name: str = Field(description="اسم الخطة")
    code: str = Field(description="كود الخطة")
    price_monthly: Decimal = Field(description="السعر الشهري")
    price_yearly: Decimal = Field(description="السعر السنوي")
    currency: str = Field(default="MR_USDT", description="العملة")
    features: List[str] = Field(default=[], description="قائمة الميزات")
    max_users: int = Field(default=10, description="الحد الأقصى للمستخدمين")
    max_products: int = Field(default=50, description="الحد الأقصى للمنتجات")
    max_courses: int = Field(default=20, description="الحد الأقصى للكورسات")


class ServicePlanCreate(ServicePlanBase):
    pass


class ServicePlanResponse(ServicePlanBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 3. اشتراكات المستأجر (Subscriptions)
# ==========================================

class TenantSubscriptionBase(BaseModel):
    tenant_id: int = Field(description="معرف المستأجر")
    plan_id: int = Field(description="معرف الخطة")
    status: str = Field(default="ACTIVE", description="حالة الاشتراك")
    auto_renew: bool = Field(default=True, description="التجديد التلقائي")
    payment_method: str = Field(default="WALLET", description="طريقة الدفع")


class TenantSubscriptionCreate(TenantSubscriptionBase):
    trial_end_date: Optional[datetime] = None


class TenantSubscriptionResponse(TenantSubscriptionBase):
    id: int
    idempotency_key: Optional[str]
    grace_period_end_date: Optional[datetime]
    trial_end_date: Optional[datetime]
    start_date: datetime
    end_date: Optional[datetime]
    next_billing_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    plan: Optional[ServicePlanResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 4. صلاحيات الوصول (Service Access)
# ==========================================

class TenantServiceAccessBase(BaseModel):
    tenant_id: int
    service_id: int
    access_level: str = Field(default="BASIC")
    user_limit: Optional[int] = None
    storage_limit: Optional[int] = None
    api_calls_limit: Optional[int] = None


class TenantServiceAccessResponse(TenantServiceAccessBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 5. الفواتير (Invoices)
# ==========================================

class InvoiceItem(BaseModel):
    service: str = Field(description="اسم الخدمة")
    period: str = Field(description="فترة الفوترة")
    amount: float = Field(description="المبلغ")
    currency: str = Field(default="MR_USDT")


class InvoiceBase(BaseModel):
    tenant_id: int
    subscription_id: int
    invoice_number: str = Field(description="رقم الفاتورة")
    amount: Decimal = Field(description="المبلغ الإجمالي")
    currency: str = Field(default="MR_USDT")
    description: Optional[str] = None
    items: List[Dict[str, Any]] = Field(default=[], description="تفاصيل الخدمات المشحونة")
    status: str = Field(default="PENDING", description="حالة الفاتورة")
    due_date: Optional[datetime] = None


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceResponse(InvoiceBase):
    id: int
    paid_at: Optional[datetime]
    paid_tx_hash: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 6. رايات الميزات (Feature Flags)
# ==========================================

class FeatureFlagBase(BaseModel):
    tenant_id: int
    service_id: int
    feature_key: str = Field(description="مفتاح الميزة")
    is_enabled: bool = Field(default=False)


class FeatureFlagResponse(FeatureFlagBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 7. استجابات الوصول (Access Responses)
# ==========================================

class ServiceAccessStatus(BaseModel):
    service_id: int
    service_code: str
    service_name: str
    accessible: bool
    access_level: str
    subscription_status: str
    plan_name: Optional[str] = None
    trial_end_date: Optional[datetime] = None


class CheckAccessResponse(BaseModel):
    service_code: str
    accessible: bool
    reason: Optional[str] = None


# ==========================================
# 8. الاستعلامات (Queries)
# ==========================================

class SubscriptionQuery(BaseModel):
    tenant_id: Optional[int] = None
    service_code: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


class InvoiceQuery(BaseModel):
    tenant_id: Optional[int] = None
    status: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None