"""
regression tests لجلسة `invitations-batch0b1-close-hole` (الدفعة 0-B1، المرحلة 1).
تقرير الجلسة: .claude/reports/invitations-batch0b1-close-hole-session-log.md

الخلفية: `POST /invitations/{id}/accept` كان (1) للمجهول ينشئ حسابًا تحت مستأجر يحدده
هيدر `X-Tenant-ID` غير الموثوق، و(2) للمسجَّل يكتب في مستأجر الهيدر لا مستأجر المستخدم.
بعد الإصلاح:
  - المجهول (أو توكن غير صالح/منتهٍ) => 401 + `WWW-Authenticate: Bearer` +
    code=REGISTRATION_VIA_INVITATION_REQUIRED، قبل أي وصول للـDB أو بوابة SaaS أو بحث عن الدعوة،
    وبجسم متطابق لدعوة موجودة وغير موجودة، والهيدر يُتجاهَل.
  - المسجَّل => المستأجر = `current_user.tenant_id` فقط؛ دعوة مستأجر آخر => 404.
  - `_create_user_from_invitation` (وكلمة المرور الافتراضية) حُذفت.

كل البيانات throwaway بأسماء `p_gw_*` وتُحذف في `finally` (يُتحقق بلقطة عدّادات جداول DB
قبل/بعد التشغيل). لا تعتمد على صفوف SaaS المؤقتة: `_check_saas_limits` مُعطَّل بنفس نمط
الاختبارات القائمة، وفي مسار المجهول يُثبَت أنه لم يُستدعَ أصلًا.

ملاحظة تقنية: تُلتقَط المعرّفات كأعداد صحيحة فورًا (كائنات ORM تنتهي صلاحيتها بعد rollback/commit
ولا يجوز lazy-load في سياق async)، وتُقرأ حالة الدعوة بأعمدة مباشرة لا بكائن من خريطة الهوية
(الطلب عبر HTTP يكتب من جلسة أخرى).
"""
import uuid
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import delete, func, select

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels
from app.core.errors import NotFoundError
from app.core.security import create_access_token
from app.domains.finance.models import Wallet
from app.domains.identity.models import User
from app.domains.identity.schemas import UserCreate
from app.domains.identity.service import UserService
from app.domains.invitations.models import (
    CampaignType, CustomerInteraction, InvitationStatus, InvitationTargetType, InvitationType,
    Lead, SovereignInvitation,
)
from app.domains.invitations.repository import InvitationsRepository
from app.domains.invitations.router import _REGISTRATION_VIA_INVITATION_REQUIRED_MESSAGE
from app.domains.invitations.service import InvitationsService

TENANT_A = 1    # المستأجر العام للتسجيل
TENANT_B = 16   # TEST_TENANT_B
ACCEPT_PATH = "/api/invitations/{}/accept"
EXPECTED_401_BODY = {
    "detail": _REGISTRATION_VIA_INVITATION_REQUIRED_MESSAGE,
    "code": "REGISTRATION_VIA_INVITATION_REQUIRED",
}


async def _noop_check_saas_limits(self, tenant_id, feature="crm"):
    return None


def _sfx() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, suffix: str, label: str) -> User:
    svc = UserService(db, TENANT_A)
    return await svc.register(
        UserCreate(
            username=f"p_gw_gateway_{label}_{suffix}",
            email=f"p_gw_gateway_{label}_{suffix}@eppne.com",
            password="Pgw-Gateway-Test-9a",
        ),
        f"P-GW-GATEWAY-{label}-{suffix}",
    )


async def _create_sent_invitation(db, tenant_id: int, title: str) -> SovereignInvitation:
    inv = await InvitationsRepository(db).create_invitation(
        tenant_id=tenant_id,
        invitation_type=InvitationType.GENERAL,
        target_type=InvitationTargetType.PERSON,
        campaign_type=CampaignType.SERVICE,
        campaign_id=999999,
        title=title,
        status=InvitationStatus.SENT,
    )
    await db.commit()
    return inv


async def _cleanup(db, user_ids, invitation_ids):
    await db.rollback()
    refs = [f"INV-{i}" for i in invitation_ids]
    lead_ids = []
    if refs:
        lead_ids += list((await db.execute(select(Lead.id).where(Lead.source_reference.in_(refs)))).scalars().all())
    if user_ids:
        lead_ids += list((await db.execute(select(Lead.id).where(Lead.converted_user_id.in_(user_ids)))).scalars().all())
        await db.execute(delete(CustomerInteraction).where(CustomerInteraction.user_id.in_(user_ids)))
    if lead_ids:
        await db.execute(delete(CustomerInteraction).where(CustomerInteraction.lead_id.in_(lead_ids)))
        await db.execute(delete(Lead).where(Lead.id.in_(lead_ids)))
    if user_ids:
        await db.execute(delete(Wallet).where(Wallet.user_id.in_(user_ids)))
        await db.execute(delete(User).where(User.id.in_(user_ids)))
    if invitation_ids:
        await db.execute(delete(SovereignInvitation).where(SovereignInvitation.id.in_(invitation_ids)))
    await db.commit()


