# app/domains/achievements/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from typing import List

from app.domains.achievements.repository import AchievementRepository
from app.domains.achievements.models import AchievementDefinition, UserAchievement, AchievementCategory
from app.domains.achievements.schemas import (
    AchievementDefinitionCreate, AchievementCategoryStatItem, AchievementTopUserItem,
    AchievementDefinitionStatItem,
)
from app.domains.identity.repository import UserRepository
from app.core.errors import NotFoundError, AlreadyExistsError

# أسماء الأحداث المُشغِّلة — نفس القيم المنشورة فعليًا من
# academy/service.py (enroll_in_course / update_progress) ومُسجَّلة في
# app/core/critical_events.py. ثوابت محلية لتفادي تكرار الـstring literal
# داخل نفس الملف بس (مش pattern عام في المشروع — الأحداث التانية كلها
# strings حرة، راجع achievement-trigger-events-inventory-session-log.md).
BOOTCAMP_ENROLLMENT_EVENT_NAME = "academy.bootcamp_enrollment.created"
COURSE_COMPLETED_EVENT_NAME = "academy.course.completed"
# مُنشَر بالفعل من projects/service.py (add_contribution) — صفر تعديل
# على projects نفسها في هذه الجلسة. ⚠️ payload المصدر بيستخدم
# "contributor_id" مش "user_id" — راجع
# achievement-project-funding-category-planning-session-log.md.
CONTRIBUTION_RECEIVED_EVENT_NAME = "project.contribution.received"


