// components/insurance/SubscriptionCard.tsx
'use client';

import { useRenewSubscription, useCancelSubscription } from '@/hooks/insurance/useSubscriptions';
import { Calendar, DollarSign, CheckCircle, XCircle, Loader2, Shield } from 'lucide-react';
import { format } from 'date-fns/ar';
import { cn } from '@/lib/utils';
import type { InsuranceSubscription } from '@/types/insurance';

export default function SubscriptionCard({ subscription }: { subscription: InsuranceSubscription }) {
  const renew = useRenewSubscription();
  const cancel = useCancelSubscription();

  const isActive = subscription.status === 'ACTIVE';
  const isExpired = subscription.end_date && new Date(subscription.end_date) < new Date();

  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">بوليصة #{subscription.policy_id}</h4>
          <p className="text-sm text-muted-foreground/60">
            {subscription.subscriber_user_id ? `مستخدم #${subscription.subscriber_user_id}` :
             subscription.fleet_id ? `أسطول #${subscription.fleet_id}` :
             subscription.land_asset_id ? `أرض #${subscription.land_asset_id}` :
             subscription.project_id ? `مشروع #${subscription.project_id}` :
             subscription.employment_contract_id ? `عقد عمل #${subscription.employment_contract_id}` :
             'غير محدد'}
          </p>
        </div>
        <span className={cn(
          "text-xs px-2 py-0.5 rounded-full border",
          isActive && !isExpired ? "border-emerald-500/30 text-emerald-500" :
          isExpired ? "border-red-500/30 text-red-500" :
          "border-amber-500/30 text-amber-500"
        )}>
          {isActive && !isExpired ? 'نشط' : isExpired ? 'منتهي' : subscription.status}
        </span>
      </div>
      <div className="mt-2 space-y-1 text-xs text-muted-foreground/50">
        <div className="flex items-center gap-2">
          <Calendar className="w-3 h-3" />
          {format(new Date(subscription.start_date), 'dd/MM/yyyy')}
          {subscription.end_date && ` - ${format(new Date(subscription.end_date), 'dd/MM/yyyy')}`}
        </div>
        {subscription.policy_nft_id && (
          <div className="flex items-center gap-2">
            <CheckCircle className="w-3 h-3 text-emerald-500" />
            NFT: {subscription.policy_nft_id.slice(0, 16)}...
          </div>
        )}
      </div>
      <div className="mt-2 flex gap-2">
        {isActive && isExpired && (
          <button
            onClick={() => renew.mutate(subscription.id)}
            disabled={renew.isPending}
            className="flex-1 px-3 py-1.5 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors text-xs flex items-center justify-center gap-1"
          >
            {renew.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
            تجديد
          </button>
        )}
        {isActive && !isExpired && (
          <button
            onClick={() => cancel.mutate(subscription.id)}
            disabled={cancel.isPending}
            className="flex-1 px-3 py-1.5 rounded-xl bg-red-500/20 text-red-500 border border-red-500/30 hover:bg-red-500/30 transition-colors text-xs flex items-center justify-center gap-1"
          >
            {cancel.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
            إلغاء
          </button>
        )}
      </div>
    </div>
  );
}