# app/domains/logistics/router.py
"""
مسارات (Endpoints) قطاع اللوجيستيات والمخازن – النسخة الذهبية
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, cast

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser
from app.domains.identity.models import User
from app.domains.logistics.service import LogisticsService
from app.domains.logistics.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/logistics", tags=["Sovereign Logistics & Warehousing"])


# ============================================================
# 1. المخازن (Warehouses)
# ============================================================

@router.post("/warehouses", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_warehouse(
    data: WarehouseCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    warehouse = await service.create_warehouse(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return warehouse


@router.get("/warehouses", response_model=List[WarehouseResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_warehouses(
    warehouse_type: Optional[WarehouseType] = Query(None, description="نوع المخزن"),
    is_active: Optional[bool] = Query(None, description="هل المخزن نشط؟"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    warehouses = await service.list_warehouses(
        tenant_id=cast(int, tenant.id),
        warehouse_type=warehouse_type,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    return warehouses


@router.get("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
@rate_limit(max_requests=50, window_seconds=60)
async def get_warehouse(
    warehouse_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    warehouse = await service.get_warehouse(
        warehouse_id=warehouse_id,
        tenant_id=cast(int, tenant.id)
    )
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return warehouse


@router.put("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_warehouse(
    warehouse_id: int,
    data: WarehouseUpdate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    warehouse = await service.update_warehouse(
        warehouse_id=warehouse_id,
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(exclude_unset=True)
    )
    return warehouse


@router.delete("/warehouses/{warehouse_id}")
@rate_limit(max_requests=5, window_seconds=60)
async def delete_warehouse(
    warehouse_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    await service.delete_warehouse(
        warehouse_id=warehouse_id,
        tenant_id=cast(int, tenant.id)
    )
    return {"message": "Warehouse deleted"}


@router.post("/warehouses/{warehouse_id}/zones", response_model=WarehouseZoneResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=20, window_seconds=60)
async def create_warehouse_zone(
    warehouse_id: int,
    data: WarehouseZoneCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    zone = await service.create_warehouse_zone(
        tenant_id=cast(int, tenant.id),
        warehouse_id=warehouse_id,
        data=data.model_dump()
    )
    return zone


# ============================================================
# 2. المخزون (Inventory)
# ============================================================

@router.post("/inventory/receive", response_model=InventoryTransactionResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=30, window_seconds=60)
async def receive_inventory(
    data: InventoryReceive,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    transaction = await service.receive_inventory(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return transaction


@router.post("/inventory/issue", response_model=InventoryTransactionResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=30, window_seconds=60)
async def issue_inventory(
    data: InventoryIssue,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    transaction = await service.issue_inventory(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(),
        idempotency_key=idempotency_key
    )
    return transaction


@router.post("/inventory/adjust/{inventory_item_id}", response_model=InventoryTransactionResponse)
@rate_limit(max_requests=20, window_seconds=60)
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
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        inventory_item_id=inventory_item_id,
        new_quantity=data.new_quantity,
        note=data.note,
        idempotency_key=idempotency_key
    )
    return transaction


@router.get("/inventory", response_model=List[InventoryItemResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_inventory(
    warehouse_id: Optional[int] = Query(None, description="معرف المخزن"),
    status: Optional[InventoryStatus] = Query(None, description="حالة المخزون"),
    product_category: Optional[str] = Query(None, description="تصنيف المنتج"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    items = await service.list_inventory(
        tenant_id=cast(int, tenant.id),
        warehouse_id=warehouse_id,
        status=status,
        product_category=product_category,
        skip=skip,
        limit=limit
    )
    return items


@router.get("/inventory/low-stock", response_model=List[InventoryItemResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def get_low_stock(
    warehouse_id: Optional[int] = Query(None, description="معرف المخزن"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    items = await service.get_low_stock_items(
        tenant_id=cast(int, tenant.id),
        warehouse_id=warehouse_id
    )
    return items


@router.get("/inventory/expired", response_model=List[InventoryItemResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def get_expired(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    items = await service.get_expired_items(tenant_id=cast(int, tenant.id))
    return items


@router.get("/inventory/{item_id}", response_model=InventoryItemResponse)
@rate_limit(max_requests=50, window_seconds=60)
async def get_inventory_item(
    item_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    item = await service.get_inventory_item(
        inventory_item_id=item_id,
        tenant_id=cast(int, tenant.id)
    )
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@router.get("/inventory/{item_id}/transactions", response_model=List[InventoryTransactionResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def get_inventory_transactions(
    item_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    transactions = await service.get_inventory_transactions(
        tenant_id=cast(int, tenant.id),
        inventory_item_id=item_id,
        skip=skip,
        limit=limit
    )
    return transactions


# ============================================================
# 3. المعدات (Equipment)
# ============================================================

@router.post("/equipment", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_equipment(
    data: EquipmentCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    equipment = await service.create_equipment(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return equipment


@router.get("/equipment", response_model=List[EquipmentResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_equipment(
    equipment_type: Optional[str] = Query(None, description="نوع المعدة"),
    status: Optional[EquipmentStatus] = Query(None, description="حالة المعدة"),
    warehouse_id: Optional[int] = Query(None, description="معرف المخزن"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    equipment = await service.list_equipment(
        tenant_id=cast(int, tenant.id),
        equipment_type=equipment_type,
        status=status,
        warehouse_id=warehouse_id,
        skip=skip,
        limit=limit
    )
    return equipment


@router.get("/equipment/{equipment_id}", response_model=EquipmentResponse)
@rate_limit(max_requests=50, window_seconds=60)
async def get_equipment(
    equipment_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    equip = await service.get_equipment(
        equipment_id=equipment_id,
        tenant_id=cast(int, tenant.id)
    )
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return equip


@router.put("/equipment/{equipment_id}", response_model=EquipmentResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_equipment(
    equipment_id: int,
    data: EquipmentUpdate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    updated = await service.update_equipment(
        equipment_id=equipment_id,
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(exclude_unset=True)
    )
    return updated


@router.post("/equipment/{equipment_id}/maintenance", response_model=EquipmentMaintenanceResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=15, window_seconds=60)
async def create_maintenance(
    equipment_id: int,
    data: EquipmentMaintenanceCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    maintenance = await service.create_equipment_maintenance(
        tenant_id=cast(int, tenant.id),
        equipment_id=equipment_id,
        data=data.model_dump()
    )
    return maintenance


# ============================================================
# 4. التنبؤ بالطلب (Forecasting)
# ============================================================

@router.post("/forecast", response_model=InventoryForecastResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def generate_forecast(
    product_id: int = Query(..., description="معرف المنتج"),
    period: str = Query("MONTHLY", description="فترة التنبؤ"),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    forecast = await service.generate_forecast(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        product_id=product_id,
        period=period,
        idempotency_key=idempotency_key
    )
    return forecast


@router.get("/forecast", response_model=List[InventoryForecastResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def list_forecasts(
    product_id: Optional[int] = Query(None, description="معرف المنتج"),
    period: Optional[str] = Query(None, description="فترة التنبؤ"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    forecasts = await service.list_forecasts(
        tenant_id=cast(int, tenant.id),
        product_id=product_id,
        period=period,
        skip=skip,
        limit=limit
    )
    return forecasts


# ============================================================
# 5. إحصائيات سريعة
# ============================================================

@router.get("/stats", response_model=LogisticsStatsResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def get_logistics_stats(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = LogisticsService(db)
    stats = await service.get_logistics_stats(tenant_id=cast(int, tenant.id))
    return stats