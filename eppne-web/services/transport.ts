// services/transport.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

type TransportHubCreate = components['schemas']['TransportHubCreate'];
type TransportHubResponse = components['schemas']['TransportHubResponse'];
type FleetCreate = components['schemas']['FleetCreate'];
type FleetUpdate = components['schemas']['FleetUpdate'];
type FleetResponse = components['schemas']['FleetResponse'];
type VehicleCreate = components['schemas']['VehicleCreate'];
type VehicleUpdate = components['schemas']['VehicleUpdate'];
type VehicleResponse = components['schemas']['VehicleResponse'];
type DriverResponse = components['schemas']['DriverResponse'];
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
   * POST /transport/hubs
   * تدعم X-Tenant-ID
   */
  createHub: async (data: TransportHubCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<TransportHubResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<TransportHubResponse>("/transport/hubs", data, {
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
   * GET /transport/hubs
   * تدعم X-Tenant-ID
   */
  listHubs: async (params?: { hub_type?: string | null; skip?: number; limit?: number }, headers?: { 'X-Tenant-ID'?: number }): Promise<TransportHubResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<TransportHubResponse[]>("/transport/hubs", {
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
   * POST /transport/fleets
   * تدعم X-Tenant-ID
   */
  createFleet: async (data: FleetCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<FleetResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<FleetResponse>("/transport/fleets", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الأسطول");
    }
  },

  /**
   * جلب كل الأساطيل (نشطة فقط — is_active=false مستبعدة)
   * GET /transport/fleets
   * تدعم X-Tenant-ID
   */
  listFleets: async (
    params?: { skip?: number; limit?: number },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<FleetResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<FleetResponse[]>("/transport/fleets", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الأساطيل");
    }
  },

  /**
   * تعديل اسم أسطول
   * PATCH /transport/fleets/{fleet_id}
   * تدعم X-Tenant-ID
   */
  updateFleet: async (
    fleetId: number,
    data: FleetUpdate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<FleetResponse> => {
    try {
      const id = Number(fleetId);
      if (isNaN(id)) throw new Error("معرف الأسطول غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.patch<FleetResponse>(`/transport/fleets/${id}`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تعديل الأسطول");
    }
  },

  /**
   * حذف أسطول (soft delete — is_active=false)
   * DELETE /transport/fleets/{fleet_id}
   * تدعم X-Tenant-ID
   */
  deleteFleet: async (fleetId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<void> => {
    try {
      const id = Number(fleetId);
      if (isNaN(id)) throw new Error("معرف الأسطول غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      await apiClient.delete(`/transport/fleets/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل حذف الأسطول");
    }
  },

  /**
   * جلب المستخدمين النشطين لنفس التينانت — لاختيار سائق عند جدولة رحلة.
   * بدون كيان/دور "سائق" منفصل [قرار مستخدم، جلسة
   * transport-vehicles-drivers-feature-build، 2026-09-04]: create_trip
   * أصلًا بتقبل أي user_id كـdriver_id بلا فحص دور.
   * GET /transport/drivers
   * تدعم X-Tenant-ID
   */
  listDrivers: async (
    params?: { skip?: number; limit?: number },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<DriverResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<DriverResponse[]>("/transport/drivers", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب السائقين");
    }
  },

  /**
   * إنشاء مركبة جديدة
   * POST /transport/vehicles
   * تدعم X-Tenant-ID
   */
  createVehicle: async (data: VehicleCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<VehicleResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<VehicleResponse>("/transport/vehicles", data, {
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
   * PATCH /transport/vehicles/{vehicle_id}/location
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
      await apiClient.patch(`/transport/vehicles/${id}/location`, location, {
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل تحديث موقع المركبة");
    }
  },

  /**
   * جلب المركبات المتاحة
   * GET /transport/vehicles/available
   * تدعم X-Tenant-ID
   */
  getAvailableVehicles: async (params?: { fleet_id?: number | null }, headers?: { 'X-Tenant-ID'?: number }): Promise<VehicleResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<VehicleResponse[]>("/transport/vehicles/available", {
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
   * جلب كل المركبات (بدون فلتر حالة إجباري، عكس getAvailableVehicles)
   * GET /transport/vehicles
   * تدعم X-Tenant-ID
   */
  listVehicles: async (
    params?: { fleet_id?: number | null; status?: string | null; skip?: number; limit?: number },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<VehicleResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<VehicleResponse[]>("/transport/vehicles", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المركبات");
    }
  },

  /**
   * تعديل بيانات مركبة (غير الموقع — له مسار منفصل updateVehicleLocation)
   * PATCH /transport/vehicles/{vehicle_id}
   * تدعم X-Tenant-ID
   */
  updateVehicle: async (
    vehicleId: number,
    data: VehicleUpdate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<VehicleResponse> => {
    try {
      const id = Number(vehicleId);
      if (isNaN(id)) throw new Error("معرف المركبة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.patch<VehicleResponse>(`/transport/vehicles/${id}`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تعديل المركبة");
    }
  },

  /**
   * حذف مركبة (hard delete — يُرفض لو لها تاريخ رحلات)
   * DELETE /transport/vehicles/{vehicle_id}
   * تدعم X-Tenant-ID
   */
  deleteVehicle: async (vehicleId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<void> => {
    try {
      const id = Number(vehicleId);
      if (isNaN(id)) throw new Error("معرف المركبة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      await apiClient.delete(`/transport/vehicles/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل حذف المركبة");
    }
  },

  /**
   * جلب مركبة واحدة (تشمل موقعها الحالي)
   * GET /transport/vehicles/{vehicle_id}
   * تدعم X-Tenant-ID
   */
  getVehicle: async (vehicleId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<VehicleResponse> => {
    try {
      const id = Number(vehicleId);
      if (isNaN(id)) throw new Error("معرف المركبة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<VehicleResponse>(`/transport/vehicles/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب بيانات المركبة");
    }
  },

  /**
   * إنشاء مسار جديد
   * POST /transport/routes
   * تدعم X-Tenant-ID
   */
  createRoute: async (data: RouteCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<RouteResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<RouteResponse>("/transport/routes", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المسار");
    }
  },

  /**
   * جلب مسار واحد
   * GET /transport/routes/{route_id}
   * تدعم X-Tenant-ID
   */
  getRoute: async (routeId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<RouteResponse> => {
    try {
      const id = Number(routeId);
      if (isNaN(id)) throw new Error("معرف المسار غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<RouteResponse>(`/transport/routes/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المسار");
    }
  },

  /**
   * إنشاء رحلة جديدة
   * POST /transport/trips
   * تدعم X-Tenant-ID
   */
  createTrip: async (data: TripCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<TripResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<TripResponse>("/transport/trips", data, {
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
   * PATCH /transport/trips/{trip_id}/start
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
      const { data: result } = await apiClient.patch<TripResponse>(`/transport/trips/${id}/start`, data, {
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
   * PATCH /transport/trips/{trip_id}/complete
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
      const { data: result } = await apiClient.patch<TripResponse>(`/transport/trips/${id}/complete`, data, {
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
   * GET /transport/trips/my
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
      const { data } = await apiClient.get<TripResponse[]>("/transport/trips/my", {
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
   * جلب رحلة واحدة
   * GET /transport/trips/{trip_id}
   * تدعم X-Tenant-ID
   */
  getTrip: async (tripId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<TripResponse> => {
    try {
      const id = Number(tripId);
      if (isNaN(id)) throw new Error("معرف الرحلة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<TripResponse>(`/transport/trips/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الرحلة");
    }
  },

  /**
   * حجز رحلة
   * POST /transport/bookings
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
      const { data: result } = await apiClient.post<TripBookingResponse>("/transport/bookings", data, {
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
   * GET /transport/bookings/my
   * تدعم X-Tenant-ID
   */
  getMyBookings: async (headers?: { 'X-Tenant-ID'?: number }): Promise<TripBookingResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<TripBookingResponse[]>("/transport/bookings/my", {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب حجوزاتي");
    }
  },

  /**
   * جلب قائمة الحجوزات مع التصفية
   * GET /transport/bookings
   * تدعم X-Tenant-ID
   */
  listBookings: async (
    params?: { passenger_id?: number; trip_id?: number },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<TripBookingResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<TripBookingResponse[]>("/transport/bookings", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الحجوزات");
    }
  },

  /**
   * إلغاء حجز
   * PATCH /transport/bookings/{booking_id}/cancel
   * تدعم X-Tenant-ID
   */
  cancelBooking: async (bookingId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<TripBookingResponse> => {
    try {
      const id = Number(bookingId);
      if (isNaN(id)) throw new Error("معرف الحجز غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.patch<TripBookingResponse>(
        `/transport/bookings/${id}/cancel`,
        undefined,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إلغاء الحجز");
    }
  },

  /**
   * إنشاء مهمة توصيل جديدة
   * POST /transport/deliveries
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
      const { data: result } = await apiClient.post<DeliveryTaskResponse>("/transport/deliveries", data, {
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
   * POST /transport/deliveries/{task_id}/pay
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
        `/transport/deliveries/${id}/pay`,
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
   * POST /transport/deliveries/{task_id}/complete
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
        `/transport/deliveries/${id}/complete`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إكمال التوصيل");
    }
  },

  /**
   * ربط مهمة توصيل برحلة
   * POST /transport/deliveries/{task_id}/assign
   * تدعم X-Tenant-ID
   */
  assignDeliveryToTrip: async (taskId: number, tripId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<DeliveryTaskResponse> => {
    try {
      const id = Number(taskId);
      if (isNaN(id)) throw new Error("معرف المهمة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<DeliveryTaskResponse>(
        `/transport/deliveries/${id}/assign`,
        { trip_id: tripId },
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل ربط مهمة التوصيل بالرحلة");
    }
  },
};