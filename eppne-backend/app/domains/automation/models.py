"""
نماذج (Models) قطاع الأتمتة المتقدمة – منافس n8n
يدعم: سير العمل (Workflows)، العقد (Nodes)، الحواف (Edges)، المشغلات (Triggers)،
التنفيذات، السجلات، والمتغيرات السرية (Secrets).
"""
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text, Boolean,
    Numeric, JSON, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class TriggerType(str, enum.Enum):
    WEBHOOK = "WEBHOOK"           # استقبال HTTP request
    SCHEDULE = "SCHEDULE"         # جدول زمني (cron)
    EVENT = "EVENT"               # حدث من النظام (مثل order.created)
    MANUAL = "MANUAL"             # تشغيل يدوي


class NodeType(str, enum.Enum):
    # الأنواع الأصلية
    HTTP_REQUEST = "HTTP_REQUEST"
    CONDITION = "CONDITION"       # if/else
    DELAY = "DELAY"               # انتظار
    TRANSFORM = "TRANSFORM"       # تحويل بيانات
    NOTIFICATION = "NOTIFICATION"
    EMAIL = "EMAIL"
    AI_AGENT = "AI_AGENT"
    SQL_QUERY = "SQL_QUERY"
    WEBHOOK_RESPONSE = "WEBHOOK_RESPONSE"
    LOOP = "LOOP"                 # تكرار (forEach)
    WEBHOOK_TRIGGER = "WEBHOOK_TRIGGER"  # عقدة خاصة لبدء webhook
    WEBSOCKET = "WEBSOCKET"          # عقدة WebSocket (اتصال ثنائي الاتجاه)
    FILE_UPLOAD = "FILE_UPLOAD"      # عقدة رفع ملف إلى S3/MinIO

    # ========== قطاع الهوية (Identity) ==========
    CREATE_USER = "CREATE_USER"
    ASSIGN_ROLE = "ASSIGN_ROLE"
    UPDATE_USER = "UPDATE_USER"
    DELETE_USER = "DELETE_USER"

    # ========== قطاع الكيانات السيادية (Sovereign Entities) ==========
    CREATE_ENTITY = "CREATE_ENTITY"
    UPDATE_ENTITY = "UPDATE_ENTITY"
    VERIFY_KYB = "VERIFY_KYB"
    ADD_REPRESENTATIVE = "ADD_REPRESENTATIVE"

    # ========== قطاع المالية (Finance) ==========
    CREATE_INVOICE = "CREATE_INVOICE"
    TRANSFER_FUNDS = "TRANSFER_FUNDS"
    RECORD_PAYMENT = "RECORD_PAYMENT"
    CHECK_BALANCE = "CHECK_BALANCE"

    # ========== قطاع التجارة (Commerce) ==========
    CREATE_ORDER = "CREATE_ORDER"
    UPDATE_INVENTORY = "UPDATE_INVENTORY"
    SHIP_ORDER = "SHIP_ORDER"
    CANCEL_ORDER = "CANCEL_ORDER"

    # ========== قطاع الأكاديمية (Academy) ==========
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

    # Trigger configuration
    trigger_type = Column(SQLEnum(TriggerType), nullable=False)
    trigger_config = Column(JSON, nullable=False)  # {cron: "0 9 * * *", webhook_path: "/unique-id", event: "order.created"}

    # Graph structure (nodes + edges) – هيكل قابل للتصدير من واجهة drag&drop
    nodes = Column(JSON, nullable=False)           # [{"id": "node1", "type": "HTTP_REQUEST", "position": {"x": 100, "y": 100}, "config": {...}}]
    edges = Column(JSON, nullable=False)           # [{"id": "edge1", "source": "node1", "target": "node2", "sourceHandle": "source", "targetHandle": "target"}]

    # Settings
    max_retries = Column(Integer, default=3)
    retry_delay_seconds = Column(Integer, default=5)
    timeout_seconds = Column(Integer, default=60)
    concurrency_limit = Column(Integer, default=10)

    # Webhook endpoint (يُولد تلقائياً عند اختيار webhook trigger)
    webhook_path = Column(String(255), unique=True, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_workflow_tenant_active", "tenant_id", "is_active"),
    )


class WorkflowExecution(Base):
    __tablename__ = "automation_executions"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("automation_workflows.id"), nullable=False, index=True)
    triggered_by = Column(String(100), nullable=True)  # webhook, schedule, manual, event
    trigger_payload = Column(JSON, nullable=True)      # البيانات الواردة (مثل payload webhook)

    # ============================================================
    # 🔥 الحقول الجديدة للتدقيق الأمني (Security Audit)
    # ============================================================
    trigger_ip = Column(String(45), nullable=True)       # دعم IPv6 (أقصى طول 45 حرفاً)
    trigger_user_agent = Column(String(255), nullable=True)  # وكيل المستخدم

    status = Column(SQLEnum(ExecutionStatus), default=ExecutionStatus.PENDING)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)

    current_node_id = Column(String(100), nullable=True)  # id of node currently executing
    node_results = Column(JSON, default=dict)             # تخزين نتائج كل عقدة

    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # تسليم البيانات بين العقد (context)
    context = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_execution_workflow_status", "workflow_id", "status"),
        Index("ix_execution_created", "created_at"),
        Index("ix_execution_trigger_ip", "trigger_ip"),  # ✅ فهرس لتسريع البحث عن IP
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

    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class WorkflowSecret(Base):
    __tablename__ = "automation_secrets"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    value_encrypted = Column(Text, nullable=False)   # تشفير لاحقاً (يمكن استخدام cryptography.fernet)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_secret_tenant_name", "tenant_id", "name", unique=True),
    )