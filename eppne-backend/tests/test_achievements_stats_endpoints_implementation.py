"""
regression test لجلسة `achievements-stats-endpoints-implementation` (2026-09-15)
— endpoints إحصائية جديدة على achievements/router.py فقط (صفر تعديل على
أي جدول أو منطق منح موجود). راجع:
.claude/reports/achievements-stats-endpoints-implementation-session-log.md

يغطي:
1) GET /achievements/stats/by-category (عبر AchievementService مباشرة):
   عدد UserAchievement فعلي لكل فئة، بمقارنة delta قبل/بعد منح حقيقي عبر
   3 فئات (TRAINING, TEAM_BUILDING, PROJECT_FUNDING) — أسلوب delta مش
   قيمة مطلقة، لأن فحص مسبق للـDB الحقيقية أثبت وجود صف throwaway واحد
   قديم متبقٍّ فعليًا في TRAINING (REGTEST-ACHIEVEMENT-DUP-* من جلسة
   `achievements-foundation-implementation` — تنظيف `finally` فيها فشل
   جزئيًا)، مش بيانات متراكمة عبر 3 فئات كما افتُرض في تخطيط الجلسة.
2) GET /achievements/stats/top-users: عدد دقيق لكل مستخدم + ترتيب تنازلي
   صحيح.
3) GET /achievements/stats/by-definition: عدد دقيق لكل تعريف + الاسم —
   تعريفات throwaway جديدة (id لسه مش موجود قبل كده) فمفيش حاجة لـdelta
   هنا، القيمة المطلقة صحيحة مباشرة.
4) الحماية الفعلية عبر HTTP حقيقي (httpx.AsyncClient + ASGITransport):
   SUPER_ADMIN يقدر ينادي الـendpoints (200 + بيانات مطابقة للمحسوب مباشرة)،
   مستخدم عادي يترفض (403) — عبر dependency_overrides على
   app.core.security.get_current_active_user (الـsub-dependency الحقيقية
   جوّه get_current_superuser نفسها، فمنطق فحص الدور بيتنفَّذ فعليًا،
   مش متجاوَز بالكامل).
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

from app.domains.achievements.service import AchievementService
from app.domains.achievements.schemas import AchievementDefinitionCreate
from app.domains.achievements.models import AchievementDefinition, UserAchievement, AchievementCategory

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


def _definition_payload(name: str, category: AchievementCategory) -> AchievementDefinitionCreate:
    return AchievementDefinitionCreate(
        name=name,
        description="إنجاز اختباري لجلسة achievements-stats-endpoints-implementation",
        category=category,
    )


@pytest.mark.asyncio
async def test_stats_by_category_and_top_users_match_real_grants(db):
    admin = await _create_user(db, "p_regtest_ach_stats_admin")
    user_a = await _create_user(db, "p_regtest_ach_stats_a")
    user_b = await _create_user(db, "p_regtest_ach_stats_b")
    user_c = await _create_user(db, "p_regtest_ach_stats_c")

    service = AchievementService(db, TENANT_ID)

    # baseline قبل أي منح جديد — يمتص أي صف throwaway قديم متبقٍّ فعليًا
    # (اتأكَّد منه مباشرة ضد DB قبل هذه الجلسة: صف REGTEST-ACHIEVEMENT-DUP-*
    # واحد في TRAINING).
    baseline_by_category = {
        item.category: item.count for item in await service.get_stats_by_category()
    }

    def_ids = []
    try:
        def_training = await service.create_definition(
            _definition_payload(f"REGTEST-ACH-STATS-TRAINING-{_suffix()}", AchievementCategory.TRAINING),
            created_by=admin.id,
        )
        def_ids.append(def_training.id)
        def_team = await service.create_definition(
            _definition_payload(f"REGTEST-ACH-STATS-TEAM-{_suffix()}", AchievementCategory.TEAM_BUILDING),
            created_by=admin.id,
        )
        def_ids.append(def_team.id)
        def_project = await service.create_definition(
            _definition_payload(f"REGTEST-ACH-STATS-PROJECT-{_suffix()}", AchievementCategory.PROJECT_FUNDING),
            created_by=admin.id,
        )
        def_ids.append(def_project.id)

        # TRAINING → أ, ب (2) | TEAM_BUILDING → أ (1) | PROJECT_FUNDING → أ, ب, ج (3)
        await service.grant_achievement(user_a.id, def_training.id, admin.id)
        await service.grant_achievement(user_b.id, def_training.id, admin.id)
        await service.grant_achievement(user_a.id, def_team.id, admin.id)
        await service.grant_achievement(user_a.id, def_project.id, admin.id)
        await service.grant_achievement(user_b.id, def_project.id, admin.id)
        await service.grant_achievement(user_c.id, def_project.id, admin.id)

        # ---- 1) by-category عبر الخدمة مباشرة: delta بالظبط ----
        after_by_category = {
            item.category: item.count for item in await service.get_stats_by_category()
        }
        assert (
            after_by_category[AchievementCategory.TRAINING]
            - baseline_by_category.get(AchievementCategory.TRAINING, 0)
        ) == 2
        assert (
            after_by_category[AchievementCategory.TEAM_BUILDING]
            - baseline_by_category.get(AchievementCategory.TEAM_BUILDING, 0)
        ) == 1
        assert (
            after_by_category[AchievementCategory.PROJECT_FUNDING]
            - baseline_by_category.get(AchievementCategory.PROJECT_FUNDING, 0)
        ) == 3

        # ---- 2) top-users عبر الخدمة مباشرة: عدد دقيق + ترتيب تنازلي صحيح ----
        top_users = await service.get_top_users(limit=50)
        by_user_id = {item.user_id: item for item in top_users}
        assert by_user_id[user_a.id].achievement_count == 3
        assert by_user_id[user_a.id].user_name == user_a.username
        assert by_user_id[user_b.id].achievement_count == 2
        assert by_user_id[user_c.id].achievement_count == 1

        our_users_in_order = [
            item.user_id for item in top_users if item.user_id in (user_a.id, user_b.id, user_c.id)
        ]
        assert our_users_in_order == [user_a.id, user_b.id, user_c.id]

        # ---- 3) by-definition عبر الخدمة مباشرة: قيمة مطلقة (تعريفات throwaway جديدة، صفر تأثير سابق) ----
        by_definition = {
            item.achievement_definition_id: item for item in await service.get_stats_by_definition()
        }
        assert by_definition[def_training.id].count == 2
        assert by_definition[def_training.id].achievement_name == def_training.name
        assert by_definition[def_team.id].count == 1
        assert by_definition[def_project.id].count == 3

        # ---- 4) نفس الأرقام عبر HTTP الفعلي (SUPER_ADMIN) ----
        await db.execute(update(User).where(User.id == admin.id).values(system_role=SystemRole.SUPER_ADMIN))
        await db.commit()

        fastapi_app.dependency_overrides[get_current_active_user] = lambda: admin
        try:
            transport = httpx.ASGITransport(app=fastapi_app)
            async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
                category_response = await client.get("/api/achievements/stats/by-category")
                top_users_response = await client.get(
                    "/api/achievements/stats/top-users", params={"limit": 50}
                )
                by_definition_response = await client.get("/api/achievements/stats/by-definition")
        finally:
            fastapi_app.dependency_overrides.pop(get_current_active_user, None)

        assert category_response.status_code == 200, category_response.text[:500]
        category_body = {row["category"]: row["count"] for row in category_response.json()}
        assert category_body == {k.value: v for k, v in after_by_category.items()}

        assert top_users_response.status_code == 200, top_users_response.text[:500]
        top_users_body = {row["user_id"]: row for row in top_users_response.json()}
        assert top_users_body[user_a.id]["achievement_count"] == 3
        assert top_users_body[user_a.id]["user_name"] == user_a.username
        assert top_users_body[user_b.id]["achievement_count"] == 2
        assert top_users_body[user_c.id]["achievement_count"] == 1

        assert by_definition_response.status_code == 200, by_definition_response.text[:500]
        by_definition_body = {
            row["achievement_definition_id"]: row for row in by_definition_response.json()
        }
        assert by_definition_body[def_training.id]["count"] == 2
        assert by_definition_body[def_training.id]["achievement_name"] == def_training.name
        assert by_definition_body[def_team.id]["count"] == 1
        assert by_definition_body[def_project.id]["count"] == 3
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(
                delete(UserAchievement).where(
                    UserAchievement.user_id.in_([user_a.id, user_b.id, user_c.id])
                )
            )
            if def_ids:
                await cleanup_db.execute(
                    delete(AchievementDefinition).where(AchievementDefinition.id.in_(def_ids))
                )
            await cleanup_db.execute(
                delete(User).where(User.id.in_([admin.id, user_a.id, user_b.id, user_c.id]))
            )
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_stats_endpoints_reject_non_superuser_via_http(db):
    regular_user = await _create_user(db, "p_regtest_ach_stats_regular")

    fastapi_app.dependency_overrides[get_current_active_user] = lambda: regular_user
    try:
        transport = httpx.ASGITransport(app=fastapi_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
            category_response = await client.get("/api/achievements/stats/by-category")
            top_users_response = await client.get("/api/achievements/stats/top-users")
            by_definition_response = await client.get("/api/achievements/stats/by-definition")
    finally:
        fastapi_app.dependency_overrides.pop(get_current_active_user, None)

    assert category_response.status_code == 403, category_response.text[:500]
    assert top_users_response.status_code == 403, top_users_response.text[:500]
    assert by_definition_response.status_code == 403, by_definition_response.text[:500]

    async with AsyncSessionLocal() as cleanup_db:
        await cleanup_db.execute(delete(User).where(User.id == regular_user.id))
        await cleanup_db.commit()
