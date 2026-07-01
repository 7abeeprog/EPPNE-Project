# app/domains/ai_agents/models.py
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum

# ========== الأنواع المساعدة ==========
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
    CANCELLED = "CANCELLED"  # 🔥 إلغاء الطلب


# ============================================================
# 1. الوكلاء الرقميون (مع فرض العزل السيادي)
# ============================================================
class AIAgent(Base):
    __tablename__ = "ai_agents"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 إلزامي
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)             # 🔥 إلزامي

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


# ============================================================
# 2. صمام الأمان البشري (Human-in-the-loop) مع Idempotency
# ============================================================
class AgentApprovalQueue(Base):
    __tablename__ = "agent_approval_queue"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    agent_id = Column(Integer, ForeignKey("ai_agents.id"), nullable=False, index=True)
    human_approver_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    action_type = Column(String(100), nullable=False)   # مثلاً: "TRANSFER_FUNDS", "SIGN_CONTRACT"
    proposed_payload = Column(JSON, nullable=False)     # البيانات المقترحة للتنفيذ

    # 🔥 Idempotency Key (لمنع التكرار)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)

    status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    human_feedback = Column(Text, nullable=True)        # تعليق الموافق/الرافض

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_approval_tenant_status", "tenant_id", "status"),
        Index("ix_approval_agent_status", "agent_id", "status"),
    )


# ============================================================
# 3. سجل استهلاك الذكاء الاصطناعي (Pay-per-Compute)
# ============================================================
class AITaskLog(Base):
    __tablename__ = "ai_task_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    agent_id = Column(Integer, ForeignKey("ai_agents.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    task_type = Column(String(50), index=True)          # "CHAT", "ANALYSIS", "DECISION", "EXECUTION"

    # 🔥 Idempotency Key (لمنع تسجيل المهام المكررة)
    idempotency_key = Column(String(255), nullable=True, index=True)

    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    cost_mrusdt = Column(Numeric(15, 8), default=0)     # التكلفة المحسوبة

    settlement_type = Column(String(50), default="WEB3_CRYPTO")
    payment_tx_hash = Column(String(100), nullable=True)

    # 🔥 النموذج المستخدم فعلياً (يُسجل من LLMFactory)
    used_model = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_tasklog_tenant_task", "tenant_id", "task_type"),
        Index("ix_tasklog_agent_created", "agent_id", "created_at"),
        Index("ix_tasklog_used_model", "used_model"),  # فهرس لتسريع تحليلات النماذج
    )