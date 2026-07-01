// types/logistics.ts
export type WarehouseType = 'CENTRAL' | 'REGIONAL' | 'RETAIL' | 'COLD_STORAGE' | 'HAZARDOUS' | 'FARM';
export type InventoryStatus = 'AVAILABLE' | 'RESERVED' | 'DAMAGED' | 'EXPIRED' | 'IN_TRANSIT';
export type EquipmentStatus = 'AVAILABLE' | 'IN_USE' | 'MAINTENANCE' | 'DAMAGED' | 'RETIRED';
export type TransactionType = 'RECEIVE' | 'ISSUE' | 'TRANSFER' | 'ADJUSTMENT' | 'RETURN';
export type OrderStatus = 'DRAFT' | 'PENDING' | 'APPROVED' | 'PROCESSING' | 'SHIPPED' | 'DELIVERED' | 'CANCELLED';

export interface Warehouse {
  id: number;
  tenant_id: number;
  entity_id?: number;
  name: string;
  warehouse_type: WarehouseType;
  location: string;
  gps_location?: { lat: number; lng: number };
  total_capacity_sqm: number;
  used_capacity_sqm: number;
  total_capacity_units: number;
  used_capacity_units: number;
  is_active: boolean;
  manager_id?: number;
  manager_name?: string;
  created_by: number;
  created_at: string;
  updated_at: string;
}

export interface WarehouseZone {
  id: number;
  tenant_id: number;
  warehouse_id: number;
  zone_code: string;
  zone_type: string;
  capacity_units: number;
  used_units: number;
  created_at: string;
  updated_at: string;
}

export interface InventoryItem {
  id: number;
  tenant_id: number;
  warehouse_id: number;
  zone_id?: number;
  product_id?: number;
  product_name: string;
  product_sku?: string;
  product_category?: string;
  quantity: number;
  reserved_quantity: number;
  min_stock_threshold: number;
  max_stock_threshold: number;
  unit: string;
  unit_price_mrusdt: number;
  batch_number?: string;
  manufacture_date?: string;
  expiry_date?: string;
  status: InventoryStatus;
  supplier_id?: number;
  source_order_id?: number;
  created_at: string;
  updated_at: string;
}

export interface InventoryTransaction {
  id: number;
  tenant_id: number;
  inventory_item_id: number;
  transaction_type: TransactionType;
  quantity: number;
  source_warehouse_id?: number;
  destination_warehouse_id?: number;
  reference_type?: string;
  reference_id?: number;
  notes?: string;
  performed_by: number;
  performer_name?: string;
  blockchain_tx_hash?: string;
  document_url?: string;
  created_at: string;
}

export interface Equipment {
  id: number;
  tenant_id: number;
  name: string;
  equipment_type: string;
  serial_number?: string;
  manufacturer?: string;
  model?: string;
  warehouse_id?: number;
  warehouse_name?: string;
  current_location?: string;
  purchase_date?: string;
  purchase_price_mrusdt: number;
  warranty_expiry?: string;
  status: EquipmentStatus;
  last_maintenance_date?: string;
  next_maintenance_date?: string;
  smart_asset_id?: number;
  created_by: number;
  created_at: string;
  updated_at: string;
}

export interface EquipmentMaintenance {
  id: number;
  tenant_id: number;
  equipment_id: number;
  equipment_name?: string;
  maintenance_type: string;
  description: string;
  cost_mrusdt: number;
  performed_by?: number;
  performer_name?: string;
  scheduled_date?: string;
  completed_date?: string;
  status: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface InventoryForecast {
  id: number;
  tenant_id: number;
  product_id?: number;
  product_sku?: string;
  forecast_period: string;
  forecast_date: string;
  predicted_demand: number;
  confidence_score: number;
  seasonality_factor: number;
  trend_factor: number;
  external_factors: Record<string, any>;
  ai_agent_id?: number;
  ai_model_version?: string;
  created_at: string;
  updated_at: string;
}

// ========== UI Types ==========
export interface LogisticsStats {
  total_warehouses: number;
  active_warehouses: number;
  total_inventory_items: number;
  total_quantity: number;
  total_value_mrusdt: number;
  low_stock_items: number;
  expired_items: number;
  total_equipment: number;
  available_equipment: number;
}

export interface InventoryItemFormData {
  warehouse_id: number;
  zone_id?: number;
  product_id?: number;
  product_name: string;
  product_sku?: string;
  product_category?: string;
  quantity: number;
  unit: string;
  unit_price_mrusdt: number;
  batch_number?: string;
  manufacture_date?: string;
  expiry_date?: string;
  supplier_id?: number;
}

export interface WarehouseFormData {
  name: string;
  warehouse_type: WarehouseType;
  location: string;
  gps_location?: { lat: number; lng: number };
  total_capacity_sqm: number;
  total_capacity_units: number;
  manager_id?: number;
}

export interface EquipmentFormData {
  name: string;
  equipment_type: string;
  serial_number?: string;
  manufacturer?: string;
  model?: string;
  warehouse_id?: number;
  current_location?: string;
  purchase_date?: string;
  purchase_price_mrusdt: number;
  warranty_expiry?: string;
}