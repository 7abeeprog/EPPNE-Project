"""
regression test لجلسة `frontend-category-b-phase2-remaining-domains` (2026-09-02).
تقرير الجلسة: .claude/reports/frontend-category-b-phase2-session-log.md

السياق: عدة دوال في `InsuranceRepository` كانت جاهزة بدون service
wrapper ولا router endpoint: get_claim, update_claim, get_pension,
update_pension, get_subscription, update_employee_profile. أضفنا أيضًا
suspend_pension/cancel_subscription/update_policy كعمليات مخصَّصة تحاكي
نمط renew_subscription/review_claim الموجود بالفعل.
هذا الاختبار يتحقق حيًا (DB حقيقية) من كل الإضافات، بما فيها تحقق عزل
tenant_id (get_claim/get_pension/get_subscription/update_policy) وتحقق
ownership (cancel_subscription).

يعيد استخدام صف throwaway الموجود بالفعل تحت tenant_id=1
(sovereign_entities_v2 id=4) كـissuer_entity_id، بنفس نمط
test_saas_active_subscription.py — قراءة فقط، صفر تعديل/حذف عليه.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timedelta

import pytest
from sqlalchemy import delete

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.core.errors import NotFoundError

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.insurance.service import InsuranceService, ENTITY_TYPE as INSURANCE_ENTITY_TYPE
from app.domains.insurance.repository import InsuranceRepository
from app.domains.insurance.models import (
    InsurancePolicy, InsuranceSubscription, InsuranceClaim, PensionRecord,
    EmployeeInsuranceProfile, PolicyType, PremiumCycle, PensionStatus,
)
from app.core.models import EntityMembership, EntityMembershipRole

TENANT_ID = 1
OTHER_TENANT_ID = 2
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


@pytest.mark.asyncio
async def test_update_policy_real_record_and_tenant_isolation(db):
    """[2026-09-10] بعد إصلاح فجوة الصلاحيات في update_policy (راجع
    .claude/reports/insurance-entity-membership-gap-fix-session-log.md)،
    reviewer_id لازم يكون عضو OWNER/EXECUTIVE_DIRECTOR على issuer_entity_id
    البوليصة — عضوية throwaway بتتحط هنا وتتنضف في finally."""
    user = await _create_user(db, "p_regtest_ins_policy_user")
    repo = InsuranceRepository(db)
    policy = await repo.create_policy(
        tenant_id=TENANT_ID, issuer_entity_id=EXISTING_ISSUER_ENTITY_ID,
        name=f"REGTEST-POLICY-{_suffix()}", policy_type=PolicyType.ACCIDENT,
        base_premium_mrusdt=Decimal("10"), premium_cycle=PremiumCycle.MONTHLY,
        max_coverage_limit_mrusdt=Decimal("500"), created_by=user.id,
    )
    policy_id = policy.id

    db.add(EntityMembership(
        entity_type=INSURANCE_ENTITY_TYPE, entity_id=EXISTING_ISSUER_ENTITY_ID,
        user_id=user.id, tenant_id=TENANT_ID, role=EntityMembershipRole.OWNER,
    ))
    await db.commit()

    service = InsuranceService(db)
    try:
        with pytest.raises(NotFoundError):
            await service.update_policy(policy_id, OTHER_TENANT_ID, reviewer_id=user.id, data={"name": "hacked"})

        result = await service.update_policy(policy_id, TENANT_ID, reviewer_id=user.id, data={"name": "REGTEST-UPDATED"})
        assert result.name == "REGTEST-UPDATED"
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(InsurancePolicy).where(InsurancePolicy.id == policy_id))
            await cleanup_db.execute(delete(EntityMembership).where(
                EntityMembership.entity_type == INSURANCE_ENTITY_TYPE,
                EntityMembership.entity_id == EXISTING_ISSUER_ENTITY_ID,
                EntityMembership.user_id == user.id,
            ))
            await cleanup_db.execute(delete(User).where(User.id == user.id))
            await cleanup_db.commit()


async def _setup_subscription(db, *, subscriber_id: int):
    repo = InsuranceRepository(db)
    suffix = _suffix()
    policy = await repo.create_policy(
        tenant_id=TENANT_ID, issuer_entity_id=EXISTING_ISSUER_ENTITY_ID,
        name=f"REGTEST-SUBPOLICY-{suffix}", policy_type=PolicyType.MEDICAL,
        base_premium_mrusdt=Decimal("15"), premium_cycle=PremiumCycle.MONTHLY,
        max_coverage_limit_mrusdt=Decimal("1000"), created_by=subscriber_id,
    )
    subscription = await repo.create_subscription(
        tenant_id=TENANT_ID, policy_id=policy.id, subscriber_user_id=subscriber_id,
        start_date=datetime.utcnow(), status="ACTIVE",
    )
    return policy, subscription


@pytest.mark.asyncio
async def test_get_subscription_and_cancel_subscription(db):
    subscriber = await _create_user(db, "p_regtest_ins_sub_subscriber")
    other_user = await _create_user(db, "p_regtest_ins_sub_other")
    policy, subscription = await _setup_subscription(db, subscriber_id=subscriber.id)

    service = InsuranceService(db)
    try:
        result = await service.get_subscription(subscription.id, TENANT_ID)
        assert result.id == subscription.id

        with pytest.raises(NotFoundError):
            await service.get_subscription(subscription.id, OTHER_TENANT_ID)

        with pytest.raises(NotFoundError):
            await service.cancel_subscription(subscription.id, other_user.id)

        cancelled = await service.cancel_subscription(subscription.id, subscriber.id)
        assert cancelled.status == "CANCELLED"
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(InsuranceSubscription).where(InsuranceSubscription.id == subscription.id))
            await cleanup_db.execute(delete(InsurancePolicy).where(InsurancePolicy.id == policy.id))
            await cleanup_db.execute(delete(User).where(User.id.in_([subscriber.id, other_user.id])))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_get_claim_and_update_claim(db):
    claimant = await _create_user(db, "p_regtest_ins_claim_claimant")
    policy, subscription = await _setup_subscription(db, subscriber_id=claimant.id)

    repo = InsuranceRepository(db)
    claim = await repo.create_claim(
        tenant_id=TENANT_ID, subscription_id=subscription.id, claimant_user_id=claimant.id,
        incident_date=datetime.utcnow(), incident_description="REGTEST incident",
        claimed_amount_mrusdt=Decimal("100"),
    )
    await db.commit()

    service = InsuranceService(db)
    try:
        result = await service.get_claim(claim.id, TENANT_ID)
        assert result.id == claim.id

        with pytest.raises(NotFoundError):
            await service.get_claim(claim.id, OTHER_TENANT_ID)

        updated = await service.update_claim(claim.id, TENANT_ID, {"investigation_notes": "REGTEST note"})
        assert updated.investigation_notes == "REGTEST note"
        await db.commit()  # update_claim's repo layer only flushes (matches review_claim's
        # transactional design, which commits at a higher level) — commit explicitly here so
        # the finally block's separate cleanup session isn't blocked waiting on this row's lock.
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(InsuranceClaim).where(InsuranceClaim.id == claim.id))
            await cleanup_db.execute(delete(InsuranceSubscription).where(InsuranceSubscription.id == subscription.id))
            await cleanup_db.execute(delete(InsurancePolicy).where(InsurancePolicy.id == policy.id))
            await cleanup_db.execute(delete(User).where(User.id == claimant.id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_get_pension_update_pension_suspend_pension(db):
    beneficiary = await _create_user(db, "p_regtest_ins_pension_beneficiary")
    repo = InsuranceRepository(db)
    pension = await repo.create_pension(
        tenant_id=TENANT_ID, beneficiary_id=beneficiary.id, pension_type="RETIREMENT",
        monthly_amount_mrusdt=Decimal("50"), start_date=datetime.utcnow(),
    )
    pension_id = pension.id

    service = InsuranceService(db)
    try:
        result = await service.get_pension(pension_id, TENANT_ID)
        assert result.id == pension_id

        with pytest.raises(NotFoundError):
            await service.get_pension(pension_id, OTHER_TENANT_ID)

        updated = await service.update_pension(pension_id, TENANT_ID, {"monthly_amount_mrusdt": Decimal("75")})
        assert updated.monthly_amount_mrusdt == Decimal("75")

        suspended = await service.suspend_pension(pension_id, TENANT_ID)
        assert suspended.status == PensionStatus.SUSPENDED
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(PensionRecord).where(PensionRecord.id == pension_id))
            await cleanup_db.execute(delete(User).where(User.id == beneficiary.id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_update_employee_profile_real_record(db):
    user = await _create_user(db, "p_regtest_ins_empprofile_user")
    repo = InsuranceRepository(db)
    profile = await repo.create_employee_profile(
        tenant_id=TENANT_ID, user_id=user.id,
        government_insurance_number=f"REGTEST-{_suffix()}",
        employee_share_percentage=Decimal("5"), employer_share_percentage=Decimal("10"),
    )
    profile_id = profile.id

    service = InsuranceService(db)
    try:
        updated = await service.update_employee_profile(user.id, {"employee_share_percentage": Decimal("7")})
        assert updated.employee_share_percentage == Decimal("7")
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(EmployeeInsuranceProfile).where(EmployeeInsuranceProfile.id == profile_id))
            await cleanup_db.execute(delete(User).where(User.id == user.id))
            await cleanup_db.commit()
