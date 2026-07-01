// components/arbitration-syndicates/ElectionCard.tsx
'use client';

import { Calendar, Users, Vote, Clock, CheckCircle, XCircle } from 'lucide-react';
import { format } from 'date-fns/ar';
import { cn } from '@/lib/utils';
import type { SyndicateElection } from '@/types/arbitration-syndicates';

const statusConfig: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  UPCOMING: {
    label: 'قادمة',
    color: 'border-blue-500/30 text-blue-500 bg-blue-500/5',
    icon: <Clock className="w-3.5 h-3.5" />,
  },
  NOMINATION: {
    label: 'ترشيح',
    color: 'border-amber-500/30 text-amber-500 bg-amber-500/5',
    icon: <Users className="w-3.5 h-3.5" />,
  },
  VOTING: {
    label: 'تصويت',
    color: 'border-emerald-500/30 text-emerald-500 bg-emerald-500/5',
    icon: <Vote className="w-3.5 h-3.5 animate-pulse" />,
  },
  CLOSED: {
    label: 'مغلقة',
    color: 'border-gray-500/30 text-gray-400 bg-gray-500/5',
    icon: <CheckCircle className="w-3.5 h-3.5" />,
  },
  CANCELLED: {
    label: 'ملغية',
    color: 'border-red-500/30 text-red-500 bg-red-500/5',
    icon: <XCircle className="w-3.5 h-3.5" />,
  },
};

export default function ElectionCard({ election }: { election: SyndicateElection }) {
  const config = statusConfig[election.status] || statusConfig.UPCOMING;

  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">{election.title}</h4>
          <p className="text-sm text-muted-foreground/60">{election.election_type} • {election.election_year}</p>
        </div>
        <span className={cn("inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full border", config.color)}>
          {config.icon}
          {config.label}
        </span>
      </div>
      <div className="mt-2 space-y-1 text-xs text-muted-foreground/50">
        <div className="flex items-center gap-2">
          <Calendar className="w-3 h-3" />
          الترشيح: {format(new Date(election.nomination_start), 'dd/MM')} - {format(new Date(election.nomination_end), 'dd/MM')}
        </div>
        <div className="flex items-center gap-2">
          <Vote className="w-3 h-3" />
          التصويت: {format(new Date(election.voting_start), 'dd/MM')} - {format(new Date(election.voting_end), 'dd/MM')}
        </div>
      </div>
    </div>
  );
}