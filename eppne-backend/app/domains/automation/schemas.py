"""
نماذج (Schemas) Pydantic لقطاع الأتمتة – التحقق من صحة البيانات وتسلسلها.
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class TriggerType(str, Enum):
    WEBHOOK = "WEBHOOK"
    SCHEDULE = "SCHEDULE"
    EVENT = "EVENT"
    MANUAL = "MANUAL"
    WEBHOOK_RESPONSE = "WEBHOOK_RESPONSE"
    LOOP = "LOOP"
    WEBSOCKET = "WEBSOCKET"
    FILE_UPLOAD = "FILE_UPLOAD"

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


# ---------------------- Node Configs ----------------------
class Position(BaseModel):
    x: float = 0
    y: float = 0


class HttpRequestConfig(BaseModel):
    url: str
    method: str = "GET"
    headers: Dict[str, str] = {}
    body: Optional[Union[Dict, str]] = None


class ConditionConfig(BaseModel):
    operator: str = Field(..., description="eq, neq, gt, lt, contains, starts_with, ends_with")
    left: str = Field(..., description="القيمة الأولى (يمكن أن تحتوي على متغيرات {{...}})")
    right: str = Field(..., description="القيمة الثانية")


class DelayConfig(BaseModel):
    seconds: int = Field(..., ge=0, le=86400)


class TransformConfig(BaseModel):
    template: Dict[str, Any] = Field(..., description="قالب تحويل JSON مع دعم {{...}}")


class NotificationConfig(BaseModel):
    user_id: str
    title: str
    body: str


class EmailConfig(BaseModel):
    to: str
    subject: str
    body: str


# ============================================================
# 🔥 AIAgentConfig – محدث لدعم الإجراءات والموافقات البشرية
# ============================================================
class AIAgentConfig(BaseModel):
    agent_id: int = Field(..., description="معرف الوكيل الرقمي")
    prompt: str = Field(..., description="الرسالة أو التعليمات للوكيل")
    action_type: str = Field("ANALYZE_SENSOR", description="نوع الإجراء الذي سينفذه الوكيل")
    wait_for_approval: bool = Field(False, description="هل ينتظر الموافقة البشرية قبل المتابعة؟")
    save_response_to: str = Field("ai_response", description="المفتاح الذي سيُخزن فيه رد الوكيل في السياق")
    timeout_seconds: int = Field(60, ge=5, le=300, description="مهلة انتظار الوكيل")


class SqlQueryConfig(BaseModel):
    query: str = Field(..., description="استعلام SQL (يُسمح فقط SELECT إلا إذا تم منح أذونات خاصة)")


class WebhookResponseConfig(BaseModel):
    status_code: int = 200
    body: Union[Dict, str] = {}


class LoopConfig(BaseModel):
    items: str = Field(..., description="مصدر العناصر للتكرار (مثل {{node_xxx.results}})")
    loop_nodes: List[str] = Field(..., description="معرفات العقد التي ستُكرر لكل عنصر")


class WebSocketConfig(BaseModel):
    url: str = Field(..., description="wss:// أو ws:// عنوان خادم WebSocket")
    action: str = Field(..., description="send, receive, listen")  # send: إرسال رسالة، receive: استقبال رسالة واحدة، listen: الاستماع المستمر
    message: Optional[str] = Field(None, description="الرسالة المراد إرسالها (يمكن أن تحتوي على متغيرات {{...}})")
    timeout_seconds: int = Field(30, ge=1, le=300)
    save_response_to: str = Field("ws_response", description="المفتاح الذي سيُخزن فيه الرد في السياق")


class FileUploadConfig(BaseModel):
    source: str = Field(..., description="محتوى الملف أو مساره (يمكن أن يكون {{node_xxx.output}})")
    filename: str = Field(..., description="اسم الملف المراد حفظه")
    destination: str = Field(..., description="المسار في التخزين (مثل s3://bucket/folder/ أو minio://bucket/folder)")
    make_public: bool = Field(False, description="هل يجعل الملف عاماً (public read)؟")
    save_url_to: str = Field("file_url", description="المفتاح الذي سيُخزن فيه رابط الملف في السياق")


# ============================================================
# 🧩 عقدة شاملة – تدعم جميع أنواع العقد بما فيها AI_AGENT
# ============================================================
class NodeConfigSchema(BaseModel):
    id: str
    type: NodeType
    name: str
    position: Position = Position()
    config: Dict[str, Any] = Field(default_factory=dict)


class EdgeConfigSchema(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None


# ---------------------- Workflow ----------------------
class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_type: TriggerType
    trigger_config: Dict[str, Any]
    nodes: List[NodeConfigSchema]
    edges: List[EdgeConfigSchema]
    max_retries: int = 3
    retry_delay_seconds: int = 5
    timeout_seconds: int = 60
    concurrency_limit: int = 10

    @field_validator("trigger_config")
    def validate_trigger_config(cls, v, info):
        trigger_type = info.data.get("trigger_type")
        if trigger_type == TriggerType.SCHEDULE and "cron" not in v:
            raise ValueError("Schedule trigger requires 'cron' in trigger_config")
        if trigger_type == TriggerType.EVENT and "event" not in v:
            raise ValueError("Event trigger requires 'event' in trigger_config")
        if trigger_type == TriggerType.WEBHOOK:
            # webhook_path يُولد تلقائياً – لا يحتاج إلى تحقق
            pass
        return v


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    nodes: Optional[List[NodeConfigSchema]] = None
    edges: Optional[List[EdgeConfigSchema]] = None
    max_retries: Optional[int] = None
    retry_delay_seconds: Optional[int] = None
    timeout_seconds: Optional[int] = None
    concurrency_limit: Optional[int] = None


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
    trigger_payload: Optional[Dict[str, Any]] = None


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
    name: str = Field(..., min_length=1, max_length=100)
    value: str


class SecretResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)