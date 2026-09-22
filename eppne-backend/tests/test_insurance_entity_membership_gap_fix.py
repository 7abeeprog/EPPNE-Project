"""
regression test لجلسة `insurance-entity-membership-gap-fix` (2026-09-10).
تقرير الجلسة: .claude/reports/insurance-entity-membership-gap-fix-session-log.md

السياق: جلسة سابقة (`insurance-entity-membership-pattern-extraction`) وثَّقت
إن فحص عضوية الكيان (EntityMembershipService) في insurance كان جزئيًا —
مطبَّق فقط في review_claim، غايب تمامًا عن create_policy/update_policy. أي
مستخدم superuser كان يقدر ينشئ/يعدّل بوليصة باسم أي كيان سيادي بدون ما يكون
عضو فيه إطلاقًا. هذه الجلسة سدّت الفجوة في الدالتين، وصحّحت أيضًا
issuer_entity_id.ondelete من CASCADE لـSET NULL (migration 049) — حذف كيان
سيادي كان بيمسح كل بوالصه تلقائيًا (خطر بيانات مالية)، دلوقتي بيسيب
البوليصة موجودة بسجلها التاريخي مع issuer_entity_id=NULL.

هذا الاختبار يتحقق حيًا (DB حقيقية، صفر mock) من:
1. create_policy: عضو OWNER/EXECUTIVE_DIRECTOR ينجح، غير العضو يترفض 403.
2. update_policy: نفس المنطق باستخدام policy.issuer_entity_id الموجودة.
3. subscribe: **لم تُلمَس عمدًا** — مستخدم عادي مش عضو في أي كيان لسه يقدر
   يشترك بدون أي فحص عضوية (تأكيد صريح إن التغيير ما أثّرش عليها).
4. migration 049: حذف الكيان المُصدِر يسيب البوليصة موجودة بـ
   issuer_entity_id=NULL بدل ما يمسحها (CASCADE القديم).

يعيد استخدام صف throwaway الموجود بالفعل تحت tenant_id=1
(sovereign_entities_v2 id=4) كـissuer_entity_id لاختبارات 1-3، بنفس نمط
test_insurance_getter_endpoints_wiring.py — قراءة فقط، صفر تعديل/حذف عليه.
اختبار #4 ينشئ وبيمسح كيانًا throwaway منفصلًا بالكامل (خاص به وحده) عشان
يثبت سلوك SET NULL الفعلي عند الحذف.
"""
import uuid
from decimal import Decimal
from datetime import datetime

import pytest
from sqlalchemy import delete, select

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.core.errors import PermissionDeniedError

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.insurance.service import InsuranceService, ENTITY_TYPE
from app.domains.insurance.repository import InsuranceRepository
from app.domains.insurance.models import InsurancePolicy, InsuranceSubscription, PolicyType, PremiumCycle

from app.domains.sovereign_entities.models import SovereignEntity, SovereignEntityType
from app.core.models import EntityMembership, EntityMembershipRole

TENANT_ID = 1
EXISTING_ISSUER_ENTITY_ID = 4


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


async def _add_membership(db, *, entity_id: int, user_id: int, role: EntityMembershipRole) -> None:
    db.add(EntityMembership(
        entity_type=ENTITY_TYPE, entity_id=entity_id,
        user_id=user_id, tenant_id=TENANT_ID, role=role,
    ))
    await db.commit()


async def _cleanup_membership(db, *, entity_id: int, user_id: int) -> None:
    await db.execute(delete(EntityMembership).where(
        EntityMembership.entity_type == ENTITY_TYPE,
        EntityMembership.entity_id == entity_id,
        EntityMembership.user_id == user_id,
    ))
    await db.commit()


def _policy_payload(**overrides) -> dict:
    payload = {
        "issuer_entity_id": EXISTING_ISSUER_ENTITY_ID,
        "name": f"REGTEST-GAPFIX-POLICY-{_suffix()}",
        "policy_type": PolicyType.ACCIDENT,
        "base_premium_mrusdt": Decimal("10"),
        "premium_cycle": PremiumCycle.MONTHLY,
        "max_coverage_limit_mrusdt": Decimal("500"),
    }
    payload.update(overrides)
    return payload


# ============================================================
# 1) create_policy — عضو ينجح، غير العضو يترفض
# ============================================================

@pytest.mark.asyncio
async def test_create_policy_owner_succeeds_non_member_rejected(db):
    owner = await _create_user(db, "p_regtest_gapfix_create_owner")
    outsider = await _create_user(db, "p_regtest_gapfix_create_outsider")
    await _add_membership(db, entity_id=EXISTING_ISSUER_ENTITY_ID, user_id=owner.id, role=EntityMembershipRole.OWNER)

    service = InsuranceService(db)
    policy_id = None
    try:
        policy = await service.create_policy(user_id=owner.id, tenant_id=TENANT_ID, data=_policy_payload())
        policy_id = policy.id
        assert policy.issuer_entity_id == EXISTING_ISSUER_ENTITY_ID

        with pytest.raises(PermissionDeniedError):
            await service.create_policy(user_id=outsider.id, tenant_id=TENANT_ID, data=_policy_payload())
    finally:
        if policy_id is not None:
            await db.execute(delete(InsurancePolicy).where(InsurancePolicy.id == policy_id))
            await db.commit()
        await _cleanup_membership(db, entity_id=EXISTING_ISSUER_ENTITY_ID, user_id=owner.id)
        await db.execute(delete(User).where(User.id.in_([owner.id, outsider.id])))
        await db.commit()


# ============================================================
# 2) update_policy — نفس المنطق، باستخدام policy.issuer_entity_id الموجودة
# ============================================================

