"""
regression test لجلسة `user-repository-get-user-audit` (Backlog #8).
تعليمات الجلسة: .claude/plans/user-repository-get-user-audit-session-instructions.md
تقرير الجلسة الكامل: .claude/reports/user-repository-get-user-audit-session-log.md

السبب الجذري (كان): `UserRepository` **ليست عندها method اسمها `get_user()`
إطلاقًا** (بعكس Backlog #1/`get_by_id` اللي كانت موجودة بتوقيع ناقص) — أي
استدعاء `.get_user(` عليها كان `AttributeError` مباشر.

القايمة الكاملة — 5 مواضع، 8 نقاط استدعاء حية + موضعان dead code:
 1. employment/service.py:87   — _get_user (3 نقاط استدعاء: _register_affiliate_commission:100،
    _calculate_ai_match_score:132، وapp/tasks/employment.py:308 عبر _get_user_email)
 2. digital_twin/service.py:53 — _get_user (2 نقطة استدعاء: _register_affiliate_commission:71،
    interact_with_twin:180 عبر _get_user_email — كانت كسر 500 مباشر بلا try/except)
 3. communications/service.py:29 — _get_user_tenant (3 نقاط استدعاء: send_notification:63،
    send_mail:144/145 — **استثناء معماري**: الغرض هو اكتشاف tenant_id نفسه،
    لا يوجد tenant_id متاح في أي نقطة استدعاء أصلًا)
 4. communications/service.py:36 — _get_user_email — **Dead code، بلا لمس عمدًا** (صفر مستدعٍ حي)
 5. health/service.py:54        — _get_user_email — **Dead code، بلا لمس عمدًا** (صفر مستدعٍ حي)

الإصلاح المُطبَّق:
- `employment`/`digital_twin`: نفس منهجية Backlog #1 بالحرف — تعديل توقيع
  كل private helper ليقبل `tenant_id: int`، واستبدال `.get_user(user_id)`
  بـ`.get_by_id(user_id, tenant_id)`. صفر إضافة try/except جديد.
- `communications`: **method جديدة على `UserRepository`**:
  `get_tenant_id_by_user_id(user_id) -> Optional[int]` — تبحث بـuser_id
  وحده عبر كل الـtenants وترجع `tenant_id` فقط (مش كائن User كامل —
  قرار least-privilege: أقصى ضرر ممكن لو استُخدمت غلط هو تسريب tenant_id
  فقط). `_get_user_tenant` بقت تنادي هذه الـmethod مباشرة.

**⚠️ اكتشاف جانبي حي أثناء التحقق (قسم 8 من التقرير، خارج نطاق هذه الجلسة
صراحة — توثيق فقط، بلا إصلاح):** `_register_affiliate_commission` في كل
من `employment`/`digital_twin` بتوصل الآن بنجاح لـ`get_by_id` وتجيب
المستخدم الصحيح، لكن فورًا بعدها بتصطدم بنفس طبقة الفشل التالية الموثَّقة
في جلسة #1: `User.referred_by` غير موجود إطلاقًا كحقل على الموديل →
`AttributeError` مُبتلَعة بنفس `try/except` الموجود، صمت مُسجَّل. الاختبارات
هنا **تتوقع وتتسامح مع** هذا الـ`AttributeError` تحديدًا (يثبت إن
`get_by_id` نجح ووصلنا لمنطق `referred_by`) — نفس أسلوب اختبارات #1
بالضبط. **بهذا وصلت سلسلة affiliate/Backlog #10 لحالة موحَّدة كاملة عبر
12 دومين** (10 من #1 + digital_twin وemployment هنا).

**بيانات throwaway**: مستخدم واحد جديد لكل اختبار (`UserService.register`،
بادئة `p8audit_` + `uuid4` فريد) — صفر إعادة استخدام بيانات من جلسات
سابقة. تنظيف كامل في `finally` (`delete(User)` + `commit()`).
"""
import logging
import uuid
from pathlib import Path
from typing import List

import pytest
from sqlalchemy import delete

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels

from app.domains.identity.service import UserService
from app.domains.identity.repository import UserRepository
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

TENANT_ID = 1
WRONG_TENANT_ID = 999_999
BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"AUDIT8-{prefix}-{suffix}",
    )


async def _cleanup(db, user_ids: List[int]):
    if not user_ids:
        return
    await db.execute(delete(User).where(User.id.in_(user_ids)))
    await db.commit()


class _LogCapture(logging.Handler):
    """يلتقط سجلات logger 'eppne' أثناء الاختبار — نفس الأسلوب المُستخدَم
    في جلسة #1 لإثبات وصول referred_by دون الاعتماد على استثناء يوصل
    خارج try/except الموجود أصلاً في _register_affiliate_commission."""

    def __init__(self):
        super().__init__()
        self.records: List[str] = []

    def emit(self, record):
        self.records.append(record.getMessage())


