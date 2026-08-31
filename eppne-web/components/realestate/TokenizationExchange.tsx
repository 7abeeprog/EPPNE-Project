// components/realestate/TokenizationExchange.tsx
'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { RealEstateService } from '@/services/realestate';
import { useRealEstateStore } from '@/store/realestateStore';
import { Loader2, TrendingUp, Users, Wallet, CheckCircle, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDecimalString } from '@/lib/format';
import type { PropertyOwnership } from '@/types/realestate';

const generateIdempotencyKey = (): string => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `IDEMP-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
};

export default function TokenizationExchange() {
  const queryClient = useQueryClient();
  const { addOwnership } = useRealEstateStore();
  const [selectedUnitId, setSelectedUnitId] = useState<number | null>(null);
  const [percentage, setPercentage] = useState(5);
  const [idempotencyKey] = useState(() => `ownership-${generateIdempotencyKey()}`);

  const { data: units, isLoading } = useQuery({
    queryKey: ['units-for-sale'],
    queryFn: () => RealEstateService.listUnitsForSale({ limit: 20 }),
    staleTime: 2 * 60 * 1000,
  });

  const mutation = useMutation({
    mutationFn: () => {
      if (!selectedUnitId) throw new Error('اختر وحدة');
      return RealEstateService.buyFraction(selectedUnitId, { ownership_percentage: percentage }, { 'Idempotency-Key': idempotencyKey });
    },
    onSuccess: (response) => {
      addOwnership(response as unknown as PropertyOwnership);
      queryClient.invalidateQueries({ queryKey: ['my-ownerships'] });
      setSelectedUnitId(null);
    },
  });

  const selectedUnit = units?.find(u => u.id === selectedUnitId);

  if (isLoading) {
    return <div className="flex justify-center p-8"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {units?.map((unit) => (
          <button
            key={unit.id}
            onClick={() => setSelectedUnitId(unit.id)}
            className={cn(
              "p-4 rounded-2xl border transition-all duration-300 text-right",
              "bg-card/20 backdrop-blur-xl hover:bg-card/30",
              selectedUnitId === unit.id
                ? "border-primary/50 shadow-[0_0_40px_-15px_rgba(var(--primary-rgb),0.15)]"
                : "border-white/10 hover:border-primary/20"
            )}
          >
            <div className="flex items-start justify-between">
              <div>
                <h4 className="font-medium text-foreground/90">الوحدة #{unit.unit_number}</h4>
                <p className="text-xs text-muted-foreground/50">
                  {unit.area_sqm} م² • {unit.property_type}
                </p>
              </div>
              <span className="text-sm font-bold text-primary">
                {formatDecimalString(unit.sale_price_mrusdt)} MR_USDT
              </span>
            </div>
            {selectedUnitId === unit.id && (
              <div className="mt-3 p-3 rounded-xl bg-primary/5 border border-primary/10">
                <p className="text-xs text-muted-foreground/60">
                  أدخل النسبة المئوية المطلوبة
                </p>
                <div className="flex items-center gap-3 mt-2">
                  <input
                    type="number"
                    value={percentage}
                    onChange={(e) => setPercentage(Math.min(100, Math.max(1, parseFloat(e.target.value) || 1)))}
                    min="1"
                    max="100"
                    className="w-24 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                  />
                  <span className="text-sm text-muted-foreground/50">%</span>
                  <button
                    onClick={() => mutation.mutate()}
                    disabled={mutation.isPending}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-1.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50 text-sm"
                  >
                    {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wallet className="w-4 h-4" />}
                    شراء
                  </button>
                </div>
                {selectedUnit && unit.sale_price_mrusdt && (
                  <p className="text-xs text-muted-foreground/40 mt-1">
                    {/* Estimated cost preview only — never submitted to the backend,
                        which recomputes the real charge from sale_price_mrusdt itself. */}
                    التكلفة: {((Number(unit.sale_price_mrusdt) * percentage) / 100).toFixed(2)} MR_USDT
                  </p>
                )}
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}