// types/transport.ts
export type TransportType =
  | 'BICYCLE'
  | 'MOTORCYCLE'
  | 'CAR'
  | 'BUS'
  | 'TRUCK'
  | 'SHIP'
  | 'AIRCRAFT'
  | 'SPACECRAFT'
  | 'TRAIN';

export type TripCategory = 'PASSENGER' | 'FREIGHT' | 'MASS_TRANSIT' | 'TOURISM' | 'MEDICAL' | 'EDUCATIONAL';
export type TripStatus = 'SCHEDULED' | 'ONGOING' | 'COMPLETED' | 'CANCELLED' | 'DELAYED';
export type VehicleStatus = 'AVAILABLE' | 'IN_TRIP' | 'MAINTENANCE' | 'OUT_OF_SERVICE';
export type HubType = 'BUS_STATION' | 'PORT' | 'AIRPORT' | 'SPACE_PORT' | 'RAILWAY_STATION';

export interface TransportHub {
  id: number;
  name: string;
  hub_type: HubType;
  region?: string;
  gps_location: { lat: number; lng: number };
  is_active: boolean;
  created_at: string;
}

export interface Fleet {
  id: number;
  name: string;
  entity_id: number;
  is_active: boolean;
  created_at: string;
}

export interface Vehicle {
  id: number;
  fleet_id: number;
  license_plate: string;
  vehicle_type: TransportType;
  capacity_kg?: number;
  capacity_passengers?: number;
  fuel_type: string;
  carbon_per_km: number;
  status: VehicleStatus;
  current_location?: { lat: number; lng: number };
  smart_asset_id?: number;
  created_at: string;
}

export interface Route {
  id: number;
  name: string;
  start_hub_id: number;
  end_hub_id: number;
  start_hub?: TransportHub;
  end_hub?: TransportHub;
  waypoints: Array<{ lat: number; lng: number; name?: string }>;
  distance_km: number;
  estimated_duration_minutes: number;
  is_active: boolean;
  created_at: string;
}

export interface Trip {
  id: number;
  route_id: number;
  route?: Route;
  vehicle_id: number;
  vehicle?: Vehicle;
  driver_id: number;
  driver_name?: string;
  trip_category: TripCategory;
  scheduled_start: string;
  scheduled_end: string;
  actual_start?: string;
  actual_end?: string;
  status: TripStatus;
  total_distance_km: number;
  carbon_footprint_kg: number;
  base_fare_mrusdt: number;
  total_fare_mrusdt: number;
  payment_tx_hash?: string;
  created_at: string;
}

export interface TripBooking {
  id: number;
  trip_id: number;
  trip?: Trip;
  passenger_id?: number;
  passenger_name?: string;
  company_id?: number;
  company_name?: string;
  booking_type: 'PASSENGER' | 'FREIGHT';
  seats_count?: number;
  weight_kg?: number;
  fare_paid_mrusdt: number;
  status: 'CONFIRMED' | 'CHECKED_IN' | 'CANCELLED';
  created_at: string;
}

export interface DeliveryTask {
  id: number;
  order_id?: number;
  trip_id?: number;
  trip?: Trip;
  sender_id: number;
  sender_name?: string;
  receiver_id: number;
  receiver_name?: string;
  pickup_address: { address: string; lat: number; lng: number };
  dropoff_address: { address: string; lat: number; lng: number };
  estimated_distance_km?: number;
  status: 'PENDING' | 'ASSIGNED' | 'PICKED_UP' | 'DELIVERED';
  delivery_proof_hash?: string;
  delivery_fee_mrusdt: number;
  payment_tx_hash?: string;
  created_at: string;
}

// ========== UI Types ==========
export interface TransportStats {
  total_vehicles: number;
  available_vehicles: number;
  active_trips: number;
  total_deliveries: number;
  total_carbon_saved: number;
  total_hubs: number;
  total_routes: number;
}

export interface TripFormData {
  route_id: number;
  vehicle_id: number;
  driver_id: number;
  trip_category: TripCategory;
  scheduled_start: string;
  scheduled_end: string;
  base_fare_mrusdt: number;
}

export interface DeliveryFormData {
  order_id?: number;
  receiver_id: number;
  pickup_address: { address: string; lat: number; lng: number };
  dropoff_address: { address: string; lat: number; lng: number };
  estimated_distance_km?: number;
  delivery_fee_mrusdt: number;
}

export interface HubFormData {
  name: string;
  hub_type: HubType;
  region?: string;
  gps_location: { lat: number; lng: number };
}

export interface VehicleFormData {
  fleet_id: number;
  license_plate: string;
  vehicle_type: TransportType;
  capacity_kg?: number;
  capacity_passengers?: number;
  fuel_type: string;
  carbon_per_km: number;
}

export interface RouteFormData {
  name: string;
  start_hub_id: number;
  end_hub_id: number;
  waypoints: Array<{ lat: number; lng: number; name?: string }>;
  distance_km: number;
  estimated_duration_minutes: number;
}