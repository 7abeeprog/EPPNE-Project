// components/realestate/MasterPlanExplorer.tsx
'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getMyLands } from '@/services/realestate';
import { Loader2, Map, Building2, Layers, Calendar } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { LandAsset } from '@/types/realestate';

interface MasterPlanExplorerProps {
  onSelectLand?: (land: LandAsset) => void;
}

export default function MasterPlanExplorer({ onSelectLand }: MasterPlanExplorerProps) {
  const [selectedLandId, setSelectedLandId] = useState<number | null>(null);

  const { data: lands, isLoading } = useQuery({
    queryKey: ['my-lands'],
    queryFn: () => getMyLands({ limit: 20 }).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-48">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  if (!lands || lands.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground/60">
        <Map className="w-12 h-12 mx-auto mb-4 opacity-30" />
        <p className="text-lg">لا توجد أراضي مسجلة</p>
        <p className="text-sm">أضف أرضاً جديدة لبدء التخطيط العمراني</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {lands.map((land) => (
          <button
            key={land.id}
            onClick={() => {
              setSelectedLandId(land.id);
              onSelectLand?.(land);
            }}
            className={cn(
              "p-4 rounded-2xl border transition-all duration-300 text-right",
              "bg-card/20 backdrop-blur-xl hover:bg-card/30",
              selectedLandId === land.id
                ? "border-primary/50 shadow-[0_0_40px_-15px_rgba(var(--primary-rgb),0.15)]"
                : "border-white/10 hover:border-primary/20"
            )}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-primary/10 text-primary">
                  <Layers className="w-4 h-4" />
                </div>
                <div className="text-right">
                  <h4 className="font-medium text-foreground/90">{land.plot_number}</h4>
                  <p className="text-xs text-muted-foreground/50">
                    {land.area_sqm.toFixed(0)} م² • {land.zoning}
                  </p>
                </div>
              </div>
              <span className="text-xs text-primary/80 font-medium">
                {land.current_value_mrusdt.toFixed(2)} MR_USDT
              </span>
            </div>

            <div className="mt-2 flex items-center gap-4 text-xs text-muted-foreground/40">
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                {new Date(land.created_at).toLocaleDateString('ar-EG')}
              </span>
              <span className={cn(
                "px-2 py-0.5 rounded-full border",
                land.legal_status === 'REGISTERED' ? "border-emerald-500/30 text-emerald-500" :
                land.legal_status === 'DISPUTED' ? "border-red-500/30 text-red-500" :
                "border-amber-500/30 text-amber-500"
              )}>
                {land.legal_status}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}