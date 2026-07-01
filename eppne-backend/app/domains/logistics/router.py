# app/domains/logistics/router.py
"""
مسارات (Endpoints) قطاع اللوجيستيات والمخازن – النسخة الذهبية
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser
from app.domains.identity.models import User
from app.domains.logistics.service import LogisticsService
from app.domains.logistics.repository import LogisticsRepository
from app.domains.logistics.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/logistics", tags=["Sovereign Logistics & Warehousing"])


# ========================================================================
# 1. المخازن (Warehouses)
# ========================================================================

@router.post("/warehouses", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window=60)
async def create_warehouse(
    data: WarehouseCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    warehouse = await service.create_warehouse(current_user.id, tenant.id, data.model_dump())
    return warehouse


@router.get("/warehouses", response_model=List[WarehouseResponse])
@rate_limit(max_requests=30, window=60)
async def list_warehouses(
    warehouse_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = LogisticsRepository(db)
    warehouses = await repo.list_warehouses(tenant.id, warehouse_type, is_active, skip, min(limit, 200))
    return warehouses


@router.get("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
@rate_limit(max_requests=50, window=60)
async def get_warehouse(
    warehouse_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = LogisticsRepository(db)
    warehouse = await repo.get_warehouse(warehouse_id, tenant.id)
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return warehouse


@router.put("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
@rate_limit(max_requests=10, window=60)
async def update_warehouse(
    warehouse_id: int,
    data: WarehouseUpdate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = LogisticsRepository(db)
    warehouse = await repo.get_warehouse(warehouse_id, tenant.id)
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    updated = await repo.update_warehouse(warehouse_id, tenant.id, **data.model_dump(exclude_unset=True))
    return updated


@router.delete("/warehouses/{warehouse_id}")
@rate_limit(max_requests=5, window=60)
async def delete_warehouse(
    warehouse_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = LogisticsRepository(db)
    warehouse = await repo.get_warehouse(warehouse_id, tenant.id)
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    await repo.delete_warehouse(warehouse_id, tenant.id)
    return {"message": "Warehouse deleted"}


@router.post("/warehouses/{warehouse_id}/zones", response_model=WarehouseZoneResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=20, window=60)
async def create_warehouse_zone(
    warehouse_id: int,
    data: WarehouseZoneCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = LogisticsRepository(db)
    zone = await repo.create_zone(
        tenant_id=tenant.id,
        warehouse_id=warehouse_id,
        **data.model_dump()
    )
    return zone


# ========================================================================
# 2. المخزون (Inventory)
# ========================================================================

@router.post("/inventory/receive", response_model=InventoryTransactionResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=30, window=60)
async def receive_inventory(
    data: InventoryReceive,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    transaction = await service.receive_inventory(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return transaction


@router.post("/inventory/issue", response_model=InventoryTransactionResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=30, window=60)
async def issue_inventory(
    data: InventoryIssue,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    transaction = await service.issue_inventory(
        user_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return transaction


@router.post("/inventory/adjust/{inventory_item_id}", response_model=InventoryTransactionResponse)
@rate_limit(max_requests=20, window=60)
async def adjust_inventory(
    inventory_item_id: int,
    data: InventoryAdjust,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    transaction = await service.adjust_inventory(
        user_id=current_user.id,
        tenant_id=tenant.id,
        inventory_item_id=inventory_item_id,
        new_quantity=data.new_quantity,
        note=data.note,
        idempotency_key=idempotency_key
    )
    return transaction


@router.get("/inventory", response_model=List[InventoryItemResponse])
@rate_limit(max_requests=30, window=60)
async def list_inventory(
    warehouse_id: Optional[int] = None,
    status: Optional[InventoryStatus] = None,
    product_category: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = LogisticsRepository(db)
    items = await repo.list_inventory(tenant.id, warehouse_id, status, product_category, skip, min(limit, 200))
    return items


@router.get("/inventory/low-stock", response_model=List[InventoryItemResponse])
@rate_limit(max_requests=20, window=60)
async def get_low_stock(
    warehouse_id: Optional[int] = None,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = LogisticsRepository(db)
    items = await repo.get_low_stock_items(tenant.id, warehouse_id)
    return items


@router.get("/inventory/expired", response_model=List[InventoryItemResponse])
@rate_limit(max_requests=20, window=60)
async def get_expired(
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = LogisticsRepository(db)
    items = await repo.get_expired_items(tenant.id)
    return items


@router.get("/inventory/{item_id}", response_model=InventoryItemResponse)
@rate_limit(max_requests=50, window=60)
async def get_inventory_item(
    item_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = LogisticsRepository(db)
    item = await repo.get_inventory_item(item_id, tenant.id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@router.get("/inventory/{item_id}/transactions", response_model=List[InventoryTransactionResponse])
@rate_limit(max_requests=30, window=60)
async def get_inventory_transactions(
    item_id: int,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = LogisticsRepository(db)
    transactions = await repo.list_transactions(tenant.id, inventory_item_id=item_id, skip=skip, limit=min(limit, 200))
    return transactions


# ========================================================================
# 3. المعدات (Equipment)
# ========================================================================

@router.post("/equipment", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window=60)
async def create_equipment(
    data: EquipmentCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    equipment = await service.create_equipment(current_user.id, tenant.id, data.model_dump())
    return equipment


@router.get("/equipment", response_model=List[EquipmentResponse])
@rate_limit(max_requests=30, window=60)
async def list_equipment(
    equipment_type: Optional[str] = None,
    status: Optional[EquipmentStatus] = None,
    warehouse_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = LogisticsRepository(db)
    equipment = await repo.list_equipment(tenant.id, equipment_type, status, warehouse_id, skip, min(limit, 200))
    return equipment


@router.get("/equipment/{equipment_id}", response_model=EquipmentResponse)
@rate_limit(max_requests=50, window=60)
async def get_equipment(
    equipment_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = LogisticsRepository(db)
    equip = await repo.get_equipment(equipment_id, tenant.id)
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return equip


@router.put("/equipment/{equipment_id}", response_model=EquipmentResponse)
@rate_limit(max_requests=10, window=60)
async def update_equipment(
    equipment_id: int,
    data: EquipmentUpdate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = LogisticsRepository(db)
    equip = await repo.get_equipment(equipment_id, tenant.id)
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found")
    updated = await repo.update_equipment(equipment_id, tenant.id, **data.model_dump(exclude_unset=True))
    return updated


@router.post("/equipment/{equipment_id}/maintenance", response_model=EquipmentMaintenanceResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=15, window=60)
async def create_maintenance(
    equipment_id: int,
    data: EquipmentMaintenanceCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = LogisticsRepository(db)
    maintenance = await repo.create_maintenance(
        tenant_id=tenant.id,
        equipment_id=equipment_id,
        **data.model_dump()
    )
    return maintenance


# ========================================================================
# 4. التنبؤ بالطلب (Forecasting)
# ========================================================================

@router.post("/forecast", response_model=InventoryForecastResponse)
@rate_limit(max_requests=10, window=60)
async def generate_forecast(
    product_id: int,
    period: str = "MONTHLY",
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    forecast = await service.generate_forecast(
        user_id=current_user.id,
        tenant_id=tenant.id,
        product_id=product_id,
        period=period,
        idempotency_key=idempotency_key
    )
    return forecast


@router.get("/forecast", response_model=List[InventoryForecastResponse])
@rate_limit(max_requests=20, window=60)
async def list_forecasts(
    product_id: Optional[int] = None,
    period: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = LogisticsRepository(db)
    forecasts = await repo.list_forecasts(tenant.id, product_id, period, skip, min(limit, 200))
    return forecasts


# ========================================================================
# 5. إحصائيات سريعة
# ========================================================================

@router.get("/stats", response_model=LogisticsStatsResponse)
@rate_limit(max_requests=20, window=60)
async def get_logistics_stats(
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = LogisticsRepository(db)
    warehouses = await repo.list_warehouses(tenant.id)
    inventory = await repo.list_inventory(tenant.id)
    equipment = await repo.list_equipment(tenant.id)
    low_stock = await repo.get_low_stock_items(tenant.id)
    expired = await repo.get_expired_items(tenant.id)

    total_quantity = sum(item.quantity for item in inventory)
    total_value = sum(item.quantity * item.unit_price_mrusdt for item in inventory)

    return {
        "total_warehouses": len(warehouses),
        "active_warehouses": len([w for w in warehouses if w.is_active]),
        "total_inventory_items": len(inventory),
        "total_quantity": total_quantity,
        "total_value_mrusdt": total_value,
        "low_stock_items": len(low_stock),
        "expired_items": len(expired),
        "total_equipment": len(equipment),
        "available_equipment": len([e for e in equipment if e.status == EquipmentStatus.AVAILABLE])
    }