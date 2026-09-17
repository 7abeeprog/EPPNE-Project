# app/domains/sites/models.py
"""Site موحّد عابر للقطاعات — الأساس فقط (migration 057). صفر
repository/service/router بعد في هذه المرحلة — ربط الدومينات الأربعة
(iot/manufacturing/agritech/health) هو الخطوة التالية المنفصلة. راجع:
.claude/reports/unified-site-model-and-academy-camera-design-proposal.md
"""
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime,
    Boolean, Numeric, Enum as SQLEnum, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class SiteType(str, enum.Enum):
    """native_enum=False عمدًا — تُخزَّن كـVARCHAR بلا نوع ENUM في
    Postgres، لإضافة قيمة جديدة (مثلًا NURSERY) بصفر migration مستقبلًا.
    راجع §1.3.1 من مستند التصميم."""
    ACADEMY_CAMPUS = "ACADEMY_CAMPUS"
    FACTORY = "FACTORY"
    FARM = "FARM"
    HEALTH_FACILITY = "HEALTH_FACILITY"
    SPORTS_CLUB = "SPORTS_CLUB"
    TOURISM_SITE = "TOURISM_SITE"
    TRANSPORT_HUB = "TRANSPORT_HUB"
    WAREHOUSE = "WAREHOUSE"
    GENERIC = "GENERIC"


class Site(Base):
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    parent_site_id = Column(Integer, ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True)
    site_type = Column(SQLEnum(SiteType, native_enum=False, length=50), nullable=False, index=True)

    # زوج polymorphic بدل FK صريح لجدول entity واحد — يطابق نمط
    # app.core.models.EntityMembership المُقرَّر عمدًا بالمشروع (core لا
    # يعتمد على جدول entity دومين مُحدَّد). راجع §1.2 من مستند التصميم.
    entity_type = Column(String(50), nullable=True, index=True)
    entity_id = Column(Integer, nullable=True, index=True)

    name = Column(String(255), nullable=False)

    latitude = Column(Numeric(9, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)
    address_text = Column(String(500), nullable=True)
    geo_metadata = Column(JSONB, default=dict)

    manager_id = Column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)

    # حقل محجوز فقط — صفر منطق فرض فعلي في هذه المرحلة (يطابق نمط
    # academy_tenants.branding المكتشف سابقًا). راجع §1.3 من مستند التصميم.
    data_residency_preference = Column(String(50), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_site_tenant_type", "tenant_id", "site_type"),
        Index("ix_site_parent", "parent_site_id"),
        Index("ix_site_entity", "entity_type", "entity_id"),
    )
