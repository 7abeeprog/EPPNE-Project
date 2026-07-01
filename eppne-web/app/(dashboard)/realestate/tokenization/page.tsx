// app/(dashboard)/realestate/tokenization/page.tsx (الإصدار المحدث)
'use client';

import { useState } from 'react';
import { useAssetTokenization, useCreateTokenization } from '@/hooks/realestate/useTokenization';
import { useProperties } from '@/hooks/realestate/useProperties';
import { Loader2, Plus, Coins, DollarSign, Share2, CheckCircle, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function TokenizationPage() {
  const [selectedUnitId, setSelectedUnitId] = useState<number | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [formData, setFormData] = useState({
    total_shares: 1000,
    share_price_mrusdt: 10,
    minimum_investment_shares: 1,
  });
  const [idempotencyKey, setIdempotencyKey] = useState<string>('');

  const { data: properties, isLoading: propertiesLoading, error: propertiesError } = useProperties();
  // استخدام الـ Hook فقط إذا كان هناك selectedUnitId صالح
  const { data: tokenization, isLoading: tokenizationLoading, error: tokenizationError } = useAssetTokenization(
    selectedUnitId || 0,
    { enabled: !!selectedUnitId } // إذا كان الـ Hook يدعم enabled، وإلا سنتحقق يدوياً
  );
  const createTokenization = useCreateTokenization();

  const handleCreate = () => {
    if (!selectedUnitId) {
      alert('الرجاء اختيار عقار أولاً');
      return;
    }
    const key = `tokenize-${selectedUnitId}-${Date.now()}`;
    setIdempotencyKey(key);
    createTokenization.mutate(
      {
        unit_id: selectedUnitId,
        total_shares: formData.total_shares,
        share_price_mrusdt: formData.share_price_mrusdt,
        minimum_investment_shares: formData.minimum_investment_shares,
        idempotency_key: key,
      },
      {
        onSuccess: () => {
          alert('✅ تم إنشاء التجزئة بنجاح');
          setShowCreate(false);
          // يمكن إعادة تعيين النموذج
        },
        onError: (err: any) => {
          alert(`❌ فشل إنشاء التجزئة: ${err.message || 'خطأ غير معروف'}`);
        },
      }
    );
  };

  if (propertiesLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (propertiesError) {
    return (
      <div className="text-center py-16 text-muted-foreground/60">
        <AlertCircle className="w-12 h-12 mx-auto mb-4 opacity-30" />
        <p className="text-lg">فشل في تحميل قائمة العقارات</p>
        <p className="text-sm text-muted-foreground/40">{(propertiesError as Error).message}</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">🔗 تجزئة الأصول</h1>
          <p className="text-sm text-muted-foreground/70">إدارة تجزئة العقارات إلى أسهم قابلة للتداول</p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          تجزئة جديدة
        </button>
      </div>

      {/* اختيار العقار */}
      <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <label className="text-sm font-medium text-foreground/80">اختر العقار</label>
        <select
          value={selectedUnitId || ''}
          onChange={(e) => setSelectedUnitId(parseInt(e.target.value))}
          className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
        >
          <option value="">اختر عقاراً...</option>
          {properties?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} ({p.area_sqm} م²)
            </option>
          ))}
        </select>
        {!properties || properties.length === 0 && (
          <p className="text-xs text-amber-500/80 mt-2">لا توجد عقارات متاحة للتجزئة حالياً</p>
        )}
      </div>

      {/* عرض التجزئة الحالية */}
      {selectedUnitId && tokenizationLoading && (
        <div className="flex justify-center py-4">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </div>
      )}
      {selectedUnitId && !tokenizationLoading && tokenization && (
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-emerald-500/20">
          <div className="flex items-center gap-3">
            <Coins className="w-6 h-6 text-emerald-500" />
            <div>
              <p className="font-medium text-foreground/80">تم تجزئة هذا العقار</p>
              <div className="flex items-center gap-4 mt-1 text-sm">
                <span className="text-muted-foreground/60">إجمالي الأسهم: {tokenization.total_shares}</span>
                <span className="text-muted-foreground/60">سعر السهم: {tokenization.share_price_mrusdt} MR_USDT</span>
                <span className={cn(
                  "text-xs px-2 py-0.5 rounded-full",
                  tokenization.is_fully_subscribed ? "bg-emerald-500/20 text-emerald-500" : "bg-amber-500/20 text-amber-500"
                )}>
                  {tokenization.is_fully_subscribed ? 'مكتمل' : 'متاح'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
      {selectedUnitId && !tokenizationLoading && !tokenization && (
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 text-muted-foreground/60 text-sm">
          هذا العقار غير مجزأ حالياً. يمكنك إنشاء تجزئة جديدة له.
        </div>
      )}

      {/* نموذج إنشاء التجزئة */}
      {showCreate && selectedUnitId && (
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 space-y-4">
          <h3 className="font-medium text-foreground/80">تفاصيل التجزئة</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-muted-foreground/60">إجمالي الأسهم</label>
              <input
                type="number"
                value={formData.total_shares}
                onChange={(e) => setFormData({ ...formData, total_shares: parseInt(e.target.value) || 0 })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                min="1"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground/60">سعر السهم (MR_USDT)</label>
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
              <label className="text-xs text-muted-foreground/60">الحد الأدنى للاستثمار (أسهم)</label>
              <input
                type="number"
                value={formData.minimum_investment_shares}
                onChange={(e) => setFormData({ ...formData, minimum_investment_shares: parseInt(e.target.value) || 1 })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                min="1"
              />
            </div>
          </div>
          <button
            onClick={handleCreate}
            disabled={createTokenization.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium disabled:opacity-50"
          >
            {createTokenization.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Share2 className="w-4 h-4" />}
            إنشاء التجزئة
          </button>
          <p className="text-[10px] text-muted-foreground/40 mt-2">
            سيتم استخدام مفتاح Idempotency تلقائياً لمنع التكرار
          </p>
        </div>
      )}
    </div>
  );
}