# app/domains/arbitration_syndicates/router.py (الإصدار النهائي المتكامل)
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, get_current_tenant
from app.domains.identity.models import User
from app.domains.arbitration_syndicates.service import ArbitrationSyndicatesService
from app.domains.arbitration_syndicates.repository import ArbitrationSyndicatesRepository
from app.domains.arbitration_syndicates.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/arbitration-syndicates", tags=["Sovereign Arbitration & Syndicates"])

# ========== Arbitration ==========
@router.post("/cases", response_model=ArbitrationCaseResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_dispute(
    data: ArbitrationCaseCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ArbitrationSyndicatesService(db)
    case = await service.create_dispute(
        claimant_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return case

@router.get("/cases/me", response_model=list[ArbitrationCaseResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def get_my_cases(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = ArbitrationSyndicatesRepository(db)
    cases = await repo.list_user_cases(current_user.id)
    return cases

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
    service = ArbitrationSyndicatesService(db)
    vote = await service.cast_jury_vote(
        juror_id=current_user.id,
        tenant_id=tenant.id,
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
    service = ArbitrationSyndicatesService(db)
    case = await service.issue_verdict(
        case_id=case_id,
        tenant_id=tenant.id,
        data=data.model_dump(),
        user_id=current_user.id,
        idempotency_key=idempotency_key
    )
    return {"message": "تم إصدار الحكم", "case_id": case.id}

# ========== Syndicates ==========
@router.post("/syndicates", response_model=SyndicateResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_syndicate(
    data: SyndicateCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    repo = ArbitrationSyndicatesRepository(db)
    synd = await repo.create_syndicate(tenant_id=tenant.id, **data.model_dump())
    return synd

@router.get("/syndicates", response_model=list[SyndicateResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_syndicates(
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = ArbitrationSyndicatesRepository(db)
    syndicates = await repo.list_syndicates(tenant.id)
    return syndicates

@router.post("/syndicates/{syndicate_id}/join", response_model=SyndicateMembershipResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def join_syndicate(
    syndicate_id: int,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ArbitrationSyndicatesService(db)
    membership = await service.join_syndicate(
        user_id=current_user.id,
        tenant_id=tenant.id,
        syndicate_id=syndicate_id,
        idempotency_key=idempotency_key
    )
    return membership

@router.post("/licenses", response_model=ProfessionalLicenseResponse, status_code=201)
@rate_limit(max_requests=5, window_seconds=60)
async def issue_license(
    data: ProfessionalLicenseCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ArbitrationSyndicatesService(db)
    license = await service.issue_license(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return license

@router.get("/licenses/me", response_model=list[ProfessionalLicenseResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def get_my_licenses(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = ArbitrationSyndicatesRepository(db)
    licenses = await repo.get_licenses_for_user(current_user.id)
    return licenses

# ========== Elections ==========
@router.post("/elections", response_model=ElectionResponse, status_code=201)
@rate_limit(max_requests=5, window_seconds=60)
async def create_election(
    data: ElectionCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    repo = ArbitrationSyndicatesRepository(db)
    election = await repo.create_election(tenant_id=tenant.id, **data.model_dump())
    return election

@router.post("/elections/{election_id}/candidates", response_model=CandidateResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def nominate_candidate(
    election_id: int,
    data: CandidateCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = ArbitrationSyndicatesRepository(db)
    candidate = await repo.create_candidate(
        tenant_id=tenant.id,
        election_id=election_id,
        user_id=current_user.id,
        **data.model_dump()
    )
    return candidate

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
    service = ArbitrationSyndicatesService(db)
    vote = await service.cast_election_vote(
        voter_id=current_user.id,
        tenant_id=tenant.id,
        election_id=election_id,
        candidate_id=data.candidate_id,
        idempotency_key=idempotency_key
    )
    return {"message": "تم تسجيل صوتك بنجاح", "vote_hash": vote.vote_hash}