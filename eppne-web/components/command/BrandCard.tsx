// components/command/BrandCard.tsx
'use client';

import { Building2, Users, DollarSign, Activity, CheckCircle, XCircle } from 'lucide-react';
import { format } from 'date-fns/ar';
import { cn } from '@/lib/utils';
import type { Brand } from '@/types/command';

interface BrandCardProps {
  brand: Brand;
  onClick?: () => void;
}

export default function BrandCard({ brand, onClick }: BrandCardProps) {
  return (
    <div
      onClick={onClick}
      className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all cursor-pointer"
      style={{
        '--brand-primary': brand.primary_color || '#8CC63F',
      } as React.CSSProperties}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl overflow-hidden bg-white/5 border border-white/10 flex items-center justify-center">
            {brand.logo_url ? (
              <img src={brand.logo_url} alt={brand.name} className="w-full h-full object-cover" />
            ) : (
              <Building2 className="w-6 h-6 text-muted-foreground/30" />
            )}
          </div>
          <div>
            <h4 className="font-medium text-foreground/80">{brand.name}</h4>
            <p className="text-xs text-muted-foreground/50">
              {brand.subscription_plan} • {format(new Date(brand.created_at), 'dd/MM/yyyy')}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={cn(
            "text-xs px-2 py-0.5 rounded-full border",
            brand.is_active ? "border-emerald-500/30 text-emerald-500" : "border-red-500/30 text-red-500"
          )}>
            {brand.is_active ? <CheckCircle className="w-3 h-3 inline mr-0.5" /> : <XCircle className="w-3 h-3 inline mr-0.5" />}
            {brand.is_active ? 'نشط' : 'موقف'}
          </span>
          <span className="text-xs text-muted-foreground/40">#{brand.id}</span>
        </div>
      </div>

      {brand.stats && (
        <div className="mt-3 grid grid-cols-3 gap-2 text-xs border-t border-white/5 pt-3">
          <div className="text-center">
            <span className="text-muted-foreground/50">المستخدمون</span>
            <p className="text-foreground/80 font-medium mt-0.5">{brand.stats.total_users}</p>
          </div>
          <div className="text-center">
            <span className="text-muted-foreground/50">الإيرادات</span>
            <p className="text-foreground/80 font-medium mt-0.5">{brand.stats.total_revenue.toFixed(0)} MR_USDT</p>
          </div>
          <div className="text-center">
            <span className="text-muted-foreground/50">المعاملات</span>
            <p className="text-foreground/80 font-medium mt-0.5">{brand.stats.total_transactions}</p>
          </div>
        </div>
      )}
    </div>
  );
}