// app/(dashboard)/realestate/tokenization/page.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { getAvailableProperties } from '@/services/realestate';
import { useCreateTokenization } from '@/hooks/realestate/useTokenization';
import { useAssetTokenization } from '@/hooks/realestate/useTokenization';
import { Loader2, Sparkles, Shield, Plus, Eye, CheckCircle, XCircle, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

const statusColors = {
  ACTIVE: 'border-emerald-500/30 text-emerald-500 bg-emerald-500/5',
  FULLY_SUBSCRIBED: 'border-blue-500/30 text-blue-500 bg-blue-500/5',
  INACTIVE: 'border-gray-500/30 text-gray-400 bg-gray-500/5',
};

export default function TokenizationPage() {
  const router = useRouter();
  const [selectedProperty, setSelectedProperty] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    total_shares: 1000,
    share_price_mrusdt: 10,
    minimum_investment_shares: 1,
  });
  const [showCreateForm, setShowCreateForm] = useState(false);

  const { data: properties, isLoading: propertiesLoading } = useQuery({
    queryKey: ['available-properties'],
    queryFn: () => getAvailableProperties().then((res) => res.data),
    staleTime: 2 * 60 * 1000,
  });

  // جلب بيانات التجزئة لكل عقار (يمكن تحسينه)
  const { data: tokenizations, isLoading: tokenLoading } = useQuery({
    queryKey: ['all-tokenizations'],
    queryFn: async () => {
      // في الإنتاج، سيتم استخدام نقطة نهاية مخصصة
      return [];
    },
    staleTime: 2 * 60 * 1000,
  });

  const createTokenization = useCreateTokenization();

  const handleCreate = () => {
    if (!selectedProperty) return;
    createTokenization.mutate({
      unit_id: selectedProperty,
      ...formData,
    });
    setShowCreateForm(false);
    setSelectedProperty(null);
  };

  if (propertiesLoading || tokenLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90 flex items-center gap-2">
            <Shield className="w-6 h-6 text-primary" />
            تجزئة الأصول
          </h1>
          <p className="text-sm text-muted-foreground/70">تحويل العقارات إلى أصول رقمية قابلة للتداول</p>
        </div>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          تجزئة جديدة
        </button>
      </div>

      {/* نموذج الإنشاء */}
      {showCreateForm && (
        <div className="p-6 rounded-2xl bg-card/30 backdrop-blur-xl border border-white/10 space-y-4">
          <h3 className="text-lg font-semibold text-foreground/90">🔗 إنشاء تجزئة جديدة</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-muted-foreground/60">العقار</label>
              <select
                value={selectedProperty || ''}
                onChange={(e) => setSelectedProperty(parseInt(e.target.value))}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              >
                <option value="">اختر عقاراً</option>
                {properties?.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title} ({p.area_sqm} م²)
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">إجمالي الأسهم</label>
              <input
                type="number"
                value={formData.total_shares}
                onChange={(e) => setFormData({ ...formData, total_shares: parseInt(e.target.value) || 0 })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                min="1"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">سعر السهم (MR_USDT)</label>
              <input
                type="number"
                step="0.01"
                value={formData.share_price_mrusdt}
                onChange={(e) => setFormData({ ...formData, share_price_mrusdt: parseFloat(e.target.value) || 0 })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                min="0.01"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">الحد الأدنى للاستثمار (أسهم)</label>
              <input
                type="number"
                value={formData.minimum_investment_shares}
                onChange={(e) => setFormData({ ...formData, minimum_investment_shares: parseInt(e.target.value) || 1 })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                min="1"
              />
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              onClick={handleCreate}
              disabled={createTokenization.isPending || !selectedProperty}
              className="px-6 py-2 rounded-xl bg-primary text-primary-foreground font-medium disabled:opacity-50 flex items-center gap-2"
            >
              {createTokenization.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              إنشاء التجزئة
            </button>
            <button
              onClick={() => { setShowCreateForm(false); setSelectedProperty(null); }}
              className="px-6 py-2 rounded-xl border border-white/10 hover:bg-white/5 transition-colors"
            >
              إلغاء
            </button>
          </div>
        </div>
      )}

      {/* قائمة التجزئات */}
      {tokenizations?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <Shield className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد تجزئات</p>
          <p className="text-sm">ابدأ بتجزئة أول عقار لك</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {tokenizations?.map((token) => (
            <div
              key={token.id}
              className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all cursor-pointer"
              onClick={() => router.push(`/realestate/property/${token.unit_id}`)}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-foreground/80">
                  عقار #{token.unit_id}
                </span>
                <span
                  className={cn(
                    "text-xs px-2 py-0.5 rounded-full border",
                    statusColors[token.is_active ? (token.is_fully_subscribed ? 'FULLY_SUBSCRIBED' : 'ACTIVE') : 'INACTIVE']
                  )}
                >
                  {token.is_fully_subscribed ? 'مكتمل' : token.is_active ? 'نشط' : 'غير نشط'}
                </span>
              </div>
              <div className="mt-2 space-y-1 text-sm text-muted-foreground/60">
                <div className="flex justify-between">
                  <span>الأسهم</span>
                  <span className="text-foreground/80">{token.total_shares}</span>
                </div>
                <div className="flex justify-between">
                  <span>سعر السهم</span>
                  <span className="text-foreground/80">{token.share_price_mrusdt} MR_USDT</span>
                </div>
                <div className="flex justify-between">
                  <span>العقد الذكي</span>
                  <span className="text-foreground/80 font-mono text-xs truncate max-w-[120px]">
                    {token.smart_contract_address || '—'}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}