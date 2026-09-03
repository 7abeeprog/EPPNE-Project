# app/domains/tourism_sports/router.py (الإصدار النهائي المتكامل)
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, cast

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser
from app.domains.identity.models import User
from app.domains.tourism_sports.service import TourismSportsService
from app.domains.tourism_sports.schemas import *
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/tourism-sports", tags=["Sovereign Tourism, Entertainment & Sports"])

# ========== السياحة ==========
@router.post("/destinations", response_model=DestinationResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_destination(
    data: DestinationCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    user_id = cast(int, current_user.id)
    dest = await service.create_destination(user_id, cast(int, current_user.tenant_id), data.model_dump())  # ✅ cast
    return dest

@router.get("/destinations", response_model=list[DestinationResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_destinations(
    destination_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    dests = await service.list_destinations(cast(int, current_user.tenant_id), destination_type)  # ✅ cast
    return dests

@router.get("/destinations/{dest_id}", response_model=DestinationResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_destination(
    dest_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    dest = await service.get_destination(dest_id, cast(int, current_user.tenant_id))
    return dest

@router.post("/programs", response_model=TourismProgramResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_program(
    data: TourismProgramCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    user_id = cast(int, current_user.id)
    prog = await service.create_program(user_id, cast(int, current_user.tenant_id), data.model_dump())  # ✅ cast
    return prog

@router.get("/programs", response_model=list[TourismProgramResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_programs(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    programs = await service.list_programs(cast(int, current_user.tenant_id))
    return programs

@router.get("/programs/{program_id}", response_model=TourismProgramResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_program(
    program_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    program = await service.get_program(program_id, cast(int, current_user.tenant_id))
    return program

@router.post("/programs/{program_id}/book", response_model=ProgramBookingResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def book_program(
    program_id: int,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    user_id = cast(int, current_user.id)
    participant = await service.book_program(user_id, cast(int, current_user.tenant_id), program_id, idempotency_key)  # ✅ cast
    return participant

# ========== الترفيه ==========
@router.post("/events", response_model=EventResponse, status_code=201)
@rate_limit(max_requests=10, window_seconds=60)
async def create_event(
    data: EventCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    user_id = cast(int, current_user.id)
    event = await service.create_event(user_id, cast(int, current_user.tenant_id), data.model_dump())  # ✅ cast
    return event

@router.get("/events/{event_id}", response_model=EventResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_event(
    event_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    event = await service.get_event(event_id, cast(int, current_user.tenant_id))
    return event

@router.post("/tickets/purchase", response_model=TicketResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def buy_ticket(
    data: TicketPurchase,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    user_id = cast(int, current_user.id)
    ticket = await service.purchase_event_ticket(
        user_id=user_id,
        tenant_id=cast(int, current_user.tenant_id),  # ✅ cast
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
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    user_id = cast(int, current_user.id)
    org = await service.create_sports_org(user_id, cast(int, current_user.tenant_id), data.model_dump())  # ✅ cast
    return org

@router.get("/sports/organizations", response_model=list[SportsOrgResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_sports_orgs(
    org_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    orgs = await service.list_sports_orgs(cast(int, current_user.tenant_id), org_type)
    return orgs

@router.get("/sports/organizations/{org_id}", response_model=SportsOrgResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_sports_org(
    org_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    org = await service.get_sports_org(org_id, cast(int, current_user.tenant_id))
    return org

@router.post("/sports/players/profile", response_model=PlayerProfileResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def create_player_profile(
    data: PlayerProfileCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    user_id = cast(int, current_user.id)
    profile = await service.create_player_profile(user_id, cast(int, current_user.tenant_id), data.model_dump())  # ✅ cast
    return profile

@router.get("/sports/players", response_model=list[PlayerProfileResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_players(
    club_id: Optional[int] = None,
    sport_category: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    players = await service.list_players(cast(int, current_user.tenant_id), club_id, sport_category)
    return players

@router.get("/sports/players/{profile_id}", response_model=PlayerProfileResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_player(
    profile_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    player = await service.get_player(profile_id, cast(int, current_user.tenant_id))
    return player

@router.post("/sports/transfers/bid", response_model=TransferBidResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def place_transfer_bid(
    data: TransferBidCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    user_id = cast(int, current_user.id)
    transfer = await service.place_transfer_bid(
        user_id=user_id,
        tenant_id=cast(int, current_user.tenant_id),  # ✅ cast
        from_club_id=data.from_club_id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return transfer

@router.get("/sports/transfers", response_model=list[TransferBidResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_transfers(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    transfers = await service.list_transfers(cast(int, current_user.tenant_id), status)
    return transfers

@router.get("/sports/transfers/{transfer_id}", response_model=TransferBidResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_transfer(
    transfer_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    transfer = await service.get_transfer(transfer_id, cast(int, current_user.tenant_id))
    return transfer

@router.post("/sports/tournaments", response_model=TournamentResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def create_tournament(
    data: TournamentCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = TourismSportsService(db)
    user_id = cast(int, current_user.id)
    tournament = await service.create_tournament(user_id, cast(int, current_user.tenant_id), data.model_dump())  # ✅ cast
    return tournament