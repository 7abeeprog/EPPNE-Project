# app/domains/iot/repository.py (الإصدار النهائي المتكامل)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from typing import Optional, List
from app.domains.iot.models import SmartAsset, UtilityGrid, UtilityReading, MaintenanceLog, IdempotencyRecord, IoTRequestLog
from app.core.errors import NotFoundError


class IoTRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- Smart Assets ----------
    async def create_asset(self, **kwargs) -> SmartAsset:
        asset = SmartAsset(**kwargs)
        self.db.add(asset)
        return asset

    async def get_asset(self, asset_id: int) -> Optional[SmartAsset]:
        result = await self.db.execute(
            select(SmartAsset).where(SmartAsset.id == asset_id, SmartAsset.is_deleted == False)  # type: ignore
        )
        return result.scalar_one_or_none()

    async def list_assets(self, owner_id: Optional[int] = None, asset_class: Optional[str] = None, skip: int = 0, limit: int = 100):
        query = select(SmartAsset).where(SmartAsset.is_deleted == False)  # type: ignore
        if owner_id:
            query = query.where(SmartAsset.owner_id == owner_id)  # type: ignore
        if asset_class:
            query = query.where(SmartAsset.asset_class == asset_class)  # type: ignore
        query = query.offset(skip).limit(limit)  # type: ignore
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_asset(self, asset_id: int, **kwargs) -> SmartAsset:
        await self.db.execute(update(SmartAsset).where(SmartAsset.id == asset_id).values(**kwargs))  # type: ignore
        asset = await self.get_asset(asset_id)
        if not asset:
            raise NotFoundError("Asset not found")
        return asset

    # ---------- Utility Grids ----------
    async def create_grid(self, **kwargs) -> UtilityGrid:
        grid = UtilityGrid(**kwargs)
        self.db.add(grid)
        return grid

    async def get_grid(self, grid_id: int) -> Optional[UtilityGrid]:
        result = await self.db.execute(select(UtilityGrid).where(UtilityGrid.id == grid_id))  # type: ignore
        return result.scalar_one_or_none()

    async def list_grids(self, grid_type: Optional[str] = None, skip: int = 0, limit: int = 100):
        query = select(UtilityGrid)
        if grid_type:
            query = query.where(UtilityGrid.grid_type == grid_type)  # type: ignore
        query = query.offset(skip).limit(limit)  # type: ignore
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_grid_load(self, grid_id: int, load: float) -> UtilityGrid:
        await self.db.execute(update(UtilityGrid).where(UtilityGrid.id == grid_id).values(current_load=load))  # type: ignore
        return await self.get_grid(grid_id)

    # ---------- Readings ----------
    async def create_reading(self, **kwargs) -> UtilityReading:
        reading = UtilityReading(**kwargs)
        self.db.add(reading)
        return reading

    async def list_readings(
        self,
        asset_id: Optional[int] = None,
        grid_id: Optional[int] = None,
        owner_id: Optional[int] = None,
        limit: int = 100
    ):
        query = select(UtilityReading)
        if asset_id:
            query = query.where(UtilityReading.asset_id == asset_id)  # type: ignore
        if grid_id:
            query = query.where(UtilityReading.grid_id == grid_id)  # type: ignore
        if owner_id:
            subquery = select(SmartAsset.id).where(SmartAsset.owner_id == owner_id)  # type: ignore
            query = query.where(UtilityReading.asset_id.in_(subquery))  # type: ignore
        query = query.order_by(UtilityReading.reading_timestamp.desc()).limit(limit)  # type: ignore
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_unsettled_carbon_credits(self, owner_id: int):
        subquery = select(SmartAsset.id).where(SmartAsset.owner_id == owner_id)  # type: ignore
        result = await self.db.execute(
            select(UtilityReading).where(
                UtilityReading.asset_id.in_(subquery),  # type: ignore
                UtilityReading.carbon_credits_generated > 0,  # type: ignore
                UtilityReading.is_settled_on_chain == False  # type: ignore
            )
        )
        return result.scalars().all()

    async def mark_carbon_settled(self, reading_ids: List[int]):
        await self.db.execute(
            update(UtilityReading).where(UtilityReading.id.in_(reading_ids)).values(is_settled_on_chain=True)  # type: ignore
        )

    # ---------- Maintenance ----------
    async def create_maintenance(self, **kwargs) -> MaintenanceLog:
        log = MaintenanceLog(**kwargs)
        self.db.add(log)
        return log

    async def resolve_maintenance(self, log_id: int, technician_id: int) -> MaintenanceLog:
        await self.db.execute(
            update(MaintenanceLog)
            .where(MaintenanceLog.id == log_id)  # type: ignore
            .values(is_resolved=True, resolution_date=func.now(), technician_id=technician_id)  # type: ignore
        )
        result = await self.db.execute(select(MaintenanceLog).where(MaintenanceLog.id == log_id))  # type: ignore
        return result.scalar_one()

    # ---------- Idempotency ----------
    async def get_idempotency(self, key: str) -> Optional[dict]:
        result = await self.db.execute(select(IdempotencyRecord).where(IdempotencyRecord.key == key))  # type: ignore
        record = result.scalar_one_or_none()
        if record:
            return record.response_data  # type: ignore
        return None

    async def save_idempotency(self, key: str, response_data: dict, expires_at):
        record = IdempotencyRecord(key=key, response_data=response_data, expires_at=expires_at)  # type: ignore
        self.db.add(record)

    # ---------- Audit Log ----------
    async def log_request(
        self,
        user_id: Optional[int],
        endpoint: str,
        method: str,
        ip: Optional[str],
        ua: Optional[str],
        idem_key: Optional[str],
        request_body: Optional[dict],
        status_code: int
    ):
        log = IoTRequestLog(
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            ip_address=ip,
            user_agent=ua,
            idempotency_key=idem_key,
            request_body=request_body,
            status_code=status_code
        )
        self.db.add(log)