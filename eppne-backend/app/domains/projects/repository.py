# app/domains/projects/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from decimal import Decimal

from app.domains.projects.models import (
    Project,
    ProjectMilestone,
    Contribution,
    ProjectUpdate,
    ProjectFollower
)


class ProjectRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ==========================================
    # 1. Projects
    # ==========================================

    async def create_project(self, **kwargs) -> Project:
        """إنشاء مشروع جديد (يتضمن tenant_id)."""
        project = Project(**kwargs)
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def get_project(self, project_id: int, tenant_id: int) -> Optional[Project]:
        """جلب مشروع مع تحميل جميع العلاقات دفعة واحدة (لتجنب N+1)."""
        result = await self.db.execute(
            select(Project)
            .options(
                selectinload(Project.milestones),
                selectinload(Project.contributions),
                selectinload(Project.updates)
            )
            .where(Project.id == project_id, Project.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def update_project(self, project_id: int, tenant_id: int, **kwargs) -> Optional[Project]:
        """تحديث مشروع مع التأكد من tenant_id."""
        await self.db.execute(
            update(Project)
            .where(Project.id == project_id, Project.tenant_id == tenant_id)
            .values(**kwargs)
        )
        await self.db.flush()
        return await self.get_project(project_id, tenant_id)

    async def list_projects(
        self,
        tenant_id: int,
        p_type: Optional[str] = None,
        status: Optional[str] = None,
        country: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Project]:
        """قائمة المشاريع مع تحميل العلاقات الأساسية (لتجنب N+1 عند العرض)."""
        query = (
            select(Project)
            .options(
                selectinload(Project.milestones),
                selectinload(Project.contributions).selectinload(Contribution.contributor),
                selectinload(Project.updates)
            )
            .where(Project.tenant_id == tenant_id)
        )
        if p_type:
            query = query.where(Project.project_type == p_type)
        if status:
            query = query.where(Project.status == status)
        if country:
            query = query.where(Project.country == country)
        query = query.order_by(Project.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def delete_project(self, project_id: int, tenant_id: int, soft: bool = True) -> bool:
        """حذف مشروع (soft delete اختياري)."""
        if soft:
            await self.db.execute(
                update(Project)
                .where(Project.id == project_id, Project.tenant_id == tenant_id)
                .values(is_deleted=True, deleted_at=func.now())
            )
        else:
            await self.db.execute(
                delete(Project)
                .where(Project.id == project_id, Project.tenant_id == tenant_id)
            )
        await self.db.commit()
        return True

    # ==========================================
    # 2. Contributions (مع Idempotency)
    # ==========================================

    async def create_contribution(self, **kwargs) -> Contribution:
        """إنشاء مساهمة جديدة (يتضمن tenant_id و idempotency_key اختياري)."""
        # WARNING: هذا الـcommit() بيغطي كمان كتابة finance.transfer() جوه
        # service.add_contribution (اللي فيها flush() بس، بلا commit مستقل خاص بيها) —
        # لا تحوّل الـcommit() ده لـflush() بدون إضافة commit() صريح لـadd_contribution أولًا.
        contrib = Contribution(**kwargs)
        self.db.add(contrib)
        await self.db.commit()
        await self.db.refresh(contrib)
        return contrib

    async def get_contribution(self, contribution_id: int, tenant_id: int) -> Optional[Contribution]:
        """جلب مساهمة مع التأكد من tenant_id."""
        result = await self.db.execute(
            select(Contribution)
            .join(Project)
            .where(Contribution.id == contribution_id, Project.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_contribution_by_idempotency(self, idempotency_key: str) -> Optional[Contribution]:
        """جلب مساهمة باستخدام idempotency_key (بدون tenant_id لأن المفتاح فريد عالمياً)."""
        result = await self.db.execute(
            select(Contribution).where(Contribution.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def update_contribution(self, contribution_id: int, tenant_id: int, **kwargs) -> Optional[Contribution]:
        """تحديث مساهمة مع التأكد من tenant_id."""
        contrib = await self.get_contribution(contribution_id, tenant_id)
        if not contrib:
            return None
        await self.db.execute(
            update(Contribution)
            .where(Contribution.id == contribution_id)
            .values(**kwargs)
        )
        await self.db.flush()
        return await self.get_contribution(contribution_id, tenant_id)

    async def count_contributors(self, project_id: int, tenant_id: int) -> int:
        """عدد المساهمين الفريدين في مشروع معين."""
        result = await self.db.execute(
            select(func.count(func.distinct(Contribution.contributor_id)))
            .join(Project)
            .where(Contribution.project_id == project_id, Project.tenant_id == tenant_id)
        )
        return result.scalar() or 0

    async def sum_monetary_contributions(self, project_id: int, tenant_id: int) -> Decimal:
        """مجموع المساهمات المالية المعتمدة."""
        result = await self.db.execute(
            select(func.sum(Contribution.amount_mrusdt))
            .join(Project)
            .where(
                Contribution.project_id == project_id,
                Project.tenant_id == tenant_id,
                Contribution.status == "APPROVED"
            )
        )
        return result.scalar() or Decimal(0)

    async def sum_in_kind_contributions(self, project_id: int, tenant_id: int) -> Decimal:
        """مجموع المساهمات العينية المعتمدة."""
        result = await self.db.execute(
            select(func.sum(Contribution.equivalent_value_mrusdt))
            .join(Project)
            .where(
                Contribution.project_id == project_id,
                Project.tenant_id == tenant_id,
                Contribution.status == "APPROVED"
            )
        )
        return result.scalar() or Decimal(0)

    async def list_contributions(
        self,
        project_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[Contribution]:
        """قائمة المساهمات لمشروع معين."""
        query = (
            select(Contribution)
            .join(Project)
            .where(Contribution.project_id == project_id, Project.tenant_id == tenant_id)
        )
        if status:
            query = query.where(Contribution.status == status)
        query = query.order_by(Contribution.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    # ==========================================
    # 3. Milestones
    # ==========================================

    async def create_milestone(self, **kwargs) -> ProjectMilestone:
        """إنشاء مرحلة جديدة."""
        ms = ProjectMilestone(**kwargs)
        self.db.add(ms)
        await self.db.commit()
        await self.db.refresh(ms)
        return ms

    async def get_milestone(self, milestone_id: int, tenant_id: int) -> Optional[ProjectMilestone]:
        """جلب مرحلة مع التأكد من tenant_id."""
        result = await self.db.execute(
            select(ProjectMilestone)
            .join(Project)
            .where(ProjectMilestone.id == milestone_id, Project.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def update_milestone(self, milestone_id: int, tenant_id: int, **kwargs) -> Optional[ProjectMilestone]:
        """تحديث مرحلة مع التأكد من tenant_id."""
        ms = await self.get_milestone(milestone_id, tenant_id)
        if not ms:
            return None
        await self.db.execute(
            update(ProjectMilestone)
            .where(ProjectMilestone.id == milestone_id)
            .values(**kwargs)
        )
        await self.db.flush()
        return await self.get_milestone(milestone_id, tenant_id)

    async def get_milestones(self, project_id: int, tenant_id: int) -> List[ProjectMilestone]:
        """جلب جميع مراحل مشروع معين."""
        result = await self.db.execute(
            select(ProjectMilestone)
            .join(Project)
            .where(ProjectMilestone.project_id == project_id, Project.tenant_id == tenant_id)
            .order_by(ProjectMilestone.target_date)
        )
        return result.scalars().all()

    # ==========================================
    # 4. Follows
    # ==========================================

    async def create_follow(self, **kwargs) -> ProjectFollower:
        """إنشاء متابعة لمشروع."""
        follow = ProjectFollower(**kwargs)
        self.db.add(follow)
        await self.db.commit()
        await self.db.refresh(follow)
        return follow

    async def delete_follow(self, user_id: int, project_id: int, tenant_id: int) -> bool:
        """إلغاء متابعة مشروع مع التأكد من tenant_id."""
        await self.db.execute(
            delete(ProjectFollower)
            .where(
                ProjectFollower.user_id == user_id,
                ProjectFollower.project_id == project_id,
                ProjectFollower.tenant_id == tenant_id
            )
        )
        await self.db.commit()
        return True

    async def get_followers(self, project_id: int, tenant_id: int, skip: int = 0, limit: int = 50) -> List[ProjectFollower]:
        """قائمة المتابعين لمشروع معين."""
        result = await self.db.execute(
            select(ProjectFollower)
            .where(
                ProjectFollower.project_id == project_id,
                ProjectFollower.tenant_id == tenant_id
            )
            .offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def is_following(self, user_id: int, project_id: int, tenant_id: int) -> bool:
        """التحقق من أن المستخدم يتابع المشروع."""
        result = await self.db.execute(
            select(ProjectFollower)
            .where(
                ProjectFollower.user_id == user_id,
                ProjectFollower.project_id == project_id,
                ProjectFollower.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none() is not None

    # ==========================================
    # 5. Updates
    # ==========================================

    async def create_project_update(self, **kwargs) -> ProjectUpdate:
        """إنشاء تحديث جديد لمشروع."""
        upd = ProjectUpdate(**kwargs)
        self.db.add(upd)
        await self.db.commit()
        await self.db.refresh(upd)
        return upd

    async def get_project_updates(
        self,
        project_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[ProjectUpdate]:
        """جلب تحديثات مشروع معين."""
        result = await self.db.execute(
            select(ProjectUpdate)
            .join(Project)
            .where(ProjectUpdate.project_id == project_id, Project.tenant_id == tenant_id)
            .order_by(ProjectUpdate.created_at.desc())
            .offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def get_project_update(self, update_id: int, tenant_id: int) -> Optional[ProjectUpdate]:
        """جلب تحديث معين مع التأكد من tenant_id."""
        result = await self.db.execute(
            select(ProjectUpdate)
            .join(Project)
            .where(ProjectUpdate.id == update_id, Project.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    # ==========================================
    # 6. دوال إحصائية متقدمة
    # ==========================================

    async def get_project_stats(self, project_id: int, tenant_id: int) -> dict:
        """إحصائيات متقدمة عن المشروع."""
        total_contributors = await self.count_contributors(project_id, tenant_id)
        total_monetary = await self.sum_monetary_contributions(project_id, tenant_id)
        total_in_kind = await self.sum_in_kind_contributions(project_id, tenant_id)

        # نسبة التمويل
        project = await self.get_project(project_id, tenant_id)
        funding_goal = project.funding_goal_mrusdt if project else Decimal(0)
        funding_percentage = (total_monetary / funding_goal * 100) if funding_goal else Decimal(0)

        return {
            "total_contributors": total_contributors,
            "total_monetary_mrusdt": float(total_monetary),
            "total_in_kind_mrusdt": float(total_in_kind),
            "total_raised_mrusdt": float(total_monetary + total_in_kind),
            "funding_goal_mrusdt": float(funding_goal),
            "funding_percentage": float(min(funding_percentage, Decimal(100))),
        }