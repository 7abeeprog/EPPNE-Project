"""
مسارات (Endpoints) قطاع التأمينات السيادية
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, cast
from decimal import Decimal

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser
from app.domains.identity.models import User
from app.domains.insurance.service import InsuranceService
from app.domains.insurance.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/insurance", tags=["Sovereign Insurance"])


# ============================================================
# 1. بوالص التأمين (Policies)
# ============================================================

@router.post("/policies", response_model=InsurancePolicyResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_policy(
    data: InsurancePolicyCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = InsuranceService(db)
    policy = await service.create_policy(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return policy


@router.get("/policies", response_model=List[InsurancePolicyResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_policies(
    policy_type: Optional[PolicyType] = Query(None, description="نوع البوليصة"),
    is_active: Optional[bool] = Query(None, description="هل البوليصة نشطة؟"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InsuranceService(db)
    policies = await service.list_policies(
        tenant_id=cast(int, tenant.id),
        policy_type=policy_type,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    return policies


@router.get("/policies/{policy_id}", response_model=InsurancePolicyResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_policy(
    policy_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InsuranceService(db)
    policy = await service.get_policy(
        policy_id=policy_id,
        tenant_id=cast(int, tenant.id)
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


# ============================================================
# 2. اشتراكات التأمين (Subscriptions)
# ============================================================

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
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return subscription


@router.get("/subscriptions/me", response_model=List[InsuranceSubscriptionResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def get_my_subscriptions(
    status: Optional[str] = Query(None, description="حالة الاشتراك"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InsuranceService(db)
    subscriptions = await service.get_my_subscriptions(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        status=status,
        skip=skip,
        limit=limit
    )
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
    renewed = await service.renew_subscription(
        subscription_id=subscription_id,
        user_id=cast(int, current_user.id)
    )
    return renewed


# ============================================================
# 3. مطالبات التعويض (Claims)
# ============================================================

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
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return claim


@router.get("/claims/me", response_model=List[InsuranceClaimResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def get_my_claims(
    status: Optional[ClaimStatus] = Query(None, description="حالة المطالبة"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InsuranceService(db)
    claims = await service.get_my_claims(
        user_id=cast(int, current_user.id),
        status=status
    )
    return claims


@router.put("/claims/{claim_id}/review", response_model=InsuranceClaimResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def review_claim(
    claim_id: int,
    approve: bool = Query(..., description="true للموافقة، false للرفض"),
    approved_amount: Optional[Decimal] = Query(None, description="المبلغ المعتمد (إن كانت الموافقة)"),
    notes: Optional[str] = Query(None, description="ملاحظات المراجعة"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = InsuranceService(db)
    claim = await service.review_claim(
        claim_id=claim_id,
        reviewer_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        approve=approve,
        approved_amount=approved_amount,
        notes=notes,
        idempotency_key=idempotency_key
    )
    return claim


# ============================================================
# 4. المعاشات (Pensions)
# ============================================================

@router.post("/pensions", response_model=PensionRecordResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, window_seconds=60)
async def create_pension(
    data: PensionRecordCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = InsuranceService(db)
    pension_data = data.model_dump()
    pension_data["tenant_id"] = tenant.id
    pension = await service.create_pension(
        user_id=cast(int, current_user.id),
        data=pension_data
    )
    return pension


@router.get("/pensions/me", response_model=List[PensionRecordResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def get_my_pensions(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InsuranceService(db)
    pensions = await service.get_my_pensions(user_id=cast(int, current_user.id))
    return pensions


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


# ============================================================
# 5. ملفات التأمين للموظفين (Employee Insurance)
# ============================================================

@router.post("/employee-profiles", response_model=EmployeeInsuranceProfileResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, window_seconds=60)
async def create_employee_profile(
    data: EmployeeInsuranceProfileCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = InsuranceService(db)
    profile_data = data.model_dump()
    profile_data["tenant_id"] = tenant.id
    profile = await service.create_employee_insurance_profile(
        user_id=cast(int, current_user.id),
        data=profile_data
    )
    return profile


@router.get("/employee-profiles/me", response_model=EmployeeInsuranceProfileResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def get_my_employee_profile(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = InsuranceService(db)
    profile = await service.get_employee_profile(user_id=cast(int, current_user.id))
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile