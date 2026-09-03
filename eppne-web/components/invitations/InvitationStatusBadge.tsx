// components/invitations/InvitationStatusBadge.tsx
'use client';

import { cn } from '@/lib/utils';
import { FileText, Send, CheckCircle, XCircle, Clock } from 'lucide-react';
import type { InvitationStatus } from '@/types/invitations';

interface InvitationStatusBadgeProps {
  status: InvitationStatus;
  className?: string;
}

const statusConfig: Record<InvitationStatus, { label: string; color: string; icon: React.ReactNode }> = {
  DRAFT: {
    label: 'مسودة',
    color: 'border-gray-500/30 text-gray-400 bg-gray-500/5',
    icon: <FileText className="w-3.5 h-3.5" />,
  },
  SENT: {
    label: 'مرسلة',
    color: 'border-blue-500/30 text-blue-500 bg-blue-500/5',
    icon: <Send className="w-3.5 h-3.5" />,
  },
  ACCEPTED: {
    label: 'مقبولة',
    color: 'border-emerald-500/30 text-emerald-500 bg-emerald-500/5',
    icon: <CheckCircle className="w-3.5 h-3.5" />,
  },
  DECLINED: {
    label: 'مرفوضة',
    color: 'border-red-500/30 text-red-500 bg-red-500/5',
    icon: <XCircle className="w-3.5 h-3.5" />,
  },
  EXPIRED: {
    label: 'منتهية',
    color: 'border-amber-500/30 text-amber-500 bg-amber-500/5',
    icon: <Clock className="w-3.5 h-3.5" />,
  },
};

export default function InvitationStatusBadge({ status, className }: InvitationStatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full border", config.color, className)}>
      {config.icon}
      {config.label}
    </span>
  );
}
