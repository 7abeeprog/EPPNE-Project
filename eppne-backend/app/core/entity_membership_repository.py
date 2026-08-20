# app/core/entity_membership_repository.py
from typing import List, Optional
from sqlalchemy import select, update, delete, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import (
    EntityMembership, EntityMembershipRole,
    EntityPermissionOverride,
    PermissionAuditLog, AuditScope, AuditAction,
)


class EntityMembershipRepository:
    """عمليات DB خام على الجداول الثلاثة. لا منطق تفويض هنا.

    `_upsert_override` و`_insert_audit_row` داخليتان (بادئة `_`) — لا
    تُستدعيان إلا من `EntityMembershipService`، لضمان أن كل تغيير على
    `entity_permission_overrides` يصاحبه دائمًا سطر `permission_audit_log`.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------------- عضوية ----------------

    async def add_member(
        self, *, entity_type: str, entity_id: int, user_id: int,
        tenant_id: int, role: EntityMembershipRole,
        signature_pub_key: Optional[str] = None,
    ) -> EntityMembership:
        member = EntityMembership(
            entity_type=entity_type, entity_id=entity_id, user_id=user_id,
            tenant_id=tenant_id, role=role, signature_pub_key=signature_pub_key,
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member

    async def update_member_role(
        self, *, entity_type: str, entity_id: int, user_id: int,
        new_role: EntityMembershipRole,
    ) -> Optional[EntityMembership]:
        await self.db.execute(
            update(EntityMembership)
            .where(
                and_(
                    EntityMembership.entity_type == entity_type,
                    EntityMembership.entity_id == entity_id,
                    EntityMembership.user_id == user_id,
                )
            )
            .values(role=new_role)
        )
        await self.db.commit()
        return await self.get_member(
            entity_type=entity_type, entity_id=entity_id, user_id=user_id
        )

    async def remove_member(
        self, *, entity_type: str, entity_id: int, user_id: int,
    ) -> None:
        """يحذف عضوية العضو + أي entity_permission_overrides مرتبطة به
        على نفس الكيان، في نفس الـtransaction — بدون هذا، إعادة إضافة
        العضو لاحقًا كانت ترث overrides قديمة بلا منح جديد صريح."""
        await self.db.execute(
            delete(EntityPermissionOverride).where(
                and_(
                    EntityPermissionOverride.entity_type == entity_type,
                    EntityPermissionOverride.entity_id == entity_id,
                    EntityPermissionOverride.user_id == user_id,
                )
            )
        )
        await self.db.execute(
            delete(EntityMembership).where(
                and_(
                    EntityMembership.entity_type == entity_type,
                    EntityMembership.entity_id == entity_id,
                    EntityMembership.user_id == user_id,
                )
            )
        )
        await self.db.commit()

    async def get_member(
        self, *, entity_type: str, entity_id: int, user_id: int,
    ) -> Optional[EntityMembership]:
        result = await self.db.execute(
            select(EntityMembership).where(
                and_(
                    EntityMembership.entity_type == entity_type,
                    EntityMembership.entity_id == entity_id,
                    EntityMembership.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_members(
        self, *, entity_type: str, entity_id: int,
    ) -> List[EntityMembership]:
        """أعضاء كيان بعينه — يستخدم فهرس (entity_type, entity_id)."""
        result = await self.db.execute(
            select(EntityMembership).where(
                and_(
                    EntityMembership.entity_type == entity_type,
                    EntityMembership.entity_id == entity_id,
                )
            )
        )
        return list(result.scalars().all())

    async def list_entities_for_user(
        self, *, user_id: int, tenant_id: int,
    ) -> List[EntityMembership]:
        """كيانات مستخدم بعينه — يستخدم فهرس (user_id, tenant_id)."""
        result = await self.db.execute(
            select(EntityMembership).where(
                and_(
                    EntityMembership.user_id == user_id,
                    EntityMembership.tenant_id == tenant_id,
                )
            )
        )
        return list(result.scalars().all())

    # ---------------- overrides (داخلية) ----------------

    async def _upsert_override(
        self, *, entity_type: str, entity_id: int, user_id: int, tenant_id: int,
        permission: str, granted: bool, granted_by: int,
        reason: Optional[str] = None,
    ) -> EntityPermissionOverride:
        stmt = pg_insert(EntityPermissionOverride).values(
            entity_type=entity_type, entity_id=entity_id, user_id=user_id,
            tenant_id=tenant_id, permission=permission, granted=granted,
            granted_by=granted_by, reason=reason,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_entity_permission_override",
            set_={
                "granted": granted,
                "granted_by": granted_by,
                "granted_at": stmt.excluded.granted_at,
                "reason": reason,
                "tenant_id": tenant_id,
            },
        ).returning(EntityPermissionOverride)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def has_permission_override(
        self, *, entity_type: str, entity_id: int, user_id: int, permission: str,
    ) -> Optional[bool]:
        """None = لا يوجد override صريح. True/False = قيمة صريحة."""
        result = await self.db.execute(
            select(EntityPermissionOverride.granted).where(
                and_(
                    EntityPermissionOverride.entity_type == entity_type,
                    EntityPermissionOverride.entity_id == entity_id,
                    EntityPermissionOverride.user_id == user_id,
                    EntityPermissionOverride.permission == permission,
                )
            )
        )
        row = result.scalar_one_or_none()
        return row

    # ---------------- audit (داخلية) ----------------

    async def _insert_audit_row(
        self, *, scope: AuditScope, tenant_id: int,
        entity_type: Optional[str], entity_id: Optional[int],
        target_user_id: int, permission: str, action: AuditAction,
        performed_by: int, reason: Optional[str] = None,
    ) -> PermissionAuditLog:
        row = PermissionAuditLog(
            scope=scope, tenant_id=tenant_id, entity_type=entity_type,
            entity_id=entity_id, target_user_id=target_user_id,
            permission=permission, action=action, performed_by=performed_by,
            reason=reason,
        )
        self.db.add(row)
        await self.db.flush()
        return row
