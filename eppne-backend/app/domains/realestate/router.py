# app/domains/realestate/router.py (الإصدار النهائي المتكامل)
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from decimal import Decimal

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, get_current_tenant
from app.domains.identity.models import User
from app.domains.realestate.service import RealEstateService
from app.domains.realestate.repository import RealEstateRepository
from app.domains.realestate.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/realestate", tags=["Sovereign Real Estate"])

# ========== Land Assets ==========
@router.post("/lands", response_model=LandAssetResponse, status_code=201)
async def create_land_asset(
    data: LandAssetCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = RealEstateRepository(db)
    asset = await repo.create_land_asset(
        tenant_id=tenant.id,
        owner_id=current_user.id,
        **data.model_dump()
    )
    return asset

@router.get("/lands/me", response_model=list[LandAssetResponse])
async def get_my_lands(
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = RealEstateRepository(db)
    lands = await repo.list_land_assets(tenant.id, owner_id=current_user.id, skip=skip, limit=limit)
    return lands

@router.patch("/lands/{land_id}/revalue", response_model=LandAssetResponse)
async def revalue_land(
    land_id: int,
    new_value: Decimal,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = RealEstateService(db)
    land = await service.revalue_land(land_id, new_value, current_user.id)
    return land

# ========== Developments ==========
@router.post("/developments", response_model=DevelopmentResponse, status_code=201)
async def create_development(
    data: DevelopmentCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = RealEstateRepository(db)
    dev = await repo.create_development(tenant_id=tenant.id, **data.model_dump())
    return dev

@router.get("/developments/{dev_id}", response_model=DevelopmentResponse)
async def get_development(
    dev_id: int,
    db: AsyncSession = Depends(get_db)
):
    repo = RealEstateRepository(db)
    dev = await repo.get_development(dev_id)
    if not dev:
        raise HTTPException(404, "Development not found")
    return dev

# ========== Property Units ==========
@router.post("/units", response_model=PropertyUnitResponse, status_code=201)
async def create_property_unit(
    data: PropertyUnitCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = RealEstateRepository(db)
    unit = await repo.create_unit(tenant_id=tenant.id, **data.model_dump())
    return unit

@router.get("/units/for-sale", response_model=list[PropertyUnitResponse])
async def list_units_for_sale(
    development_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    repo = RealEstateRepository(db)
    units = await repo.list_units(development_id, for_sale=True, skip=skip, limit=limit)
    return units

@router.post("/units/{unit_id}/buy", response_model=OwnershipResponse)
@rate_limit(max_requests=10, window=60)
async def buy_fraction(
    unit_id: int,
    data: BuyFractionalOwnership,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = RealEstateService(db)
    ownership = await service.buy_fractional_ownership(
        buyer_id=current_user.id,
        tenant_id=tenant.id,
        unit_id=unit_id,
        percentage=data.ownership_percentage,
        idempotency_key=idempotency_key
    )
    return ownership

@router.get("/my-ownerships", response_model=list[OwnershipResponse])
async def get_my_ownerships(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = RealEstateRepository(db)
    ownerships = await repo.get_user_ownerships(current_user.id)
    return ownerships

# ========== Rental ==========
@router.post("/rentals", response_model=RentalContractResponse, status_code=201)
@rate_limit(max_requests=10, window=60)
async def create_rental_contract(
    data: RentalContractCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = RealEstateService(db)
    contract = await service.rent_unit(
        landlord_id=current_user.id,
        tenant_id=tenant.id,
        unit_id=data.unit_id,
        monthly_rent=data.monthly_rent_mrusdt,
        start_date=data.start_date,
        end_date=data.end_date,
        idempotency_key=idempotency_key
    )
    return contract

# ========== Master Plans ==========
@router.post("/master-plans", response_model=MasterPlanResponse, status_code=201)
@rate_limit(max_requests=5, window=60)
async def create_master_plan(
    data: MasterPlanCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = RealEstateService(db)
    plan = await service.create_master_plan(tenant.id, data.model_dump())
    return plan

# ========== Tokenization ==========
@router.post("/tokenize/{unit_id}", response_model=TokenizationResponse, status_code=201)
@rate_limit(max_requests=5, window=60)
async def tokenize_asset(
    unit_id: int,
    data: TokenizationCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = RealEstateService(db)
    token = await service.tokenize_asset(
        tenant_id=tenant.id,
        unit_id=unit_id,
        total_shares=data.total_shares,
        share_price=data.share_price_mrusdt
    )
    return token

# ========== Smart Contracts ==========
@router.post("/smart-contracts", response_model=SmartContractResponse, status_code=201)
@rate_limit(max_requests=5, window=60)
async def deploy_smart_contract(
    data: SmartContractCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = RealEstateService(db)
    contract = await service.deploy_smart_contract(
        tenant_id=tenant.id,
        contract_type=data.contract_type,
        reference_id=data.reference_id,
        contract_metadata=data.contract_metadata
    )
    return contract