// components/transport/TransportStatsCards.tsx
'use client';

import { cn } from '@/lib/utils';
import { Truck, MapPin, Route, Package, Leaf, Users } from 'lucide-react';
import type { TransportStats } from '@/types/transport';

interface TransportStatsCardsProps {
  stats: TransportStats;
  className?: string;
}

const statConfigs = [
  { key: 'total_hubs', label: 'المحطات', icon: MapPin, color: 'text-blue-500' },
  { key: 'total_routes', label: 'المسارات', icon: Route, color: 'text-purple-500' },
  { key: 'total_vehicles', label: 'المركبات', icon: Truck, color: 'text-primary' },
  { key: 'available_vehicles', label: 'متاحة', icon: Users, color: 'text-emerald-500' },
  { key: 'active_trips', label: 'رحلات نشطة', icon: MapPin, color: 'text-amber-500' },
  { key: 'total_deliveries', label: 'توصيلات', icon: Package, color: 'text-cyan-500' },
  { key: 'total_carbon_saved', label: 'كربون مُوفر', icon: Leaf, color: 'text-green-500' },
];

export default function TransportStatsCards({ stats, className }: TransportStatsCardsProps) {
  return (
    <div className={cn("grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3", className)}>
      {statConfigs.map((config) => {
        const value = stats[config.key as keyof TransportStats];
        return (
          <div
            key={config.key}
            className="p-3 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all"
          >
            <div className="flex items-center gap-2">
              <config.icon className={cn("w-4 h-4", config.color)} />
              <span className="text-[10px] text-muted-foreground/50">{config.label}</span>
            </div>
            <p className="mt-1 text-lg font-bold text-foreground/90">{value || 0}</p>
          </div>
        );
      })}
    </div>
  );
}