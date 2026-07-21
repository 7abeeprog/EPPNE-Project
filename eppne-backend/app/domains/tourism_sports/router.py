# app/domains/tourism_sports/router.py (الإصدار النهائي المتكامل)
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, cast

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, get_current_tenant
from app.domains.identity.models import User
from app.domains.tourism_sports.service import TourismSportsService
from app.domains.tourism_sports.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/tourism-sports", tags=["Sovereign Tourism, Entertainment & Sports"])

# ========== السياحة ==========
@router.post("/destinations", response_model=DestinationResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_destination(
    data: DestinationCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    user_id = cast(int, current_user.id)
    dest = await service.create_destination(user_id, cast(int, tenant.id), data.model_dump())  # ✅ cast
    return dest

@router.get("/destinations", response_model=list[DestinationResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_destinations(
    destination_type: Optional[str] = None,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    dests = await service.list_destinations(cast(int, tenant.id), destination_type)  # ✅ cast
    return dests

@router.post("/programs", response_model=TourismProgramResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_program(
    data: TourismProgramCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    user_id = cast(int, current_user.id)
    prog = await service.create_program(user_id, cast(int, tenant.id), data.model_dump())  # ✅ cast
    return prog

@router.post("/programs/{program_id}/book", response_model=ProgramBookingResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def book_program(
    program_id: int,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    user_id = cast(int, current_user.id)
    participant = await service.book_program(user_id, cast(int, tenant.id), program_id, idempotency_key)  # ✅ cast
    return participant

# ========== الترفيه ==========
@router.post("/events", response_model=EventResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_event(
    data: EventCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    user_id = cast(int, current_user.id)
    event = await service.create_event(user_id, cast(int, tenant.id), data.model_dump())  # ✅ cast
    return event

@router.post("/tickets/purchase", response_model=TicketResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def buy_ticket(
    data: TicketPurchase,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    user_id = cast(int, current_user.id)
    ticket = await service.purchase_event_ticket(
        user_id=user_id,
        tenant_id=cast(int, tenant.id),  # ✅ cast
        event_id=data.event_id,
        tier=data.tier.value,
        require_vip_transport=data.require_vip_transport,
        idempotency_key=idempotency_key
    )
    return ticket

# ========== الرياضة ==========
@router.post("/sports/organizations", response_model=SportsOrgResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_sports_org(
    data: SportsOrgCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    user_id = cast(int, current_user.id)
    org = await service.create_sports_org(user_id, cast(int, tenant.id), data.model_dump())  # ✅ cast
    return org

@router.post("/sports/players/profile", response_model=PlayerProfileResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def create_player_profile(
    data: PlayerProfileCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    user_id = cast(int, current_user.id)
    profile = await service.create_player_profile(user_id, cast(int, tenant.id), data.model_dump())  # ✅ cast
    return profile

@router.post("/sports/transfers/bid", response_model=TransferBidResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def place_transfer_bid(
    data: TransferBidCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    user_id = cast(int, current_user.id)
    transfer = await service.place_transfer_bid(
        user_id=user_id,
        tenant_id=cast(int, tenant.id),  # ✅ cast
        from_club_id=data.from_club_id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return transfer

@router.post("/sports/tournaments", response_model=TournamentResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def create_tournament(
    data: TournamentCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    user_id = cast(int, current_user.id)
    tournament = await service.create_tournament(user_id, cast(int, tenant.id), data.model_dump())  # ✅ cast
    return tournament