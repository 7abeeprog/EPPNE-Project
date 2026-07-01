// app/(dashboard)/transport/fleets/page.tsx
'use client';

import { useState } from 'react';
import { useFleets, useCreateFleet, useDeleteFleet } from '@/hooks/transport/useFleets';
import { useVehicles } from '@/hooks/transport/useVehicles';
import { Loader2, Plus, Trash2, Edit, Truck, Users, X } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function FleetsPage() {
  const [showForm, setShowForm] = useState(false);
  const [fleetName, setFleetName] = useState('');

  const { data: fleets, isLoading } = useFleets();
  const { data: vehicles } = useVehicles();
  const createFleet = useCreateFleet();
  const deleteFleet = useDeleteFleet();

  const handleSubmit = () => {
    createFleet.mutate({ name: fleetName }, {
      onSuccess: () => {
        setShowForm(false);
        setFleetName('');
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
            الأساطيل
          </h1>
          <p className="text-sm text-muted-foreground/70">إدارة مجموعات المركبات</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          أسطول جديد
        </button>
      </div>

      {showForm && (
        <div className="p-6 rounded-2xl bg-card/30 backdrop-blur-xl border border-white/10 space-y-4">
          <h3 className="text-lg font-semibold text-foreground/90">✏️ إنشاء أسطول جديد</h3>
          <div className="flex gap-4">
            <input
              type="text"
              value={fleetName}
              onChange={(e) => setFleetName(e.target.value)}
              placeholder="اسم الأسطول"
              className="flex-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            />
            <button
              onClick={handleSubmit}
              disabled={createFleet.isPending || !fleetName}
              className="px-6 py-2 rounded-xl bg-primary text-primary-foreground font-medium disabled:opacity-50 flex items-center gap-2"
            >
              {createFleet.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              إنشاء
            </button>
            <button
              onClick={() => { setShowForm(false); setFleetName(''); }}
              className="px-6 py-2 rounded-xl border border-white/10 hover:bg-white/5 transition-colors"
            >
              إلغاء
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {fleets?.map((fleet) => {
          const fleetVehicles = vehicles?.filter((v) => v.fleet_id === fleet.id);
          return (
            <div
              key={fleet.id}
              className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-foreground/80">{fleet.name}</h4>
                  <p className="text-xs text-muted-foreground/50 flex items-center gap-1">
                    <Users className="w-3 h-3" />
                    {fleetVehicles?.length || 0} مركبة
                  </p>
                </div>
                <div className="flex items-center gap-1">
                  <button className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
                    <Edit className="w-3.5 h-3.5 text-muted-foreground/50" />
                  </button>
                  <button
                    onClick={() => deleteFleet.mutate(fleet.id)}
                    className="p-1.5 rounded-lg hover:bg-red-500/10 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5 text-red-500/50 hover:text-red-500" />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}