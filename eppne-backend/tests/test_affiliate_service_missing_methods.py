"""
regression test لجلسة `affiliate-service-missing-methods` (Backlog #10،
المرحلة 2).
تقرير الجلسة الأصلية: .claude/reports/affiliate-service-missing-methods-session-log.md

السبب الجذري (كان): `AffiliateService` لم تكن تملك `register_commission`
ولا `get_user_by_code` إطلاقًا — مستدعاتان من 12 دومين (36 موضع استدعاء
فعلي، `grep` شامل) عبر ميثود خاص `_register_affiliate_commission` مُعرَّف
داخل كل دومين، كلها ملفوفة بـ`try/except Exception` صامت. الطلب الأساسي
كان ينجح ظاهريًا والعمولة تضيع بصمت.

**اكتشاف حرج غيَّر التشخيص بالكامل:** جدول `Commission` الموجود
(`affiliate_commissions`) مصمَّم حصريًا لعمولات مرتبطة بـOrder تجاري
حقيقي (`order_id`/`order_item_id`/`product_id` كلها FK **NOT NULL**) —
والـ12 موضع كلها أحداث بلا أي Order (إنشاء عقدة zamakana، حجز سياحي،
توظيف، اشتراك تأمين...). `register_commission` **لم يكن ممكن يُبنى
كنداء مباشر لـ`repo.create_commission`** بدون كسر الـschema. القرار
المعتمَد صراحة من المستخدم: جدول منفصل تمامًا (`affiliate_action_commissions`
/ موديل `ActionCommission`)، بدل توسيع الجدول التجاري بأعمدة nullable.

الإصلاح المُطبَّق:
1. Migration `028_create_affiliate_action_commissions` — جدول جديد
   (`tenant_id`, `affiliate_profile_id`, `user_id`, `amount`, `currency`,
   `description`, `entity_type`, `action_type`, `status`, `paid_at`,
   `paid_tx_hash`, timestamps).
2. `AffiliateRepository.create_action_commission(tenant_id, **kwargs)` —
   إضافة صرفة، نفس نمط `create_commission` الموجود.
3. `AffiliateService.register_commission(affiliate_id, user_id, amount,
   description, status="PENDING", entity_type="CROSS_DOMAIN",
   action_type=None)` — تستدعي `get_or_create_profile(affiliate_id)`
   داخليًا لحل التباس نطاق `users.id`/`affiliate_profiles.id` (كل
   الـ12 موضع بيمرروا `affiliate_id=user.referred_by`، وهي قيمة
   `users.id` فعليًا مش `affiliate_profiles.id`).
4. `AffiliateService.get_user_by_code(referral_code)` — wrapper حول
   `repo.get_affiliate_by_code`، يرجع `AffiliateProfile`.
5. إصلاح ضروري ملازم: `digital_twin/service.py` كان بيمرر `referrer.id`
   (profile id) بدل `referrer.user_id` — كان سيُعيد نفس باج خلط النطاق
   اللي البند ده مصمَّم يحله.

**تنبيه صريح متكرر عمدًا (موثَّق في التقرير الأصلي، قسم 8/13):**
`register_commission`/`get_user_by_code` **أنفسهم** يعملون بشكل صحيح
ومعزول (مؤكَّد حيًا هنا وفي الجلسة الأصلية). **لم يُصلَح** استدعاء
الـwrapper الفعلي (`_register_affiliate_commission`) من داخل أي من
الـ12 دومين نفسها — دول لسه هيفشلوا صامتين **قبل** ما يوصلوا حتى
لـ`register_commission`، بسبب ثلاث طبقات فشل سابقة موثَّقة ومفتوحة
مسبقًا، **خارج نطاق هذه الجلسة صراحة**:
- Backlog #1 (`user-repository-get-by-id-audit`): `UserRepository.get_by_id()`
  بتتنادى من 10 من الـ12 دومين بمعامل واحد بس، لكن توقيعها الحقيقي
  يطلب `tenant_id` إجباريًا → `TypeError`.
- Backlog #8 (`user-repository-get-user-audit`): دومينان (`employment`,
  `digital_twin` — قبل أي تعديل هنا) بينادوا `user_repo.get_user()`
  غير الموجودة.
- بند مكتشَف حديثًا (5.3 في التقرير): `User.referred_by` **غير موجود
  إطلاقًا** كحقل على موديل `User` — أي وصول له يرمي `AttributeError`،
  حتى لو #1/#8 اتصلحا.
كل هذه الطبقات مبتلَعة صامتة بنفس `except Exception` — يعني **الفقدان
الصامت الفعلي في الإنتاج لسه قائم اليوم**، رغم إصلاح هذا البند، لحد ما
تُحل الثلاث طبقات دي في جلسات منفصلة مخصَّصة. هذا الملف **لا يختبر
ولا يتظاهر باختبار** استدعاء الـwrapper الفعلي من أي دومين — فقط
`AffiliateService.register_commission`/`get_user_by_code` مباشرة،
بمعزل عن الطبقات المعطوبة فوقها (بنفس منهجية التحقق الحي في التقرير
الأصلي، قسم 13).

**بند Backlog إضافي موثَّق في PROGRESS_LOG.md عند إغلاق هذه الجلسة:**
`affiliate-action-commissions-not-integrated-with-balance` — العمولات
المُسجَّلة عبر `register_commission` تُخزَّن فعليًا الآن في
`affiliate_action_commissions`، لكنها **غير مدموجة** في
`get_affiliate_stats`/`withdraw_commissions`/`release_commissions`/
`get_commissions_by_user` (اللي بتقرأ من `affiliate_commissions`
التجاري فقط) — قرار نطاق صريح (خيار "ج" في التقرير)، يستاهل جلسة
مخصَّصة لأنه بيلمس منطق سحب فلوس حقيقي.
"""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select, delete

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels

