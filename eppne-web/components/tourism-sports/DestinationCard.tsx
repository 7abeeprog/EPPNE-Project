// components/tourism-sports/DestinationCard.tsx
'use client';

import { MapPin, Globe, Rocket } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { TourismDestination } from '@/types/tourism-sports';

interface DestinationCardProps {
  destination: TourismDestination;
  onClick?: () => void;
}

const typeIcons = {
  LOCAL: <MapPin className="w-4 h-4" />,
  INTERNATIONAL: <Globe className="w-4 h-4" />,
  CRUISE_PORT: <Globe className="w-4 h-4" />,
  SPACE_STATION: <Rocket className="w-4 h-4" />,
};

export default function DestinationCard({ destination, onClick }: DestinationCardProps) {
  return (
    <div
      onClick={onClick}
      className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all cursor-pointer"
    >
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-foreground/80">{destination.name}</h4>
        <span className="text-xs text-muted-foreground/50 flex items-center gap-1">
          {typeIcons[destination.destination_type]}
          {destination.destination_type}
        </span>
      </div>
      {destination.planet_body && (
        <p className="text-xs text-muted-foreground/40 mt-1">🌍 {destination.planet_body}</p>
      )}
      {destination.description && (
        <p className="text-sm text-muted-foreground/60 mt-2 line-clamp-2">{destination.description}</p>
      )}
      <div className="mt-2 text-xs text-muted-foreground/30">
        {destination.is_active ? '🟢 نشط' : '🔴 غير نشط'}
      </div>
    </div>
  );
}