// services/realestate.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

type LandAssetCreate = components['schemas']['LandAssetCreate'];
type LandAssetResponse = components['schemas']['LandAssetResponse'];
type DevelopmentCreate = components['schemas']['DevelopmentCreate'];
type DevelopmentResponse = components['schemas']['DevelopmentResponse'];
type PropertyUnitCreate = components['schemas']['PropertyUnitCreate'];
type PropertyUnitResponse = components['schemas']['PropertyUnitResponse'];
type BuyFractionalOwnership = components['schemas']['BuyFractionalOwnership'];
type OwnershipResponse = components['schemas']['OwnershipResponse'];
type RentalContractCreate = components['schemas']['RentalContractCreate'];
type RentalContractResponse = components['schemas']['RentalContractResponse'];
type MasterPlanCreate = components['schemas']['MasterPlanCreate'];
type MasterPlanResponse = components['schemas']['MasterPlanResponse'];
type TokenizationCreate = components['schemas']['TokenizationCreate'];
type TokenizationResponse = components['schemas']['TokenizationResponse'];
type SmartContractCreate = components['schemas']['SmartContractCreate'];
type SmartContractResponse = components['schemas']['SmartContractResponse'];

export const RealEstateService = {
  /**
   * إنشاء أصل أرضي جديد
   * POST /realestate/realestate/lands
   * تدعم X-Tenant-ID
   */
  createLandAsset: async (data: LandAssetCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<LandAssetResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<LandAssetResponse>("/realestate/realestate/lands", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الأصل الأرضي");
    }
  },

  /**
   * جلب أراضيي
   * GET /realestate/realestate/lands/me
   * تدعم X-Tenant-ID
   */
  getMyLands: async (params?: { skip?: number; limit?: number }, headers?: { 'X-Tenant-ID'?: number }): Promise<LandAssetResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<LandAssetResponse[]>("/realestate/realestate/lands/me", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب أراضيي");
    }
  },

  /**
   * إعادة تقييم أرض
   * PATCH /realestate/realestate/lands/{land_id}/revalue
   */
  revalueLand: async (landId: number, newValue: number | string): Promise<LandAssetResponse> => {
    try {
      const id = Number(landId);
      if (isNaN(id)) throw new Error("معرف الأرض غير صحيح");
      const { data: result } = await apiClient.patch<LandAssetResponse>(
        `/realestate/realestate/lands/${id}/revalue`,
        undefined,
        { params: { new_value: newValue }, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إعادة تقييم الأرض");
    }
  },

  /**
   * إنشاء تطوير عقاري جديد
   * POST /realestate/realestate/developments
   * تدعم X-Tenant-ID
   */
  createDevelopment: async (data: DevelopmentCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<DevelopmentResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<DevelopmentResponse>("/realestate/realestate/developments", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء التطوير العقاري");
    }
  },

  /**
   * جلب تفاصيل تطوير عقاري
   * GET /realestate/realestate/developments/{dev_id}
   */
  getDevelopment: async (devId: number): Promise<DevelopmentResponse> => {
    try {
      const id = Number(devId);
      if (isNaN(id)) throw new Error("معرف التطوير غير صحيح");
      const { data } = await apiClient.get<DevelopmentResponse>(`/realestate/realestate/developments/${id}`, {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل التطوير");
    }
  },

  /**
   * إنشاء وحدة عقارية جديدة
   * POST /realestate/realestate/units
   * تدعم X-Tenant-ID
   */
  createPropertyUnit: async (data: PropertyUnitCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<PropertyUnitResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<PropertyUnitResponse>("/realestate/realestate/units", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الوحدة العقارية");
    }
  },

  /**
   * جلب الوحدات المتاحة للبيع
   * GET /realestate/realestate/units/for-sale
   */
  listUnitsForSale: async (params?: { development_id?: number | null; skip?: number; limit?: number }): Promise<PropertyUnitResponse[]> => {
    try {
      const { data } = await apiClient.get<PropertyUnitResponse[]>("/realestate/realestate/units/for-sale", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الوحدات للبيع");
    }
  },

  /**
   * شراء حصة جزئية من وحدة عقارية
   * POST /realestate/realestate/units/{unit_id}/buy
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  buyFraction: async (
    unitId: number,
    data: BuyFractionalOwnership,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<OwnershipResponse> => {
    try {
      const id = Number(unitId);
      if (isNaN(id)) throw new Error("معرف الوحدة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<OwnershipResponse>(`/realestate/realestate/units/${id}/buy`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل شراء الحصة");
    }
  },

  /**
   * جلب ملكياتي العقارية
   * GET /realestate/realestate/my-ownerships
   */
  getMyOwnerships: async (): Promise<OwnershipResponse[]> => {
    try {
      const { data } = await apiClient.get<OwnershipResponse[]>("/realestate/realestate/my-ownerships", {
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب ملكياتي");
    }
  },

  /**
   * إنشاء عقد إيجار جديد
   * POST /realestate/realestate/rentals
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  createRentalContract: async (
    data: RentalContractCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<RentalContractResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<RentalContractResponse>("/realestate/realestate/rentals", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء عقد الإيجار");
    }
  },

  /**
   * إنشاء مخطط رئيسي جديد
   * POST /realestate/realestate/master-plans
   * تدعم X-Tenant-ID
   */
  createMasterPlan: async (data: MasterPlanCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<MasterPlanResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<MasterPlanResponse>("/realestate/realestate/master-plans", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المخطط الرئيسي");
    }
  },

  /**
   * تجزئة أصل عقاري
   * POST /realestate/realestate/tokenize/{unit_id}
   * تدعم X-Tenant-ID
   */
  tokenizeAsset: async (
    unitId: number,
    data: TokenizationCreate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<TokenizationResponse> => {
    try {
      const id = Number(unitId);
      if (isNaN(id)) throw new Error("معرف الوحدة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<TokenizationResponse>(`/realestate/realestate/tokenize/${id}`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تجزئة الأصل");
    }
  },

  /**
   * نشر عقد ذكي جديد
   * POST /realestate/realestate/smart-contracts
   * تدعم X-Tenant-ID
   */
  deploySmartContract: async (data: SmartContractCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<SmartContractResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<SmartContractResponse>(
        "/realestate/realestate/smart-contracts",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل نشر العقد الذكي");
    }
  },
};