from app.core.database import AsyncSessionLocal
from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.affiliate.service import AffiliateService
from app.domains.affiliate.models import ActionCommission, AffiliateProfile

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


async def _cleanup(db, user_ids):
    """تنظيف: action_commissions أولاً (FK)، ثم affiliate_profiles، ثم users."""
    if not user_ids:
        return
    await db.execute(delete(ActionCommission).where(ActionCommission.user_id.in_(user_ids)))
    await db.execute(delete(AffiliateProfile).where(AffiliateProfile.user_id.in_(user_ids)))
    await db.execute(delete(User).where(User.id.in_(user_ids)))
    await db.commit()


# ============================================================
# 1) register_commission — نمط الاستدعاء الحقيقي في الـ12 دومين (بلا
#    entity_type/action_type — كلهم بيمرروا نفس الخمس kwargs بالضبط)
# ============================================================

@pytest.mark.asyncio
async def test_register_commission_default_call_pattern_matches_real_call_sites(db):
    """نفس التوقيع الحرفي المستخدَم في كل الـ12 موضع فعليًا (راجع قسم 4 من
    التقرير) — بلا entity_type/action_type. لازم يتسجَّل بـentity_type
    الافتراضي `CROSS_DOMAIN` و`action_type=None`."""
    referrer = await _create_user(db, "p10_default_referrer")
    actor = await _create_user(db, "p10_default_actor")
    user_ids = [referrer.id, actor.id]

    try:
        svc = AffiliateService(db, TENANT_ID)
        commission = await svc.register_commission(
            affiliate_id=referrer.id,
            user_id=actor.id,
            amount=Decimal("2.00"),
            description="Affiliate commission for ZAMAKANA_TEST",
            status="PENDING",
        )
        assert commission.id is not None

        refreshed = (await db.execute(
            select(ActionCommission).where(ActionCommission.id == commission.id)
        )).scalar_one_or_none()
        assert refreshed is not None, "السجل المتوقع مش موجود على القرص"
        assert refreshed.user_id == actor.id
        assert refreshed.amount == Decimal("2.00")
        assert refreshed.status == "PENDING"
        assert refreshed.entity_type == "CROSS_DOMAIN"
        assert refreshed.action_type is None
        assert refreshed.currency == "MR_USDT"
    finally:
        await _cleanup(db, user_ids)


