# app/domains/guardian/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from typing import Optional, List

from app.domains.guardian.models import GuardianRelationship, GuardianVisibilitySetting, GuardianVisibilitySector
from app.domains.academy.models import Instructor


class GuardianRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- Guardian Relationships ----------
    async def create_relationship(self, **kwargs) -> GuardianRelationship:
        relationship = GuardianRelationship(**kwargs)
        self.db.add(relationship)
        await self.db.flush()
        await self.db.refresh(relationship)
        return relationship

    async def get_relationship(self, relationship_id: int, tenant_id: int) -> Optional[GuardianRelationship]:
        result = await self.db.execute(
            select(GuardianRelationship).where(
                and_(
                    GuardianRelationship.id == relationship_id,
                    GuardianRelationship.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_relationship_by_guardian_and_ward(
        self, guardian_user_id: int, ward_user_id: int,
    ) -> Optional[GuardianRelationship]:
        result = await self.db.execute(
            select(GuardianRelationship).where(
                and_(
                    GuardianRelationship.guardian_user_id == guardian_user_id,
                    GuardianRelationship.ward_user_id == ward_user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def update_relationship(
        self, relationship_id: int, tenant_id: int, **kwargs,
    ) -> Optional[GuardianRelationship]:
        relationship = await self.get_relationship(relationship_id, tenant_id)
        if not relationship:
            return None
        for key, value in kwargs.items():
            setattr(relationship, key, value)
        await self.db.flush()
        await self.db.refresh(relationship)
        return relationship

    # ---------- Visibility Settings ----------
    async def create_visibility_setting(self, **kwargs) -> GuardianVisibilitySetting:
        setting = GuardianVisibilitySetting(**kwargs)
        self.db.add(setting)
        await self.db.flush()
        await self.db.refresh(setting)
        return setting

    async def list_visibility_settings(self, guardian_relationship_id: int) -> List[GuardianVisibilitySetting]:
        result = await self.db.execute(
            select(GuardianVisibilitySetting).where(
                GuardianVisibilitySetting.guardian_relationship_id == guardian_relationship_id
            )
        )
        return list(result.scalars().all())

    async def upsert_visibility_setting(
        self, guardian_relationship_id: int, sector: GuardianVisibilitySector, is_visible: bool,
    ) -> GuardianVisibilitySetting:
        """INSERT...ON CONFLICT DO UPDATE ذرّي على القيد الفريد
        (guardian_relationship_id, sector) — نفس نمط
        `AchievementRepository.increment_bootcamp_network_size`، بلا
        SELECT أول. `populate_existing=True` إجباري في الـSELECT اللي
        بعده لنفس سبب `AchievementRepository.get_network_stats` بالحرف:
        لو الصف اتحمَّل قبل كده في نفس الـsession (زي
        `_ensure_default_visibility_settings` وقت الإنشاء الأول)، الـORM
        identity map بترجّع النسخة القديمة المخزَّنة، مش القيمة الجديدة
        الفعلية بعد الـUPDATE — حتى لو الاستعلام نفسه نفَّذ صح. اتأكَّد
        بالتنفيذ الفعلي (test فشل قبل الإصلاح: `is_visible` فضلت `True`
        بعد upsert لـ`False`)."""
        stmt = pg_insert(GuardianVisibilitySetting).values(
            guardian_relationship_id=guardian_relationship_id,
            sector=sector,
            is_visible=is_visible,
        ).on_conflict_do_update(
            index_elements=[
                GuardianVisibilitySetting.guardian_relationship_id,
                GuardianVisibilitySetting.sector,
            ],
            set_={"is_visible": is_visible},
        ).returning(GuardianVisibilitySetting.id)
        result = await self.db.execute(stmt)
        setting_id = result.scalar_one()
        await self.db.flush()
        refreshed = await self.db.execute(
            select(GuardianVisibilitySetting)
            .where(GuardianVisibilitySetting.id == setting_id)
            .execution_options(populate_existing=True)
        )
        return refreshed.scalar_one()

    # ---------- Academy (استعلام مباشر معزول، صفر لمس على academy/repository.py) ----------
    async def get_instructor_user_id(self, instructor_id: int) -> Optional[int]:
        """يرجع user_id بتاع المدرّس. الأمان محقَّق مسبقًا عبر Course.tenant_id
        (الاستدعاء بيحصل بس بعد التأكد إن الكورس نفسه ينتمي لنفس الـtenant)،
        مش عبر فلتر مباشر هنا — Instructor نفسها مفيهاش tenant_id
        (باج schema موثَّق منفصل: backlog-academy-instructors-missing-tenant-id)."""
        result = await self.db.execute(
            select(Instructor.user_id).where(Instructor.id == instructor_id)
        )
        return result.scalar_one_or_none()
