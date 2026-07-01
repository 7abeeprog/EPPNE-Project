// app/(dashboard)/transport/vehicles/page.tsx
'use client';

import { useState } from 'react';
import { useVehicles, useCreateVehicle, useDeleteVehicle } from '@/hooks/transport/useVehicles';
import { useFleets } from '@/hooks/transport/useFleets';
import VehicleStatusBadge from '@/components/transport/VehicleStatusBadge';
import { Loader2, Plus, Trash2, Edit, Truck, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { TransportType, VehicleStatus } from '@/types/transport';

const vehicleTypeLabels: Record<TransportType, string> = {
  BICYCLE: 'دراجة',
  MOTORCYCLE: 'دراجة نارية',
  CAR: 'سيارة',
  BUS: 'حافلة',
  TRUCK: 'شاحنة',
  SHIP: 'سفينة',
  AIRCRAFT: 'طائرة',
  SPACECRAFT: 'مركبة فضائية',
  TRAIN: 'قطار',
};

const statusOptions: { value: VehicleStatus; label: string }[] = [
  { value: 'AVAILABLE', label: 'متاحة' },
  { value: 'IN_TRIP', label: 'في رحلة' },
  { value: 'MAINTENANCE', label: 'صيانة' },
  { value: 'OUT_OF_SERVICE', label: 'خارج الخدمة' },
];

export default function VehiclesPage() {
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    fleet_id: 0,
    license_plate: '',
    vehicle_type: 'CAR' as TransportType,
    capacity_kg: undefined as number | undefined,
    capacity_passengers: undefined as number | undefined,
    fuel_type: 'ELECTRIC',
    carbon_per_km: 0,
  });

  const { data: vehicles, isLoading } = useVehicles();
  const { data: fleets } = useFleets();
  const createVehicle = useCreateVehicle();
  const deleteVehicle = useDeleteVehicle();

  const handleSubmit = () => {
    createVehicle.mutate(formData, {
      onSuccess: () => {
        setShowForm(false);
        setFormData({ fleet_id: 0, license_plate: '', vehicle_type: 'CAR', capacity_kg: undefined, capacity_passengers: undefined, fuel_type: 'ELECTRIC', carbon_per_km: 0 });
      },
    });
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90 flex items-center gap-2">
            <Truck className="w-6 h-6 text-primary" />
            المركبات
          </h1>
          <p className="text-sm text-muted-foreground/70">إدارة المركبات في الأساطيل</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          مركبة جديدة
        </button>
      </div>

      {showForm && (
        <div className="p-6 rounded-2xl bg-card/30 backdrop-blur-xl border border-white/10 space-y-4">
          <h3 className="text-lg font-semibold text-foreground/90">✏️ إضافة مركبة جديدة</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-muted-foreground/60">الأسطول</label>
              <select
                value={formData.fleet_id}
                onChange={(e) => setFormData({ ...formData, fleet_id: parseInt(e.target.value) })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              >
                <option value="">اختر أسطولاً</option>
                {fleets?.map((f) => (
                  <option key={f.id} value={f.id}>{f.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">رقم اللوحة</label>
              <input
                type="text"
                value={formData.license_plate}
                onChange={(e) => setFormData({ ...formData, license_plate: e.target.value })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="ABC123"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">نوع المركبة</label>
              <select
                value={formData.vehicle_type}
                onChange={(e) => setFormData({ ...formData, vehicle_type: e.target.value as TransportType })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              >
                {Object.entries(vehicleTypeLabels).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">نوع الوقود</label>
              <select
                value={formData.fuel_type}
                onChange={(e) => setFormData({ ...formData, fuel_type: e.target.value })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              >
                <option value="ELECTRIC">كهربائي</option>
                <option value="FUEL">وقود</option>
                <option value="HYBRID">هجين</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">السعة (كجم)</label>
              <input
                type="number"
                value={formData.capacity_kg || ''}
                onChange={(e) => setFormData({ ...formData, capacity_kg: parseFloat(e.target.value) || undefined })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="1000"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">عدد الركاب</label>
              <input
                type="number"
                value={formData.capacity_passengers || ''}
                onChange={(e) => setFormData({ ...formData, capacity_passengers: parseInt(e.target.value) || undefined })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="4"
              />
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              onClick={handleSubmit}
              disabled={createVehicle.isPending || !formData.license_plate || !formData.fleet_id}
              className="px-6 py-2 rounded-xl bg-primary text-primary-foreground font-medium disabled:opacity-50 flex items-center gap-2"
            >
              {createVehicle.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              إضافة
            </button>
            <button
              onClick={() => { setShowForm(false); setFormData({ fleet_id: 0, license_plate: '', vehicle_type: 'CAR', capacity_kg: undefined, capacity_passengers: undefined, fuel_type: 'ELECTRIC', carbon_per_km: 0 }); }}
              className="px-6 py-2 rounded-xl border border-white/10 hover:bg-white/5 transition-colors"
            >
              إلغاء
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {vehicles?.map((vehicle) => (
          <div
            key={vehicle.id}
            className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Truck className="w-5 h-5 text-primary/60" />
                <h4 className="font-medium text-foreground/80">{vehicle.license_plate}</h4>
              </div>
              <div className="flex items-center gap-1">
                <button className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
                  <Edit className="w-3.5 h-3.5 text-muted-foreground/50" />
                </button>
                <button
                  onClick={() => deleteVehicle.mutate(vehicle.id)}
                  className="p-1.5 rounded-lg hover:bg-red-500/10 transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5 text-red-500/50 hover:text-red-500" />
                </button>
              </div>
            </div>
            <div className="mt-2 space-y-1 text-xs text-muted-foreground/50">
              <div className="flex justify-between">
                <span>النوع</span>
                <span className="text-foreground/70">{vehicleTypeLabels[vehicle.vehicle_type]}</span>
              </div>
              <div className="flex justify-between">
                <span>الحالة</span>
                <VehicleStatusBadge status={vehicle.status} />
              </div>
              {vehicle.capacity_kg && (
                <div className="flex justify-between">
                  <span>السعة</span>
                  <span className="text-foreground/70">{vehicle.capacity_kg} كجم</span>
                </div>
              )}
              {vehicle.capacity_passengers && (
                <div className="flex justify-between">
                  <span>الركاب</span>
                  <span className="text-foreground/70">{vehicle.capacity_passengers}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span>الكربون/كم</span>
                <span className="text-foreground/70">{vehicle.carbon_per_km} كجم</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}