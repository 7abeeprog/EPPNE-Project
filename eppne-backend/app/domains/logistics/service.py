# app/domains/logistics/service.py
"""
خدمات قطاع اللوجيستيات والمخازن – النسخة الذهبية
يدعم: إدارة المخازن، المخزون، المعدات، الحركات، وسلسلة التوريد
"""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, cast
import uuid
import bleach

from app.domains.logistics.repository import LogisticsRepository
from app.domains.ai_agents.service import AIAgentsService
from app.domains.saas.service import SaaSControlService
from app.domains.affiliate.service import AffiliateService
from app.domains.invoicing.service import InvoicingService
from app.domains.finance.service import FinanceService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError, ValidationError
from app.core.idempotency import get_idempotency_result, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
import logging

logger = logging.getLogger(__name__)

from app.domains.logistics.models import (
    Warehouse, WarehouseZone, InventoryItem, InventoryTransaction,
    Equipment, EquipmentMaintenance, SupplyChainOrder, SupplyChainOrderItem,
    InventoryForecast, InventoryStatus, EquipmentStatus, OrderStatus, TransactionType
)
from app.domains.identity.models import User


class LogisticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = LogisticsRepository(db)
        self.event_bus = EventBus(cast(Any, redis_client))
        self.redis = redis_client

    # ============================================================
    # دوال مساعدة
    # ============================================================

    async def _check_saas_limits(self, tenant_id: int, feature: str = "logistics"):
        saas_service = SaaSControlService(self.db, tenant_id)
        subscription = await saas_service.get_active_subscription(tenant_id)  # type: ignore
        if not subscription:
            raise PermissionDeniedError("No active subscription found.")
        if not subscription.plan:
            raise PermissionDeniedError("No valid subscription plan found.")
        features = subscription.plan.features or []
        if feature not in features:
            raise PermissionDeniedError("Logistics feature is not included in your current plan.")
        return subscription, features

    async def _get_user(self, user_id: int) -> Optional[User]:
        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)
        return await user_repo.get_by_id(user_id)

    async def _get_user_email(self, user_id: int) -> str:
        user = await self._get_user(user_id)
        return user.email if user else f"user_{user_id}@eppne.com"  # type: ignore

    # ============================================================
    # دوال Idempotency الموحّدة
    # ============================================================

    async def _validate_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """التحقق من وجود نتيجة مخزنة مسبقاً لمفتاح Idempotency."""
        if idempotency_key:
            cached = await get_idempotency_result(idempotency_key)
            if cached is not None:
                return cached
        return None

    async def _store_idempotency(self, idempotency_key: str, result: Dict[str, Any]):
        """تخزين نتيجة العملية بعد النجاح."""
        if idempotency_key:
            await store_idempotency_result(idempotency_key, result)

    # ============================================================
    # 1. إدارة المخازن
    # ============================================================

    async def create_warehouse(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> Warehouse:
        await self._check_saas_limits(tenant_id, "logistics")
        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)
        sanitized_location = bleach.clean(data.get("location", ""), tags=[], strip=True)

        async with self.db.begin_nested():
            warehouse = await self.repo.create_warehouse(
                tenant_id=tenant_id,  # type: ignore
                created_by=user_id,
                name=sanitized_name,
                warehouse_type=data["warehouse_type"],
                location=sanitized_location,
                gps_location=data.get("gps_location"),
                total_capacity_sqm=data["total_capacity_sqm"],
                total_capacity_units=data["total_capacity_units"],
                manager_id=data.get("manager_id")
            )

        await self.db.commit()

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="WAREHOUSE_CREATED",
            resource_id=warehouse.id,  # type: ignore
            details={"name": warehouse.name}
        )

        await self.event_bus.publish("logistics.warehouse.created", {
            "warehouse_id": warehouse.id,
            "tenant_id": tenant_id,
            "name": warehouse.name
        })

        return warehouse

    async def list_warehouses(
        self,
        tenant_id: int,
        warehouse_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Warehouse]:
        return await self.repo.list_warehouses(tenant_id, warehouse_type, is_active, skip, limit)

    async def get_warehouse(self, warehouse_id: int, tenant_id: int) -> Optional[Warehouse]:
        return await self.repo.get_warehouse(warehouse_id, tenant_id)

    async def update_warehouse(
        self,
        warehouse_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> Warehouse:
        warehouse = await self.repo.get_warehouse(warehouse_id, tenant_id)
        if not warehouse:
            raise NotFoundError("Warehouse not found")
        return await self.repo.update_warehouse(warehouse_id, tenant_id, **data)

    async def delete_warehouse(self, warehouse_id: int, tenant_id: int) -> None:
        warehouse = await self.repo.get_warehouse(warehouse_id, tenant_id)
        if not warehouse:
            raise NotFoundError("Warehouse not found")
        await self.repo.delete_warehouse(warehouse_id, tenant_id)

    async def create_warehouse_zone(
        self,
        tenant_id: int,
        warehouse_id: int,
        data: Dict[str, Any]
    ) -> WarehouseZone:
        async with self.db.begin_nested():
            zone = await self.repo.create_zone(
                tenant_id=tenant_id,  # type: ignore
                warehouse_id=warehouse_id,
                **data
            )
        await self.db.commit()
        return zone

    # ============================================================
    # 2. إدارة المخزون – استلام المخزون (مع Idempotency محسّن)
    # ============================================================

    async def receive_inventory(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> InventoryTransaction:
        await self._check_saas_limits(tenant_id, "logistics")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                transaction_id = cached.get("transaction_id")
                if transaction_id:
                    # استرجاع المعاملة من قاعدة البيانات
                    transaction = await self.repo.get_transaction(transaction_id, tenant_id)
                    if transaction:
                        return transaction
                raise ValidationError("Idempotency record exists but transaction not found.")

        warehouse = await self.repo.get_warehouse(data["warehouse_id"], tenant_id)
        if not warehouse:
            raise NotFoundError("Warehouse not found")

        if warehouse.used_capacity_units + data["quantity"] > warehouse.total_capacity_units:  # type: ignore
            raise PermissionDeniedError("Insufficient warehouse capacity")

        async with self.db.begin_nested():
            inventory_item = await self.repo.create_inventory_item(
                tenant_id=tenant_id,  # type: ignore
                warehouse_id=data["warehouse_id"],
                zone_id=data.get("zone_id"),
                product_id=data.get("product_id"),
                product_name=data.get("product_name"),
                product_sku=data.get("product_sku"),
                product_category=data.get("product_category"),
                quantity=data["quantity"],
                unit=data.get("unit", "UNIT"),
                unit_price_mrusdt=data.get("unit_price_mrusdt", Decimal(0)),
                batch_number=data.get("batch_number"),
                manufacture_date=data.get("manufacture_date"),
                expiry_date=data.get("expiry_date"),
                supplier_id=data.get("supplier_id"),
                source_order_id=data.get("source_order_id"),
                idempotency_key=idempotency_key
            )

            await self.repo.update_warehouse_usage(cast(int, warehouse.id), tenant_id, data["quantity"], "add")

            transaction = await self.repo.create_transaction(
                tenant_id=tenant_id,  # type: ignore
                inventory_item_id=cast(int, inventory_item.id),
                transaction_type=TransactionType.RECEIVE,
                quantity=data["quantity"],
                destination_warehouse_id=data["warehouse_id"],
                reference_type=data.get("reference_type"),
                reference_id=data.get("reference_id"),
                notes=f"Received {data['quantity']} units of {data['product_name']}",
                performed_by=user_id,
                idempotency_key=idempotency_key
            )

        await self.db.commit()

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="INVENTORY_RECEIVED",
            resource_id=inventory_item.id,  # type: ignore
            details={"product": data["product_name"], "quantity": data["quantity"]}
        )

        await self.event_bus.publish("logistics.inventory.received", {
            "inventory_id": inventory_item.id,
            "warehouse_id": warehouse.id,
            "quantity": data["quantity"],
            "product": data["product_name"]
        })

        # تخزين معرف المعاملة فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"transaction_id": transaction.id})

        return transaction

    # ============================================================
    # 2.1 صرف المخزون (مع Idempotency محسّن)
    # ============================================================

    async def issue_inventory(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> InventoryTransaction:
        await self._check_saas_limits(tenant_id, "logistics")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                transaction_id = cached.get("transaction_id")
                if transaction_id:
                    transaction = await self.repo.get_transaction(transaction_id, tenant_id)
                    if transaction:
                        return transaction
                raise ValidationError("Idempotency record exists but transaction not found.")

        inventory_item = await self.repo.get_inventory_item(data["inventory_item_id"], tenant_id)
        if not inventory_item:
            raise NotFoundError("Inventory item not found")

        if inventory_item.quantity < data["quantity"]:  # type: ignore
            raise InsufficientBalanceError("Insufficient inventory quantity")

        async with self.db.begin_nested():
            new_quantity = inventory_item.quantity - data["quantity"]  # type: ignore
            await self.repo.update_inventory_item(
                cast(int, inventory_item.id),
                tenant_id,
                quantity=new_quantity
            )

            await self.repo.update_warehouse_usage(
                cast(int, inventory_item.warehouse_id),
                tenant_id,
                data["quantity"],
                "subtract"
            )

            transaction = await self.repo.create_transaction(
                tenant_id=tenant_id,  # type: ignore
                inventory_item_id=cast(int, inventory_item.id),
                transaction_type=TransactionType.ISSUE,
                quantity=data["quantity"],
                source_warehouse_id=inventory_item.warehouse_id,
                destination_warehouse_id=data.get("destination_warehouse_id"),
                reference_type=data.get("reference_type"),
                reference_id=data.get("reference_id"),
                notes=f"Issued {data['quantity']} units of {inventory_item.product_name}",
                performed_by=user_id,
                idempotency_key=idempotency_key
            )

        await self.db.commit()

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="INVENTORY_ISSUED",
            resource_id=inventory_item.id,  # type: ignore
            details={"product": inventory_item.product_name, "quantity": data["quantity"]}
        )

        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"transaction_id": transaction.id})

        return transaction

    # ============================================================
    # 2.2 تعديل المخزون (مع Idempotency محسّن)
    # ============================================================

    async def adjust_inventory(
        self,
        user_id: int,
        tenant_id: int,
        inventory_item_id: int,
        new_quantity: int,
        note: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> InventoryTransaction:
        await self._check_saas_limits(tenant_id, "logistics")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                transaction_id = cached.get("transaction_id")
                if transaction_id:
                    transaction = await self.repo.get_transaction(transaction_id, tenant_id)
                    if transaction:
                        return transaction
                raise ValidationError("Idempotency record exists but transaction not found.")

        inventory_item = await self.repo.get_inventory_item(inventory_item_id, tenant_id)
        if not inventory_item:
            raise NotFoundError("Inventory item not found")

        old_quantity = cast(int, inventory_item.quantity)
        diff = new_quantity - old_quantity

        async with self.db.begin_nested():
            await self.repo.update_inventory_item(
                cast(int, inventory_item.id),
                tenant_id,
                quantity=new_quantity
            )

            if diff != 0:
                await self.repo.update_warehouse_usage(
                    cast(int, inventory_item.warehouse_id),
                    tenant_id,
                    abs(diff),
                    "add" if diff > 0 else "subtract"
                )

            transaction = await self.repo.create_transaction(
                tenant_id=tenant_id,  # type: ignore
                inventory_item_id=cast(int, inventory_item.id),
                transaction_type=TransactionType.ADJUSTMENT,
                quantity=abs(diff),
                notes=f"Stock adjustment: {note or 'Inventory count'} (old: {old_quantity}, new: {new_quantity})",
                performed_by=user_id,
                idempotency_key=idempotency_key
            )

        await self.db.commit()

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="INVENTORY_ADJUSTED",
            resource_id=inventory_item.id,  # type: ignore
            details={"product": inventory_item.product_name, "old": old_quantity, "new": new_quantity}
        )

        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"transaction_id": transaction.id})

        return transaction

    async def list_inventory(
        self,
        tenant_id: int,
        warehouse_id: Optional[int] = None,
        status: Optional[InventoryStatus] = None,
        product_category: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[InventoryItem]:
        return await self.repo.list_inventory(tenant_id, warehouse_id, status, product_category, skip, limit)

    async def get_inventory_item(self, inventory_item_id: int, tenant_id: int) -> Optional[InventoryItem]:
        return await self.repo.get_inventory_item(inventory_item_id, tenant_id)

    async def get_low_stock_items(self, tenant_id: int, warehouse_id: Optional[int] = None) -> List[InventoryItem]:
        return await self.repo.get_low_stock_items(tenant_id, warehouse_id)

    async def get_expired_items(self, tenant_id: int) -> List[InventoryItem]:
        return await self.repo.get_expired_items(tenant_id)

    async def get_inventory_transactions(
        self,
        tenant_id: int,
        inventory_item_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[InventoryTransaction]:
        return await self.repo.list_transactions(tenant_id, inventory_item_id=inventory_item_id, skip=skip, limit=limit)

    # ============================================================
    # 3. إدارة المعدات
    # ============================================================

    async def create_equipment(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> Equipment:
        await self._check_saas_limits(tenant_id, "logistics")

        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)
        sanitized_serial = bleach.clean(data.get("serial_number", ""), tags=[], strip=True)

        async with self.db.begin_nested():
            equipment = await self.repo.create_equipment(
                tenant_id=tenant_id,  # type: ignore
                created_by=user_id,
                name=sanitized_name,
                equipment_type=data["equipment_type"],
                serial_number=sanitized_serial,
                manufacturer=data.get("manufacturer"),
                model=data.get("model"),
                warehouse_id=data.get("warehouse_id"),
                current_location=data.get("current_location"),
                purchase_date=data.get("purchase_date"),
                purchase_price_mrusdt=data.get("purchase_price_mrusdt", Decimal(0)),
                warranty_expiry=data.get("warranty_expiry"),
                status=EquipmentStatus.AVAILABLE,
                smart_asset_id=data.get("smart_asset_id")
            )

        await self.db.commit()

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="EQUIPMENT_CREATED",
            resource_id=equipment.id,  # type: ignore
            details={"name": equipment.name}
        )

        return equipment

    async def list_equipment(
        self,
        tenant_id: int,
        equipment_type: Optional[str] = None,
        status: Optional[EquipmentStatus] = None,
        warehouse_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Equipment]:
        return await self.repo.list_equipment(tenant_id, equipment_type, status, warehouse_id, skip, limit)

    async def get_equipment(self, equipment_id: int, tenant_id: int) -> Optional[Equipment]:
        return await self.repo.get_equipment(equipment_id, tenant_id)

    async def update_equipment(
        self,
        equipment_id: int,
        tenant_id: int,
        data: Dict[str, Any]
    ) -> Equipment:
        equipment = await self.repo.get_equipment(equipment_id, tenant_id)
        if not equipment:
            raise NotFoundError("Equipment not found")
        return await self.repo.update_equipment(equipment_id, tenant_id, **data)

    async def create_equipment_maintenance(
        self,
        tenant_id: int,
        equipment_id: int,
        data: Dict[str, Any]
    ) -> EquipmentMaintenance:
        async with self.db.begin_nested():
            maintenance = await self.repo.create_maintenance(
                tenant_id=tenant_id,  # type: ignore
                equipment_id=equipment_id,
                **data
            )
        await self.db.commit()
        return maintenance

    # ============================================================
    # 4. التنبؤ بالطلب (Forecasting) – مع Idempotency محسّن
    # ============================================================

    async def generate_forecast(
        self,
        user_id: int,
        tenant_id: int,
        product_id: int,
        period: str = "MONTHLY",
        idempotency_key: Optional[str] = None
    ) -> InventoryForecast:
        await self._check_saas_limits(tenant_id, "logistics")

        # 1. التحقق من Idempotency
        if idempotency_key:
            cached = await self._validate_idempotency(idempotency_key)
            if cached is not None:
                forecast_id = cached.get("forecast_id")
                if forecast_id:
                    forecast = await self.repo.get_forecast(forecast_id, tenant_id)
                    if forecast:
                        return forecast
                raise ValidationError("Idempotency record exists but forecast not found.")

        inventory_history = await self.repo.get_inventory_history(tenant_id, product_id, days=90)

        from app.domains.ai_governance.service import AIGovernanceService
        governance = AIGovernanceService(self.db, tenant_id)
        await governance.check_and_consume(
            agent_id=13,
            user_id=user_id,
            action_type="LOGISTICS_FORECAST",
            tokens=200,
            cost=Decimal("0.02")
        )

        prediction: Dict[str, Any] = {}
        ai_service = AIAgentsService(self.db, tenant_id)
        try:
            ai_result = await ai_service.execute_agent_action(
                agent_id=13,
                tenant_id=tenant_id,  # type: ignore
                action_type="ANALYZE_SENSOR",
                payload={
                    "product_id": product_id,
                    "history": inventory_history,
                    "period": period
                },
                executor_user_id=user_id,
                idempotency_key=idempotency_key or ""
            )

            prediction = ai_result.get("result", {}).get("prediction", {})
            predicted_demand = prediction.get("demand", 100)
            confidence = prediction.get("confidence", 85)
            seasonality = prediction.get("seasonality", 1.0)
            trend = prediction.get("trend", 1.0)
            external = prediction.get("external_factors", {})

        except Exception as e:
            logger.error(f"AI forecast failed: {e}")
            predicted_demand = 100
            confidence = 50
            seasonality = 1.0
            trend = 1.0
            external = {}

        async with self.db.begin_nested():
            forecast = await self.repo.create_forecast(
                tenant_id=tenant_id,  # type: ignore
                product_id=product_id,
                forecast_period=period,
                forecast_date=datetime.utcnow() + timedelta(days=30),
                predicted_demand=predicted_demand,
                confidence_score=confidence,
                seasonality_factor=seasonality,
                trend_factor=trend,
                external_factors=external,
                ai_agent_id=13
            )

        await self.db.commit()

        # تخزين معرف التوقع فقط
        if idempotency_key:
            await self._store_idempotency(idempotency_key, {"forecast_id": forecast.id})

        return forecast

    async def list_forecasts(
        self,
        tenant_id: int,
        product_id: Optional[int] = None,
        period: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[InventoryForecast]:
        return await self.repo.list_forecasts(tenant_id, product_id, period, skip, limit)

    # ============================================================
    # 5. إحصائيات سريعة
    # ============================================================

    async def get_logistics_stats(self, tenant_id: int) -> dict:
        warehouses = await self.repo.list_warehouses(tenant_id)
        inventory = await self.repo.list_inventory(tenant_id)
        equipment = await self.repo.list_equipment(tenant_id)
        low_stock = await self.repo.get_low_stock_items(tenant_id)
        expired = await self.repo.get_expired_items(tenant_id)

        total_quantity = sum(item.quantity for item in inventory)  # type: ignore
        total_value = sum(item.quantity * item.unit_price_mrusdt for item in inventory)  # type: ignore

        return {
            "total_warehouses": len(warehouses),
            "active_warehouses": len([w for w in warehouses if cast(Any, w.is_active)]),
            "total_inventory_items": len(inventory),
            "total_quantity": total_quantity,
            "total_value_mrusdt": total_value,
            "low_stock_items": len(low_stock),
            "expired_items": len(expired),
            "total_equipment": len(equipment),
            "available_equipment": len([e for e in equipment if cast(Any, e.status) == EquipmentStatus.AVAILABLE])
        }