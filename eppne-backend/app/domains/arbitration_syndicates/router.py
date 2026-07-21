# app/domains/arbitration_syndicates/router.py (الإصدار النهائي المتكامل)
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, cast
import uuid

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, get_current_tenant
from app.domains.identity.models import User
from app.domains.arbitration_syndicates.service import ArbitrationSyndicatesService
from app.domains.arbitration_syndicates.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/arbitration-syndicates", tags=["Sovereign Arbitration & Syndicates"])


# ============================================================
# 1. التحكيم (Arbitration)
# ============================================================

@router.post("/cases", response_model=ArbitrationCaseResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_dispute(
    data: ArbitrationCaseCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إنشاء قضية تحكيم جديدة"""
    service = ArbitrationSyndicatesService(db)
    idempotency_key = idempotency_key or f"ARB-{uuid.uuid4().hex[:12].upper()}"
    case = await service.create_dispute(
        claimant_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return case


@router.get("/cases/me", response_model=List[ArbitrationCaseResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def get_my_cases(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب قضايا التحكيم الخاصة بالمستخدم الحالي"""
    service = ArbitrationSyndicatesService(db)
    return await service.get_user_cases(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id)
    )


@router.get("/cases/{case_id}", response_model=ArbitrationCaseResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def get_case(
    case_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب تفاصيل قضية تحكيم محددة"""
    service = ArbitrationSyndicatesService(db)
    case = await service.get_case(
        case_id=case_id,
        tenant_id=cast(int, tenant.id)
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.post("/cases/{case_id}/jury-vote", response_model=dict)
@rate_limit(max_requests=10, window_seconds=60)
async def cast_jury_vote(
    case_id: int,
    data: JuryVoteCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """تصويت المحلف في قضية تحكيم"""
    service = ArbitrationSyndicatesService(db)
    idempotency_key = idempotency_key or f"JURY-{uuid.uuid4().hex[:12].upper()}"
    vote = await service.cast_jury_vote(
        juror_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        case_id=case_id,
        vote=data.vote,
        justification=data.justification,
        idempotency_key=idempotency_key
    )
    return {"message": "تم تسجيل صوت المحلف", "vote_id": vote.id}


@router.post("/cases/{case_id}/verdict")
@rate_limit(max_requests=5, window_seconds=60)
async def issue_verdict(
    case_id: int,
    data: VerdictCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """إصدار حكم في قضية تحكيم (للمشرفين فقط)"""
    service = ArbitrationSyndicatesService(db)
    idempotency_key = idempotency_key or f"VERDICT-{uuid.uuid4().hex[:12].upper()}"
    case = await service.issue_verdict(
        case_id=case_id,
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(),
        user_id=cast(int, current_user.id),
        idempotency_key=idempotency_key
    )
    return {"message": "تم إصدار الحكم", "case_id": case.id}


# ============================================================
# 2. النقابات (Syndicates)
# ============================================================

@router.post("/syndicates", response_model=SyndicateResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_syndicate(
    data: SyndicateCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """إنشاء نقابة جديدة (للمشرفين فقط)"""
    service = ArbitrationSyndicatesService(db)
    synd = await service.create_syndicate(
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return synd


@router.get("/syndicates", response_model=List[SyndicateResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_syndicates(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب قائمة النقابات النشطة للمستأجر الحالي"""
    service = ArbitrationSyndicatesService(db)
    return await service.list_syndicates(tenant_id=cast(int, tenant.id))


@router.get("/syndicates/{syndicate_id}", response_model=SyndicateResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def get_syndicate(
    syndicate_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب تفاصيل نقابة محددة"""
    service = ArbitrationSyndicatesService(db)
    synd = await service.get_syndicate(
        syndicate_id=syndicate_id,
        tenant_id=cast(int, tenant.id)
    )
    if not synd:
        raise HTTPException(status_code=404, detail="Syndicate not found")
    return synd


@router.post("/syndicates/{syndicate_id}/join", response_model=SyndicateMembershipResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def join_syndicate(
    syndicate_id: int,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """الانضمام إلى نقابة (مع دفع الرسوم)"""
    service = ArbitrationSyndicatesService(db)
    idempotency_key = idempotency_key or f"JOIN-{uuid.uuid4().hex[:12].upper()}"
    membership = await service.join_syndicate(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        syndicate_id=syndicate_id,
        idempotency_key=idempotency_key
    )
    return membership


@router.post("/licenses", response_model=ProfessionalLicenseResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, window_seconds=60)
async def issue_license(
    data: ProfessionalLicenseCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إصدار رخصة مهنية (يتطلب عضوية في النقابة)"""
    service = ArbitrationSyndicatesService(db)
    idempotency_key = idempotency_key or f"LIC-{uuid.uuid4().hex[:12].upper()}"
    license = await service.issue_license(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return license


@router.get("/licenses/me", response_model=List[ProfessionalLicenseResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def get_my_licenses(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب التراخيص المهنية الخاصة بالمستخدم الحالي"""
    service = ArbitrationSyndicatesService(db)
    return await service.get_user_licenses(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id)
    )


# ============================================================
# 3. الانتخابات (Elections)
# ============================================================

@router.post("/elections", response_model=ElectionResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, window_seconds=60)
async def create_election(
    data: ElectionCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """إنشاء انتخابات نقابية جديدة (للمشرفين فقط)"""
    service = ArbitrationSyndicatesService(db)
    election = await service.create_election(
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return election


@router.get("/elections/{election_id}", response_model=ElectionResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def get_election(
    election_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب تفاصيل انتخابات محددة"""
    service = ArbitrationSyndicatesService(db)
    election = await service.get_election(
        election_id=election_id,
        tenant_id=cast(int, tenant.id)
    )
    if not election:
        raise HTTPException(status_code=404, detail="Election not found")
    return election


@router.get("/syndicates/{syndicate_id}/elections", response_model=List[ElectionResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def list_syndicate_elections(
    syndicate_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب قائمة الانتخابات لنقابة محددة"""
    service = ArbitrationSyndicatesService(db)
    return await service.list_syndicate_elections(
        syndicate_id=syndicate_id,
        tenant_id=cast(int, tenant.id)
    )


@router.post("/elections/{election_id}/candidates", response_model=CandidateResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def nominate_candidate(
    election_id: int,
    data: CandidateCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """ترشيح مرشح للانتخابات"""
    service = ArbitrationSyndicatesService(db)
    candidate = await service.nominate_candidate(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        election_id=election_id,
        data=data.model_dump()
    )
    return candidate


@router.get("/elections/{election_id}/candidates", response_model=List[CandidateResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def list_candidates(
    election_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب قائمة المرشحين لانتخابات محددة"""
    service = ArbitrationSyndicatesService(db)
    return await service.list_candidates(
        election_id=election_id,
        tenant_id=cast(int, tenant.id)
    )


@router.post("/elections/{election_id}/vote")
@rate_limit(max_requests=5, window_seconds=60)
async def vote_in_election(
    election_id: int,
    data: VoteCast,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """التصويت في الانتخابات"""
    service = ArbitrationSyndicatesService(db)
    idempotency_key = idempotency_key or f"VOTE-{uuid.uuid4().hex[:12].upper()}"
    vote = await service.cast_election_vote(
        voter_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        election_id=election_id,
        candidate_id=data.candidate_id,
        idempotency_key=idempotency_key
    )
    return {"message": "تم تسجيل صوتك بنجاح", "vote_hash": vote.vote_hash}