def _assert_no_get_user_attributeerror_leak(records: List[str]):
    bad = [r for r in records if "has no attribute 'get_user'" in r]
    assert not bad, f"رجوع AttributeError الخاص بـBacklog #8: {bad}"


# ============================================================
# 1) employment/service.py:87 — _get_user
# ============================================================

@pytest.mark.asyncio
async def test_employment_get_user_correct_and_wrong_tenant(db):
    """الموضع #1 — employment/service.py:87 (_get_user، مستدعاة من
    _register_affiliate_commission:100 ومن _calculate_ai_match_score:132).
    tenant_id صحيح → User صحيح. tenant_id خاطئ → None (عزل tenant فعلي،
    سلوك get_by_id الأصلي محفوظ)."""
    from app.domains.employment.service import EmploymentService

    user = await _create_user(db, "p8audit_employment")
    user_ids = [user.id]
    try:
        svc = EmploymentService(db)
        found = await svc._get_user(user.id, TENANT_ID)
        assert found is not None and found.id == user.id

        found_wrong = await svc._get_user(user.id, WRONG_TENANT_ID)
        assert found_wrong is None
    finally:
        await _cleanup(db, user_ids)


@pytest.mark.asyncio
async def test_employment_get_user_email_correct_and_wrong_tenant(db):
    """نقطة الاستدعاء الخارجية الجديدة — app/tasks/employment.py:308
    (`pay_payroll_task`، عبر `service._get_user_email(employee_id, tenant_id)`)
    — كانت تفشل الدفع فعليًا (يُعاد المحاولة 3 مرات ثم يستسلم). تحقق مباشر
    على مستوى `_get_user_email` (نفس السطر المُستخدَم في المهمة) + تأكيد
    نصي إن المهمة نفسها بقت بتمرر tenant_id."""
    from app.domains.employment.service import EmploymentService

    tasks_src = (BACKEND_ROOT / "app" / "tasks" / "employment.py").read_text(encoding="utf-8")
    assert "employee_email = await service._get_user_email(employee_id, tenant_id)" in tasks_src, (
        "استدعاء pay_payroll_task:308 لازم يمرر tenant_id — راجع تقرير الجلسة قسم 7.1"
    )

    user = await _create_user(db, "p8audit_employment_payroll")
    user_ids = [user.id]
    try:
        svc = EmploymentService(db)
        email = await svc._get_user_email(user.id, TENANT_ID)
        assert email == user.email

        fallback = await svc._get_user_email(user.id, WRONG_TENANT_ID)
        assert fallback == f"user_{user.id}@eppne.com"
    finally:
        await _cleanup(db, user_ids)


@pytest.mark.asyncio
async def test_employment_calculate_ai_match_score_passes_tenant_id():
    """نقطة الاستدعاء `_calculate_ai_match_score:132` (تُستدعى من
    `apply_for_job:246`، مسار تقديم طلب توظيف حقيقي) — كانت تفشل بصمت
    وترجع درجة افتراضية 50 دايمًا (ميزة AI matching معطَّلة). تأكيد نصي
    فقط إن `tenant_id` بقى يُمرَّر (عبر `job.tenant_id`) — **بلا تشغيل
    التدفق الكامل** لتفادي استدعاء AI agent حقيقي غير ضروري لإثبات إصلاح
    معامل (نفس منطق تفادي التدفقات التجارية الكاملة في جلسة #1)."""
    import inspect
    from app.domains.employment.service import EmploymentService

    src = inspect.getsource(EmploymentService._calculate_ai_match_score)
    assert "await self._get_user(applicant_id, cast(int, job.tenant_id))" in src


@pytest.mark.asyncio
async def test_employment_register_affiliate_commission_reaches_referred_by_layer(db):
    """الموضع #1 (نقطة `_register_affiliate_commission:100`). tenant_id
    صحيح → get_by_id ينجح ويوصل لطبقة referred_by المفقودة (AttributeError
    مُبتلَعة، خارج نطاق #8 — يثبت وصول employment لنفس طبقة الفشل الموحَّدة
    مع باقي دومينات affiliate/#10). tenant_id خاطئ → صمت تام (get_by_id
    يرجع None، صفر أي محاولة وصول لـreferred_by)."""
    from app.domains.employment.service import EmploymentService
    from decimal import Decimal

    user = await _create_user(db, "p8audit_employment_commission")
    user_ids = [user.id]
    try:
        svc = EmploymentService(db)
        cap = _LogCapture()
        logging.getLogger("eppne").addHandler(cap)
        try:
            await svc._register_affiliate_commission(user.id, TENANT_ID, "JOB_CREATED", Decimal("0"))
            _assert_no_get_user_attributeerror_leak(cap.records)
            assert any("referred_by" in r for r in cap.records), (
                "المتوقع: وصلنا لطبقة referred_by المفقودة (يثبت get_by_id نجح، Backlog #8 مُصلَح)"
            )

            cap.records.clear()
            await svc._register_affiliate_commission(user.id, WRONG_TENANT_ID, "JOB_CREATED", Decimal("0"))
            assert cap.records == [], f"tenant خاطئ لازم صمت تام، لا أخطاء: {cap.records}"
        finally:
            logging.getLogger("eppne").removeHandler(cap)
    finally:
        await _cleanup(db, user_ids)


