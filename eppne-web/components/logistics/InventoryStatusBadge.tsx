// components/logistics/InventoryStatusBadge.tsx
'use client';

import { cn } from '@/lib/utils';
import { CheckCircle, Clock, AlertTriangle, XCircle, Truck } from 'lucide-react';
import type { InventoryStatus } from '@/types/logistics';

interface InventoryStatusBadgeProps {
  status: InventoryStatus;
  className?: string;
}

const statusConfig: Record<InventoryStatus, { label: string; color: string; icon: React.ReactNode }> = {
  AVAILABLE: {
    label: 'متوفر',
    color: 'border-emerald-500/30 text-emerald-500 bg-emerald-500/5',
    icon: <CheckCircle className="w-3.5 h-3.5" />,
  },
  RESERVED: {
    label: 'محجوز',
    color: 'border-amber-500/30 text-amber-500 bg-amber-500/5',
    icon: <Clock className="w-3.5 h-3.5" />,
  },
  DAMAGED: {
    label: 'تالف',
    color: 'border-red-500/30 text-red-500 bg-red-500/5',
    icon: <AlertTriangle className="w-3.5 h-3.5" />,
  },
  EXPIRED: {
    label: 'منتهي الصلاحية',
    color: 'border-red-500/30 text-red-500 bg-red-500/5',
    icon: <XCircle className="w-3.5 h-3.5" />,
  },
  IN_TRANSIT: {
    label: 'قيد النقل',
    color: 'border-blue-500/30 text-blue-500 bg-blue-500/5',
    icon: <Truck className="w-3.5 h-3.5" />,
  },
};

export default function InventoryStatusBadge({ status, className }: InventoryStatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full border", config.color, className)}>
      {config.icon}
      {config.label}
    </span>
  );
}