// components/invitations/LeadStatusBadge.tsx
'use client';

import { cn } from '@/lib/utils';
import { UserPlus, Phone, CheckCircle, Users, XCircle } from 'lucide-react';
import type { LeadStatus } from '@/types/invitations';

interface LeadStatusBadgeProps {
  status: LeadStatus;
  className?: string;
}

const statusConfig: Record<LeadStatus, { label: string; color: string; icon: React.ReactNode }> = {
  NEW: {
    label: 'جديد',
    color: 'border-blue-500/30 text-blue-500 bg-blue-500/5',
    icon: <UserPlus className="w-3.5 h-3.5" />,
  },
  CONTACTED: {
    label: 'تم التواصل',
    color: 'border-amber-500/30 text-amber-500 bg-amber-500/5',
    icon: <Phone className="w-3.5 h-3.5" />,
  },
  QUALIFIED: {
    label: 'مؤهل',
    color: 'border-purple-500/30 text-purple-500 bg-purple-500/5',
    icon: <Users className="w-3.5 h-3.5" />,
  },
  CONVERTED: {
    label: 'محول',
    color: 'border-emerald-500/30 text-emerald-500 bg-emerald-500/5',
    icon: <CheckCircle className="w-3.5 h-3.5" />,
  },
  LOST: {
    label: 'مفقود',
    color: 'border-red-500/30 text-red-500 bg-red-500/5',
    icon: <XCircle className="w-3.5 h-3.5" />,
  },
};

export default function LeadStatusBadge({ status, className }: LeadStatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full border", config.color, className)}>
      {config.icon}
      {config.label}
    </span>
  );
}