# app/domains/logistics/service.py
"""
خدمات قطاع اللوجيستيات والمخازن – النسخة الذهبية
يدعم: إدارة المخازن، المخزون، المعدات، الحركات، وسلسلة التوريد
"""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
import uuid
import bleach

from app.domains.logistics.repository import LogisticsRepository
from app.domains.ai_agents.service import AIAgentsService
from app.domains.saas.service import SaaSSubscriptionService
from app.domains.affiliate.service import AffiliateService
from app.domains.invoicing.service import InvoicingService
from app.domains.finance.service import FinanceService
from app.core.errors import NotFoundError, PermissionDeniedError, InsufficientBalanceError
from app.core.idempotency import check_idempotency, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging import logger
from app.domains.logistics.models import (
    Warehouse, WarehouseZone, InventoryItem, InventoryTransaction,
    Equipment, EquipmentMaintenance, SupplyChainOrder, SupplyChainOrderItem,
    InventoryForecast, InventoryStatus, EquipmentStatus, OrderStatus, TransactionType
)

class LogisticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = LogisticsRepository(db)
        self.ai_service = AIAgentsService(db)
        self.saas_service = SaaSSubscriptionService(db)
        self.affiliate_service = AffiliateService(db)
        self.invoicing_service = InvoicingService(db)
        self.finance = FinanceService(db)
        self.event_bus = EventBus(redis_client)
        self.redis = redis_client

    # ========== التحقق من صلاحيات SaaS ==========
    async def _check_saas_limits(self, tenant_id: int, feature: str = "logistics"):
        subscription = await self.saas_service.get_active_subscription(tenant_id)
        if not subscription:
            raise PermissionDeniedError("No active subscription found.")
        features = subscription.features or {}
        if not features.get(feature, False):
            raise PermissionDeniedError("Logistics feature is not included in your current plan.")
        return subscription, features

    # ========== 1. إدارة المخازن ==========
    async def create_warehouse(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> Warehouse:
        await self._check_saas_limits(tenant_id, "logistics")
        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)
        sanitized_location = bleach.clean(data.get("location", ""), tags=[], strip=True)

        warehouse = await self.repo.create_warehouse(
            tenant_id=tenant_id,
            created_by=user_id,
            name=sanitized_name,
            warehouse_type=data["warehouse_type"],
            location=sanitized_location,
            gps_location=data.get("gps_location"),
            total_capacity_sqm=data["total_capacity_sqm"],
            total_capacity_units=data["total_capacity_units"],
            manager_id=data.get("manager_id")
        )

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="WAREHOUSE_CREATED",
            resource_id=warehouse.id,
            details={"name": warehouse.name}
        )

        await self.event_bus.publish("logistics.warehouse.created", {
            "warehouse_id": warehouse.id,
            "tenant_id": tenant_id,
            "name": warehouse.name
        })

        return warehouse

    # ========== 2. إدارة المخزون ==========
    async def receive_inventory(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: str = None
    ) -> InventoryTransaction:
        await self._check_saas_limits(tenant_id, "logistics")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # التحقق من وجود المخزن
        warehouse = await self.repo.get_warehouse(data["warehouse_id"], tenant_id)
        if not warehouse:
            raise NotFoundError("Warehouse not found")

        # التحقق من السعة
        if warehouse.used_capacity_units + data["quantity"] > warehouse.total_capacity_units:
            raise PermissionDeniedError("Insufficient warehouse capacity")

        # إنشاء عنصر المخزون
        inventory_item = await self.repo.create_inventory_item(
            tenant_id=tenant_id,
            warehouse_id=data["warehouse_id"],
            zone_id=data.get("zone_id"),
            product_id=data.get("product_id"),
            product_name=data.get("product_name"),
            product_sku=data.get("product_sku"),
            product_category=data.get("product_category"),
            quantity=data["quantity"],
            unit=data.get("unit", "UNIT"),
            unit_price_mrusdt=data.get("unit_price_mrusdt", 0),
            batch_number=data.get("batch_number"),
            manufacture_date=data.get("manufacture_date"),
            expiry_date=data.get("expiry_date"),
            supplier_id=data.get("supplier_id"),
            source_order_id=data.get("source_order_id"),
            idempotency_key=idempotency_key
        )

        # تحديث المساحة المستخدمة في المخزن
        await self.repo.update_warehouse_usage(warehouse.id, tenant_id, data["quantity"], "add")

        # تسجيل الحركة
        transaction = await self.repo.create_transaction(
            tenant_id=tenant_id,
            inventory_item_id=inventory_item.id,
            transaction_type=TransactionType.RECEIVE,
            quantity=data["quantity"],
            destination_warehouse_id=data["warehouse_id"],
            reference_type=data.get("reference_type"),
            reference_id=data.get("reference_id"),
            notes=f"Received {data['quantity']} units of {data['product_name']}",
            performed_by=user_id,
            idempotency_key=idempotency_key
        )

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="INVENTORY_RECEIVED",
            resource_id=inventory_item.id,
            details={"product": data["product_name"], "quantity": data["quantity"]}
        )

        await self.event_bus.publish("logistics.inventory.received", {
            "inventory_id": inventory_item.id,
            "warehouse_id": warehouse.id,
            "quantity": data["quantity"],
            "product": data["product_name"]
        })

        if idempotency_key:
            await store_idempotency_result(idempotency_key, transaction)

        return transaction

    # ========== 3. صرف المخزون ==========
    async def issue_inventory(
        self,
        user_id: int,
        tenant_id: int,
        data: Dict[str, Any],
        idempotency_key: str = None
    ) -> InventoryTransaction:
        await self._check_saas_limits(tenant_id, "logistics")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # البحث عن عنصر المخزون
        inventory_item = await self.repo.get_inventory_item(data["inventory_item_id"], tenant_id)
        if not inventory_item:
            raise NotFoundError("Inventory item not found")

        if inventory_item.quantity < data["quantity"]:
            raise InsufficientBalanceError("Insufficient inventory quantity")

        # تحديث الكمية
        new_quantity = inventory_item.quantity - data["quantity"]
        await self.repo.update_inventory_item(
            inventory_item.id,
            tenant_id,
            quantity=new_quantity
        )

        # تحديث المساحة المستخدمة في المخزن
        await self.repo.update_warehouse_usage(inventory_item.warehouse_id, tenant_id, data["quantity"], "subtract")

        # تسجيل الحركة
        transaction = await self.repo.create_transaction(
            tenant_id=tenant_id,
            inventory_item_id=inventory_item.id,
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

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="INVENTORY_ISSUED",
            resource_id=inventory_item.id,
            details={"product": inventory_item.product_name, "quantity": data["quantity"]}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, transaction)

        return transaction

    # ========== 4. جرد المخزون ==========
    async def adjust_inventory(
        self,
        user_id: int,
        tenant_id: int,
        inventory_item_id: int,
        new_quantity: int,
        note: str = None,
        idempotency_key: str = None
    ) -> InventoryTransaction:
        await self._check_saas_limits(tenant_id, "logistics")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        inventory_item = await self.repo.get_inventory_item(inventory_item_id, tenant_id)
        if not inventory_item:
            raise NotFoundError("Inventory item not found")

        old_quantity = inventory_item.quantity
        diff = new_quantity - old_quantity

        # تحديث الكمية
        await self.repo.update_inventory_item(
            inventory_item.id,
            tenant_id,
            quantity=new_quantity
        )

        # تحديث المساحة المستخدمة في المخزن
        if diff != 0:
            await self.repo.update_warehouse_usage(
                inventory_item.warehouse_id,
                tenant_id,
                abs(diff),
                "add" if diff > 0 else "subtract"
            )

        # تسجيل الحركة
        transaction = await self.repo.create_transaction(
            tenant_id=tenant_id,
            inventory_item_id=inventory_item.id,
            transaction_type=TransactionType.ADJUSTMENT,
            quantity=abs(diff),
            notes=f"Stock adjustment: {note or 'Inventory count'} (old: {old_quantity}, new: {new_quantity})",
            performed_by=user_id,
            idempotency_key=idempotency_key
        )

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="INVENTORY_ADJUSTED",
            resource_id=inventory_item.id,
            details={"product": inventory_item.product_name, "old": old_quantity, "new": new_quantity}
        )

        if idempotency_key:
            await store_idempotency_result(idempotency_key, transaction)

        return transaction

    # ========== 5. إدارة المعدات ==========
    async def create_equipment(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> Equipment:
        await self._check_saas_limits(tenant_id, "logistics")

        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)
        sanitized_serial = bleach.clean(data.get("serial_number", ""), tags=[], strip=True)

        equipment = await self.repo.create_equipment(
            tenant_id=tenant_id,
            created_by=user_id,
            name=sanitized_name,
            equipment_type=data["equipment_type"],
            serial_number=sanitized_serial,
            manufacturer=data.get("manufacturer"),
            model=data.get("model"),
            warehouse_id=data.get("warehouse_id"),
            current_location=data.get("current_location"),
            purchase_date=data.get("purchase_date"),
            purchase_price_mrusdt=data.get("purchase_price_mrusdt", 0),
            warranty_expiry=data.get("warranty_expiry"),
            status=EquipmentStatus.AVAILABLE,
            smart_asset_id=data.get("smart_asset_id")
        )

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="EQUIPMENT_CREATED",
            resource_id=equipment.id,
            details={"name": equipment.name}
        )

        return equipment

    # ========== 6. التنبؤ بالطلب (مع الذكاء الاصطناعي) ==========
    async def generate_forecast(
        self,
        user_id: int,
        tenant_id: int,
        product_id: int,
        period: str = "MONTHLY",
        idempotency_key: str = None
    ) -> InventoryForecast:
        await self._check_saas_limits(tenant_id, "logistics")

        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached

        # جلب بيانات المخزون السابقة
        inventory_history = await self.repo.get_inventory_history(tenant_id, product_id, days=90)

        # 🔥 استدعاء وكيل الذكاء الاصطناعي للتنبؤ
        from app.domains.ai_governance.service import AIGovernanceService
        governance = AIGovernanceService(self.db)
        await governance.check_and_consume(
            tenant_id=tenant_id,
            agent_id=13,  # LOGISTICS_FORECASTER
            user_id=user_id,
            tokens=200,
            cost=Decimal("0.02")
        )

        try:
            ai_result = await self.ai_service.execute_agent_action(
                agent_id=13,
                tenant_id=tenant_id,
                action_type="ANALYZE_SENSOR",
                payload={
                    "product_id": product_id,
                    "history": inventory_history,
                    "period": period
                },
                executor_user_id=user_id
            )

            prediction = ai_result.get("result", {}).get("prediction", {})
            predicted_demand = prediction.get("demand", 100)
            confidence = prediction.get("confidence", 85)
            seasonality = prediction.get("seasonality", 1.0)
            trend = prediction.get("trend", 1.0)
            external = prediction.get("external_factors", {})

        except Exception as e:
            logger.error(f"AI forecast failed: {e}")
            # خيار احتياطي
            predicted_demand = 100
            confidence = 50
            seasonality = 1.0
            trend = 1.0
            external = {}

        forecast = await self.repo.create_forecast(
            tenant_id=tenant_id,
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

        if idempotency_key:
            await store_idempotency_result(idempotency_key, forecast)

        return forecast