"""
smoke test: identity_router بعد نقله من تغطية test_auth_router_protection.py
(المحذوف مع دومين auth في Phase 4).
- /api/identity/register, /api/identity/login, /api/identity/logout,
  /api/identity/refresh لازم يفضلوا عامين (من غير get_current_active_user).
- /api/identity/me, /api/identity/sessions, /api/identity/revoke-all,
  /api/identity/me/password لازم يعتمدوا على get_current_active_user.

**تحديث (جلسة security-deps-unification، راجع
.claude/reports/security-deps-unification-session-log.md §4):**
بعد توحيد core/security.py + api/deps.py، أصبح app/api/deps.py مجرد
re-export shim شفاف فوق app/core/security.py — `weak_get_current_active_user`
(المستورَدة من app.api.deps) و`strong_get_current_active_user` (من
app.core.security) أصبحتا **نفس كائن الدالة بالحرف** (`is` صحيحة). النسخة
الأضعف التي لم تكن تفحص session_version/tenant لم تعد موجودة ككائن منفصل
إطلاقًا — لذلك التأكيدات القديمة ("weak لازم متكونش في calls") أصبحت
منطقيًا معكوسة وكانت ستفشل حتمًا؛ استُبدلت بتأكيد إيجابي مباشر يثبت نجاح
التوحيد (`weak is strong`)، بدل تكرار فحص عدم الوجود لكل مسار.

**إضافة جديدة في نفس الجلسة:** اختبارات حية مباشرة لـ`get_current_user`
الموحَّدة (٤ سيناريوهات: توكن صالح عبر Header، صالح عبر Cookie، منتهي،
مُبطَل عبر session_version، وtenant غير مطابق) + `get_current_user_optional`
(تثبت أنها الآن تفحص session_version أيضًا بدل تجاهله بصمت كما كانت نسخة
deps.py القديمة).
"""
import uuid
from datetime import timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.main import fastapi_app
from app.core.security import (
    get_current_active_user as strong_get_current_active_user,
    get_current_user,
    get_current_user_optional,
    create_access_token,
)
from app.api.deps import get_current_active_user as weak_get_current_active_user
from app.core.errors import AuthenticationError
from app.domains.identity.service import UserService
from app.domains.identity.repository import UserRepository
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User
from route_utils import find_route, direct_dependency_calls

PUBLIC_PATHS = ["/api/identity/register", "/api/identity/login", "/api/identity/logout", "/api/identity/refresh"]
PROTECTED_PATHS = ["/api/identity/me", "/api/identity/sessions", "/api/identity/revoke-all", "/api/identity/me/password"]

TENANT_ID = 1
WRONG_TENANT_ID = 999_999


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"SECDEPS-{prefix}-{suffix}",
    )


async def _cleanup(db, user_id: int):
    from sqlalchemy import delete
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()


def test_shim_re_export_is_transparent():
    """التحقق الأساسي من نجاح الدمج: deps.py لم يعد يحتوي نسخة منطق
    منفصلة - فقط إعادة تصدير لنفس الكائن من core.security."""
    assert weak_get_current_active_user is strong_get_current_active_user, (
        "app.api.deps.get_current_active_user لازم يكون نفس كائن "
        "app.core.security.get_current_active_user بالحرف بعد تحويل "
        "deps.py لـshim - راجع تقرير جلسة security-deps-unification"
    )


def test_public_identity_endpoints_have_no_active_user_dependency():
    for path in PUBLIC_PATHS:
        route = find_route(fastapi_app, path)
        calls = direct_dependency_calls(route)
        assert strong_get_current_active_user not in calls, f"{path} لازم يفضل عام (public)"


def test_protected_identity_endpoints_require_active_user():
    for path in PROTECTED_PATHS:
        route = find_route(fastapi_app, path)
        calls = direct_dependency_calls(route)
        assert strong_get_current_active_user in calls, (
            f"{path} لازم يعتمد على get_current_active_user (core.security، "
            f"وهي نفس الكائن اللي كانت تُستورَد من api.deps قبل الدمج - "
            f"راجع test_shim_re_export_is_transparent)"
        )


# ============================================================
# اختبارات حية جديدة: get_current_user الموحَّدة (session-deps-unification)
# ============================================================

@pytest.mark.asyncio
async def test_get_current_user_valid_token_via_header(db):
    """توكن صالح عبر Authorization Header (Bearer) → يرجع المستخدم الصحيح."""
    user = await _create_user(db, "secdeps_valid_header")
    try:
        token = create_access_token(data={"sub": str(user.id), "sv": user.session_version, "tenant_id": TENANT_ID})
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        result = await get_current_user(credentials=creds, db=db, cookie_token=None)
        assert result.id == user.id
    finally:
        await _cleanup(db, user.id)


