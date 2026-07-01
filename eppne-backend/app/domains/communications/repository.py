"""
مستودع قطاع الاتصالات والإشعارات
يدعم: الإشعارات، الأجهزة، البريد الداخلي، المرفقات، القوالب، والمجلدات
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload  # ✅ إضافة الاستيراد
from typing import Optional, List, Dict, Any
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
        """إنشاء إشعار جديد"""
        notification = Notification(**kwargs)
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def get_notification(self, notification_id: int) -> Optional[Notification]:
        """جلب إشعار بواسطة ID"""
        result = await self.db.execute(select(Notification).where(Notification.id == notification_id))
        return result.scalar_one_or_none()

    async def list_user_notifications(
        self,
        user_id: int,
        is_read: Optional[bool] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Notification]:
        """قائمة إشعارات المستخدم مع فلترة"""
        query = select(Notification).where(Notification.user_id == user_id)
        if is_read is not None:
            query = query.where(Notification.is_read == is_read)
        if priority:
            query = query.where(Notification.priority == priority)
        query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def mark_notification_read(self, notification_id: int, user_id: int) -> Notification:
        """تحديد إشعار كمقروء"""
        notification = await self.get_notification(notification_id)
        if not notification or notification.user_id != user_id:
            raise NotFoundError("الإشعار غير موجود")
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def mark_notification_sent(self, notification_id: int) -> Notification:
        """تحديد إشعار كمرسل (بعد إرساله فعلياً)"""
        notification = await self.get_notification(notification_id)
        if not notification:
            raise NotFoundError("الإشعار غير موجود")
        notification.is_sent = True
        notification.sent_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def delete_old_notifications(self, days: int = 30) -> int:
        """حذف الإشعارات الأقدم من عدد الأيام (تنظيف تلقائي)"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await self.db.execute(
            delete(Notification).where(Notification.created_at < cutoff, Notification.is_read == True)
        )
        await self.db.commit()
        return result.rowcount

    # ==============================
    # 2. أجهزة الإشعارات (Push Devices)
    # ==============================

    async def register_device(self, **kwargs) -> NotificationDevice:
        """تسجيل جهاز جديد (FCM token)"""
        device = NotificationDevice(**kwargs)
        self.db.add(device)
        await self.db.commit()
        await self.db.refresh(device)
        return device

    async def get_user_devices(self, user_id: int) -> List[NotificationDevice]:
        """جلب أجهزة المستخدم النشطة"""
        result = await self.db.execute(
            select(NotificationDevice).where(
                NotificationDevice.user_id == user_id,
                NotificationDevice.is_active == True
            )
        )
        return result.scalars().all()

    async def deactivate_device(self, device_token: str) -> None:
        """إلغاء تفعيل جهاز (عند تسجيل الخروج أو تغيير التوكن)"""
        await self.db.execute(
            update(NotificationDevice).where(NotificationDevice.device_token == device_token).values(is_active=False)
        )
        await self.db.commit()

    # ==============================
    # 3. البريد الداخلي (Mail)
    # ==============================

    async def create_thread(self, subject: str, tenant_id: int) -> MailThread:
        """إنشاء محادثة جديدة (Thread)"""
        thread = MailThread(subject=subject, tenant_id=tenant_id)
        self.db.add(thread)
        await self.db.commit()
        await self.db.refresh(thread)
        return thread

    async def get_thread(self, thread_id: int) -> Optional[MailThread]:
        result = await self.db.execute(select(MailThread).where(MailThread.id == thread_id))
        return result.scalar_one_or_none()

    async def create_message(self, **kwargs) -> MailMessage:
        """إنشاء رسالة جديدة (ترسل ويضاف نسختها للمجلدات)"""
        message = MailMessage(**kwargs)
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_message(self, message_id: int) -> Optional[MailMessage]:
        result = await self.db.execute(select(MailMessage).where(MailMessage.id == message_id))
        return result.scalar_one_or_none()

    async def add_to_mailbox(self, message_id: int, owner_id: int, folder: MailFolder) -> MailboxItem:
        """إضافة رسالة إلى صندوق بريد مستخدم معين (INBOX, SENT, ARCHIVE, TRASH)"""
        item = MailboxItem(message_id=message_id, owner_id=owner_id, folder=folder)
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def get_mailbox_items(
        self,
        owner_id: int,
        folder: Optional[MailFolder] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[MailboxItem]:
        """جلب عناصر صندوق البريد لمستخدم مع تحميل علاقات الرسالة والمرسل"""
        query = select(MailboxItem).where(
            MailboxItem.owner_id == owner_id,
            MailboxItem.is_deleted == False
        )
        
        # 🔥 التحسين الحاسم: جلب الرسائل المرتبطة (message) والمرسل (sender) في استعلام واحد
        query = query.options(
            selectinload(MailboxItem.message).selectinload(MailMessage.sender)
        )
        
        if folder:
            query = query.where(MailboxItem.folder == folder)
        query = query.order_by(MailboxItem.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def move_to_folder(self, item_id: int, new_folder: MailFolder, owner_id: int) -> MailboxItem:
        """نقل رسالة بين المجلدات (INBOX, ARCHIVE, TRASH)"""
        result = await self.db.execute(select(MailboxItem).where(MailboxItem.id == item_id, MailboxItem.owner_id == owner_id))
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("العنصر غير موجود")
        item.folder = new_folder
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def toggle_star(self, item_id: int, owner_id: int) -> MailboxItem:
        """تحديد/إلغاء تحديد النجمة (مهم)"""
        result = await self.db.execute(select(MailboxItem).where(MailboxItem.id == item_id, MailboxItem.owner_id == owner_id))
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("العنصر غير موجود")
        item.is_starred = not item.is_starred
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def mark_read(self, item_id: int, owner_id: int, is_read: bool = True) -> MailboxItem:
        """تحديد الرسالة كمقروءة أو غير مقروءة"""
        result = await self.db.execute(select(MailboxItem).where(MailboxItem.id == item_id, MailboxItem.owner_id == owner_id))
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("العنصر غير موجود")
        item.is_read = is_read
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete_message_permanently(self, item_id: int, owner_id: int) -> None:
        """حذف نهائي (من سلة المحذوفات)"""
        result = await self.db.execute(select(MailboxItem).where(MailboxItem.id == item_id, MailboxItem.owner_id == owner_id))
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("العنصر غير موجود")
        if item.folder != MailFolder.TRASH:
            raise ValueError("لا يمكن الحذف النهائي إلا من سلة المحذوفات")
        await self.db.delete(item)
        await self.db.commit()

    # ==============================
    # 4. المرفقات (Attachments)
    # ==============================

    async def add_attachment(self, **kwargs) -> MailAttachment:
        attachment = MailAttachment(**kwargs)
        self.db.add(attachment)
        await self.db.commit()
        await self.db.refresh(attachment)
        return attachment

    async def get_attachments_for_message(self, message_id: int) -> List[MailAttachment]:
        result = await self.db.execute(select(MailAttachment).where(MailAttachment.message_id == message_id))
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
                CommunicationTemplate.tenant_id == tenant_id,
                CommunicationTemplate.trigger_event == trigger_event,
                CommunicationTemplate.is_active == True
            )
        )
        return result.scalar_one_or_none()

    async def list_templates(self, tenant_id: int) -> List[CommunicationTemplate]:
        result = await self.db.execute(
            select(CommunicationTemplate).where(CommunicationTemplate.tenant_id == tenant_id)
        )
        return result.scalars().all()

    async def update_template(self, template_id: int, **kwargs) -> CommunicationTemplate:
        await self.db.execute(update(CommunicationTemplate).where(CommunicationTemplate.id == template_id).values(**kwargs))
        await self.db.commit()
        result = await self.db.execute(select(CommunicationTemplate).where(CommunicationTemplate.id == template_id))
        template = result.scalar_one_or_none()
        if not template:
            raise NotFoundError("القالب غير موجود")
        return template