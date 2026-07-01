# app/domains/realestate/models.py (الإصدار النهائي المتكامل)
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, JSON, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum

# ========== الأنواع المساعدة ==========
class ZoningCategory(str, enum.Enum):
    RESIDENTIAL = "RESIDENTIAL"
    COMMERCIAL = "COMMERCIAL"
    INDUSTRIAL = "INDUSTRIAL"
    AGRICULTURAL = "AGRICULTURAL"
    LOGISTICS = "LOGISTICS"
    ENTERTAINMENT = "ENTERTAINMENT"
    ADMINISTRATIVE = "ADMINISTRATIVE"

class LegalStatus(str, enum.Enum):
    REGISTERED = "REGISTERED"
    GOVERNMENT_ALLOCATION = "GOVERNMENT_ALLOCATION"
    UNDER_LEGALIZATION = "UNDER_LEGALIZATION"
    USUFRUCT = "USUFRUCT"
    DISPUTED = "DISPUTED"

class ConstructionStatus(str, enum.Enum):
    EMPTY_LAND = "EMPTY_LAND"
    EXCAVATION = "EXCAVATION"
    CONCRETE_STRUCTURE = "CONCRETE_STRUCTURE"
    FINISHING = "FINISHING"
    COMPLETED = "COMPLETED"
    SMART_ACTIVE = "SMART_ACTIVE"

class PropertyType(str, enum.Enum):
    APARTMENT = "APARTMENT"
    VILLA = "VILLA"
    OFFICE = "OFFICE"
    RETAIL = "RETAIL"
    WAREHOUSE = "WAREHOUSE"
    FACTORY = "FACTORY"
    LAND = "LAND"

class ContractType(str, enum.Enum):
    SALE = "SALE"
    RENTAL = "RENTAL"
    MORTGAGE = "MORTGAGE"
    LEASE = "LEASE"


# ========== 1. الأراضي السيادية (مع Multi-Tenancy) ==========
class LandAsset(Base):
    __tablename__ = "land_assets"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    parent_id = Column(Integer, ForeignKey("land_assets.id"), nullable=True, index=True)

    plot_number = Column(String(100), unique=True, nullable=False, index=True)
    area_sqm = Column(Numeric(15, 2), nullable=False)
    gps_polygon = Column(JSON, nullable=False)
    zoning = Column(SQLEnum(ZoningCategory), nullable=False)
    legal_status = Column(SQLEnum(LegalStatus), nullable=False)

    current_value_mrusdt = Column(Numeric(30, 8), default=0)
    has_insurance = Column(Boolean, default=False)

    owner_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_land_assets_tenant_owner", "tenant_id", "owner_id"),
        Index("ix_land_assets_owner_zoning", "owner_id", "zoning"),
    )


# ========== 2. المشاريع العمرانية ==========
class RealEstateDevelopment(Base):
    __tablename__ = "real_estate_developments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    land_asset_id = Column(Integer, ForeignKey("land_assets.id"), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)

    name = Column(String(255), nullable=False)
    development_type = Column(String(50), nullable=False)
    construction_status = Column(SQLEnum(ConstructionStatus), default=ConstructionStatus.EMPTY_LAND)

    total_budget_mrusdt = Column(Numeric(30, 8), default=0)
    spent_budget_mrusdt = Column(Numeric(30, 8), default=0)
    completion_percentage = Column(Numeric(5, 2), default=0)

    bim_model_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_developments_tenant_land", "tenant_id", "land_asset_id"),
    )


# ========== 3. الوحدات العقارية ==========
class PropertyUnit(Base):
    __tablename__ = "property_units"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    development_id = Column(Integer, ForeignKey("real_estate_developments.id"), nullable=False, index=True)

    unit_number = Column(String(50), nullable=False)
    floor_number = Column(Integer, nullable=True)
    area_sqm = Column(Numeric(10, 2), nullable=False)
    property_type = Column(SQLEnum(PropertyType), nullable=False)

    sale_price_mrusdt = Column(Numeric(30, 8), nullable=True)
    rent_per_month_mrusdt = Column(Numeric(30, 8), nullable=True)

    smart_asset_id = Column(Integer, ForeignKey("smart_assets.id"), nullable=True)

    is_available_for_sale = Column(Boolean, default=True)
    is_available_for_rent = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_units_tenant_development", "tenant_id", "development_id"),
    )


# ========== 4. الملكية الجزئية (مع Idempotency) ==========
class PropertyOwnership(Base):
    __tablename__ = "property_ownerships"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد

    unit_id = Column(Integer, ForeignKey("property_units.id"), nullable=False, index=True)
    owner_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    ownership_percentage = Column(Numeric(5, 2), nullable=False)
    acquisition_date = Column(DateTime(timezone=True), nullable=False)

    deed_nft_token_id = Column(String(100), unique=True, nullable=True)
    purchase_tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_ownership_tenant_unit_owner", "tenant_id", "unit_id", "owner_user_id"),
        CheckConstraint("ownership_percentage > 0 AND ownership_percentage <= 100", name="check_ownership_pct"),
    )


# ========== 5. عقود الإيجار (مع Idempotency) ==========
class RentalContract(Base):
    __tablename__ = "rental_contracts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد

    unit_id = Column(Integer, ForeignKey("property_units.id"), nullable=False, index=True)
    tenant_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    landlord_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    monthly_rent_mrusdt = Column(Numeric(30, 8), nullable=False)

    status = Column(String(50), default="ACTIVE")
    contract_tx_hash = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_rental_tenant_landlord", "tenant_id", "landlord_user_id"),
    )


# ========== 6. المخطط الرئيسي (Master Plan) – توسعة جديدة ==========
class MasterPlan(Base):
    __tablename__ = "master_plans"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    land_asset_id = Column(Integer, ForeignKey("land_assets.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    gis_data = Column(JSON, nullable=True)
    bim_model_hash = Column(String(100), nullable=True)

    total_units_planned = Column(Integer, default=0)
    total_area_sqm = Column(Numeric(15, 2), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_master_plan_tenant_land", "tenant_id", "land_asset_id"),
    )


# ========== 7. تجزئة الأصول (Asset Tokenization) – توسعة جديدة ==========
class AssetTokenization(Base):
    __tablename__ = "asset_tokenizations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    unit_id = Column(Integer, ForeignKey("property_units.id"), nullable=False, index=True)

    total_shares = Column(Integer, nullable=False)
    share_price_mrusdt = Column(Numeric(30, 8), nullable=False)
    minimum_investment_shares = Column(Integer, default=1)

    is_active = Column(Boolean, default=True)
    is_fully_subscribed = Column(Boolean, default=False)

    smart_contract_address = Column(String(42), nullable=True)
    token_symbol = Column(String(10), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_tokenization_tenant_unit", "tenant_id", "unit_id"),
    )


# ========== 8. محرك العقود الذكية (Smart Contract Engine) – توسعة جديدة ==========
class SmartContractEngine(Base):
    __tablename__ = "smart_contract_engine"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد

    contract_type = Column(SQLEnum(ContractType), nullable=False)
    reference_id = Column(Integer, nullable=False)
    blockchain_tx_hash = Column(String(100), nullable=True)

    execution_status = Column(String(50), default="PENDING")
    executed_at = Column(DateTime(timezone=True), nullable=True)

    contract_metadata = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_smart_contract_tenant_type", "tenant_id", "contract_type"),
    )