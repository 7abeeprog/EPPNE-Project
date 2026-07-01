// components/transport/VehicleStatusBadge.tsx
'use client';

import { cn } from '@/lib/utils';
import { CheckCircle, Clock, Wrench, XCircle } from 'lucide-react';
import type { VehicleStatus } from '@/types/transport';

interface VehicleStatusBadgeProps {
  status: VehicleStatus;
  className?: string;
}

const statusConfig: Record<VehicleStatus, { label: string; color: string; icon: React.ReactNode }> = {
  AVAILABLE: {
    label: 'متاحة',
    color: 'border-emerald-500/30 text-emerald-500 bg-emerald-500/5',
    icon: <CheckCircle className="w-3.5 h-3.5" />,
  },
  IN_TRIP: {
    label: 'في رحلة',
    color: 'border-blue-500/30 text-blue-500 bg-blue-500/5',
    icon: <Clock className="w-3.5 h-3.5 animate-pulse" />,
  },
  MAINTENANCE: {
    label: 'صيانة',
    color: 'border-amber-500/30 text-amber-500 bg-amber-500/5',
    icon: <Wrench className="w-3.5 h-3.5" />,
  },
  OUT_OF_SERVICE: {
    label: 'خارج الخدمة',
    color: 'border-red-500/30 text-red-500 bg-red-500/5',
    icon: <XCircle className="w-3.5 h-3.5" />,
  },
};

export default function VehicleStatusBadge({ status, className }: VehicleStatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border", config.color, className)}>
      {config.icon}
      {config.label}
    </span>
  );
}