class AchievementService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = AchievementRepository(db)

    # ============================================================
    # 1. تعريفات الإنجازات (Admin)
    # ============================================================

    async def create_definition(
        self, data: AchievementDefinitionCreate, created_by: int,
    ) -> AchievementDefinition:
        definition = await self.repo.create_definition(
            tenant_id=self.tenant_id,
            created_by=created_by,
            **data.model_dump(),
        )
        await self.db.commit()
        return definition

    async def list_definitions(self, skip: int = 0, limit: int = 100) -> List[AchievementDefinition]:
        return await self.repo.list_definitions(self.tenant_id, skip, limit)

    # ============================================================
    # 2. منح الإنجازات — يدوي فقط في هذه المرحلة (Admin)
    # ============================================================

    async def grant_achievement(
        self,
        user_id: int,
        achievement_definition_id: int,
        granted_by: int,
    ) -> UserAchievement:
        """منح يدوي بحت — granted_by=current_user.id، source_event_name=None
        دايمًا. المنح التلقائي عبر أحداث (AUTO_EVENT) مرحلة قادمة، مش هنا."""
        definition = await self.repo.get_definition(achievement_definition_id, self.tenant_id)
        if not definition:
            raise NotFoundError("تعريف الإنجاز غير موجود")

        user_repo = UserRepository(self.db)
        user = await user_repo.get_by_id(user_id, self.tenant_id)
        if not user:
            raise NotFoundError("المستخدم غير موجود")

        existing = await self.repo.get_user_achievement(user_id, achievement_definition_id)
        if existing:
            raise AlreadyExistsError("هذا المستخدم حاصل بالفعل على هذا الإنجاز")

        try:
            achievement = await self.repo.create_user_achievement(
                tenant_id=self.tenant_id,
                user_id=user_id,
                achievement_definition_id=achievement_definition_id,
                granted_by=granted_by,
                source_event_name=None,
                source_payload=None,
            )
            await self.db.commit()
        except IntegrityError:
            # نفس نمط transport/service.py: القيد الفريد على مستوى DB هو
            # الحارس النهائي (سباق نظري لو نفس المنح اتبعت مرتين بالتوازي
            # بين الـpre-check فوق والـcommit هنا).
            await self.db.rollback()
            raise AlreadyExistsError("هذا المستخدم حاصل بالفعل على هذا الإنجاز")

        return achievement

    # ============================================================
    # 3. عرض إنجازات مستخدم
    # ============================================================

    async def get_user_achievements(self, user_id: int) -> List[UserAchievement]:
        return await self.repo.list_user_achievements(user_id, self.tenant_id)

    # ============================================================
    # 3ب. إحصائيات (Admin)
    # ============================================================

    async def get_stats_by_category(self) -> List[AchievementCategoryStatItem]:
        rows = await self.repo.count_user_achievements_by_category(self.tenant_id)
        return [AchievementCategoryStatItem(category=row[0], count=row[1]) for row in rows]

    async def get_top_users(self, limit: int) -> List[AchievementTopUserItem]:
        rows = await self.repo.get_top_users_by_achievement_count(self.tenant_id, limit)
        return [
            AchievementTopUserItem(user_id=row[0], user_name=row[1], achievement_count=row[2])
            for row in rows
        ]

    async def get_stats_by_definition(self) -> List[AchievementDefinitionStatItem]:
        rows = await self.repo.count_users_by_achievement_definition(self.tenant_id)
        return [
            AchievementDefinitionStatItem(achievement_definition_id=row[0], achievement_name=row[1], count=row[2])
            for row in rows
        ]

    # ============================================================
    # 4. تتبّع الشبكة (walk-up) + منح تلقائي عند تجاوز العتبة (TEAM_BUILDING)
    # ============================================================

    async def update_bootcamp_network_stats(
        self, user_id: int, tenant_id: int, max_depth: int = 8,
    ) -> List[int]:
        """يمشي فوق سلسلة `users.referred_by_user_id` بدءًا من `user_id`
        لحد `max_depth` مستويات، ويزوّد `bootcamp_network_size` لكل سلف
        بـ1 (INSERT...ON CONFLICT DO UPDATE ذرّي في الـrepo، مش SELECT ثم
        UPDATE). بعد كل UPDATE ناجح على سلف، بتفحص فورًا كل
        `AchievementDefinition` نشط من فئة TEAM_BUILDING مربوط بنفس اسم
        الحدث — لو القيمة الجديدة تجاوزت `trigger_threshold`، تمنح
        الإنجاز تلقائيًا (`granted_by=None`) عبر INSERT...ON CONFLICT DO
        NOTHING (القيد الفريد بيمنع أي تكرار، بلا SELECT أول). بيرجع
        قايمة user_ids اللي اتحدّثوا فعليًا (الأقرب أولًا)."""
        updated_user_ids: List[int] = []
        current_id = user_id
        ancestor_level = 0
        for _ in range(max_depth):
            referrer_id = await self.repo.get_referred_by_user_id(current_id)
            if referrer_id is None:
                break
            ancestor_level += 1

            new_network_size = await self.repo.increment_bootcamp_network_size(referrer_id, tenant_id)
            updated_user_ids.append(referrer_id)

            await self._check_and_grant_team_building_achievements(
                tenant_id=tenant_id,
                ancestor_id=referrer_id,
                new_network_size=new_network_size,
                ancestor_level=ancestor_level,
            )

            current_id = referrer_id

        if updated_user_ids:
            await self.db.commit()

        return updated_user_ids

    async def _check_and_grant_team_building_achievements(
        self,
        tenant_id: int,
        ancestor_id: int,
        new_network_size: int,
        ancestor_level: int,
    ) -> None:
        """فحص عتبات TEAM_BUILDING فقط. `trigger_type=AUTO_EVENT` شرط
        إضافي هنا (مش مذكور صراحة في المواصفة الأصلية) — الحقل مُصمَّم
        خصيصًا للتمييز عن تعريفات MANUAL؛ فحصه هنا يمنع منح تلقائي
        لتعريف كان مقصود يُمنح يدويًا بس، حتى لو حد ملأ
        trigger_event_name عليه بالغلط."""
        definitions = await self.repo.get_auto_grant_definitions(
            tenant_id=tenant_id,
            category=AchievementCategory.TEAM_BUILDING,
            trigger_event_name=BOOTCAMP_ENROLLMENT_EVENT_NAME,
        )
        for definition in definitions:
            if definition.trigger_threshold is None:
                continue
            if new_network_size < definition.trigger_threshold:
                continue
            await self.repo.grant_achievement_if_not_exists(
                tenant_id=tenant_id,
                user_id=ancestor_id,
                achievement_definition_id=definition.id,
                granted_by=None,
                source_event_name=BOOTCAMP_ENROLLMENT_EVENT_NAME,
                source_payload={
                    "network_size": new_network_size,
                    "ancestor_level": ancestor_level,
                },
            )

    # ============================================================
    # 5. منح تلقائي مباشر عند إكمال كورس (TRAINING) — بلا عتبة، بلا walk-up
    # ============================================================

    async def grant_training_achievements_for_course_completion(
        self, user_id: int, tenant_id: int, course_id: int,
    ) -> List[int]:
        """يُستدعى من dispatch_critical_event_task لما
        "academy.course.completed" يتنشر. بلا فحص عتبة (على عكس
        TEAM_BUILDING) — أي `AchievementDefinition` نشط من فئة TRAINING
        مربوط بنفس اسم الحدث يتمنح **مباشرة** لأول مرة يوصل فيها الحدث
        لهذا المستخدم، عبر نفس آلية INSERT...ON CONFLICT DO NOTHING
        (القيد الفريد بيمنع أي تكرار، بلا SELECT أول — بالحرف نفس نمط
        TEAM_BUILDING). `trigger_threshold` غير مستخدَم هنا إطلاقًا حتى
        لو مملوء. بيرجع قايمة achievement_definition_id اللي اتمنحت
        فعليًا (مش كلهم بالضرورة — لو المستخدم عنده الإنجاز بالفعل من
        نداء سابق، بيتخطّى بصمت)."""
        definitions = await self.repo.get_auto_grant_definitions(
            tenant_id=tenant_id,
            category=AchievementCategory.TRAINING,
            trigger_event_name=COURSE_COMPLETED_EVENT_NAME,
        )
        granted_definition_ids: List[int] = []
        for definition in definitions:
            granted = await self.repo.grant_achievement_if_not_exists(
                tenant_id=tenant_id,
                user_id=user_id,
                achievement_definition_id=definition.id,
                granted_by=None,
                source_event_name=COURSE_COMPLETED_EVENT_NAME,
                source_payload={"course_id": course_id},
            )
            if granted:
                granted_definition_ids.append(definition.id)

        if granted_definition_ids:
            await self.db.commit()

        return granted_definition_ids

    # ============================================================
    # 6. منح تلقائي مباشر عند أول مساهمة (PROJECT_FUNDING) — بلا عتبة
    # ============================================================

    async def grant_project_funding_achievements_for_contribution(
        self, user_id: int, tenant_id: int, contribution_id: int, project_id: int,
    ) -> List[int]:
        """يُستدعى من dispatch_critical_event_task لما
        "project.contribution.received" يتنشر (الحدث موجود بالفعل من
        قبل في projects/service.py، بلا أي تعديل عليه). بلا فحص عتبة،
        بلا walk-up — بالضبط نفس نمط `grant_training_achievements_for_course_completion`
        بالحرف: أي `AchievementDefinition` نشط من فئة PROJECT_FUNDING
        مربوط بنفس اسم الحدث يتمنح مباشرة لأول مرة، عبر INSERT...ON
        CONFLICT DO NOTHING (القيد الفريد بيمنع أي تكرار لاحق — نفس
        المستخدم ممكن يساهم في مشاريع كتير من غير أي قيد يمنعه، لكن
        الإنجاز بيتمنح مرة واحدة بس). بيرجع قايمة achievement_definition_id
        اللي اتمنحت فعليًا."""
        definitions = await self.repo.get_auto_grant_definitions(
            tenant_id=tenant_id,
            category=AchievementCategory.PROJECT_FUNDING,
            trigger_event_name=CONTRIBUTION_RECEIVED_EVENT_NAME,
        )
        granted_definition_ids: List[int] = []
        for definition in definitions:
            granted = await self.repo.grant_achievement_if_not_exists(
                tenant_id=tenant_id,
                user_id=user_id,
                achievement_definition_id=definition.id,
                granted_by=None,
                source_event_name=CONTRIBUTION_RECEIVED_EVENT_NAME,
                source_payload={"project_id": project_id, "contribution_id": contribution_id},
            )
            if granted:
                granted_definition_ids.append(definition.id)

        if granted_definition_ids:
            await self.db.commit()

        return granted_definition_ids
