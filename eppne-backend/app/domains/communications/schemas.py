from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.domains.communications.models import NotificationPriority, MailFolder

class NotificationCreate(BaseModel):
    user_id: int
    title: str
    body: str
    data: Dict[str, Any] = {}
    priority: NotificationPriority = NotificationPriority.NORMAL
    idempotency_key: Optional[str] = None  # ✅ جديد

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    body: str
    data: Dict[str, Any]
    priority: NotificationPriority
    is_read: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DeviceRegister(BaseModel):
    device_token: str
    platform: str

class MailMessageCreate(BaseModel):
    recipient_id: int
    subject: str
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    is_certified: bool = False
    attachments: Optional[List[Dict]] = None  # ✅ جديد
    idempotency_key: Optional[str] = None  # ✅ جديد

class MailMessageResponse(BaseModel):
    id: int
    thread_id: Optional[int]
    sender_id: int
    recipient_id: int
    subject: str
    body_text: Optional[str]
    body_html: Optional[str]
    is_certified: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class MailboxItemResponse(BaseModel):
    id: int
    message_id: int
    folder: MailFolder
    is_read: bool
    is_starred: bool
    message: MailMessageResponse
    model_config = ConfigDict(from_attributes=True)

class CommunicationTemplateCreate(BaseModel):
    name: str
    trigger_event: str
    subject_template: str
    body_template: str
    channel: str = "EMAIL"

class CommunicationTemplateResponse(BaseModel):
    id: int
    tenant_id: int
    name: str
    trigger_event: str
    subject_template: str
    body_template: str
    channel: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)