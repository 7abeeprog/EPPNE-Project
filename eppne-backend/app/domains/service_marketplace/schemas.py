# app/domains/service_marketplace/schemas.py
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.service_marketplace.models import (
    ServiceType, DeploymentStatus, SubscriptionPlan
)


# ========== Service ==========
class MarketplaceServiceCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255, description="اسم الخدمة")
    description: Optional[str] = Field(default=None, description="وصف الخدمة")
    service_type: ServiceType = Field(description="نوع الخدمة")
    thumbnail_url: Optional[str] = Field(default=None, description="رابط الصورة المصغرة")
    demo_url: Optional[str] = Field(default=None, description="رابط العرض التوضيحي")
    documentation_url: Optional[str] = Field(default=None, description="رابط التوثيق")
    database_schema: Optional[Dict[str, Any]] = Field(default=None, description="مخطط قاعدة البيانات")
    api_blueprint: Optional[Dict[str, Any]] = Field(default=None, description="مخطط الـ API")
    frontend_template_url: Optional[str] = Field(default=None, description="رابط قالب الواجهة")
    default_config: Dict[str, Any] = Field(default={}, description="الإعدادات الافتراضية")
    requires_modules: List[str] = Field(default=[], description="الوحدات المطلوبة")
    min_sovereign_rank: Optional[str] = Field(default=None, description="الرتبة السيادية الدنيا")
    base_price_mrusdt: Decimal = Field(default=Decimal('0.0'), description="السعر الأساسي")
    subscription_price_basic_mrusdt: Decimal = Field(default=Decimal('0.0'), description="سعر الاشتراك الأساسي")
    subscription_price_pro_mrusdt: Decimal = Field(default=Decimal('0.0'), description="سعر الاشتراك الاحترافي")
    subscription_price_enterprise_mrusdt: Decimal = Field(default=Decimal('0.0'), description="سعر الاشتراك المؤسسي")
    available_addons: List[int] = Field(default=[], description="معرفات الإضافات المتاحة")
    is_featured: bool = Field(default=False, description="هل الخدمة مميزة")


class MarketplaceServiceResponse(MarketplaceServiceCreate):
    id: int = Field(description="معرف الخدمة")
    tenant_id: int = Field(description="معرف المستأجر")
    version: str = Field(description="الإصدار الحالي")
    is_active: bool = Field(description="نشطة")
    created_by: int = Field(description="معرف المنشئ")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    updated_at: datetime = Field(description="تاريخ التحديث")
    model_config = ConfigDict(from_attributes=True)


# ========== Service Version ==========
class ServiceVersionCreate(BaseModel):
    version: str = Field(description="رقم الإصدار")
    changelog: Optional[str] = Field(default=None, description="سجل التغييرات")
    database_schema: Optional[Dict[str, Any]] = Field(default=None, description="مخطط قاعدة البيانات")
    api_blueprint: Optional[Dict[str, Any]] = Field(default=None, description="مخطط الـ API")
    frontend_template_url: Optional[str] = Field(default=None, description="رابط قالب الواجهة")


class ServiceVersionResponse(ServiceVersionCreate):
    id: int = Field(description="معرف الإصدار")
    service_id: int = Field(description="معرف الخدمة")
    is_active: bool = Field(description="نشط")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)


# ========== License (Purchase & Deployment) ==========
class ServiceLicensePurchase(BaseModel):
    service_id: int = Field(description="معرف الخدمة")
    subscription_plan: SubscriptionPlan = Field(default=SubscriptionPlan.BASIC, description="خطة الاشتراك")
    purchased_addons: List[int] = Field(default=[], description="معرفات الإضافات المشتراة")
    custom_config: Dict[str, Any] = Field(default={}, description="إعدادات مخصصة")
    custom_domain: Optional[str] = Field(None, pattern="^[a-z0-9-]+$", description="النطاق المخصص أو الفرعي")
    auto_renew: bool = Field(default=True, description="التجديد التلقائي")


class ServiceLicenseResponse(BaseModel):
    id: int = Field(description="معرف الترخيص")
    service_id: int = Field(description="معرف الخدمة")
    tenant_id: int = Field(description="معرف المستأجر")
    buyer_user_id: int = Field(description="معرف المشتري")
    deployed_domain: Optional[str] = Field(default=None, description="النطاق المنشور")
    deployment_status: DeploymentStatus = Field(description="حالة النشر")
    deployment_log: Optional[str] = Field(default=None, description="سجل النشر")
    subscription_plan: SubscriptionPlan = Field(description="خطة الاشتراك")
    purchased_addons: List[int] = Field(default=[], description="معرفات الإضافات المشتراة")
    custom_config: Dict[str, Any] = Field(default={}, description="الإعدادات المخصصة")
    paid_amount_mrusdt: Decimal = Field(description="المبلغ المدفوع")
    subscription_start: Optional[datetime] = Field(default=None, description="تاريخ بدء الاشتراك")
    subscription_end: Optional[datetime] = Field(default=None, description="تاريخ انتهاء الاشتراك")
    auto_renew: bool = Field(description="التجديد التلقائي")
    is_active: bool = Field(description="نشط")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    updated_at: datetime = Field(description="تاريخ التحديث")
    model_config = ConfigDict(from_attributes=True)


class DeploymentStatusUpdate(BaseModel):
    status: DeploymentStatus = Field(description="حالة النشر الجديدة")
    deployment_log: Optional[str] = Field(default=None, description="سجل النشر")


# ========== Add-ons ==========
class ServiceAddonCreate(BaseModel):
    name: str = Field(description="اسم الإضافة")
    description: Optional[str] = Field(default=None, description="وصف الإضافة")
    addon_type: str = Field(description="نوع الإضافة")
    compatible_service_types: List[str] = Field(default=[], description="أنواع الخدمات المتوافقة")
    database_schema: Optional[Dict[str, Any]] = Field(default=None, description="مخطط قاعدة البيانات")
    api_blueprint: Optional[Dict[str, Any]] = Field(default=None, description="مخطط الـ API")
    frontend_component_url: Optional[str] = Field(default=None, description="رابط مكون الواجهة")
    price_mrusdt: Decimal = Field(default=Decimal('0.0'), description="السعر")


class ServiceAddonResponse(ServiceAddonCreate):
    id: int = Field(description="معرف الإضافة")
    tenant_id: int = Field(description="معرف المستأجر")
    version: str = Field(description="الإصدار")
    is_active: bool = Field(description="نشطة")
    created_by: int = Field(description="معرف المنشئ")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    updated_at: datetime = Field(description="تاريخ التحديث")
    model_config = ConfigDict(from_attributes=True)


# ========== Customization Requests ==========
class CustomizationRequestCreate(BaseModel):
    title: str = Field(description="عنوان الطلب")
    description: str = Field(description="وصف الطلب")
    proposed_budget_mrusdt: Optional[Decimal] = Field(default=None, description="الميزانية المقترحة")


class CustomizationRequestResponse(CustomizationRequestCreate):
    id: int = Field(description="معرف الطلب")
    license_id: int = Field(description="معرف الترخيص")
    requester_id: int = Field(description="معرف مقدم الطلب")
    status: str = Field(description="الحالة")
    assigned_developer_id: Optional[int] = Field(default=None, description="معرف المطور المسند")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    updated_at: datetime = Field(description="تاريخ التحديث")
    model_config = ConfigDict(from_attributes=True)