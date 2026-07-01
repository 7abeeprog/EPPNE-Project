# app/domains/projects/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
import uuid
import json
import asyncio
import bleach
from datetime import datetime
from typing import Optional

from app.domains.projects.repository import ProjectRepository
from app.domains.projects.models import ProjectStatus, ContributionType, Project, ProjectMilestone, Contribution
from app.domains.finance.service import FinanceService
from app.core.errors import NotFoundError, PermissionDeniedError, IdempotencyError
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.cache import cache_result, invalidate_cache

# قائمة العلامات المسموحة (للحماية من XSS مع السماح ببعض التنسيق)
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'a', 'img', 'blockquote', 'code', 'pre'
]
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'target'],
    'img': ['src', 'alt', 'width', 'height']
}


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProjectRepository(db)
        self.finance = FinanceService(db)
        self.event_bus = EventBus(redis_client)
        self.redis = redis_client

    # ==========================================
    # 0. دالة تعقيم النصوص (Sanitization)
    # ==========================================
    def sanitize_html(self, text: str) -> str:
        """تعقيم النص من أي أكواد برمجية خبيثة"""
        if not text:
            return text
        return bleach.clean(
            text,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True
        )

    # ==========================================
    # 1. إنشاء مشروع (مع tenant_id وتعقيم)
    # ==========================================
    async def create_project(self, owner_id: int, tenant_id: int, data) -> Project:
        """إنشاء مشروع جديد مع تعقيم المدخلات."""
        sanitized_data = data.model_dump()
        sanitized_data['title'] = self.sanitize_html(sanitized_data.get('title', ''))
        sanitized_data['description'] = self.sanitize_html(sanitized_data.get('description', ''))

        return await self.repo.create_project(
            owner_id=owner_id,
            tenant_id=tenant_id,
            **sanitized_data
        )

    # ==========================================
    # 2. نشر المشروع (مع إطلاق حدث)
    # ==========================================
    async def publish_project(self, project_id: int, owner_id: int, tenant_id: int) -> Project:
        """نشر المشروع وإطلاق حدث project.published."""
        project = await self.repo.get_project(project_id, tenant_id)
        if not project:
            raise NotFoundError("Project not found")
        if project.owner_id != owner_id:
            raise PermissionDeniedError("غير مصرح لك")

        updated = await self.repo.update_project(
            project_id, tenant_id,
            is_published=True,
            status=ProjectStatus.FUNDRAISING
        )

        # 🔥 نشر الحدث للأتمتة
        await self.event_bus.publish("project.published", {
            "project_id": project.id,
            "tenant_id": tenant_id,
            "owner_id": owner_id,
            "title": project.title,
            "funding_goal": float(project.funding_goal_mrusdt)
        })

        # إبطال الكاش
        await invalidate_cache(f"project_analytics_{project_id}")

        return updated

    # ==========================================
    # 3. إضافة مساهمة (مع Idempotency باستخدام SETNX Atomic Lock)
    # ==========================================
    async def add_contribution(
        self,
        contributor_id: int,
        tenant_id: int,
        data,
        idempotency_key: Optional[str] = None
    ) -> dict:
        """
        إضافة مساهمة مع دعم Idempotency باستخدام SETNX (Atomic Lock)
        """
        redis_key = None
        if idempotency_key:
            redis_key = f"idempotency:{idempotency_key}"
            # 🔥 استخدام SETNX لضمان الذرية (Atomic)
            acquired = await self.redis.setnx(redis_key, json.dumps({"status": "processing"}))
            
            if not acquired:
                # المفتاح موجود بالفعل، نقرأ النتيجة المخزنة
                cached = await self.redis.get(redis_key)
                if cached:
                    return json.loads(cached)
                # في حال كان المفتاح موجوداً ولكن القيمة انتهت صلاحيتها (نادر)
                raise IdempotencyError("Request already being processed")
            
            # وضع صلاحية للمفتاح (ساعة واحدة)
            await self.redis.expire(redis_key, 3600)

        try:
            # 2. جلب المشروع مع التحقق من tenant_id
            project = await self.repo.get_project(data.project_id, tenant_id)
            if not project:
                raise NotFoundError("Project not found")
            if project.status != ProjectStatus.FUNDRAISING:
                raise PermissionDeniedError("المشروع لا يقبل مساهمات حالياً")

            # 3. حساب القيمة المعادلة
            val_map = {
                ContributionType.LABOR_HOURS: 50,
                ContributionType.CONSULTING: 200,
                ContributionType.LAND: 100
            }
            eq_val = data.amount_mrusdt or (
                data.land_area_sqm * 100 if data.land_area_sqm else 0
            ) or (
                data.labor_hours * 50 if data.labor_hours else 0
            ) or (
                data.consulting_hours * 200 if data.consulting_hours else 0
            ) or data.equipment_estimated_value or 0

            # 4. تنفيذ التحويل المالي مع Idempotency (نمرر المفتاح للـ FinanceService)
            if data.contribution_type == ContributionType.MONETARY:
                try:
                    await self.finance.transfer(
                        contributor_id,
                        "system@eppne.com",
                        project.currency,
                        data.amount_mrusdt,
                        f"Proj:{project.id}",
                        idempotency_key=idempotency_key
                    )
                except Exception as e:
                    # حذف Idempotency Key في حال الفشل (لإعادة المحاولة)
                    if redis_key:
                        await self.redis.delete(redis_key)
                    raise

            # 5. إنشاء المساهمة
            contribution = await self.repo.create_contribution(
                tenant_id=tenant_id,
                project_id=project.id,
                contributor_id=contributor_id,
                contribution_type=data.contribution_type,
                equivalent_value_mrusdt=eq_val,
                status="PENDING",
                idempotency_key=idempotency_key,
                **data.model_dump(exclude_unset=True)
            )

            # 6. تخزين النتيجة في Redis (بعد نجاح العملية)
            result = {
                "id": contribution.id,
                "status": "PENDING",
                "equivalent_value_mrusdt": float(eq_val)
            }
            if redis_key:
                # تحديث القيمة من "processing" إلى النتيجة الفعلية
                await self.redis.setex(redis_key, 3600, json.dumps(result))

            # 7. نشر الحدث للأتمتة (غير متزامن)
            await self.event_bus.publish("project.contribution.received", {
                "project_id": project.id,
                "tenant_id": tenant_id,
                "contributor_id": contributor_id,
                "amount": float(eq_val),
                "contribution_id": contribution.id
            })

            # 8. إبطال الكاش للتحليلات
            await invalidate_cache(f"project_analytics_{project.id}")

            return result

        except Exception as e:
            # في حال حدوث أي خطأ غير متوقع، نحرر الـ Lock
            if redis_key:
                await self.redis.delete(redis_key)
            raise

    # ==========================================
    # 4. الموافقة على المساهمة
    # ==========================================
    async def approve_contribution(
        self,
        contribution_id: int,
        owner_id: int,
        tenant_id: int,
        approved: bool,
        notes: Optional[str] = None
    ) -> Contribution:
        """الموافقة على مساهمة أو رفضها."""
        contribution = await self.repo.get_contribution(contribution_id, tenant_id)
        if not contribution:
            raise NotFoundError("Contribution not found")

        project = await self.repo.get_project(contribution.project_id, tenant_id)
        if project.owner_id != owner_id:
            raise PermissionDeniedError("غير مصرح لك")

        status = "APPROVED" if approved else "REJECTED"
        if approved:
            # تحديث التمويل الحالي
            new_funding = project.current_funding_mrusdt + contribution.equivalent_value_mrusdt
            await self.repo.update_project(
                project.id, tenant_id,
                current_funding_mrusdt=new_funding
            )

        updated = await self.repo.update_contribution(contribution_id, tenant_id, status=status)

        # إبطال الكاش
        await invalidate_cache(f"project_analytics_{project.id}")

        return updated

    # ==========================================
    # 5. إكمال مرحلة (Milestone)
    # ==========================================
    async def complete_milestone(
        self,
        milestone_id: int,
        owner_id: int,
        tenant_id: int,
        data
    ) -> ProjectMilestone:
        """إكمال مرحلة وإطلاق الأموال المرتبطة بها."""
        milestone = await self.repo.get_milestone(milestone_id, tenant_id)
        if not milestone:
            raise NotFoundError("Milestone not found")

        project = await self.repo.get_project(milestone.project_id, tenant_id)
        if project.owner_id != owner_id:
            raise PermissionDeniedError("غير مصرح لك")

        updated = await self.repo.update_milestone(
            milestone_id, tenant_id,
            is_completed=True,
            actual_date=data.actual_date
        )

        # 🔥 نشر الحدث للأتمتة (إطلاق الأموال)
        if milestone.funds_to_release > 0:
            await self.event_bus.publish("project.milestone.completed", {
                "project_id": project.id,
                "tenant_id": tenant_id,
                "milestone_id": milestone.id,
                "funds_to_release": float(milestone.funds_to_release)
            })

        # إبطال الكاش
        await invalidate_cache(f"project_analytics_{project.id}")

        return updated

    # ==========================================
    # 6. التحليلات (مع Caching واستعلامات متوازية)
    # ==========================================
    async def get_project_analytics(self, project_id: int, tenant_id: int) -> dict:
        """جلب التحليلات مع Caching واستعلامات متوازية"""
        cache_key = f"project_analytics_{project_id}"

        # 1. محاولة القراءة من الكاش
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # 2. جلب المشروع (للتأكد من وجوده وصلاحيته)
        project = await self.repo.get_project(project_id, tenant_id)
        if not project:
            raise NotFoundError("Project not found")

        # 3. 🔥 تشغيل الاستعلامات بالتوازي (Concurrent)
        total_contributors, total_monetary, total_in_kind = await asyncio.gather(
            self.repo.count_contributors(project_id, tenant_id),
            self.repo.sum_monetary_contributions(project_id, tenant_id),
            self.repo.sum_in_kind_contributions(project_id, tenant_id)
        )

        # 4. حساب المؤشرات المشتقة
        total_funding = total_monetary + total_in_kind
        funding_percentage = float(total_funding / project.funding_goal_mrusdt * 100) if project.funding_goal_mrusdt > 0 else 0

        # 5. بناء النتيجة
        analytics = {
            "project_id": project_id,
            "title": project.title,
            "status": project.status.value,
            "total_contributors": total_contributors,
            "total_monetary_contributions": float(total_monetary),
            "total_in_kind_value": float(total_in_kind),
            "total_funding_mrusdt": float(total_funding),
            "funding_percentage": funding_percentage,
            "remaining_to_goal": float(project.funding_goal_mrusdt - total_funding),
            "milestones_completed": len([m for m in project.milestones if m.is_completed]),
            "milestones_total": len(project.milestones),
            "updated_at": datetime.utcnow().isoformat()
        }

        # 6. تخزين النتيجة في الكاش لمدة 5 دقائق
        await self.redis.setex(cache_key, 300, json.dumps(analytics))

        return analytics

    # ==========================================
    # 7. دوال إضافية (Follow, Updates, إلخ)
    # ==========================================

    async def follow_project(self, user_id: int, project_id: int, tenant_id: int) -> bool:
        """متابعة مشروع."""
        project = await self.repo.get_project(project_id, tenant_id)
        if not project:
            raise NotFoundError("Project not found")

        if await self.repo.is_following(user_id, project_id, tenant_id):
            return True

        await self.repo.create_follow(
            tenant_id=tenant_id,
            user_id=user_id,
            project_id=project_id
        )
        return True

    async def unfollow_project(self, user_id: int, project_id: int, tenant_id: int) -> bool:
        """إلغاء متابعة مشروع."""
        await self.repo.delete_follow(user_id, project_id, tenant_id)
        return True

    async def get_project_updates(
        self,
        project_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> list:
        """جلب تحديثات المشروع."""
        project = await self.repo.get_project(project_id, tenant_id)
        if not project:
            raise NotFoundError("Project not found")
        return await self.repo.get_project_updates(project_id, tenant_id, skip, limit)

    # ==========================================
    # 8. إضافة تحديث (مع تعقيم المدخلات)
    # ==========================================
    async def add_project_update(
        self,
        project_id: int,
        author_id: int,
        tenant_id: int,
        data
    ) -> dict:
        """إضافة تحديث جديد للمشروع مع تعقيم المدخلات."""
        project = await self.repo.get_project(project_id, tenant_id)
        if not project:
            raise NotFoundError("Project not found")

        # تعقيم النصوص
        sanitized_title = self.sanitize_html(data.title)
        sanitized_content = self.sanitize_html(data.content)

        update_obj = await self.repo.create_project_update(
            tenant_id=tenant_id,
            project_id=project_id,
            author_id=author_id,
            title=sanitized_title,
            content=sanitized_content,
            media_urls=data.get("media_urls", []) if hasattr(data, "get") else []
        )

        # نشر الحدث للأتمتة
        await self.event_bus.publish("project.update.added", {
            "project_id": project_id,
            "tenant_id": tenant_id,
            "update_id": update_obj.id,
            "author_id": author_id
        })

        return {"id": update_obj.id, "title": sanitized_title, "created_at": update_obj.created_at}