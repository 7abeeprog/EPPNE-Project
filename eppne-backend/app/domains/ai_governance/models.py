# app/domains/ai_governance/models.py
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text, Boolean, Numeric, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class UsagePeriod(str, enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class LimitType(str, enum.Enum):
    REQUEST_COUNT = "REQUEST_COUNT"
    TOKEN_COUNT = "TOKEN_COUNT"
    COST_MRUSDT = "COST_MRUSDT"
    CONCURRENT = "CONCURRENT"


class AgentQuota(Base):
    __tablename__ = "agent_quotas"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("ai_agents.id"), nullable=False, index=True)

    limit_type = Column(SQLEnum(LimitType), nullable=False)
    period = Column(SQLEnum(UsagePeriod), nullable=False)
    limit_value = Column(Numeric(15, 2), nullable=False)   # عدد الطلبات، التوكنات، أو التكلفة

    current_usage = Column(Numeric(15, 2), default=0)
    reset_at = Column(DateTime(timezone=True), nullable=False)   # موعد إعادة تعيين العداد
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_quota_tenant_agent", "tenant_id", "agent_id"),
        Index("ix_quota_reset", "reset_at"),
    )


class AgentUsageLog(Base):
    __tablename__ = "agent_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("ai_agents.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    action_type = Column(String(50), nullable=False)
    request_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_mrusdt = Column(Numeric(15, 8), default=0)
    response_time_ms = Column(Integer)
    status = Column(String(20), default="SUCCESS")
    error_message = Column(Text, nullable=True)

    # 🔥 Idempotency Key (لمنع تسجيل الاستخدام المكرر)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AgentRateLimit(Base):
    __tablename__ = "agent_rate_limits"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    agent_id = Column(Integer, ForeignKey("ai_agents.id"), nullable=False, index=True)

    requests_per_minute = Column(Integer, default=60)
    requests_per_hour = Column(Integer, default=1000)
    concurrent_limit = Column(Integer, default=10)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_ratelimit_tenant_agent", "tenant_id", "agent_id"),
    )


class AgentAuditLog(Base):
    __tablename__ = "agent_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    agent_id = Column(Integer, ForeignKey("ai_agents.id"), nullable=False)
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)  # CREATE, UPDATE, SUSPEND, ACTIVATE, CHANGE_QUOTA
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_audit_tenant_agent", "tenant_id", "agent_id"),
    )