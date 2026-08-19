"""
موديلات البنية التحتية العامة لصلاحيات وعضوية الكيانات (cross-domain).

تُستورَد من أي دومين يمثِّل كيانًا (sovereign_entities اليوم، courses/stores
مستقبلًا) — راجع .claude/plans/entity-membership-technical-design.md
للتصميم الكامل (schema، فهارس، قرار الحذف بلا ترحيل).

نطاق الجلسة 1 من 2 (Foundation): هذه الموديلات + منطق CRUD الأساسي فقط.
صفر لمس على sovereign_entities/models.py (EntityRole/EntityRepresentative
القديمان يبقيان كما هما حتى الجلسة 2).
"""
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text,
    Boolean, Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class EntityMembershipRole(str, enum.Enum):
    """منفصل عمدًا عن sovereign_entities.EntityRole رغم تطابق القيم —
    core لا يستورد من أي دومين وظيفي (entity-membership-technical-design.md §2)."""
    OWNER = "OWNER"
    EXECUTIVE_DIRECTOR = "EXECUTIVE_DIRECTOR"
    SIGNATORY = "SIGNATORY"
    REPRESENTATIVE = "REPRESENTATIVE"


class AuditScope(str, enum.Enum):
    PLATFORM = "PLATFORM"
    ENTITY = "ENTITY"


class AuditAction(str, enum.Enum):
    GRANT = "GRANT"
    REVOKE = "REVOKE"


class EntityMembership(Base):
    __tablename__ = "entity_memberships"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)  # Polymorphic — بلا FK حقيقي
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(SQLEnum(EntityMembershipRole), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "user_id", name="uq_entity_membership"),
        Index("ix_entity_memberships_entity", "entity_type", "entity_id"),
        Index("ix_entity_memberships_user_tenant", "user_id", "tenant_id"),
    )


class EntityPermissionOverride(Base):
    __tablename__ = "entity_permission_overrides"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    permission = Column(String(100), nullable=False)  # أول قيمة: "can_sign_contracts"
    granted = Column(Boolean, nullable=False)  # true=منح صريح، false=سحب صريح — لا NULL
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    reason = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "entity_type", "entity_id", "user_id", "permission",
            name="uq_entity_permission_override",
        ),
        # فهرس القيد الفريد يغطي أيضًا استعلام hot-path (فحص وجود override)
    )


class PermissionAuditLog(Base):
    __tablename__ = "permission_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    scope = Column(SQLEnum(AuditScope), nullable=False)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False)
    entity_type = Column(String(50), nullable=True)   # NULL إلا لو scope=ENTITY
    entity_id = Column(Integer, nullable=True)          # نفس الشرط
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    permission = Column(String(100), nullable=False)
    action = Column(SQLEnum(AuditAction), nullable=False)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    performed_at = Column(DateTime(timezone=True), server_default=func.now())
    reason = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_audit_performed_by", "performed_by"),
        Index("ix_audit_target_user", "target_user_id"),
        Index("ix_audit_performed_at", "performed_at"),
    )
