# app/domains/ai_agents/models.py
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, Enum as SQLEnum, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class AgentRole(str, enum.Enum):
    CEO = "CEO"
    SWARM_ORCHESTRATOR = "SWARM_ORCHESTRATOR"
    CLIMATE_BROKER = "CLIMATE_BROKER"
    ARBITRATOR = "ARBITRATOR"
    SURVIVAL_CRISIS = "SURVIVAL_CRISIS"
    PHILANTHROPY = "PHILANTHROPY"
    SALES_NEGOTIATOR = "SALES_NEGOTIATOR"
    DEVOPS_ARCHITECT = "DEVOPS_ARCHITECT"
    IOT_CONTROLLER = "IOT_CONTROLLER"
    HEALTH_BIO = "HEALTH_BIO"
    ACCESSIBILITY = "ACCESSIBILITY"
    EDUCATOR = "EDUCATOR"
    DIGITAL_TWIN = "DIGITAL_TWIN"
    SUPPORT = "SUPPORT"


class AgentStatus(str, enum.Enum):
    IDLE = "IDLE"
    ACTIVE = "ACTIVE"
    LEARNING = "LEARNING"
    SUSPENDED = "SUSPENDED"


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class AIAgent(Base):
    __tablename__ = "ai_agents"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    role = Column(SQLEnum(AgentRole), nullable=False)
    status = Column(SQLEnum(AgentStatus), default=AgentStatus.IDLE)

    system_prompt = Column(Text, nullable=False)
    base_model = Column(String(100), default="gemini-1.5-pro")

    can_execute_payments = Column(Boolean, default=False)
    can_sign_contracts = Column(Boolean, default=False)
    requires_human_approval = Column(Boolean, default=True)

    interaction_cost_mrusdt = Column(Numeric(15, 8), default=0)
    agent_wallet_address = Column(String(42), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_agent_tenant_owner", "tenant_id", "owner_id"),
        Index("ix_agent_status_role", "status", "role"),
    )


class AgentApprovalQueue(Base):
    __tablename__ = "agent_approval_queue"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("ai_agents.id"), nullable=False, index=True)
    human_approver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    action_type = Column(String(100), nullable=False)
    proposed_payload = Column(JSONB, nullable=False)

    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    human_feedback = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_approval_tenant_status", "tenant_id", "status"),
        Index("ix_approval_agent_status", "agent_id", "status"),
    )


class AITaskLog(Base):
    __tablename__ = "ai_task_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("ai_agents.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    task_type = Column(String(50), index=True)

    idempotency_key = Column(String(255), nullable=True, index=True)

    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    cost_mrusdt = Column(Numeric(15, 8), default=0)

    settlement_type = Column(String(50), default="WEB3_CRYPTO")
    payment_tx_hash = Column(String(100), nullable=True)

    used_model = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_tasklog_tenant_task", "tenant_id", "task_type"),
        Index("ix_tasklog_agent_created", "agent_id", "created_at"),
        Index("ix_tasklog_used_model", "used_model"),
        Index("ix_tasklog_created_type", "created_at", "task_type"),
    )