// store/transportStore.ts
import { create } from 'zustand';
import type { Vehicle, Trip, DeliveryTask } from '@/types/transport';

interface TransportState {
  selectedVehicle: Vehicle | null;
  selectedTrip: Trip | null;
  selectedDelivery: DeliveryTask | null;
  isTrackingLive: boolean;
  trackingVehicleId: number | null;
  setSelectedVehicle: (vehicle: Vehicle | null) => void;
  setSelectedTrip: (trip: Trip | null) => void;
  setSelectedDelivery: (delivery: DeliveryTask | null) => void;
  setTrackingLive: (status: boolean) => void;
  setTrackingVehicleId: (id: number | null) => void;
}

export const useTransportStore = create<TransportState>((set) => ({
  selectedVehicle: null,
  selectedTrip: null,
  selectedDelivery: null,
  isTrackingLive: false,
  trackingVehicleId: null,

  setSelectedVehicle: (vehicle) => set({ selectedVehicle: vehicle }),
  setSelectedTrip: (trip) => set({ selectedTrip: trip }),
  setSelectedDelivery: (delivery) => set({ selectedDelivery: delivery }),
  setTrackingLive: (status) => set({ isTrackingLive: status }),
  setTrackingVehicleId: (id) => set({ trackingVehicleId: id }),
}));