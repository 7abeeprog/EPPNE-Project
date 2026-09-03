// components/invitations/TicketStatusBadge.tsx
'use client';

import { cn } from '@/lib/utils';
import { CircleDot, Loader2, CheckCircle, Lock } from 'lucide-react';
import type { TicketStatus } from '@/types/invitations';

interface TicketStatusBadgeProps {
  status: TicketStatus;
  className?: string;
}

const statusConfig: Record<TicketStatus, { label: string; color: string; icon: React.ReactNode }> = {
  OPEN: {
    label: 'مفتوحة',
    color: 'border-blue-500/30 text-blue-500 bg-blue-500/5',
    icon: <CircleDot className="w-3.5 h-3.5" />,
  },
  IN_PROGRESS: {
    label: 'قيد المعالجة',
    color: 'border-amber-500/30 text-amber-500 bg-amber-500/5',
    icon: <Loader2 className="w-3.5 h-3.5" />,
  },
  RESOLVED: {
    label: 'محلولة',
    color: 'border-emerald-500/30 text-emerald-500 bg-emerald-500/5',
    icon: <CheckCircle className="w-3.5 h-3.5" />,
  },
  CLOSED: {
    label: 'مغلقة',
    color: 'border-gray-500/30 text-gray-400 bg-gray-500/5',
    icon: <Lock className="w-3.5 h-3.5" />,
  },
};

export default function TicketStatusBadge({ status, className }: TicketStatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full border", config.color, className)}>
      {config.icon}
      {config.label}
    </span>
  );
}
