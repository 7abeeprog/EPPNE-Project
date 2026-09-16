# app/domains/guardian/models.py
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Text, Boolean,
    Date, DateTime, Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum


# ==========================================
# 1. تعريفات الأنواع (Enums)
# ==========================================
class GuardianRelationshipType(str, enum.Enum):
    FATHER = "FATHER"
    MOTHER = "MOTHER"
    GUARDIAN = "GUARDIAN"


class GuardianRelationshipStatus(str, enum.Enum):
    PENDING_WARD_APPROVAL = "PENDING_WARD_APPROVAL"
    PENDING_ADMIN_REVIEW = "PENDING_ADMIN_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class GuardianVisibilitySector(str, enum.Enum):
    ACADEMY = "ACADEMY"
    SOCIAL = "SOCIAL"
    TRANSPORT = "TRANSPORT"
    HEALTH = "HEALTH"


# ==========================================
# 2. الموديلات (Models)
# ==========================================
class GuardianRelationship(Base):
    """رابط ولي أمر↔طالب — الأساس فقط (migration 056). صفر منطق تدفق
    (طلب/موافقة/رفض/تحقق إداري) فعلي في هذه المرحلة — الحالة الافتراضية
    PENDING_WARD_APPROVAL مجرد قيمة مخزَّنة، مفيش أي كود بعد يقرأها أو
    يغيّرها (المرحلة القادمة). راجع:
    .claude/reports/guardian-relationship-design-planning-session-log.md"""
    __tablename__ = "guardian_relationships"
    __table_args__ = (
        UniqueConstraint("guardian_user_id", "ward_user_id", name="uq_guardian_ward"),
        Index("ix_guardian_relationships_tenant_id", "tenant_id"),
        Index("ix_guardian_relationships_status", "status"),
        Index("ix_guardian_relationships_guardian_user_id", "guardian_user_id"),
        Index("ix_guardian_relationships_ward_user_id", "ward_user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False)

    guardian_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ward_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    relationship_type = Column(SQLEnum(GuardianRelationshipType, name="guardianrelationshiptype"), nullable=False)
    status = Column(
        SQLEnum(GuardianRelationshipStatus, name="guardianrelationshipstatus"),
        nullable=False, default=GuardianRelationshipStatus.PENDING_WARD_APPROVAL,
    )

    initiated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # منفصل عمدًا عن users.birth_date القديمة (99.16% NULL على الإنتاج —
    # راجع .claude/reports/birth-date-null-percentage-check-session-log.md)
    # — القيمة المُدخَلة صراحةً وقت طلب/موافقة الربط، مش المعتمدة على
    # البيانات القديمة الناقصة.
    ward_birth_date_provided = Column(Date, nullable=True)

    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class GuardianVisibilitySetting(Base):
    """تحكّم في ظهور قطاع مُعيَّن لعلاقة ولاية مُحدَّدة — الشكل البنيوي
    فقط، صفر منطق قراءة/فرض فعلي في هذه المرحلة."""
    __tablename__ = "guardian_visibility_settings"
    __table_args__ = (
        UniqueConstraint("guardian_relationship_id", "sector", name="uq_guardian_visibility_relationship_sector"),
        Index("ix_guardian_visibility_settings_relationship_id", "guardian_relationship_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    guardian_relationship_id = Column(
        Integer, ForeignKey("guardian_relationships.id", ondelete="CASCADE"), nullable=False,
    )
    sector = Column(SQLEnum(GuardianVisibilitySector, name="guardianvisibilitysector"), nullable=False)
    is_visible = Column(Boolean, nullable=False, default=True)
