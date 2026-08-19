"""
regression test لجلسة `invitations-savepoint-leak` (Backlog #11a).
تقرير الجلسة الأصلية: .claude/reports/invitations-savepoint-leak-session-log.md

السبب الجذري (كان): `_create_user_from_invitation` كانت تُستدعى *جوه*
`self.db.begin_nested()` في `accept_invitation`، و`UserRepository.create()`/
`WalletRepository.create()` بتعمل `commit()` مباشر — ده كان بيقفل الـSAVEPOINT
فيسيب يوزر حقيقي على القرص بلا محفظة لو أي كود بعده كراش.

الإصلاح المُطبَّق (`invitations/service.py`):
1. نقل `_create_user_from_invitation` بره `begin_nested()`.
2. تثبيت idempotency_key الممرَّر لـ`UserService.register()` بصيغة
   `INV-ACCEPT-T{tenant_id}-{invitation_id}` بدل uuid عشوائي، لضمان أن
   إعادة المحاولة بعد فشل جزئي لا تُنشئ يوزر مكرَّر.

هذا الملف يغطي نفس السيناريوهين اللي اتحققوا حيًا في الجلسة الأصلية:
قبول نظيف، وفشل جزئي متعمَّد بعد إنشاء اليوزر ثم إعادة محاولة.
"""
import uuid

import pytest
from sqlalchemy import select, delete

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels (نفس نمط test_ai_routing_security.py)
from app.domains.invitations.service import InvitationsService
from app.domains.invitations.repository import InvitationsRepository
from app.domains.invitations.models import (
    SovereignInvitation, Lead, CustomerInteraction,
    InvitationType, InvitationTargetType, CampaignType, InvitationStatus,
)
from app.domains.identity.models import User
from app.domains.finance.models import Wallet

# tenant_id=1 = "Local Test Tenant" — نفس المستأجر throwaway المستخدم في
# التحقق الحي الأصلي (اختير هنا لأن له اشتراك SaaS فعلي في قاعدة البيانات،
# رغم أنه بدون feature "crm" — ولذلك بيتم تخطي _check_saas_limits أدناه،
# بنفس الطريقة اللي استخدمها سكريبت التحقق الأصلي، لأنها منطق غير مرتبط
# (Backlog #9) موثَّق مسبقًا في التقرير).
TENANT_ID = 1


async def _noop_check_saas_limits(self, tenant_id, feature="crm"):
    return None, []


def _unique_suffix() -> str:
    return uuid.uuid4().hex[:10]


# fixture "db" مُعرَّفة مركزيًا في tests/conftest.py (مشتركة لكل ملفات
# regression-tests-backfill) — بتوفر جلسة AsyncSessionLocal حقيقية، وبتتعامل
# مع مشكلة event loop/connection pool على Windows في الـteardown.


async def _create_sent_invitation(db, title: str) -> SovereignInvitation:
    repo = InvitationsRepository(db)
    inv = await repo.create_invitation(
        tenant_id=TENANT_ID,
        invitation_type=InvitationType.GENERAL,
        target_type=InvitationTargetType.PERSON,
        campaign_type=CampaignType.SERVICE,
        campaign_id=999999,
        title=title,
        status=InvitationStatus.SENT,
    )
    await db.commit()
    return inv


async def _cleanup(db, email: str, invitation_id: int):
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user:
        await db.execute(delete(Wallet).where(Wallet.user_id == user.id))
        await db.execute(delete(CustomerInteraction).where(CustomerInteraction.user_id == user.id))
        await db.execute(delete(Lead).where(Lead.converted_user_id == user.id))
        await db.execute(delete(User).where(User.id == user.id))
    await db.execute(delete(SovereignInvitation).where(SovereignInvitation.id == invitation_id))
    await db.commit()


