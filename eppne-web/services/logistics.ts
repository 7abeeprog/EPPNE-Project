// services/logistics.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

type WarehouseCreate = components['schemas']['WarehouseCreate'];
type WarehouseResponse = components['schemas']['WarehouseResponse'];
type WarehouseUpdate = components['schemas']['WarehouseUpdate'];
type WarehouseType = components['schemas']['WarehouseType'];
type WarehouseZoneCreate = components['schemas']['WarehouseZoneCreate'];
type WarehouseZoneResponse = components['schemas']['WarehouseZoneResponse'];
type InventoryReceive = components['schemas']['InventoryReceive'];
type InventoryIssue = components['schemas']['InventoryIssue'];
type InventoryAdjust = components['schemas']['InventoryAdjust'];
type InventoryTransactionResponse = components['schemas']['InventoryTransactionResponse'];
type InventoryItemResponse = components['schemas']['InventoryItemResponse'];
type InventoryStatus = components['schemas']['InventoryStatus'];
type EquipmentCreate = components['schemas']['EquipmentCreate'];
type EquipmentResponse = components['schemas']['EquipmentResponse'];
type EquipmentUpdate = components['schemas']['EquipmentUpdate'];
type EquipmentStatus = components['schemas']['EquipmentStatus'];
type EquipmentMaintenanceCreate = components['schemas']['EquipmentMaintenanceCreate'];
type EquipmentMaintenanceResponse = components['schemas']['EquipmentMaintenanceResponse'];
type InventoryForecastResponse = components['schemas']['InventoryForecastResponse'];
type LogisticsStatsResponse = components['schemas']['LogisticsStatsResponse'];

