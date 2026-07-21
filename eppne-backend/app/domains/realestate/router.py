# app/domains/realestate/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, cast
from decimal import Decimal

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, get_current_tenant
from app.domains.identity.models import User
from app.domains.realestate.service import RealEstateService
from app.domains.realestate.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/realestate", tags=["Sovereign Real Estate"])

# ========== Land Assets ==========
@router.post("/lands", response_model=LandAssetResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_land_asset(
    data: LandAssetCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = RealEstateService(db)
    user_id = cast(int, current_user.id)
    asset = await service.create_land_asset(
        tenant_id=cast(int, tenant.id),
        owner_id=user_id,
        data=data.model_dump()
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
    service = RealEstateService(db)
    user_id = cast(int, current_user.id)
    lands = await service.get_my_lands(cast(int, tenant.id), user_id, skip=skip, limit=limit)
    return lands

@router.patch("/lands/{land_id}/revalue", response_model=LandAssetResponse)
async def revalue_land(
    land_id: int,
    new_value: Decimal,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = RealEstateService(db)
    admin_id = cast(int, current_user.id)
    land = await service.revalue_land(land_id, new_value, admin_id)
    return land

# ========== Developments ==========
@router.post("/developments", response_model=DevelopmentResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_development(
    data: DevelopmentCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = RealEstateService(db)
    dev = await service.create_development(tenant_id=cast(int, tenant.id), data=data.model_dump())
    return dev

@router.get("/developments/{dev_id}", response_model=DevelopmentResponse)
async def get_development(
    dev_id: int,
    db: AsyncSession = Depends(get_db)
):
    service = RealEstateService(db)
    return await service.get_development(dev_id)

# ========== Property Units ==========
@router.post("/units", response_model=PropertyUnitResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_property_unit(
    data: PropertyUnitCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = RealEstateService(db)
    unit = await service.create_property_unit(
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return unit

@router.get("/units/for-sale", response_model=list[PropertyUnitResponse])
async def list_units_for_sale(
    development_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    service = RealEstateService(db)
    units = await service.list_units_for_sale(development_id, skip, limit)
    return units

@router.post("/units/{unit_id}/buy", response_model=OwnershipResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def buy_fraction(
    unit_id: int,
    data: BuyFractionalOwnership,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = RealEstateService(db)
    user_id = cast(int, current_user.id)
    ownership = await service.buy_fractional_ownership(
        buyer_id=user_id,
        tenant_id=cast(int, tenant.id),
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
    service = RealEstateService(db)
    user_id = cast(int, current_user.id)
    ownerships = await service.get_my_ownerships(user_id)
    return ownerships

# ========== Rental ==========
@router.post("/rentals", response_model=RentalContractResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_rental_contract(
    data: RentalContractCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = RealEstateService(db)
    user_id = cast(int, current_user.id)
    contract = await service.rent_unit(
        landlord_id=user_id,
        tenant_id=cast(int, tenant.id),
        unit_id=data.unit_id,
        tenant_user_id=data.tenant_user_id,
        monthly_rent=data.monthly_rent_mrusdt,
        start_date=data.start_date,
        end_date=data.end_date,
        idempotency_key=idempotency_key
    )
    return contract

# ========== Master Plans ==========
@router.post("/master-plans", response_model=MasterPlanResponse, status_code=201)
@rate_limit(max_requests=5, window_seconds=60)
async def create_master_plan(
    data: MasterPlanCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = RealEstateService(db)
    plan = await service.create_master_plan(cast(int, tenant.id), data.model_dump())
    return plan

# ========== Tokenization ==========
@router.post("/tokenize/{unit_id}", response_model=TokenizationResponse, status_code=201)
@rate_limit(max_requests=5, window_seconds=60)
async def tokenize_asset(
    unit_id: int,
    data: TokenizationCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = RealEstateService(db)
    token = await service.tokenize_asset(
        tenant_id=cast(int, tenant.id),
        unit_id=unit_id,
        total_shares=data.total_shares,
        share_price=data.share_price_mrusdt
    )
    return token

# ========== Smart Contracts ==========
@router.post("/smart-contracts", response_model=SmartContractResponse, status_code=201)
@rate_limit(max_requests=5, window_seconds=60)
async def deploy_smart_contract(
    data: SmartContractCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = RealEstateService(db)
    contract = await service.deploy_smart_contract(
        tenant_id=cast(int, tenant.id),
        contract_type=data.contract_type,
        reference_id=data.reference_id,
        contract_metadata=data.contract_metadata,
        idempotency_key=idempotency_key
    )
    return contract