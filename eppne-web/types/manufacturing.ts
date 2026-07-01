// types/manufacturing.ts
export type FacilityType =
  | 'HEAVY_FACTORY'
  | 'ASSEMBLY_LINE'
  | 'BIO_REFINERY'
  | 'FARM_PROCESSING';

export type ProductionStatus =
  | 'PLANNED'
  | 'IN_PROGRESS'
  | 'QC_TESTING'
  | 'COMPLETED'
  | 'REJECTED';

export type ProductCategory =
  | 'FOOD_AND_BEVERAGE'
  | 'AUTOMOTIVE'
  | 'ELECTRONICS'
  | 'ROBOTICS_AI'
  | 'TEXTILES_APPAREL'
  | 'TOYS_AND_GAMES'
  | 'HOME_APPLIANCES'
  | 'OFFICE_SUPPLIES'
  | 'HEAVY_MACHINERY'
  | 'SMART_BIO_UNITS';

export type TrackingStatus = 'IN_FACTORY' | 'IN_TRANSIT' | 'DELIVERED' | 'RECALLED';

export interface ManufacturingFacility {
  id: number;
  tenant_id: number;
  real_estate_unit_id?: number;
  entity_id: number;
  name: string;
  facility_type: FacilityType;
  location_gps?: { lat: number; lng: number };
  manager_id: number;
  safety_compliance_score: number;
  is_active: boolean;
  created_at: string;
}

export interface ProductionLine {
  id: number;
  facility_id: number;
  tenant_id: number;
  name: string;
  hourly_capacity: number;
  is_active: boolean;
  smart_asset_id?: number;
  created_at: string;
}

export interface ProductBlueprint {
  id: number;
  tenant_id: number;
  facility_id: number;
  sku: string;
  name: string;
  product_category: ProductCategory;
  description?: string;
  bill_of_materials: Record<string, any>;
  base_price_mrusdt: number;
  is_perishable: boolean;
  shelf_life_days?: number;
  warranty_months?: number;
  has_digital_twin: boolean;
  created_at: string;
}

export interface ProductionBatch {
  id: number;
  tenant_id: number;
  product_blueprint_id: number;
  line_id: number;
  batch_number: string;
  source_tracking_number?: string;
  target_quantity: number;
  produced_quantity: number;
  status: ProductionStatus;
  quality_control_notes?: string;
  created_at: string;
}

export interface SmartProductItem {
  id: number;
  tenant_id: number;
  batch_id: number;
  serial_number: string;
  smart_barcode: string;
  digital_twin_nft_id?: string;
  item_metadata: Record<string, any>;
  qc_passed?: boolean;
  expiration_date?: string;
  status: TrackingStatus;
  current_location?: string;
  owner_id?: number;
  created_at: string;
}

export interface RawMaterialBatch {
  id: number;
  tenant_id: number;
  material_name: string;
  supplier_id?: number;
  source_traceability?: string;
  quantity_kg: number;
  unit_price_mrusdt: number;
  total_cost_mrusdt: number;
  received_date: string;
  quality_check_passed: boolean;
  quality_certificate_hash?: string;
  batch_number: string;
  blockchain_tx_hash?: string;
  created_at: string;
}

export interface MaterialConsumptionLog {
  id: number;
  batch_id: number;
  raw_material_batch_id: number;
  tenant_id: number;
  quantity_used_kg: number;
  consumed_at: string;
  recorded_by: number;
  blockchain_tx_hash?: string;
}

export interface ProductDigitalTwin {
  id: number;
  tenant_id: number;
  product_item_id: number;
  manufacturing_date: string;
  batch_number: string;
  production_line_id?: number;
  actual_bom: Record<string, any>;
  maintenance_log: Record<string, any>[];
  total_maintenance_cost_mrusdt: number;
  quality_certificates: Record<string, any>[];
  digital_twin_nft_id?: string;
  ipfs_metadata_hash?: string;
  created_at: string;
}

export interface QualityCertificate {
  id: number;
  tenant_id: number;
  certificate_type: string; // ISO9001, CE, FDA, HALAL, ORGANIC
  certificate_name: string;
  issuing_body: string;
  certified_entity_type: string;
  certified_entity_id: number;
  issue_date: string;
  expiry_date: string;
  status: string;
  certificate_nft_id?: string;
  ipfs_document_hash?: string;
  created_by: number;
  created_at: string;
}

export interface PredictiveMaintenanceLog {
  id: number;
  tenant_id: number;
  production_line_id: number;
  sensor_data: Record<string, any>;
  ai_prediction: Record<string, any>;
  recommended_action?: string;
  status: 'PENDING' | 'SCHEDULED' | 'COMPLETED';
  maintenance_scheduled_at?: string;
  maintenance_completed_at?: string;
  created_at: string;
}

export interface SparePart {
  id: number;
  tenant_id: number;
  part_name: string;
  part_number: string;
  compatible_machines: number[];
  stock_quantity: number;
  min_stock_threshold: number;
  unit_price_mrusdt: number;
  supplier_id?: number;
  last_restocked_at?: string;
  created_at: string;
}

// ========== UI Types ==========
export interface ManufacturingStats {
  total_facilities: number;
  total_lines: number;
  active_batches: number;
  total_products_manufactured: number;
  total_material_cost: number;
  pending_maintenance: number;
}

export interface ProductionDashboardData {
  facilities: ManufacturingFacility[];
  active_batches: ProductionBatch[];
  recent_products: SmartProductItem[];
  pending_maintenance: PredictiveMaintenanceLog[];
}