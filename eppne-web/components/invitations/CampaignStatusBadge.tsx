// components/invitations/CampaignStatusBadge.tsx
'use client';

import { cn } from '@/lib/utils';
import { FileText, Play, Pause, CheckCircle, XCircle } from 'lucide-react';
import type { CampaignStatus } from '@/types/invitations';

interface CampaignStatusBadgeProps {
  status: CampaignStatus;
  className?: string;
}

const statusConfig: Record<CampaignStatus, { label: string; color: string; icon: React.ReactNode }> = {
  DRAFT: {
    label: 'مسودة',
    color: 'border-gray-500/30 text-gray-400 bg-gray-500/5',
    icon: <FileText className="w-3.5 h-3.5" />,
  },
  ACTIVE: {
    label: 'نشطة',
    color: 'border-emerald-500/30 text-emerald-500 bg-emerald-500/5',
    icon: <Play className="w-3.5 h-3.5" />,
  },
  PAUSED: {
    label: 'موقفة',
    color: 'border-amber-500/30 text-amber-500 bg-amber-500/5',
    icon: <Pause className="w-3.5 h-3.5" />,
  },
  COMPLETED: {
    label: 'مكتملة',
    color: 'border-blue-500/30 text-blue-500 bg-blue-500/5',
    icon: <CheckCircle className="w-3.5 h-3.5" />,
  },
  CANCELLED: {
    label: 'ملغية',
    color: 'border-red-500/30 text-red-500 bg-red-500/5',
    icon: <XCircle className="w-3.5 h-3.5" />,
  },
};

export default function CampaignStatusBadge({ status, className }: CampaignStatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full border", config.color, className)}>
      {config.icon}
      {config.label}
    </span>
  );
}