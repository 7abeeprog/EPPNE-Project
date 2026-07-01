// services/logistics.ts
import api from '@/lib/axios';
import type {
  Warehouse,
  WarehouseZone,
  InventoryItem,
  InventoryTransaction,
  Equipment,
  EquipmentMaintenance,
  InventoryForecast,
  LogisticsStats,
  WarehouseType,
  InventoryStatus,
  EquipmentStatus,
  TransactionType,
  WarehouseFormData,
  InventoryItemFormData,
  EquipmentFormData,
} from '@/types/logistics';

// ========== Warehouses ==========
export const getWarehouses = (params?: { warehouse_type?: WarehouseType; is_active?: boolean; skip?: number; limit?: number }) =>
  api.get<Warehouse[]>('/logistics/warehouses', { params });

export const getWarehouse = (id: number) => api.get<Warehouse>(`/logistics/warehouses/${id}`);

export const createWarehouse = (data: WarehouseFormData) =>
  api.post<Warehouse>('/logistics/warehouses', data);

export const updateWarehouse = (id: number, data: Partial<WarehouseFormData & { is_active: boolean }>) =>
  api.put<Warehouse>(`/logistics/warehouses/${id}`, data);

export const deleteWarehouse = (id: number) => api.delete(`/logistics/warehouses/${id}`);

export const createWarehouseZone = (warehouseId: number, data: { zone_code: string; zone_type: string; capacity_units: number }) =>
  api.post<WarehouseZone>(`/logistics/warehouses/${warehouseId}/zones`, data);

// ========== Inventory ==========
export const getInventory = (params?: { warehouse_id?: number; status?: InventoryStatus; product_category?: string; skip?: number; limit?: number }) =>
  api.get<InventoryItem[]>('/logistics/inventory', { params });

export const getInventoryItem = (id: number) => api.get<InventoryItem>(`/logistics/inventory/${id}`);

export const getInventoryTransactions = (itemId: number, params?: { skip?: number; limit?: number }) =>
  api.get<InventoryTransaction[]>(`/logistics/inventory/${itemId}/transactions`, { params });

export const receiveInventory = (
  data: {
    warehouse_id: number;
    zone_id?: number;
    product_id?: number;
    product_name: string;
    product_sku?: string;
    product_category?: string;
    quantity: number;
    unit?: string;
    unit_price_mrusdt?: number;
    batch_number?: string;
    manufacture_date?: string;
    expiry_date?: string;
    supplier_id?: number;
    source_order_id?: number;
  },
  idempotencyKey?: string
) =>
  api.post<InventoryTransaction>('/logistics/inventory/receive', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const issueInventory = (
  data: { inventory_item_id: number; quantity: number; destination_warehouse_id?: number },
  idempotencyKey?: string
) =>
  api.post<InventoryTransaction>('/logistics/inventory/issue', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const adjustInventory = (
  itemId: number,
  data: { new_quantity: number; note?: string },
  idempotencyKey?: string
) =>
  api.post<InventoryTransaction>(`/logistics/inventory/adjust/${itemId}`, data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const getLowStock = (params?: { warehouse_id?: number }) =>
  api.get<InventoryItem[]>('/logistics/inventory/low-stock', { params });

export const getExpired = () => api.get<InventoryItem[]>('/logistics/inventory/expired');

// ========== Equipment ==========
export const getEquipment = (params?: { equipment_type?: string; status?: EquipmentStatus; warehouse_id?: number; skip?: number; limit?: number }) =>
  api.get<Equipment[]>('/logistics/equipment', { params });

export const getEquipmentItem = (id: number) => api.get<Equipment>(`/logistics/equipment/${id}`);

export const createEquipment = (data: EquipmentFormData) =>
  api.post<Equipment>('/logistics/equipment', data);

export const updateEquipment = (id: number, data: Partial<EquipmentFormData & { status: EquipmentStatus }>) =>
  api.put<Equipment>(`/logistics/equipment/${id}`, data);

export const createMaintenance = (
  equipmentId: number,
  data: { maintenance_type: string; description: string; cost_mrusdt?: number; scheduled_date?: string }
) => api.post<EquipmentMaintenance>(`/logistics/equipment/${equipmentId}/maintenance`, data);

// ========== Forecasting ==========
export const generateForecast = (productId: number, period?: string, idempotencyKey?: string) =>
  api.post<InventoryForecast>(
    `/logistics/forecast?product_id=${productId}&period=${period || 'MONTHLY'}`,
    {},
    { headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {} }
  );

export const getForecasts = (params?: { product_id?: number; period?: string; skip?: number; limit?: number }) =>
  api.get<InventoryForecast[]>('/logistics/forecast', { params });

// ========== Stats ==========
export const getLogisticsStats = () => api.get<LogisticsStats>('/logistics/stats');