// components/sovereign-entities/WalletBalance.tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { getEntityBalance } from '@/services/sovereign-entities';
import { Wallet, TrendingUp, TrendingDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface WalletBalanceProps {
  entityId: number;
  className?: string;
}

export default function WalletBalance({ entityId, className }: WalletBalanceProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['entity-balance', entityId],
    queryFn: () => getEntityBalance(entityId).then(res => res.data),
    refetchInterval: 30000, // تحديث كل 30 ثانية
    staleTime: 10000,
  });

  if (isLoading) {
    return (
      <div className={cn("p-4 rounded-2xl bg-card/30 backdrop-blur-xl border border-white/10 animate-pulse", className)}>
        <div className="h-12 w-32 bg-white/10 rounded-xl" />
      </div>
    );
  }

  const balance = data?.balance_mrusdt || 0;

  return (
    <div className={cn("relative p-5 rounded-2xl bg-gradient-to-br from-card/60 to-card/30 backdrop-blur-2xl border border-white/10 overflow-hidden", className)}>
      {/* تأثير النيون الخلفي */}
      <div className="absolute -top-20 -right-20 w-40 h-40 rounded-full bg-primary/5 blur-3xl" />
      
      <div className="relative">
        <div className="flex items-center gap-2 text-sm text-muted-foreground/70">
          <Wallet className="w-4 h-4" />
          رصيد المحفظة
        </div>
        <div className="flex items-end gap-3 mt-1">
          <span className="text-3xl font-bold text-foreground/90 tabular-nums tracking-tight">
            {balance.toFixed(2)}
          </span>
          <span className="text-sm text-muted-foreground/50 font-medium">MR_USDT</span>
          {balance > 0 && (
            <span className="flex items-center gap-0.5 text-xs text-emerald-500/70">
              <TrendingUp className="w-3 h-3" />
              نشط
            </span>
          )}
        </div>
      </div>
    </div>
  );
}