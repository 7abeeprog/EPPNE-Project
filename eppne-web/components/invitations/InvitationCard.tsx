// components/invitations/InvitationCard.tsx
'use client';

import { Mail, Users, Percent, Gift, MousePointerClick, Calendar } from 'lucide-react';
import { format } from 'date-fns';
import { ar } from 'date-fns/locale';
import InvitationStatusBadge from './InvitationStatusBadge';
import type { SovereignInvitation } from '@/types/invitations';

export default function InvitationCard({ invitation, onClick }: { invitation: SovereignInvitation; onClick?: () => void }) {
  return (
    <div
      onClick={onClick}
      className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all cursor-pointer"
    >
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80 flex items-center gap-2">
            <Mail className="w-4 h-4 text-primary/60" />
            {invitation.title || invitation.target_entity_identifier || `دعوة #${invitation.id}`}
          </h4>
          {invitation.custom_message && (
            <p className="mt-1 text-sm text-muted-foreground/60 line-clamp-2">{invitation.custom_message}</p>
          )}
          <div className="flex flex-wrap gap-2 mt-1 text-xs text-muted-foreground/50">
            <span className="flex items-center gap-1">
              <Users className="w-3 h-3" />
              {invitation.target_type}
            </span>
            {invitation.expires_at && (
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                ينتهي: {format(new Date(invitation.expires_at), 'dd/MM/yyyy', { locale: ar })}
              </span>
            )}
          </div>
        </div>
        <InvitationStatusBadge status={invitation.status} />
      </div>
      <div className="flex flex-wrap gap-3 mt-3 text-xs text-muted-foreground/50">
        {Number(invitation.discount_percentage) > 0 && (
          <span className="flex items-center gap-1">
            <Percent className="w-3 h-3" />
            خصم {invitation.discount_percentage}%
          </span>
        )}
        {Number(invitation.gift_coins_amount) > 0 && (
          <span className="flex items-center gap-1">
            <Gift className="w-3 h-3" />
            {invitation.gift_coins_amount} {invitation.gift_currency}
          </span>
        )}
        <span className="flex items-center gap-1">
          <MousePointerClick className="w-3 h-3" />
          {invitation.click_count} نقرة
        </span>
        <span>{invitation.current_uses} / {invitation.max_uses} استخدام</span>
      </div>
    </div>
  );
}
