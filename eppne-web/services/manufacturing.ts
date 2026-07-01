// services/manufacturing.ts
import api from '@/lib/axios';
import type {
  ManufacturingFacility,
  ProductionLine,
  ProductBlueprint,
  ProductionBatch,
  SmartProductItem,
  RawMaterialBatch,
  MaterialConsumptionLog,
  ProductDigitalTwin,
  QualityCertificate,
  PredictiveMaintenanceLog,
  SparePart,
  ManufacturingStats,
  FacilityType,
  ProductionStatus,
  ProductCategory,
  TrackingStatus,
} from '@/types/manufacturing';

// ========== Facilities ==========
export const getFacilities = (params?: { skip?: number; limit?: number }) =>
  api.get<ManufacturingFacility[]>('/manufacturing/facilities', { params });

export const getFacility = (id: number) => api.get<ManufacturingFacility>(`/manufacturing/facilities/${id}`);

export const createFacility = (data: {
  name: string;
  facility_type: FacilityType;
  location_gps?: { lat: number; lng: number };
  real_estate_unit_id?: number;
}) => api.post<ManufacturingFacility>('/manufacturing/facilities', data);

export const updateFacility = (id: number, data: Partial<{ name: string; is_active: boolean }>) =>
  api.put<ManufacturingFacility>(`/manufacturing/facilities/${id}`, data);

export const deleteFacility = (id: number) => api.delete(`/manufacturing/facilities/${id}`);

// ========== Production Lines ==========
export const getProductionLines = (facilityId: number) =>
  api.get<ProductionLine[]>(`/manufacturing/facilities/${facilityId}/lines`);

export const createProductionLine = (
  facilityId: number,
  data: { name: string; hourly_capacity: number; smart_asset_id?: number }
) => api.post<ProductionLine>(`/manufacturing/facilities/${facilityId}/lines`, data);

// ========== Blueprints ==========
export const getBlueprints = (params?: { facility_id?: number; skip?: number; limit?: number }) =>
  api.get<ProductBlueprint[]>('/manufacturing/blueprints', { params });

export const createBlueprint = (data: {
  facility_id: number;
  sku: string;
  name: string;
  product_category: ProductCategory;
  description?: string;
  bill_of_materials: Record<string, any>;
  base_price_mrusdt: number;
  is_perishable?: boolean;
  shelf_life_days?: number;
  warranty_months?: number;
  has_digital_twin?: boolean;
}) => api.post<ProductBlueprint>('/manufacturing/blueprints', data);

// ========== Batches ==========
export const createBatch = (data: {
  product_blueprint_id: number;
  line_id: number;
  batch_number: string;
  source_tracking_number?: string;
  target_quantity: number;
}) => api.post<ProductionBatch>('/manufacturing/batches', data);

export const getBatchItems = (batchId: number) =>
  api.get<SmartProductItem[]>(`/manufacturing/batches/${batchId}/items`);

export const startProduction = (batchId: number, idempotencyKey?: string) =>
  api.post<{ message: string; batch_number: string; items_generated: number; status: string }>(
    `/manufacturing/batches/${batchId}/start`,
    {},
    { headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {} }
  );

// ========== Raw Materials ==========
export const getRawMaterials = (params?: { skip?: number; limit?: number }) =>
  api.get<RawMaterialBatch[]>('/manufacturing/raw-materials', { params });

export const registerRawMaterial = (data: {
  material_name: string;
  supplier_id?: number;
  source_traceability?: string;
  quantity_kg: number;
  unit_price_mrusdt: number;
  received_date: string;
  quality_check_passed?: boolean;
  quality_certificate_hash?: string;
}) => api.post<RawMaterialBatch>('/manufacturing/raw-materials', data);

export const consumeRawMaterial = (
  batchId: number,
  data: { raw_material_batch_id: number; quantity_used_kg: number },
  idempotencyKey?: string
) =>
  api.post<MaterialConsumptionLog>(`/manufacturing/batches/${batchId}/consume-material`, data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

// ========== Digital Twin ==========
export const getDigitalTwin = (productItemId: number) =>
  api.get<ProductDigitalTwin>(`/manufacturing/product-items/${productItemId}/digital-twin`);

export const createDigitalTwin = (
  productItemId: number,
  data: { batch_id: number; production_line_id?: number }
) =>
  api.post<ProductDigitalTwin>(
    `/manufacturing/product-items/${productItemId}/digital-twin`,
    data
  );

// ========== Quality Certificates ==========
export const issueQualityCertificate = (data: {
  certificate_type: string;
  certificate_name: string;
  issuing_body: string;
  certified_entity_type: string;
  certified_entity_id: number;
  issue_date: string;
  expiry_date: string;
  ipfs_document_hash?: string;
}) => api.post<QualityCertificate>('/manufacturing/quality-certificates', data);

export const getEntityCertificates = (entityType: string, entityId: number) =>
  api.get<QualityCertificate[]>(`/manufacturing/quality-certificates/${entityType}/${entityId}`);

// ========== Predictive Maintenance ==========
export const createMaintenanceLog = (data: {
  production_line_id: number;
  sensor_data: Record<string, any>;
  ai_prediction: Record<string, any>;
  recommended_action?: string;
}) => api.post<PredictiveMaintenanceLog>('/manufacturing/predictive-maintenance', data);

export const getPendingMaintenance = (lineId: number) =>
  api.get<PredictiveMaintenanceLog[]>(`/manufacturing/production-lines/${lineId}/pending-maintenance`);

export const scheduleMaintenance = (logId: number, scheduled_at: string) =>
  api.post(`/manufacturing/maintenance/${logId}/schedule`, { scheduled_at });

// ========== Spare Parts ==========
export const getSpareParts = (params?: { skip?: number; limit?: number }) =>
  api.get<SparePart[]>('/manufacturing/spare-parts', { params });

export const createSparePart = (data: {
  part_name: string;
  part_number: string;
  compatible_machines?: number[];
  stock_quantity?: number;
  min_stock_threshold?: number;
  unit_price_mrusdt: number;
  supplier_id?: number;
}) => api.post<SparePart>('/manufacturing/spare-parts', data);

export const restockSparePart = (partId: number, data: { quantity_added: number; unit_price_paid?: number }) =>
  api.post<SparePart>(`/manufacturing/spare-parts/${partId}/restock`, data);

// ========== Stats ==========
export const getManufacturingStats = () => api.get<ManufacturingStats>('/manufacturing/stats');