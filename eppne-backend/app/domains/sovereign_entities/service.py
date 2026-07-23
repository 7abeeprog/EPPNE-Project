# pyright: reportGeneralTypeIssues=false
# pyright: reportCallIssue=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportArgumentType=false

"""
خدمات قطاع الكيانات السيادية والهوية المؤسسية
يدعم: إدارة الكيانات، الممثلين، التحقق (KYB)، بناء الصفحات التفاعلية (Drag & Drop)،
والتكامل مع قطاعات المناقصات، التأمين، والدعوات.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, cast
import uuid
import re

from app.domains.sovereign_entities.repository import SovereignEntitiesRepository
from app.domains.finance.service import FinanceService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, ValidationError
from app.core.idempotency import get_idempotency_result, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.domains.sovereign_entities.models import (
    SovereignEntity, EntityRepresentative, EntityPage, EntityDocument,
    KYBStatus, EntityRole, SovereignEntityType,
    EntityPageTemplate, PageComponent
)
from sqlalchemy.sql import func


class SovereignEntitiesService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SovereignEntitiesRepository(db)
        self.finance = FinanceService(db)
        self.event_bus = EventBus(cast(Any, redis_client))

    # ==============================
    # 0. دوال Idempotency الموحّدة
    # ==============================

    async def _validate_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """التحقق من وجود نتيجة مخزنة مسبقاً لمفتاح Idempotency."""
        if idempotency_key:
            cached = await get_idempotency_result(idempotency_key)
            if cached is not None:
                return cached
        return None

    async def _store_idempotency(self, idempotency_key: str, result: Dict[str, Any]):
        """تخزين نتيجة العملية بعد النجاح."""
        if idempotency_key:
            await store_idempotency_result(idempotency_key, result)

    # ==============================
    # 1. إدارة الكيانات الأساسية
    # ==============================

    async def create_entity(self, user_id: int, tenant_id: int, data: dict) -> SovereignEntity:
        """إنشاء كيان سيادي جديد (شركة، وزارة، منظمة، إلخ)"""
        if data.get("registration_number"):
            existing = await self.repo.get_entity_by_registration(data["registration_number"])
            if existing:
                raise PermissionDeniedError("Entity with this registration number already exists")

        entity = await self.repo.create_entity(
            tenant_id=tenant_id,
            created_by=user_id,
            **data
        )

        slug = self._generate_slug(data["name"]) + f"-{entity.id}"
        await self.repo.create_entity_page(
            entity_id=entity.id,
            slug=slug,
            custom_structure=None
        )

        await self.repo.add_representative(
            entity_id=entity.id,
            user_id=user_id,
            role=EntityRole.OWNER,
            can_sign_contracts=True
        )

        await audit_log(  # type: ignore[call-arg]
            user_id=user_id,
            tenant_id=tenant_id,
            action="ENTITY_CREATED",
            resource_id=entity.id,
            details={"name": entity.name, "type": entity.entity_type.value}
        )

        await self.event_bus.publish("entity.created", {
            "entity_id": entity.id,
            "tenant_id": tenant_id,
            "name": entity.name
        })

        return entity

    async def get_entity(self, entity_id: int) -> SovereignEntity:
        entity = await self.repo.get_entity(entity_id)
        if not entity:
            raise NotFoundError("Entity not found")
        return entity

    async def list_entities(
        self,
        tenant_id: int,
        entity_type: Optional[SovereignEntityType] = None,
        kyb_status: Optional[KYBStatus] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[SovereignEntity]:
        """قائمة الكيانات مع فلترة حسب النوع وحالة KYB."""
        return await self.repo.list_entities(tenant_id, entity_type, kyb_status, skip, limit)

    async def get_my_entities(self, user_id: int) -> List[SovereignEntity]:
        """جلب الكيانات التي يمثلها المستخدم."""
        reps = await self.repo.get_representatives_by_user(user_id)
        entity_ids = [cast(int, r.entity_id) for r in reps]
        return await self.repo.list_entities_by_ids(entity_ids)

    async def update_entity(self, entity_id: int, user_id: int, data: dict) -> SovereignEntity:
        entity = await self.repo.get_entity(entity_id)
        if not entity:
            raise NotFoundError("Entity not found")
        if not await self._is_representative(entity_id, user_id):
            raise PermissionDeniedError("You are not authorized to update this entity")
        return await self.repo.update_entity(entity_id, **data)

    async def delete_entity(self, entity_id: int, user_id: int, soft: bool = True) -> None:
        entity = await self.repo.get_entity(entity_id)
        if not entity:
            raise NotFoundError("Entity not found")
        if not await self._is_representative(entity_id, user_id):
            raise PermissionDeniedError("You are not authorized to delete this entity")
        await self.repo.delete_entity(entity_id, soft)

    # ==============================
    # 2. إدارة الممثلين (Representatives)
    # ==============================

    async def add_representative(self, entity_id: int, admin_user_id: int, data: dict) -> EntityRepresentative:
        if not await self._is_authorized_representative(entity_id, admin_user_id, [EntityRole.OWNER, EntityRole.EXECUTIVE_DIRECTOR]):
            raise PermissionDeniedError("Only owner or executive director can add representatives")
        return await self.repo.add_representative(entity_id=entity_id, **data)

    async def remove_representative(self, entity_id: int, admin_user_id: int, user_id_to_remove: int) -> None:
        if not await self._is_authorized_representative(entity_id, admin_user_id, [EntityRole.OWNER, EntityRole.EXECUTIVE_DIRECTOR]):
            raise PermissionDeniedError("Only owner or executive director can remove representatives")
        await self.repo.remove_representative(entity_id, user_id_to_remove)

    async def get_representatives(self, entity_id: int) -> List[EntityRepresentative]:
        """جلب قائمة ممثلي الكيان."""
        return await self.repo.get_representatives(entity_id)

    # ==============================
    # 3. التحقق من الكيانات (KYB)
    # ==============================

    async def upload_kyb_document(
        self,
        entity_id: int,
        user_id: int,
        tenant_id: int,
        document_type: str,
        document_url: str
    ) -> EntityDocument:
        if not await self._is_representative(entity_id, user_id):
            raise PermissionDeniedError("Only entity representative can upload documents")
        return await self.repo.add_document(
            entity_id=entity_id,
            document_type=document_type,
            document_url=document_url,
            uploaded_by=user_id,
            status="PENDING"
        )

    async def get_kyb_documents(self, entity_id: int, user_id: int) -> List[EntityDocument]:
        """جلب مستندات KYB للكيان (يتطلب صلاحية ممثل)."""
        if not await self._is_representative(entity_id, user_id):
            raise PermissionDeniedError("Only entity representative can view documents")
        return await self.repo.get_documents(entity_id)

    async def review_kyb(
        self,
        entity_id: int,
        admin_id: int,
        status: str,
        rejection_reason: Optional[str] = None
    ) -> SovereignEntity:
        entity = await self.repo.get_entity(entity_id)
        if not entity:
            raise NotFoundError("Entity not found")
        if status == "VERIFIED":
            await self.repo.update_entity(
                entity_id,
                kyb_status=KYBStatus.VERIFIED,
                verified_by=admin_id,
                verified_at=func.now()
            )
        else:
            await self.repo.update_entity(
                entity_id,
                kyb_status=KYBStatus.REJECTED,
                rejection_reason=rejection_reason
            )
        return await self.repo.get_entity(entity_id)

    # ==============================
    # 4. بناء الهوية المؤسسية (Brand Builder)
    # ==============================

    async def get_entity_page(self, entity_id: int, include_private: bool = False) -> dict:
        entity = await self.repo.get_entity(entity_id)
        if not entity:
            raise NotFoundError("Entity not found")

        page = await self.repo.get_entity_page(entity_id)

        if not page:
            slug = self._generate_slug(cast(str, entity.name)) + f"-{entity.id}"
            page = await self.repo.create_entity_page(
                entity_id=entity.id,
                slug=slug,
                custom_structure=None
            )

        await self.repo.increment_page_visits(entity_id)

        page = await self.repo.get_entity_page(entity_id)

        if not page:
            raise NotFoundError("Entity page not found after creation")

        entity_data = {
            "id": entity.id,
            "name": entity.name,
            "logo_url": entity.logo_url,
            "cover_image_url": entity.cover_image_url,
            "primary_color": entity.primary_color,
            "secondary_color": entity.secondary_color,
            "kyb_status": entity.kyb_status.value if entity.kyb_status else None,
            "is_active": entity.is_active,
        }

        return {
            "entity": entity_data,
            "page": {
                "slug": page.slug,
                "meta_title": page.meta_title,
                "meta_description": page.meta_description,
                "custom_domain": page.custom_domain,
                "structure": page.custom_structure or await self._get_default_template_structure(),
                "visits_count": page.visits_count,
                "last_visit_at": page.last_visit_at,
                "published_at": page.published_at,
            }
        }

    async def update_entity_page(self, entity_id: int, user_id: int, data: dict) -> EntityPage:
        if not await self._is_representative(entity_id, user_id):
            raise PermissionDeniedError("Only entity representative can edit the page")
        return await self.repo.update_entity_page(entity_id, **data)

    async def publish_entity_page(self, entity_id: int, user_id: int) -> EntityPage:
        if not await self._is_representative(entity_id, user_id):
            raise PermissionDeniedError("Only entity representative can publish the page")
        return await self.repo.update_entity_page(entity_id, published_at=datetime.utcnow())

    async def get_public_entity_page(self, slug: str) -> dict:
        """جلب الصفحة العامة مع تحميل بيانات الكيان في استعلام واحد."""
        page, entity = await self.repo.get_entity_page_by_slug_with_entity(slug)
        if not page or not entity:
            raise NotFoundError("Page not found")
        if not entity.is_active:
            raise NotFoundError("Entity not active")

        await self.repo.increment_page_visits(cast(int, entity.id))

        return {
            "entity": {
                "id": entity.id,
                "name": entity.name,
                "logo_url": entity.logo_url,
                "cover_image_url": entity.cover_image_url,
                "primary_color": entity.primary_color,
                "secondary_color": entity.secondary_color,
            },
            "page": {
                "structure": page.custom_structure or await self._get_default_template_structure(),
                "meta_title": page.meta_title,
                "meta_description": page.meta_description,
            }
        }

    # ==============================
    # 5. قوالب ومكونات الصفحات
    # ==============================

    async def create_page_template(self, tenant_id: int, user_id: int, data: dict) -> EntityPageTemplate:
        """إنشاء قالب صفحة جديد (للمشرفين)."""
        return await self.repo.create_template(tenant_id=tenant_id, **data)

    async def list_templates(self, tenant_id: int) -> List[EntityPageTemplate]:
        """قائمة قوالب الصفحات للمستأجر."""
        return await self.repo.list_templates(tenant_id)

    async def list_components(self, tenant_id: int) -> List[PageComponent]:
        """قائمة مكونات الصفحات للمستأجر."""
        return await self.repo.list_components(tenant_id)

    # ==============================
    # 6. التكامل مع القطاعات الأخرى – الإيداع (مع Idempotency محسّن)
    # ==============================

    async def get_entity_balance(self, entity_id: int) -> Decimal:
        entity = await self.repo.get_entity(entity_id)
        if not entity:
            raise NotFoundError("Entity not found")
        return cast(Decimal, entity.treasury_balance_mrusdt)

    async def deposit_to_entity_wallet(
        self,
        entity_id: int,
        admin_user_id: int,
        amount: Decimal,
        currency: str = "MR_USDT",
        notes: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> dict:
        """
        إيداع مبلغ في خزينة الكيان (مثل تحويل من حساب رئيسي أو أرباح).
        يدعم Idempotency لمنع تكرار الإيداع.
        """
        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                return cached

        if not await self._is_authorized_representative(entity_id, admin_user_id, [EntityRole.OWNER, EntityRole.EXECUTIVE_DIRECTOR]):
            raise PermissionDeniedError("Only owner or executive director can deposit to entity wallet")

        entity = await self.repo.get_entity(entity_id)
        if not entity:
            raise NotFoundError("Entity not found")

        async with self.db.begin_nested():
            new_balance = cast(Decimal, entity.treasury_balance_mrusdt) + amount
            await self.repo.update_entity(entity_id, treasury_balance_mrusdt=new_balance)

            tx_hash = await self.finance.record_deposit(  # type: ignore[attr-defined]
                entity_id=entity_id,
                user_id=admin_user_id,
                amount=amount,
                currency=currency,
                notes=notes or f"Deposit to entity {entity.name}",
                idempotency_key=idempotency_key
            )

            await audit_log(  # type: ignore[call-arg]
                user_id=admin_user_id,
                tenant_id=entity.tenant_id,
                action="ENTITY_DEPOSIT",
                resource_id=entity_id,
                details={"amount": float(cast(Decimal, amount)), "currency": currency}
            )

            await self.event_bus.publish("entity.deposit", {
                "entity_id": entity_id,
                "amount": float(cast(Decimal, amount)),
                "currency": currency,
                "user_id": admin_user_id
            })

        result = {
            "transaction_hash": tx_hash,
            "new_balance": float(cast(Decimal, new_balance)),
            "currency": currency
        }

        # تخزين النتيجة كاملة
        if idempotency_key:
            await self._store_idempotency(idempotency_key, result)

        return result

    # ==============================
    # 7. التحويل من الكيان (مع Idempotency محسّن)
    # ==============================

    async def transfer_from_entity(
        self,
        entity_id: int,
        from_representative_id: int,
        to_address: str,
        amount: Decimal,
        currency: str = "MR_USDT",
        notes: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> str:
        """
        تحويل من خزينة الكيان إلى عنوان خارجي (مع Idempotency).
        """
        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                return cached.get("transaction_hash", "")

        entity = await self.repo.get_entity(entity_id)
        if not entity:
            raise NotFoundError("Entity not found")

        rep = await self.repo.get_representative(entity_id, from_representative_id)
        if not rep or not rep.can_sign_contracts:  # type: ignore
            raise PermissionDeniedError("You are not authorized to sign transfers from this entity")

        if cast(Decimal, entity.treasury_balance_mrusdt) < amount:
            raise InsufficientBalanceError("Insufficient entity balance")

        async with self.db.begin_nested():
            tx_hash = await self.finance.transfer(
                sender_id=from_representative_id,
                receiver_email=to_address,
                currency=currency,
                amount=amount,
                notes=notes or f"Transfer from entity {entity.name}",
                idempotency_key=idempotency_key or ""
            )

            new_balance = cast(Decimal, entity.treasury_balance_mrusdt) - amount
            await self.repo.update_entity(entity_id, treasury_balance_mrusdt=new_balance)

            await audit_log(  # type: ignore[call-arg]
                user_id=from_representative_id,
                tenant_id=entity.tenant_id,
                action="ENTITY_TRANSFER",
                resource_id=entity_id,
                details={
                    "to": to_address,
                    "amount": float(cast(Decimal, amount)),
                    "currency": currency,
                    "tx_hash": tx_hash
                }
            )

            await self.event_bus.publish("entity.transfer", {
                "entity_id": entity_id,
                "amount": float(cast(Decimal, amount)),
                "currency": currency,
                "to": to_address,
                "user_id": from_representative_id
            })

        result = {
            "transaction_hash": tx_hash,
            "new_balance": float(cast(Decimal, new_balance))
        }

        if idempotency_key:
            await self._store_idempotency(idempotency_key, result)

        return tx_hash

    # ==============================
    # 8. الهيكل التنظيمي (Tree)
    # ==============================

    async def get_entity_tree(self, entity_id: int) -> Optional[dict]:
        """
        جلب شجرة الكيان بالكامل (للعرض في واجهة الإدارة).
        """
        entity = await self.repo.get_entity(entity_id)
        if not entity:
            raise NotFoundError("Entity not found")
        tree = await self.repo.get_entity_tree(entity_id)
        return tree

    # ==============================
    # 9. دوال مساعدة
    # ==============================

    async def _is_representative(self, entity_id: int, user_id: int) -> bool:
        reps = await self.repo.get_representatives(entity_id)
        return any(r.user_id == user_id for r in reps)  # type: ignore

    async def _is_authorized_representative(
        self,
        entity_id: int,
        user_id: int,
        allowed_roles: List[EntityRole]
    ) -> bool:
        reps = await self.repo.get_representatives(entity_id)
        for r in reps:
            if r.user_id == user_id and r.role in allowed_roles:  # type: ignore
                return True
        return False

    def _generate_slug(self, name: str) -> str:
        slug = re.sub(r'[^a-zA-Z0-9\-]', '-', name.lower())
        slug = re.sub(r'-+', '-', slug).strip('-')
        return slug

    async def _get_default_template_structure(self) -> dict:
        return {
            "sections": [
                {
                    "id": "hero",
                    "layout": "full-width",
                    "components": [
                        {"component_type": "hero", "props": {"title": "مرحباً بكم", "subtitle": "نحن نبتكر المستقبل"}}
                    ]
                },
                {
                    "id": "services",
                    "layout": "grid",
                    "components": [
                        {"component_type": "services_grid", "props": {"items": []}}
                    ]
                }
            ]
        }