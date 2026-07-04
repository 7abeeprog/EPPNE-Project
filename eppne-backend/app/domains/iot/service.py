# app/domains/iot/service.py (الإصدار النهائي المتكامل)
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
import httpx
import asyncio

from app.domains.iot.repository import IoTRepository
from app.domains.iot.models import UtilityType, SmartAsset, UtilityGrid, UtilityReading, MaintenanceLog
from app.domains.finance.service import FinanceService
from app.core.config import settings
from app.core.redis_client import redis_client as get_redis_client
from app.core.errors import BusinessError, NotFoundError

class IoTService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = IoTRepository(db)
        self.finance = FinanceService(db)
        self.redis = get_redis_client()

    # ========== مساعدات خاصة ==========
    async def _get_idempotency(self, key: str) -> Optional[Dict]:
        # البحث في Redis أولاً (أسرع)
        redis_val = await self.redis.get(f"idem:{key}")
        if redis_val:
            return json.loads(redis_val)
        # ثم في قاعدة البيانات
        return await self.repo.get_idempotency(key)

    async def _save_idempotency(self, key: str, response: dict, ttl_seconds: int = 86400):
        # تخزين في Redis مع صلاحية
        await self.redis.setex(f"idem:{key}", ttl_seconds, json.dumps(response))
        # تخزين في DB للاستمرارية
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        await self.repo.save_idempotency(key, response, expires_at)

    # ========== عمليات الأصول ==========
    async def create_asset(self, owner_id: int, data: dict) -> SmartAsset:
        async with self.db.begin():
            asset = await self.repo.create_asset(owner_id=owner_id, **data)
            return asset

    async def get_asset(self, asset_id: int, user_id: int) -> Optional[SmartAsset]:
        asset = await self.repo.get_asset(asset_id)
        if not asset or asset.owner_id != user_id:
            raise NotFoundError("Asset not found or not owned")
        return asset

    async def list_assets(self, user_id: int, asset_class: Optional[str] = None, skip=0, limit=100):
        # محاولة قراءة من Redis
        cache_key = f"user_assets:{user_id}:{asset_class or 'all'}:{skip}:{limit}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        assets = await self.repo.list_assets(owner_id=user_id, asset_class=asset_class, skip=skip, limit=limit)
        # تخزين في Redis مع صلاحية 5 دقائق
        await self.redis.setex(cache_key, 300, json.dumps([a.__dict__ for a in assets], default=str))
        return assets

    async def update_asset(self, asset_id: int, user_id: int, data: dict) -> SmartAsset:
        async with self.db.begin():
            asset = await self.repo.get_asset(asset_id)
            if not asset or asset.owner_id != user_id:
                raise NotFoundError("Asset not found or not owned")
            updated = await self.repo.update_asset(asset_id, **data)
            # إبطال ذاكرة التخزين المؤقت للمستخدم
            await self.redis.delete(f"user_assets:{user_id}:*")
            return updated

    # ========== عمليات المحطات (للمشرف فقط) ==========
    async def create_grid(self, data: dict) -> UtilityGrid:
        async with self.db.begin():
            grid = await self.repo.create_grid(**data)
            return grid

    async def list_grids(self, grid_type: Optional[str] = None, skip=0, limit=50):
        cache_key = f"grids:{grid_type or 'all'}:{skip}:{limit}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        grids = await self.repo.list_grids(grid_type, skip, limit)
        await self.redis.setex(cache_key, 600, json.dumps([g.__dict__ for g in grids], default=str))
        return grids

    # ========== القراءات (مع Idempotency) ==========
    async def record_reading(self, data: dict, idempotency_key: Optional[str] = None,
                             ip: Optional[str] = None, ua: Optional[str] = None) -> dict:
        # التحقق من Idempotency
        if idempotency_key:
            existing = await self._get_idempotency(idempotency_key)
            if existing:
                return existing

        async with self.db.begin():
            # حساب الكربون
            carbon_mt = Decimal(0)
            carbon_credits = Decimal(0)
            if data['reading_type'] == UtilityType.ELECTRICITY:
                carbon_mt = Decimal(data.get('consumed_value', 0)) * Decimal('0.0004')
            elif data['reading_type'] == UtilityType.BIOGAS:
                carbon_credits = Decimal(data.get('produced_value', 0)) * Decimal('0.002')

            data['carbon_emissions_mt'] = carbon_mt
            data['carbon_credits_generated'] = carbon_credits

            # حفظ القراءة
            reading = await self.repo.create_reading(**data)

            # تحديث حمل المحطة إن وجدت
            if reading.grid_id and reading.consumed_value > 0:
                grid = await self.repo.get_grid(reading.grid_id)
                if grid:
                    new_load = Decimal(grid.current_load) + Decimal(reading.consumed_value)
                    await self.repo.update_grid_load(grid.id, new_load)

            # تسجيل سجل التدقيق
            await self.repo.log_request(
                user_id=None,  # يمكن تمريره من الـ Router
                endpoint="/iot/readings",
                method="POST",
                ip=ip,
                ua=ua,
                idem_key=idempotency_key,
                request_body=data,
                status_code=201
            )

            # إذا كان هناك مفتاح Idempotency، نخزن النتيجة
            result = {"status": "success", "reading_id": reading.id, "carbon_credits": float(carbon_credits)}
            if idempotency_key:
                await self._save_idempotency(idempotency_key, result)

            return result

    async def get_readings(self, user_id: int, asset_id: Optional[int] = None,
                           grid_id: Optional[int] = None, limit: int = 100):
        # تصفية حسب المالك
        return await self.repo.list_readings(asset_id, grid_id, owner_id=user_id, limit=limit)

    # ========== تسييل الكربون (مع Idempotency) ==========
    async def settle_carbon_credits(self, owner_id: int, asset_ids: Optional[List[int]] = None,
                                    idempotency_key: Optional[str] = None,
                                    ip: Optional[str] = None, ua: Optional[str] = None) -> dict:
        # التحقق من Idempotency
        if idempotency_key:
            existing = await self._get_idempotency(idempotency_key)
            if existing:
                return existing

        async with self.db.begin():
            # 1. جلب الأرصدة غير المسواة
            unsettled = await self.repo.get_unsettled_carbon_credits(owner_id)
            if asset_ids:
                unsettled = [r for r in unsettled if r.asset_id in asset_ids]

            if not unsettled:
                result = {"status": "NO_CREDITS", "message": "لا توجد أرصدة كربونية متاحة للتسييل"}
                if idempotency_key:
                    await self._save_idempotency(idempotency_key, result)
                return result

            total_credits = sum(r.carbon_credits_generated for r in unsettled)
            reading_ids = [r.id for r in unsettled]

            # 2. حساب القيمة المالية
            monetary_value = total_credits * Decimal('50.0')  # 50 MRUSDT لكل طن

            # 3. استدعاء الخدمة المالية (مع محاولة إعادة)
            try:
                await self.finance.deposit(
                    user_id=owner_id,
                    currency="MR_USDT",
                    amount=monetary_value,
                    description=f"تسييل {total_credits} طن كربون من {len(reading_ids)} قراءة"
                )
            except Exception as e:
                # إذا فشل الإيداع، نرفع استثناء لإلغاء المعاملة (لن نحدث حالة القراءات)
                raise BusinessError(f"فشل الإيداع المالي: {str(e)}")

            # 4. تحديث القراءات إلى مسواة
            await self.repo.mark_carbon_settled(reading_ids)

            # 5. تسجيل التدقيق
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
                "total_credits_settled": float(total_credits),
                "monetary_value_added_mrusdt": float(monetary_value),
                "readings_processed": len(reading_ids)
            }

            if idempotency_key:
                await self._save_idempotency(idempotency_key, result)

            return result

    # ========== الصيانة ==========
    async def create_maintenance(self, data: dict) -> MaintenanceLog:
        async with self.db.begin():
            log = await self.repo.create_maintenance(**data)
            return log

    async def resolve_maintenance(self, log_id: int, technician_id: int) -> MaintenanceLog:
        async with self.db.begin():
            log = await self.repo.resolve_maintenance(log_id, technician_id)
            return log