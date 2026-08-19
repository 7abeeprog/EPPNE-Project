"""
regression test لجلسة `user-repository-get-by-id-audit` (Backlog #1).
تعليمات الجلسة: .claude/plans/user-repository-get-by-id-audit-session-instructions.md
تقرير الجلسة الكامل: .claude/reports/user-repository-get-by-id-audit-session-log.md

السبب الجذري (كان): `UserRepository.get_by_id(user_id, tenant_id, load_wallet=False)`
توقيعها الحقيقي يطلب `tenant_id` إجباريًا كمعامل ثانٍ، لكن 15 موضعًا فعليًا
عبر 13 دومين كانوا بينادوها بمعامل واحد بس (`user_id`) → `TypeError` فورية،
مش حتى تصل لتنفيذ الاستعلام.

القايمة الكاملة الـ15 (القسم 3 من التقرير، مرقَّمة هنا بنفس ترتيب الجدول):
 1. zamakana/service.py:650              — _register_affiliate_commission
 2. transport/service.py:569             — _get_user_by_id (book_trip/pay_delivery)
 3. transport/service.py:577             — _register_affiliate_commission
 4. tourism_sports/service.py:518        — _register_affiliate_commission
 5. tenders_auctions/service.py:484      — _register_affiliate_commission
 6. social/service.py:678                — _get_user_email (داخل begin_nested)
 7. service_marketplace/service.py:476   — _get_user (عبر _register_affiliate_commission)
 8. realestate/service.py:576            — _get_land_owner_for_unit
 9. realestate/service.py:584            — _register_affiliate_commission
10. arbitration_syndicates/service.py:564 — _register_affiliate_commission
11. manufacturing/service.py:57          — _get_user (عبر _register_affiliate_commission)
12. logistics/service.py:62              — **Dead code، بلا لمس عمدًا** (لا مستدعٍ حي)
13. iot/service.py:31                    — _get_user_email (settle_carbon_credits)
14. invitations/service.py:56            — _get_user (عبر _register_affiliate_commission)
15. insurance/service.py:60              — _get_user/_get_user_email (3 مسارات: 68/464/554)

الإصلاح المُطبَّق: تمرير `tenant_id` الفعلي (متاح أصلاً في نطاق كل دالة —
إما كمعامل مباشر، أو مُشتق من صف محمَّل زي `pension.tenant_id`) كمعامل
ثانٍ لكل استدعاء، مع تعديل توقيع أي دالة مساعدة خاصة (`_get_user_by_id`/
`_get_user_email`/`_get_user`/`_get_land_owner_for_unit`) ما كانتش بتقبل
`tenant_id` إطلاقًا. صفر تغيير في منطق معالجة الأخطاء الموجود (نفس
`try/except`/`begin_nested()` الأصلي في كل موضع).

**منهجية التحقق**: بنفس مستوى التحقق الحي الموثَّق في القسم 12.2 من
التقرير — استدعاء حقيقي بجلسة DB حقيقية يصل فعليًا لنفس السطر المُصلَح،
بمعاملين صحيحين (`user_id`, `tenant_id` صحيحين) **و**بـ`tenant_id` خاطئ
(عزل tenant فعلي، مش بس اختفاء الخطأ). التحقق على مستوى الدالة المساعدة
الخاصة مباشرة (بدل تنفيذ التدفق التجاري الكامل من الـAPI) — نفس التبرير
الموثَّق في التقرير: البج معامل ناقص تحديدًا، والتحقق على مستوى نفس
السطر المُصلَح بجلسة DB حقيقية وبيانات حقيقية يصل فعليًا لنفس الكود
المُصلَح بلا أي mock، ويتفادى تكلفة تركيب سيناريوهات تجارية كاملة (رحلات/
عقارات/بوالص تأمين) غير ضرورية لإثبات إصلاح معامل. نقاط الاستدعاء نفسها
(مين بيمرر إيه) تتأكد بمطابقة السطر المصدري ضمن كل اختبار.

**⚠️ اكتشاف جانبي حي أثناء التحقق (القسم 13 من التقرير، خارج نطاق هذه
الجلسة صراحة — توثيق فقط، بلا إصلاح):** كل مواضع `_register_affiliate_commission`
(9 دومينات + insurance = 10) بتوصل الآن بنجاح لـ`get_by_id` وتجيب
المستخدم الصحيح، لكن فورًا بعدها بتصطدم بطبقة الفشل التالية الموثَّقة
مسبقًا في جلسة `affiliate-service-missing-methods` (قسم 5.3): **`User.referred_by`
غير موجود إطلاقًا كحقل على الموديل** → `AttributeError` (مُبتلَعة بنفس
`try/except` الموجود، صمت مُسجَّل). الاختبارات هنا **تتوقع وتتسامح مع**
هذا الـ`AttributeError` تحديدًا (يثبت إن `get_by_id` نجح ووصلنا لمنطق
`referred_by`) بينما **ترفض بشكل قاطع** أي إشارة لـ`TypeError`/
`missing`/`positional argument` (كان سيثبت رجوع Backlog #1 نفسه).
`digital_twin`/`employment` خارج هذا التوثيق تمامًا — لسه محجوزان عند
Backlog #8 (`get_user()` غير موجودة)، ولا علاقة لهما بـ#1.

**بيانات throwaway**: مستخدم واحد جديد لكل اختبار (`UserService.register`،
بادئة `p1audit_*` + `uuid4` فريد) — صفر إعادة استخدام بيانات من جلسات
سابقة. تنظيف كامل في `finally` (`delete(User)` + `commit()`).
"""
import logging
import uuid
from decimal import Decimal
from typing import List

