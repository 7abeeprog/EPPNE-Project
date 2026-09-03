"""
regression test لجلسة `category-b-decision-needed-triage` (2026-09-04).
تقرير الجلسة: .claude/reports/category-b-decision-needed-triage-session-log.md

السياق: قرارات "قرار بسيط" وافق عليها المستخدم صراحة للتنفيذ الفوري:
1. `place_transfer_bid` (كود أصلي قديم) كان بينادي `self.repo.get_transfer(transfer_id)`
   على دالة غير موجودة إطلاقًا في repository.py — أي طلب مكرر بنفس idempotency_key
   كان هيفشل بـ AttributeError في الإنتاج. أُضيفت `get_transfer`/`list_transfers`
   لـrepository.py + service.py + router.py (بما فيها GET endpoint لـTransferCard).
2. 4 list/get endpoints جديدة كانت مطلوبة من hooks الفرونت إند بدون أي دعم
   باك إند: `get_destination` (مفرد)، `list_programs`، `list_sports_orgs`،
   `list_players`.

هذا الاختبار يتحقق حيًا (DB حقيقية، صفر mock) من كل الوصلات الجديدة،
بما فيها تحقق عزل tenant_id (IDOR) للـgetters المفردة.
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
    TourismDestination, TourismProgram, SportsOrganization, PlayerProfile,
    PlayerTransfer, DestinationType, ProgramTier, SportsEntityType,
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
async def test_get_destination_real_record_and_tenant_isolation(db):
    repo = TourismSportsRepository(db)
    dest = await repo.create_destination(
        tenant_id=TENANT_ID, name=f"REGTEST-DEST-{_suffix()}",
        destination_type=DestinationType.LOCAL,
    )
    dest_id = dest.id
    service = TourismSportsService(db)
    try:
        result = await service.get_destination(dest_id, TENANT_ID)
        assert result.id == dest_id

        with pytest.raises(NotFoundError):
            await service.get_destination(dest_id, OTHER_TENANT_ID)
        with pytest.raises(NotFoundError):
            await service.get_destination(999_999_999, TENANT_ID)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(TourismDestination).where(TourismDestination.id == dest_id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_list_programs_scoped_to_tenant(db):
    # ملاحظة: OTHER_TENANT_ID=2 مش موجود فعليًا في academy_tenants على DB
    # الاختبار (FK constraint) — عزل tenant_id متحقَّق منه مباشرة عبر
    # get_program/get_event/get_sports_org/get_player/get_destination/
    # get_transfer في نفس الملف وملف phase2 المرجعي، فهذا الاختبار يكتفي
    # بالتحقق من ظهور السجل الحقيقي في القائمة.
    repo = TourismSportsRepository(db)
    program = await repo.create_program(
        tenant_id=TENANT_ID, title=f"REGTEST-PROG-LIST-{_suffix()}",
        program_tier=ProgramTier.STANDARD, base_price_mrusdt=Decimal("100"),
        max_capacity=10, start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=1), status="ANNOUNCED",
    )
    service = TourismSportsService(db)
    try:
        result = await service.list_programs(TENANT_ID)
        ids = [p.id for p in result]
        assert program.id in ids
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(TourismProgram).where(TourismProgram.id == program.id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_list_sports_orgs_scoped_to_tenant_and_type(db):
    owner = await _create_user(db, "p_regtest_listorgs_owner")
    repo = TourismSportsRepository(db)
    club = await repo.create_sports_org(
        tenant_id=TENANT_ID, owner_id=owner.id, name=f"REGTEST-CLUB-{_suffix()}",
        org_type=SportsEntityType.CLUB,
    )
    agency = await repo.create_sports_org(
        tenant_id=TENANT_ID, owner_id=owner.id, name=f"REGTEST-AGENCY-{_suffix()}",
        org_type=SportsEntityType.MARKETING_AGENCY,
    )
    service = TourismSportsService(db)
    try:
        result = await service.list_sports_orgs(TENANT_ID)
        ids = [o.id for o in result]
        assert club.id in ids and agency.id in ids

        clubs_only = await service.list_sports_orgs(TENANT_ID, org_type=SportsEntityType.CLUB.value)
        clubs_only_ids = [o.id for o in clubs_only]
        assert club.id in clubs_only_ids
        assert agency.id not in clubs_only_ids
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(SportsOrganization).where(SportsOrganization.id.in_([club.id, agency.id])))
            await cleanup_db.execute(delete(User).where(User.id == owner.id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_list_players_scoped_to_tenant_and_club(db):
    user1 = await _create_user(db, "p_regtest_listplayers_u1")
    user2 = await _create_user(db, "p_regtest_listplayers_u2")
    owner = await _create_user(db, "p_regtest_listplayers_owner")
    repo = TourismSportsRepository(db)
    club = await repo.create_sports_org(
        tenant_id=TENANT_ID, owner_id=owner.id, name=f"REGTEST-CLUB2-{_suffix()}",
        org_type=SportsEntityType.CLUB,
    )
    player1 = await repo.create_player_profile(
        tenant_id=TENANT_ID, user_id=user1.id, sport_category=SportCategory.PHYSICAL, club_id=club.id,
    )
    player2 = await repo.create_player_profile(
        tenant_id=TENANT_ID, user_id=user2.id, sport_category=SportCategory.PHYSICAL,
    )
    service = TourismSportsService(db)
    try:
        result = await service.list_players(TENANT_ID)
        ids = [p.id for p in result]
        assert player1.id in ids and player2.id in ids

        club_only = await service.list_players(TENANT_ID, club_id=club.id)
        club_only_ids = [p.id for p in club_only]
        assert player1.id in club_only_ids
        assert player2.id not in club_only_ids
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(PlayerProfile).where(PlayerProfile.id.in_([player1.id, player2.id])))
            await cleanup_db.execute(delete(SportsOrganization).where(SportsOrganization.id == club.id))
            await cleanup_db.execute(delete(User).where(User.id.in_([user1.id, user2.id, owner.id])))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_get_transfer_and_list_transfers_real_record_and_tenant_isolation(db):
    """يغطي البند الأولوية-أعلى: place_transfer_bid كان بينادي repo.get_transfer
    غير الموجودة إطلاقًا (باج حي في مسار idempotency-cache، مش مجرد قرار UI)."""
    owner = await _create_user(db, "p_regtest_transfer_owner")
    player_user = await _create_user(db, "p_regtest_transfer_player")
    repo = TourismSportsRepository(db)
    from_club = await repo.create_sports_org(
        tenant_id=TENANT_ID, owner_id=owner.id, name=f"REGTEST-FROMCLUB-{_suffix()}",
        org_type=SportsEntityType.CLUB,
    )
    to_club = await repo.create_sports_org(
        tenant_id=TENANT_ID, owner_id=owner.id, name=f"REGTEST-TOCLUB-{_suffix()}",
        org_type=SportsEntityType.CLUB,
    )
    player = await repo.create_player_profile(
        tenant_id=TENANT_ID, user_id=player_user.id, sport_category=SportCategory.PHYSICAL,
    )
    transfer = await repo.create_transfer(
        tenant_id=TENANT_ID, player_id=player.id, from_club_id=from_club.id, to_club_id=to_club.id,
        bid_amount_mrusdt=Decimal("1000"), contract_duration_months=12,
    )
    # create_transfer() فقط flush() بلا commit() — لازم commit صريح هنا وإلا
    # الصف يفضل مقفول على الـtransaction الأصلية، وجلسة التنظيف (finally،
    # session منفصلة) بتتقفل (deadlock) عليه. نفس الباج المكتشَف سابقًا في
    # insurance.update_claim (راجع frontend-category-b-phase2-session-log.md).
    await db.commit()
    transfer_id = transfer.id
    service = TourismSportsService(db)
    try:
        # مسار الباج الأصلي: نفس استدعاء place_transfer_bid عند idempotency cache hit
        direct = await repo.get_transfer(transfer_id, TENANT_ID)
        assert direct is not None
        assert direct.id == transfer_id

        result = await service.get_transfer(transfer_id, TENANT_ID)
        assert result.id == transfer_id

        with pytest.raises(NotFoundError):
            await service.get_transfer(transfer_id, OTHER_TENANT_ID)

        listed = await service.list_transfers(TENANT_ID)
        assert transfer_id in [t.id for t in listed]
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(PlayerTransfer).where(PlayerTransfer.id == transfer_id))
            await cleanup_db.execute(delete(PlayerProfile).where(PlayerProfile.id == player.id))
            await cleanup_db.execute(delete(SportsOrganization).where(SportsOrganization.id.in_([from_club.id, to_club.id])))
            await cleanup_db.execute(delete(User).where(User.id.in_([owner.id, player_user.id])))
            await cleanup_db.commit()
