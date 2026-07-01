// app/(dashboard)/transport/hubs/page.tsx
'use client';

import { useState } from 'react';
import { useHubs, useCreateHub, useDeleteHub } from '@/hooks/transport/useHubs';
import { Loader2, Plus, Trash2, Edit, MapPin, Building2, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { HubType } from '@/types/transport';

const hubTypeLabels: Record<HubType, string> = {
  BUS_STATION: 'محطة حافلات',
  PORT: 'ميناء',
  AIRPORT: 'مطار',
  SPACE_PORT: 'ميناء فضائي',
  RAILWAY_STATION: 'محطة قطار',
};

export default function HubsPage() {
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    hub_type: 'BUS_STATION' as HubType,
    region: '',
    gps_location: { lat: 0, lng: 0 },
  });

  const { data: hubs, isLoading } = useHubs();
  const createHub = useCreateHub();
  const deleteHub = useDeleteHub();

  const handleSubmit = () => {
    createHub.mutate(formData, {
      onSuccess: () => {
        setShowForm(false);
        setFormData({ name: '', hub_type: 'BUS_STATION', region: '', gps_location: { lat: 0, lng: 0 } });
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
            <MapPin className="w-6 h-6 text-primary" />
            المحطات
          </h1>
          <p className="text-sm text-muted-foreground/70">إدارة محطات النقل</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          محطة جديدة
        </button>
      </div>

      {showForm && (
        <div className="p-6 rounded-2xl bg-card/30 backdrop-blur-xl border border-white/10 space-y-4">
          <h3 className="text-lg font-semibold text-foreground/90">✏️ إنشاء محطة جديدة</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-muted-foreground/60">الاسم</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="اسم المحطة"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">النوع</label>
              <select
                value={formData.hub_type}
                onChange={(e) => setFormData({ ...formData, hub_type: e.target.value as HubType })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              >
                {Object.entries(hubTypeLabels).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">المنطقة</label>
              <input
                type="text"
                value={formData.region}
                onChange={(e) => setFormData({ ...formData, region: e.target.value })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="المنطقة"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">الموقع (GPS)</label>
              <div className="flex gap-2 mt-1">
                <input
                  type="number"
                  step="0.000001"
                  value={formData.gps_location.lat}
                  onChange={(e) => setFormData({ ...formData, gps_location: { ...formData.gps_location, lat: parseFloat(e.target.value) } })}
                  className="w-1/2 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                  placeholder="Lat"
                />
                <input
                  type="number"
                  step="0.000001"
                  value={formData.gps_location.lng}
                  onChange={(e) => setFormData({ ...formData, gps_location: { ...formData.gps_location, lng: parseFloat(e.target.value) } })}
                  className="w-1/2 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                  placeholder="Lng"
                />
              </div>
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              onClick={handleSubmit}
              disabled={createHub.isPending || !formData.name}
              className="px-6 py-2 rounded-xl bg-primary text-primary-foreground font-medium disabled:opacity-50 flex items-center gap-2"
            >
              {createHub.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              إنشاء
            </button>
            <button
              onClick={() => { setShowForm(false); setFormData({ name: '', hub_type: 'BUS_STATION', region: '', gps_location: { lat: 0, lng: 0 } }); }}
              className="px-6 py-2 rounded-xl border border-white/10 hover:bg-white/5 transition-colors"
            >
              إلغاء
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {hubs?.map((hub) => (
          <div
            key={hub.id}
            className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Building2 className="w-5 h-5 text-primary/60" />
                <h4 className="font-medium text-foreground/80">{hub.name}</h4>
              </div>
              <div className="flex items-center gap-1">
                <button className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
                  <Edit className="w-3.5 h-3.5 text-muted-foreground/50" />
                </button>
                <button
                  onClick={() => deleteHub.mutate(hub.id)}
                  className="p-1.5 rounded-lg hover:bg-red-500/10 transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5 text-red-500/50 hover:text-red-500" />
                </button>
              </div>
            </div>
            <div className="mt-2 text-xs text-muted-foreground/50 space-y-0.5">
              <div className="flex justify-between">
                <span>النوع</span>
                <span className="text-foreground/70">{hubTypeLabels[hub.hub_type]}</span>
              </div>
              {hub.region && (
                <div className="flex justify-between">
                  <span>المنطقة</span>
                  <span className="text-foreground/70">{hub.region}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span>الموقع</span>
                <span className="text-foreground/70 font-mono text-[10px]">
                  {hub.gps_location.lat.toFixed(4)}, {hub.gps_location.lng.toFixed(4)}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}