import pytest
from sqlalchemy import delete

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User
from app.core.errors import NotFoundError

TENANT_ID = 1
WRONG_TENANT_ID = 999_999


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"AUDIT1-{prefix}-{suffix}",
    )


async def _cleanup(db, user_ids: List[int]):
    if not user_ids:
        return
    await db.execute(delete(User).where(User.id.in_(user_ids)))
    await db.commit()


class _LogCapture(logging.Handler):
    """يلتقط سجلات logger 'eppne' أثناء الاختبار — نفس الأسلوب المُستخدَم
    في التحقق الحي الأصلي (قسم 12.2) لإثبات غياب TypeError دون الاعتماد
    على استثناء يوصل خارج try/except الموجود أصلاً في _register_affiliate_commission."""

    def __init__(self):
        super().__init__()
        self.records: List[str] = []

    def emit(self, record):
        self.records.append(record.getMessage())


def _assert_no_typeerror_leak(records: List[str]):
    bad = [r for r in records if any(x in r.lower() for x in ("missing", "positional argument", "typeerror"))]
    assert not bad, f"رجوع TypeError الخاص بـBacklog #1: {bad}"


# ============================================================
# 1) zamakana/service.py:650
# ============================================================

@pytest.mark.asyncio
async def test_zamakana_register_affiliate_commission_get_by_id_fixed(db):
    """الموضع #1 — zamakana/service.py:650 داخل _register_affiliate_commission.
    tenant_id صحيح → get_by_id ينجح ويوصل لطبقة referred_by (AttributeError
    متسامَح بها، خارج نطاق #1). tenant_id خاطئ → get_by_id يرجع None، صفر
    أي خطأ إطلاقًا (لا TypeError ولا AttributeError)."""
    from app.domains.zamakana.service import ZamakanaService

    user = await _create_user(db, "p1audit_zamakana")
    user_ids = [user.id]
    try:
        svc = ZamakanaService(db)
        cap = _LogCapture()
        logging.getLogger("eppne").addHandler(cap)
        try:
            await svc._register_affiliate_commission(user.id, TENANT_ID, "TEST_ACTION")
            _assert_no_typeerror_leak(cap.records)
            assert any("referred_by" in r for r in cap.records), (
                "المتوقع: وصلنا لطبقة referred_by المفقودة (يثبت get_by_id نجح)"
            )

            cap.records.clear()
            await svc._register_affiliate_commission(user.id, WRONG_TENANT_ID, "TEST_ACTION")
            assert cap.records == [], f"tenant خاطئ لازم يرجع None بصمت تام، لا أخطاء: {cap.records}"
        finally:
            logging.getLogger("eppne").removeHandler(cap)
    finally:
        await _cleanup(db, user_ids)


# ============================================================
# 2+3) transport/service.py:569 و:577
# ============================================================

