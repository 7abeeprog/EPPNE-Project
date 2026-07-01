// app/(dashboard)/realestate/ownerships/page.tsx
'use client';

import { useRouter } from 'next/navigation';
import { useMyOwnerships } from '@/hooks/realestate/useMyOwnerships';
import { format } from 'date-fns/ar';
import { Loader2, Building2, TrendingUp, Calendar, ExternalLink, Shield } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function MyOwnershipsPage() {
  const router = useRouter();
  const { data: ownerships, isLoading } = useMyOwnerships();

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!ownerships || ownerships.length === 0) {
    return (
      <div className="p-6 text-center text-muted-foreground/60">
        <Shield className="w-12 h-12 mx-auto mb-4 opacity-30" />
        <p className="text-lg">لا تملك أي حصص عقارية</p>
        <p className="text-sm">استكشف العقارات المتاحة للتجزئة</p>
      </div>
    );
  }

  const totalValue = ownerships.reduce((sum, o) => sum + (o.current_value || 0), 0);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground/90 flex items-center gap-2">
          <Shield className="w-6 h-6 text-primary" />
          ملكياتي العقارية
        </h1>
        <p className="text-sm text-muted-foreground/70">حصصك في العقارات المجزأة</p>
      </div>

      {/* ملخص سريع */}
      <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <div className="flex flex-wrap gap-6 text-sm">
          <div>
            <span className="text-muted-foreground/50">عدد الحصص</span>
            <p className="text-lg font-bold text-foreground/90">{ownerships.length}</p>
          </div>
          <div>
            <span className="text-muted-foreground/50">إجمالي القيمة التقديرية</span>
            <p className="text-lg font-bold text-primary">{totalValue.toFixed(2)} MR_USDT</p>
          </div>
          <div>
            <span className="text-muted-foreground/50">متوسط الحصة</span>
            <p className="text-lg font-bold text-foreground/90">
              {(ownerships.reduce((s, o) => s + o.ownership_percentage, 0) / ownerships.length).toFixed(2)}%
            </p>
          </div>
        </div>
      </div>

      {/* قائمة الملكيات */}
      <div className="space-y-3">
        {ownerships.map((ownership) => (
          <div
            key={ownership.id}
            className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all cursor-pointer"
            onClick={() => router.push(`/realestate/property/${ownership.unit_id}`)}
          >
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-foreground/80">عقار #{ownership.unit_id}</h4>
                <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground/50">
                  <span className="flex items-center gap-1">
                    <TrendingUp className="w-3 h-3" />
                    حصة: {ownership.ownership_percentage}%
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {format(new Date(ownership.acquisition_date), 'dd/MM/yyyy')}
                  </span>
                  {ownership.current_value && (
                    <span className="flex items-center gap-1">
                      <Building2 className="w-3 h-3" />
                      {ownership.current_value.toFixed(2)} MR_USDT
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {ownership.deed_nft_token_id && (
                  <span className="text-xs px-2 py-0.5 rounded-full border border-emerald-500/30 text-emerald-500 bg-emerald-500/5 flex items-center gap-1">
                    <Shield className="w-3 h-3" />
                    NFT
                  </span>
                )}
                <ExternalLink className="w-4 h-4 text-muted-foreground/50" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}