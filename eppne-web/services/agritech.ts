// services/agritech.ts
import api from '@/lib/axios';
import type {
  SmartFarm,
  FarmZone,
  CropCycle,
  HarvestBatch,
  BioAssetCohort,
  BioProductYield,
  SupplyChainStage,
  TraceabilityQR,
  AgriculturalCertificate,
  SoilSensorReading,
  WeatherAlert,
  AgritechStats,
  FarmType,
  HarvestGrade,
  BioAssetType,
  BioProductType,
  CropCategory,
} from '@/types/agritech';

// ========== Farms ==========
export const getFarms = (params?: { farm_type?: FarmType; skip?: number; limit?: number }) =>
  api.get<SmartFarm[]>('/agritech/farms', { params });

export const getFarm = (id: number) => api.get<SmartFarm>(`/agritech/farms/${id}`);

export const createFarm = (data: {
  land_asset_id: number;
  name: string;
  farm_type: FarmType;
  total_area_acres: number;
  has_insurance?: boolean;
}) => api.post<SmartFarm>('/agritech/farms', data);

export const updateFarm = (id: number, data: Partial<{ name: string; has_insurance: boolean }>) =>
  api.put<SmartFarm>(`/agritech/farms/${id}`, data);

export const deleteFarm = (id: number) => api.delete(`/agritech/farms/${id}`);

// ========== Zones ==========
export const getZones = (farmId: number) => api.get<FarmZone[]>(`/agritech/farms/${farmId}/zones`);

export const createZone = (farmId: number, data: {
  zone_code: string;
  zone_type: string;
  area_sqm?: number;
  soil_type?: string;
  irrigation_type?: string;
  smart_asset_id?: number;
}) => api.post<FarmZone>(`/agritech/farms/${farmId}/zones`, data);

// ========== Crop Cycles ==========
export const startCropCycle = (zoneId: number, data: {
  crop_name: string;
  category: CropCategory;
  seed_nft_id?: string;
  planting_date: string;
  expected_harvest_date: string;
  expected_yield_kg: number;
}) => api.post<CropCycle>(`/agritech/zones/${zoneId}/crop-cycles`, data);

export const getCropCycles = (zoneId: number) => api.get<CropCycle[]>(`/agritech/zones/${zoneId}/crop-cycles`);

// ========== Harvest ==========
export const registerHarvest = (
  cycleId: number,
  data: {
    grade: HarvestGrade;
    quantity_kg: number;
    waste_for_smart_bio_kg?: number;
    fodder_for_livestock_kg?: number;
    destination_facility_id?: number;
  },
  idempotencyKey?: string
) =>
  api.post<HarvestBatch>(`/agritech/crop-cycles/${cycleId}/harvest`, data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const getHarvests = (cycleId: number) => api.get<HarvestBatch[]>(`/agritech/crop-cycles/${cycleId}/harvests`);

// ========== Bio Assets ==========
export const createBioCohort = (zoneId: number, data: {
  bio_type: BioAssetType;
  species_or_breed: string;
  initial_count_or_kg: number;
  start_date: string;
}) => api.post<BioAssetCohort>(`/agritech/zones/${zoneId}/bio-cohorts`, data);

export const getBioCohorts = (zoneId: number) => api.get<BioAssetCohort[]>(`/agritech/zones/${zoneId}/bio-cohorts`);

export const registerBioYield = (
  cohortId: number,
  data: {
    product_type: BioProductType;
    quantity_unit: number;
    collection_date: string;
    destination_farm_id?: number;
    waste_for_smart_bio_kg?: number;
  },
  idempotencyKey?: string
) =>
  api.post<BioProductYield>(`/agritech/bio-cohorts/${cohortId}/yields`, data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

// ========== Traceability ==========
export const addTraceabilityStage = (data: {
  traceable_type: string;
  traceable_id: number;
  stage_name: string;
  stage_order: number;
  location?: string;
  ipfs_evidence_hash?: string;
}) => api.post<SupplyChainStage>('/agritech/traceability/stage', data);

export const getTraceability = (traceableType: string, traceableId: number) =>
  api.get<SupplyChainStage[]>(`/agritech/traceability/${traceableType}/${traceableId}`);

export const generateTraceabilityQR = (traceableType: string, traceableId: number) =>
  api.post<TraceabilityQR>(`/agritech/traceability/qr/${traceableType}/${traceableId}`);

// ========== Certificates ==========
export const issueCertificate = (data: {
  certificate_type: string;
  certificate_name: string;
  issuing_body: string;
  certified_entity_type: string;
  certified_entity_id: number;
  issue_date: string;
  expiry_date: string;
  ipfs_document_hash?: string;
}) => api.post<AgriculturalCertificate>('/agritech/certificates', data);

export const getEntityCertificates = (entityType: string, entityId: number) =>
  api.get<AgriculturalCertificate[]>(`/agritech/certificates/${entityType}/${entityId}`);

// ========== Sensors ==========
export const recordSoilReading = (data: {
  zone_id: number;
  sensor_device_id: string;
  moisture_percent?: number;
  temperature_celsius?: number;
  ph_level?: number;
  nitrogen_ppm?: number;
  phosphorus_ppm?: number;
  potassium_ppm?: number;
  recorded_at: string;
}) => api.post<SoilSensorReading>('/agritech/soil-readings', data);

export const getSoilReadings = (zoneId: number, params?: { limit?: number }) =>
  api.get<SoilSensorReading[]>(`/agritech/soil-readings/${zoneId}`, { params });

// ========== Weather Alerts ==========
export const getWeatherAlerts = () => api.get<WeatherAlert[]>('/agritech/weather-alerts');

// ========== Stats ==========
export const getAgritechStats = () => api.get<AgritechStats>('/agritech/stats');