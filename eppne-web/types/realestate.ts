// types/realestate.ts (الإصدار النهائي المتكامل مع جميع الإضافات)
export type ZoningCategory = 'RESIDENTIAL' | 'COMMERCIAL' | 'INDUSTRIAL' | 'AGRICULTURAL' | 'LOGISTICS' | 'ENTERTAINMENT' | 'ADMINISTRATIVE';
export type LegalStatus = 'REGISTERED' | 'GOVERNMENT_ALLOCATION' | 'UNDER_LEGALIZATION' | 'USUFRUCT' | 'DISPUTED';
export type ConstructionStatus = 'EMPTY_LAND' | 'EXCAVATION' | 'CONCRETE_STRUCTURE' | 'FINISHING' | 'COMPLETED' | 'SMART_ACTIVE';
export type PropertyType = 'APARTMENT' | 'VILLA' | 'OFFICE' | 'RETAIL' | 'WAREHOUSE' | 'FACTORY' | 'LAND';
export type ContractType = 'SALE' | 'RENTAL' | 'MORTGAGE' | 'LEASE';

export interface LandAsset {
  id: number;
  plot_number: string;
  area_sqm: number;
  gps_polygon: Record<string, any>;
  zoning: ZoningCategory;
  legal_status: LegalStatus;
  current_value_mrusdt: number;
  has_insurance: boolean;
  owner_id: number;
  created_at: string;
}

export interface RealEstateDevelopment {
  id: number;
  land_asset_id: number;
  name: string;
  development_type: string;
  construction_status: ConstructionStatus;
  total_budget_mrusdt: number;
  spent_budget_mrusdt: number;
  completion_percentage: number;
  bim_model_hash?: string;
  created_at: string;
}

export interface PropertyUnit {
  id: number;
  development_id: number;
  unit_number: string;
  floor_number?: number;
  area_sqm: number;
  property_type: PropertyType;
  sale_price_mrusdt?: number;
  rent_per_month_mrusdt?: number;
  smart_asset_id?: number;
  is_available_for_sale: boolean;
  is_available_for_rent: boolean;
  created_at: string;
}

export interface PropertyOwnership {
  id: number;
  unit_id: number;
  owner_user_id: number;
  ownership_percentage: number;
  acquisition_date: string;
  deed_nft_token_id?: string;
  purchase_tx_hash?: string;
  created_at: string;
}

export interface RentalContract {
  id: number;
  unit_id: number;
  tenant_user_id: number;
  landlord_user_id: number;
  start_date: string;
  end_date: string;
  monthly_rent_mrusdt: number;
  status: 'ACTIVE' | 'COMPLETED' | 'TERMINATED';
  contract_tx_hash?: string;
  created_at: string;
}

export interface MasterPlan {
  id: number;
  land_asset_id: number;
  name: string;
  description?: string;
  gis_data?: Record<string, any>;
  bim_model_hash?: string;
  total_units_planned: number;
  total_area_sqm: number;
  created_at: string;
}

export interface AssetTokenization {
  id: number;
  unit_id: number;
  total_shares: number;
  share_price_mrusdt: number;
  minimum_investment_shares: number;
  is_active: boolean;
  is_fully_subscribed: boolean;
  smart_contract_address?: string;
  token_symbol?: string;
  created_at: string;
}

export interface SmartContractEngine {
  id: number;
  contract_type: ContractType;
  reference_id: number;
  blockchain_tx_hash?: string;
  execution_status: 'PENDING' | 'CONFIRMED' | 'FAILED';
  executed_at?: string;
  contract_metadata: Record<string, any>;
  created_at: string;
}

// ========== UI Types ==========
export interface PortfolioSummary {
  total_units_owned: number;
  total_ownership_percentage: number;
  total_value_mrusdt: number;
  monthly_rental_income: number;
  active_rental_contracts: number;
}

export interface TokenizationPurchase {
  unit_id: number;
  shares: number;
  total_cost: number;
}

// ========== إضافات جديدة ==========

/**
 * بيانات تجزئة العقار (مطابقة لـ AssetTokenization مع تحديثات إضافية)
 */
export interface Tokenization {
  id: number;
  unit_id: number;
  total_shares: number;
  share_price_mrusdt: number;
  minimum_investment_shares: number;
  is_active: boolean;
  is_fully_subscribed: boolean;
  smart_contract_address?: string;
  token_symbol?: string;
  created_at: string;
  updated_at: string;
}

/**
 * بيانات ملكية جزئية (مطابقة لـ PropertyOwnership مع إضافة current_value)
 */
export interface Ownership {
  id: number;
  unit_id: number;
  owner_user_id: number;
  ownership_percentage: number;
  acquisition_date: string;
  deed_nft_token_id?: string;
  purchase_tx_hash?: string;
  current_value?: number;  // القيمة الحالية المقدرة للملكية
  created_at: string;
}