"""
مسارات (Endpoints) قطاع الاتصالات والإشعارات – النسخة المحصنة سيادياً
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.websockets import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
import json
import asyncio  # ✅ إضافة استيراد asyncio

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser, get_current_user_optional
from app.domains.identity.models import User
from app.domains.communications.service import CommunicationsService
from app.domains.communications.repository import CommunicationsRepository
from app.domains.communications.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.security import verify_token  # دالة للتحقق من JWT (موجودة في core/security)
from app.core.rate_limiter import rate_limit  # تطبيق Rate Limiting (يمكن استخدام slowapi أو تنفيذ مخصص)
from app.core.audit import audit_log  # خدمة تسجيل التدقيق السيادي
from app.core.idempotency import check_idempotency, store_idempotency_result  # آليات Idempotency

router = APIRouter(prefix="/communications", tags=["Sovereign Communications"])


# ========== WebSocket محمي بـ JWT مع تشغيل متزامن (Concurrent) ==========
@router.websocket("/ws")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(...)  # JWT يمرر كـ query parameter
):
    """
    WebSocket endpoint محمي – يتطلب تمرير JWT صالح.
    يستمع لإشعارات Redis ويرسلها للعميل، ويتلقى أوامر من العميل بشكل متزامن.
    """
    # 1. التحقق من صحة التوكن
    payload = verify_token(token)
    if not payload or "user_id" not in payload:
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    user_id = payload["user_id"]
    tenant_id = payload.get("tenant_id")
    
    # 2. قبول الاتصال
    await websocket.accept()
    
    # 3. الاتصال بـ Redis Pub/Sub
    from app.core.redis_client import redis_client
    channel = f"user:{user_id}:notifications"
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)
    
    # 4. تعريف المهام المتزامنة
    async def listen_to_redis():
        """الاستماع لرسائل Redis وإرسالها للعميل"""
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    
    async def listen_to_client():
        """الاستماع لرسائل العميل (Heartbeat/أوامر)"""
        while True:
            try:
                data = await websocket.receive_text()
                # يمكن معالجة أوامر العميل هنا (مثل تحديث حالة القراءة)
                # مثال: إذا كان data == "ping" يمكن الرد بـ "pong"
                pass
            except WebSocketDisconnect:
                break
    
    try:
        # تشغيل المهمتين معاً في نفس الوقت (Concurrency)
        redis_task = asyncio.create_task(listen_to_redis())
        client_task = asyncio.create_task(listen_to_client())
        
        # انتظر حتى تنتهي إحداهما (أي قطع الاتصال)
        done, pending = await asyncio.wait(
            [redis_task, client_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        # إلغاء المهمة الأخرى المعلقة
        for task in pending:
            task.cancel()
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()


# ========== دالة مساعدة للإرسال عبر Redis Pub/Sub ==========
async def broadcast_to_user_redis(user_id: int, message: dict):
    """إرسال إشعار عبر Redis Pub/Sub إلى مستخدم معين"""
    from app.core.redis_client import redis_client
    channel = f"user:{user_id}:notifications"
    await redis_client.publish(channel, json.dumps(message))


# ========== 1. الإشعارات ==========

@router.post("/notifications/send", response_model=NotificationResponse, status_code=201)
@rate_limit(max_requests=50, window=60)  # 50 طلب في الدقيقة
async def send_notification(
    data: NotificationCreate,
    request: Request,
    current_user: User = Depends(get_current_superuser),  # فقط الإدارة أو النظام
    db: AsyncSession = Depends(get_db)
):
    # التحقق من Idempotency
    idempotency_key = data.idempotency_key or request.headers.get("Idempotency-Key")
    if idempotency_key:
        cached_result = await check_idempotency(idempotency_key)
        if cached_result:
            return cached_result
    
    service = CommunicationsService(db)
    notification = await service.send_notification(
        user_id=data.user_id,
        title=data.title,
        body=data.body,
        data=data.data,
        priority=data.priority,
        channel=data.channel,
        idempotency_key=idempotency_key
    )
    
    # تسجيل التدقيق
    await audit_log(
        user_id=current_user.id,
        action="NOTIFICATION_SEND",
        resource_id=notification.id,
        details={"recipient": data.user_id, "title": data.title}
    )
    
    # تخزين نتيجة Idempotency (إن وجد)
    if idempotency_key:
        await store_idempotency_result(idempotency_key, notification)
    
    # إرسال عبر WebSocket (عبر Redis Pub/Sub) إذا كان المستخدم متصلاً
    await broadcast_to_user_redis(data.user_id, {
        "type": "notification",
        "id": notification.id,
        "title": notification.title,
        "body": notification.body,
        "data": notification.data,
        "created_at": notification.created_at.isoformat()
    })
    
    return notification


@router.get("/notifications/me", response_model=list[NotificationResponse])
@rate_limit(max_requests=100, window=60)
async def get_my_notifications(
    is_read: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    notifs = await service.get_user_notifications(current_user.id, is_read, skip, limit)
    return notifs


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
@rate_limit(max_requests=30, window=60)
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    notif = await service.mark_as_read(current_user.id, notification_id)
    return notif


# ========== 2. أجهزة الإشعارات (Push) ==========

@router.post("/devices/register", response_model=dict)
@rate_limit(max_requests=10, window=60)
async def register_device(
    data: DeviceRegister,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = CommunicationsRepository(db)
    await repo.register_device(
        user_id=current_user.id,
        device_token=data.device_token,
        platform=data.platform,
        is_active=True
    )
    
    await audit_log(
        user_id=current_user.id,
        action="DEVICE_REGISTER",
        details={"platform": data.platform}
    )
    
    return {"message": "تم تسجيل الجهاز بنجاح"}


# ========== 3. البريد الداخلي ==========

@router.post("/mail/send", response_model=MailMessageResponse, status_code=201)
@rate_limit(max_requests=30, window=60)
async def send_mail(
    data: MailMessageCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # التحقق من Idempotency
    idempotency_key = data.idempotency_key or request.headers.get("Idempotency-Key")
    if idempotency_key:
        cached_result = await check_idempotency(idempotency_key)
        if cached_result:
            return cached_result
    
    service = CommunicationsService(db)
    message = await service.send_mail(
        sender_id=current_user.id,
        recipient_id=data.recipient_id,
        subject=data.subject,
        body_text=data.body_text,
        body_html=data.body_html,
        is_certified=data.is_certified,
        attachments=data.attachments,
        idempotency_key=idempotency_key
    )
    
    # تسجيل التدقيق
    await audit_log(
        user_id=current_user.id,
        action="MAIL_SEND",
        resource_id=message.id,
        details={"recipient": data.recipient_id, "subject": data.subject}
    )
    
    if idempotency_key:
        await store_idempotency_result(idempotency_key, message)
    
    return message


@router.get("/mail/inbox", response_model=list[MailboxItemResponse])
@rate_limit(max_requests=50, window=60)
async def get_inbox(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    items = await service.get_inbox(current_user.id, skip, limit)
    return items


@router.get("/mail/sent", response_model=list[MailboxItemResponse])
@rate_limit(max_requests=50, window=60)
async def get_sent(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    items = await service.get_sent(current_user.id, skip, limit)
    return items


@router.post("/mail/move-to-trash/{item_id}")
@rate_limit(max_requests=30, window=60)
async def move_to_trash(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    await service.move_to_trash(current_user.id, item_id)
    
    await audit_log(
        user_id=current_user.id,
        action="MAIL_MOVE_TO_TRASH",
        resource_id=item_id
    )
    
    return {"message": "نقل إلى سلة المحذوفات"}


@router.post("/mail/restore/{item_id}")
@rate_limit(max_requests=30, window=60)
async def restore_from_trash(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    await service.restore_from_trash(current_user.id, item_id)
    
    await audit_log(
        user_id=current_user.id,
        action="MAIL_RESTORE",
        resource_id=item_id
    )
    
    return {"message": "استعادة من سلة المحذوفات"}


@router.post("/mail/archive/{item_id}")
@rate_limit(max_requests=30, window=60)
async def archive_message(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    await service.archive_message(current_user.id, item_id)
    
    await audit_log(
        user_id=current_user.id,
        action="MAIL_ARCHIVE",
        resource_id=item_id
    )
    
    return {"message": "تمت الأرشفة"}


@router.post("/mail/star/{item_id}")
@rate_limit(max_requests=30, window=60)
async def star_message(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    await service.star_message(current_user.id, item_id)
    return {"message": "تم تحديث النجمة"}


@router.post("/mail/mark-read/{item_id}")
@rate_limit(max_requests=30, window=60)
async def mark_read(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    await service.mark_conversation_read(current_user.id, item_id)
    return {"message": "تم تحديد كمقروء"}


@router.delete("/mail/permanent/{item_id}")
@rate_limit(max_requests=10, window=60)
async def delete_permanently(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    await service.delete_permanently(current_user.id, item_id)
    
    await audit_log(
        user_id=current_user.id,
        action="MAIL_DELETE_PERMANENT",
        resource_id=item_id
    )
    
    return {"message": "تم الحذف النهائي"}


# ========== 4. قوالب الاتصال (للإدارة) ==========

@router.post("/templates", response_model=CommunicationTemplateResponse, status_code=201)
@rate_limit(max_requests=20, window=60)
async def create_template(
    data: CommunicationTemplateCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    repo = CommunicationsRepository(db)
    template = await repo.create_template(
        tenant_id=tenant.id,
        name=data.name,
        trigger_event=data.trigger_event,
        subject_template=data.subject_template,
        body_template=data.body_template,
        channel=data.channel
    )
    
    await audit_log(
        user_id=current_user.id,
        action="TEMPLATE_CREATE",
        resource_id=template.id,
        details={"name": data.name}
    )
    
    return template


@router.get("/templates", response_model=list[CommunicationTemplateResponse])
@rate_limit(max_requests=50, window=60)
async def list_templates(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    repo = CommunicationsRepository(db)
    templates = await repo.list_templates(tenant.id)
    return templates