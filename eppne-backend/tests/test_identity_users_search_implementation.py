"""
regression test لجلسة `achievements-admin-dashboard-frontend-implementation`
(2026-09-15) — إضافة GET /identity/users/search?q=&limit= (دومين identity،
صفر لمس لأي كود achievements). راجع:
.claude/reports/achievements-stats-endpoints-implementation-session-log.md

السياق: فورم المنح اليدوي في لوحة achievements الجديدة محتاج "بحث
بالاسم/الإيميل" عن مستخدم — لا يوجد أي endpoint بحث/قائمة مستخدمين شغّال
في الباك إند إطلاقًا قبل هذه الجلسة (تأكَّد بالبحث الكامل في الكودبيز).
**ملاحظة منفصلة تمامًا، غير مُصلَحة هنا عمدًا:** `entity-representatives.tsx`
(فرونت إند) بينادي `/users/search` (بلا `/identity` prefix) — endpoint غير
موجود إطلاقًا، بج قديم منفصل خارج نطاق هذه الجلسة.

يغطي:
1) البحث الجزئي (ILIKE) على username أو email، بحساسية أحرف كبيرة/صغيرة.
2) عزل التينانت — مستخدم من تينانت تاني بنفس نص البحث ميظهرش.
3) الحماية عبر HTTP فعلي: `is_admin_or_above` (نفس نمط
   `GET /identity/invitations?scope=tenant` في نفس الدومين بالحرف — مش
   `get_current_superuser` الأقوى المستخدَم في achievements) — مستخدم
   عادي (USER) يترفض بـ403، ADMIN يُسمح له.
"""
import uuid

import pytest
import httpx
from sqlalchemy import delete, update

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.core.security import get_current_active_user
from app.core.enums import SystemRole

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

TENANT_ID = 1
OTHER_TENANT_ID = 16  # "TEST_TENANT_B" — تينانت throwaway موجود فعليًا في DB (تينانت 2 مش موجود)


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str, tenant_id: int = TENANT_ID) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, tenant_id).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


@pytest.mark.asyncio
async def test_search_users_matches_partial_username_or_email_with_tenant_isolation(db):
    unique_marker = f"regtestsearch{_suffix()}"
    target = await _create_user(db, f"p_{unique_marker}")
    other_tenant_user = await _create_user(db, f"p_{unique_marker}_other_tenant", tenant_id=OTHER_TENANT_ID)
    unrelated = await _create_user(db, "p_regtest_search_unrelated")

    service = UserService(db, TENANT_ID)
    try:
        # بحث جزئي بالاسم (username)
        by_username = await service.search_users(unique_marker, limit=10)
        assert {u.id for u in by_username} == {target.id}

        # بحث جزئي بالإيميل (نفس marker موجود جوّه الإيميل كمان)
        by_email_fragment = await service.search_users(unique_marker[:10], limit=10)
        assert target.id in {u.id for u in by_email_fragment}

        # عزل التينانت — نفس الـmarker بالظبط في تينانت تاني، مش هيظهر من تينانت 1
        assert other_tenant_user.id not in {u.id for u in by_username}

        # نص بحث غير مرتبط — صفر نتائج تحوي المستخدمين المستهدفين
        no_match = await service.search_users(f"nonexistent-{_suffix()}", limit=10)
        assert target.id not in {u.id for u in no_match}
        assert unrelated.id not in {u.id for u in no_match}
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(
                delete(User).where(User.id.in_([target.id, other_tenant_user.id, unrelated.id]))
            )
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_search_users_endpoint_requires_admin_or_above_via_http(db):
    regular_user = await _create_user(db, "p_regtest_search_regular")
    admin_user = await _create_user(db, "p_regtest_search_admin")
    marker = f"regtestsearchhttp{_suffix()}"
    findable = await _create_user(db, f"p_{marker}")

    try:
        await db.execute(update(User).where(User.id == admin_user.id).values(system_role=SystemRole.ADMIN))
        await db.commit()

        transport = httpx.ASGITransport(app=fastapi_app)

        fastapi_app.dependency_overrides[get_current_active_user] = lambda: regular_user
        try:
            async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
                forbidden_response = await client.get("/api/identity/users/search", params={"q": marker})
        finally:
            fastapi_app.dependency_overrides.pop(get_current_active_user, None)
        assert forbidden_response.status_code == 403, forbidden_response.text[:500]

        fastapi_app.dependency_overrides[get_current_active_user] = lambda: admin_user
        try:
            async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
                allowed_response = await client.get("/api/identity/users/search", params={"q": marker})
        finally:
            fastapi_app.dependency_overrides.pop(get_current_active_user, None)
        assert allowed_response.status_code == 200, allowed_response.text[:500]
        body = allowed_response.json()
        assert len(body) == 1
        assert body[0]["user_id"] == findable.id
        assert body[0]["name"] == findable.username
        assert body[0]["email"] == findable.email
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(
                delete(User).where(User.id.in_([regular_user.id, admin_user.id, findable.id]))
            )
            await cleanup_db.commit()
