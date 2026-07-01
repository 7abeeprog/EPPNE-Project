// services/transport.ts
import api from '@/lib/axios';
import type {
  TransportHub,
  Fleet,
  Vehicle,
  Route,
  Trip,
  TripBooking,
  DeliveryTask,
  TransportStats,
  TripFormData,
  DeliveryFormData,
  HubFormData,
  VehicleFormData,
  RouteFormData,
  TransportType,
  TripCategory,
  VehicleStatus,
  HubType,
} from '@/types/transport';

// ========== Hubs ==========
export const getHubs = (params?: { hub_type?: HubType; skip?: number; limit?: number }) =>
  api.get<TransportHub[]>('/transport/hubs', { params });

export const createHub = (data: HubFormData) =>
  api.post<TransportHub>('/transport/hubs', data);

export const updateHub = (id: number, data: Partial<HubFormData>) =>
  api.put<TransportHub>(`/transport/hubs/${id}`, data);

export const deleteHub = (id: number) => api.delete(`/transport/hubs/${id}`);

// ========== Fleets ==========
export const getFleets = () => api.get<Fleet[]>('/transport/fleets');

export const createFleet = (data: { name: string }) =>
  api.post<Fleet>('/transport/fleets', data);

export const updateFleet = (id: number, data: { name: string }) =>
  api.put<Fleet>(`/transport/fleets/${id}`, data);

export const deleteFleet = (id: number) => api.delete(`/transport/fleets/${id}`);

// ========== Vehicles ==========
export const getVehicles = (params?: { fleet_id?: number; status?: VehicleStatus; skip?: number; limit?: number }) =>
  api.get<Vehicle[]>('/transport/vehicles', { params });

export const getAvailableVehicles = (params?: { fleet_id?: number }) =>
  api.get<Vehicle[]>('/transport/vehicles/available', { params });

export const getVehicle = (id: number) => api.get<Vehicle>(`/transport/vehicles/${id}`);

export const createVehicle = (data: VehicleFormData) =>
  api.post<Vehicle>('/transport/vehicles', data);

export const updateVehicle = (id: number, data: Partial<VehicleFormData>) =>
  api.put<Vehicle>(`/transport/vehicles/${id}`, data);

export const deleteVehicle = (id: number) => api.delete(`/transport/vehicles/${id}`);

export const updateVehicleLocation = (vehicleId: number, location: { lat: number; lng: number }) =>
  api.patch(`/transport/vehicles/${vehicleId}/location`, location);

export const getVehicleLocation = (vehicleId: number) =>
  api.get<{ lat: number; lng: number; updated_at: string }>(`/transport/vehicles/${vehicleId}/location`);

// ========== Routes ==========
export const getRoutes = (params?: { is_active?: boolean; skip?: number; limit?: number }) =>
  api.get<Route[]>('/transport/routes', { params });

export const getRoute = (id: number) => api.get<Route>(`/transport/routes/${id}`);

export const createRoute = (data: RouteFormData) =>
  api.post<Route>('/transport/routes', data);

export const updateRoute = (id: number, data: Partial<RouteFormData>) =>
  api.put<Route>(`/transport/routes/${id}`, data);

export const deleteRoute = (id: number) => api.delete(`/transport/routes/${id}`);

export const optimizeRoute = (startHubId: number, endHubId: number) =>
  api.post<Route>('/transport/routes/optimize', { start_hub_id: startHubId, end_hub_id: endHubId });

// ========== Trips ==========
export const getTrips = (params?: { status?: TripStatus; driver_id?: number; skip?: number; limit?: number }) =>
  api.get<Trip[]>('/transport/trips', { params });

export const getTrip = (id: number) => api.get<Trip>(`/transport/trips/${id}`);

export const createTrip = (data: TripFormData) =>
  api.post<Trip>('/transport/trips', data);

export const startTrip = (tripId: number, actual_start: string) =>
  api.patch<Trip>(`/transport/trips/${tripId}/start`, { actual_start });

export const completeTrip = (tripId: number, actual_end: string, total_distance_km: number) =>
  api.patch<Trip>(`/transport/trips/${tripId}/complete`, { actual_end, total_distance_km });

export const cancelTrip = (tripId: number) =>
  api.patch<Trip>(`/transport/trips/${tripId}/cancel`);

export const getMyTrips = (params?: { status?: TripStatus; skip?: number; limit?: number }) =>
  api.get<Trip[]>('/transport/trips/my', { params });

// ========== Bookings ==========
export const getBookings = (params?: { trip_id?: number; passenger_id?: number; skip?: number; limit?: number }) =>
  api.get<TripBooking[]>('/transport/bookings', { params });

export const getMyBookings = () => api.get<TripBooking[]>('/transport/bookings/my');

export const bookTrip = (
  data: {
    trip_id: number;
    passenger_id?: number;
    company_id?: number;
    booking_type: 'PASSENGER' | 'FREIGHT';
    seats_count?: number;
    weight_kg?: number;
  },
  idempotencyKey?: string
) =>
  api.post<TripBooking>('/transport/bookings', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const cancelBooking = (bookingId: number) =>
  api.patch<TripBooking>(`/transport/bookings/${bookingId}/cancel`);

// ========== Deliveries ==========
export const getDeliveries = (params?: { status?: string; skip?: number; limit?: number }) =>
  api.get<DeliveryTask[]>('/transport/deliveries', { params });

export const getMyDeliveries = () => api.get<DeliveryTask[]>('/transport/deliveries/my');

export const createDelivery = (data: DeliveryFormData) =>
  api.post<DeliveryTask>('/transport/deliveries', data);

export const payDelivery = (taskId: number, idempotencyKey?: string) =>
  api.post<DeliveryTask>(
    `/transport/deliveries/${taskId}/pay`,
    {},
    { headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {} }
  );

export const completeDelivery = (taskId: number, proof_hash: string) =>
  api.post<DeliveryTask>(`/transport/deliveries/${taskId}/complete`, { proof_hash });

export const assignDeliveryToTrip = (taskId: number, tripId: number) =>
  api.patch<DeliveryTask>(`/transport/deliveries/${taskId}/assign`, { trip_id: tripId });

// ========== Stats ==========
export const getTransportStats = () => api.get<TransportStats>('/transport/stats');

// ========== Drivers ==========
export const getDrivers = (params?: { is_active?: boolean; skip?: number; limit?: number }) =>
  api.get<User[]>('/transport/drivers', { params });