# ============================================================
# 2) digital_twin/service.py:53 — _get_user
# ============================================================

@pytest.mark.asyncio
async def test_digital_twin_get_user_correct_and_wrong_tenant(db):
    """الموضع #2 — digital_twin/service.py:53 (_get_user)."""
    from app.domains.digital_twin.service import DigitalTwinService

    user = await _create_user(db, "p8audit_digitaltwin")
    user_ids = [user.id]
    try:
        svc = DigitalTwinService(db)
        found = await svc._get_user(user.id, TENANT_ID)
        assert found is not None and found.id == user.id

        found_wrong = await svc._get_user(user.id, WRONG_TENANT_ID)
        assert found_wrong is None
    finally:
        await _cleanup(db, user_ids)


@pytest.mark.asyncio
async def test_digital_twin_get_user_email_correct_and_wrong_tenant(db):
    """نقطة الاستدعاء `interact_with_twin:180` (عبر `_get_user_email`) —
    **كانت كسر واضح 500 داخل `db.begin_nested()` بلا أي try/except** (نفس
    نمط `social:678` في جلسة #1). صفر تغيير في `begin_nested()`/معالجة
    الأخطاء هنا — فقط إصلاح تمرير المعامل الناقص."""
    from app.domains.digital_twin.service import DigitalTwinService

    user = await _create_user(db, "p8audit_digitaltwin_interact")
    user_ids = [user.id]
    try:
        svc = DigitalTwinService(db)
        email = await svc._get_user_email(user.id, TENANT_ID)
        assert email == user.email

        fallback = await svc._get_user_email(user.id, WRONG_TENANT_ID)
        assert fallback == f"user_{user.id}@eppne.com"
    finally:
        await _cleanup(db, user_ids)


@pytest.mark.asyncio
async def test_digital_twin_register_affiliate_commission_reaches_referred_by_layer(db):
    """نقطة الاستدعاء `_register_affiliate_commission:71`."""
    from app.domains.digital_twin.service import DigitalTwinService

    user = await _create_user(db, "p8audit_digitaltwin_commission")
    user_ids = [user.id]
    try:
        svc = DigitalTwinService(db)
        cap = _LogCapture()
        logging.getLogger("eppne").addHandler(cap)
        try:
            await svc._register_affiliate_commission(user.id, TENANT_ID, "TWIN_CREATION")
            _assert_no_get_user_attributeerror_leak(cap.records)
            assert any("referred_by" in r for r in cap.records), (
                "المتوقع: وصلنا لطبقة referred_by المفقودة (يثبت get_by_id نجح، Backlog #8 مُصلَح)"
            )

            cap.records.clear()
            await svc._register_affiliate_commission(user.id, WRONG_TENANT_ID, "TWIN_CREATION")
            assert cap.records == [], f"tenant خاطئ لازم صمت تام، لا أخطاء: {cap.records}"
        finally:
            logging.getLogger("eppne").removeHandler(cap)
    finally:
        await _cleanup(db, user_ids)


# ============================================================
# 3) communications/service.py:29 — _get_user_tenant (استثناء معماري)
# ============================================================

@pytest.mark.asyncio
async def test_user_repository_get_tenant_id_by_user_id(db):
    """method جديدة على UserRepository (قرار معماري معتمَد، قسم 6.2 من
    التقرير): تبحث بـuser_id وحده عبر كل الـtenants، ترجع tenant_id فقط
    (مش كائن User كامل — least privilege). مستخدم حقيقي → tenant_id
    صحيح. مستخدم غير موجود → None."""
    user = await _create_user(db, "p8audit_repo_tenant_lookup")
    user_ids = [user.id]
    try:
        repo = UserRepository(db)
        tenant_id = await repo.get_tenant_id_by_user_id(user.id)
        assert tenant_id == TENANT_ID

        missing = await repo.get_tenant_id_by_user_id(9_999_999)
        assert missing is None
    finally:
        await _cleanup(db, user_ids)


