"""
regression test لجلسة `frontend-category-b-item3-components` (2026-09-02/03).

السياق: أثناء بناء `CampaignCard`/`InvitationCard`/`TicketCard` (البند 3)،
اكتشف tsc إن ثلاثة حقول موجودة فعليًا على الموديل (وعلى `types/invitations.ts`
المحلي، وعلى المكوّنات الموجودة أصلاً زي `CampaignStatusBadge`) لكنها
**كانت مفقودة تمامًا من schemas الاستجابة** (Pydantic Response models) —
يعني الـAPI كان بيُسقط هذه الحقول صامتًا من كل استجابة:
- `CampaignResponse.status` (الموديل عنده العمود، الـschema ماكانش بيصدّره)
- `InvitationResponse.current_uses` (نفس الشيء)
- `TicketCreate/TicketResponse.priority` كان `str` عام (regex-validated)
  بدل `Literal["LOW","MEDIUM","HIGH","URGENT"]` دقيق (لا فقدان بيانات هنا،
  بس دقة النوع تحسَّنت لتطابق الفعل الحقيقي المسموح).

هذا الاختبار يتحقق حيًا (DB حقيقية) من أن الحقول الثلاثة تُسلسَل الآن
بشكل صحيح عبر schema الاستجابة الفعلية.
"""
import uuid
from decimal import Decimal
from datetime import datetime

import pytest
from sqlalchemy import delete

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.invitations.repository import InvitationsRepository
from app.domains.invitations.schemas import CampaignResponse, InvitationResponse, TicketResponse
from app.domains.invitations.models import (
    MarketingCampaign, SovereignInvitation, SupportTicket,
    CampaignType, CampaignStatus, InvitationType, InvitationTargetType,
)

TENANT_ID = 1


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


@pytest.mark.asyncio
async def test_campaign_response_includes_status(db):
    creator = await _create_user(db, "p_regtest_inv_schema_campaign")
    repo = InvitationsRepository(db)
    campaign = await repo.create_campaign(
        tenant_id=TENANT_ID, name=f"REGTEST-CAMPAIGN-{_suffix()}",
        campaign_type=CampaignType.SERVICE, start_date=datetime.utcnow(),
        status=CampaignStatus.ACTIVE, created_by=creator.id,
    )
    campaign_id = campaign.id
    try:
        serialized = CampaignResponse.model_validate(campaign)
        assert serialized.status == CampaignStatus.ACTIVE
        await db.commit()  # create_campaign only flush()es — commit explicitly so the
        # finally block's separate cleanup session isn't blocked on this row's lock.
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(MarketingCampaign).where(MarketingCampaign.id == campaign_id))
            await cleanup_db.execute(delete(User).where(User.id == creator.id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_invitation_response_includes_current_uses(db):
    repo = InvitationsRepository(db)
    invitation = await repo.create_invitation(
        tenant_id=TENANT_ID, invitation_type=InvitationType.GENERAL,
        target_type=InvitationTargetType.PERSON, campaign_type=CampaignType.SERVICE,
        campaign_id=1, current_uses=3, max_uses=10,
    )
    invitation_id = invitation.id
    try:
        serialized = InvitationResponse.model_validate(invitation)
        assert serialized.current_uses == 3
        await db.commit()
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(SovereignInvitation).where(SovereignInvitation.id == invitation_id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_ticket_response_priority_is_literal_typed(db):
    repo = InvitationsRepository(db)
    ticket = await repo.create_ticket(
        tenant_id=TENANT_ID, subject=f"REGTEST-TICKET-{_suffix()}",
        description="REGTEST", priority="HIGH",
    )
    ticket_id = ticket.id
    try:
        serialized = TicketResponse.model_validate(ticket)
        assert serialized.priority == "HIGH"
        await db.commit()
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(SupportTicket).where(SupportTicket.id == ticket_id))
            await cleanup_db.commit()