export const LogisticsService = {
  /**
   * إنشاء مستودع جديد
   * POST /logistics/logistics/warehouses
   * تدعم X-Tenant-ID
   */
  createWarehouse: async (data: WarehouseCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<WarehouseResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<WarehouseResponse>("/logistics/logistics/warehouses", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المستودع");
    }
  },

  /**
   * جلب قائمة المستودعات مع التصفية
   * GET /logistics/logistics/warehouses
   * تدعم X-Tenant-ID
   */
  listWarehouses: async (
    params?: {
      warehouse_type?: WarehouseType | null;
      is_active?: boolean | null;
      skip?: number;
      limit?: number;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<WarehouseResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<WarehouseResponse[]>("/logistics/logistics/warehouses", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المستودعات");
    }
  },

  /**
   * جلب تفاصيل مستودع محدد
   * GET /logistics/logistics/warehouses/{warehouse_id}
   * تدعم X-Tenant-ID
   */
  getWarehouse: async (warehouseId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<WarehouseResponse> => {
    try {
      const id = Number(warehouseId);
      if (isNaN(id)) throw new Error("معرف المستودع غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<WarehouseResponse>(`/logistics/logistics/warehouses/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل المستودع");
    }
  },

  /**
   * تحديث مستودع
   * PUT /logistics/logistics/warehouses/{warehouse_id}
   * تدعم X-Tenant-ID
   */
  updateWarehouse: async (
    warehouseId: number,
    data: WarehouseUpdate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<WarehouseResponse> => {
    try {
      const id = Number(warehouseId);
      if (isNaN(id)) throw new Error("معرف المستودع غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.put<WarehouseResponse>(`/logistics/logistics/warehouses/${id}`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث المستودع");
    }
  },

  /**
   * حذف مستودع
   * DELETE /logistics/logistics/warehouses/{warehouse_id}
   * تدعم X-Tenant-ID
   */
  deleteWarehouse: async (warehouseId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<void> => {
    try {
      const id = Number(warehouseId);
      if (isNaN(id)) throw new Error("معرف المستودع غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      await apiClient.delete(`/logistics/logistics/warehouses/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل حذف المستودع");
    }
  },

  /**
   * إنشاء منطقة داخل مستودع
   * POST /logistics/logistics/warehouses/{warehouse_id}/zones
   * تدعم X-Tenant-ID
   */
  createWarehouseZone: async (
    warehouseId: number,
    data: WarehouseZoneCreate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<WarehouseZoneResponse> => {
    try {
      const id = Number(warehouseId);
      if (isNaN(id)) throw new Error("معرف المستودع غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<WarehouseZoneResponse>(
        `/logistics/logistics/warehouses/${id}/zones`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء منطقة المستودع");
    }
  },

  /**
   * استلام مخزون
   * POST /logistics/logistics/inventory/receive
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  receiveInventory: async (
    data: InventoryReceive,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<InventoryTransactionResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<InventoryTransactionResponse>(
        "/logistics/logistics/inventory/receive",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل استلام المخزون");
    }
  },

  /**
   * صرف مخزون
   * POST /logistics/logistics/inventory/issue
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  issueInventory: async (
    data: InventoryIssue,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<InventoryTransactionResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<InventoryTransactionResponse>(
        "/logistics/logistics/inventory/issue",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل صرف المخزون");
    }
  },

  /**
   * تعديل المخزون (جرد)
   * POST /logistics/logistics/inventory/adjust/{inventory_item_id}
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  adjustInventory: async (
    inventoryItemId: number,
    data: InventoryAdjust,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<InventoryTransactionResponse> => {
    try {
      const id = Number(inventoryItemId);
      if (isNaN(id)) throw new Error("معرف الصنف غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<InventoryTransactionResponse>(
        `/logistics/logistics/inventory/adjust/${id}`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تعديل المخزون");
    }
  },

  /**
   * جلب قائمة المخزون مع التصفية
   * GET /logistics/logistics/inventory
   * تدعم X-Tenant-ID
   */
  listInventory: async (
    params?: {
      warehouse_id?: number | null;
      status?: InventoryStatus | null;
      product_category?: string | null;
      skip?: number;
      limit?: number;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<InventoryItemResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<InventoryItemResponse[]>("/logistics/logistics/inventory", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المخزون");
    }
  },

  /**
   * جلب المخزون المنخفض
   * GET /logistics/logistics/inventory/low-stock
   * تدعم X-Tenant-ID
   */
  getLowStock: async (params?: { warehouse_id?: number | null }, headers?: { 'X-Tenant-ID'?: number }): Promise<InventoryItemResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<InventoryItemResponse[]>("/logistics/logistics/inventory/low-stock", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المخزون المنخفض");
    }
  },

  /**
   * جلب المخزون منتهي الصلاحية
   * GET /logistics/logistics/inventory/expired
   * تدعم X-Tenant-ID
   */
  getExpired: async (headers?: { 'X-Tenant-ID'?: number }): Promise<InventoryItemResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<InventoryItemResponse[]>("/logistics/logistics/inventory/expired", {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المخزون منتهي الصلاحية");
    }
  },

  /**
   * جلب تفاصيل صنف مخزون محدد
   * GET /logistics/logistics/inventory/{item_id}
   * تدعم X-Tenant-ID
   */
  getInventoryItem: async (itemId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<InventoryItemResponse> => {
    try {
      const id = Number(itemId);
      if (isNaN(id)) throw new Error("معرف الصنف غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<InventoryItemResponse>(`/logistics/logistics/inventory/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل الصنف");
    }
  },

  /**
   * جلب معاملات صنف مخزون محدد
   * GET /logistics/logistics/inventory/{item_id}/transactions
   * تدعم X-Tenant-ID
   */
  getInventoryTransactions: async (
    itemId: number,
    params?: { skip?: number; limit?: number },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<InventoryTransactionResponse[]> => {
    try {
      const id = Number(itemId);
      if (isNaN(id)) throw new Error("معرف الصنف غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<InventoryTransactionResponse[]>(`/logistics/logistics/inventory/${id}/transactions`, {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب معاملات الصنف");
    }
  },

  /**
   * إنشاء معدات جديدة
   * POST /logistics/logistics/equipment
   * تدعم X-Tenant-ID
   */
  createEquipment: async (data: EquipmentCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<EquipmentResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<EquipmentResponse>("/logistics/logistics/equipment", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المعدات");
    }
  },

  /**
   * جلب قائمة المعدات مع التصفية
   * GET /logistics/logistics/equipment
   * تدعم X-Tenant-ID
   */
  listEquipment: async (
    params?: {
      equipment_type?: string | null;
      status?: EquipmentStatus | null;
      warehouse_id?: number | null;
      skip?: number;
      limit?: number;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<EquipmentResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<EquipmentResponse[]>("/logistics/logistics/equipment", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المعدات");
    }
  },

  /**
   * جلب تفاصيل معدات محددة
   * GET /logistics/logistics/equipment/{equipment_id}
   * تدعم X-Tenant-ID
   */
  getEquipment: async (equipmentId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<EquipmentResponse> => {
    try {
      const id = Number(equipmentId);
      if (isNaN(id)) throw new Error("معرف المعدات غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<EquipmentResponse>(`/logistics/logistics/equipment/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب تفاصيل المعدات");
    }
  },

  /**
   * تحديث معدات
   * PUT /logistics/logistics/equipment/{equipment_id}
   * تدعم X-Tenant-ID
   */
  updateEquipment: async (
    equipmentId: number,
    data: EquipmentUpdate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<EquipmentResponse> => {
    try {
      const id = Number(equipmentId);
      if (isNaN(id)) throw new Error("معرف المعدات غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.put<EquipmentResponse>(`/logistics/logistics/equipment/${id}`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث المعدات");
    }
  },

  /**
   * إنشاء طلب صيانة لمعدات
   * POST /logistics/logistics/equipment/{equipment_id}/maintenance
   * تدعم X-Tenant-ID
   */
  createMaintenance: async (
    equipmentId: number,
    data: EquipmentMaintenanceCreate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<EquipmentMaintenanceResponse> => {
    try {
      const id = Number(equipmentId);
      if (isNaN(id)) throw new Error("معرف المعدات غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<EquipmentMaintenanceResponse>(
        `/logistics/logistics/equipment/${id}/maintenance`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء طلب الصيانة");
    }
  },

  /**
   * إنشاء توقع للمخزون
   * POST /logistics/logistics/forecast
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  generateForecast: async (
    productId: number,
    period?: string,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<InventoryForecastResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<InventoryForecastResponse>(
        "/logistics/logistics/forecast",
        undefined,
        {
          params: { product_id: productId, period: period || 'MONTHLY' },
          headers: reqHeaders,
          withCredentials: true,
        }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء التوقع");
    }
  },

  /**
   * جلب قائمة التوقعات
   * GET /logistics/logistics/forecast
   * تدعم X-Tenant-ID
   */
  listForecasts: async (
    params?: {
      product_id?: number | null;
      period?: string | null;
      skip?: number;
      limit?: number;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<InventoryForecastResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<InventoryForecastResponse[]>("/logistics/logistics/forecast", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب التوقعات");
    }
  },

  /**
   * جلب إحصائيات الخدمات اللوجستية
   * GET /logistics/logistics/stats
   * تدعم X-Tenant-ID
   */
  getLogisticsStats: async (headers?: { 'X-Tenant-ID'?: number }): Promise<LogisticsStatsResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<LogisticsStatsResponse>("/logistics/logistics/stats", {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب إحصائيات الخدمات اللوجستية");
    }
  },
};