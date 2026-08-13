# app/domains/logistics/repository.py
"""
مستودع (Repository) قطاع اللوجيستيات والمخازن
يدعم جميع عمليات CRUD مع العزل السيادي التام
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from app.domains.logistics.models import *
from app.core.errors import NotFoundError


class LogisticsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # 1. المخازن (Warehouses)
    # ============================================================

    async def create_warehouse(self, **kwargs) -> Warehouse:
        warehouse = Warehouse(**kwargs)
        self.db.add(warehouse)
        await self.db.flush()
        await self.db.refresh(warehouse)
        return warehouse

    async def get_warehouse(self, warehouse_id: int, tenant_id: int) -> Optional[Warehouse]:
        result = await self.db.execute(
            select(Warehouse).where(
                Warehouse.id == warehouse_id,  # type: ignore
                Warehouse.tenant_id == tenant_id,  # type: ignore
                Warehouse.is_deleted == False  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def list_warehouses(
        self,
        tenant_id: int,
        warehouse_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Warehouse]:
        query = select(Warehouse).where(
            Warehouse.tenant_id == tenant_id,  # type: ignore
            Warehouse.is_deleted == False  # type: ignore
        )
        if warehouse_type:
            query = query.where(Warehouse.warehouse_type == warehouse_type)  # type: ignore
        if is_active is not None:
            query = query.where(Warehouse.is_active == is_active)  # type: ignore
        query = query.order_by(Warehouse.created_at.desc()).offset(skip).limit(limit)  # type: ignore
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_warehouse(self, warehouse_id: int, tenant_id: int, **kwargs) -> Optional[Warehouse]:
        await self.db.execute(
            update(Warehouse)
            .where(Warehouse.id == warehouse_id, Warehouse.tenant_id == tenant_id)  # type: ignore
            .values(**kwargs)
        )
        await self.db.commit()
        return await self.get_warehouse(warehouse_id, tenant_id)

    async def update_warehouse_usage(self, warehouse_id: int, tenant_id: int, units: int, operation: str = "add") -> Warehouse:
        warehouse = await self.get_warehouse(warehouse_id, tenant_id)
        if not warehouse:
            raise NotFoundError("Warehouse not found")
        if operation == "add":
            warehouse.used_capacity_units += units  # type: ignore
        else:
            warehouse.used_capacity_units = max(0, warehouse.used_capacity_units - units)  # type: ignore
        await self.db.flush()
        await self.db.refresh(warehouse)
        return warehouse

    async def delete_warehouse(self, warehouse_id: int, tenant_id: int) -> None:
        await self.db.execute(
            update(Warehouse)
            .where(Warehouse.id == warehouse_id, Warehouse.tenant_id == tenant_id)  # type: ignore
            .values(is_deleted=True, deleted_at=func.now())
        )
        await self.db.commit()

    # ============================================================
    # 2. مناطق المخازن (Warehouse Zones)
    # ============================================================

    async def create_zone(self, **kwargs) -> WarehouseZone:
        zone = WarehouseZone(**kwargs)
        self.db.add(zone)
        await self.db.flush()
        await self.db.refresh(zone)
        return zone

    async def get_zone(self, zone_id: int, tenant_id: int) -> Optional[WarehouseZone]:
        result = await self.db.execute(
            select(WarehouseZone).where(
                WarehouseZone.id == zone_id,  # type: ignore
                WarehouseZone.tenant_id == tenant_id  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def list_zones(self, warehouse_id: int, tenant_id: int) -> List[WarehouseZone]:
        result = await self.db.execute(
            select(WarehouseZone).where(
                WarehouseZone.warehouse_id == warehouse_id,  # type: ignore
                WarehouseZone.tenant_id == tenant_id  # type: ignore
            )
        )
        return list(result.scalars().all())

    async def update_zone_usage(self, zone_id: int, tenant_id: int, units: int, operation: str = "add") -> WarehouseZone:
        zone = await self.get_zone(zone_id, tenant_id)
        if not zone:
            raise NotFoundError("Zone not found")
        if operation == "add":
            zone.used_units += units  # type: ignore
        else:
            zone.used_units = max(0, zone.used_units - units)  # type: ignore
        await self.db.commit()
        await self.db.refresh(zone)
        return zone

    # ============================================================
    # 3. المخزون (Inventory Items)
    # ============================================================

    async def create_inventory_item(self, **kwargs) -> InventoryItem:
        item = InventoryItem(**kwargs)
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def get_inventory_item(self, item_id: int, tenant_id: int) -> Optional[InventoryItem]:
        result = await self.db.execute(
            select(InventoryItem).where(
                InventoryItem.id == item_id,  # type: ignore
                InventoryItem.tenant_id == tenant_id,  # type: ignore
                InventoryItem.is_deleted == False  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def get_inventory_by_product(self, product_id: int, tenant_id: int, warehouse_id: Optional[int] = None) -> List[InventoryItem]:
        query = select(InventoryItem).where(
            InventoryItem.product_id == product_id,  # type: ignore
            InventoryItem.tenant_id == tenant_id,  # type: ignore
            InventoryItem.is_deleted == False  # type: ignore
        )
        if warehouse_id:
            query = query.where(InventoryItem.warehouse_id == warehouse_id)  # type: ignore
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_inventory(
        self,
        tenant_id: int,
        warehouse_id: Optional[int] = None,
        status: Optional[InventoryStatus] = None,
        product_category: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[InventoryItem]:
        query = select(InventoryItem).where(
            InventoryItem.tenant_id == tenant_id,  # type: ignore
            InventoryItem.is_deleted == False  # type: ignore
        )
        if warehouse_id:
            query = query.where(InventoryItem.warehouse_id == warehouse_id)  # type: ignore
        if status:
            query = query.where(InventoryItem.status == status)  # type: ignore
        if product_category:
            query = query.where(InventoryItem.product_category == product_category)  # type: ignore
        query = query.order_by(InventoryItem.created_at.desc()).offset(skip).limit(limit)  # type: ignore
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_inventory_item(self, item_id: int, tenant_id: int, **kwargs) -> InventoryItem:
        await self.db.execute(
            update(InventoryItem)
            .where(InventoryItem.id == item_id, InventoryItem.tenant_id == tenant_id)  # type: ignore
            .values(**kwargs)
        )
        await self.db.flush()
        return await self.get_inventory_item(item_id, tenant_id)

    async def get_low_stock_items(self, tenant_id: int, warehouse_id: Optional[int] = None) -> List[InventoryItem]:
        query = select(InventoryItem).where(
            InventoryItem.tenant_id == tenant_id,  # type: ignore
            InventoryItem.quantity <= InventoryItem.min_stock_threshold,  # type: ignore
            InventoryItem.is_deleted == False  # type: ignore
        )
        if warehouse_id:
            query = query.where(InventoryItem.warehouse_id == warehouse_id)  # type: ignore
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_expired_items(self, tenant_id: int) -> List[InventoryItem]:
        result = await self.db.execute(
            select(InventoryItem).where(
                InventoryItem.tenant_id == tenant_id,  # type: ignore
                InventoryItem.expiry_date < datetime.utcnow(),  # type: ignore
                InventoryItem.is_deleted == False  # type: ignore
            )
        )
        return list(result.scalars().all())

    async def delete_inventory_item(self, item_id: int, tenant_id: int) -> None:
        await self.db.execute(
            update(InventoryItem)
            .where(InventoryItem.id == item_id, InventoryItem.tenant_id == tenant_id)  # type: ignore
            .values(is_deleted=True, deleted_at=func.now())
        )
        await self.db.commit()

    # ============================================================
    # 4. حركات المخزون (Transactions)
    # ============================================================

    async def create_transaction(self, **kwargs) -> InventoryTransaction:
        transaction = InventoryTransaction(**kwargs)
        self.db.add(transaction)
        await self.db.flush()
        await self.db.refresh(transaction)
        return transaction

    async def get_transaction(self, transaction_id: int, tenant_id: int) -> Optional[InventoryTransaction]:
        result = await self.db.execute(
            select(InventoryTransaction).where(
                InventoryTransaction.id == transaction_id,  # type: ignore
                InventoryTransaction.tenant_id == tenant_id  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def list_transactions(
        self,
        tenant_id: int,
        inventory_item_id: Optional[int] = None,
        transaction_type: Optional[TransactionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[InventoryTransaction]:
        query = select(InventoryTransaction).where(
            InventoryTransaction.tenant_id == tenant_id  # type: ignore
        )
        if inventory_item_id:
            query = query.where(InventoryTransaction.inventory_item_id == inventory_item_id)  # type: ignore
        if transaction_type:
            query = query.where(InventoryTransaction.transaction_type == transaction_type)  # type: ignore
        if start_date:
            query = query.where(InventoryTransaction.created_at >= start_date)  # type: ignore
        if end_date:
            query = query.where(InventoryTransaction.created_at <= end_date)  # type: ignore
        query = query.order_by(InventoryTransaction.created_at.desc()).offset(skip).limit(limit)  # type: ignore
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_inventory_history(self, tenant_id: int, product_id: int, days: int = 90) -> List[dict]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await self.db.execute(
            select(
                InventoryTransaction.created_at,
                InventoryTransaction.quantity,
                InventoryTransaction.transaction_type
            )
            .join(InventoryItem, InventoryTransaction.inventory_item_id == InventoryItem.id)  # type: ignore
            .where(
                InventoryTransaction.tenant_id == tenant_id,  # type: ignore
                InventoryItem.product_id == product_id,  # type: ignore
                InventoryTransaction.created_at >= cutoff  # type: ignore
            )
            .order_by(InventoryTransaction.created_at)
        )
        rows = result.all()
        return [
            {
                "date": row.created_at.isoformat(),
                "quantity": row.quantity,
                "type": row.transaction_type.value
            }
            for row in rows
        ]

    # ============================================================
    # 5. المعدات (Equipment)
    # ============================================================

    async def create_equipment(self, **kwargs) -> Equipment:
        equipment = Equipment(**kwargs)
        self.db.add(equipment)
        await self.db.flush()
        await self.db.refresh(equipment)
        return equipment

    async def get_equipment(self, equipment_id: int, tenant_id: int) -> Optional[Equipment]:
        result = await self.db.execute(
            select(Equipment).where(
                Equipment.id == equipment_id,  # type: ignore
                Equipment.tenant_id == tenant_id,  # type: ignore
                Equipment.is_deleted == False  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def list_equipment(
        self,
        tenant_id: int,
        equipment_type: Optional[str] = None,
        status: Optional[EquipmentStatus] = None,
        warehouse_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Equipment]:
        query = select(Equipment).where(
            Equipment.tenant_id == tenant_id,  # type: ignore
            Equipment.is_deleted == False  # type: ignore
        )
        if equipment_type:
            query = query.where(Equipment.equipment_type == equipment_type)  # type: ignore
        if status:
            query = query.where(Equipment.status == status)  # type: ignore
        if warehouse_id:
            query = query.where(Equipment.warehouse_id == warehouse_id)  # type: ignore
        query = query.order_by(Equipment.created_at.desc()).offset(skip).limit(limit)  # type: ignore
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_equipment(self, equipment_id: int, tenant_id: int, **kwargs) -> Equipment:
        await self.db.execute(
            update(Equipment)
            .where(Equipment.id == equipment_id, Equipment.tenant_id == tenant_id)  # type: ignore
            .values(**kwargs)
        )
        await self.db.commit()
        return await self.get_equipment(equipment_id, tenant_id)

    async def delete_equipment(self, equipment_id: int, tenant_id: int) -> None:
        await self.db.execute(
            update(Equipment)
            .where(Equipment.id == equipment_id, Equipment.tenant_id == tenant_id)  # type: ignore
            .values(is_deleted=True, deleted_at=func.now())
        )
        await self.db.commit()

    # ============================================================
    # 6. صيانة المعدات (Equipment Maintenance)
    # ============================================================

    async def create_maintenance(self, **kwargs) -> EquipmentMaintenance:
        maintenance = EquipmentMaintenance(**kwargs)
        self.db.add(maintenance)
        await self.db.flush()
        await self.db.refresh(maintenance)
        return maintenance

    async def get_maintenance(self, maintenance_id: int, tenant_id: int) -> Optional[EquipmentMaintenance]:
        result = await self.db.execute(
            select(EquipmentMaintenance).where(
                EquipmentMaintenance.id == maintenance_id,  # type: ignore
                EquipmentMaintenance.tenant_id == tenant_id  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def list_maintenance(
        self,
        tenant_id: int,
        equipment_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[EquipmentMaintenance]:
        query = select(EquipmentMaintenance).where(
            EquipmentMaintenance.tenant_id == tenant_id  # type: ignore
        )
        if equipment_id:
            query = query.where(EquipmentMaintenance.equipment_id == equipment_id)  # type: ignore
        if status:
            query = query.where(EquipmentMaintenance.status == status)  # type: ignore
        query = query.order_by(EquipmentMaintenance.created_at.desc()).offset(skip).limit(limit)  # type: ignore
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_maintenance(self, maintenance_id: int, tenant_id: int, **kwargs) -> EquipmentMaintenance:
        await self.db.execute(
            update(EquipmentMaintenance)
            .where(EquipmentMaintenance.id == maintenance_id, EquipmentMaintenance.tenant_id == tenant_id)  # type: ignore
            .values(**kwargs)
        )
        await self.db.commit()
        return await self.get_maintenance(maintenance_id, tenant_id)

    # ============================================================
    # 7. أوامر سلسلة التوريد (Supply Chain Orders)
    # ============================================================

    async def create_order(self, **kwargs) -> SupplyChainOrder:
        order = SupplyChainOrder(**kwargs)
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def get_order(self, order_id: int, tenant_id: int) -> Optional[SupplyChainOrder]:
        result = await self.db.execute(
            select(SupplyChainOrder).where(
                SupplyChainOrder.id == order_id,  # type: ignore
                SupplyChainOrder.tenant_id == tenant_id,  # type: ignore
                SupplyChainOrder.is_deleted == False  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def list_orders(
        self,
        tenant_id: int,
        status: Optional[OrderStatus] = None,
        order_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[SupplyChainOrder]:
        query = select(SupplyChainOrder).where(
            SupplyChainOrder.tenant_id == tenant_id,  # type: ignore
            SupplyChainOrder.is_deleted == False  # type: ignore
        )
        if status:
            query = query.where(SupplyChainOrder.status == status)  # type: ignore
        if order_type:
            query = query.where(SupplyChainOrder.order_type == order_type)  # type: ignore
        query = query.order_by(SupplyChainOrder.created_at.desc()).offset(skip).limit(limit)  # type: ignore
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_order(self, order_id: int, tenant_id: int, **kwargs) -> SupplyChainOrder:
        await self.db.execute(
            update(SupplyChainOrder)
            .where(SupplyChainOrder.id == order_id, SupplyChainOrder.tenant_id == tenant_id)  # type: ignore
            .values(**kwargs)
        )
        await self.db.commit()
        return await self.get_order(order_id, tenant_id)

    async def delete_order(self, order_id: int, tenant_id: int) -> None:
        await self.db.execute(
            update(SupplyChainOrder)
            .where(SupplyChainOrder.id == order_id, SupplyChainOrder.tenant_id == tenant_id)  # type: ignore
            .values(is_deleted=True, deleted_at=func.now())
        )
        await self.db.commit()

    # ============================================================
    # 8. عناصر الأوامر (Order Items)
    # ============================================================

    async def create_order_item(self, **kwargs) -> SupplyChainOrderItem:
        item = SupplyChainOrderItem(**kwargs)
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def list_order_items(self, order_id: int, tenant_id: int) -> List[SupplyChainOrderItem]:
        result = await self.db.execute(
            select(SupplyChainOrderItem).where(
                SupplyChainOrderItem.order_id == order_id,  # type: ignore
                SupplyChainOrderItem.tenant_id == tenant_id  # type: ignore
            )
        )
        return list(result.scalars().all())

    # ============================================================
    # 9. التنبؤ بالطلب (Forecasts)
    # ============================================================

    async def create_forecast(self, **kwargs) -> InventoryForecast:
        forecast = InventoryForecast(**kwargs)
        self.db.add(forecast)
        await self.db.flush()
        await self.db.refresh(forecast)
        return forecast

    async def get_forecast(self, forecast_id: int, tenant_id: int) -> Optional[InventoryForecast]:
        result = await self.db.execute(
            select(InventoryForecast).where(
                InventoryForecast.id == forecast_id,  # type: ignore
                InventoryForecast.tenant_id == tenant_id  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def list_forecasts(
        self,
        tenant_id: int,
        product_id: Optional[int] = None,
        period: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[InventoryForecast]:
        query = select(InventoryForecast).where(
            InventoryForecast.tenant_id == tenant_id  # type: ignore
        )
        if product_id:
            query = query.where(InventoryForecast.product_id == product_id)  # type: ignore
        if period:
            query = query.where(InventoryForecast.forecast_period == period)  # type: ignore
        query = query.order_by(InventoryForecast.created_at.desc()).offset(skip).limit(limit)  # type: ignore
        result = await self.db.execute(query)
        return list(result.scalars().all())