# app/domains/privacy/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text  
from datetime import datetime
import uuid
import logging
from typing import Optional, Dict, Any

from app.domains.privacy.repository import PrivacyRepository
from app.domains.privacy.models import (
    PrivacySetting, DataConsentLog, DataErasureRequest, 
    TombstoneRecord, ErasureStatus, ConsentType
)
from app.core.errors import PermissionDeniedError, NotFoundError, ValidationError
from app.core.task_queue import task_queue  
from app.core.security import is_privacy_officer, encrypt_ip  

# 🔥 فصل الـ Logger ليكون محلياً ومستقلاً
logger = logging.getLogger("eppne.privacy.service")

class PrivacyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PrivacyRepository(db)

    # ==========================================
    # 1. إعدادات الخصوصية (Privacy Settings)
    # ==========================================
    async def update_privacy_settings(self, user_id: int, data: Dict[str, Any]) -> PrivacySetting:
        """تحديث إعدادات الخصوصية للمستخدم"""
        if "profile_visibility" in data:
            valid_values = ["PUBLIC", "FRIENDS_ONLY", "PRIVATE"]
            if data["profile_visibility"] not in valid_values:
                raise ValidationError(f"profile_visibility must be one of {valid_values}")

        return await self.repo.update_privacy_settings(user_id, data)

    # ==========================================
    # 2. تسجيل الموافقات (Consent Logs)
    # ==========================================
    async def record_consent(
        self, 
        user_id: int, 
        consent_type: str, 
        granted: bool, 
        ip: Optional[str], 
        user_agent: Optional[str]
    ) -> DataConsentLog:
        """تسجيل موافقة المستخدم وتشفير الـ IP"""
        if consent_type not in [c.value for c in ConsentType]:
            raise ValidationError(f"Invalid consent_type: {consent_type}")

        encrypted_ip = encrypt_ip(ip) if ip else None

        return await self.repo.create_consent_log(
            user_id=user_id,
            consent_type=consent_type,
            is_granted=granted,
            ip_address=encrypted_ip,
            user_agent=user_agent,
            consent_tx_hash=f"CONSENT-{uuid.uuid4().hex[:12].upper()}"
        )

    # ==========================================
    # 3. طلبات محو البيانات (Data Erasure)
    # ==========================================
    async def request_data_erasure(
        self, 
        user_id: int, 
        target_module: str, 
        reason: Optional[str] = None
    ) -> DataErasureRequest:
        """إنشاء طلب محو بيانات جديد"""
        existing = await self.repo.get_pending_erasure_request(user_id, target_module)
        if existing:
            raise ValidationError("You already have a pending erasure request for this module.")

        return await self.repo.create_erasure_request(
            user_id=user_id,
            target_module=target_module,
            reason=reason,
            status=ErasureStatus.PENDING
        )

    # ==========================================
    # 4. معالجة طلبات المحو (Admin Only)
    # ==========================================
    async def process_erasure_request(
        self, 
        request_id: int, 
        admin_id: int, 
        approve: bool, 
        notes: Optional[str] = None
    ) -> DataErasureRequest:
        """معالجة طلب محو البيانات بمعايير عسكرية للمعاملات"""
        if not await is_privacy_officer(admin_id):
            raise PermissionDeniedError("Only Privacy Officers can process erasure requests.")

        request_obj = await self.repo.get_erasure_request(request_id)
        if not request_obj:
            raise NotFoundError("Erasure request not found")

        current_status = getattr(request_obj, 'status', None)
        if current_status != ErasureStatus.PENDING:
            raise ValidationError(f"Request is already {current_status}")

        req_user_id = int(getattr(request_obj, 'user_id', 0))
        req_module = str(getattr(request_obj, 'target_module', ''))

        async with self.db.begin_nested():
            if approve:
                await self._erase_module_data(req_user_id, req_module)
                status = ErasureStatus.COMPLETED
                receipt_tx = f"ERASE-{uuid.uuid4().hex[:16].upper()}"
            else:
                status = ErasureStatus.REJECTED
                receipt_tx = None

            updated_request = await self.repo.update_erasure_request(
                request_id,
                status=status,
                processed_at=datetime.utcnow(),
                admin_notes=notes,
                erasure_receipt_tx=receipt_tx
            )

            if approve:
                task_queue.enqueue(
                    "privacy.tasks.unpin_from_ipfs",
                    args=[req_user_id, req_module],
                    queue="privacy"
                )
                task_queue.enqueue(
                    "privacy.tasks.burn_tokens",
                    args=[req_user_id, receipt_tx],
                    queue="blockchain"
                )

        return updated_request

    # ==========================================
    # 5. مسح البيانات الفعلي (Core Logic)
    # ==========================================
    async def _erase_module_data(self, user_id: int, module: str) -> None:
        """توجيه الحذف للقطاعات المختارة"""
        try:
            if module in ["identity", "all"]:
                await self._erase_identity_data(user_id)
            if module in ["academy", "all"]:
                await self._erase_academy_data(user_id)
            if module in ["finance", "all"]:
                await self._erase_finance_data(user_id)
            if module in ["commerce", "all"]:
                await self._erase_commerce_data(user_id)
            if module in ["health", "all"]:
                await self._erase_health_data(user_id)
            if module in ["iot", "all"]:
                await self._erase_iot_data(user_id)
            if module in ["realestate", "all"]:
                await self._erase_realestate_data(user_id)
        except Exception as e:
            logger.error(f"Failed to erase data for user {user_id} in module {module}: {str(e)}")
            raise

    # ==========================================
    # 6. المعالج الذري (Atomic Erasure Engine)
    # ==========================================
    async def _delete_and_tombstone(self, table_name: str, user_id: int, user_column: str = "user_id") -> None:
        """تنفيذ الحذف الذري وإنشاء الشواهد"""
        query = text(f"DELETE FROM {table_name} WHERE {user_column} = :uid RETURNING id")
        result = await self.db.execute(query, {"uid": user_id})
        deleted_ids = result.scalars().all()

        for rec_id in deleted_ids:
            tombstone = TombstoneRecord(
                table_name=table_name,
                record_id=rec_id,  
                deleted_by_id=user_id,
                original_tx_hash=f"TOMB-{uuid.uuid4().hex[:16].upper()}"
            )
            self.db.add(tombstone)

    # ==========================================
    # 7. دوال الحذف المخصصة بالقطاعات
    # ==========================================
    async def _erase_identity_data(self, user_id: int) -> None:
        await self._delete_and_tombstone("privacy_settings", user_id)
        await self._delete_and_tombstone("data_consent_logs", user_id)
        await self._delete_and_tombstone("data_erasure_requests", user_id)

    async def _erase_academy_data(self, user_id: int) -> None:
        await self._delete_and_tombstone("academy_enrollments", user_id)
        await self._delete_and_tombstone("task_submissions", user_id)
        await self._delete_and_tombstone("live_attendance", user_id)
        await self._delete_and_tombstone("student_digital_twins", user_id)
        await self._delete_and_tombstone("spiritual_certificates", user_id)
        await self._delete_and_tombstone("sovereign_badges", user_id)

    async def _erase_finance_data(self, user_id: int) -> None:
        await self._delete_and_tombstone("transactions", user_id)
        await self._delete_and_tombstone("payment_installments", user_id)
        await self._delete_and_tombstone("wallets", user_id)

    async def _erase_commerce_data(self, user_id: int) -> None:
        await self._delete_and_tombstone("orders", user_id)
        await self._delete_and_tombstone("carts", user_id)

    async def _erase_health_data(self, user_id: int) -> None:
        await self._delete_and_tombstone("health_records", user_id)
        await self._delete_and_tombstone("biometrics", user_id)

    async def _erase_iot_data(self, user_id: int) -> None:
        await self._delete_and_tombstone("sensor_data", user_id)
        await self._delete_and_tombstone("devices", user_id)

    async def _erase_realestate_data(self, user_id: int) -> None:
        await self._delete_and_tombstone("properties", user_id, user_column="owner_id")
        await self._delete_and_tombstone("leases", user_id, user_column="tenant_id")

    # ==========================================
    # 8. دوال المهام الخلفية (Background Tasks)
    # ==========================================
    async def _async_unpin_ipfs(self, user_id: int, module: str) -> None:
        try:
            logger.info(f"Unpinning IPFS data for user {user_id} in module {module}")
            await self.db.execute(
                text("UPDATE tombstone_records SET ipfs_unpin_status = TRUE "
                     "WHERE table_name LIKE :module AND deleted_by_id = :user_id"),
                {"module": f"%{module}%", "user_id": user_id}
            )
            await self.db.commit()
        except Exception as e:
            logger.error(f"Failed to unpin IPFS for user {user_id}: {str(e)}")
            await self.db.rollback()
            raise

    async def _async_burn_tokens(self, user_id: int, receipt_tx: str) -> None:
        try:
            logger.info(f"Burning tokens for user {user_id} with receipt {receipt_tx}")
            # 🔥 الدالة الجديدة المخصصة للـ Hash
            await self.repo.update_tombstone_by_tx(receipt_tx, 'blockchain_burn_status', ErasureStatus.COMPLETED)
        except Exception as e:
            logger.error(f"Failed to burn tokens for user {user_id}: {str(e)}")
            await self.repo.update_tombstone_by_tx(receipt_tx, 'blockchain_burn_status', ErasureStatus.REJECTED)
            raise