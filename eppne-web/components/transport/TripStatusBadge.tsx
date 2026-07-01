// components/transport/TripStatusBadge.tsx
'use client';

import { cn } from '@/lib/utils';
import { Calendar, Play, CheckCircle, XCircle, Clock } from 'lucide-react';
import type { TripStatus } from '@/types/transport';

interface TripStatusBadgeProps {
  status: TripStatus;
  className?: string;
}

const statusConfig: Record<TripStatus, { label: string; color: string; icon: React.ReactNode }> = {
  SCHEDULED: {
    label: 'مجدولة',
    color: 'border-blue-500/30 text-blue-500 bg-blue-500/5',
    icon: <Calendar className="w-3.5 h-3.5" />,
  },
  ONGOING: {
    label: 'قيد التنفيذ',
    color: 'border-emerald-500/30 text-emerald-500 bg-emerald-500/5 animate-pulse',
    icon: <Play className="w-3.5 h-3.5" />,
  },
  COMPLETED: {
    label: 'مكتملة',
    color: 'border-gray-500/30 text-gray-400 bg-gray-500/5',
    icon: <CheckCircle className="w-3.5 h-3.5" />,
  },
  CANCELLED: {
    label: 'ملغية',
    color: 'border-red-500/30 text-red-500 bg-red-500/5',
    icon: <XCircle className="w-3.5 h-3.5" />,
  },
  DELAYED: {
    label: 'متأخرة',
    color: 'border-amber-500/30 text-amber-500 bg-amber-500/5',
    icon: <Clock className="w-3.5 h-3.5" />,
  },
};

export default function TripStatusBadge({ status, className }: TripStatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border", config.color, className)}>
      {config.icon}
      {config.label}
    </span>
  );
}