@pytest.mark.asyncio
async def test_update_policy_member_succeeds_non_member_rejected(db):
    creator = await _create_user(db, "p_regtest_gapfix_update_creator")
    member = await _create_user(db, "p_regtest_gapfix_update_member")
    outsider = await _create_user(db, "p_regtest_gapfix_update_outsider")

    repo = InsuranceRepository(db)
    policy = await repo.create_policy(tenant_id=TENANT_ID, created_by=creator.id, **_policy_payload())
    await db.commit()
    policy_id = policy.id

    await _add_membership(
        db, entity_id=EXISTING_ISSUER_ENTITY_ID, user_id=member.id,
        role=EntityMembershipRole.EXECUTIVE_DIRECTOR,
    )

    service = InsuranceService(db)
    try:
        with pytest.raises(PermissionDeniedError):
            await service.update_policy(policy_id, TENANT_ID, reviewer_id=outsider.id, data={"name": "hacked"})

        result = await service.update_policy(
            policy_id, TENANT_ID, reviewer_id=member.id, data={"name": "REGTEST-GAPFIX-UPDATED"},
        )
        assert result.name == "REGTEST-GAPFIX-UPDATED"
    finally:
        await db.execute(delete(InsurancePolicy).where(InsurancePolicy.id == policy_id))
        await db.commit()
        await _cleanup_membership(db, entity_id=EXISTING_ISSUER_ENTITY_ID, user_id=member.id)
        await db.execute(delete(User).where(User.id.in_([creator.id, member.id, outsider.id])))
        await db.commit()


# ============================================================
# 3) subscribe — لم تُلمَس: مستخدم عادي (صفر عضوية) لسه يقدر يشترك
# ============================================================

@pytest.mark.asyncio
async def test_subscribe_still_works_for_non_member_user(db):
    subscriber = await _create_user(db, "p_regtest_gapfix_subscribe_user")

    # إثبات صريح إن subscriber مش عضو في أي كيان إطلاقًا
    existing_memberships = (await db.execute(
        select(EntityMembership).where(EntityMembership.user_id == subscriber.id)
    )).scalars().all()
    assert existing_memberships == []

    repo = InsuranceRepository(db)
    policy = await repo.create_policy(
        tenant_id=TENANT_ID, created_by=subscriber.id,
        **_policy_payload(base_premium_mrusdt=Decimal("0"), max_coverage_limit_mrusdt=Decimal("100")),
    )
    await db.commit()
    policy_id = policy.id

    service = InsuranceService(db)
    subscription_id = None
    try:
        subscription = await service.subscribe(
            user_id=subscriber.id, tenant_id=TENANT_ID,
            data={
                "policy_id": policy_id, "subscriber_user_id": subscriber.id,
                "start_date": datetime.utcnow(),
            },
            idempotency_key=f"REGTEST-GAPFIX-SUB-{_suffix()}",
        )
        subscription_id = subscription.id
        assert subscription.status == "ACTIVE"
    finally:
        if subscription_id is not None:
            await db.execute(delete(InsuranceSubscription).where(InsuranceSubscription.id == subscription_id))
        await db.execute(delete(InsurancePolicy).where(InsurancePolicy.id == policy_id))
        await db.commit()
        await db.execute(delete(User).where(User.id == subscriber.id))
        await db.commit()


# ============================================================
# 4) migration 049 — حذف الكيان المُصدِر يسيب البوليصة بـissuer_entity_id=NULL
# ============================================================

@pytest.mark.asyncio
async def test_issuer_entity_deletion_sets_null_not_cascade(db):
    creator = await _create_user(db, "p_regtest_gapfix_setnull_creator")

    throwaway_entity = SovereignEntity(
        tenant_id=TENANT_ID,
        name=f"REGTEST-GAPFIX-ENTITY-{_suffix()}",
        entity_type=SovereignEntityType.ENTERPRISE,
        country_of_origin="EG",
        official_email=f"regtest-gapfix-entity-{_suffix()}@eppne.com",
        created_by=creator.id,
    )
    db.add(throwaway_entity)
    await db.commit()
    await db.refresh(throwaway_entity)
    entity_id = throwaway_entity.id

    repo = InsuranceRepository(db)
    policy = await repo.create_policy(
        tenant_id=TENANT_ID, created_by=creator.id,
        **_policy_payload(issuer_entity_id=entity_id),
    )
    await db.commit()
    policy_id = policy.id

    try:
        await db.execute(delete(SovereignEntity).where(SovereignEntity.id == entity_id))
        await db.commit()
        # ON DELETE SET NULL بيتنفَّذ جوّه Postgres مباشرة (مش عبر الـORM) —
        # الـidentity map في `db` محتفظة بالـobject القديم (issuer_entity_id
        # قبل الحذف)، فالتحقق لازم يبقى بجلسة منفصلة تمامًا عشان تقرأ القيمة
        # الحقيقية من القرص (expire_all() هنا كان بيكسر creator.id في finally
        # لاحقًا — lazy-load متزامن غير مسموح في AsyncSession).
        async with AsyncSessionLocal() as verify_db:
            refreshed = (await verify_db.execute(
                select(InsurancePolicy).where(InsurancePolicy.id == policy_id)
            )).scalar_one_or_none()
        assert refreshed is not None, (
            "البوليصة اتمسحت مع الكيان — يعني الـondelete لسه CASCADE ومش SET NULL "
            "(migration 049 مش مطبَّقة أو فشلت)"
        )
        assert refreshed.issuer_entity_id is None
    finally:
        await db.execute(delete(InsurancePolicy).where(InsurancePolicy.id == policy_id))
        await db.commit()
        await db.execute(delete(User).where(User.id == creator.id))
        await db.commit()
