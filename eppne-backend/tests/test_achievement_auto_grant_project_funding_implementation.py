"""
regression test لجلسة `achievement-auto-grant-project-funding` (2026-09-15)
— ربط فئة PROJECT_FUNDING بالمنح التلقائي: حدث موجود بالفعل
("project.contribution.received")، بلا أي تعديل على projects، بلا
walk-up، بلا فحص عتبة (منح مباشر لأول مساهمة). راجع:
.claude/reports/achievement-auto-grant-project-funding-session-log.md

هذه آخر فئة من الفئات التلاتة — نظام الإنجازات بالكامل (TEAM_BUILDING،
TRAINING، PROJECT_FUNDING) بيتقفل رسميًا بهذا الاختبار.

يغطي:
1) `ProjectService.add_contribution` بينشر `project.contribution.received`
   بالـpayload الصحيح — تأكيد المفتاح `contributor_id` (مش `user_id`).
2) `AchievementService.grant_project_funding_achievements_for_contribution`:
   أول مساهمة في مشروع throwaway → إنجاز PROJECT_FUNDING يتمنح
   (`granted_by=None`). مساهمة **في مشروع تاني مختلف تمامًا** بنفس
   المستخدم → صفر إنجاز إضافي (التعريف عام، القيد الفريد بيمنع — نفس
   نمط TRAINING بالحرف).
3) المسار الكامل عبر dispatch_critical_event_task.run(...) (نفس نمط
   الفئتين السابقتين — asyncio.to_thread + engine.dispose() bracketing).
"""
import asyncio
import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import delete, select

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal, engine
from app.core.celery_app import celery_app
from app.core.critical_events import CRITICAL_EVENT_HANDLERS

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.projects.service import ProjectService
from app.domains.projects.schemas import ContributionCreate
from app.domains.projects.models import Project, ProjectType, ProjectStatus, ContributionType, Contribution

from app.domains.achievements.service import AchievementService, CONTRIBUTION_RECEIVED_EVENT_NAME
from app.domains.achievements.schemas import AchievementDefinitionCreate
from app.domains.achievements.models import (
    AchievementDefinition, UserAchievement, AchievementCategory, AchievementTriggerType,
)

from app.tasks.events import dispatch_critical_event_task

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


async def _create_project(db, owner_id: int) -> Project:
    # FUNDRAISING مباشرة (مش عبر publish_project) — throwaway بحت
    project = Project(
        tenant_id=TENANT_ID,
        owner_id=owner_id,
        title=f"REGTEST-ACH-FUNDING-PROJECT-{_suffix()}",
        description="مشروع اختباري throwaway لجلسة achievement-auto-grant-project-funding",
        project_type=ProjectType.OTHER,
        status=ProjectStatus.FUNDRAISING,
        funding_goal_mrusdt=Decimal("1000"),
    )
    db.add(project)
    await db.flush()
    return project


def _contribution_payload(project_id: int) -> ContributionCreate:
    # LABOR_HOURS عمدًا — بيتفادى تمامًا مسار FinanceService.transfer
    # (المخصص لـMONETARY بس)، فمش محتاجين رصيد محفظة حقيقي للاختبار.
    return ContributionCreate(
        project_id=project_id,
        contribution_type=ContributionType.LABOR_HOURS,
        labor_hours=Decimal("2"),
        labor_description="REGTEST contribution",
    )


async def _get_user_achievements(user_id: int, definition_id: int) -> list:
    async with AsyncSessionLocal() as verify_db:
        result = await verify_db.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_definition_id == definition_id,
            )
        )
        return list(result.scalars().all())


def test_event_registered_as_critical():
    assert CONTRIBUTION_RECEIVED_EVENT_NAME in CRITICAL_EVENT_HANDLERS
    assert CONTRIBUTION_RECEIVED_EVENT_NAME == "project.contribution.received"