@pytest.mark.asyncio
async def test_transport_get_user_by_id_correct_and_wrong_tenant(db):
    """الموضع #2 — transport/service.py:569 (_get_user_by_id، مستدعاة من
    book_trip:326 وpay_delivery:507). tenant_id صحيح → User صحيح. tenant_id
    خاطئ → NotFoundError صريحة (سلوك الدالة الأصلي محفوظ، مش TypeError)."""
    from app.domains.transport.service import TransportService

    user = await _create_user(db, "p1audit_transport")
    user_ids = [user.id]
    try:
        svc = TransportService(db)
        found = await svc._get_user_by_id(user.id, TENANT_ID)
        assert found is not None and found.id == user.id

        with pytest.raises(NotFoundError):
            await svc._get_user_by_id(user.id, WRONG_TENANT_ID)
    finally:
        await _cleanup(db, user_ids)


@pytest.mark.asyncio
async def test_transport_register_affiliate_commission_get_by_id_fixed(db):
    """الموضع #3 — transport/service.py:577 داخل _register_affiliate_commission
    (self.user_repo.get_by_id مباشر، منفصل عن _get_user_by_id)."""
    from app.domains.transport.service import TransportService

    user = await _create_user(db, "p1audit_transport_commission")
    user_ids = [user.id]
    try:
        svc = TransportService(db)
        cap = _LogCapture()
        logging.getLogger("eppne").addHandler(cap)
        try:
            await svc._register_affiliate_commission(user.id, TENANT_ID, Decimal("10"))
            _assert_no_typeerror_leak(cap.records)
            assert any("referred_by" in r for r in cap.records)

            cap.records.clear()
            await svc._register_affiliate_commission(user.id, WRONG_TENANT_ID, Decimal("10"))
            assert cap.records == []
        finally:
            logging.getLogger("eppne").removeHandler(cap)
    finally:
        await _cleanup(db, user_ids)


# ============================================================
# 4) tourism_sports/service.py:518
# ============================================================

@pytest.mark.asyncio
async def test_tourism_sports_register_affiliate_commission_get_by_id_fixed(db):
    """الموضع #4 — tourism_sports/service.py:518."""
    from app.domains.tourism_sports.service import TourismSportsService

    user = await _create_user(db, "p1audit_tourism")
    user_ids = [user.id]
    try:
        svc = TourismSportsService(db)
        cap = _LogCapture()
        logging.getLogger("eppne").addHandler(cap)
        try:
            await svc._register_affiliate_commission(user.id, TENANT_ID, "TEST_ACTION", Decimal("10"))
            _assert_no_typeerror_leak(cap.records)
            assert any("referred_by" in r for r in cap.records)

            cap.records.clear()
            await svc._register_affiliate_commission(user.id, WRONG_TENANT_ID, "TEST_ACTION", Decimal("10"))
            assert cap.records == []
        finally:
            logging.getLogger("eppne").removeHandler(cap)
    finally:
        await _cleanup(db, user_ids)


# ============================================================
# 5) tenders_auctions/service.py:484
# ============================================================

@pytest.mark.asyncio
async def test_tenders_auctions_register_affiliate_commission_get_by_id_fixed(db):
    """الموضع #5 — tenders_auctions/service.py:484."""
    from app.domains.tenders_auctions.service import TendersAuctionsService

    user = await _create_user(db, "p1audit_tenders")
    user_ids = [user.id]
    try:
        svc = TendersAuctionsService(db)
        cap = _LogCapture()
        logging.getLogger("eppne").addHandler(cap)
        try:
            await svc._register_affiliate_commission(user.id, TENANT_ID, "TENDER_CREATED")
            _assert_no_typeerror_leak(cap.records)
            assert any("referred_by" in r for r in cap.records)

            cap.records.clear()
            await svc._register_affiliate_commission(user.id, WRONG_TENANT_ID, "TENDER_CREATED")
            assert cap.records == []
        finally:
            logging.getLogger("eppne").removeHandler(cap)
    finally:
        await _cleanup(db, user_ids)


# ============================================================
# 6) social/service.py:678
# ============================================================

@pytest.mark.asyncio
async def test_social_get_user_email_correct_and_wrong_tenant(db):
    """الموضع #6 — social/service.py:678 (_get_user_email، داخل begin_nested()
    في send_digital_gift:492 — صفر try/except، بالتصميم المعتمَد). tenant_id
    صحيح → إيميل حقيقي. tenant_id خاطئ → fallback نصي (سلوك الدالة الأصلي
    محفوظ، لا استثناء)."""
    from app.domains.social.service import SocialService

    user = await _create_user(db, "p1audit_social")
    user_ids = [user.id]
    try:
        svc = SocialService(db)
        email = await svc._get_user_email(user.id, TENANT_ID)
        assert email == user.email

        fallback = await svc._get_user_email(user.id, WRONG_TENANT_ID)
        assert fallback == f"user_{user.id}@eppne.com"
    finally:
        await _cleanup(db, user_ids)


