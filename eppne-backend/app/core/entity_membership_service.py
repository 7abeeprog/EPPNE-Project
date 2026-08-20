# app/core/entity_membership_service.py
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entity_membership_repository import EntityMembershipRepository
from app.core.models import (
    EntityMembership, EntityMembershipRole,
    EntityPermissionOverride,
    AuditScope, AuditAction,
)


class EntityMembershipService:
    """طبقة عمل فوق EntityMembershipRepository.

    بنية تحتية عامة عابرة للدومينات (app/core/) — **لا تستورد أي شيء من
    sovereign_entities أو أي دومين وظيفي آخر**، وليس لها أي علم بأنواع
    الكيانات المحدَّدة أو بمن يُسمح له باستدعاء دوالها.

    **فحص التفويض ليس مسؤولية هذه الطبقة.** "هل current_user هذا فعلًا
    OWNER/EXECUTIVE_DIRECTOR على هذا الكيان، ومسموح له يستدعي
    add_member/grant_permission؟" — هذا القرار بالكامل مسؤولية الدومين
    المستدعي (current_user، سياق الـendpoint، قواعد التفويض الخاصة بنوع
    الكيان). يُطبَّق فعليًا في sovereign_entities عند دمجه بهذا النظام في
    الجلسة 2 من entity-membership-technical-design.md §6 — غير مُطبَّق هنا
    عمدًا، وهذه الجلسة (1 من 2) لا تلمس sovereign_entities إطلاقًا.

    الضمان الوحيد غير القابل للتفاوض في هذه الطبقة: أي تغيير على
    entity_permission_overrides (عبر grant_permission/revoke_permission)
    يُسجَّل تلقائيًا في permission_audit_log في نفس الـtransaction — لا
    يوجد مسار آخر متاح في الكودبيس لتعديل الـoverrides بدون هذا التسجيل.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EntityMembershipRepository(db)

    # ---------------- عضوية: تمرير مباشر ----------------

    async def add_member(
        self, *, entity_type: str, entity_id: int, user_id: int,
        tenant_id: int, role: EntityMembershipRole,
        signature_pub_key: Optional[str] = None,
    ) -> EntityMembership:
        return await self.repo.add_member(
            entity_type=entity_type, entity_id=entity_id, user_id=user_id,
            tenant_id=tenant_id, role=role, signature_pub_key=signature_pub_key,
        )

    async def change_role(
        self, *, entity_type: str, entity_id: int, user_id: int,
        new_role: EntityMembershipRole,
    ) -> Optional[EntityMembership]:
        return await self.repo.update_member_role(
            entity_type=entity_type, entity_id=entity_id, user_id=user_id,
            new_role=new_role,
        )

    async def remove_member(
        self, *, entity_type: str, entity_id: int, user_id: int,
    ) -> None:
        await self.repo.remove_member(
            entity_type=entity_type, entity_id=entity_id, user_id=user_id,
        )

    async def get_member(
        self, *, entity_type: str, entity_id: int, user_id: int,
    ) -> Optional[EntityMembership]:
        return await self.repo.get_member(entity_type=entity_type, entity_id=entity_id, user_id=user_id)

    async def get_members(
        self, *, entity_type: str, entity_id: int,
    ) -> List[EntityMembership]:
        return await self.repo.list_members(entity_type=entity_type, entity_id=entity_id)

    async def get_user_entities(
        self, *, user_id: int, tenant_id: int,
    ) -> List[EntityMembership]:
        return await self.repo.list_entities_for_user(user_id=user_id, tenant_id=tenant_id)

    # ---------------- overrides: المسار الوحيد لتعديلها ----------------

    async def grant_permission(
        self, *, entity_type: str, entity_id: int, user_id: int, tenant_id: int,
        permission: str, granted_by: int, reason: Optional[str] = None,
    ) -> EntityPermissionOverride:
        override = await self.repo._upsert_override(
            entity_type=entity_type, entity_id=entity_id, user_id=user_id,
            tenant_id=tenant_id, permission=permission, granted=True,
            granted_by=granted_by, reason=reason,
        )
        await self.repo._insert_audit_row(
            scope=AuditScope.ENTITY, tenant_id=tenant_id,
            entity_type=entity_type, entity_id=entity_id,
            target_user_id=user_id, permission=permission,
            action=AuditAction.GRANT, performed_by=granted_by, reason=reason,
        )
        await self.db.commit()
        await self.db.refresh(override)
        return override

    async def revoke_permission(
        self, *, entity_type: str, entity_id: int, user_id: int, tenant_id: int,
        permission: str, revoked_by: int, reason: Optional[str] = None,
    ) -> EntityPermissionOverride:
        override = await self.repo._upsert_override(
            entity_type=entity_type, entity_id=entity_id, user_id=user_id,
            tenant_id=tenant_id, permission=permission, granted=False,
            granted_by=revoked_by, reason=reason,
        )
        await self.repo._insert_audit_row(
            scope=AuditScope.ENTITY, tenant_id=tenant_id,
            entity_type=entity_type, entity_id=entity_id,
            target_user_id=user_id, permission=permission,
            action=AuditAction.REVOKE, performed_by=revoked_by, reason=reason,
        )
        await self.db.commit()
        await self.db.refresh(override)
        return override

    async def check_permission(
        self, *, entity_type: str, entity_id: int, user_id: int, permission: str,
    ) -> Optional[bool]:
        return await self.repo.has_permission_override(
            entity_type=entity_type, entity_id=entity_id,
            user_id=user_id, permission=permission,
        )
