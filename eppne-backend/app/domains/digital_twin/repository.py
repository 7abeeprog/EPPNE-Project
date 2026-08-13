# app/domains/digital_twin/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, delete
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

from app.domains.digital_twin.models import *
from app.core.errors import NotFoundError


class DigitalTwinRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # 1. التوأم الرقمي (Digital Twin) مع العزل السيادي
    # ============================================================

    async def get_twin_config(self, user_id: int, tenant_id: int) -> Optional[DigitalTwinConfig]:
        """جلب إعدادات التوأم الرقمي مع التأكد من tenant_id."""
        result = await self.db.execute(
            select(DigitalTwinConfig).where(
                DigitalTwinConfig.user_id == user_id,
                DigitalTwinConfig.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def create_twin_config(self, **kwargs) -> DigitalTwinConfig:
        """إنشاء إعدادات توأم رقمي جديدة (يتضمن tenant_id)."""
        twin = DigitalTwinConfig(**kwargs)
        self.db.add(twin)
        await self.db.flush()
        await self.db.refresh(twin)
        return twin

    async def update_twin_config(self, user_id: int, tenant_id: int, **kwargs) -> DigitalTwinConfig:
        """تحديث إعدادات التوأم الرقمي مع التأكد من tenant_id."""
        twin = await self.get_twin_config(user_id, tenant_id)
        if not twin:
            raise NotFoundError("التوأم الرقمي غير موجود")
        for key, value in kwargs.items():
            setattr(twin, key, value)
        await self.db.commit()
        await self.db.refresh(twin)
        return twin

    async def create_twin_permission(self, **kwargs) -> TwinPermission:
        """إنشاء صلاحية جديدة للتوأم الرقمي."""
        perm = TwinPermission(**kwargs)
        self.db.add(perm)
        await self.db.commit()
        await self.db.refresh(perm)
        return perm

    async def create_interaction_log(self, **kwargs) -> TwinInteractionLog:
        """إنشاء سجل تفاعل جديد (يتضمن tenant_id و idempotency_key)."""
        log = TwinInteractionLog(**kwargs)
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def sum_monthly_spending(self, twin_config_id: int, tenant_id: int) -> Decimal:
        """جمع رسوم التفاعل للشهر الحالي مع التأكد من tenant_id."""
        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        result = await self.db.execute(
            select(func.sum(TwinInteractionLog.fee_paid_mrusdt))
            .where(
                TwinInteractionLog.twin_config_id == twin_config_id,
                TwinInteractionLog.tenant_id == tenant_id,
                TwinInteractionLog.created_at >= start_of_month
            )
        )
        return result.scalar() or Decimal(0)

    # ============================================================
    # 2. خزائن الزمن (Time Capsule) مع العزل السيادي
    # ============================================================

    async def create_time_capsule(self, **kwargs) -> TimeCapsule:
        """إنشاء خزنة زمنية جديدة (يتضمن tenant_id)."""
        capsule = TimeCapsule(**kwargs)
        self.db.add(capsule)
        await self.db.flush()
        await self.db.refresh(capsule)
        return capsule

    async def get_time_capsule(self, user_id: int, tenant_id: int) -> Optional[TimeCapsule]:
        """جلب خزنة زمنية مع التأكد من tenant_id."""
        result = await self.db.execute(
            select(TimeCapsule).where(
                TimeCapsule.user_id == user_id,
                TimeCapsule.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def update_capsule_heartbeat(self, user_id: int, tenant_id: int) -> Optional[TimeCapsule]:
        """تحديث نبض الحياة للخزنة الزمنية مع التأكد من tenant_id."""
        # 🔥 استخدام update بدلاً من تعيين القيمة مباشرة
        await self.db.execute(
            update(TimeCapsule)
            .where(
                TimeCapsule.user_id == user_id,
                TimeCapsule.tenant_id == tenant_id
            )
            .values(last_heartbeat_at=func.now())
        )
        await self.db.commit()
        return await self.get_time_capsule(user_id, tenant_id)

    async def create_beneficiary(self, **kwargs) -> LegacyBeneficiary:
        """إنشاء مستفيد جديد (يتضمن tenant_id)."""
        beneficiary = LegacyBeneficiary(**kwargs)
        self.db.add(beneficiary)
        await self.db.flush()
        await self.db.refresh(beneficiary)
        return beneficiary

    async def list_beneficiaries(self, capsule_id: int, tenant_id: int) -> List[LegacyBeneficiary]:
        """قائمة المستفيدين مع التأكد من tenant_id."""
        result = await self.db.execute(
            select(LegacyBeneficiary).where(
                LegacyBeneficiary.capsule_id == capsule_id,
                LegacyBeneficiary.tenant_id == tenant_id
            )
        )
        # 🔥 تحويل النتيجة إلى list
        return list(result.scalars().all())

    async def create_digital_will(self, **kwargs) -> DigitalWill:
        """إنشاء وصية رقمية جديدة (يتضمن tenant_id)."""
        will = DigitalWill(**kwargs)
        self.db.add(will)
        await self.db.commit()
        await self.db.refresh(will)
        return will

    async def get_digital_will(self, user_id: int, tenant_id: int) -> Optional[DigitalWill]:
        """جلب الوصية الرقمية مع التأكد من tenant_id."""
        result = await self.db.execute(
            select(DigitalWill).where(
                DigitalWill.user_id == user_id,
                DigitalWill.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def mark_will_executed(self, will_id: int, tenant_id: int) -> Optional[DigitalWill]:
        """تحديد الوصية كمنفذة مع التأكد من tenant_id."""
        await self.db.execute(
            update(DigitalWill)
            .where(DigitalWill.id == will_id, DigitalWill.tenant_id == tenant_id)
            .values(is_executed=True, executed_at=func.now())
        )
        await self.db.commit()
        # جلب الوصية المحدثة
        result = await self.db.execute(
            select(DigitalWill).where(DigitalWill.id == will_id, DigitalWill.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    # ============================================================
    # 3. أوراكل الموت (Death Oracle) مع العزل السيادي
    # ============================================================

    async def get_death_oracle(self, user_id: int, tenant_id: int) -> Optional[DeathOracleCheck]:
        """جلب سجل أوراكل الموت مع التأكد من tenant_id."""
        result = await self.db.execute(
            select(DeathOracleCheck).where(
                DeathOracleCheck.user_id == user_id,
                DeathOracleCheck.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def create_death_oracle(self, **kwargs) -> DeathOracleCheck:
        """إنشاء سجل أوراكل موت جديد (يتضمن tenant_id)."""
        oracle = DeathOracleCheck(**kwargs)
        self.db.add(oracle)
        await self.db.commit()
        await self.db.refresh(oracle)
        return oracle

    async def update_death_oracle_status(
        self,
        user_id: int,
        tenant_id: int,
        status: str,
        death_certificate_ipfs: Optional[str] = None,
        release_tx: Optional[str] = None
    ) -> DeathOracleCheck:
        """تحديث حالة أوراكل الموت مع التأكد من tenant_id."""
        # 🔥 استخدام update بدلاً من تعيين القيم مباشرة
        values = {"status": status}
        if death_certificate_ipfs:
            values["official_death_certificate_ipfs"] = death_certificate_ipfs
        if release_tx:
            values["release_tx_hash"] = release_tx

        await self.db.execute(
            update(DeathOracleCheck)
            .where(
                DeathOracleCheck.user_id == user_id,
                DeathOracleCheck.tenant_id == tenant_id
            )
            .values(**values)
        )
        await self.db.commit()
        return await self.get_death_oracle(user_id, tenant_id)

    # ============================================================
    # 4. محطات الحياة (Life Milestones) مع العزل السيادي
    # ============================================================

    async def create_life_milestone(self, **kwargs) -> LifeMilestone:
        """إنشاء محطة حياة جديدة (يتضمن tenant_id)."""
        milestone = LifeMilestone(**kwargs)
        self.db.add(milestone)
        await self.db.commit()
        await self.db.refresh(milestone)
        return milestone

    async def list_life_milestones(self, user_id: int, tenant_id: int) -> List[LifeMilestone]:
        """قائمة محطات الحياة مع التأكد من tenant_id."""
        result = await self.db.execute(
            select(LifeMilestone)
            .where(
                LifeMilestone.user_id == user_id,
                LifeMilestone.tenant_id == tenant_id
            )
            .order_by(LifeMilestone.occurrence_date)
        )
        # 🔥 تحويل النتيجة إلى list
        return list(result.scalars().all())

    # ============================================================
    # 5. الحجز قبل الولادة (Pre-Birth) مع العزل السيادي
    # ============================================================

    async def create_pre_birth_record(self, **kwargs) -> PreBirthRecord:
        """إنشاء سجل حجز قبل الولادة (يتضمن tenant_id)."""
        record = PreBirthRecord(**kwargs)
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def get_pre_birth_record(self, reserved_sovereign_id: str, tenant_id: int) -> Optional[PreBirthRecord]:
        """جلب سجل حجز قبل الولادة مع التأكد من tenant_id."""
        result = await self.db.execute(
            select(PreBirthRecord).where(
                PreBirthRecord.reserved_sovereign_id == reserved_sovereign_id,
                PreBirthRecord.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    # ============================================================
    # 6. التوائم النشطة (للفوترة)
    # ============================================================

    async def list_active_twins(self, tenant_id: int) -> List[DigitalTwinConfig]:
        """
        جلب جميع التوائم الرقمية النشطة لمستأجر معين.
        تُستدعى من مهمة billing.process_twin_subscriptions.
        """
        result = await self.db.execute(
            select(DigitalTwinConfig)
            .where(
                DigitalTwinConfig.tenant_id == tenant_id,
                DigitalTwinConfig.is_active == True
            )
        )
        return list(result.scalars().all())