async def _leads_for(db, invitation_id: int):
    return list((await db.execute(select(Lead).where(Lead.source_reference == f"INV-{invitation_id}"))).scalars().all())


async def _invitation_state(db, invitation_id: int, tenant_id: int):
    row = (await db.execute(
        select(SovereignInvitation.status, SovereignInvitation.current_uses).where(
            SovereignInvitation.id == invitation_id, SovereignInvitation.tenant_id == tenant_id,
        )
    )).one()
    return row[0], row[1]


def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=fastapi_app), base_url="http://localhost")


def _bearer(user_id: int, session_version: int) -> dict:
    token = create_access_token(
        {"sub": str(user_id), "sv": session_version, "tenant_id": TENANT_A}, user_tenant_id=TENANT_A,
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# (أ) قبول مسجَّل ضمن نفس المستأجر
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_a_registered_same_tenant_accept_creates_lead_and_marks_accepted(db, monkeypatch):
    monkeypatch.setattr(InvitationsService, "_check_saas_limits", _noop_check_saas_limits)
    sfx = _sfx()
    user_ids, inv_ids = [], []
    try:
        user = await _create_user(db, sfx, "a")
        uid = user.id
        user_ids.append(uid)
        inv = await _create_sent_invitation(db, TENANT_A, f"p_gw_gateway_a_{sfx}")
        inv_id = inv.id
        inv_ids.append(inv_id)
        users_before = (await db.execute(select(func.count()).select_from(User))).scalar_one()

        result = await InvitationsService(db).accept_invitation(
            invitation_id=inv_id, tenant_id=TENANT_A,
            accept_data={"email": f"p_gw_gateway_a_lead_{sfx}@example.com", "name": "p_gw"},
            user_id=uid,
        )

        leads = await _leads_for(db, inv_id)
        assert len(leads) == 1
        assert leads[0].converted_user_id == uid and leads[0].tenant_id == TENANT_A
        assert (await _invitation_state(db, inv_id, TENANT_A)) == (InvitationStatus.ACCEPTED, 1)
        assert result["user_id"] == uid and result["lead_id"] == leads[0].id
        users_after = (await db.execute(select(func.count()).select_from(User))).scalar_one()
        assert users_after == users_before, "accept لا يجب أن ينشئ أي يوزر"
    finally:
        await _cleanup(db, user_ids, inv_ids)


# ---------------------------------------------------------------------------
# (ب) دعوة مستأجر آخر => NotFoundError في الاتجاهين، بلا كتابة
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("invitation_tenant,caller_tenant", [(TENANT_A, TENANT_B), (TENANT_B, TENANT_A)])
async def test_b_cross_tenant_accept_is_not_found_and_writes_nothing(db, monkeypatch, invitation_tenant, caller_tenant):
    monkeypatch.setattr(InvitationsService, "_check_saas_limits", _noop_check_saas_limits)
    sfx = _sfx()
    inv_ids = []
    try:
        inv = await _create_sent_invitation(db, invitation_tenant, f"p_gw_gateway_b_{invitation_tenant}_{sfx}")
        inv_id = inv.id
        inv_ids.append(inv_id)
        with pytest.raises(NotFoundError):
            await InvitationsService(db).accept_invitation(
                invitation_id=inv_id, tenant_id=caller_tenant,
                accept_data={"email": f"p_gw_gateway_b_{sfx}@example.com", "name": "p_gw"},
                user_id=-1,  # لا يُستخدم: يفشل قبل أي كتابة
            )
        await db.rollback()
        assert await _leads_for(db, inv_id) == []
        assert (await _invitation_state(db, inv_id, invitation_tenant)) == (InvitationStatus.SENT, 0)
    finally:
        await _cleanup(db, [], inv_ids)


# ---------------------------------------------------------------------------
# (ج) المجهول => 401 قبل أي DB/بوابة SaaS/بحث، وجسم متطابق لموجودة وغير موجودة،
#     وكذلك لتوكن تالف/منتهٍ/كوكي تالف
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_c_anonymous_accept_401_before_any_lookup_and_identical_bodies(db, monkeypatch):
    calls = []

    async def _spy_gate(self, tenant_id, feature="crm"):
        calls.append(("saas_gate", tenant_id))

    real_get = InvitationsRepository.get_invitation

    async def _spy_get(self, inv_id, tenant_id):
        calls.append(("get_invitation", inv_id))
        return await real_get(self, inv_id, tenant_id)

    monkeypatch.setattr(InvitationsService, "_check_saas_limits", _spy_gate)
    monkeypatch.setattr(InvitationsRepository, "get_invitation", _spy_get)

    sfx = _sfx()
    email = f"p_gw_gateway_c_{sfx}@eppne.com"
    body = {"email": email, "password": "Pgw-Gateway-Test-9a", "name": "p_gw"}
    inv_ids = []
    expired = create_access_token(
        {"sub": "1", "sv": 0, "tenant_id": TENANT_A}, expires_delta=timedelta(seconds=-60), user_tenant_id=TENANT_A,
    )
    try:
        inv = await _create_sent_invitation(db, TENANT_B, f"p_gw_gateway_c_{sfx}")
        inv_id = inv.id
        inv_ids.append(inv_id)
        calls.clear()  # الاستدعاءات أثناء الإعداد لا تُحسب
        variants = [
            {},                                   # بلا هيدر
            {"X-Tenant-ID": str(TENANT_B)},       # مستأجر الدعوة
            {"X-Tenant-ID": str(TENANT_A)},
            {"Authorization": "Bearer not-a-jwt"},
            {"Authorization": f"Bearer {expired}"},
            {"Cookie": "access_token=not-a-jwt"},
        ]
        async with _client() as client:
            for headers in variants:
                r_exist = await client.post(ACCEPT_PATH.format(inv_id), json=body, headers=headers)
                r_ghost = await client.post(ACCEPT_PATH.format(999999999), json=body, headers=headers)
                for r in (r_exist, r_ghost):
                    assert r.status_code == 401, (headers, r.status_code, r.text)
                    assert r.headers["www-authenticate"] == "Bearer"
                    assert r.json() == EXPECTED_401_BODY
                assert r_exist.content == r_ghost.content, f"جسمان مختلفان => تسريب وجود الدعوة ({headers})"
                assert r_exist.headers["content-type"] == r_ghost.headers["content-type"]

        assert calls == [], f"المجهول لمس بوابة SaaS/بحث الدعوة: {calls}"
        assert (await db.execute(select(User).where(User.email == email))).scalar_one_or_none() is None
        assert await _leads_for(db, inv_id) == []
        assert (await _invitation_state(db, inv_id, TENANT_B)) == (InvitationStatus.SENT, 0)
    finally:
        await _cleanup(db, [], inv_ids)


# ---------------------------------------------------------------------------
# (د) هيدر X-Tenant-ID تالف/غريب لا يغيّر شيئًا (لا 422 ولا 500)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("header_value", ["abc", "999999", "-5", "1.5", "16; DROP"])
async def test_d_malformed_tenant_header_is_ignored_on_anonymous_path(header_value):
    async with _client() as client:
        r = await client.post(
            ACCEPT_PATH.format(1), json={"name": "p_gw"}, headers={"X-Tenant-ID": header_value},
        )
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"
    assert r.json() == EXPECTED_401_BODY


# ---------------------------------------------------------------------------
# (هـ) الدالة المحذوفة لم تعد موجودة
# ---------------------------------------------------------------------------
def test_e_create_user_from_invitation_is_removed():
    assert not hasattr(InvitationsService, "_create_user_from_invitation")


# ---------------------------------------------------------------------------
# (و) `user_id`/`tenant_id` داخل الجسم تُتجاهَل؛ الفاعل والمستأجر من current_user فقط
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f_body_user_id_and_tenant_id_are_ignored_for_authenticated_caller(db, monkeypatch):
    monkeypatch.setattr(InvitationsService, "_check_saas_limits", _noop_check_saas_limits)
    sfx = _sfx()
    user_ids, inv_ids = [], []
    try:
        user_a = await _create_user(db, sfx, "fa")
        a_id, a_sv = user_a.id, user_a.session_version
        user_ids.append(a_id)
        user_b = await _create_user(db, sfx, "fb")
        b_id = user_b.id
        user_ids.append(b_id)
        inv = await _create_sent_invitation(db, TENANT_A, f"p_gw_gateway_f_{sfx}")
        inv_id = inv.id
        inv_ids.append(inv_id)
        async with _client() as client:
            r = await client.post(
                ACCEPT_PATH.format(inv_id),
                headers={**_bearer(a_id, a_sv), "X-Tenant-ID": str(TENANT_B)},
                json={"email": f"p_gw_gateway_f_lead_{sfx}@example.com", "name": "p_gw",
                      "user_id": b_id, "tenant_id": TENANT_B},
            )
        assert r.status_code == 200, r.text
        assert r.json()["user_id"] == a_id
        leads = await _leads_for(db, inv_id)
        assert len(leads) == 1
        assert leads[0].converted_user_id == a_id, "الفاعل أُخذ من الجسم بدل current_user"
        assert leads[0].tenant_id == TENANT_A, "المستأجر أُخذ من الهيدر/الجسم بدل current_user"
        assert (await _invitation_state(db, inv_id, TENANT_A)) == (InvitationStatus.ACCEPTED, 1)
    finally:
        await _cleanup(db, user_ids, inv_ids)
