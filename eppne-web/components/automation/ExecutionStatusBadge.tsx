// components/automation/ExecutionStatusBadge.tsx
'use client';

import { cn } from '@/lib/utils';
import { Loader2, CheckCircle2, XCircle, Clock, AlertCircle } from 'lucide-react';

interface ExecutionStatusBadgeProps {
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'RETRY' | 'CANCELLED';
  className?: string;
  showLabel?: boolean;
}

const statusConfig = {
  PENDING: { label: 'قيد الانتظار', icon: Clock, className: 'text-amber-500 border-amber-500/30 bg-amber-500/10' },
  RUNNING: { label: 'قيد التشغيل', icon: Loader2, className: 'text-blue-500 border-blue-500/30 bg-blue-500/10 animate-pulse' },
  SUCCESS: { label: 'تم بنجاح', icon: CheckCircle2, className: 'text-emerald-500 border-emerald-500/30 bg-emerald-500/10' },
  FAILED: { label: 'فشل', icon: XCircle, className: 'text-red-500 border-red-500/30 bg-red-500/10' },
  RETRY: { label: 'إعادة محاولة', icon: AlertCircle, className: 'text-orange-500 border-orange-500/30 bg-orange-500/10' },
  CANCELLED: { label: 'ملغي', icon: XCircle, className: 'text-gray-500 border-gray-500/30 bg-gray-500/10' },
};

export default function ExecutionStatusBadge({ status, className, showLabel = true }: ExecutionStatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.PENDING;
  const Icon = config.icon;

  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border backdrop-blur-sm transition-all duration-300",
      config.className,
      className
    )}>
      <Icon className={cn("w-3.5 h-3.5", status === 'RUNNING' && 'animate-spin')} />
      {showLabel && config.label}
    </span>
  );
}