# app/domains/achievements/models.py
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Text, Boolean,
    DateTime, Enum as SQLEnum, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base
import enum


# ==========================================
# 1. تعريفات الأنواع (Enums)
# ==========================================
class AchievementCategory(str, enum.Enum):
    TRAINING = "TRAINING"
    TEAM_BUILDING = "TEAM_BUILDING"
    PROJECT_FUNDING = "PROJECT_FUNDING"


class AchievementTriggerType(str, enum.Enum):
    MANUAL = "MANUAL"
    AUTO_EVENT = "AUTO_EVENT"


# ==========================================
# 2. الموديلات (Models)
# ==========================================
class AchievementDefinition(Base):
    """تعريف إنجاز قابل للمنح — يدويًا (MANUAL) في هذه المرحلة، أو مستقبلًا
    تلقائيًا عبر حدث (AUTO_EVENT، trigger_event_name/trigger_threshold) —
    مفيش أي كود يقرأ trigger_event_name/trigger_threshold بعد؛ مجرد تخزين
    للمرحلة القادمة."""
    __tablename__ = "achievement_definitions"
    __table_args__ = (
        Index("ix_achievement_definitions_tenant_id", "tenant_id"),
        Index("ix_achievement_definitions_category", "category"),
        Index("ix_achievement_definitions_tenant_active", "tenant_id", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(SQLEnum(AchievementCategory, name="achievementcategory"), nullable=False)
    icon_url = Column(String(512), nullable=True)
    points_value = Column(Integer, nullable=False, default=0)

    trigger_type = Column(
        SQLEnum(AchievementTriggerType, name="achievementtriggertype"),
        nullable=False, default=AchievementTriggerType.MANUAL,
    )
    trigger_event_name = Column(String(100), nullable=True)
    trigger_threshold = Column(Integer, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserAchievement(Base):
    """إنجاز مُمنوح فعليًا لمستخدم. القيد الفريد (user_id،
    achievement_definition_id) يمنع منح نفس التعريف للمستخدم نفسه مرتين."""
    __tablename__ = "user_achievements"
    __table_args__ = (
        Index(
            "ix_user_achievements_unique_user_definition",
            "user_id", "achievement_definition_id", unique=True,
        ),
        Index("ix_user_achievements_tenant_id", "tenant_id"),
        Index("ix_user_achievements_user_id", "user_id"),
        Index("ix_user_achievements_achievement_definition_id", "achievement_definition_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    achievement_definition_id = Column(
        Integer, ForeignKey("achievement_definitions.id", ondelete="CASCADE"), nullable=False, index=True,
    )

    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # NULL لو مُنح تلقائيًا (AUTO_EVENT، المرحلة القادمة) — في هذه المرحلة
    # دايمًا current_user.id للمشرف المانح (منح يدوي بس).
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    # يُملآن فقط وقت المنح التلقائي المستقبلي — دايمًا NULL في هذه المرحلة.
    source_event_name = Column(String(100), nullable=True)
    source_payload = Column(JSONB, nullable=True)


class UserNetworkStats(Base):
    """عمود تراكمي محفوظ لحجم شبكة المستخدم (بوتكامب) — الشكل البنيوي فقط
    في هذه المرحلة. مفيش أي كود بيحدّث bootcamp_network_size بعد؛
    القيمة الافتراضية 0 لكل المستخدمين. راجع:
    .claude/reports/team-building-network-size-badge-investigation-session-log.md
    (§4.3) للسبب اللي خلانا نختار عمود تراكمي بدل حساب live بـCTE."""
    __tablename__ = "user_network_stats"
    __table_args__ = (
        Index("ix_user_network_stats_tenant_id", "tenant_id"),
    )

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False)
    bootcamp_network_size = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