@pytest.mark.asyncio
async def test_communications_get_user_tenant_correct_user(db):
    """الموضع #3 — communications/service.py:29 (_get_user_tenant).
    **استثناء معماري عن كل باقي المواضع**: الغرض من هذه الدالة هو اكتشاف
    tenant_id نفسه — لا يوجد tenant_id متاح في نطاق أي من نقاط الاستدعاء
    الثلاث (send_notification:63، send_mail:144، send_mail:145) أصلًا،
    فالحل المعتاد (إضافة معامل tenant_id) لا ينطبق. الحل المعتمَد بدلاً
    من ذلك: method جديدة `get_tenant_id_by_user_id` (مُختبَرة أعلاه) —
    `_get_user_tenant` بقت تنادي عليها مباشرة. تأكيد نصي إن الثلاث نقاط
    استدعاء لسه بتنادي `_get_user_tenant` كما هي (بلا تغيير في توقيعها،
    القرار المتعمَّد بالحفاظ على استعلامين منفصلين في send_mail)."""
    import inspect
    from app.domains.communications.service import CommunicationsService

    src = inspect.getsource(CommunicationsService)
    assert "return await self.user_repo.get_tenant_id_by_user_id(user_id)" in src
    assert src.count("await self._get_user_tenant(") == 3, (
        "المتوقع 3 نقاط استدعاء لـ_get_user_tenant: send_notification:63، "
        "send_mail:144 (sender_tenant)، send_mail:145 (recipient_tenant) — "
        "راجع تقرير الجلسة قسم 3.3 قبل تعديل هذا العدد"
    )

    user = await _create_user(db, "p8audit_communications")
    user_ids = [user.id]
    try:
        svc = CommunicationsService(db)
        tenant_id = await svc._get_user_tenant(user.id)
        assert tenant_id == TENANT_ID
    finally:
        await _cleanup(db, user_ids)


# ============================================================
# 4) communications/service.py:36 — Dead code، توثيق فقط، بلا لمس
# ============================================================

def test_communications_get_user_email_left_untouched_as_documented_dead_code():
    """الموضع #4 — communications/service.py (_get_user_email). **قرار
    نطاق صريح ومعتمَد**: بلا لمس عمدًا — صفر مستدعٍ حي لها في الملف كله
    ولا في المشروع (نفس فئة `logistics/service.py:62` من جلسة #1). هذا
    الاختبار **لا يتحقق من نجاح** — يوثِّق ويقفل الحالة الحالية (لسه
    بتستخدم `.get_user(` المكسورة) عمدًا، عشان لو حد أضاف مستدعٍ حي
    جديد لها مستقبلًا بلا وعي بالسياق، الاختبار ده هيفشل ويوجِّهه لقراءة
    تقرير هذه الجلسة (قسم 3.4) قبل اللمس."""
    import inspect
    from app.domains.communications.service import CommunicationsService

    src = inspect.getsource(CommunicationsService)
    assert "async def _get_user_email(self, user_id: int) -> str:" in src
    assert "user = await self.user_repo.get_user(user_id)" in src, (
        "_get_user_email في communications اتغيَّرت! كانت متروكة عمدًا كـdead "
        "code تنادي .get_user( المكسورة (Backlog #8، قسم 3.4 من التقرير). "
        "لو دلوقتي فيه مستدعٍ حي جديد لها، لازم تُصلَح بنفس أسلوب باقي "
        "المواضع (استخدام get_by_id مع tenant_id) — راجع تقرير الجلسة قبل التعديل."
    )
    assert src.count("await self._get_user_email(") == 0, (
        "ظهر مستدعٍ حي جديد لـ_get_user_email في communications! لازم يُصلَح "
        "الآن (كانت dead code فقط وقت هذه الجلسة) — راجع تقرير #8 قسم 3.4"
    )


# ============================================================
# 5) health/service.py:54 — Dead code، توثيق فقط، بلا لمس
# ============================================================

def test_health_get_user_email_left_untouched_as_documented_dead_code():
    """الموضع #5 — health/service.py:54 (_get_user_email). **قرار نطاق
    صريح ومعتمَد**: بلا لمس عمدًا — صفر مستدعٍ حي لها في الملف كله ولا
    في المشروع. نفس منطق الاختبار السابق لـcommunications:36."""
    import inspect
    from app.domains.health.service import HealthService

    src = inspect.getsource(HealthService)
    assert "async def _get_user_email(self, user_id: int) -> str:" in src
    assert "user = await user_repo.get_user(user_id)" in src, (
        "_get_user_email في health اتغيَّرت! كانت متروكة عمدًا كـdead code "
        "تنادي .get_user( المكسورة (Backlog #8، قسم 3.5 من التقرير). لو "
        "دلوقتي فيه مستدعٍ حي جديد لها، لازم تُصلَح — راجع تقرير الجلسة قبل التعديل."
    )
    assert src.count("await self._get_user_email(") == 0, (
        "ظهر مستدعٍ حي جديد لـ_get_user_email في health! لازم يُصلَح الآن "
        "(كانت dead code فقط وقت هذه الجلسة) — راجع تقرير #8 قسم 3.5"
    )
