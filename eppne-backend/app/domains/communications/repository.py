"""
مستودع قطاع الاتصالات والإشعارات
يدعم: الإشعارات، الأجهزة، البريد الداخلي، المرفقات، القوالب، والمجلدات
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any, Sequence
from datetime import datetime, timedelta
from app.domains.communications.models import (
    Notification, NotificationDevice, MailThread, MailMessage,
    MailboxItem, MailAttachment, CommunicationTemplate, MailFolder
)
from app.core.errors import NotFoundError


class CommunicationsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ==============================
    # 1. الإشعارات (Notifications)
    # ==============================

    async def create_notification(self, **kwargs) -> Notification:
        notification = Notification(**kwargs)
        self.db.add(notification)
        await self.db.flush()
        await self.db.refresh(notification)
        return notification

    async def get_notification(self, notification_id: int) -> Optional[Notification]:
        result = await self.db.execute(select(Notification).where(Notification.id == notification_id))  # type: ignore
        return result.scalar_one_or_none()

    async def get_notification_by_idempotency(self, idempotency_key: str) -> Optional[Notification]:
        if not idempotency_key:
            return None
        result = await self.db.execute(select(Notification).where(Notification.idempotency_key == idempotency_key))  # type: ignore
        return result.scalar_one_or_none()

    async def list_user_notifications(
        self,
        user_id: int,
        is_read: Optional[bool] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Sequence[Notification]:
        query = select(Notification).where(Notification.user_id == user_id)  # type: ignore
        if is_read is not None:
            query = query.where(Notification.is_read == is_read)  # type: ignore
        if priority:
            query = query.where(Notification.priority == priority)  # type: ignore
        query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)  # type: ignore
        result = await self.db.execute(query)
        return result.scalars().all()

    async def mark_notification_read(self, notification_id: int, user_id: int) -> Notification:
        notification = await self.get_notification(notification_id)
        if not notification or notification.user_id != user_id:  # type: ignore
            raise NotFoundError("الإشعار غير موجود")
        notification.is_read = True  # type: ignore
        notification.read_at = datetime.utcnow()  # type: ignore
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def mark_notification_sent(self, notification_id: int) -> Notification:
        notification = await self.get_notification(notification_id)
        if not notification:
            raise NotFoundError("الإشعار غير موجود")
        notification.is_sent = True  # type: ignore
        notification.sent_at = datetime.utcnow()  # type: ignore
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def delete_old_notifications(self, days: int = 30) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await self.db.execute(
            delete(Notification).where(Notification.created_at < cutoff, Notification.is_read == True)  # type: ignore
        )
        await self.db.commit()
        return result.rowcount

    # ==============================
    # 2. أجهزة الإشعارات (Push Devices)
    # ==============================

    async def register_device(self, **kwargs) -> NotificationDevice:
        device = NotificationDevice(**kwargs)
        self.db.add(device)
        await self.db.commit()
        await self.db.refresh(device)
        return device

    async def get_user_devices(self, user_id: int) -> Sequence[NotificationDevice]:
        result = await self.db.execute(
            select(NotificationDevice).where(
                NotificationDevice.user_id == user_id,  # type: ignore
                NotificationDevice.is_active == True  # type: ignore
            )
        )
        return result.scalars().all()

    async def deactivate_device(self, device_token: str) -> None:
        await self.db.execute(
            update(NotificationDevice).where(NotificationDevice.device_token == device_token).values(is_active=False)  # type: ignore
        )
        await self.db.commit()

    # ==============================
    # 3. البريد الداخلي (Mail)
    # ==============================

    async def create_thread(self, subject: str, tenant_id: int) -> MailThread:
        thread = MailThread(subject=subject, tenant_id=tenant_id)
        self.db.add(thread)
        await self.db.flush()
        await self.db.refresh(thread)
        return thread

    async def get_thread(self, thread_id: int) -> Optional[MailThread]:
        result = await self.db.execute(select(MailThread).where(MailThread.id == thread_id))  # type: ignore
        return result.scalar_one_or_none()

    async def create_message(self, **kwargs) -> MailMessage:
        message = MailMessage(**kwargs)
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def get_message(self, message_id: int) -> Optional[MailMessage]:
        result = await self.db.execute(select(MailMessage).where(MailMessage.id == message_id))  # type: ignore
        return result.scalar_one_or_none()

    async def get_message_by_idempotency(self, idempotency_key: str) -> Optional[MailMessage]:
        if not idempotency_key:
            return None
        result = await self.db.execute(select(MailMessage).where(MailMessage.idempotency_key == idempotency_key))  # type: ignore
        return result.scalar_one_or_none()

    async def add_to_mailbox(self, message_id: int, owner_id: int, folder: MailFolder) -> MailboxItem:
        item = MailboxItem(message_id=message_id, owner_id=owner_id, folder=folder)
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def get_mailbox_items(
        self,
        owner_id: int,
        folder: Optional[MailFolder] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Sequence[MailboxItem]:
        query = select(MailboxItem).where(MailboxItem.owner_id == owner_id)  # type: ignore
        if folder:
            query = query.where(MailboxItem.folder == folder)  # type: ignore
        query = query.order_by(MailboxItem.created_at.desc()).offset(skip).limit(limit)  # type: ignore
        result = await self.db.execute(query)
        return result.scalars().all()

    async def move_to_folder(self, item_id: int, new_folder: MailFolder, owner_id: int) -> MailboxItem:
        result = await self.db.execute(
            select(MailboxItem).where(MailboxItem.id == item_id, MailboxItem.owner_id == owner_id)  # type: ignore
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("العنصر غير موجود")
        item.folder = new_folder  # type: ignore
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def toggle_star(self, item_id: int, owner_id: int) -> MailboxItem:
        result = await self.db.execute(
            select(MailboxItem).where(MailboxItem.id == item_id, MailboxItem.owner_id == owner_id)  # type: ignore
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("العنصر غير موجود")
        item.is_starred = not item.is_starred  # type: ignore
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def mark_read(self, item_id: int, owner_id: int, is_read: bool = True) -> MailboxItem:
        result = await self.db.execute(
            select(MailboxItem).where(MailboxItem.id == item_id, MailboxItem.owner_id == owner_id)  # type: ignore
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("العنصر غير موجود")
        item.is_read = is_read  # type: ignore
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete_message_permanently(self, item_id: int, owner_id: int) -> None:
        result = await self.db.execute(
            select(MailboxItem).where(MailboxItem.id == item_id, MailboxItem.owner_id == owner_id)  # type: ignore
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("العنصر غير موجود")
        if item.folder != MailFolder.TRASH:  # type: ignore
            raise ValueError("لا يمكن الحذف النهائي إلا من سلة المحذوفات")
        await self.db.delete(item)
        await self.db.commit()

    # ==============================
    # 4. المرفقات (Attachments)
    # ==============================

    async def add_attachment(self, **kwargs) -> MailAttachment:
        attachment = MailAttachment(**kwargs)
        self.db.add(attachment)
        await self.db.flush()
        await self.db.refresh(attachment)
        return attachment

    async def get_attachments_for_message(self, message_id: int) -> Sequence[MailAttachment]:
        result = await self.db.execute(select(MailAttachment).where(MailAttachment.message_id == message_id))  # type: ignore
        return result.scalars().all()

    # ==============================
    # 5. قوالب الاتصال (Templates)
    # ==============================

    async def create_template(self, **kwargs) -> CommunicationTemplate:
        template = CommunicationTemplate(**kwargs)
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def get_template_by_event(self, tenant_id: int, trigger_event: str) -> Optional[CommunicationTemplate]:
        result = await self.db.execute(
            select(CommunicationTemplate).where(
                CommunicationTemplate.tenant_id == tenant_id,  # type: ignore
                CommunicationTemplate.trigger_event == trigger_event,  # type: ignore
                CommunicationTemplate.is_active == True  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def list_templates(self, tenant_id: int) -> Sequence[CommunicationTemplate]:
        result = await self.db.execute(
            select(CommunicationTemplate).where(CommunicationTemplate.tenant_id == tenant_id)  # type: ignore
        )
        return result.scalars().all()

    async def update_template(self, template_id: int, **kwargs) -> CommunicationTemplate:
        await self.db.execute(
            update(CommunicationTemplate).where(CommunicationTemplate.id == template_id).values(**kwargs)  # type: ignore
        )
        await self.db.commit()
        result = await self.db.execute(select(CommunicationTemplate).where(CommunicationTemplate.id == template_id))  # type: ignore
        template = result.scalar_one_or_none()
        if not template:
            raise NotFoundError("القالب غير موجود")
        return template