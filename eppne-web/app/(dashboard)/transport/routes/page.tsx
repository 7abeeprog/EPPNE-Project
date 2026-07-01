// app/(dashboard)/transport/routes/page.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useRoutes, useCreateRoute, useDeleteRoute } from '@/hooks/transport/useRoutes';
import { useHubs } from '@/hooks/transport/useHubs';
import RouteOptimizer from '@/components/transport/RouteOptimizer';
import { Loader2, Plus, Trash2, Edit, Route as RouteIcon, MapPin, Clock, Ruler, Sparkles, X } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function RoutesPage() {
  const router = useRouter();
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    start_hub_id: 0,
    end_hub_id: 0,
    waypoints: [] as Array<{ lat: number; lng: number; name?: string }>,
    distance_km: 0,
    estimated_duration_minutes: 0,
  });

  const { data: routes, isLoading } = useRoutes();
  const { data: hubs } = useHubs();
  const createRoute = useCreateRoute();
  const deleteRoute = useDeleteRoute();
  const [optimizedData, setOptimizedData] = useState<any>(null);

  const handleSubmit = () => {
    createRoute.mutate(formData, {
      onSuccess: () => {
        setShowForm(false);
        setFormData({ name: '', start_hub_id: 0, end_hub_id: 0, waypoints: [], distance_km: 0, estimated_duration_minutes: 0 });
        setOptimizedData(null);
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
            <RouteIcon className="w-6 h-6 text-primary" />
            المسارات
          </h1>
          <p className="text-sm text-muted-foreground/70">إدارة مسارات النقل</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          مسار جديد
        </button>
      </div>

      {showForm && (
        <div className="p-6 rounded-2xl bg-card/30 backdrop-blur-xl border border-white/10 space-y-4">
          <h3 className="text-lg font-semibold text-foreground/90 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            إنشاء مسار جديد
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-muted-foreground/60">اسم المسار</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="اسم المسار"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">محطة البداية</label>
              <select
                value={formData.start_hub_id}
                onChange={(e) => setFormData({ ...formData, start_hub_id: parseInt(e.target.value) })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              >
                <option value="">اختر محطة</option>
                {hubs?.map((h) => (
                  <option key={h.id} value={h.id}>{h.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">محطة النهاية</label>
              <select
                value={formData.end_hub_id}
                onChange={(e) => setFormData({ ...formData, end_hub_id: parseInt(e.target.value) })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              >
                <option value="">اختر محطة</option>
                {hubs?.map((h) => (
                  <option key={h.id} value={h.id}>{h.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">المسافة (كم)</label>
              <input
                type="number"
                step="0.1"
                value={formData.distance_km}
                onChange={(e) => setFormData({ ...formData, distance_km: parseFloat(e.target.value) })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="0.0"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">المدة المتوقعة (دقيقة)</label>
              <input
                type="number"
                value={formData.estimated_duration_minutes}
                onChange={(e) => setFormData({ ...formData, estimated_duration_minutes: parseInt(e.target.value) })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="30"
              />
            </div>
          </div>

          {/* محسن المسارات */}
          <RouteOptimizer
            startHubId={formData.start_hub_id}
            endHubId={formData.end_hub_id}
            onOptimized={(data) => {
              setOptimizedData(data);
              setFormData((prev) => ({
                ...prev,
                distance_km: data.distance_km,
                estimated_duration_minutes: data.estimated_duration_minutes,
                waypoints: data.waypoints || [],
              }));
            }}
          />

          <div className="flex gap-3 pt-2">
            <button
              onClick={handleSubmit}
              disabled={createRoute.isPending || !formData.name || !formData.start_hub_id || !formData.end_hub_id}
              className="px-6 py-2 rounded-xl bg-primary text-primary-foreground font-medium disabled:opacity-50 flex items-center gap-2"
            >
              {createRoute.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              إنشاء
            </button>
            <button
              onClick={() => { setShowForm(false); setFormData({ name: '', start_hub_id: 0, end_hub_id: 0, waypoints: [], distance_km: 0, estimated_duration_minutes: 0 }); setOptimizedData(null); }}
              className="px-6 py-2 rounded-xl border border-white/10 hover:bg-white/5 transition-colors"
            >
              إلغاء
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {routes?.map((route) => {
          const startHub = hubs?.find((h) => h.id === route.start_hub_id);
          const endHub = hubs?.find((h) => h.id === route.end_hub_id);
          return (
            <div
              key={route.id}
              className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all cursor-pointer"
              onClick={() => router.push(`/transport/routes/${route.id}`)}
            >
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-foreground/80">{route.name}</h4>
                  <p className="text-xs text-muted-foreground/50 flex items-center gap-1">
                    <MapPin className="w-3 h-3" />
                    {startHub?.name || '?'} → {endHub?.name || '?'}
                  </p>
                </div>
                <div className="flex items-center gap-1">
                  <button className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
                    <Edit className="w-3.5 h-3.5 text-muted-foreground/50" />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteRoute.mutate(route.id); }}
                    className="p-1.5 rounded-lg hover:bg-red-500/10 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5 text-red-500/50 hover:text-red-500" />
                  </button>
                </div>
              </div>
              <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground/50">
                <span className="flex items-center gap-1">
                  <Ruler className="w-3 h-3" />
                  {route.distance_km} كم
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {route.estimated_duration_minutes} د
                </span>
                {route.waypoints && route.waypoints.length > 0 && (
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3 h-3" />
                    {route.waypoints.length} نقاط
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}