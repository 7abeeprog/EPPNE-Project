// app/(dashboard)/zamakana/campaigns/[id]/page.tsx
'use client';

import { useParams } from 'next/navigation';
import { useCampaign } from '@/hooks/zamakana/useCampaigns';
import { useCampaignPledges } from '@/hooks/zamakana/usePledges';
import { useState } from 'react';
import { Loader2, ArrowLeft, Clock, Users, Calendar, Shield } from 'lucide-react';
import Link from 'next/link';
import { format } from 'date-fns/ar';
import PledgeForm from '@/components/zamakana/PledgeForm';
import PledgeCard from '@/components/zamakana/PledgeCard';

export default function CampaignDetailPage() {
  const params = useParams();
  const campaignId = parseInt(params.id as string);
  const [showPledgeForm, setShowPledgeForm] = useState(false);

  const { data: campaign, isLoading: cLoading } = useCampaign(campaignId);
  const { data: pledges, isLoading: pLoading } = useCampaignPledges(campaignId);

  if (cLoading || pLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!campaign) {
    return <div className="p-6 text-center text-muted-foreground/60">الحملة غير موجودة</div>;
  }

  const progress = campaign.target_time_hours > 0
    ? (campaign.collected_time_hours / campaign.target_time_hours) * 100
    : 0;

  return (
    <div className="p-6 space-y-6">
      <Link href="/zamakana/campaigns" className="flex items-center gap-2 text-sm text-muted-foreground/60 hover:text-foreground/80 transition-colors">
        <ArrowLeft className="w-4 h-4" />
        العودة إلى الحملات
      </Link>

      <div className="p-6 rounded-3xl bg-card/20 backdrop-blur-2xl border border-white/10">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground/90">{campaign.title}</h1>
            <p className="text-sm text-muted-foreground/60 mt-1">{campaign.description}</p>
            <div className="flex flex-wrap gap-4 mt-2 text-sm text-muted-foreground/50">
              <span className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                {campaign.collected_time_hours} / {campaign.target_time_hours} ساعة
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                {format(new Date(campaign.start_date), 'dd/MM/yyyy')} - {format(new Date(campaign.end_date), 'dd/MM/yyyy')}
              </span>
              <span className="flex items-center gap-1">
                <Users className="w-4 h-4" />
                {pledges?.length || 0} مشارك
              </span>
            </div>
          </div>
          <div className="text-right">
            <span className={cn(
              "text-xs px-2 py-0.5 rounded-full border",
              campaign.status === 'COMPLETED' ? "border-emerald-500/30 text-emerald-500" :
              campaign.status === 'ACTIVE' ? "border-blue-500/30 text-blue-500" :
              "border-red-500/30 text-red-500"
            )}>
              {campaign.status === 'COMPLETED' ? 'مكتملة' :
               campaign.status === 'ACTIVE' ? 'نشطة' : campaign.status}
            </span>
            {campaign.status === 'ACTIVE' && (
              <button
                onClick={() => setShowPledgeForm(true)}
                className="mt-2 block px-4 py-2 rounded-xl bg-primary text-primary-foreground text-sm font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
              >
                تعهد بالساعات
              </button>
            )}
          </div>
        </div>
        <div className="mt-4">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground/50">التقدم</span>
            <span className="text-primary font-medium">{progress.toFixed(1)}%</span>
          </div>
          <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden mt-1">
            <div
              className="h-full rounded-full bg-gradient-to-r from-primary to-secondary transition-all duration-1000"
              style={{ width: `${Math.min(progress, 100)}%` }}
            />
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-foreground/80 mb-3">📋 التعهدات</h3>
        {pledges?.length === 0 ? (
          <p className="text-muted-foreground/60 text-center py-8">لا توجد تعهدات بعد</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {pledges?.map((pledge) => (
              <PledgeCard key={pledge.id} pledge={pledge} />
            ))}
          </div>
        )}
      </div>

      {showPledgeForm && (
        <PledgeForm
          isOpen={showPledgeForm}
          onClose={() => setShowPledgeForm(false)}
          campaignId={campaignId}
        />
      )}
    </div>
  );
}