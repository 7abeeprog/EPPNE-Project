"""
regression test لجلسة `frontend-category-b-phase2-remaining-domains` (2026-09-02).
تقرير الجلسة: .claude/reports/frontend-category-b-phase2-session-log.md

السياق: 4 دوال كانت مطلوبة من الفرونت إند عبر hooks/tourism-sports/*.ts
(getProgram, getSportsOrg, getPlayer, getEvent) موجودة في
`TourismSportsRepository` بالفعل بدون service wrapper ولا router endpoint.
هذا الاختبار يتحقق حيًا (DB حقيقية، صفر mock) من الوصلات الأربع الجديدة
المضافة في service.py: get_program, get_sports_org, get_player, get_event —
بما في ذلك تحقق عزل tenant_id (IDOR) لكل واحدة منها.
"""
from decimal import Decimal
from datetime import datetime, timedelta

import pytest
from sqlalchemy import delete

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.core.errors import NotFoundError

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.tourism_sports.service import TourismSportsService
from app.domains.tourism_sports.repository import TourismSportsRepository
from app.domains.tourism_sports.models import (
    TourismProgram, EntertainmentVenue, EntertainmentEvent,
    SportsOrganization, PlayerProfile, ProgramTier, EventType, SportsEntityType,
    SportCategory,
)

TENANT_ID = 1
OTHER_TENANT_ID = 2


def _suffix() -> str:
    import uuid
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


@pytest.mark.asyncio
async def test_get_program_real_record_and_tenant_isolation(db):
    repo = TourismSportsRepository(db)
    program = await repo.create_program(
        tenant_id=TENANT_ID, title=f"REGTEST-PROG-{_suffix()}",
        program_tier=ProgramTier.STANDARD, base_price_mrusdt=Decimal("100"),
        max_capacity=10, start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=1), status="ANNOUNCED",
    )
    program_id = program.id
    service = TourismSportsService(db)
    try:
        result = await service.get_program(program_id, TENANT_ID)
        assert result.id == program_id

        with pytest.raises(NotFoundError):
            await service.get_program(program_id, OTHER_TENANT_ID)
        with pytest.raises(NotFoundError):
            await service.get_program(999_999_999, TENANT_ID)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(TourismProgram).where(TourismProgram.id == program_id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_get_event_real_record_and_tenant_isolation(db):
    repo = TourismSportsRepository(db)
    venue = await repo.create_venue(
        tenant_id=TENANT_ID, name=f"REGTEST-VENUE-{_suffix()}",
        location="Test Location", max_capacity=100,
    )
    event = await repo.create_event(
        tenant_id=TENANT_ID, venue_id=venue.id, title=f"REGTEST-EVENT-{_suffix()}",
        event_type=EventType.CONCERT, start_time=datetime.utcnow(),
        end_time=datetime.utcnow() + timedelta(hours=3), base_ticket_price_mrusdt=Decimal("50"),
    )
    event_id, venue_id = event.id, venue.id
    service = TourismSportsService(db)
    try:
        result = await service.get_event(event_id, TENANT_ID)
        assert result.id == event_id

        with pytest.raises(NotFoundError):
            await service.get_event(event_id, OTHER_TENANT_ID)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(EntertainmentEvent).where(EntertainmentEvent.id == event_id))
            await cleanup_db.execute(delete(EntertainmentVenue).where(EntertainmentVenue.id == venue_id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_get_sports_org_real_record_and_tenant_isolation(db):
    owner = await _create_user(db, "p_regtest_sportsorg_owner")
    repo = TourismSportsRepository(db)
    org = await repo.create_sports_org(
        tenant_id=TENANT_ID, owner_id=owner.id, name=f"REGTEST-ORG-{_suffix()}",
        org_type=SportsEntityType.CLUB,
    )
    org_id = org.id
    service = TourismSportsService(db)
    try:
        result = await service.get_sports_org(org_id, TENANT_ID)
        assert result.id == org_id

        with pytest.raises(NotFoundError):
            await service.get_sports_org(org_id, OTHER_TENANT_ID)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(SportsOrganization).where(SportsOrganization.id == org_id))
            await cleanup_db.execute(delete(User).where(User.id == owner.id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_get_player_real_record_and_tenant_isolation(db):
    user = await _create_user(db, "p_regtest_player_user")
    repo = TourismSportsRepository(db)
    player = await repo.create_player_profile(
        tenant_id=TENANT_ID, user_id=user.id, sport_category=SportCategory.PHYSICAL,
    )
    player_id = player.id
    service = TourismSportsService(db)
    try:
        result = await service.get_player(player_id, TENANT_ID)
        assert result.id == player_id

        with pytest.raises(NotFoundError):
            await service.get_player(player_id, OTHER_TENANT_ID)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(PlayerProfile).where(PlayerProfile.id == player_id))
            await cleanup_db.execute(delete(User).where(User.id == user.id))
            await cleanup_db.commit()
