"""
نماذج (Schemas) Pydantic لقطاع الأتمتة – التحقق من صحة البيانات وتسلسلها.
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from decimal import Decimal


class TriggerType(str, Enum):
    WEBHOOK = "WEBHOOK"
    SCHEDULE = "SCHEDULE"
    EVENT = "EVENT"
    MANUAL = "MANUAL"


class NodeType(str, Enum):
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
    WEBSOCKET = "WEBSOCKET"
    FILE_UPLOAD = "FILE_UPLOAD"
    SLACK = "SLACK"
    DATABASE = "DATABASE"
    HTTP_RESPONSE = "HTTP_RESPONSE"
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


# ---------------------- Node Configs ----------------------
class Position(BaseModel):
    x: float = Field(default=0.0, description="الإحداثي الأفقي")
    y: float = Field(default=0.0, description="الإحداثي الرأسي")


class HttpRequestConfig(BaseModel):
    url: str = Field(description="عنوان URL")
    method: str = Field(default="GET", description="طريقة HTTP")
    headers: Dict[str, str] = Field(default_factory=dict, description="رؤوس HTTP")
    body: Optional[Union[Dict, str]] = Field(default=None, description="محتوى الطلب")


class ConditionConfig(BaseModel):
    operator: str = Field(description="نوع المقارنة (eq, neq, gt, lt, contains, starts_with, ends_with)")
    left: str = Field(description="القيمة الأولى (يمكن أن تحتوي على متغيرات {{...}})")
    right: str = Field(description="القيمة الثانية")


class DelayConfig(BaseModel):
    seconds: int = Field(..., ge=0, le=86400, description="عدد الثواني للتأخير")


class TransformConfig(BaseModel):
    template: Dict[str, Any] = Field(..., description="قالب تحويل JSON مع دعم {{...}}")


class NotificationConfig(BaseModel):
    user_id: str = Field(description="معرف المستخدم المستلم")
    title: str = Field(description="عنوان الإشعار")
    body: str = Field(description="محتوى الإشعار")


class EmailConfig(BaseModel):
    to: str = Field(description="البريد الإلكتروني المستلم")
    subject: str = Field(description="موضوع البريد")
    body: str = Field(description="محتوى البريد")


class AIAgentConfig(BaseModel):
    agent_id: int = Field(description="معرف الوكيل الرقمي")
    prompt: str = Field(description="الرسالة أو التعليمات للوكيل")
    action_type: str = Field(default="ANALYZE_SENSOR", description="نوع الإجراء الذي سينفذه الوكيل")
    wait_for_approval: bool = Field(default=False, description="هل ينتظر الموافقة البشرية قبل المتابعة؟")
    save_response_to: str = Field(default="ai_response", description="المفتاح الذي سيُخزن فيه رد الوكيل في السياق")
    timeout_seconds: int = Field(default=60, ge=5, le=300, description="مهلة انتظار الوكيل")


class SqlQueryConfig(BaseModel):
    query: str = Field(description="استعلام SQL (يُسمح فقط SELECT)")


class WebhookResponseConfig(BaseModel):
    status_code: int = Field(default=200, description="رمز حالة HTTP")
    body: Union[Dict, str] = Field(default={}, description="محتوى الرد")


class LoopConfig(BaseModel):
    items: str = Field(description="مصدر العناصر للتكرار (مثل {{node_xxx.results}})")
    loop_nodes: List[str] = Field(description="معرفات العقد التي ستُكرر لكل عنصر")
    max_iterations: int = Field(default=100, ge=1, le=1000, description="الحد الأقصى لعدد التكرارات")


class WebSocketConfig(BaseModel):
    url: str = Field(description="wss:// أو ws:// عنوان خادم WebSocket")
    action: str = Field(description="send, receive, listen")
    message: Optional[str] = Field(default=None, description="الرسالة المراد إرسالها")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="مهلة الاتصال")
    save_response_to: str = Field(default="ws_response", description="المفتاح الذي سيُخزن فيه الرد في السياق")


class FileUploadConfig(BaseModel):
    source: str = Field(description="محتوى الملف أو مساره")
    filename: str = Field(description="اسم الملف المراد حفظه")
    destination: str = Field(description="المسار في التخزين (مثل s3://bucket/folder/)")
    make_public: bool = Field(default=False, description="هل يجعل الملف عاماً (public read)؟")
    save_url_to: str = Field(default="file_url", description="المفتاح الذي سيُخزن فيه رابط الملف في السياق")


class SlackConfig(BaseModel):
    webhook_url: str = Field(description="رابط Webhook الخاص بـ Slack")
    message: str = Field(description="الرسالة المراد إرسالها")
    channel: Optional[str] = Field(default=None, description="القناة (اختياري)")


class DatabaseConfig(BaseModel):
    query: str = Field(description="استعلام SQL")
    params: Dict[str, Any] = Field(default_factory=dict, description="معاملات الاستعلام")
    connection_string: Optional[str] = Field(default=None, description="سلسلة الاتصال (مشفر)")


class HttpResponseConfig(BaseModel):
    status_code: int = Field(default=200, description="رمز حالة HTTP")
    body: Dict[str, Any] = Field(default_factory=dict, description="محتوى الرد")
    headers: Dict[str, str] = Field(default_factory=dict, description="رؤوس HTTP")


# ============================================================
# 🧩 عقدة شاملة – تدعم جميع أنواع العقد
# ============================================================
class NodeConfigSchema(BaseModel):
    id: str = Field(description="معرف العقدة الفريد")
    type: NodeType = Field(description="نوع العقدة")
    name: str = Field(description="اسم العقدة")
    position: Position = Field(default_factory=Position, description="موقع العقدة")
    config: Dict[str, Any] = Field(default_factory=dict, description="إعدادات العقدة")


class EdgeConfigSchema(BaseModel):
    id: str = Field(description="معرف الحافة الفريد")
    source: str = Field(description="معرف العقدة المصدر")
    target: str = Field(description="معرف العقدة الهدف")
    sourceHandle: Optional[str] = Field(default=None, description="مقبض المصدر")
    targetHandle: Optional[str] = Field(default=None, description="مقبض الهدف")


# ---------------------- Workflow ----------------------
class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="اسم سير العمل")
    description: Optional[str] = Field(default=None, description="وصف سير العمل")
    trigger_type: TriggerType = Field(description="نوع المشغل")
    trigger_config: Dict[str, Any] = Field(description="إعدادات المشغل")
    nodes: List[NodeConfigSchema] = Field(description="قائمة العقد")
    edges: List[EdgeConfigSchema] = Field(description="قائمة الحواف")
    max_retries: int = Field(default=3, ge=0, le=10, description="عدد محاولات إعادة المحاولة")
    retry_delay_seconds: int = Field(default=5, ge=1, le=60, description="مدة الانتظار بين المحاولات")
    timeout_seconds: int = Field(default=60, ge=1, le=600, description="مهلة التنفيذ")
    concurrency_limit: int = Field(default=10, ge=1, le=100, description="الحد الأقصى للتنفيذ المتوازي")

    @field_validator("trigger_config")
    @classmethod
    def validate_trigger_config(cls, v: dict, info) -> dict:
        trigger_type = info.data.get("trigger_type")
        if trigger_type == TriggerType.SCHEDULE and "cron" not in v:
            raise ValueError("Schedule trigger requires 'cron' in trigger_config")
        if trigger_type == TriggerType.EVENT and "event" not in v:
            raise ValueError("Event trigger requires 'event' in trigger_config")
        return v


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255, description="اسم سير العمل")
    description: Optional[str] = Field(default=None, description="وصف سير العمل")
    is_active: Optional[bool] = Field(default=None, description="هل سير العمل نشط؟")
    nodes: Optional[List[NodeConfigSchema]] = Field(default=None, description="قائمة العقد")
    edges: Optional[List[EdgeConfigSchema]] = Field(default=None, description="قائمة الحواف")
    max_retries: Optional[int] = Field(default=None, ge=0, le=10, description="عدد محاولات إعادة المحاولة")
    retry_delay_seconds: Optional[int] = Field(default=None, ge=1, le=60, description="مدة الانتظار بين المحاولات")
    timeout_seconds: Optional[int] = Field(default=None, ge=1, le=600, description="مهلة التنفيذ")
    concurrency_limit: Optional[int] = Field(default=None, ge=1, le=100, description="الحد الأقصى للتنفيذ المتوازي")


class WorkflowResponse(BaseModel):
    id: int
    tenant_id: int
    created_by: int
    name: str
    description: Optional[str]
    is_active: bool
    trigger_type: TriggerType
    trigger_config: Dict[str, Any]
    nodes: List[NodeConfigSchema]
    edges: List[EdgeConfigSchema]
    max_retries: int
    retry_delay_seconds: int
    timeout_seconds: int
    concurrency_limit: int
    webhook_path: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------- Execution ----------------------
class ExecutionTrigger(BaseModel):
    trigger_payload: Optional[Dict[str, Any]] = Field(default=None, description="البيانات المرسلة مع المشغل")


class ExecutionResponse(BaseModel):
    id: int
    workflow_id: int
    triggered_by: str
    trigger_payload: Optional[Dict[str, Any]]
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    current_node_id: Optional[str]
    node_results: Dict[str, Any]
    error_message: Optional[str]
    retry_count: int
    context: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NodeLogResponse(BaseModel):
    id: int
    execution_id: int
    node_id: str
    node_type: str
    status: str
    input_data: Optional[Dict[str, Any]]
    output_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    started_at: datetime
    finished_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ---------------------- Secrets ----------------------
class SecretCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="اسم السر")
    value: str = Field(..., description="القيمة المراد تخزينها (ستُشفر تلقائياً)")


class SecretResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)