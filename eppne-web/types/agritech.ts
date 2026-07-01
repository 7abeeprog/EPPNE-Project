// types/agritech.ts
export type FarmType =
  | 'TRADITIONAL_SOIL'
  | 'HYDROPONICS'
  | 'AEROPONICS'
  | 'VERTICAL_FARM'
  | 'AQUAPONICS'
  | 'LIVESTOCK_FARM'
  | 'POULTRY_FARM'
  | 'FISH_FARM'
  | 'VERMICULTURE_FARM'
  | 'ALGAE_FARM';

export type CropCategory =
  | 'VEGETABLES'
  | 'FRUITS'
  | 'GRAINS'
  | 'LEGUMES'
  | 'MEDICINAL_AROMATIC'
  | 'FODDER_CROPS'
  | 'INDUSTRIAL_CROPS'
  | 'ORNAMENTAL_PLANTS'
  | 'TIMBER_TREES';

export type HarvestGrade =
  | 'GRADE_1_EXPORT'
  | 'GRADE_2_LOCAL'
  | 'GRADE_3_PROCESSING'
  | 'GRADE_4_FODDER'
  | 'WASTE_SMART_BIO';

export type BioAssetType =
  | 'LIVESTOCK'
  | 'POULTRY'
  | 'AQUACULTURE'
  | 'VERMICULTURE'
  | 'ALGAE'
  | 'INSECTS';

export type BioProductType =
  | 'MILK'
  | 'EGG'
  | 'MEAT'
  | 'HONEY'
  | 'VERMICOMPOST'
  | 'COMPOST_TEA'
  | 'BIO_WASTE';

export interface SmartFarm {
  id: number;
  land_asset_id: number;
  manager_id: number;
  name: string;
  farm_type: FarmType;
  total_area_acres: number;
  has_insurance: boolean;
  created_at: string;
}

export interface FarmZone {
  id: number;
  farm_id: number;
  zone_code: string;
  zone_type: string;
  area_sqm?: number;
  soil_type?: string;
  irrigation_type?: string;
  smart_asset_id?: number;
  created_at: string;
}

export interface CropCycle {
  id: number;
  zone_id: number;
  crop_name: string;
  category: CropCategory;
  seed_nft_id?: string;
  planting_date: string;
  expected_harvest_date: string;
  expected_yield_kg: number;
  created_at: string;
}

export interface HarvestBatch {
  id: number;
  cycle_id: number;
  harvest_date: string;
  grade: HarvestGrade;
  quantity_kg: number;
  waste_for_smart_bio_kg: number;
  fodder_for_livestock_kg: number;
  destination_facility_id?: number;
  shipment_tracking_number?: string;
  created_at: string;
}

export interface BioAssetCohort {
  id: number;
  zone_id: number;
  bio_type: BioAssetType;
  species_or_breed: string;
  initial_count_or_kg: number;
  current_count_or_kg: number;
  start_date: string;
  health_status: string;
  created_at: string;
}

export interface BioProductYield {
  id: number;
  cohort_id: number;
  product_type: BioProductType;
  quantity_unit: number;
  collection_date: string;
  destination_farm_id?: number;
  waste_for_smart_bio_kg: number;
  created_at: string;
}

export interface SupplyChainStage {
  id: number;
  traceable_type: string;
  traceable_id: number;
  stage_name: string;
  stage_order: number;
  location?: string;
  operator_id?: number;
  timestamp: string;
  blockchain_tx_hash?: string;
  ipfs_evidence_hash?: string;
  created_at: string;
}

export interface TraceabilityQR {
  id: number;
  traceable_type: string;
  traceable_id: number;
  qr_code: string;
  public_url?: string;
  expires_at?: string;
  created_at: string;
}

export interface AgriculturalCertificate {
  id: number;
  certificate_type: string;
  certificate_name: string;
  issuing_body: string;
  certified_entity_type: string;
  certified_entity_id: number;
  issue_date: string;
  expiry_date: string;
  status: 'ACTIVE' | 'EXPIRED' | 'REVOKED';
  certificate_nft_id?: string;
  ipfs_document_hash?: string;
  created_by: number;
  created_at: string;
}

export interface SoilSensorReading {
  id: number;
  zone_id: number;
  sensor_device_id: string;
  moisture_percent?: number;
  temperature_celsius?: number;
  ph_level?: number;
  nitrogen_ppm?: number;
  phosphorus_ppm?: number;
  potassium_ppm?: number;
  recorded_at: string;
  created_at: string;
}

export interface WeatherAlert {
  id: number;
  alert_type: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  location_gps?: { lat: number; lng: number };
  message: string;
  start_time: string;
  end_time?: string;
  affected_farm_ids: number[];
  is_active: boolean;
  created_at: string;
}

// ========== UI Types ==========
export interface AIRecommendation {
  id: string;
  type: 'IRRIGATE' | 'FERTILIZE' | 'HARVEST' | 'MONITOR';
  title: string;
  description: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH';
  farm_id?: number;
  zone_id?: number;
  created_at: string;
}

export interface AgritechStats {
  total_farms: number;
  total_zones: number;
  active_crop_cycles: number;
  total_harvest_kg: number;
  total_bio_assets: number;
  active_alerts: number;
}