// components/invitations/CampaignCard.tsx
'use client';

import { Megaphone, Wallet, Users, Calendar } from 'lucide-react';
import { format } from 'date-fns';
import { ar } from 'date-fns/locale';
import CampaignStatusBadge from './CampaignStatusBadge';
import type { MarketingCampaign } from '@/types/invitations';

export default function CampaignCard({ campaign, onClick }: { campaign: MarketingCampaign; onClick?: () => void }) {
  return (
    <div
      onClick={onClick}
      className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all cursor-pointer"
    >
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80 flex items-center gap-2">
            <Megaphone className="w-4 h-4 text-primary/60" />
            {campaign.name}
          </h4>
          {campaign.description && (
            <p className="mt-1 text-sm text-muted-foreground/60 line-clamp-2">{campaign.description}</p>
          )}
        </div>
        <CampaignStatusBadge status={campaign.status} />
      </div>
      <div className="flex flex-wrap gap-3 mt-3 text-xs text-muted-foreground/50">
        <span className="flex items-center gap-1">
          <Wallet className="w-3 h-3" />
          {campaign.spent_mrusdt} / {campaign.budget_mrusdt} MR_USDT
        </span>
        <span className="flex items-center gap-1">
          <Users className="w-3 h-3" />
          {campaign.converted_leads} / {campaign.total_leads} عميل محوَّل
        </span>
        <span className="flex items-center gap-1">
          <Calendar className="w-3 h-3" />
          {format(new Date(campaign.start_date), 'dd/MM/yyyy', { locale: ar })}
        </span>
      </div>
      {campaign.channels.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {campaign.channels.map((channel) => (
            <span key={channel} className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 text-muted-foreground/50 border border-white/10">
              {channel}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
