"""
خدمات قطاع الاتصالات – النسخة المحصنة والمُعدة للـ Async
"""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional, List, Dict, Any, cast
import uuid
import json

from app.domains.communications.repository import CommunicationsRepository
from app.domains.communications.models import MailFolder, NotificationPriority, NotificationChannel, Notification, MailMessage, MailboxItem, NotificationDevice, CommunicationTemplate
from app.core.errors import NotFoundError, PermissionDeniedError, IdempotencyError
from app.domains.identity.repository import UserRepository
from app.core.celery_app import send_notification_task, send_email_task


class CommunicationsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CommunicationsRepository(db)
        self.user_repo = UserRepository(db)

    # ============================================================
    # دوال مساعدة
    # ============================================================

    async def _get_user_tenant(self, user_id: int) -> Optional[int]:
        """جلب tenant_id الحقيقي للمستخدم من قاعدة البيانات."""
        user = await self.user_repo.get_user(user_id)  # type: ignore
        if not user:
            return None
        return user.tenant_id  # type: ignore

    async def _get_user_email(self, user_id: int) -> str:
        """جلب البريد الإلكتروني للمستخدم."""
        user = await self.user_repo.get_user(user_id)  # type: ignore
        if not user:
            return f"user_{user_id}@eppne.com"
        return user.email  # type: ignore

    # ============================================================
    # 1. الإشعارات (Notifications)
    # ============================================================

    async def send_notification(
        self,
        user_id: int,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        priority: str = NotificationPriority.NORMAL,
        channel: str = NotificationChannel.IN_APP,
        idempotency_key: Optional[str] = None
    ) -> Notification:
        """إرسال إشعار – تخزينه أولاً ثم جدولة الإرسال عبر Celery."""
        # التحقق من Idempotency
        if idempotency_key:
            existing = await self.repo.get_notification_by_idempotency(idempotency_key)
            if existing:
                return existing

        # جلب tenant_id الفعلي للمستخدم
        tenant_id = await self._get_user_tenant(user_id)
        if not tenant_id:
            raise PermissionDeniedError("لا يمكن تحديد المستأجر لهذا المستخدم")

        # 🔥 معاملة ذرية لإنشاء الإشعار
        async with self.db.begin_nested():
            notification = await self.repo.create_notification(
                tenant_id=tenant_id,
                user_id=user_id,
                title=title,
                body=body,
                data=data or {},
                priority=priority,
                channel=channel,
                is_sent=False,
                idempotency_key=idempotency_key
            )

        # جدولة الإرسال الفعلي (غير متزامن عبر Celery)
        send_notification_task.delay(  # type: ignore
            notification_id=notification.id,
            user_id=user_id,
            title=title,
            body=body,
            data=data or {},
            channel=channel,
            priority=priority
        )

        return notification

    async def get_user_notifications(
        self,
        user_id: int,
        is_read: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Notification]:
        return list(await self.repo.list_user_notifications(user_id, is_read, skip=skip, limit=limit))

    async def mark_as_read(self, user_id: int, notification_id: int) -> Notification:
        return await self.repo.mark_notification_read(notification_id, user_id)

    # ============================================================
    # 2. أجهزة الإشعارات (Push Devices)
    # ============================================================

    async def register_device(self, user_id: int, device_token: str, platform: str) -> NotificationDevice:
        """تسجيل جهاز جديد للإشعارات."""
        return await self.repo.register_device(
            user_id=user_id,
            device_token=device_token,
            platform=platform,
            is_active=True
        )

    # ============================================================
    # 3. البريد الداخلي (Internal Mail)
    # ============================================================

    async def send_mail(
        self,
        sender_id: int,
        recipient_id: int,
        subject: str,
        body_text: Optional[str] = None,
        body_html: Optional[str] = None,
        is_certified: bool = False,
        attachments: Optional[List[Dict]] = None,
        idempotency_key: Optional[str] = None
    ) -> MailMessage:
        """إرسال بريد داخلي – مع التحقق من Multi-Tenancy."""
        # التحقق من Idempotency
        if idempotency_key:
            existing = await self.repo.get_message_by_idempotency(idempotency_key)
            if existing:
                return existing

        # التحقق من أن المرسل والمستلم في نفس المستأجر
        sender_tenant = await self._get_user_tenant(sender_id)
        recipient_tenant = await self._get_user_tenant(recipient_id)
        if sender_tenant != recipient_tenant:
            raise PermissionDeniedError("المرسل والمستلم ليسا في نفس المستأجر")

        # 🔥 معاملة ذرية لإنشاء البريد
        async with self.db.begin_nested():
            # إنشاء thread
            thread = await self.repo.create_thread(subject=subject, tenant_id=cast(int, sender_tenant))

            # إنشاء الرسالة
            certified_tx = f"CERT-{uuid.uuid4().hex[:12].upper()}" if is_certified else None
            message = await self.repo.create_message(
                thread_id=thread.id,
                sender_id=sender_id,
                recipient_id=recipient_id,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                is_certified=is_certified,
                certified_tx_hash=certified_tx,
                idempotency_key=idempotency_key
            )

            # إضافة إلى صندوقي المستلم والمرسل
            await self.repo.add_to_mailbox(cast(int, message.id), recipient_id, MailFolder.INBOX)
            await self.repo.add_to_mailbox(cast(int, message.id), sender_id, MailFolder.SENT)

            # إضافة المرفقات إن وجدت
            if attachments:
                for att in attachments:
                    await self.repo.add_attachment(
                        message_id=message.id,
                        file_name=att.get("file_name", ""),
                        file_url=att.get("file_url", ""),
                        file_size_bytes=att.get("file_size_bytes", 0),
                        mime_type=att.get("mime_type"),
                        ipfs_hash=att.get("ipfs_hash")
                    )

        # إرسال إشعار للمستلم (جدولة عبر Celery) – خارج المعاملة
        send_notification_task.delay(  # type: ignore
            user_id=recipient_id,
            title=f"رسالة جديدة: {subject}",
            body=body_text[:200] if body_text else "لديك رسالة جديدة",
            data={"message_id": message.id, "sender_id": sender_id},
            channel="IN_APP"
        )

        return message

    async def reply_to_mail(
        self,
        sender_id: int,
        original_message_id: int,
        body_text: str,
        body_html: Optional[str] = None
    ) -> MailMessage:
        """الرد على رسالة موجودة (يتم وضعها في نفس الـ thread)"""
        original = await self.repo.get_message(original_message_id)
        if not original:
            raise NotFoundError("الرسالة الأصلية غير موجودة")

        return await self.send_mail(
            sender_id=sender_id,
            recipient_id=original.sender_id,  # type: ignore
            subject=f"رد: {original.subject}",  # type: ignore
            body_text=body_text,
            body_html=body_html,
            is_certified=False
        )

    async def get_inbox(self, user_id: int, skip: int = 0, limit: int = 50) -> List[MailboxItem]:
        return list(await self.repo.get_mailbox_items(user_id, folder=MailFolder.INBOX, skip=skip, limit=limit))

    async def get_sent(self, user_id: int, skip: int = 0, limit: int = 50) -> List[MailboxItem]:
        return list(await self.repo.get_mailbox_items(user_id, folder=MailFolder.SENT, skip=skip, limit=limit))

    async def move_to_trash(self, user_id: int, item_id: int) -> MailboxItem:
        return await self.repo.move_to_folder(item_id, MailFolder.TRASH, user_id)

    async def restore_from_trash(self, user_id: int, item_id: int) -> MailboxItem:
        return await self.repo.move_to_folder(item_id, MailFolder.INBOX, user_id)

    async def archive_message(self, user_id: int, item_id: int) -> MailboxItem:
        return await self.repo.move_to_folder(item_id, MailFolder.ARCHIVE, user_id)

    async def star_message(self, user_id: int, item_id: int) -> MailboxItem:
        return await self.repo.toggle_star(item_id, user_id)

    async def mark_conversation_read(self, user_id: int, item_id: int) -> MailboxItem:
        return await self.repo.mark_read(item_id, user_id, is_read=True)

    async def delete_permanently(self, user_id: int, item_id: int) -> None:
        await self.repo.delete_message_permanently(item_id, user_id)

    # ============================================================
    # 4. قوالب الاتصال (Templates)
    # ============================================================

    async def create_template(
        self,
        tenant_id: int,
        name: str,
        trigger_event: str,
        subject_template: str,
        body_template: str,
        channel: str = "EMAIL"
    ) -> CommunicationTemplate:
        """إنشاء قالب اتصال جديد."""
        return await self.repo.create_template(
            tenant_id=tenant_id,
            name=name,
            trigger_event=trigger_event,
            subject_template=subject_template,
            body_template=body_template,
            channel=channel,
            is_active=True
        )

    async def list_templates(self, tenant_id: int) -> List[CommunicationTemplate]:
        """جلب قائمة القوالب للمستأجر."""
        return list(await self.repo.list_templates(tenant_id))
    async def render_template(self, tenant_id: int, trigger_event: str, context: Dict[str, Any]) -> dict:
        """استدعاء قالب بناءً على الحدث، وملؤه بالبيانات (context)"""
        template = await self.repo.get_template_by_event(tenant_id, trigger_event)
        if not template:
            return {
                "subject": "إشعار من النظام",
                "body": f"حدث {trigger_event} - {json.dumps(context)}"
            }
        subject = template.subject_template  # type: ignore
        body = template.body_template  # type: ignore
        for key, value in context.items():
            subject = subject.replace(f"{{{{{key}}}}}", str(value))
            body = body.replace(f"{{{{{key}}}}}", str(value))
        return {"subject": subject, "body": body}