# ============================================================
# 7) service_marketplace/service.py:476
# ============================================================

@pytest.mark.asyncio
async def test_service_marketplace_get_user_correct_and_wrong_tenant(db):
    """الموضع #7 — service_marketplace/service.py:476 (_get_user، عبر
    _register_affiliate_commission:486)."""
    from app.domains.service_marketplace.service import ServiceMarketplaceService

    user = await _create_user(db, "p1audit_svcmkt")
    user_ids = [user.id]
    try:
        svc = ServiceMarketplaceService(db)
        found = await svc._get_user(user.id, TENANT_ID)
        assert found is not None and found.id == user.id

        found_wrong = await svc._get_user(user.id, WRONG_TENANT_ID)
        assert found_wrong is None

        cap = _LogCapture()
        logging.getLogger("eppne").addHandler(cap)
        try:
            await svc._register_affiliate_commission(user.id, TENANT_ID, Decimal("10"), "test")
            _assert_no_typeerror_leak(cap.records)
            assert any("referred_by" in r for r in cap.records)
        finally:
            logging.getLogger("eppne").removeHandler(cap)
    finally:
        await _cleanup(db, user_ids)


# ============================================================
# 8+9) realestate/service.py:576 و:584
# ============================================================

@pytest.mark.asyncio
async def test_realestate_land_owner_get_by_id_correct_and_wrong_tenant(db):
    """الموضع #8 — realestate/service.py:576 (_get_land_owner_for_unit).
    تحقق على مستوى self.user_repo.get_by_id المباشر — نفس الـinstance/نفس
    الاستدعاء الحرفي المُستخدَم داخل _get_land_owner_for_unit (سطر 576)،
    بدل تركيب Development/LandAsset/PropertyUnit حقيقيين بالكامل (تكلفة
    غير ضرورية لإثبات إصلاح معامل — نفس المنهجية الموثَّقة في قسم 12.2 من
    التقرير). نقطة الاستدعاء نفسها (تمرير tenant_id من fractional purchase
    عند السطر ~237) تتأكد بمطابقة السطر المصدري أدناه."""
    import inspect
    from app.domains.realestate.service import RealEstateService

    src = inspect.getsource(RealEstateService._get_land_owner_for_unit)
    assert "tenant_id" in inspect.signature(RealEstateService._get_land_owner_for_unit).parameters
    assert "get_by_id(cast(int, land.owner_id), tenant_id)" in src

    user = await _create_user(db, "p1audit_realestate_owner")
    user_ids = [user.id]
    try:
        svc = RealEstateService(db)
        found = await svc.user_repo.get_by_id(user.id, TENANT_ID)
        assert found is not None and found.id == user.id

        found_wrong = await svc.user_repo.get_by_id(user.id, WRONG_TENANT_ID)
        assert found_wrong is None
    finally:
        await _cleanup(db, user_ids)


@pytest.mark.asyncio
async def test_realestate_register_affiliate_commission_get_by_id_fixed(db):
    """الموضع #9 — realestate/service.py:584 داخل _register_affiliate_commission."""
    from app.domains.realestate.service import RealEstateService

    user = await _create_user(db, "p1audit_realestate_commission")
    user_ids = [user.id]
    try:
        svc = RealEstateService(db)
        cap = _LogCapture()
        logging.getLogger("eppne").addHandler(cap)
        try:
            await svc._register_affiliate_commission(user.id, TENANT_ID, Decimal("10"))
            _assert_no_typeerror_leak(cap.records)
            assert any("referred_by" in r for r in cap.records)

            cap.records.clear()
            await svc._register_affiliate_commission(user.id, WRONG_TENANT_ID, Decimal("10"))
            assert cap.records == []
        finally:
            logging.getLogger("eppne").removeHandler(cap)
    finally:
        await _cleanup(db, user_ids)


# ============================================================
# 10) arbitration_syndicates/service.py:564
# ============================================================

