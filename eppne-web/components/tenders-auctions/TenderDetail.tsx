// components/tenders-auctions/TenderDetail.tsx
'use client';

import { useTender } from '@/hooks/tenders-auctions/useTenders';
import { useTenderBids } from '@/hooks/tenders-auctions/useTenderBids';
import { useState } from 'react';
import { Loader2, Calendar, DollarSign, Building2, FileText, Users } from 'lucide-react';
import { format } from 'date-fns/ar';
import { cn } from '@/lib/utils';
import SubmitBidModal from './SubmitBidModal';
import EvaluateBidModal from './EvaluateBidModal';
import type { SovereignTender } from '@/types/tenders-auctions';

interface TenderDetailProps {
  tender: SovereignTender;
  isOwner?: boolean;
}

const statusColors: Record<string, string> = {
  DRAFT: 'text-gray-400',
  OPEN: 'text-emerald-500',
  EVALUATING: 'text-amber-500',
  AWARDED: 'text-blue-500',
  CANCELLED: 'text-red-500',
};

export default function TenderDetail({ tender, isOwner = false }: TenderDetailProps) {
  const [submitModalOpen, setSubmitModalOpen] = useState(false);
  const [evaluateModalOpen, setEvaluateModalOpen] = useState(false);
  const [selectedBidId, setSelectedBidId] = useState<number | null>(null);
  const { data: bids, isLoading: bLoading } = useTenderBids(tender.id);

  if (bLoading) {
    return <div className="flex justify-center items-center h-32"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;
  }

  return (
    <div className="space-y-6">
      <div className="p-6 rounded-3xl bg-card/20 backdrop-blur-2xl border border-white/10">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground/90">{tender.title}</h1>
            <p className="text-sm text-muted-foreground/60 mt-1">{tender.description}</p>
            <div className="flex flex-wrap gap-4 mt-2 text-sm text-muted-foreground/50">
              <span className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                {format(new Date(tender.opening_date), 'dd/MM/yyyy')} - {format(new Date(tender.closing_date), 'dd/MM/yyyy')}
              </span>
              <span className="flex items-center gap-1">
                <DollarSign className="w-4 h-4" />
                التأمين: {tender.bid_bond_mrusdt} MR_USDT
              </span>
              <span className="flex items-center gap-1">
                <Building2 className="w-4 h-4" />
                الكيان: #{tender.entity_id}
              </span>
              <span className="flex items-center gap-1">
                <Users className="w-4 h-4" />
                {bids?.length || 0} عطاء
              </span>
            </div>
          </div>
          <div className="text-right">
            <span className={cn("text-sm font-medium", statusColors[tender.status] || 'text-muted-foreground')}>
              {tender.status}
            </span>
            {tender.status === 'OPEN' && !isOwner && (
              <button
                onClick={() => setSubmitModalOpen(true)}
                className="mt-2 block px-4 py-2 rounded-xl bg-primary text-primary-foreground text-sm font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
              >
                تقديم عطاء
              </button>
            )}
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-foreground/80 mb-3">📋 العطاءات</h3>
        {bids?.length === 0 ? (
          <p className="text-muted-foreground/60 text-center py-8">لا توجد عطاءات حتى الآن</p>
        ) : (
          <div className="space-y-3">
            {bids?.map((bid) => (
              <div key={bid.id} className="flex items-center justify-between p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
                <div>
                  <p className="text-sm font-medium text-foreground/80">مقدم العطاء: #{bid.bidder_id}</p>
                  <p className="text-xs text-muted-foreground/50">التقييم الفني: {bid.technical_score ?? '—'}</p>
                  {bid.financial_amount_mrusdt && (
                    <p className="text-xs text-muted-foreground/50">المبلغ: {bid.financial_amount_mrusdt} MR_USDT</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className={cn("text-xs px-2 py-0.5 rounded-full border", bidStatusColors[bid.status] || 'border-white/10')}>
                    {bid.status}
                  </span>
                  {isOwner && tender.status === 'EVALUATING' && bid.status === 'SUBMITTED' && (
                    <button
                      onClick={() => {
                        setSelectedBidId(bid.id);
                        setEvaluateModalOpen(true);
                      }}
                      className="px-3 py-1.5 rounded-xl bg-amber-500/20 text-amber-500 border border-amber-500/30 hover:bg-amber-500/30 transition-colors text-xs"
                    >
                      تقييم
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <SubmitBidModal isOpen={submitModalOpen} onClose={() => setSubmitModalOpen(false)} tenderId={tender.id} />
      {selectedBidId && (
        <EvaluateBidModal
          isOpen={evaluateModalOpen}
          onClose={() => { setEvaluateModalOpen(false); setSelectedBidId(null); }}
          bidId={selectedBidId}
        />
      )}
    </div>
  );
}