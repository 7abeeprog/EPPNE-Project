from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload  # ✅ إضافة الواردات الجديدة
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.domains.sovereign_entities.models import (
    SovereignEntity, EntityRepresentative, EntityPage, EntityPageTemplate,
    PageComponent, EntityDocument, KYBStatus, SovereignEntityType
)
from app.core.errors import NotFoundError


class SovereignEntitiesRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ========== Sovereign Entities ==========
    async def create_entity(self, **kwargs) -> SovereignEntity:
        entity = SovereignEntity(**kwargs)
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity

    async def get_entity(self, entity_id: int) -> Optional[SovereignEntity]:
        result = await self.db.execute(
            select(SovereignEntity).where(SovereignEntity.id == entity_id, SovereignEntity.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def get_entity_by_slug(self, slug: str) -> Optional[SovereignEntity]:
        result = await self.db.execute(
            select(SovereignEntity).join(EntityPage).where(EntityPage.slug == slug, SovereignEntity.is_active == True)
        )
        return result.scalar_one_or_none()

    async def list_entities(
        self,
        tenant_id: int,
        entity_type: Optional[SovereignEntityType] = None,
        kyb_status: Optional[KYBStatus] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[SovereignEntity]:
        query = select(SovereignEntity).where(SovereignEntity.tenant_id == tenant_id, SovereignEntity.is_deleted == False)
        if entity_type:
            query = query.where(SovereignEntity.entity_type == entity_type)
        if kyb_status:
            query = query.where(SovereignEntity.kyb_status == kyb_status)
        query = query.order_by(SovereignEntity.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_entity(self, entity_id: int, **kwargs) -> SovereignEntity:
        await self.db.execute(update(SovereignEntity).where(SovereignEntity.id == entity_id).values(**kwargs))
        await self.db.commit()
        entity = await self.get_entity(entity_id)
        if not entity:
            raise NotFoundError("Entity not found")
        return entity

    async def delete_entity(self, entity_id: int, soft: bool = True) -> None:
        if soft:
            await self.db.execute(update(SovereignEntity).where(SovereignEntity.id == entity_id).values(is_deleted=True, deleted_at=func.now()))
        else:
            await self.db.execute(delete(SovereignEntity).where(SovereignEntity.id == entity_id))
        await self.db.commit()

    # ========== Representatives ==========
    async def add_representative(self, **kwargs) -> EntityRepresentative:
        rep = EntityRepresentative(**kwargs)
        self.db.add(rep)
        await self.db.commit()
        await self.db.refresh(rep)
        return rep

    async def get_representatives(self, entity_id: int) -> List[EntityRepresentative]:
        result = await self.db.execute(select(EntityRepresentative).where(EntityRepresentative.entity_id == entity_id, EntityRepresentative.is_active == True))
        return result.scalars().all()

    async def remove_representative(self, entity_id: int, user_id: int) -> None:
        await self.db.execute(delete(EntityRepresentative).where(EntityRepresentative.entity_id == entity_id, EntityRepresentative.user_id == user_id))
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
        return result.scalars().all()

    async def update_document_status(self, doc_id: int, status: str, verifier_id: int, reason: str = None) -> EntityDocument:
        values = {"status": status, "verified_by": verifier_id, "verified_at": func.now()}
        if reason:
            values["rejection_reason"] = reason
        await self.db.execute(update(EntityDocument).where(EntityDocument.id == doc_id).values(**values))
        await self.db.commit()
        result = await self.db.execute(select(EntityDocument).where(EntityDocument.id == doc_id))
        return result.scalar_one()

    # ========== Entity Pages (Brand Builder) ==========
    async def create_entity_page(self, **kwargs) -> EntityPage:
        page = EntityPage(**kwargs)
        self.db.add(page)
        await self.db.commit()
        await self.db.refresh(page)
        return page

    async def get_entity_page(self, entity_id: int) -> Optional[EntityPage]:
        result = await self.db.execute(select(EntityPage).where(EntityPage.entity_id == entity_id))
        return result.scalar_one_or_none()

    async def update_entity_page(self, entity_id: int, **kwargs) -> EntityPage:
        await self.db.execute(update(EntityPage).where(EntityPage.entity_id == entity_id).values(**kwargs))
        await self.db.commit()
        return await self.get_entity_page(entity_id)

    async def increment_page_visits(self, entity_id: int) -> None:
        await self.db.execute(
            update(EntityPage).where(EntityPage.entity_id == entity_id).values(
                visits_count=EntityPage.visits_count + 1,
                last_visit_at=func.now()
            )
        )
        await self.db.commit()

    # ========== Templates & Components ==========
    async def create_template(self, **kwargs) -> EntityPageTemplate:
        template = EntityPageTemplate(**kwargs)
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def list_templates(self, tenant_id: int) -> List[EntityPageTemplate]:
        result = await self.db.execute(select(EntityPageTemplate).where(EntityPageTemplate.tenant_id == tenant_id))
        return result.scalars().all()

    async def list_components(self, tenant_id: int) -> List[PageComponent]:
        result = await self.db.execute(select(PageComponent).where(PageComponent.tenant_id == tenant_id, PageComponent.is_active == True))
        return result.scalars().all()

    # ========== دوال تم استئصال ألغامها (Missing Functions) ==========
    async def get_entity_by_registration(self, registration_number: str) -> Optional[SovereignEntity]:
        result = await self.db.execute(
            select(SovereignEntity).where(SovereignEntity.registration_number == registration_number)
        )
        return result.scalar_one_or_none()

    async def get_representatives_by_user(self, user_id: int) -> List[EntityRepresentative]:
        result = await self.db.execute(
            select(EntityRepresentative).where(
                EntityRepresentative.user_id == user_id, 
                EntityRepresentative.is_active == True
            )
        )
        return result.scalars().all()

    async def list_entities_by_ids(self, entity_ids: List[int]) -> List[SovereignEntity]:
        if not entity_ids:
            return []
        result = await self.db.execute(
            select(SovereignEntity).where(
                SovereignEntity.id.in_(entity_ids), 
                SovereignEntity.is_deleted == False
            )
        )
        return result.scalars().all()

    async def get_entity_page_by_slug(self, slug: str) -> Optional[EntityPage]:
        result = await self.db.execute(
            select(EntityPage).where(EntityPage.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_representative(self, entity_id: int, user_id: int) -> Optional[EntityRepresentative]:
        result = await self.db.execute(
            select(EntityRepresentative).where(
                EntityRepresentative.entity_id == entity_id, 
                EntityRepresentative.user_id == user_id, 
                EntityRepresentative.is_active == True
            )
        )
        return result.scalar_one_or_none()

    # ============================================================
    # 🆕 التحسينات الجديدة (Eager Loading & Tree)
    # ============================================================

    # 🔥 تحسين: جلب صفحة الكيان مع بيانات الكيان في استعلام واحد
    async def get_entity_page_with_entity(self, entity_id: int) -> Optional[tuple[EntityPage, SovereignEntity]]:
        """
        جلب صفحة الكيان مع الكيان المرتبط بها في استعلام واحد باستخدام selectinload.
        """
        result = await self.db.execute(
            select(EntityPage)
            .where(EntityPage.entity_id == entity_id)
            .options(selectinload(EntityPage.entity))  # تحميل الكيان المرتبط
        )
        page = result.scalar_one_or_none()
        if page:
            return page, page.entity
        return None, None

    async def get_entity_page_by_slug_with_entity(self, slug: str) -> Optional[tuple[EntityPage, SovereignEntity]]:
        """
        جلب صفحة الكيان عبر slug مع الكيان المرتبط في استعلام واحد.
        """
        result = await self.db.execute(
            select(EntityPage)
            .where(EntityPage.slug == slug)
            .options(selectinload(EntityPage.entity))
        )
        page = result.scalar_one_or_none()
        if page:
            return page, page.entity
        return None, None

    # 🟢 دالة استرجاع الشجرة (Hierarchical Tree)
    async def get_entity_tree(self, root_entity_id: int) -> dict:
        """
        استرجاع شجرة الكيان بالكامل (الأب مع جميع الأبناء والأحفاد) باستخدام استعلام واحد.
        يتم البناء في الذاكرة لتجنب استعلامات متكررة للـ DB.
        """
        # جلب جميع الكيانات التابعة لهذا الجذر (مع الأبناء المباشرين)
        result = await self.db.execute(
            select(SovereignEntity)
            .where(
                or_(
                    SovereignEntity.id == root_entity_id,
                    SovereignEntity.parent_id == root_entity_id
                ),
                SovereignEntity.is_deleted == False
            )
        )
        entities = result.scalars().all()
        
        # بناء شجرة (Map)
        entity_map = {e.id: e for e in entities}
        tree = []
        
        # ربط الأبناء بآبائهم
        for entity in entities:
            if entity.parent_id is None:
                tree.append(entity)  # الجذر
            else:
                parent = entity_map.get(entity.parent_id)
                if parent:
                    if not hasattr(parent, 'children'):
                        parent.children = []
                    parent.children.append(entity)
        
        # إرجاع الكائن الجذر مع أبنائه
        root = entity_map.get(root_entity_id)
        if root:
            return self._build_tree_dict(root)
        return None

    def _build_tree_dict(self, entity: SovereignEntity) -> dict:
        """
        تحويل الكيان والشجرة إلى قاموس للـ JSON.
        """
        return {
            "id": entity.id,
            "name": entity.name,
            "entity_type": entity.entity_type.value,
            "logo_url": entity.logo_url,
            "children": [self._build_tree_dict(child) for child in getattr(entity, 'children', [])]
        }