@pytest.mark.asyncio
async def test_arbitration_syndicates_register_affiliate_commission_get_by_id_fixed(db):
    """الموضع #10 — arbitration_syndicates/service.py:564."""
    from app.domains.arbitration_syndicates.service import ArbitrationSyndicatesService

    user = await _create_user(db, "p1audit_arbitration")
    user_ids = [user.id]
    try:
        svc = ArbitrationSyndicatesService(db)
        cap = _LogCapture()
        logging.getLogger("eppne").addHandler(cap)
        try:
            await svc._register_affiliate_commission(user.id, TENANT_ID, "ARBITRATION_CASE_CREATED")
            _assert_no_typeerror_leak(cap.records)
            assert any("referred_by" in r for r in cap.records)

            cap.records.clear()
            await svc._register_affiliate_commission(user.id, WRONG_TENANT_ID, "ARBITRATION_CASE_CREATED")
            assert cap.records == []
        finally:
            logging.getLogger("eppne").removeHandler(cap)
    finally:
        await _cleanup(db, user_ids)


# ============================================================
# 11) manufacturing/service.py:57
# ============================================================

@pytest.mark.asyncio
async def test_manufacturing_get_user_correct_and_wrong_tenant(db):
    """الموضع #11 — manufacturing/service.py:57 (_get_user، عبر
    _register_affiliate_commission:66). `_get_user_email` في نفس الملف
    ميتة الاستدعاء (dead code) لكن توقيعها اتحدَّث كمان لتفادي كسر جديد
    في كود ميت (موثَّق في قسم 12.1 من التقرير)."""
    from app.domains.manufacturing.service import ManufacturingService

    user = await _create_user(db, "p1audit_manufacturing")
    user_ids = [user.id]
    try:
        svc = ManufacturingService(db)
        found = await svc._get_user(user.id, TENANT_ID)
        assert found is not None and found.id == user.id

        found_wrong = await svc._get_user(user.id, WRONG_TENANT_ID)
        assert found_wrong is None

        cap = _LogCapture()
        logging.getLogger("eppne").addHandler(cap)
        try:
            await svc._register_affiliate_commission(user.id, TENANT_ID, "FACILITY_CREATED")
            _assert_no_typeerror_leak(cap.records)
            assert any("referred_by" in r for r in cap.records)
        finally:
            logging.getLogger("eppne").removeHandler(cap)
    finally:
        await _cleanup(db, user_ids)


# ============================================================
# 12) logistics/service.py:62 — Dead code، توثيق فقط، بلا لمس
# ============================================================

def test_logistics_get_user_left_untouched_as_documented_dead_code():
    """الموضع #12 — logistics/service.py:62. **قرار نطاق صريح**: بلا لمس
    عمدًا — `_get_user`/`_get_user_email` بلا أي مستدعٍ حي في المشروع كله
    (لا يوجد `_register_affiliate_commission` في هذا الملف أصلاً). هذا
    الاختبار **لا يتحقق من نجاح** — بالعكس، يوثِّق ويقفل الحالة الحالية
    (لسه معامل واحد بس) عمدًا، عشان لو حد غيَّرها مستقبلًا بلا وعي بالسياق
    (يضيف مستدعٍ حي جديد مثلًا)، الاختبار ده هيفشل ويوجِّهه لقراءة تقرير
    هذه الجلسة والقسم 9.5 قبل اللمس."""
    import inspect
    from app.domains.logistics.service import LogisticsService

    sig = inspect.signature(LogisticsService._get_user)
    params = list(sig.parameters)
    assert params == ["self", "user_id"], (
        "توقيع _get_user في logistics اتغيَّر! كان متروك عمدًا كـdead code "
        "بمعامل واحد بس (Backlog #1، user-repository-get-by-id-audit، القسم 9.5). "
        "لو دلوقتي فيه مستدعٍ حي جديد ليها، لازم تُصلَح بنفس أسلوب باقي الـ14 "
        "موضع (إضافة tenant_id) — راجع تقرير الجلسة قبل التعديل."
    )


# ============================================================
# 13) iot/service.py:31
# ============================================================

@pytest.mark.asyncio
async def test_iot_get_user_email_correct_and_wrong_tenant(db):
    """الموضع #13 — iot/service.py:31 (_get_user_email، مستدعاة من
    settle_carbon_credits:214 داخل try/except يحوّلها لـBusinessError —
    سلوك محفوظ، مش مُغيَّر هنا)."""
    from app.domains.iot.service import IoTService

    user = await _create_user(db, "p1audit_iot")
    user_ids = [user.id]
    try:
        svc = IoTService(db)
        email = await svc._get_user_email(user.id, TENANT_ID)
        assert email == user.email

        fallback = await svc._get_user_email(user.id, WRONG_TENANT_ID)
        assert fallback == f"user_{user.id}@eppne.com"
    finally:
        await _cleanup(db, user_ids)