# ============================================================
# 2) register_commission — نمط نسبة مئوية مع entity_type/action_type
#    صريحين (محاكاة transport: 2%)
# ============================================================

@pytest.mark.asyncio
async def test_register_commission_percentage_pattern_with_explicit_entity_type(db):
    referrer = await _create_user(db, "p10_pct_referrer")
    actor = await _create_user(db, "p10_pct_actor")
    user_ids = [referrer.id, actor.id]

    try:
        svc = AffiliateService(db, TENANT_ID)
        fare = Decimal("100.00")
        commission_amount = fare * Decimal("0.02")

        commission = await svc.register_commission(
            affiliate_id=referrer.id,
            user_id=actor.id,
            amount=commission_amount,
            description="Transport transaction commission",
            status="PENDING",
            entity_type="TRANSPORT",
            action_type="RIDE_COMPLETED",
        )

        refreshed = (await db.execute(
            select(ActionCommission).where(ActionCommission.id == commission.id)
        )).scalar_one_or_none()
        assert refreshed is not None
        assert refreshed.amount == Decimal("2.00000000")
        assert refreshed.entity_type == "TRANSPORT"
        assert refreshed.action_type == "RIDE_COMPLETED"
    finally:
        await _cleanup(db, user_ids)


# ============================================================
# 3) register_commission — نمط مبلغ ثابت (محاكاة tenders_auctions: 25.00
#    ثابت لـAUCTION_WON)
# ============================================================

@pytest.mark.asyncio
async def test_register_commission_flat_amount_pattern(db):
    referrer = await _create_user(db, "p10_flat_referrer")
    actor = await _create_user(db, "p10_flat_actor")
    user_ids = [referrer.id, actor.id]

    try:
        svc = AffiliateService(db, TENANT_ID)
        commission = await svc.register_commission(
            affiliate_id=referrer.id,
            user_id=actor.id,
            amount=Decimal("25.00"),
            description="Affiliate commission for AUCTION_WON",
            status="PENDING",
            entity_type="TENDERS_AUCTIONS",
            action_type="AUCTION_WON",
        )

        refreshed = (await db.execute(
            select(ActionCommission).where(ActionCommission.id == commission.id)
        )).scalar_one_or_none()
        assert refreshed is not None
        assert refreshed.amount == Decimal("25.00000000")
        assert refreshed.entity_type == "TENDERS_AUCTIONS"
    finally:
        await _cleanup(db, user_ids)


# ============================================================
# 4) get_user_by_code — كود صحيح يرجّع AffiliateProfile، كود غير موجود
#    يرجّع None
# ============================================================

@pytest.mark.asyncio
async def test_get_user_by_code_valid_and_invalid(db):
    referrer = await _create_user(db, "p10_code_referrer")
    actor = await _create_user(db, "p10_code_actor")
    user_ids = [referrer.id, actor.id]

    try:
        svc = AffiliateService(db, TENANT_ID)
        # لازم يُنشأ بروفايل أولاً (get_or_create_profile) عشان يكون له referral_code
        profile = await svc.get_or_create_profile(referrer.id)

        found = await svc.get_user_by_code(profile.referral_code)
        assert found is not None
        assert found.id == profile.id
        assert found.user_id == referrer.id

        not_found = await svc.get_user_by_code(f"NOPE-{_suffix()}")
        assert not_found is None
    finally:
        await _cleanup(db, user_ids)


# ============================================================
# 5) المسار الكامل الخاص بـdigital_twin: get_or_create_profile → كود →
#    get_user_by_code(code) → .user_id → register_commission (نفس
#    التصحيح المطبَّق فعليًا في digital_twin/service.py:82)
# ============================================================

