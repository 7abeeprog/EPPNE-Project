// types/iot.ts
export type AssetClass = 'SURVEILLANCE' | 'SMART_BIO_UNIT' | 'ACCESS_GATE' | 'HVAC' | 'UTILITY_METER' | 'INDUSTRIAL_ROBOT';
export type DeviceHealth = 'EXCELLENT' | 'GOOD' | 'NEEDS_MAINTENANCE' | 'OFFLINE' | 'CRITICAL_FAILURE';
export type UtilityType = 'ELECTRICITY' | 'WATER' | 'BIOGAS' | 'CARBON_CREDIT';
export type GridStationType = 'ELECTRICAL_POWER' | 'WATER_TREATMENT' | 'SEWAGE_AND_WASTE' | 'FUEL_AND_GAS' | 'SMART_BIO_PLANT';

export interface SmartAsset {
  id: number;
  asset_code: string;
  asset_class: AssetClass;
  owner_id: number | null;
  location_gps: { lat: number; lng: number } | null;
  specs: Record<string, any>;
  is_online: boolean;
  health_status: DeviceHealth;
  iot_wallet_address: string | null;
  created_at: string;
}

export interface UtilityReading {
  id: number;
  asset_id: number | null;
  grid_id: number | null;
  reading_type: UtilityType;
  reading_timestamp: string;
  consumed_value: number;
  produced_value: number;
  carbon_emissions_mt: number;
  carbon_credits_generated: number;
  is_settled_on_chain: boolean;
}

export interface MaintenanceLog {
  id: number;
  asset_id: number | null;
  grid_id: number | null;
  technician_id: number | null;
  maintenance_type: string;
  task_description: string;
  cost_mrusdt: number;
  time_credits_spent: number;
  is_resolved: boolean;
  resolution_date: string | null;
  created_at: string;
}

export interface CarbonSettlementResponse {
  status: string;
  total_credits_settled: number;
  monetary_value_added_mrusdt: number;
  readings_processed: number;
}