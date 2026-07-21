# app/domains/communications/schemas.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.domains.communications.models import NotificationPriority, MailFolder


# ============================================================
# الإشعارات (Notifications)
# ============================================================

class NotificationCreate(BaseModel):
    user_id: int = Field(description="معرف المستخدم المستقبل")
    title: str = Field(description="عنوان الإشعار")
    body: str = Field(description="محتوى الإشعار")
    data: Dict[str, Any] = Field(default_factory=dict, description="بيانات إضافية")
    priority: NotificationPriority = Field(default=NotificationPriority.NORMAL, description="أولوية الإشعار")
    idempotency_key: Optional[str] = Field(default=None, description="مفتاح عدم التكرار")


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
    device_token: str = Field(description="رمز الجهاز (FCM/Expo)")
    platform: str = Field(description="نظام التشغيل (ios, android, web)")


# ============================================================
# البريد الداخلي (Mail)
# ============================================================

class MailMessageCreate(BaseModel):
    recipient_id: int = Field(description="معرف المستلم")
    subject: str = Field(description="موضوع الرسالة")
    body_text: Optional[str] = Field(default=None, description="محتوى نصي")
    body_html: Optional[str] = Field(default=None, description="محتوى HTML")
    is_certified: bool = Field(default=False, description="بريد موثق")
    attachments: Optional[List[Dict]] = Field(default=None, description="المرفقات")
    idempotency_key: Optional[str] = Field(default=None, description="مفتاح عدم التكرار")


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


# ============================================================
# قوالب الاتصال (Templates)
# ============================================================

class CommunicationTemplateCreate(BaseModel):
    name: str = Field(description="اسم القالب")
    trigger_event: str = Field(description="الحدث المشغل (USER_WELCOME, INVOICE_DUE, ...)")
    subject_template: str = Field(description="قالب الموضوع")
    body_template: str = Field(description="قالب المحتوى")
    channel: str = Field(default="EMAIL", description="قناة الإرسال")


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