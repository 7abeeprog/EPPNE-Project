// components/marketplace/DeploymentStatusBadge.tsx
'use client';

import { cn } from '@/lib/utils';
import { Loader2, CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react';
import type { DeploymentStatus } from '@/types/marketplace';

interface DeploymentStatusBadgeProps {
  status: DeploymentStatus;
  className?: string;
  showLabel?: boolean;
}

const statusConfig: Record<DeploymentStatus, {
  label: string;
  icon: React.ReactNode;
  className: string;
}> = {
  PENDING: {
    label: 'قيد الانتظار',
    icon: <Clock className="w-3.5 h-3.5" />,
    className: 'text-amber-500 bg-amber-500/10 border-amber-500/30',
  },
  DEPLOYING: {
    label: 'جاري النشر',
    icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
    className: 'text-blue-500 bg-blue-500/10 border-blue-500/30',
  },
  ACTIVE: {
    label: 'نشط',
    icon: <CheckCircle className="w-3.5 h-3.5" />,
    className: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30',
  },
  FAILED: {
    label: 'فشل',
    icon: <XCircle className="w-3.5 h-3.5" />,
    className: 'text-red-500 bg-red-500/10 border-red-500/30',
  },
  SUSPENDED: {
    label: 'معلق',
    icon: <AlertTriangle className="w-3.5 h-3.5" />,
    className: 'text-orange-500 bg-orange-500/10 border-orange-500/30',
  },
};

export default function DeploymentStatusBadge({ status, className, showLabel = true }: DeploymentStatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.PENDING;

  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border backdrop-blur-sm transition-all duration-300",
      config.className,
      className
    )}>
      {config.icon}
      {showLabel && config.label}
    </span>
  );
}