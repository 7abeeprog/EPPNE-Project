# app/domains/achievements/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from typing import Optional, List

from app.domains.achievements.models import (
    AchievementDefinition, UserAchievement, UserNetworkStats,
    AchievementCategory, AchievementTriggerType,
)
from app.domains.identity.models import User


class AchievementRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- Achievement Definitions ----------
    async def create_definition(self, **kwargs) -> AchievementDefinition:
        definition = AchievementDefinition(**kwargs)
        self.db.add(definition)
        await self.db.flush()
        await self.db.refresh(definition)
        return definition

    async def get_definition(self, definition_id: int, tenant_id: int) -> Optional[AchievementDefinition]:
        result = await self.db.execute(
            select(AchievementDefinition).where(
                and_(
                    AchievementDefinition.id == definition_id,
                    AchievementDefinition.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_definitions(
        self, tenant_id: int, skip: int = 0, limit: int = 100,
    ) -> List[AchievementDefinition]:
        result = await self.db.execute(
            select(AchievementDefinition)
            .where(AchievementDefinition.tenant_id == tenant_id)
            .order_by(AchievementDefinition.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    # ---------- User Achievements ----------
    async def get_user_achievement(
        self, user_id: int, achievement_definition_id: int,
    ) -> Optional[UserAchievement]:
        result = await self.db.execute(
            select(UserAchievement).where(
                and_(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_definition_id == achievement_definition_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create_user_achievement(self, **kwargs) -> UserAchievement:
        achievement = UserAchievement(**kwargs)
        self.db.add(achievement)
        await self.db.flush()
        await self.db.refresh(achievement)
        return achievement

    async def list_user_achievements(self, user_id: int, tenant_id: int) -> List[UserAchievement]:
        result = await self.db.execute(
            select(UserAchievement)
            .where(and_(UserAchievement.user_id == user_id, UserAchievement.tenant_id == tenant_id))
            .order_by(UserAchievement.granted_at.desc())
        )
        return list(result.scalars().all())

    # ---------- Stats (Admin) ----------
    async def count_user_achievements_by_category(self, tenant_id: int):
        """عدد صفوف UserAchievement فعليًا لكل فئة (INNER JOIN عمدًا —
        فئة بدون أي منح فعلي مش هتظهر إطلاقًا، مش هتظهر بـcount=0)."""
        result = await self.db.execute(
            select(AchievementDefinition.category, func.count(UserAchievement.id))
            .select_from(UserAchievement)
            .join(AchievementDefinition, AchievementDefinition.id == UserAchievement.achievement_definition_id)
            .where(UserAchievement.tenant_id == tenant_id)
            .group_by(AchievementDefinition.category)
        )
        return result.all()

    async def count_users_by_achievement_definition(self, tenant_id: int):
        """عدد صفوف UserAchievement فعليًا لكل تعريف (INNER JOIN عمدًا —
        نفس منطق count_user_achievements_by_category بالحرف — تعريف بدون
        أي منح فعلي مش هيظهر إطلاقًا، مش هيظهر بـcount=0)."""
        result = await self.db.execute(
            select(AchievementDefinition.id, AchievementDefinition.name, func.count(UserAchievement.id))
            .select_from(UserAchievement)
            .join(AchievementDefinition, AchievementDefinition.id == UserAchievement.achievement_definition_id)
            .where(UserAchievement.tenant_id == tenant_id)
            .group_by(AchievementDefinition.id, AchievementDefinition.name)
        )
        return result.all()

    async def get_top_users_by_achievement_count(self, tenant_id: int, limit: int):
        result = await self.db.execute(
            select(User.id, User.username, func.count(UserAchievement.id).label("achievement_count"))
            .select_from(UserAchievement)
            .join(User, User.id == UserAchievement.user_id)
            .where(UserAchievement.tenant_id == tenant_id)
            .group_by(User.id, User.username)
            .order_by(func.count(UserAchievement.id).desc())
            .limit(limit)
        )
        return result.all()

    # ---------- Network Stats (walk-up) ----------
    async def get_referred_by_user_id(self, user_id: int) -> Optional[int]:
        """راعي المستخدم المباشر (خطوة واحدة لفوق) — `None` لو مفيش راعٍ
        (جذر السلسلة) أو المستخدم مش موجود."""
        result = await self.db.execute(
            select(User.referred_by_user_id).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def increment_bootcamp_network_size(self, user_id: int, tenant_id: int) -> int:
        """يزوّد bootcamp_network_size بـ1 لهذا المستخدم — INSERT...ON
        CONFLICT DO UPDATE ذرّي (statement واحد)، مش SELECT ثم UPDATE:
        بيغطي حالة "لسه مفيش صف user_network_stats لهذا المستخدم" (كل
        المستخدمين حاليًا، الجدول اتبنى فاضي في الجلسة السابقة) بلا أي
        سباق قراءة/كتابة محتمل بين عدة أحداث متزامنة لنفس السلف.
        `RETURNING bootcamp_network_size` بيرجّع القيمة الجديدة مباشرة من
        DB — بيتفادى مشكلة identity map القديمة (راجع `get_network_stats`
        تحت) للمستدعي اللي محتاج القيمة فورًا (فحص العتبات)."""
        stmt = pg_insert(UserNetworkStats).values(
            user_id=user_id,
            tenant_id=tenant_id,
            bootcamp_network_size=1,
        ).on_conflict_do_update(
            index_elements=[UserNetworkStats.user_id],
            set_={
                "bootcamp_network_size": UserNetworkStats.bootcamp_network_size + 1,
                "updated_at": func.now(),
            },
        ).returning(UserNetworkStats.bootcamp_network_size)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_network_stats(self, user_id: int) -> Optional[UserNetworkStats]:
        """`populate_existing=True` إجباري هنا: `increment_bootcamp_network_size`
        فوق Core statement خام (INSERT...ON CONFLICT) بيتخطّى الـidentity map
        بالكامل — بدونه، أي كائن `UserNetworkStats` اتحمَّل قبل كده لنفس
        الـsession بيرجع من الكاش القديم زي ما هو (`bootcamp_network_size`
        القديمة)، مش القيمة الفعلية الجديدة في DB، حتى لو الاستعلام نفسه
        جديد ونفَّذ فعليًا. اتأكَّد بالتنفيذ الفعلي — استدعاء تاني لنفس
        المستخدم من نفس الـsession كان بيرجّع القيمة القديمة بالحرف قبل
        هذا الإصلاح."""
        result = await self.db.execute(
            select(UserNetworkStats)
            .where(UserNetworkStats.user_id == user_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    # ---------- Auto-grant (threshold-based) ----------
    async def get_auto_grant_definitions(
        self, tenant_id: int, category: AchievementCategory, trigger_event_name: str,
    ) -> List[AchievementDefinition]:
        """تعريفات نشطة فقط، AUTO_EVENT فقط (مش MANUAL حتى لو حد ملأ
        trigger_event_name عليه بالغلط — trigger_type هو الحقل المُصمَّم
        خصيصًا للتمييز ده)، لنفس الفئة واسم الحدث."""
        result = await self.db.execute(
            select(AchievementDefinition).where(
                and_(
                    AchievementDefinition.tenant_id == tenant_id,
                    AchievementDefinition.category == category,
                    AchievementDefinition.trigger_event_name == trigger_event_name,
                    AchievementDefinition.trigger_type == AchievementTriggerType.AUTO_EVENT,
                    AchievementDefinition.is_active == True,  # noqa: E712
                )
            )
        )
        return list(result.scalars().all())

    async def grant_achievement_if_not_exists(
        self,
        tenant_id: int,
        user_id: int,
        achievement_definition_id: int,
        granted_by: Optional[int],
        source_event_name: Optional[str],
        source_payload: Optional[dict],
    ) -> bool:
        """INSERT...ON CONFLICT DO NOTHING ذرّي — بلا SELECT أول، القيد
        الفريد (user_id, achievement_definition_id) هو الحارس الوحيد ضد
        منح مزدوج (سباق نظري بين عدة أحداث متزامنة لنفس السلف+التعريف).
        يرجّع True لو المنح حصل فعليًا (صف جديد)، False لو كان ممنوح
        بالفعل (تخطّي صامت، متوقَّع تمامًا — مش خطأ)."""
        stmt = pg_insert(UserAchievement).values(
            tenant_id=tenant_id,
            user_id=user_id,
            achievement_definition_id=achievement_definition_id,
            granted_by=granted_by,
            source_event_name=source_event_name,
            source_payload=source_payload,
        ).on_conflict_do_nothing(
            index_elements=[UserAchievement.user_id, UserAchievement.achievement_definition_id],
        ).returning(UserAchievement.id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
