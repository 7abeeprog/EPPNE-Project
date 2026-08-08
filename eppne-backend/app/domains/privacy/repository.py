# app/domains/privacy/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, text
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.domains.privacy.models import (
    PrivacySetting, DataConsentLog, DataErasureRequest,
    TombstoneRecord, ErasureStatus
)
from app.core.errors import NotFoundError
from app.core.pagination import PaginatedResponse

class PrivacyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ==========================================
    # 1. إعدادات الخصوصية (Privacy Settings)
    # ==========================================
    async def get_privacy_settings(self, user_id: int, tenant_id: int) -> PrivacySetting:
        """جلب إعدادات الخصوصية للمستخدم، وإنشاء إعدادات افتراضية إذا لم تكن موجودة."""
        query: Any = select(PrivacySetting).where(
            PrivacySetting.user_id == user_id, PrivacySetting.tenant_id == tenant_id
        )
        result = await self.db.execute(query)
        settings = result.scalar_one_or_none()

        if not settings:
            settings = PrivacySetting(user_id=user_id, tenant_id=tenant_id)
            self.db.add(settings)
            await self.db.commit()
            await self.db.refresh(settings)

        return settings

    async def update_privacy_settings(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> PrivacySetting:
        """تحديث إعدادات الخصوصية للمستخدم."""
        settings = await self.get_privacy_settings(user_id, tenant_id)

        for key, value in data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    # ==========================================
    # 2. سجلات الموافقات (Consent Logs)
    # ==========================================
    async def create_consent_log(
        self,
        user_id: int,
        tenant_id: int,
        consent_type: str,
        is_granted: bool,
        ip_address: Optional[str],
        user_agent: Optional[str],
        consent_tx_hash: str
    ) -> DataConsentLog:
        """إنشاء سجل موافقة جديد."""
        log = DataConsentLog(
            user_id=user_id,
            tenant_id=tenant_id,
            consent_type=consent_type,
            is_granted=is_granted,
            ip_address=ip_address,
            user_agent=user_agent,
            consent_tx_hash=consent_tx_hash
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    # ==========================================
    # 3. طلبات محو البيانات (Erasure Requests)
    # ==========================================
    async def create_erasure_request(
        self,
        user_id: int,
        tenant_id: int,
        target_module: str,
        reason: Optional[str],
        status: ErasureStatus
    ) -> DataErasureRequest:
        """إنشاء طلب محو بيانات جديد."""
        request_obj = DataErasureRequest(
            user_id=user_id,
            tenant_id=tenant_id,
            target_module=target_module,
            reason=reason,
            status=status
        )
        self.db.add(request_obj)
        await self.db.commit()
        await self.db.refresh(request_obj)
        return request_obj

    async def get_erasure_request(self, request_id: int, tenant_id: int) -> Optional[DataErasureRequest]:
        """جلب طلب محو بيانات بواسطة المعرف."""
        query: Any = select(DataErasureRequest).where(
            DataErasureRequest.status == ErasureStatus.PENDING,
            DataErasureRequest.tenant_id == tenant_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_pending_erasure_request(self, user_id: int, tenant_id: int, target_module: str) -> Optional[DataErasureRequest]:
        """جلب طلب محو بيانات معلق للمستخدم والقطاع المحدد."""
        query: Any = (
            select(DataErasureRequest)
            .where(
                DataErasureRequest.user_id == user_id,
                DataErasureRequest.tenant_id == tenant_id,
                DataErasureRequest.target_module == target_module,
                DataErasureRequest.status == ErasureStatus.PENDING
            )
            .order_by(DataErasureRequest.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_erasure_requests(
        self,
        user_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 20,
        status: Optional[ErasureStatus] = None
    ) -> PaginatedResponse[Any]:
        """
        جلب طلبات محو البيانات للمستخدم مع Pagination.
        """
        query: Any = select(DataErasureRequest).where(
            DataErasureRequest.user_id == user_id, DataErasureRequest.tenant_id == tenant_id
        )
        if status:
            query = query.where(DataErasureRequest.status == status)
        query = query.order_by(DataErasureRequest.created_at.asc()).offset(skip).limit(limit)


        total = await self._estimate_row_count(DataErasureRequest.__tablename__, user_id, tenant_id, status)

        paginated_query = query.offset(skip).limit(limit)
        result = await self.db.execute(paginated_query)
        items = result.scalars().all()

        return PaginatedResponse(
            data=items,
            total=total,
            skip=skip,
            limit=limit
        )

    async def get_pending_erasure_requests_for_admin(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> PaginatedResponse[Any]:
        """
        جلب طلبات محو البيانات المعلقة (للمشرفين).
        """
        query: Any = select(DataErasureRequest).where(
            DataErasureRequest.status == ErasureStatus.PENDING,
            DataErasureRequest.tenant_id == tenant_id
        ).order_by(DataErasureRequest.created_at.asc())

        total = await self._estimate_pending_count(tenant_id)

        paginated_query = query.offset(skip).limit(limit)
        result = await self.db.execute(paginated_query)
        items = result.scalars().all()

        return PaginatedResponse(
            data=items,
            total=total,
            skip=skip,
            limit=limit
        )

    async def update_erasure_request(self, request_id: int, tenant_id: int, **kwargs) -> DataErasureRequest:
        """تحديث طلب محو البيانات بالكامل."""
        request_obj = await self.get_erasure_request(request_id, tenant_id)
        if not request_obj:
            raise NotFoundError("Erasure request not found")

        for key, value in kwargs.items():
            if hasattr(request_obj, key):
                setattr(request_obj, key, value)

        await self.db.commit()
        await self.db.refresh(request_obj)
        return request_obj

    # ==========================================
    # 4. سجلات الشواهد (Tombstone Records)
    # ==========================================
    async def create_tombstone(
        self,
        tenant_id: int,
        table_name: str,
        record_id: int,
        deleted_by_id: int,
        erasure_request_id: Optional[int] = None,
        original_tx_hash: Optional[str] = None
    ) -> TombstoneRecord:
        """إنشاء سجل شاهدة (Tombstone) جديد."""
        tombstone = TombstoneRecord(
            tenant_id=tenant_id,
            table_name=table_name,
            record_id=record_id,
            deleted_by_id=deleted_by_id,
            erasure_request_id=erasure_request_id,
            original_tx_hash=original_tx_hash
        )
        self.db.add(tombstone)
        await self.db.commit()
        await self.db.refresh(tombstone)
        return tombstone

    async def get_tombstones_by_user(
        self,
        user_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> PaginatedResponse[Any]:
        """جلب سجلات الشواهد للمستخدم مع Pagination."""
        query: Any = select(TombstoneRecord).where(
            TombstoneRecord.deleted_by_id == user_id, TombstoneRecord.tenant_id == tenant_id
        )
        query = query.order_by(TombstoneRecord.created_at.desc())

        total = await self._estimate_row_count(TombstoneRecord.__tablename__, user_id, tenant_id)

        paginated_query = query.offset(skip).limit(limit)
        result = await self.db.execute(paginated_query)
        items = result.scalars().all()

        return PaginatedResponse(
            data=items,
            total=total,
            skip=skip,
            limit=limit
        )

    # 🔥 الدالة الوحيدة والمعتمدة لتحديث حالة الـ Tombstone
    async def update_tombstone_by_tx(self, tx_hash: str, field_name: str, status_value: Any, tenant_id: int) -> bool:
        """
        تحديث حالة سجل الحذف بأمان (للـ Blockchain أو IPFS) باستخدام الـ Hash.
        """
        try:
            query: Any = (
                update(TombstoneRecord)
                .where(TombstoneRecord.original_tx_hash == tx_hash, TombstoneRecord.tenant_id == tenant_id)
                .values({field_name: status_value})
            )
            await self.db.execute(query)
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()  # 🔥 حماية صارمة لمنع قفل قاعدة البيانات
            raise e

    # ==========================================
    # 5. دوال مساعدة لتقدير عدد الصفوف (Row Estimation)
    # ==========================================
    async def _estimate_row_count(self, table_name: str, user_id: int, tenant_id: int, status: Optional[ErasureStatus] = None) -> int:
        try:
            query = text("SELECT reltuples::bigint FROM pg_class WHERE relname = :table_name")
            result = await self.db.execute(query, {"table_name": table_name})
            estimated_total = result.scalar() or 0

            if estimated_total < 10000:
                base_query = select(DataErasureRequest).where(
                    DataErasureRequest.user_id == user_id, DataErasureRequest.tenant_id == tenant_id
                )
                count_query: Any = select(func.count()).select_from(
                    base_query.where(DataErasureRequest.status == status) if status else base_query
                )
                count_result = await self.db.execute(count_query)
                return count_result.scalar() or 0

            return estimated_total
        except Exception:
            try:
                base_query = select(DataErasureRequest).where(
                    DataErasureRequest.user_id == user_id, DataErasureRequest.tenant_id == tenant_id
                )
                count_query: Any = select(func.count()).select_from(
                    base_query.where(DataErasureRequest.status == status) if status else base_query
                )
                count_result = await self.db.execute(count_query)
                return count_result.scalar() or 0
            except Exception:
                return 0

    async def _estimate_pending_count(self, tenant_id: int) -> int:
        try:
            query = text("SELECT reltuples::bigint FROM pg_class WHERE relname = 'data_erasure_requests'")
            result = await self.db.execute(query)
            total = result.scalar() or 0

            if total < 10000:
                count_query: Any = select(func.count()).where(
                    DataErasureRequest.status == ErasureStatus.PENDING,
                    DataErasureRequest.tenant_id == tenant_id
                )
                count_result = await self.db.execute(count_query)
                return count_result.scalar() or 0

            return int(total * 0.05)
        except Exception:
            try:
                count_query: Any = select(func.count()).where(
                    DataErasureRequest.status == ErasureStatus.PENDING,
                    DataErasureRequest.tenant_id == tenant_id
                )
                count_result = await self.db.execute(count_query)
                return count_result.scalar() or 0
            except Exception:
                return 0

    # ==========================================
    # 6. دوال مستقبلية مع selectinload (لتجنب N+1)
    # ==========================================
    async def get_erasure_requests_with_tombstones(
        self,
        user_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> PaginatedResponse[Any]:
        query: Any = select(DataErasureRequest)\
            .where(DataErasureRequest.user_id == user_id, DataErasureRequest.tenant_id == tenant_id)\
            .options(selectinload(DataErasureRequest.tombstones))\
            .order_by(DataErasureRequest.created_at.desc())

        total = await self._estimate_row_count(DataErasureRequest.__tablename__, user_id, tenant_id)

        paginated_query = query.offset(skip).limit(limit)
        result = await self.db.execute(paginated_query)
        items = result.scalars().all()

        return PaginatedResponse(
            data=items,
            total=total,
            skip=skip,
            limit=limit
        )
