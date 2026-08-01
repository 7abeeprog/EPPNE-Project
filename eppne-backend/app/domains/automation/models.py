"""
نماذج (Models) قطاع الأتمتة المتقدمة – منافس n8n
يدعم: سير العمل (Workflows)، العقد (Nodes)، الحواف (Edges)، المشغلات (Triggers)،
التنفيذات، السجلات، والمتغيرات السرية (Secrets).
"""
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text, Boolean,
    Numeric, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB  # ✅ تم إضافة الاستيراد الصحيح
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class TriggerType(str, enum.Enum):
    WEBHOOK = "WEBHOOK"
    SCHEDULE = "SCHEDULE"
    EVENT = "EVENT"
    MANUAL = "MANUAL"


class NodeType(str, enum.Enum):
    HTTP_REQUEST = "HTTP_REQUEST"
    CONDITION = "CONDITION"
    DELAY = "DELAY"
    TRANSFORM = "TRANSFORM"
    NOTIFICATION = "NOTIFICATION"
    EMAIL = "EMAIL"
    AI_AGENT = "AI_AGENT"
    SQL_QUERY = "SQL_QUERY"
    WEBHOOK_RESPONSE = "WEBHOOK_RESPONSE"
    LOOP = "LOOP"
    WEBHOOK_TRIGGER = "WEBHOOK_TRIGGER"
    WEBSOCKET = "WEBSOCKET"
    FILE_UPLOAD = "FILE_UPLOAD"
    CREATE_USER = "CREATE_USER"
    ASSIGN_ROLE = "ASSIGN_ROLE"
    UPDATE_USER = "UPDATE_USER"
    DELETE_USER = "DELETE_USER"
    CREATE_ENTITY = "CREATE_ENTITY"
    UPDATE_ENTITY = "UPDATE_ENTITY"
    VERIFY_KYB = "VERIFY_KYB"
    ADD_REPRESENTATIVE = "ADD_REPRESENTATIVE"
    CREATE_INVOICE = "CREATE_INVOICE"
    TRANSFER_FUNDS = "TRANSFER_FUNDS"
    RECORD_PAYMENT = "RECORD_PAYMENT"
    CHECK_BALANCE = "CHECK_BALANCE"
    CREATE_ORDER = "CREATE_ORDER"
    UPDATE_INVENTORY = "UPDATE_INVENTORY"
    SHIP_ORDER = "SHIP_ORDER"
    CANCEL_ORDER = "CANCEL_ORDER"
    ENROLL_COURSE = "ENROLL_COURSE"
    COMPLETE_LESSON = "COMPLETE_LESSON"
    ISSUE_CERTIFICATE = "ISSUE_CERTIFICATE"
    CREATE_COURSE = "CREATE_COURSE"


class ExecutionStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETRY = "RETRY"
    CANCELLED = "CANCELLED"


class Workflow(Base):
    __tablename__ = "automation_workflows"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    trigger_type = Column(SQLEnum(TriggerType), nullable=False)
    trigger_config = Column(JSONB, nullable=False)

    nodes = Column(JSONB, nullable=False)
    edges = Column(JSONB, nullable=False)

    max_retries = Column(Integer, default=3)
    retry_delay_seconds = Column(Integer, default=5)
    timeout_seconds = Column(Integer, default=60)
    concurrency_limit = Column(Integer, default=10)

    webhook_path = Column(String(255), unique=True, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_workflow_tenant_active", "tenant_id", "is_active"),
        Index("ix_workflow_trigger_type", "trigger_type"),
    )


class WorkflowExecution(Base):
    __tablename__ = "automation_executions"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("automation_workflows.id"), nullable=False, index=True)
    triggered_by = Column(String(100), nullable=True)
    trigger_payload = Column(JSONB, nullable=True)

    trigger_ip = Column(String(45), nullable=True)
    trigger_user_agent = Column(String(255), nullable=True)

    status = Column(SQLEnum(ExecutionStatus), default=ExecutionStatus.PENDING)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)

    current_node_id = Column(String(100), nullable=True)
    node_results = Column(JSONB, default=dict)

    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    context = Column(JSONB, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_execution_workflow_status", "workflow_id", "status"),
        Index("ix_execution_created", "created_at"),
        Index("ix_execution_trigger_ip", "trigger_ip"),
        Index("ix_execution_status_created", "status", "created_at"),
    )


class NodeExecutionLog(Base):
    __tablename__ = "automation_node_logs"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("automation_executions.id"), nullable=False, index=True)
    node_id = Column(String(100), nullable=False)
    node_type = Column(String(50), nullable=False)

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="RUNNING")

    input_data = Column(JSONB, nullable=True)
    output_data = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_nodelog_execution_status", "execution_id", "status"),
    )


class WorkflowSecret(Base):
    __tablename__ = "automation_secrets"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    value_encrypted = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_secret_tenant_name", "tenant_id", "name", unique=True),
    )