# ============================================================
# 14) invitations/service.py:56
# ============================================================

@pytest.mark.asyncio
async def test_invitations_get_user_correct_and_wrong_tenant(db):
    """الموضع #14 — invitations/service.py:56 (_get_user، عبر
    _register_affiliate_commission:68). `_get_user_email` ميتة الاستدعاء
    (نفس ملاحظة manufacturing)."""
    from app.domains.invitations.service import InvitationsService

    user = await _create_user(db, "p1audit_invitations")
    user_ids = [user.id]
    try:
        svc = InvitationsService(db)
        found = await svc._get_user(user.id, TENANT_ID)
        assert found is not None and found.id == user.id

        found_wrong = await svc._get_user(user.id, WRONG_TENANT_ID)
        assert found_wrong is None

        cap = _LogCapture()
        logging.getLogger("eppne").addHandler(cap)
        try:
            await svc._register_affiliate_commission(user.id, TENANT_ID, "INVITATION_CREATED")
            _assert_no_typeerror_leak(cap.records)
            assert any("referred_by" in r for r in cap.records)
        finally:
            logging.getLogger("eppne").removeHandler(cap)
    finally:
        await _cleanup(db, user_ids)


# ============================================================
# 15) insurance/service.py:60 — 3 مسارات (68 عبر _register_affiliate_commission،
#     464 عبر review_claim، 554 عبر disburse_monthly_pensions)
# ============================================================

@pytest.mark.asyncio
async def test_insurance_get_user_and_get_user_email_all_three_call_paths(db):
    """الموضع #15 — insurance/service.py:60 (_get_user) و:63 (_get_user_email،
    تلف _get_user). **تعديل واحد يغطي 3 مسارات استدعاء فعلية في نفس الملف**
    (قسم 9.2 من التقرير):
    - :68 داخل _register_affiliate_commission (tenant_id من معامل الدالة)
    - :464 داخل review_claim (tenant_id من معامل الدالة) — كان الكسر
      الواضح (500) الموثَّق حيًا مسبقًا في test_saas_active_subscription.py
      (حُدِّث في هذه الجلسة بعد إصلاح #1 — راجع docstring الاختبار هناك)
    - :554 داخل disburse_monthly_pensions (tenant_id من `pension.tenant_id`
      المُشتق من صف محمَّل — **أسوأ فئة صمت سابقًا**، `except Exception: pass`
      بلا أي تسجيل إطلاقًا)
    التحقق هنا على مستوى الدالتين المساعدتين مباشرة (نفس الآلية المشتركة
    للمسارات الثلاثة) + تأكيد نصي إن كل الثلاث نقاط استدعاء بالكود بتمرر
    tenant_id فعليًا."""
    import inspect
    from app.domains.insurance.service import InsuranceService

    src = inspect.getsource(InsuranceService)
    assert "await self._get_user(user_id, tenant_id)" in src  # :68
    assert "await self._get_user_email(claim.claimant_user_id, tenant_id)" in src  # :464
    assert "await self._get_user_email(pension.beneficiary_id, cast(int, pension.tenant_id))" in src  # :554

    user = await _create_user(db, "p1audit_insurance")
    user_ids = [user.id]
    try:
        svc = InsuranceService(db)
        found = await svc._get_user(user.id, TENANT_ID)
        assert found is not None and found.id == user.id
        found_wrong = await svc._get_user(user.id, WRONG_TENANT_ID)
        assert found_wrong is None

        email = await svc._get_user_email(user.id, TENANT_ID)
        assert email == user.email
        fallback = await svc._get_user_email(user.id, WRONG_TENANT_ID)
        assert fallback == f"user_{user.id}@eppne.com"

        cap = _LogCapture()
        logging.getLogger("eppne").addHandler(cap)
        try:
            await svc._register_affiliate_commission(user.id, TENANT_ID, "TEST_ACTION", Decimal("10"))
            _assert_no_typeerror_leak(cap.records)
            assert any("referred_by" in r for r in cap.records)
        finally:
            logging.getLogger("eppne").removeHandler(cap)
    finally:
        await _cleanup(db, user_ids)
