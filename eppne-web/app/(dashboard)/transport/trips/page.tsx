// app/(dashboard)/transport/trips/page.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMyTrips, useCreateTrip, useStartTrip, useCompleteTrip, useCancelTrip } from '@/hooks/transport/useTrips';
import { useAvailableVehicles } from '@/hooks/transport/useVehicles';
import { useRoutes } from '@/hooks/transport/useRoutes';
import { useDrivers } from '@/hooks/transport/useDrivers';
import TripStatusBadge from '@/components/transport/TripStatusBadge';
import CarbonFootprintBadge from '@/components/transport/CarbonFootprintBadge';
import { Loader2, Plus, Play, CheckCircle, XCircle, Calendar, Truck, User, Route as RouteIcon, Filter, Search, Eye, ChevronDown, ChevronUp, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns/ar';
import type { TripStatus, TripCategory } from '@/types/transport';

const categoryLabels: Record<TripCategory, string> = {
  PASSENGER: 'ركاب',
  FREIGHT: 'شحن',
  MASS_TRANSIT: 'نقل عام',
  TOURISM: 'سياحة',
  MEDICAL: 'طبي',
  EDUCATIONAL: 'تعليمي',
};

export default function TripsPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState<TripStatus | ''>('');
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedTrip, setExpandedTrip] = useState<number | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);

  const { data: trips, isLoading: tripsLoading, refetch } = useMyTrips({
    ...(statusFilter && { status: statusFilter }),
    limit: 50,
  });

  const { data: vehicles, isLoading: vehiclesLoading } = useAvailableVehicles();
  const { data: routes, isLoading: routesLoading } = useRoutes();
  const { data: drivers, isLoading: driversLoading } = useDrivers();

  const createTrip = useCreateTrip();
  const startTrip = useStartTrip();
  const completeTrip = useCompleteTrip();
  const cancelTrip = useCancelTrip();

  const [formData, setFormData] = useState({
    route_id: '',
    vehicle_id: '',
    driver_id: '',
    trip_category: 'PASSENGER' as TripCategory,
    scheduled_start: '',
    scheduled_end: '',
    base_fare_mrusdt: 0,
  });

  const isLoading = tripsLoading || vehiclesLoading || routesLoading || driversLoading;

  const handleCreateTrip = (e: React.FormEvent) => {
    e.preventDefault();
    createTrip.mutate({
      route_id: parseInt(formData.route_id),
      vehicle_id: parseInt(formData.vehicle_id),
      driver_id: parseInt(formData.driver_id),
      trip_category: formData.trip_category,
      scheduled_start: formData.scheduled_start,
      scheduled_end: formData.scheduled_end,
      base_fare_mrusdt: parseFloat(formData.base_fare_mrusdt.toString()),
    });
    setShowCreateForm(false);
    resetForm();
  };

  const resetForm = () => {
    setFormData({
      route_id: '',
      vehicle_id: '',
      driver_id: '',
      trip_category: 'PASSENGER',
      scheduled_start: '',
      scheduled_end: '',
      base_fare_mrusdt: 0,
    });
  };

  const filteredTrips = trips?.filter((trip) =>
    trip.id.toString().includes(searchTerm) ||
    (trip.driver_name || '').includes(searchTerm)
  );

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90 flex items-center gap-2">
            🚛 الرحلات
            <span className="text-sm font-normal text-muted-foreground/60">
              ({trips?.length || 0} رحلة)
            </span>
          </h1>
          <p className="text-sm text-muted-foreground/70">إدارة وجدولة الرحلات</p>
        </div>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          رحلة جديدة
        </button>
      </div>

      {showCreateForm && (
        <div className="p-6 rounded-2xl bg-card/30 backdrop-blur-xl border border-white/10 space-y-4">
          <h3 className="text-lg font-semibold text-foreground/90">✏️ إنشاء رحلة جديدة</h3>
          <form onSubmit={handleCreateTrip} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="text-sm text-muted-foreground/60">المسار</label>
              <select
                value={formData.route_id}
                onChange={(e) => setFormData((prev) => ({ ...prev, route_id: e.target.value }))}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                required
              >
                <option value="">اختر مساراً</option>
                {routes?.map((route) => (
                  <option key={route.id} value={route.id}>
                    {route.name} ({route.distance_km} كم)
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">المركبة</label>
              <select
                value={formData.vehicle_id}
                onChange={(e) => setFormData((prev) => ({ ...prev, vehicle_id: e.target.value }))}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                required
              >
                <option value="">اختر مركبة</option>
                {vehicles?.map((vehicle) => (
                  <option key={vehicle.id} value={vehicle.id}>
                    {vehicle.license_plate} ({vehicle.vehicle_type})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">السائق</label>
              <select
                value={formData.driver_id}
                onChange={(e) => setFormData((prev) => ({ ...prev, driver_id: e.target.value }))}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                required
              >
                <option value="">اختر سائقاً</option>
                {drivers?.map((driver) => (
                  <option key={driver.id} value={driver.id}>
                    {driver.name || `سائق #${driver.id}`}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">نوع الرحلة</label>
              <select
                value={formData.trip_category}
                onChange={(e) => setFormData((prev) => ({ ...prev, trip_category: e.target.value as TripCategory }))}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              >
                {Object.entries(categoryLabels).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">بداية الرحلة</label>
              <input
                type="datetime-local"
                value={formData.scheduled_start}
                onChange={(e) => setFormData((prev) => ({ ...prev, scheduled_start: e.target.value }))}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                required
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">نهاية الرحلة المتوقعة</label>
              <input
                type="datetime-local"
                value={formData.scheduled_end}
                onChange={(e) => setFormData((prev) => ({ ...prev, scheduled_end: e.target.value }))}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                required
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">الأجرة الأساسية (MR_USDT)</label>
              <input
                type="number"
                step="0.01"
                value={formData.base_fare_mrusdt}
                onChange={(e) => setFormData((prev) => ({ ...prev, base_fare_mrusdt: parseFloat(e.target.value) || 0 }))}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="0.00"
              />
            </div>
            <div className="md:col-span-2 lg:col-span-3 flex gap-3 pt-2">
              <button
                type="submit"
                disabled={createTrip.isPending}
                className="px-6 py-2 rounded-xl bg-primary text-primary-foreground font-medium disabled:opacity-50 flex items-center gap-2"
              >
                {createTrip.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                {createTrip.isPending ? 'جاري الإنشاء...' : 'إنشاء الرحلة'}
              </button>
              <button
                type="button"
                onClick={() => { setShowCreateForm(false); resetForm(); }}
                className="px-6 py-2 rounded-xl border border-white/10 hover:bg-white/5 transition-colors"
              >
                إلغاء
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <div className="flex items-center gap-2 flex-1 min-w-[200px] bg-white/5 rounded-xl px-3 py-2 border border-white/5">
          <Search className="w-4 h-4 text-muted-foreground/50" />
          <input
            type="text"
            placeholder="ابحث عن رحلة..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-transparent border-0 outline-none text-sm w-full text-foreground/80 placeholder:text-muted-foreground/40"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as TripStatus | '')}
          className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-foreground/80 outline-none focus:border-primary/30"
        >
          <option value="">كل الحالات</option>
          <option value="SCHEDULED">مجدولة</option>
          <option value="ONGOING">قيد التنفيذ</option>
          <option value="COMPLETED">مكتملة</option>
          <option value="CANCELLED">ملغية</option>
          <option value="DELAYED">متأخرة</option>
        </select>
        <button
          onClick={() => refetch()}
          className="px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10 transition-colors text-sm"
        >
          <Loader2 className="w-4 h-4 animate-spin" />
        </button>
      </div>

      {filteredTrips?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <Truck className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد رحلات</p>
          <p className="text-sm">أنشئ رحلة جديدة للبدء</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredTrips?.map((trip) => {
            const isExpanded = expandedTrip === trip.id;

            return (
              <div
                key={trip.id}
                className={cn(
                  "rounded-2xl border transition-all duration-300 bg-card/20 backdrop-blur-sm",
                  trip.status === 'ONGOING' ? "border-emerald-500/30 shadow-[0_0_30px_rgba(52,211,153,0.1)]" : "border-white/10",
                  isExpanded && "border-primary/30 shadow-[0_0_40px_-15px_rgba(var(--primary-rgb),0.15)]"
                )}
              >
                <div
                  className="flex items-center gap-4 p-4 cursor-pointer"
                  onClick={() => setExpandedTrip(isExpanded ? null : trip.id)}
                >
                  <div className={cn(
                    "flex-shrink-0 w-3 h-3 rounded-full",
                    trip.status === 'ONGOING' ? "bg-emerald-500 animate-pulse" :
                    trip.status === 'COMPLETED' ? "bg-gray-500" :
                    trip.status === 'SCHEDULED' ? "bg-blue-500" :
                    "bg-red-500"
                  )} />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3">
                      <h4 className="font-medium text-foreground/80">
                        رحلة #{trip.id}
                      </h4>
                      <TripStatusBadge status={trip.status} />
                      <span className="text-xs text-muted-foreground/50">
                        {categoryLabels[trip.trip_category]}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-3 mt-0.5 text-xs text-muted-foreground/50">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {format(new Date(trip.scheduled_start), 'dd/MM/yyyy HH:mm')}
                      </span>
                      <span className="flex items-center gap-1">
                        <Truck className="w-3 h-3" />
                        مركبة #{trip.vehicle_id}
                      </span>
                      <span className="flex items-center gap-1">
                        <User className="w-3 h-3" />
                        {trip.driver_name || `سائق #${trip.driver_id}`}
                      </span>
                      {trip.total_distance_km > 0 && (
                        <span className="flex items-center gap-1">
                          <RouteIcon className="w-3 h-3" />
                          {trip.total_distance_km} كم
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {trip.status === 'SCHEDULED' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); startTrip.mutate({ tripId: trip.id, actualStart: new Date().toISOString() }); }}
                        disabled={startTrip.isPending}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-emerald-500/20 text-emerald-500 border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors text-sm disabled:opacity-50"
                      >
                        {startTrip.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                        بدء
                      </button>
                    )}
                    {trip.status === 'ONGOING' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); const d = prompt('أدخل المسافة الفعلية (كم):'); if (d) completeTrip.mutate({ tripId: trip.id, actualEnd: new Date().toISOString(), totalDistance: parseFloat(d) }); }}
                        disabled={completeTrip.isPending}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-blue-500/20 text-blue-500 border border-blue-500/30 hover:bg-blue-500/30 transition-colors text-sm disabled:opacity-50"
                      >
                        {completeTrip.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle className="w-3 h-3" />}
                        إنهاء
                      </button>
                    )}
                    {trip.status === 'SCHEDULED' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); if (confirm('هل أنت متأكد من إلغاء هذه الرحلة؟')) cancelTrip.mutate(trip.id); }}
                        disabled={cancelTrip.isPending}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-red-500/20 text-red-500 border border-red-500/30 hover:bg-red-500/30 transition-colors text-sm disabled:opacity-50"
                      >
                        {cancelTrip.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <XCircle className="w-3 h-3" />}
                        إلغاء
                      </button>
                    )}
                    <button className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
                      <Eye className="w-4 h-4 text-muted-foreground/50" />
                    </button>
                  </div>

                  <button className="p-1 rounded-lg hover:bg-white/10 transition-colors">
                    {isExpanded ? <ChevronUp className="w-4 h-4 text-muted-foreground/50" /> : <ChevronDown className="w-4 h-4 text-muted-foreground/50" />}
                  </button>
                </div>

                {isExpanded && (
                  <div className="px-4 pb-4 pt-0 border-t border-white/5 space-y-3">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-3">
                      <div className="p-3 rounded-xl bg-white/5">
                        <p className="text-xs text-muted-foreground/50">المسافة</p>
                        <p className="text-sm font-medium text-foreground/80">{trip.total_distance_km || '—'} كم</p>
                      </div>
                      <div className="p-3 rounded-xl bg-white/5">
                        <p className="text-xs text-muted-foreground/50">البصمة الكربونية</p>
                        {trip.total_distance_km > 0 ? (
                          <CarbonFootprintBadge carbonKg={trip.carbon_footprint_kg} distanceKm={trip.total_distance_km} />
                        ) : (
                          <p className="text-sm font-medium text-foreground/80">—</p>
                        )}
                      </div>
                      <div className="p-3 rounded-xl bg-white/5">
                        <p className="text-xs text-muted-foreground/50">الأجرة الأساسية</p>
                        <p className="text-sm font-medium text-foreground/80">{trip.base_fare_mrusdt} MR_USDT</p>
                      </div>
                      <div className="p-3 rounded-xl bg-white/5">
                        <p className="text-xs text-muted-foreground/50">الحالة</p>
                        <TripStatusBadge status={trip.status} />
                      </div>
                    </div>
                    {trip.actual_start && (
                      <p className="text-xs text-muted-foreground/50">
                        بدأت فعلياً: {format(new Date(trip.actual_start), 'dd/MM/yyyy HH:mm')}
                      </p>
                    )}
                    {trip.actual_end && (
                      <p className="text-xs text-muted-foreground/50">
                        انتهت فعلياً: {format(new Date(trip.actual_end), 'dd/MM/yyyy HH:mm')}
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}