# app/domains/projects/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
import uuid
import json
import asyncio
import bleach
from datetime import datetime
from typing import Optional, List, Dict, Any, cast

from app.domains.projects.repository import ProjectRepository
from app.domains.projects.models import ProjectStatus, ContributionType, Project, ProjectMilestone, Contribution, ProjectUpdate
from app.domains.finance.service import FinanceService
from app.domains.commerce.repository import CommerceRepository
from app.core.errors import NotFoundError, PermissionDeniedError, IdempotencyError
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.cache import CacheManager, invalidate_cache
from app.core.pagination import PaginatedResponse

# قائمة العلامات المسموحة (للحماية من XSS)
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
        self.commerce_repo = CommerceRepository(db)
        self.event_bus = EventBus(cast(Any, redis_client))
        self.redis = redis_client

    # ==========================================
    # 0. تعقيم النصوص
    # ==========================================
    def sanitize_html(self, text: str) -> str:
        if not text:
            return text
        return bleach.clean(
            text,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True
        )

    # ==========================================
    # 1. المشاريع (CRUD)
    # ==========================================
    async def create_project(self, owner_id: int, tenant_id: int, data) -> Project:
        sanitized = data.model_dump()
        sanitized['title'] = self.sanitize_html(sanitized.get('title', ''))
        sanitized['description'] = self.sanitize_html(sanitized.get('description', ''))
        return await self.repo.create_project(
            owner_id=owner_id,
            tenant_id=tenant_id,
            **sanitized
        )

    async def get_project(self, project_id: int, tenant_id: int) -> Project:
        project = await self.repo.get_project(project_id, tenant_id)
        if not project:
            raise NotFoundError("Project not found")
        return project

    async def list_projects(
        self,
        tenant_id: int,
        project_type: Optional[str] = None,
        status: Optional[str] = None,
        country: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Project]:
        return await self.repo.list_projects(tenant_id, project_type, status, country, skip, limit)

    async def update_project(
        self,
        project_id: int,
        tenant_id: int,
        owner_id: int,
        data: Dict[str, Any]
    ) -> Project:
        project = await self.repo.get_project(project_id, tenant_id)
        if not project:
            raise NotFoundError("Project not found")
        if cast(int, project.owner_id) != owner_id:
            raise PermissionDeniedError("Not authorized to update this project")

        if 'title' in data:
            data['title'] = self.sanitize_html(data['title'])
        if 'description' in data:
            data['description'] = self.sanitize_html(data['description'])

        updated = await self.repo.update_project(project_id, tenant_id, **data)
        if not updated:
            raise NotFoundError("Project not found after update")
        # 🔥 إضافة await
        await invalidate_cache(f"project_analytics_{project_id}")
        return updated

    async def delete_project(self, project_id: int, tenant_id: int, owner_id: int, soft: bool = True) -> bool:
        project = await self.repo.get_project(project_id, tenant_id)
        if not project:
            raise NotFoundError("Project not found")
        if cast(int, project.owner_id) != owner_id:
            raise PermissionDeniedError("Not authorized to delete this project")
        return await self.repo.delete_project(project_id, tenant_id, soft=soft)

    async def publish_project(self, project_id: int, owner_id: int, tenant_id: int) -> Project:
        project = await self.repo.get_project(project_id, tenant_id)
        if not project:
            raise NotFoundError("Project not found")
        if cast(int, project.owner_id) != owner_id:
            raise PermissionDeniedError("Not authorized to publish this project")

        updated = await self.repo.update_project(
            project_id, tenant_id,
            is_published=True,
            status=ProjectStatus.FUNDRAISING
        )
        if not updated:
            raise NotFoundError("Project not found after update")

        await self.event_bus.publish("project.published", {
            "project_id": project.id,
            "tenant_id": tenant_id,
            "owner_id": owner_id,
            "title": project.title,
            "funding_goal": float(project.funding_goal_mrusdt)  # type: ignore
        })

        # 🔥 إضافة await
        await invalidate_cache(f"project_analytics_{project_id}")
        return updated

    # ==========================================
    # 2. المساهمات (مع Idempotency)
    # ==========================================
    async def add_contribution(
        self,
        contributor_id: int,
        tenant_id: int,
        data,
        idempotency_key: Optional[str] = None
    ) -> dict:
        redis_key = None
        if idempotency_key:
            redis_key = f"idempotency:{idempotency_key}"
            # استخدام setnx مع تجاهل تحذير Pylance
            acquired = await self.redis.setnx(redis_key, json.dumps({"status": "processing"}))  # type: ignore
            if not acquired:
                cached = await self.redis.get(redis_key)
                if cached:
                    return json.loads(cached)
                raise IdempotencyError("Request already being processed")
            await self.redis.expire(redis_key, 3600)

        try:
            project = await self.repo.get_project(data.project_id, tenant_id)
            if not project:
                raise NotFoundError("Project not found")
            if project.status != ProjectStatus.FUNDRAISING:  # type: ignore
                raise PermissionDeniedError("Project is not accepting contributions")

            eq_val = data.amount_mrusdt or (
                data.land_area_sqm * Decimal('100') if data.land_area_sqm else Decimal('0')
            ) or (
                data.labor_hours * Decimal('50') if data.labor_hours else Decimal('0')
            ) or (
                data.consulting_hours * Decimal('200') if data.consulting_hours else Decimal('0')
            ) or data.equipment_estimated_value or Decimal('0')

            if data.contribution_type == ContributionType.MONETARY:
                try:
                    await self.finance.transfer(
                        sender_id=contributor_id,
                        receiver_email="system@eppne.com",
                        currency=project.currency,  # type: ignore
                        amount=data.amount_mrusdt,
                        notes=f"Proj:{project.id}",
                        idempotency_key=idempotency_key or ""
                    )
                except Exception as e:
                    if redis_key:
                        await self.redis.delete(redis_key)
                    raise

            contribution_data = {
                'tenant_id': tenant_id,
                'project_id': project.id,
                'contributor_id': contributor_id,
                'contribution_type': data.contribution_type,
                'equivalent_value_mrusdt': eq_val,
                'status': "PENDING",
            }
            optional_fields = ['amount_mrusdt', 'land_area_sqm', 'land_address', 'land_title_deed_hash',
                               'labor_hours', 'labor_description', 'equipment_description',
                               'equipment_estimated_value', 'consulting_hours', 'consulting_expertise']
            for field in optional_fields:
                val = getattr(data, field, None)
                if val is not None:
                    contribution_data[field] = val

            contribution = await self.repo.create_contribution(**contribution_data)

            result = {
                "id": contribution.id,
                "status": "PENDING",
                "equivalent_value_mrusdt": float(eq_val)
            }
            if redis_key:
                await self.redis.setex(redis_key, 3600, json.dumps(result))

            await self.event_bus.publish("project.contribution.received", {
                "project_id": project.id,
                "tenant_id": tenant_id,
                "contributor_id": contributor_id,
                "amount": float(eq_val),
                "contribution_id": contribution.id
            })

            # 🔥 إضافة await
            await invalidate_cache(f"project_analytics_{project.id}")
            return result

        except Exception as e:
            if redis_key:
                await self.redis.delete(redis_key)
            raise

    async def get_contribution(self, contribution_id: int, tenant_id: int) -> Contribution:
        contrib = await self.repo.get_contribution(contribution_id, tenant_id)
        if not contrib:
            raise NotFoundError("Contribution not found")
        return contrib

    async def approve_contribution(
        self,
        contribution_id: int,
        owner_id: int,
        tenant_id: int,
        approved: bool,
        notes: Optional[str] = None
    ) -> Contribution:
        async with self.db.begin_nested():
            contribution = await self.repo.get_contribution(contribution_id, tenant_id)
            if not contribution:
                raise NotFoundError("Contribution not found")

            project = await self.repo.get_project(cast(int, contribution.project_id), tenant_id)
            if not project:
                raise NotFoundError("Project not found")
            if cast(int, project.owner_id) != owner_id:
                raise PermissionDeniedError("Not authorized to approve this contribution")

            status = "APPROVED" if approved else "REJECTED"
            if approved:
                new_funding = project.current_funding_mrusdt + contribution.equivalent_value_mrusdt  # type: ignore
                await self.repo.update_project(
                    cast(int, project.id), tenant_id,
                    current_funding_mrusdt=new_funding
                )

            updated = await self.repo.update_contribution(contribution_id, tenant_id, status=status)
            if not updated:
                raise NotFoundError("Contribution not found after update")

            # 🔥 إضافة await
            await invalidate_cache(f"project_analytics_{project.id}")
        await self.db.commit()
        return updated

    # ==========================================
    # 3. المراحل (Milestones)
    # ==========================================
    async def add_milestone(
        self,
        project_id: int,
        owner_id: int,
        tenant_id: int,
        data
    ) -> ProjectMilestone:
        project = await self.repo.get_project(project_id, tenant_id)
        if not project:
            raise NotFoundError("Project not found")
        if cast(int, project.owner_id) != owner_id:
            raise PermissionDeniedError("Not authorized to add milestone")

        milestone_data = data.model_dump()
        milestone_data['tenant_id'] = tenant_id
        milestone_data['project_id'] = project_id
        return await self.repo.create_milestone(**milestone_data)

    async def get_milestones(self, project_id: int, tenant_id: int) -> List[ProjectMilestone]:
        project = await self.repo.get_project(project_id, tenant_id)
        if not project:
            raise NotFoundError("Project not found")
        return await self.repo.get_milestones(project_id, tenant_id)

    async def complete_milestone(
        self,
        milestone_id: int,
        owner_id: int,
        tenant_id: int,
        data
    ) -> ProjectMilestone:
        async with self.db.begin_nested():
            milestone = await self.repo.get_milestone(milestone_id, tenant_id)
            if not milestone:
                raise NotFoundError("Milestone not found")

            project = await self.repo.get_project(cast(int, milestone.project_id), tenant_id)
            if not project:
                raise NotFoundError("Project not found")
            if cast(int, project.owner_id) != owner_id:
                raise PermissionDeniedError("Not authorized to complete this milestone")

            updated = await self.repo.update_milestone(
                milestone_id, tenant_id,
                is_completed=True,
                actual_date=data.actual_date
            )
            if not updated:
                raise NotFoundError("Milestone not found after update")

            if milestone.funds_to_release > 0:  # type: ignore
                await self.event_bus.publish("project.milestone.completed", {
                    "project_id": project.id,
                    "tenant_id": tenant_id,
                    "milestone_id": milestone.id,
                    "funds_to_release": float(milestone.funds_to_release)  # type: ignore
                })

            # 🔥 إضافة await
            await invalidate_cache(f"project_analytics_{project.id}")
        await self.db.commit()
        return updated

    # ==========================================
    # 4. المتابعة (Follow)
    # ==========================================
    async def follow_project(self, user_id: int, project_id: int, tenant_id: int) -> bool:
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
        await self.repo.delete_follow(user_id, project_id, tenant_id)
        return True

    async def get_followers(self, project_id: int, tenant_id: int, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        project = await self.repo.get_project(project_id, tenant_id)
        if not project:
            raise NotFoundError("Project not found")
        followers = await self.repo.get_followers(project_id, tenant_id, skip, limit)
        result = []
        for f in followers:
            created_at = getattr(f, 'created_at', None)
            result.append({
                "user_id": f.user_id,
                "followed_at": created_at.isoformat() if created_at is not None else None
            })
        return result

    # ==========================================
    # 5. التحديثات (Updates)
    # ==========================================
    async def add_project_update(
        self,
        project_id: int,
        author_id: int,
        tenant_id: int,
        title: str,
        content: str,
        media_urls: Optional[List[str]] = None
    ) -> dict:
        project = await self.repo.get_project(project_id, tenant_id)
        if not project:
            raise NotFoundError("Project not found")

        sanitized_title = self.sanitize_html(title)
        sanitized_content = self.sanitize_html(content)

        update_obj = await self.repo.create_project_update(
            tenant_id=tenant_id,
            project_id=project_id,
            author_id=author_id,
            title=sanitized_title,
            content=sanitized_content,
            media_urls=media_urls or []
        )

        await self.event_bus.publish("project.update.added", {
            "project_id": project_id,
            "tenant_id": tenant_id,
            "update_id": update_obj.id,
            "author_id": author_id
        })

        return {"id": update_obj.id, "title": sanitized_title, "created_at": update_obj.created_at}

    async def get_project_updates(
        self,
        project_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[ProjectUpdate]:
        project = await self.repo.get_project(project_id, tenant_id)
        if not project:
            raise NotFoundError("Project not found")
        return await self.repo.get_project_updates(project_id, tenant_id, skip, limit)

    # ==========================================
    # 6. منتجات (من Commerce) – تم نقله إلى هنا
    # ==========================================
    async def list_products(self, store_id: int, skip: int = 0, limit: int = 50) -> PaginatedResponse:
        return await self.commerce_repo.get_products_by_store(store_id, skip, limit)

    # ==========================================
    # 7. التحليلات (مع Caching واستعلامات متوازية)
    # ==========================================
    async def get_project_analytics(self, project_id: int, tenant_id: int) -> dict:
        cache_key = f"project_analytics_{project_id}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        project = await self.repo.get_project(project_id, tenant_id)
        if not project:
            raise NotFoundError("Project not found")

        total_contributors, total_monetary, total_in_kind = await asyncio.gather(
            self.repo.count_contributors(project_id, tenant_id),
            self.repo.sum_monetary_contributions(project_id, tenant_id),
            self.repo.sum_in_kind_contributions(project_id, tenant_id)
        )

        total_funding = total_monetary + total_in_kind
        funding_percentage = float(total_funding / project.funding_goal_mrusdt * 100) if project.funding_goal_mrusdt > 0 else 0  # type: ignore

        milestones = await self.repo.get_milestones(project_id, tenant_id)
        milestones_completed = sum(1 for m in milestones if m.is_completed)  # type: ignore

        analytics = {
            "project_id": project_id,
            "title": project.title,
            "status": project.status.value,
            "total_contributors": total_contributors,
            "total_monetary_contributions": float(total_monetary),
            "total_in_kind_value": float(total_in_kind),
            "total_funding_mrusdt": float(total_funding),
            "funding_percentage": funding_percentage,
            "remaining_to_goal": float(project.funding_goal_mrusdt - total_funding),  # type: ignore
            "milestones_completed": milestones_completed,
            "milestones_total": len(milestones),
            "updated_at": datetime.utcnow().isoformat()
        }

        await self.redis.setex(cache_key, 300, json.dumps(analytics))
        return analytics