"""
Regression tests دائمة لجلسة security-deps-unification (توحيد
app/core/security.py + app/api/deps.py). راجع
.claude/reports/security-deps-unification-session-log.md للتقرير الكامل
بكل قرارات الدمج، ولـ§9/§10 تحديدًا للتحقق الحي اليدوي عبر HTTP حقيقي
(uvicorn + curl عبر الشبكة) الذي أثبت إغلاق الثغرتين - هذا الملف يوفر
النسخة الدائمة القابلة لإعادة التشغيل من نفس السيناريوهين، عبر استدعاء
حقيقي لنفس الدوال بنفس البيانات (لا مجرد HTTP يدوي لمرة واحدة).

**سيناريو session_version** (كان §9، `deps.get_current_active_user`
القديمة لا تفحصه إطلاقًا): مُغطًّى بالفعل بالكامل في
`tests/test_identity_router_protection.py`
(`test_get_current_user_revoked_session_rejected` +
`test_get_current_user_optional_returns_none_for_revoked_session`) -
غير مُكرَّر هنا عمدًا.

**سيناريو require_sector** (كان §10، النسخة القديمة في `deps.py` كانت
معطَّلة بالكامل - تعتمد على `getattr(user, "sector", None)` وحقل
`sector` غير موجود على `User` model إطلاقًا، فتسقط دائمًا لـfallback
ثابت `"academy"` لأي مستخدم غير إداري): **هذه هي الفجوة الوحيدة غير
المُغطاة بأي pytest دائم قبل هذا الملف** - كان التحقق حيًّا عبر HTTP
يدوي فقط (§10). الاختبارات هنا تغطيها بالكامل، بنفس ترتيب استدعاء
FastAPI الحقيقي: `get_current_user` يُستدعى أولًا فيضبط الـContextVar
كأثر جانبي حقيقي (بالضبط كما يحدث فعليًا عبر `Depends(get_current_active_user)`
المتداخلة داخل `sector_checker`)، ثم `sector_checker` (ناتج
`require_sector(sector)`) يُستدعى بنفس `current_user`.
"""
import uuid

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import delete, update

from app.main import fastapi_app  # noqa: F401 -- registers all models
from app.core.security import get_current_user, require_sector, create_access_token
from app.core.errors import PermissionDeniedError
from app.core.enums import SystemRole
from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

TENANT_ID = 1


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"SECDEPS-SECTOR-{prefix}-{suffix}",
    )


async def _cleanup(db, user_id: int):
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()


async def _authenticate_with_sector(db, user: User, sector) -> User:
    """يحاكي ترتيب تنفيذ FastAPI الحقيقي: استدعاء get_current_user فعليًا
    (يضبط ContextVar عبر set_sector كأثر جانبي حقيقي، بنفس آلية أي
    endpoint حقيقي)، ويرجع current_user الجاهز لتمريره لـsector_checker."""
    token = create_access_token(
        data={"sub": str(user.id), "sv": user.session_version, "tenant_id": TENANT_ID, "sector": sector}
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return await get_current_user(credentials=creds, db=db, cookie_token=None)


@pytest.mark.asyncio
async def test_require_sector_matching_sector_allows_access(db):
    """توكن بـsector مطابق للقطاع المطلوب على الـendpoint → يُسمح بالمرور.
    مصدر القيمة: ContextVar الحقيقية (get_sector())، وليست حقلًا على User -
    هذا هو الإصلاح الفعلي محل هذه الجلسة."""
    user = await _create_user(db, "reqsector_match")
    try:
        authenticated_user = await _authenticate_with_sector(db, user, "communications")
        checker = require_sector("communications")
        result = await checker(current_user=authenticated_user)
        assert result.id == user.id
    finally:
        await _cleanup(db, user.id)


@pytest.mark.asyncio
async def test_require_sector_mismatched_sector_rejected_with_real_sector_in_message(db):
    """توكن بـsector مختلف عن قطاع الـendpoint → PermissionDeniedError،
    ورسالة الخطأ تعكس القيمة **الحقيقية** من التوكن (communications) لا
    القيمة الثابتة "academy" التي كانت النسخة المعطَّلة تُرجعها دائمًا
    لأي مستخدم غير إداري (مطابق لـ§10 من تقرير الجلسة)."""
    user = await _create_user(db, "reqsector_mismatch")
    try:
        authenticated_user = await _authenticate_with_sector(db, user, "communications")
        checker = require_sector("academy")
        with pytest.raises(PermissionDeniedError) as exc_info:
            await checker(current_user=authenticated_user)
        assert "communications" in str(exc_info.value.message)
    finally:
        await _cleanup(db, user.id)


@pytest.mark.asyncio
async def test_require_sector_no_sector_claim_rejected_not_silently_defaulted(db):
    """توكن بلا claim اسمه sector إطلاقًا (الحالة الافتراضية الحقيقية
    اليوم لأي تسجيل دخول عادي - identity/service.py لا يُصدر sector حاليًا،
    راجع تقرير التشخيص §1.3) → يُرفض بوضوح ("User sector not defined")
    بدل الانزلاق الصامت لقيمة افتراضية ثابتة كما كانت نسخة deps.py القديمة
    تفعل (fallback إلى "academy" بلا أي تنبيه)."""
    user = await _create_user(db, "reqsector_none")
    try:
        authenticated_user = await _authenticate_with_sector(db, user, None)
        checker = require_sector("academy")
        with pytest.raises(PermissionDeniedError) as exc_info:
            await checker(current_user=authenticated_user)
        assert "sector not defined" in exc_info.value.message.lower()
    finally:
        await _cleanup(db, user.id)


@pytest.mark.asyncio
async def test_require_sector_super_admin_bypasses_regardless_of_sector(db):
    """SUPER_ADMIN/EXECUTIVE_DIRECTOR يتخطون فحص القطاع بالكامل (سلوك
    مقصود، محفوظ بالحرف من security.py الأصلية) - حتى مع sector مختلف
    تمامًا عن قطاع الـendpoint المطلوب."""
    user = await _create_user(db, "reqsector_admin")
    try:
        await db.execute(update(User).where(User.id == user.id).values(system_role=SystemRole.SUPER_ADMIN))
        await db.commit()

        authenticated_user = await _authenticate_with_sector(db, user, "communications")
        checker = require_sector("academy")
        result = await checker(current_user=authenticated_user)
        assert result.id == user.id
    finally:
        await _cleanup(db, user.id)