@pytest.mark.asyncio
async def test_add_contribution_publishes_event_with_contributor_id_key(db):
    contributor = await _create_user(db, "p_regtest_ach_funding_publish")
    owner = await _create_user(db, "p_regtest_ach_funding_publish_owner")
    project = await _create_project(db, owner.id)
    await db.commit()

    project_service = ProjectService(db)
    captured_events = []
    original_publish = project_service.event_bus.publish

    async def _spy_publish(event_name, payload):
        captured_events.append((event_name, payload))
        return await original_publish(event_name, payload)

    project_service.event_bus.publish = _spy_publish

    try:
        with patch.object(celery_app, "send_task") as mock_send_task:
            result = await project_service.add_contribution(
                contributor.id, TENANT_ID, _contribution_payload(project.id),
            )

        assert len(captured_events) == 1
        event_name, payload = captured_events[0]
        assert event_name == CONTRIBUTION_RECEIVED_EVENT_NAME
        # المفتاح "contributor_id" مش "user_id" — تأكيد مباشر من تقرير التخطيط
        assert "contributor_id" in payload
        assert "user_id" not in payload
        assert payload == {
            "project_id": project.id,
            "tenant_id": TENANT_ID,
            "contributor_id": contributor.id,
            "amount": 100.0,  # 2 labor_hours * 50
            "contribution_id": result["id"],
        }
        mock_send_task.assert_called_once_with(
            "events.dispatch_critical_event", args=[CONTRIBUTION_RECEIVED_EVENT_NAME, payload], queue="events",
        )
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(Contribution).where(Contribution.project_id == project.id))
            await cleanup_db.execute(delete(Project).where(Project.id == project.id))
            await cleanup_db.execute(delete(User).where(User.id.in_([contributor.id, owner.id])))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_first_contribution_grants_achievement_second_project_does_not(db):
    contributor = await _create_user(db, "p_regtest_ach_funding_grant")
    owner = await _create_user(db, "p_regtest_ach_funding_grant_owner")
    project_1 = await _create_project(db, owner.id)
    project_2 = await _create_project(db, owner.id)
    await db.commit()

    project_service = ProjectService(db)
    achievement_service = AchievementService(db, TENANT_ID)
    definition_id = None
    try:
        definition = await achievement_service.create_definition(
            AchievementDefinitionCreate(
                name="أول مساهمة",
                description="إنجاز اختباري لجلسة achievement-auto-grant-project-funding",
                category=AchievementCategory.PROJECT_FUNDING,
                trigger_type=AchievementTriggerType.AUTO_EVENT,
                trigger_event_name=CONTRIBUTION_RECEIVED_EVENT_NAME,
            ),
            created_by=contributor.id,
        )
        definition_id = definition.id
        assert definition.trigger_threshold is None  # غير مستخدَم لـPROJECT_FUNDING

        # ---- مساهمة أولى في مشروع 1 → منح مباشر ----
        with patch.object(celery_app, "send_task"):
            first_result = await project_service.add_contribution(
                contributor.id, TENANT_ID, _contribution_payload(project_1.id),
            )

        granted = await achievement_service.grant_project_funding_achievements_for_contribution(
            user_id=contributor.id, tenant_id=TENANT_ID,
            contribution_id=first_result["id"], project_id=project_1.id,
        )
        assert granted == [definition_id]

        achievements_after_first = await _get_user_achievements(contributor.id, definition_id)
        assert len(achievements_after_first) == 1
        row = achievements_after_first[0]
        assert row.granted_by is None
        assert row.source_event_name == CONTRIBUTION_RECEIVED_EVENT_NAME
        assert row.source_payload == {"project_id": project_1.id, "contribution_id": first_result["id"]}

        # ---- مساهمة تانية في مشروع 2 مختلف تمامًا → صفر إنجاز إضافي ----
        with patch.object(celery_app, "send_task"):
            second_result = await project_service.add_contribution(
                contributor.id, TENANT_ID, _contribution_payload(project_2.id),
            )

        granted_again = await achievement_service.grant_project_funding_achievements_for_contribution(
            user_id=contributor.id, tenant_id=TENANT_ID,
            contribution_id=second_result["id"], project_id=project_2.id,
        )
        assert granted_again == [], "مشروع تاني — التعريف عام مش خاص بمشروع، مايتمنحش تاني"

        achievements_after_second = await _get_user_achievements(contributor.id, definition_id)
        assert len(achievements_after_second) == 1, "لازم يفضل صف واحد بالظبط، مش اتنين"
        assert achievements_after_second[0].id == row.id, "نفس الصف الأصلي بالظبط"
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(Contribution).where(Contribution.project_id.in_([project_1.id, project_2.id])))
            await cleanup_db.execute(delete(UserAchievement).where(UserAchievement.user_id == contributor.id))
            if definition_id:
                await cleanup_db.execute(delete(AchievementDefinition).where(AchievementDefinition.id == definition_id))
            await cleanup_db.execute(delete(Project).where(Project.id.in_([project_1.id, project_2.id])))
            await cleanup_db.execute(delete(User).where(User.id.in_([contributor.id, owner.id])))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_full_dispatch_path_grants_achievement(db):
    contributor = await _create_user(db, "p_regtest_ach_funding_full")
    owner = await _create_user(db, "p_regtest_ach_funding_full_owner")
    project = await _create_project(db, owner.id)
    await db.commit()
    contributor_id, owner_id = contributor.id, owner.id

    project_service = ProjectService(db)
    achievement_service = AchievementService(db, TENANT_ID)
    definition_id = None
    try:
        definition = await achievement_service.create_definition(
            AchievementDefinitionCreate(
                name="أول مساهمة (dispatch)",
                description="إنجاز اختباري لمسار dispatch الكامل",
                category=AchievementCategory.PROJECT_FUNDING,
                trigger_type=AchievementTriggerType.AUTO_EVENT,
                trigger_event_name=CONTRIBUTION_RECEIVED_EVENT_NAME,
            ),
            created_by=contributor_id,
        )
        definition_id = definition.id

        captured_events = []
        original_publish = project_service.event_bus.publish

        async def _spy_publish(event_name, payload):
            captured_events.append((event_name, payload))
            return await original_publish(event_name, payload)

        project_service.event_bus.publish = _spy_publish

        with patch.object(celery_app, "send_task"):
            await project_service.add_contribution(
                contributor_id, TENANT_ID, _contribution_payload(project.id),
            )

        assert len(captured_events) == 1
        event_name, payload = captured_events[0]
        assert event_name == CONTRIBUTION_RECEIVED_EVENT_NAME

        # محاكاة الـworker — نفس نمط الفئتين السابقتين
        await engine.dispose()
        await asyncio.to_thread(dispatch_critical_event_task.run, event_name, payload)
        await engine.dispose()

        achievements = await _get_user_achievements(contributor_id, definition_id)
        assert len(achievements) == 1
        assert achievements[0].granted_by is None
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(Contribution).where(Contribution.project_id == project.id))
            await cleanup_db.execute(delete(UserAchievement).where(UserAchievement.user_id == contributor_id))
            if definition_id:
                await cleanup_db.execute(delete(AchievementDefinition).where(AchievementDefinition.id == definition_id))
            await cleanup_db.execute(delete(Project).where(Project.id == project.id))
            await cleanup_db.execute(delete(User).where(User.id.in_([contributor_id, owner_id])))
            await cleanup_db.commit()
