"""
خدمات قطاع الاتصالات – النسخة المحصنة والمُعدة للـ Async
"""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid
import json

from app.domains.communications.repository import CommunicationsRepository
from app.domains.communications.models import MailFolder, NotificationPriority, NotificationChannel, Notification, MailMessage, MailboxItem
from app.core.errors import NotFoundError, PermissionDeniedError, IdempotencyError
from app.domains.identity.repository import UserRepository  # ربط حقيقي بالهوية
from app.core.celery_app import send_notification_task, send_email_task  # مهام Celery

class CommunicationsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CommunicationsRepository(db)
        self.user_repo = UserRepository(db)  # استدعاء مستودع الهوية

    # ==============================
    # 1. الإشعارات (Notifications)
    # ==============================

    async def send_notification(
        self,
        user_id: int,
        title: str,
        body: str,
        data: Dict[str, Any] = None,
        priority: str = NotificationPriority.NORMAL,
        channel: str = NotificationChannel.IN_APP,
        idempotency_key: Optional[str] = None
    ) -> Notification:
        """
        إرسال إشعار – تخزينه أولاً ثم جدولة الإرسال عبر Celery.
        """
        # التحقق من Idempotency (يتم في الـ router أيضاً، لكن نؤكد هنا)
        if idempotency_key:
            existing = await self.repo.get_notification_by_idempotency(idempotency_key)
            if existing:
                return existing

        # جلب tenant_id الفعلي للمستخدم
        tenant_id = await self._get_user_tenant(user_id)
        if not tenant_id:
            raise PermissionDeniedError("لا يمكن تحديد المستأجر لهذا المستخدم")

        # تخزين الإشعار
        notification = await self.repo.create_notification(
            tenant_id=tenant_id,
            user_id=user_id,
            title=title,
            body=body,
            data=data or {},
            priority=priority,
            channel=channel,
            is_sent=False,
            idempotency_key=idempotency_key  # نضيف حقل idempotency_key في النموذج
        )

        # جدولة الإرسال الفعلي (غير متزامن عبر Celery)
        send_notification_task.delay(
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
        is_read: bool = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Notification]:
        return await self.repo.list_user_notifications(user_id, is_read, skip=skip, limit=limit)

    async def mark_as_read(self, user_id: int, notification_id: int) -> Notification:
        return await self.repo.mark_notification_read(notification_id, user_id)

    # ==============================
    # 2. البريد الداخلي (Internal Mail)
    # ==============================

    async def send_mail(
        self,
        sender_id: int,
        recipient_id: int,
        subject: str,
        body_text: str = None,
        body_html: str = None,
        is_certified: bool = False,
        attachments: List[Dict] = None,
        idempotency_key: Optional[str] = None
    ) -> MailMessage:
        """
        إرسال بريد داخلي – مع التحقق من Multi-Tenancy.
        """
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

        # إنشاء thread (يمكن لاحقاً ربط الردود)
        thread = await self.repo.create_thread(subject=subject, tenant_id=sender_tenant)

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
            idempotency_key=idempotency_key  # إضافة حقل جديد
        )

        # إضافة إلى صندوقي المستلم والمرسل
        await self.repo.add_to_mailbox(message.id, recipient_id, MailFolder.INBOX)
        await self.repo.add_to_mailbox(message.id, sender_id, MailFolder.SENT)

        # إضافة المرفقات إن وجدت
        if attachments:
            for att in attachments:
                await self.repo.add_attachment(
                    message_id=message.id,
                    file_name=att["file_name"],
                    file_url=att["file_url"],
                    file_size_bytes=att.get("file_size_bytes", 0),
                    mime_type=att.get("mime_type"),
                    ipfs_hash=att.get("ipfs_hash")
                )

        # إرسال إشعار للمستلم (جدولة عبر Celery)
        send_notification_task.delay(
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
        body_html: str = None
    ) -> MailMessage:
        """
        الرد على رسالة موجودة (يتم وضعها في نفس الـ thread)
        """
        original = await self.repo.get_message(original_message_id)
        if not original:
            raise NotFoundError("الرسالة الأصلية غير موجودة")

        # الرد يكون من sender إلى recipient الأصلي
        return await self.send_mail(
            sender_id=sender_id,
            recipient_id=original.sender_id,
            subject=f"رد: {original.subject}",
            body_text=body_text,
            body_html=body_html,
            is_certified=False
        )

    async def get_inbox(self, user_id: int, skip: int = 0, limit: int = 50) -> List[MailboxItem]:
        return await self.repo.get_mailbox_items(user_id, folder=MailFolder.INBOX, skip=skip, limit=limit)

    async def get_sent(self, user_id: int, skip: int = 0, limit: int = 50) -> List[MailboxItem]:
        return await self.repo.get_mailbox_items(user_id, folder=MailFolder.SENT, skip=skip, limit=limit)

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

    # ==============================
    # 3. قوالب الاتصال (Templates)
    # ==============================

    async def render_template(self, tenant_id: int, trigger_event: str, context: Dict[str, Any]) -> dict:
        """
        استدعاء قالب بناءً على الحدث، وملؤه بالبيانات (context)
        """
        template = await self.repo.get_template_by_event(tenant_id, trigger_event)
        if not template:
            # قالب افتراضي
            return {
                "subject": "إشعار من النظام",
                "body": f"حدث {trigger_event} - {json.dumps(context)}"
            }
        # استبدال المتغيرات في القالب (مثال بسيط، يمكن استخدام Jinja2)
        subject = template.subject_template
        body = template.body_template
        for key, value in context.items():
            subject = subject.replace(f"{{{{{key}}}}}", str(value))
            body = body.replace(f"{{{{{key}}}}}", str(value))
        return {"subject": subject, "body": body}

    # ==============================
    # 4. دوال مساعدة (Helpers) – الإصلاح الجذري
    # ==============================

    async def _get_user_tenant(self, user_id: int) -> Optional[int]:
        """
        جلب tenant_id الحقيقي للمستخدم من قاعدة البيانات.
        """
        user = await self.user_repo.get_user(user_id)
        if not user:
            return None
        # نفترض أن المستخدم له عمود `tenant_id`
        return user.tenant_id

    async def _get_user_email(self, user_id: int) -> str:
        """جلب البريد الإلكتروني للمستخدم (لإرسال الإيميلات الخارجية)"""
        user = await self.user_repo.get_user(user_id)
        if not user:
            return f"user_{user_id}@eppne.com"
        return user.email