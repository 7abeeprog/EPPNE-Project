"""
مسارات (Endpoints) قطاع الاتصالات والإشعارات – النسخة المحصنة سيادياً
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.websockets import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, cast
from datetime import datetime
import json
import asyncio

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser, get_current_user_optional
from app.domains.identity.models import User
from app.domains.communications.service import CommunicationsService
from app.domains.communications.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.security import decode_token
from app.core.rate_limiter import rate_limit
from app.core.audit import audit_log
from app.core.idempotency import check_idempotency, store_idempotency_result

router = APIRouter(prefix="/communications", tags=["Sovereign Communications"])


# ============================================================
# WebSocket محمي بـ JWT
# ============================================================

@router.websocket("/ws")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(...)
):
    """WebSocket endpoint محمي – يتطلب تمرير JWT صالح."""
    payload = decode_token(token)
    if not payload or "user_id" not in payload:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    user_id = payload["user_id"]
    tenant_id = payload.get("tenant_id")

    await websocket.accept()

    from app.core.redis_client import redis_client
    channel = f"user:{user_id}:notifications"
    pubsub = redis_client.pubsub()  # type: ignore
    await pubsub.subscribe(channel)

    async def listen_to_redis():
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])

    async def listen_to_client():
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break

    try:
        redis_task = asyncio.create_task(listen_to_redis())
        client_task = asyncio.create_task(listen_to_client())
        done, pending = await asyncio.wait(
            [redis_task, client_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()


# ============================================================
# دالة مساعدة للإرسال عبر Redis Pub/Sub
# ============================================================

async def broadcast_to_user_redis(user_id: int, message: dict):
    from app.core.redis_client import redis_client
    channel = f"user:{user_id}:notifications"
    await redis_client.publish(channel, json.dumps(message))  # type: ignore


# ============================================================
# 1. الإشعارات (Notifications)
# ============================================================

@router.post("/notifications/send", response_model=NotificationResponse, status_code=201)
@rate_limit(max_requests=50, window_seconds=60)
async def send_notification(
    data: NotificationCreate,
    request: Request,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
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
        channel="IN_APP",
        idempotency_key=idempotency_key
    )

    await audit_log(
        user_id=cast(int, current_user.id),
        action="NOTIFICATION_SEND",
        resource_id=notification.id,  # type: ignore
        details={"recipient": data.user_id, "title": data.title}
    )

    if idempotency_key:
        await store_idempotency_result(idempotency_key, notification)

    await broadcast_to_user_redis(data.user_id, {
        "type": "notification",
        "id": notification.id,
        "title": notification.title,
        "body": notification.body,
        "data": notification.data,
        "created_at": notification.created_at.isoformat()  # type: ignore
    })

    return notification


@router.get("/notifications/me", response_model=List[NotificationResponse])
@rate_limit(max_requests=100, window_seconds=60)
async def get_my_notifications(
    is_read: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    notifs = await service.get_user_notifications(
        user_id=cast(int, current_user.id),
        is_read=is_read,
        skip=skip,
        limit=limit
    )
    return notifs


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    notif = await service.mark_as_read(
        user_id=cast(int, current_user.id),
        notification_id=notification_id
    )
    return notif


# ============================================================
# 2. أجهزة الإشعارات (Push)
# ============================================================

@router.post("/devices/register", response_model=dict)
@rate_limit(max_requests=10, window_seconds=60)
async def register_device(
    data: DeviceRegister,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    await service.register_device(
        user_id=cast(int, current_user.id),
        device_token=data.device_token,
        platform=data.platform
    )

    await audit_log(  # type: ignore
        user_id=cast(int, current_user.id),
        action="DEVICE_REGISTER",
        details={"platform": data.platform}
    )

    return {"message": "تم تسجيل الجهاز بنجاح"}


# ============================================================
# 3. البريد الداخلي (Mail)
# ============================================================

@router.post("/mail/send", response_model=MailMessageResponse, status_code=201)
@rate_limit(max_requests=30, window_seconds=60)
async def send_mail(
    data: MailMessageCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    idempotency_key = data.idempotency_key or request.headers.get("Idempotency-Key")
    if idempotency_key:
        cached_result = await check_idempotency(idempotency_key)
        if cached_result:
            return cached_result

    service = CommunicationsService(db)
    message = await service.send_mail(
        sender_id=cast(int, current_user.id),
        recipient_id=data.recipient_id,
        subject=data.subject,
        body_text=data.body_text,
        body_html=data.body_html,
        is_certified=data.is_certified,
        attachments=data.attachments,
        idempotency_key=idempotency_key
    )

    await audit_log(
        user_id=cast(int, current_user.id),
        action="MAIL_SEND",
        resource_id=message.id,  # type: ignore
        details={"recipient": data.recipient_id, "subject": data.subject}
    )

    if idempotency_key:
        await store_idempotency_result(idempotency_key, message)

    return message


@router.get("/mail/inbox", response_model=List[MailboxItemResponse])
@rate_limit(max_requests=50, window_seconds=60)
async def get_inbox(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    items = await service.get_inbox(
        user_id=cast(int, current_user.id),
        skip=skip,
        limit=limit
    )
    return items


@router.get("/mail/sent", response_model=List[MailboxItemResponse])
@rate_limit(max_requests=50, window_seconds=60)
async def get_sent(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    items = await service.get_sent(
        user_id=cast(int, current_user.id),
        skip=skip,
        limit=limit
    )
    return items


@router.post("/mail/move-to-trash/{item_id}")
@rate_limit(max_requests=30, window_seconds=60)
async def move_to_trash(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    await service.move_to_trash(
        user_id=cast(int, current_user.id),
        item_id=item_id
    )

    await audit_log(
        user_id=cast(int, current_user.id),
        action="MAIL_MOVE_TO_TRASH",
        resource_id=item_id  # type: ignore
    )

    return {"message": "نقل إلى سلة المحذوفات"}


@router.post("/mail/restore/{item_id}")
@rate_limit(max_requests=30, window_seconds=60)
async def restore_from_trash(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    await service.restore_from_trash(
        user_id=cast(int, current_user.id),
        item_id=item_id
    )

    await audit_log(
        user_id=cast(int, current_user.id),
        action="MAIL_MOVE_TO_TRASH",
        resource_id=item_id  # type: ignore
    )

    return {"message": "استعادة من سلة المحذوفات"}


@router.post("/mail/archive/{item_id}")
@rate_limit(max_requests=30, window_seconds=60)
async def archive_message(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    await service.archive_message(
        user_id=cast(int, current_user.id),
        item_id=item_id
    )

    await audit_log(
        user_id=cast(int, current_user.id),
        action="MAIL_ARCHIVE",
        resource_id=item_id  # type: ignore
    )

    return {"message": "تمت الأرشفة"}


@router.post("/mail/star/{item_id}")
@rate_limit(max_requests=30, window_seconds=60)
async def star_message(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    await service.star_message(
        user_id=cast(int, current_user.id),
        item_id=item_id
    )
    return {"message": "تم تحديث النجمة"}


@router.post("/mail/mark-read/{item_id}")
@rate_limit(max_requests=30, window_seconds=60)
async def mark_read(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    await service.mark_conversation_read(
        user_id=cast(int, current_user.id),
        item_id=item_id
    )
    return {"message": "تم تحديد كمقروء"}


@router.delete("/mail/permanent/{item_id}")
@rate_limit(max_requests=10, window_seconds=60)
async def delete_permanently(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    await service.delete_permanently(
        user_id=cast(int, current_user.id),
        item_id=item_id
    )

    await audit_log(
        user_id=cast(int, current_user.id),
        action="MAIL_DELETE_PERMANENT",
        resource_id=item_id  # type: ignore
    )

    return {"message": "تم الحذف النهائي"}


# ============================================================
# 4. قوالب الاتصال (للإدارة)
# ============================================================

@router.post("/templates", response_model=CommunicationTemplateResponse, status_code=201)
@rate_limit(max_requests=20, window_seconds=60)
async def create_template(
    data: CommunicationTemplateCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    template = await service.create_template(
        tenant_id=cast(int, tenant.id),
        name=data.name,
        trigger_event=data.trigger_event,
        subject_template=data.subject_template,
        body_template=data.body_template,
        channel=data.channel
    )

    await audit_log(
        user_id=cast(int, current_user.id),
        action="TEMPLATE_CREATE",
        resource_id=template.id,  # type: ignore
        details={"name": data.name}
    )

    return template


@router.get("/templates", response_model=List[CommunicationTemplateResponse])
@rate_limit(max_requests=50, window_seconds=60)
async def list_templates(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = CommunicationsService(db)
    templates = await service.list_templates(tenant_id=cast(int, tenant.id))
    return templates