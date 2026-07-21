// services/transport.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

type TransportHubCreate = components['schemas']['TransportHubCreate'];
type TransportHubResponse = components['schemas']['TransportHubResponse'];
type FleetCreate = components['schemas']['FleetCreate'];
type FleetResponse = components['schemas']['FleetResponse'];
type VehicleCreate = components['schemas']['VehicleCreate'];
type VehicleResponse = components['schemas']['VehicleResponse'];
type RouteCreate = components['schemas']['RouteCreate'];
type RouteResponse = components['schemas']['RouteResponse'];
type TripCreate = components['schemas']['TripCreate'];
type TripResponse = components['schemas']['TripResponse'];
type TripStartRequest = components['schemas']['TripStartRequest'];
type TripCompleteRequest = components['schemas']['TripCompleteRequest'];
type TripBookingCreate = components['schemas']['TripBookingCreate'];
type TripBookingResponse = components['schemas']['TripBookingResponse'];
type DeliveryTaskCreate = components['schemas']['DeliveryTaskCreate'];
type DeliveryTaskResponse = components['schemas']['DeliveryTaskResponse'];
type DeliveryProof = components['schemas']['DeliveryProof'];

export const TransportService = {
  /**
   * إنشاء مركز نقل جديد
   * POST /transport/transport/hubs
   * تدعم X-Tenant-ID
   */
  createHub: async (data: TransportHubCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<TransportHubResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<TransportHubResponse>("/transport/transport/hubs", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المركز");
    }
  },

  /**
   * جلب قائمة المراكز مع التصفية
   * GET /transport/transport/hubs
   * تدعم X-Tenant-ID
   */
  listHubs: async (params?: { hub_type?: string | null; skip?: number; limit?: number }, headers?: { 'X-Tenant-ID'?: number }): Promise<TransportHubResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<TransportHubResponse[]>("/transport/transport/hubs", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المراكز");
    }
  },

  /**
   * إنشاء أسطول جديد
   * POST /transport/transport/fleets
   * تدعم X-Tenant-ID
   */
  createFleet: async (data: FleetCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<FleetResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<FleetResponse>("/transport/transport/fleets", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الأسطول");
    }
  },

  /**
   * إنشاء مركبة جديدة
   * POST /transport/transport/vehicles
   * تدعم X-Tenant-ID
   */
  createVehicle: async (data: VehicleCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<VehicleResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<VehicleResponse>("/transport/transport/vehicles", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المركبة");
    }
  },

  /**
   * تحديث موقع المركبة
   * PATCH /transport/transport/vehicles/{vehicle_id}/location
   * تدعم X-Tenant-ID
   */
  updateVehicleLocation: async (
    vehicleId: number,
    location: Record<string, number>,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<void> => {
    try {
      const id = Number(vehicleId);
      if (isNaN(id)) throw new Error("معرف المركبة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      await apiClient.patch(`/transport/transport/vehicles/${id}/location`, location, {
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل تحديث موقع المركبة");
    }
  },

  /**
   * جلب المركبات المتاحة
   * GET /transport/transport/vehicles/available
   * تدعم X-Tenant-ID
   */
  getAvailableVehicles: async (params?: { fleet_id?: number | null }, headers?: { 'X-Tenant-ID'?: number }): Promise<VehicleResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<VehicleResponse[]>("/transport/transport/vehicles/available", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المركبات المتاحة");
    }
  },

  /**
   * إنشاء مسار جديد
   * POST /transport/transport/routes
   * تدعم X-Tenant-ID
   */
  createRoute: async (data: RouteCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<RouteResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<RouteResponse>("/transport/transport/routes", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المسار");
    }
  },

  /**
   * إنشاء رحلة جديدة
   * POST /transport/transport/trips
   * تدعم X-Tenant-ID
   */
  createTrip: async (data: TripCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<TripResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<TripResponse>("/transport/transport/trips", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الرحلة");
    }
  },

  /**
   * بدء الرحلة
   * PATCH /transport/transport/trips/{trip_id}/start
   * تدعم X-Tenant-ID
   */
  startTrip: async (tripId: number, data: TripStartRequest, headers?: { 'X-Tenant-ID'?: number }): Promise<TripResponse> => {
    try {
      const id = Number(tripId);
      if (isNaN(id)) throw new Error("معرف الرحلة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.patch<TripResponse>(`/transport/transport/trips/${id}/start`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل بدء الرحلة");
    }
  },

  /**
   * إكمال الرحلة
   * PATCH /transport/transport/trips/{trip_id}/complete
   * تدعم X-Tenant-ID
   */
  completeTrip: async (tripId: number, data: TripCompleteRequest, headers?: { 'X-Tenant-ID'?: number }): Promise<TripResponse> => {
    try {
      const id = Number(tripId);
      if (isNaN(id)) throw new Error("معرف الرحلة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.patch<TripResponse>(`/transport/transport/trips/${id}/complete`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إكمال الرحلة");
    }
  },

  /**
   * جلب رحلاتي
   * GET /transport/transport/trips/my
   * تدعم X-Tenant-ID
   */
  getMyTrips: async (
    params?: { status_filter?: string | null; skip?: number; limit?: number },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<TripResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<TripResponse[]>("/transport/transport/trips/my", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب رحلاتي");
    }
  },

  /**
   * حجز رحلة
   * POST /transport/transport/bookings
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  bookTrip: async (
    data: TripBookingCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<TripBookingResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<TripBookingResponse>("/transport/transport/bookings", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل حجز الرحلة");
    }
  },

  /**
   * جلب حجوزاتي
   * GET /transport/transport/bookings/my
   * تدعم X-Tenant-ID
   */
  getMyBookings: async (headers?: { 'X-Tenant-ID'?: number }): Promise<TripBookingResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<TripBookingResponse[]>("/transport/transport/bookings/my", {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب حجوزاتي");
    }
  },

  /**
   * إنشاء مهمة توصيل جديدة
   * POST /transport/transport/deliveries
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  createDelivery: async (
    data: DeliveryTaskCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<DeliveryTaskResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<DeliveryTaskResponse>("/transport/transport/deliveries", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء مهمة التوصيل");
    }
  },

  /**
   * دفع تكلفة التوصيل
   * POST /transport/transport/deliveries/{task_id}/pay
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  payDelivery: async (
    taskId: number,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<DeliveryTaskResponse> => {
    try {
      const id = Number(taskId);
      if (isNaN(id)) throw new Error("معرف المهمة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<DeliveryTaskResponse>(
        `/transport/transport/deliveries/${id}/pay`,
        undefined,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل دفع التوصيل");
    }
  },

  /**
   * إكمال مهمة التوصيل
   * POST /transport/transport/deliveries/{task_id}/complete
   * تدعم X-Tenant-ID
   */
  completeDelivery: async (taskId: number, data: DeliveryProof, headers?: { 'X-Tenant-ID'?: number }): Promise<DeliveryTaskResponse> => {
    try {
      const id = Number(taskId);
      if (isNaN(id)) throw new Error("معرف المهمة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<DeliveryTaskResponse>(
        `/transport/transport/deliveries/${id}/complete`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إكمال التوصيل");
    }
  },
};