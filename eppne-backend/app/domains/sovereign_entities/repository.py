# app/domains/sovereign_entities/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, text
from sqlalchemy.orm import selectinload, joinedload
from typing import Optional, List, Dict, Any, cast
from datetime import datetime
from app.domains.sovereign_entities.models import (
    SovereignEntity, EntityRepresentative, EntityPage, EntityPageTemplate,
    PageComponent, EntityDocument, KYBStatus, SovereignEntityType
)
from app.core.errors import NotFoundError


class SovereignEntitiesRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ========== Sovereign Entities (مع tenant_id) ==========
    async def create_entity(self, **kwargs) -> SovereignEntity:
        entity = SovereignEntity(**kwargs)
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity

    async def get_entity(self, entity_id: int, tenant_id: int) -> Optional[SovereignEntity]:
        result = await self.db.execute(
            select(SovereignEntity).where(
                and_(
                    SovereignEntity.id == entity_id,
                    SovereignEntity.tenant_id == tenant_id,
                    SovereignEntity.is_deleted == False
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_entity_by_registration(self, registration_number: str, tenant_id: int) -> Optional[SovereignEntity]:
        result = await self.db.execute(
            select(SovereignEntity).where(
                and_(
                    SovereignEntity.registration_number == registration_number,
                    SovereignEntity.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_entity_by_slug(self, slug: str, tenant_id: int) -> Optional[SovereignEntity]:
        result = await self.db.execute(
            select(SovereignEntity)
            .join(EntityPage, EntityPage.entity_id == SovereignEntity.id)
            .where(
                and_(
                    EntityPage.slug == slug,
                    SovereignEntity.tenant_id == tenant_id,
                    SovereignEntity.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_entities(
        self,
        tenant_id: int,
        entity_type: Optional[SovereignEntityType] = None,
        kyb_status: Optional[KYBStatus] = None,
        skip: int = 0,
        limit: int = 50
    ) -> dict:  # ✅ تغيير النوع إلى dict
        query = select(SovereignEntity).where(
            and_(
                SovereignEntity.tenant_id == tenant_id,
                SovereignEntity.is_deleted == False
            )
        )
        if entity_type:
            query = query.where(SovereignEntity.entity_type == entity_type)
        if kyb_status:
            query = query.where(SovereignEntity.kyb_status == kyb_status)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(SovereignEntity.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return {
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit
        }

    async def update_entity(self, entity_id: int, tenant_id: int, **kwargs) -> SovereignEntity:
        await self.db.execute(
            update(SovereignEntity)
            .where(and_(SovereignEntity.id == entity_id, SovereignEntity.tenant_id == tenant_id))
            .values(**kwargs)
        )
        await self.db.flush()
        entity = await self.get_entity(entity_id, tenant_id)
        if not entity:
            raise NotFoundError("Entity not found")
        return entity

    async def delete_entity(self, entity_id: int, tenant_id: int, soft: bool = True) -> None:
        if soft:
            await self.db.execute(
                update(SovereignEntity)
                .where(and_(SovereignEntity.id == entity_id, SovereignEntity.tenant_id == tenant_id))
                .values(is_deleted=True, deleted_at=func.now())
            )
        else:
            await self.db.execute(
                delete(SovereignEntity)
                .where(and_(SovereignEntity.id == entity_id, SovereignEntity.tenant_id == tenant_id))
            )
        await self.db.commit()

    # ========== Representatives ==========
    async def add_representative(self, **kwargs) -> EntityRepresentative:
        rep = EntityRepresentative(**kwargs)
        self.db.add(rep)
        await self.db.commit()
        await self.db.refresh(rep)
        return rep

    async def get_representatives(self, entity_id: int) -> List[EntityRepresentative]:
        result = await self.db.execute(
            select(EntityRepresentative).where(
                and_(
                    EntityRepresentative.entity_id == entity_id,
                    EntityRepresentative.is_active == True
                )
            )
        )
        return list(result.scalars().all())

    async def get_representatives_by_user(self, user_id: int, tenant_id: int) -> List[EntityRepresentative]:
        result = await self.db.execute(
            select(EntityRepresentative)
            .join(SovereignEntity, SovereignEntity.id == EntityRepresentative.entity_id)
            .where(
                and_(
                    EntityRepresentative.user_id == user_id,
                    EntityRepresentative.is_active == True,
                    SovereignEntity.tenant_id == tenant_id,
                    SovereignEntity.is_deleted == False
                )
            )
        )
        return list(result.scalars().all())

    async def get_representative(self, entity_id: int, user_id: int, tenant_id: int) -> Optional[EntityRepresentative]:
        result = await self.db.execute(
            select(EntityRepresentative)
            .join(SovereignEntity, SovereignEntity.id == EntityRepresentative.entity_id)
            .where(
                and_(
                    EntityRepresentative.entity_id == entity_id,
                    EntityRepresentative.user_id == user_id,
                    EntityRepresentative.is_active == True,
                    SovereignEntity.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def remove_representative(self, entity_id: int, user_id: int) -> None:
        await self.db.execute(
            delete(EntityRepresentative).where(
                and_(
                    EntityRepresentative.entity_id == entity_id,
                    EntityRepresentative.user_id == user_id
                )
            )
        )
        await self.db.commit()

    # ========== KYB Documents ==========
    async def add_document(self, **kwargs) -> EntityDocument:
        doc = EntityDocument(**kwargs)
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def get_documents(self, entity_id: int) -> List[EntityDocument]:
        result = await self.db.execute(select(EntityDocument).where(EntityDocument.entity_id == entity_id))
        return list(result.scalars().all())

    async def update_document_status(self, doc_id: int, status: str, verifier_id: int, reason: Optional[str] = None) -> EntityDocument:
        values = {"status": status, "verified_by": verifier_id, "verified_at": func.now()}
        if reason:
            values["rejection_reason"] = reason
        await self.db.execute(update(EntityDocument).where(EntityDocument.id == doc_id).values(**values))
        await self.db.commit()
        result = await self.db.execute(select(EntityDocument).where(EntityDocument.id == doc_id))
        return result.scalar_one()

    # ========== Entity Pages ==========
    async def create_entity_page(self, tenant_id: int, **kwargs) -> EntityPage:
        page = EntityPage(tenant_id=tenant_id, **kwargs)
        self.db.add(page)
        await self.db.commit()
        await self.db.refresh(page)
        return page

    async def get_entity_page(self, entity_id: int, tenant_id: int) -> Optional[EntityPage]:
        result = await self.db.execute(
            select(EntityPage)
            .join(SovereignEntity, SovereignEntity.id == EntityPage.entity_id)
            .where(
                and_(
                    EntityPage.entity_id == entity_id,
                    SovereignEntity.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_entity_page_by_slug(self, slug: str, tenant_id: int) -> Optional[EntityPage]:
        result = await self.db.execute(
            select(EntityPage)
            .join(SovereignEntity, SovereignEntity.id == EntityPage.entity_id)
            .where(
                and_(
                    EntityPage.slug == slug,
                    SovereignEntity.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_entity_page_by_slug_with_entity(self, slug: str, tenant_id: int) -> Optional[tuple[EntityPage, SovereignEntity]]:
        result = await self.db.execute(
            select(EntityPage)
            .join(SovereignEntity, SovereignEntity.id == EntityPage.entity_id)
            .where(
                and_(
                    EntityPage.slug == slug,
                    SovereignEntity.tenant_id == tenant_id,
                    SovereignEntity.is_active == True
                )
            )
            .options(selectinload(EntityPage.entity))
        )
        page = result.scalar_one_or_none()
        if page:
            return page, page.entity
        return None

    async def update_entity_page(self, entity_id: int, tenant_id: int, **kwargs) -> EntityPage:
        await self.db.execute(
            update(EntityPage)
            .where(EntityPage.entity_id == entity_id)
            .where(SovereignEntity.tenant_id == tenant_id)
            .values(**kwargs)
        )
        await self.db.commit()
        return await self.get_entity_page(entity_id, tenant_id)

    async def increment_page_visits(self, entity_id: int) -> None:
        await self.db.execute(
            update(EntityPage).where(EntityPage.entity_id == entity_id).values(
                visits_count=EntityPage.visits_count + 1,
                last_visit_at=func.now()
            )
        )
        await self.db.commit()

    # ========== Templates & Components ==========
    async def create_template(self, tenant_id: int, **kwargs) -> EntityPageTemplate:
        template = EntityPageTemplate(tenant_id=tenant_id, **kwargs)
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def list_templates(self, tenant_id: int) -> List[EntityPageTemplate]:
        result = await self.db.execute(select(EntityPageTemplate).where(EntityPageTemplate.tenant_id == tenant_id))
        return list(result.scalars().all())

    async def list_components(self, tenant_id: int) -> List[PageComponent]:
        result = await self.db.execute(select(PageComponent).where(PageComponent.tenant_id == tenant_id, PageComponent.is_active == True))
        return list(result.scalars().all())

    # ========== دوال مساعدة ==========
    async def list_entities_by_ids(self, entity_ids: List[int], tenant_id: int) -> List[SovereignEntity]:
        if not entity_ids:
            return []
        result = await self.db.execute(
            select(SovereignEntity).where(
                and_(
                    SovereignEntity.id.in_(entity_ids),
                    SovereignEntity.tenant_id == tenant_id,
                    SovereignEntity.is_deleted == False
                )
            )
        )
        return list(result.scalars().all())

    # ========== Entity Tree (Recursive CTE) ==========
    async def get_entity_tree(self, root_entity_id: int, tenant_id: int) -> Optional[dict]:
        recursive_cte = text("""
            WITH RECURSIVE entity_tree AS (
                SELECT id, name, entity_type, logo_url, parent_id, 1 as level
                FROM sovereign_entities_v2
                WHERE id = :root_id AND tenant_id = :tenant_id AND is_deleted = false
                UNION ALL
                SELECT e.id, e.name, e.entity_type, e.logo_url, e.parent_id, et.level + 1
                FROM sovereign_entities_v2 e
                INNER JOIN entity_tree et ON e.parent_id = et.id
                WHERE e.tenant_id = :tenant_id AND e.is_deleted = false
            )
            SELECT id, name, entity_type, logo_url, parent_id, level
            FROM entity_tree
            ORDER BY level, name
        """)

        result = await self.db.execute(recursive_cte, {
            "root_id": root_entity_id,
            "tenant_id": tenant_id
        })

        rows = result.all()
        if not rows:
            return None

        entity_map = {}
        root = None
        for row in rows:
            entity = {
                "id": row.id,
                "name": row.name,
                "entity_type": row.entity_type,
                "logo_url": row.logo_url,
                "parent_id": row.parent_id,
                "children": []
            }
            entity_map[row.id] = entity
            if row.parent_id is None:
                root = entity
            else:
                parent = entity_map.get(row.parent_id)
                if parent:
                    parent["children"].append(entity)

        return root