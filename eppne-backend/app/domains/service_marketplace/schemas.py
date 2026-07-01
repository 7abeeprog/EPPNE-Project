from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.service_marketplace.models import (
    ServiceType, DeploymentStatus, SubscriptionPlan
)


# ========== Service ==========
class MarketplaceServiceCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    service_type: ServiceType
    thumbnail_url: Optional[str] = None
    demo_url: Optional[str] = None
    documentation_url: Optional[str] = None
    database_schema: Optional[Dict[str, Any]] = None
    api_blueprint: Optional[Dict[str, Any]] = None
    frontend_template_url: Optional[str] = None
    default_config: Dict[str, Any] = {}
    requires_modules: List[str] = []
    min_sovereign_rank: Optional[str] = None
    base_price_mrusdt: Decimal = 0
    subscription_price_basic_mrusdt: Decimal = 0
    subscription_price_pro_mrusdt: Decimal = 0
    subscription_price_enterprise_mrusdt: Decimal = 0
    available_addons: List[int] = []
    is_featured: bool = False


class MarketplaceServiceResponse(MarketplaceServiceCreate):
    id: int
    tenant_id: int
    version: str
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========== Service Version ==========
class ServiceVersionCreate(BaseModel):
    version: str
    changelog: Optional[str] = None
    database_schema: Optional[Dict[str, Any]] = None
    api_blueprint: Optional[Dict[str, Any]] = None
    frontend_template_url: Optional[str] = None


class ServiceVersionResponse(ServiceVersionCreate):
    id: int
    service_id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========== License (Purchase & Deployment) ==========
class ServiceLicensePurchase(BaseModel):
    service_id: int
    subscription_plan: SubscriptionPlan = SubscriptionPlan.BASIC
    purchased_addons: List[int] = []
    custom_config: Dict[str, Any] = {}
    custom_domain: Optional[str] = Field(None, pattern="^[a-z0-9-]+$", description="subdomain or custom domain")
    auto_renew: bool = True


class ServiceLicenseResponse(BaseModel):
    id: int
    service_id: int
    tenant_id: int
    buyer_user_id: int
    deployed_domain: Optional[str]
    deployment_status: DeploymentStatus
    deployment_log: Optional[str]
    subscription_plan: SubscriptionPlan
    purchased_addons: List[int]
    custom_config: Dict[str, Any]
    paid_amount_mrusdt: Decimal
    subscription_start: Optional[datetime]
    subscription_end: Optional[datetime]
    auto_renew: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DeploymentStatusUpdate(BaseModel):
    status: DeploymentStatus
    deployment_log: Optional[str] = None


# ========== Add-ons ==========
class ServiceAddonCreate(BaseModel):
    name: str
    description: Optional[str] = None
    addon_type: str
    compatible_service_types: List[str] = []
    database_schema: Optional[Dict[str, Any]] = None
    api_blueprint: Optional[Dict[str, Any]] = None
    frontend_component_url: Optional[str] = None
    price_mrusdt: Decimal = 0


class ServiceAddonResponse(ServiceAddonCreate):
    id: int
    tenant_id: int
    version: str
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ========== Customization Requests ==========
class CustomizationRequestCreate(BaseModel):
    title: str
    description: str
    proposed_budget_mrusdt: Optional[Decimal] = None


class CustomizationRequestResponse(CustomizationRequestCreate):
    id: int
    license_id: int
    requester_id: int
    status: str
    assigned_developer_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)