@pytest.mark.asyncio
async def test_digital_twin_affiliate_code_pattern_end_to_end(db):
    referrer = await _create_user(db, "p10_twin_referrer")
    actor = await _create_user(db, "p10_twin_actor")
    user_ids = [referrer.id, actor.id]

    try:
        svc = AffiliateService(db, TENANT_ID)
        profile = await svc.get_or_create_profile(referrer.id)

        looked_up = await svc.get_user_by_code(profile.referral_code)
        assert looked_up is not None
        # التصحيح المطبَّق: referrer_id = referrer.user_id (مش referrer.id)
        referrer_id = looked_up.user_id
        assert referrer_id == referrer.id

        commission = await svc.register_commission(
            affiliate_id=referrer_id,
            user_id=actor.id,
            amount=Decimal("5.00"),
            description="Affiliate commission for TWIN_INTERACTION via affiliate_code",
            status="PENDING",
            entity_type="DIGITAL_TWIN",
            action_type="TWIN_INTERACTION",
        )

        refreshed = (await db.execute(
            select(ActionCommission).where(ActionCommission.id == commission.id)
        )).scalar_one_or_none()
        assert refreshed is not None
        assert refreshed.affiliate_profile_id == profile.id, (
            "لو اتمرر referrer.id (profile id) غلط بدل referrer.user_id، "
            "get_or_create_profile كان هيدور على profile.id كأنه user_id "
            "وينشئ بروفايل غلط/يفشل — نفس باج خلط النطاق الموثَّق في التقرير"
        )
    finally:
        await _cleanup(db, user_ids)


# ============================================================
# 6) حالة حافة: نفس affiliate_id عبر جلستين DB منفصلتين تمامًا (مش نفس
#    session) — لازم يعيد استخدام نفس AffiliateProfile، صفر تكرار
# ============================================================

@pytest.mark.asyncio
async def test_register_commission_reuses_same_profile_across_separate_sessions(db):
    """get_or_create_profile لازم تكون idempotent حتى عبر استدعاءين
    بجلستين DB مستقلتين تمامًا (محاكاة طلبين HTTP حقيقيين منفصلين لنفس
    المُحيل) — مش بس داخل نفس session زي التحقق الحي الأصلي في التقرير."""
    referrer = await _create_user(db, "p10_sep_referrer")
    actor = await _create_user(db, "p10_sep_actor")
    user_ids = [referrer.id, actor.id]
    await db.commit()  # لازم يبقى مرئي لجلسات تانية قبل ما نفتحها

    try:
        # الجلسة الأولى (مستقلة عن fixture db)
        async with AsyncSessionLocal() as db1:
            svc1 = AffiliateService(db1, TENANT_ID)
            c1 = await svc1.register_commission(
                affiliate_id=referrer.id,
                user_id=actor.id,
                amount=Decimal("3.00"),
                description="First call — separate session",
                status="PENDING",
            )
            profile1_id = c1.affiliate_profile_id

        # الجلسة الثانية (مستقلة تمامًا كمان، مختلفة عن db1 وعن fixture db)
        async with AsyncSessionLocal() as db2:
            svc2 = AffiliateService(db2, TENANT_ID)
            c2 = await svc2.register_commission(
                affiliate_id=referrer.id,
                user_id=actor.id,
                amount=Decimal("4.00"),
                description="Second call — separate session",
                status="PENDING",
            )
            profile2_id = c2.affiliate_profile_id

        assert profile1_id == profile2_id, (
            "get_or_create_profile أنشأت بروفايلين مختلفين لنفس affiliate_id "
            "عبر جلستين منفصلتين — تكرار غير مقبول"
        )

        # تحقق مستقل إضافي: صف واحد بالضبط في affiliate_profiles
        profiles = (await db.execute(
            select(AffiliateProfile).where(AffiliateProfile.user_id == referrer.id)
        )).scalars().all()
        assert len(profiles) == 1, f"متوقَّع بروفايل واحد بالضبط، لُقي {len(profiles)}"
    finally:
        await _cleanup(db, user_ids)
