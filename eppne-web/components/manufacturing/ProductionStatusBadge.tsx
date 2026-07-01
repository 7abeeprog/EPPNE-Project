// components/manufacturing/ProductionStatusBadge.tsx
'use client';

import { cn } from '@/lib/utils';
import { Clock, Play, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import type { ProductionStatus } from '@/types/manufacturing';

interface ProductionStatusBadgeProps {
  status: ProductionStatus;
  className?: string;
}

const statusConfig: Record<ProductionStatus, { label: string; color: string; icon: React.ReactNode }> = {
  PLANNED: {
    label: 'مخطط',
    color: 'border-blue-500/30 text-blue-500 bg-blue-500/5',
    icon: <Clock className="w-3.5 h-3.5" />,
  },
  IN_PROGRESS: {
    label: 'قيد الإنتاج',
    color: 'border-amber-500/30 text-amber-500 bg-amber-500/5',
    icon: <Play className="w-3.5 h-3.5 animate-pulse" />,
  },
  QC_TESTING: {
    label: 'فحص جودة',
    color: 'border-purple-500/30 text-purple-500 bg-purple-500/5',
    icon: <RefreshCw className="w-3.5 h-3.5" />,
  },
  COMPLETED: {
    label: 'مكتمل',
    color: 'border-emerald-500/30 text-emerald-500 bg-emerald-500/5',
    icon: <CheckCircle className="w-3.5 h-3.5" />,
  },
  REJECTED: {
    label: 'مرفوض',
    color: 'border-red-500/30 text-red-500 bg-red-500/5',
    icon: <XCircle className="w-3.5 h-3.5" />,
  },
};

export default function ProductionStatusBadge({ status, className }: ProductionStatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border", config.color, className)}>
      {config.icon}
      {config.label}
    </span>
  );
}