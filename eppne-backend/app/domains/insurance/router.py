"""
مسارات (Endpoints) قطاع التأمينات السيادية
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from decimal import Decimal

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser
from app.domains.identity.models import User
from app.domains.insurance.service import InsuranceService
from app.domains.insurance.repository import InsuranceRepository
from app.domains.insurance.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/insurance", tags=["Sovereign Insurance"])


# ========== Policies ==========
@router.post("/policies", response_model=InsurancePolicyResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_policy(
    data: InsurancePolicyCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = InsuranceService(db)
    policy = await service.create_policy(current_user.id, tenant.id, data.model_dump())
    return policy


@router.get("/policies", response_model=List[InsurancePolicyResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_policies(
    policy_type: Optional[PolicyType] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = InsuranceRepository(db)
    policies = await repo.list_policies(tenant.id, policy_type, is_active, skip, limit)
    return policies


@router.get("/policies/{policy_id}", response_model=InsurancePolicyResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_policy(
    policy_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = InsuranceRepository(db)
    policy = await repo.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


# ========== Subscriptions (مع Idempotency + Rate Limiting) ==========
@router.post("/subscriptions", response_model=InsuranceSubscriptionResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def subscribe(
    data: InsuranceSubscriptionCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InsuranceService(db)
    subscription = await service.subscribe(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return subscription


@router.get("/subscriptions/me", response_model=List[InsuranceSubscriptionResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def get_my_subscriptions(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = InsuranceRepository(db)
    subscriptions = await repo.list_subscriptions(tenant.id, current_user.id, status, skip, limit)
    return subscriptions


@router.post("/subscriptions/{subscription_id}/renew", response_model=InsuranceSubscriptionResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def renew_subscription(
    subscription_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InsuranceService(db)
    renewed = await service.renew_subscription(subscription_id, current_user.id)
    return renewed


# ========== Claims (مع Idempotency + Rate Limiting) ==========
@router.post("/claims", response_model=InsuranceClaimResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=20, window_seconds=60)
async def submit_claim(
    data: InsuranceClaimCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InsuranceService(db)
    claim = await service.submit_claim(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return claim


@router.get("/claims/me", response_model=List[InsuranceClaimResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def get_my_claims(
    status: Optional[ClaimStatus] = None,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = InsuranceRepository(db)
    claims = await repo.list_claims_for_user(current_user.id, status)
    return claims


@router.put("/claims/{claim_id}/review", response_model=InsuranceClaimResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def review_claim(
    claim_id: int,
    approve: bool,
    approved_amount: Optional[Decimal] = None,
    notes: Optional[str] = None,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = InsuranceService(db)
    claim = await service.review_claim(
        claim_id=claim_id,
        reviewer_id=current_user.id,
        tenant_id=tenant.id,
        approve=approve,
        approved_amount=approved_amount,
        notes=notes,
        idempotency_key=idempotency_key
    )
    return claim


# ========== Pensions ==========
@router.post("/pensions", response_model=PensionRecordResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, window_seconds=60)
async def create_pension(
    data: PensionRecordCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = InsuranceService(db)
    pension = await service.create_pension(current_user.id, data.model_dump())
    return pension


@router.get("/pensions/me", response_model=List[PensionRecordResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def get_my_pensions(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = InsuranceRepository(db)
    pensions = await repo.list_pensions_for_beneficiary(current_user.id)
    return pensions


# ========== Employee Insurance ==========
@router.post("/employee-profiles", response_model=EmployeeInsuranceProfileResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, window_seconds=60)
async def create_employee_profile(
    data: EmployeeInsuranceProfileCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = InsuranceService(db)
    profile = await service.create_employee_insurance_profile(current_user.id, data.model_dump())
    return profile


@router.get("/employee-profiles/me", response_model=EmployeeInsuranceProfileResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def get_my_employee_profile(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = InsuranceRepository(db)
    profile = await repo.get_employee_profile(current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


# ========== Admin / Scheduled Jobs ==========
@router.post("/admin/disburse-pensions")
@rate_limit(max_requests=5, window_seconds=60)
async def disburse_pensions(
    background_tasks: BackgroundTasks,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = InsuranceService(db)
    count = await service.disburse_monthly_pensions()
    return {"message": f"Disbursed {count} pensions", "count": count}