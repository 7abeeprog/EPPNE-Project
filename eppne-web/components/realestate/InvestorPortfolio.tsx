// components/realestate/InvestorPortfolio.tsx (الإصدار النهائي المتكامل)
'use client';

import { useQuery } from '@tanstack/react-query';
import { getMyOwnerships, getSmartContractStatus } from '@/services/realestate';
import { Loader2, Building2, TrendingUp, Calendar, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function InvestorPortfolio() {
  const { data: ownerships, isLoading } = useQuery({
    queryKey: ['my-ownerships'],
    queryFn: () => getMyOwnerships().then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  if (isLoading) {
    return <div className="flex justify-center p-8"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;
  }

  if (!ownerships || ownerships.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground/60">
        <Building2 className="w-12 h-12 mx-auto mb-4 opacity-30" />
        <p className="text-lg">لا توجد ملكيات عقارية</p>
        <p className="text-sm">استثمر في العقارات المجزأة لبناء محفظتك</p>
      </div>
    );
  }

  const totalValue = ownerships.reduce((sum, o) => sum + (o.ownership_percentage || 0), 0);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <p className="text-xs text-muted-foreground/50">إجمالي الملكيات</p>
          <p className="text-lg font-bold text-foreground/90">{ownerships.length}</p>
        </div>
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <p className="text-xs text-muted-foreground/50">متوسط النسبة</p>
          <p className="text-lg font-bold text-foreground/90">
            {(ownerships.reduce((sum, o) => sum + o.ownership_percentage, 0) / ownerships.length).toFixed(1)}%
          </p>
        </div>
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <p className="text-xs text-muted-foreground/50">إجمالي القيمة</p>
          <p className="text-lg font-bold text-foreground/90">
            {ownerships.reduce((sum, o) => sum + (o.ownership_percentage || 0), 0).toFixed(2)} MR_USDT
          </p>
        </div>
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <p className="text-xs text-muted-foreground/50">الصكوك الرقمية</p>
          <p className="text-lg font-bold text-foreground/90">
            {ownerships.filter(o => o.deed_nft_token_id).length}
          </p>
        </div>
      </div>

      <div className="space-y-2">
        {ownerships.map((ownership) => (
          <div
            key={ownership.id}
            className="flex items-center justify-between p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-primary/10 text-primary">
                <FileText className="w-4 h-4" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground/80">الوحدة #{ownership.unit_id}</p>
                <p className="text-xs text-muted-foreground/50 flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  {new Date(ownership.acquisition_date).toLocaleDateString('ar-EG')}
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm font-bold text-primary">
                {ownership.ownership_percentage}%
              </p>
              {ownership.deed_nft_token_id && (
                <p className="text-[10px] text-muted-foreground/40 font-mono truncate max-w-[100px]">
                  {ownership.deed_nft_token_id}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ========== المكون الجديد: مراقب حالة العقد الذكي ==========
interface SmartContractStatusProps {
  contractId: number;
  onStatusChange?: (status: string) => void;
}

export function SmartContractStatusMonitor({ contractId, onStatusChange }: SmartContractStatusProps) {
  // استخدام Polling لمتابعة حالة العقد الذكي
  const { data, isLoading, error } = useQuery({
    queryKey: ['smart-contract-status', contractId],
    queryFn: () => getSmartContractStatus(contractId).then(res => res.data),
    refetchInterval: (data) => {
      // إذا كانت الحالة PENDING، نجلب كل 3 ثوانٍ
      if (data?.status === 'PENDING') return 3000;
      // إذا كانت CONFIRMED أو FAILED، نتوقف عن الجلب
      return false;
    },
    staleTime: 1000,
    onSuccess: (data) => {
      if (onStatusChange) onStatusChange(data.status);
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground/60">
        <Loader2 className="w-4 h-4 animate-spin" />
        جاري تنفيذ العقد الذكي...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-500/80 text-sm">
        ❌ فشل في تنفيذ العقد: {(error as Error).message}
      </div>
    );
  }

  const statusConfig = {
    PENDING: { label: 'قيد التنفيذ', color: 'text-amber-500 bg-amber-500/10 border-amber-500/30', icon: '⏳' },
    CONFIRMED: { label: 'تم التنفيذ', color: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30', icon: '✅' },
    FAILED: { label: 'فشل التنفيذ', color: 'text-red-500 bg-red-500/10 border-red-500/30', icon: '❌' },
  };

  const status = statusConfig[data?.status as keyof typeof statusConfig] || statusConfig.PENDING;

  return (
    <div className={cn(
      "flex items-center gap-2 px-3 py-2 rounded-xl border text-sm",
      status.color
    )}>
      <span>{status.icon}</span>
      <span>{status.label}</span>
      {data?.tx_hash && (
        <span className="text-xs font-mono text-muted-foreground/50 truncate max-w-[100px]">
          {data.tx_hash.slice(0, 10)}...
        </span>
      )}
      {data?.status === 'PENDING' && (
        <Loader2 className="w-3 h-3 animate-spin ml-1" />
      )}
    </div>
  );
}