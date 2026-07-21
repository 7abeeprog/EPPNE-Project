# app/domains/iot/service.py (الإصدار النهائي المتكامل)
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from typing import Optional, List, Dict, Any, cast
from datetime import datetime, timedelta
import json
import uuid

from app.domains.iot.repository import IoTRepository
from app.domains.iot.models import UtilityType, SmartAsset, UtilityGrid, UtilityReading, MaintenanceLog
from app.domains.finance.service import FinanceService
from app.core.config import settings
from app.core.redis_client import redis_client as get_redis_client
from app.core.errors import BusinessError, NotFoundError, PermissionDeniedError
from app.core.idempotency import check_idempotency, store_idempotency_result


class IoTService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = IoTRepository(db)
        self.finance = FinanceService(db)
        self.redis = cast(Any, get_redis_client)

    # ============================================================
    # دوال مساعدة
    # ============================================================

    async def _get_user_email(self, user_id: int) -> str:
        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)
        user = await user_repo.get_by_id(user_id)
        return user.email if user else f"user_{user_id}@eppne.com"  # type: ignore

    async def _validate_idempotency(self, idempotency_key: str) -> Optional[dict]:
        if not idempotency_key:
            return None
        cached = await check_idempotency(idempotency_key)
        if cached:
            return cached
        return None

    async def _store_idempotency(self, idempotency_key: str, result: dict):
        if idempotency_key:
            await store_idempotency_result(idempotency_key, result)

    # ============================================================
    # 1. عمليات الأصول (Assets)
    # ============================================================

    async def create_asset(self, owner_id: int, data: Dict[str, Any]) -> SmartAsset:
        async with self.db.begin_nested():
            asset = await self.repo.create_asset(owner_id=owner_id, **data)
            return asset

    async def get_asset(self, asset_id: int, user_id: int) -> Optional[SmartAsset]:
        asset = await self.repo.get_asset(asset_id)
        if not asset or asset.owner_id != user_id:  # type: ignore
            raise NotFoundError("Asset not found or not owned")
        return asset

    async def list_assets(self, user_id: int, asset_class: Optional[str] = None, skip: int = 0, limit: int = 100):
        cache_key = f"user_assets:{user_id}:{asset_class or 'all'}:{skip}:{limit}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        assets = await self.repo.list_assets(owner_id=user_id, asset_class=asset_class, skip=skip, limit=limit)
        await self.redis.setex(cache_key, 300, json.dumps([a.__dict__ for a in assets], default=str))
        return assets

    async def update_asset(self, asset_id: int, user_id: int, data: Dict[str, Any]) -> SmartAsset:
        async with self.db.begin_nested():
            asset = await self.repo.get_asset(asset_id)
            if not asset or asset.owner_id != user_id:  # type: ignore
                raise NotFoundError("Asset not found or not owned")
            updated = await self.repo.update_asset(asset_id, **data)
            await self.redis.delete(f"user_assets:{user_id}:*")
            return updated

    # ============================================================
    # 2. عمليات المحطات (Grids) – للمشرف فقط
    # ============================================================

    async def create_grid(self, data: Dict[str, Any]) -> UtilityGrid:
        async with self.db.begin_nested():
            grid = await self.repo.create_grid(**data)
            return grid

    async def list_grids(self, grid_type: Optional[str] = None, skip: int = 0, limit: int = 50):
        cache_key = f"grids:{grid_type or 'all'}:{skip}:{limit}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        grids = await self.repo.list_grids(grid_type, skip, limit)
        await self.redis.setex(cache_key, 600, json.dumps([g.__dict__ for g in grids], default=str))
        return grids

    # ============================================================
    # 3. القراءات (Readings) – مع Idempotency
    # ============================================================

    async def record_reading(
        self,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> dict:
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached:
                return cached

        async with self.db.begin_nested():
            carbon_mt = Decimal(0)
            carbon_credits = Decimal(0)
            reading_type = data.get('reading_type')
            if reading_type == UtilityType.ELECTRICITY:
                carbon_mt = Decimal(data.get('consumed_value', 0)) * Decimal('0.0004')
            elif reading_type == UtilityType.BIOGAS:
                carbon_credits = Decimal(data.get('produced_value', 0)) * Decimal('0.002')

            data['carbon_emissions_mt'] = carbon_mt
            data['carbon_credits_generated'] = carbon_credits

            reading = await self.repo.create_reading(**data)

            if reading.grid_id and reading.consumed_value > 0:  # type: ignore
                grid = await self.repo.get_grid(reading.grid_id)  # type: ignore
                if grid:
                    new_load = Decimal(grid.current_load) + Decimal(reading.consumed_value)  # type: ignore
                    await self.repo.update_grid_load(grid.id, new_load)  # type: ignore

            await self.repo.log_request(
                user_id=None,
                endpoint="/iot/readings",
                method="POST",
                ip=ip,
                ua=ua,
                idem_key=idempotency_key,
                request_body=data,
                status_code=201
            )

            result = {"status": "success", "reading_id": reading.id, "carbon_credits": float(carbon_credits)}

        if idempotency_key:
            await self._store_idempotency(idempotency_key, result)

        return result

    async def get_readings(
        self,
        user_id: int,
        asset_id: Optional[int] = None,
        grid_id: Optional[int] = None,
        limit: int = 100
    ):
        return await self.repo.list_readings(asset_id, grid_id, owner_id=user_id, limit=limit)

    # ============================================================
    # 4. تسييل الكربون (Carbon Settlement) – مع Idempotency
    # ============================================================

    async def settle_carbon_credits(
        self,
        owner_id: int,
        asset_ids: Optional[List[int]] = None,
        idempotency_key: Optional[str] = None,
        ip: Optional[str] = None,
        ua: Optional[str] = None
    ) -> dict:
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached:
                return cached

        async with self.db.begin_nested():
            unsettled = await self.repo.get_unsettled_carbon_credits(owner_id)
            if asset_ids:
                unsettled = [r for r in unsettled if r.asset_id in asset_ids]  # type: ignore

            if not unsettled:
                result = {"status": "NO_CREDITS", "message": "لا توجد أرصدة كربونية متاحة للتسييل"}
                if idempotency_key:
                    await self._store_idempotency(idempotency_key, result)
                return result

            total_credits = sum(r.carbon_credits_generated for r in unsettled)  # type: ignore
            reading_ids = [r.id for r in unsettled]  # type: ignore
            monetary_value = total_credits * Decimal('50.0')

            payment_idempotency = f"carbon_settle_{idempotency_key or uuid.uuid4().hex[:12]}"
            try:
                await self.finance.transfer(
                    sender_id=1,
                    receiver_email=await self._get_user_email(owner_id),
                    currency="MR_USDT",
                    amount=cast(Decimal, monetary_value),
                    notes=f"تسييل {total_credits} طن كربون",
                    idempotency_key=payment_idempotency
                )
            except Exception as e:
                raise BusinessError(f"فشل الإيداع المالي: {str(e)}")

            await self.repo.mark_carbon_settled(cast(Any, reading_ids))

            await self.repo.log_request(
                user_id=owner_id,
                endpoint="/iot/carbon/settle",
                method="POST",
                ip=ip,
                ua=ua,
                idem_key=idempotency_key,
                request_body={"asset_ids": asset_ids},
                status_code=200
            )

            result = {
                "status": "SUCCESS",
                "total_credits_settled": float(cast(Decimal, total_credits)),
                "monetary_value_added_mrusdt": float(cast(Decimal, monetary_value)),
                "readings_processed": len(reading_ids)
            }

        if idempotency_key:
            await self._store_idempotency(idempotency_key, result)

        return result

    # ============================================================
    # 5. الصيانة (Maintenance)
    # ============================================================

    async def create_maintenance(self, data: Dict[str, Any]) -> MaintenanceLog:
        async with self.db.begin_nested():
            log = await self.repo.create_maintenance(**data)
            return log

    async def resolve_maintenance(self, log_id: int, technician_id: int) -> MaintenanceLog:
        async with self.db.begin_nested():
            log = await self.repo.resolve_maintenance(log_id, technician_id)
            return log