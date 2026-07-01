// components/invitations/LeadCard.tsx
'use client';

import { User, Mail, Phone, Building2, Briefcase } from 'lucide-react';
import { format } from 'date-fns/ar';
import { cn } from '@/lib/utils';
import LeadStatusBadge from './LeadStatusBadge';
import type { Lead } from '@/types/invitations';

export default function LeadCard({ lead, onClick }: { lead: Lead; onClick?: () => void }) {
  return (
    <div
      onClick={onClick}
      className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all cursor-pointer"
    >
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">
            {lead.first_name || lead.last_name ? `${lead.first_name || ''} ${lead.last_name || ''}` : lead.email || 'عميل غير مسمى'}
          </h4>
          <div className="flex flex-wrap gap-2 mt-1 text-xs text-muted-foreground/50">
            {lead.email && (
              <span className="flex items-center gap-1">
                <Mail className="w-3 h-3" />
                {lead.email}
              </span>
            )}
            {lead.phone && (
              <span className="flex items-center gap-1">
                <Phone className="w-3 h-3" />
                {lead.phone}
              </span>
            )}
            {lead.company && (
              <span className="flex items-center gap-1">
                <Building2 className="w-3 h-3" />
                {lead.company}
              </span>
            )}
            {lead.position && (
              <span className="flex items-center gap-1">
                <Briefcase className="w-3 h-3" />
                {lead.position}
              </span>
            )}
          </div>
        </div>
        <LeadStatusBadge status={lead.status} />
      </div>
      <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground/40">
        <span>المصدر: {lead.source}</span>
        <span>درجة الجاهزية: {lead.score}%</span>
        <span>{format(new Date(lead.created_at), 'dd/MM/yyyy')}</span>
      </div>
    </div>
  );
}