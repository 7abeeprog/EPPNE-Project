"""
regression test لجلسة `frontend-category-b-phase2-remaining-domains` (2026-09-02).
تقرير الجلسة: .claude/reports/frontend-category-b-phase2-session-log.md

السياق: `SocialRepository` كانت تملك get_post, get_group, get_contract,
get_match_profile, get_active_subscription_for_group جاهزة (بعضها
مستخدَم داخليًا فقط، مثل get_contract في sign_contract) بدون service
wrapper عام ولا router endpoint. هذا الاختبار يتحقق حيًا (DB حقيقية)
من الإضافات الخمس، بما فيها تحقق عزل tenant_id.

ملاحظة مهمة اتضحت أثناء هذه الجلسة: بعض دوال repository.py (مثل
update_claim في insurance) تستخدم flush() فقط بدون commit() — أي
تعديل عبر service methods زي دي لازم commit صريح قبل أي تنظيف (finally)
بجلسة db منفصلة، وإلا هتقفل (deadlock) على قفل الصف. اتّبعنا نفس
الاحتياط هنا لكل عملية create/update تمر عبر flush فقط.
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

from app.domains.social.service import SocialService
from app.domains.social.repository import SocialRepository
from app.domains.social.models import (
    Post, SocialGroup, GroupMember, SocialSmartContract, AIMatchProfile,
    GroupSubscriptionPlan, GroupSubscription,
)

TENANT_ID = 1
OTHER_TENANT_ID = 2


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
async def test_get_post_real_record_and_tenant_isolation(db):
    author = await _create_user(db, "p_regtest_social_post_author")
    repo = SocialRepository(db)
    post = await repo.create_post(tenant_id=TENANT_ID, author_id=author.id, content="REGTEST post")
    post_id = post.id

    service = SocialService(db)
    try:
        result = await service.get_post(post_id, TENANT_ID)
        assert result.id == post_id

        with pytest.raises(NotFoundError):
            await service.get_post(post_id, OTHER_TENANT_ID)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(Post).where(Post.id == post_id))
            await cleanup_db.execute(delete(User).where(User.id == author.id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_get_group_real_record_and_tenant_isolation(db):
    creator = await _create_user(db, "p_regtest_social_group_creator")
    repo = SocialRepository(db)
    group = await repo.create_group(tenant_id=TENANT_ID, creator_id=creator.id, name=f"REGTEST-GROUP-{_suffix()}")
    group_id = group.id

    service = SocialService(db)
    try:
        result = await service.get_group(group_id, TENANT_ID)
        assert result.id == group_id

        with pytest.raises(NotFoundError):
            await service.get_group(group_id, OTHER_TENANT_ID)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(GroupMember).where(GroupMember.group_id == group_id))
            await cleanup_db.execute(delete(SocialGroup).where(SocialGroup.id == group_id))
            await cleanup_db.execute(delete(User).where(User.id == creator.id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_get_contract_real_record_and_tenant_isolation(db):
    creator = await _create_user(db, "p_regtest_social_contract_creator")
    repo = SocialRepository(db)
    contract = await repo.create_contract(
        tenant_id=TENANT_ID, creator_id=creator.id, contract_type="SERVICE",
        title=f"REGTEST-CONTRACT-{_suffix()}", terms_and_conditions={}, status="DRAFT",
    )
    contract_id = contract.id

    service = SocialService(db)
    try:
        result = await service.get_contract(contract_id, TENANT_ID)
        assert result.id == contract_id

        with pytest.raises(NotFoundError):
            await service.get_contract(contract_id, OTHER_TENANT_ID)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(SocialSmartContract).where(SocialSmartContract.id == contract_id))
            await cleanup_db.execute(delete(User).where(User.id == creator.id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_get_match_profile_real_record_and_tenant_isolation(db):
    user = await _create_user(db, "p_regtest_social_match_user")
    repo = SocialRepository(db)
    profile = await repo.create_or_update_match_profile(
        user_id=user.id, data={"tenant_id": TENANT_ID, "seek_type": ["FRIENDSHIP"], "ai_preferences": {}},
    )
    await db.commit()
    profile_id = profile.id

    service = SocialService(db)
    try:
        result = await service.get_match_profile(user.id, TENANT_ID)
        assert result.id == profile_id

        with pytest.raises(NotFoundError):
            await service.get_match_profile(user.id, OTHER_TENANT_ID)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(AIMatchProfile).where(AIMatchProfile.id == profile_id))
            await cleanup_db.execute(delete(User).where(User.id == user.id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_get_group_subscription_active_and_tenant_isolation(db):
    creator = await _create_user(db, "p_regtest_social_sub_creator")
    repo = SocialRepository(db)
    group = await repo.create_group(tenant_id=TENANT_ID, creator_id=creator.id, name=f"REGTEST-SUBGROUP-{_suffix()}")
    plan = await repo.create_subscription_plan(
        tenant_id=TENANT_ID, name=f"REGTEST-PLAN-{_suffix()}",
        price_monthly_mrusdt=Decimal("10"), price_yearly_mrusdt=Decimal("100"),
    )
    subscription = await repo.create_group_subscription(
        tenant_id=TENANT_ID, group_id=group.id, plan_id=plan.id,
        start_date=datetime.utcnow(), end_date=datetime.utcnow() + timedelta(days=30), status="ACTIVE",
    )
    await db.commit()
    group_id, plan_id, sub_id = group.id, plan.id, subscription.id

    service = SocialService(db)
    try:
        result = await service.get_group_subscription(group_id, TENANT_ID)
        assert result is not None
        assert result.id == sub_id

        result_wrong_tenant = await service.get_group_subscription(group_id, OTHER_TENANT_ID)
        assert result_wrong_tenant is None
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(GroupSubscription).where(GroupSubscription.id == sub_id))
            await cleanup_db.execute(delete(GroupSubscriptionPlan).where(GroupSubscriptionPlan.id == plan_id))
            await cleanup_db.execute(delete(GroupMember).where(GroupMember.group_id == group_id))
            await cleanup_db.execute(delete(SocialGroup).where(SocialGroup.id == group_id))
            await cleanup_db.execute(delete(User).where(User.id == creator.id))
            await cleanup_db.commit()
