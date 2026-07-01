// services/realestate.ts (الإصدار النهائي المتكامل مع جميع الإضافات)
import api from '@/lib/axios';
import type {
  LandAsset,
  RealEstateDevelopment,
  PropertyUnit,
  PropertyOwnership,
  RentalContract,
  MasterPlan,
  AssetTokenization,
  SmartContractEngine,
  PortfolioSummary,
  ContractType,
  SmartContractResponse,
  Property,        // 🔥 جديد
  Ownership,       // 🔥 جديد
  Tokenization,    // 🔥 جديد
} from '@/types/realestate';

// ========== Land Assets ==========
export const getMyLands = (params?: { skip?: number; limit?: number }) =>
  api.get<LandAsset[]>('/realestate/lands/me', { params });

export const createLandAsset = (data: Partial<LandAsset>) =>
  api.post<LandAsset>('/realestate/lands', data);

export const revalueLand = (landId: number, newValue: number) =>
  api.patch<LandAsset>(`/realestate/lands/${landId}/revalue?new_value=${newValue}`);

// ========== Developments ==========
export const getDevelopment = (devId: number) =>
  api.get<RealEstateDevelopment>(`/realestate/developments/${devId}`);

export const createDevelopment = (data: Partial<RealEstateDevelopment>) =>
  api.post<RealEstateDevelopment>('/realestate/developments', data);

// ========== Property Units ==========
export const getUnitsForSale = (params?: { development_id?: number; skip?: number; limit?: number }) =>
  api.get<PropertyUnit[]>('/realestate/units/for-sale', { params });

export const createUnit = (data: Partial<PropertyUnit>) =>
  api.post<PropertyUnit>('/realestate/units', data);

// ========== Ownership ==========
export const buyFractionalOwnership = (
  unitId: number,
  data: { ownership_percentage: number },
  idempotencyKey?: string
) =>
  api.post<PropertyOwnership>(`/realestate/units/${unitId}/buy`, data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const getMyOwnerships = () =>
  api.get<PropertyOwnership[]>('/realestate/my-ownerships');

// ========== Rental ==========
export const createRentalContract = (
  data: {
    unit_id: number;
    tenant_user_id: number;
    start_date: string;
    end_date: string;
    monthly_rent_mrusdt: number;
  },
  idempotencyKey?: string
) =>
  api.post<RentalContract>('/realestate/rentals', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

// ========== Master Plans ==========
export const createMasterPlan = (data: Partial<MasterPlan>) =>
  api.post<MasterPlan>('/realestate/master-plans', data);

// ========== Tokenization ==========
export const tokenizeAsset = (unitId: number, data: { total_shares: number; share_price_mrusdt: number }) =>
  api.post<AssetTokenization>(`/realestate/tokenize/${unitId}`, data);

// ========== Smart Contracts ==========
export const getSmartContractStatus = (contractId: number) =>
  api.get<{ status: string; tx_hash?: string; executed_at?: string }>(
    `/realestate/smart-contracts/${contractId}/status`
  );

export const deploySmartContract = (
  data: {
    contract_type: 'SALE' | 'RENTAL' | 'MORTGAGE' | 'LEASE';
    reference_id: number;
    contract_metadata: Record<string, any>;
  },
  idempotencyKey?: string
) =>
  api.post<SmartContractResponse>('/realestate/smart-contracts', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

// ========== Portfolio ==========
export const getPortfolioSummary = () =>
  api.get<PortfolioSummary>('/realestate/portfolio/summary');

// ========== إضافات جديدة ==========

/**
 * جلب العقارات المتاحة للبيع
 */
export const getAvailableProperties = () =>
  api.get<Property[]>('/realestate/properties/available');

/**
 * جلب قائمة مالكي عقار معين
 */
export const getPropertyOwnerships = (propertyId: number) =>
  api.get<Ownership[]>(`/realestate/properties/${propertyId}/ownerships`);

/**
 * جلب بيانات تجزئة عقار معين
 */
export const getAssetTokenization = (unitId: number) =>
  api.get<Tokenization>(`/realestate/tokenization/${unitId}`);

/**
 * إنشاء تجزئة جديدة لعقار
 */
export const createTokenization = (data: {
  unit_id: number;
  total_shares: number;
  share_price_mrusdt: number;
  minimum_investment_shares: number;
}) => api.post<Tokenization>('/realestate/tokenization', data);

/**
 * شراء حصة جزئية في عقار (مع Idempotency إلزامي)
 */
export const buyFractionalShare = (
  unitId: number,
  data: { ownership_percentage: number },
  idempotencyKey: string
) =>
  api.post<Ownership>(`/realestate/units/${unitId}/buy`, data, {
    headers: { 'Idempotency-Key': idempotencyKey },
  });