@pytest.mark.asyncio
async def test_get_current_user_valid_token_via_cookie(db):
    """توكن صالح عبر HttpOnly Cookie (بلا Header) → يرجع المستخدم الصحيح."""
    user = await _create_user(db, "secdeps_valid_cookie")
    try:
        token = create_access_token(data={"sub": str(user.id), "sv": user.session_version, "tenant_id": TENANT_ID})

        result = await get_current_user(credentials=None, db=db, cookie_token=token)
        assert result.id == user.id
    finally:
        await _cleanup(db, user.id)


@pytest.mark.asyncio
async def test_get_current_user_expired_token_rejected(db):
    """توكن منتهي الصلاحية → 401 Token expired."""
    user = await _create_user(db, "secdeps_expired")
    try:
        token = create_access_token(
            data={"sub": str(user.id), "sv": user.session_version, "tenant_id": TENANT_ID},
            expires_delta=timedelta(seconds=-10),
        )
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds, db=db, cookie_token=None)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()
    finally:
        await _cleanup(db, user.id)


@pytest.mark.asyncio
async def test_get_current_user_revoked_session_rejected(db):
    """توكن بـsession_version قديم بعد 'تسجيل خروج من كل الأجهزة'
    (increment_session_version) → يُرفض بـ'Session has been revoked'.
    هذا هو التحقق الحي المباشر لإغلاق الفجوة الأمنية الأصلية لهذه الجلسة:
    قبل الدمج، أي endpoint كان يستخدم app.api.deps.get_current_user
    (النسخة القديمة) كان يقبل هذا التوكن رغم إبطاله."""
    user = await _create_user(db, "secdeps_revoked")
    try:
        old_sv = user.session_version
        token = create_access_token(data={"sub": str(user.id), "sv": old_sv, "tenant_id": TENANT_ID})

        repo = UserRepository(db)
        await repo.increment_session_version(user.id, TENANT_ID)

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_user(credentials=creds, db=db, cookie_token=None)
        assert "revoked" in str(exc_info.value).lower() or "revoked" in exc_info.value.message.lower()
    finally:
        await _cleanup(db, user.id)


@pytest.mark.asyncio
async def test_get_current_user_tenant_mismatch_rejected(db):
    """توكن بـtenant_id مختلف عن tenant المستخدم الحقيقي → يُرفض.
    ملاحظة (راجع تقرير الجلسة §0): UserRepository.get_by_id تفلتر
    tenant_id في الاستعلام نفسه، فالنتيجة الفعلية هنا 'User not found'
    (AuthenticationError) وليس رسالة 'Tenant mismatch' تحديدًا - الفحص
    الثاني في get_current_user دفاع إضافي صريح، نادرًا ما يكون هو من
    يرفع الاستثناء عمليًا. المهم المُثبَت هنا: **عزل tenant يعمل فعليًا
    من طرف لطرف** - توكن مزوَّر بـtenant خاطئ لا يمرّ مهما كان مصدر الرفض."""
    user = await _create_user(db, "secdeps_tenant_mismatch")
    try:
        token = create_access_token(
            data={"sub": str(user.id), "sv": user.session_version, "tenant_id": WRONG_TENANT_ID}
        )
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(AuthenticationError):
            await get_current_user(credentials=creds, db=db, cookie_token=None)
    finally:
        await _cleanup(db, user.id)


@pytest.mark.asyncio
async def test_get_current_user_optional_returns_none_without_token(db):
    """بلا أي توكن (لا Header ولا Cookie) → None، بلا أي استثناء."""
    result = await get_current_user_optional(credentials=None, db=db, cookie_token=None)
    assert result is None


@pytest.mark.asyncio
async def test_get_current_user_optional_returns_user_for_valid_token(db):
    """توكن صالح → نفس سلوك get_current_user الإجبارية، ترجع المستخدم."""
    user = await _create_user(db, "secdeps_optional_valid")
    try:
        token = create_access_token(data={"sub": str(user.id), "sv": user.session_version, "tenant_id": TENANT_ID})
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        result = await get_current_user_optional(credentials=creds, db=db, cookie_token=None)
        assert result is not None and result.id == user.id
    finally:
        await _cleanup(db, user.id)


@pytest.mark.asyncio
async def test_get_current_user_optional_returns_none_for_revoked_session(db):
    """توكن بـsession_version مُبطَل → None (بلا استثناء يظهر للمستخدم
    الضيف)، **وليس قبولًا صامتًا كما كانت نسخة api/deps.py القديمة** -
    هذا يثبت أن دعم 'المستخدم الاختياري' الموسَّع (القرار المعتمَد في
    §6 من تقرير الجلسة) بقى يفحص session_version فعليًا في الثلاثة
    راوترات التي تستخدمها لنقاط دخول الضيوف
    (communications/sovereign_entities/invitations)."""
    user = await _create_user(db, "secdeps_optional_revoked")
    try:
        old_sv = user.session_version
        token = create_access_token(data={"sub": str(user.id), "sv": old_sv, "tenant_id": TENANT_ID})

        repo = UserRepository(db)
        await repo.increment_session_version(user.id, TENANT_ID)

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        result = await get_current_user_optional(credentials=creds, db=db, cookie_token=None)
        assert result is None
    finally:
        await _cleanup(db, user.id)
