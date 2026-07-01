# app/domains/realestate/repository.py (الإصدار النهائي المتكامل مع جميع الإضافات)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from typing import Optional, List
from decimal import Decimal
from app.domains.realestate.models import *
from app.core.errors import NotFoundError

class RealEstateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- Land Assets ----------
    async def create_land_asset(self, **kwargs) -> LandAsset:
        asset = LandAsset(**kwargs)
        self.db.add(asset)
        await self.db.commit()
        await self.db.refresh(asset)
        return asset

    async def get_land_asset(self, asset_id: int) -> Optional[LandAsset]:
        result = await self.db.execute(select(LandAsset).where(LandAsset.id == asset_id))
        return result.scalar_one_or_none()

    async def list_land_assets(self, tenant_id: int, owner_id: Optional[int] = None, skip=0, limit=100):
        query = select(LandAsset).where(LandAsset.tenant_id == tenant_id, LandAsset.is_deleted == False)
        if owner_id:
            query = query.where(LandAsset.owner_id == owner_id)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_land_value(self, asset_id: int, new_value: Decimal) -> LandAsset:
        await self.db.execute(update(LandAsset).where(LandAsset.id == asset_id).values(current_value_mrusdt=new_value))
        await self.db.commit()
        return await self.get_land_asset(asset_id)

    # ---------- Developments ----------
    async def create_development(self, **kwargs) -> RealEstateDevelopment:
        dev = RealEstateDevelopment(**kwargs)
        self.db.add(dev)
        await self.db.commit()
        await self.db.refresh(dev)
        return dev

    async def get_development(self, dev_id: int) -> Optional[RealEstateDevelopment]:
        result = await self.db.execute(select(RealEstateDevelopment).where(RealEstateDevelopment.id == dev_id))
        return result.scalar_one_or_none()

    async def update_development_progress(self, dev_id: int, spent: Decimal, completion: float) -> RealEstateDevelopment:
        await self.db.execute(
            update(RealEstateDevelopment)
            .where(RealEstateDevelopment.id == dev_id)
            .values(spent_budget_mrusdt=spent, completion_percentage=completion)
        )
        await self.db.commit()
        return await self.get_development(dev_id)

    # ---------- Property Units ----------
    async def create_unit(self, **kwargs) -> PropertyUnit:
        unit = PropertyUnit(**kwargs)
        self.db.add(unit)
        await self.db.commit()
        await self.db.refresh(unit)
        return unit

    async def get_unit(self, unit_id: int) -> Optional[PropertyUnit]:
        result = await self.db.execute(select(PropertyUnit).where(PropertyUnit.id == unit_id))
        return result.scalar_one_or_none()

    async def list_units(self, development_id: Optional[int] = None, for_sale: bool = False, skip=0, limit=100):
        query = select(PropertyUnit).where(PropertyUnit.is_deleted == False)
        if development_id:
            query = query.where(PropertyUnit.development_id == development_id)
        if for_sale:
            query = query.where(PropertyUnit.is_available_for_sale == True)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_unit_availability(self, unit_id: int, for_sale: bool = None, for_rent: bool = None) -> PropertyUnit:
        updates = {}
        if for_sale is not None:
            updates["is_available_for_sale"] = for_sale
        if for_rent is not None:
            updates["is_available_for_rent"] = for_rent
        if updates:
            await self.db.execute(update(PropertyUnit).where(PropertyUnit.id == unit_id).values(**updates))
            await self.db.commit()
        return await self.get_unit(unit_id)

    # ---------- Ownership ----------
    async def create_ownership(self, **kwargs) -> PropertyOwnership:
        ownership = PropertyOwnership(**kwargs)
        self.db.add(ownership)
        await self.db.commit()
        await self.db.refresh(ownership)
        return ownership

    async def get_ownerships_by_unit(self, unit_id: int) -> List[PropertyOwnership]:
        result = await self.db.execute(select(PropertyOwnership).where(PropertyOwnership.unit_id == unit_id))
        return result.scalars().all()

    async def get_total_ownership_percentage(self, unit_id: int) -> float:
        result = await self.db.execute(
            select(func.sum(PropertyOwnership.ownership_percentage)).where(PropertyOwnership.unit_id == unit_id)
        )
        return result.scalar() or 0.0

    async def get_user_ownerships(self, user_id: int) -> List[PropertyOwnership]:
        result = await self.db.execute(select(PropertyOwnership).where(PropertyOwnership.owner_user_id == user_id))
        return result.scalars().all()

    # ---------- Rental Contracts ----------
    async def create_rental_contract(self, **kwargs) -> RentalContract:
        contract = RentalContract(**kwargs)
        self.db.add(contract)
        await self.db.commit()
        await self.db.refresh(contract)
        return contract

    async def get_rental_contracts_for_tenant(self, tenant_id: int) -> List[RentalContract]:
        result = await self.db.execute(select(RentalContract).where(RentalContract.tenant_user_id == tenant_id))
        return result.scalars().all()

    # ========== Master Plan ==========
    async def create_master_plan(self, **kwargs) -> MasterPlan:
        plan = MasterPlan(**kwargs)
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def get_master_plan(self, plan_id: int, tenant_id: int) -> Optional[MasterPlan]:
        result = await self.db.execute(
            select(MasterPlan).where(MasterPlan.id == plan_id, MasterPlan.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    # ========== Tokenization ==========
    async def create_tokenization(self, **kwargs) -> AssetTokenization:
        token = AssetTokenization(**kwargs)
        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)
        return token

    async def get_tokenization_by_unit(self, unit_id: int, tenant_id: int) -> Optional[AssetTokenization]:
        result = await self.db.execute(
            select(AssetTokenization).where(AssetTokenization.unit_id == unit_id, AssetTokenization.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    # ========== Smart Contract ==========
    async def create_smart_contract(self, **kwargs) -> SmartContractEngine:
        contract = SmartContractEngine(**kwargs)
        self.db.add(contract)
        await self.db.commit()
        await self.db.refresh(contract)
        return contract

    async def get_smart_contract(self, contract_id: int, tenant_id: int) -> Optional[SmartContractEngine]:
        result = await self.db.execute(
            select(SmartContractEngine).where(SmartContractEngine.id == contract_id, SmartContractEngine.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def update_smart_contract_status(
        self,
        contract_id: int,
        status: str,
        tx_hash: str = None
    ) -> SmartContractEngine:
        values = {"execution_status": status}
        if tx_hash:
            values["blockchain_tx_hash"] = tx_hash
        if status == "CONFIRMED":
            values["executed_at"] = func.now()
        
        await self.db.execute(
            update(SmartContractEngine)
            .where(SmartContractEngine.id == contract_id)
            .values(**values)
        )
        await self.db.commit()
        
        result = await self.db.execute(
            select(SmartContractEngine).where(SmartContractEngine.id == contract_id)
        )
        return result.scalar_one()

    async def get_pending_smart_contracts(self, tenant_id: int) -> List[SmartContractEngine]:
        result = await self.db.execute(
            select(SmartContractEngine)
            .where(
                SmartContractEngine.tenant_id == tenant_id,
                SmartContractEngine.execution_status == "PENDING"
            )
        )
        return result.scalars().all()