@pytest.mark.asyncio
async def test_accept_invitation_clean_creates_user_with_wallet(db, monkeypatch):
    """قبول دعوة نظيف (بلا أي فشل) لازم ينتج يوزر واحد بمحفظة كاملة،
    ودعوة ACCEPTED — مش يوزر يتيم بلا محفظة زي الباج الأصلي."""
    monkeypatch.setattr(InvitationsService, "_check_saas_limits", _noop_check_saas_limits)

    suffix = _unique_suffix()
    email = f"p_regtest_savepoint_clean_{suffix}@eppne.com"
    invitation = await _create_sent_invitation(db, f"REGTEST-SAVEPOINT-CLEAN-{suffix}")
    service = InvitationsService(db)

    try:
        result = await service.accept_invitation(
            invitation_id=invitation.id,
            tenant_id=TENANT_ID,
            accept_data={"email": email, "name": "Regression Test", "password": "TempPass123!"},
        )

        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        assert user is not None, "اليوزر المتوقع مش موجود على القرص"

        wallet = (await db.execute(select(Wallet).where(Wallet.user_id == user.id))).scalar_one_or_none()
        assert wallet is not None, "اليوزر اتعمل بلا محفظة — نفس الباج الأصلي رجع"

        refreshed = await InvitationsRepository(db).get_invitation(invitation.id, TENANT_ID)
        assert refreshed is not None
        assert refreshed.status == InvitationStatus.ACCEPTED
        assert refreshed.current_uses == 1
        assert result["user_id"] == user.id
    finally:
        await _cleanup(db, email, invitation.id)


@pytest.mark.asyncio
async def test_accept_invitation_retry_after_partial_failure_is_idempotent(db, monkeypatch):
    """محاولة أولى تفشل عمدًا بعد إنشاء اليوزر (جوه begin_nested) — لازم
    اليوزر يفضل موجود بمحفظة كاملة رغم الفشل. إعادة المحاولة لازم تستخدم
    نفس اليوزر (idempotency_key ثابت) بدل ما تنشئ واحد مكرَّر، وتكمّل قبول
    الدعوة بنجاح (current_uses=1 مش 2)."""
    monkeypatch.setattr(InvitationsService, "_check_saas_limits", _noop_check_saas_limits)

    suffix = _unique_suffix()
    email = f"p_regtest_savepoint_retry_{suffix}@eppne.com"
    invitation = await _create_sent_invitation(db, f"REGTEST-SAVEPOINT-RETRY-{suffix}")
    service = InvitationsService(db)
    accept_data = {"email": email, "name": "Regression Retry", "password": "TempPass123!"}

    original_create_lead = InvitationsRepository.create_lead
    call_state = {"failed_once": False}

    async def flaky_create_lead(self, **kwargs):
        if not call_state["failed_once"]:
            call_state["failed_once"] = True
            raise RuntimeError("SIMULATED-FAILURE-AFTER-USER-CREATION")
        return await original_create_lead(self, **kwargs)

    monkeypatch.setattr(InvitationsRepository, "create_lead", flaky_create_lead)

    try:
        with pytest.raises(RuntimeError, match="SIMULATED-FAILURE-AFTER-USER-CREATION"):
            await service.accept_invitation(
                invitation_id=invitation.id, tenant_id=TENANT_ID, accept_data=accept_data,
            )

        user_after_first = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        assert user_after_first is not None, "اليوزر لازم يتعمل ويتحفظ حتى لو المحاولة فشلت بعده"

        wallet_after_first = (
            await db.execute(select(Wallet).where(Wallet.user_id == user_after_first.id))
        ).scalar_one_or_none()
        assert wallet_after_first is not None, "اليوزر اتعمل بلا محفظة بعد الفشل الجزئي — نفس الباج الأصلي"

        invitation_after_first = await InvitationsRepository(db).get_invitation(invitation.id, TENANT_ID)
        assert invitation_after_first is not None
        assert invitation_after_first.status == InvitationStatus.SENT, (
            "الدعوة لازم تفضل SENT بعد فشل المحاولة الأولى (لسه معلَّقة، مش ACCEPTED)"
        )

        result = await service.accept_invitation(
            invitation_id=invitation.id, tenant_id=TENANT_ID, accept_data=accept_data,
        )

        users = (await db.execute(select(User).where(User.email == email))).scalars().all()
        assert len(users) == 1, "إعادة المحاولة أنشأت يوزر مكرَّر بدل استخدام نفس اليوزر"
        assert result["user_id"] == user_after_first.id

        refreshed = await InvitationsRepository(db).get_invitation(invitation.id, TENANT_ID)
        assert refreshed is not None
        assert refreshed.status == InvitationStatus.ACCEPTED
        assert refreshed.current_uses == 1, "current_uses لازم يبقى 1 مش 2 رغم محاولتين"
    finally:
        await _cleanup(db, email, invitation.id)
