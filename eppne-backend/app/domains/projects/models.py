# app/domains/projects/models.py
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Text, Boolean,
    Numeric, DateTime, Enum as SQLEnum, UniqueConstraint, Index
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

# ==========================================
# 1. تعريفات الأنواع (Enums)
# ==========================================
class ProjectType(str, enum.Enum):
    INDUSTRIAL = "INDUSTRIAL"
    AGRICULTURAL = "AGRICULTURAL"
    REAL_ESTATE = "REAL_ESTATE"
    EDUCATIONAL = "EDUCATIONAL"
    HEALTHCARE = "HEALTHCARE"
    ENERGY = "ENERGY"
    TECHNOLOGY = "TECHNOLOGY"
    SOCIAL = "SOCIAL"
    OTHER = "OTHER"

class ProjectStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    FUNDRAISING = "FUNDRAISING"
    UNDER_CONSTRUCTION = "UNDER_CONSTRUCTION"
    OPERATIONAL = "OPERATIONAL"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class ContributionType(str, enum.Enum):
    MONETARY = "MONETARY"
    LAND = "LAND"
    FACILITY = "FACILITY"
    LABOR_HOURS = "LABOR_HOURS"
    EQUIPMENT = "EQUIPMENT"
    CONSULTING = "CONSULTING"

class CarbonImpactScope(str, enum.Enum):
    CONSTRUCTION = "CONSTRUCTION"
    OPERATION = "OPERATION"
    FULL_LIFECYCLE = "FULL_LIFECYCLE"


# ==========================================
# 2. الموديلات (Models)
# ==========================================
class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    project_type = Column(SQLEnum(ProjectType), nullable=False)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.DRAFT)
    carbon_impact_scope = Column(SQLEnum(CarbonImpactScope), nullable=True)

    country = Column(String(100), nullable=True)
    funding_goal_mrusdt = Column(Numeric(30, 8), nullable=False)
    current_funding_mrusdt = Column(Numeric(30, 8), default=0)
    currency = Column(String(20), default="MR_USDT")
    is_published = Column(Boolean, default=False)

    # العلاقات
    milestones = relationship("ProjectMilestone", back_populates="project", cascade="all, delete-orphan")
    contributions = relationship("Contribution", back_populates="project", cascade="all, delete-orphan")
    updates = relationship("ProjectUpdate", back_populates="project", cascade="all, delete-orphan")
    followers = relationship("ProjectFollower", back_populates="project", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 🔥 فهارس جديدة محسّنة
    __table_args__ = (
        Index("ix_project_tenant_status", "tenant_id", "status"),
        Index("ix_project_tenant_type", "tenant_id", "project_type"),
        Index("ix_project_tenant_owner", "tenant_id", "owner_id"),
    )


class ProjectMilestone(Base):
    __tablename__ = "project_milestones"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    target_date = Column(DateTime(timezone=True), nullable=False)
    funds_to_release = Column(Numeric(30, 8), default=0)
    is_completed = Column(Boolean, default=False)

    project = relationship("Project", back_populates="milestones")

    __table_args__ = (
        Index("ix_milestone_tenant_project", "tenant_id", "project_id"),
    )


class Contribution(Base):
    __tablename__ = "contributions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    contributor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    contribution_type = Column(SQLEnum(ContributionType), nullable=False)
    equivalent_value_mrusdt = Column(Numeric(30, 8), nullable=False)
    amount_mrusdt = Column(Numeric(30, 8), nullable=True)
    status = Column(String(50), default="PENDING")

    # 🔥 Idempotency Key (لمنع التكرار)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    project = relationship("Project", back_populates="contributions")
    contributor = relationship("User", foreign_keys=[contributor_id])

    __table_args__ = (
        Index("ix_contribution_tenant_project", "tenant_id", "project_id"),
        Index("ix_contribution_tenant_contributor", "tenant_id", "contributor_id"),
    )


class ProjectUpdate(Base):
    __tablename__ = "project_updates"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    project = relationship("Project", back_populates="updates")
    author = relationship("User", foreign_keys=[author_id])

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_update_tenant_project", "tenant_id", "project_id"),
    )


class ProjectFollower(Base):
    __tablename__ = "project_followers"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    project = relationship("Project", back_populates="followers")
    user = relationship("User", foreign_keys=[user_id])

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "project_id", name="uq_user_project_follow"),
        Index("ix_follower_tenant_user", "tenant_id", "user_id"),
        Index("ix_follower_tenant_project", "tenant_id", "project_id"),
    )