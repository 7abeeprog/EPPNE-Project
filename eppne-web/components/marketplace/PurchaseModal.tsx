// components/marketplace/PurchaseModal.tsx
'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { purchaseService } from '@/services/marketplace';
import { X, Loader2, Check, AlertTriangle, DollarSign } from 'lucide-react';
import { cn } from '@/lib/utils';
import { v4 as uuidv4 } from 'uuid';
import type { MarketplaceService, ServiceAddon, SubscriptionPlan, PurchaseData } from '@/types/marketplace';

interface PurchaseModalProps {
  service: MarketplaceService;
  addons: ServiceAddon[];
  onClose: () => void;
}

const planLabels: Record<SubscriptionPlan, string> = {
  FREE: 'مجاني',
  BASIC: 'أساسي',
  PROFESSIONAL: 'احترافي',
  ENTERPRISE: 'مؤسسي',
};

export default function PurchaseModal({ service, addons, onClose }: PurchaseModalProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [selectedPlan, setSelectedPlan] = useState<SubscriptionPlan>('BASIC');
  const [selectedAddons, setSelectedAddons] = useState<number[]>([]);
  const [customDomain, setCustomDomain] = useState('');
  const [autoRenew, setAutoRenew] = useState(true);

  // توليد Idempotency Key عند فتح النافذة
  const idempotencyKey = useRef(`purchase-${uuidv4()}`);

  const planPrices: Record<SubscriptionPlan, number> = {
    FREE: 0,
    BASIC: Number(service.subscription_price_basic_mrusdt) || 0,
    PROFESSIONAL: Number(service.subscription_price_pro_mrusdt) || 0,
    ENTERPRISE: Number(service.subscription_price_enterprise_mrusdt) || 0,
  };

  const addonsPrice = selectedAddons.reduce((sum, id) => {
    const addon = addons.find(a => a.id === id);
    return sum + (addon ? Number(addon.price_mrusdt) : 0);
  }, 0);

  const totalPrice = planPrices[selectedPlan] + addonsPrice;

  const mutation = useMutation({
    mutationFn: () => {
      const data: PurchaseData = {
        service_id: service.id,
        subscription_plan: selectedPlan,
        purchased_addons: selectedAddons,
        custom_config: {},
        custom_domain: customDomain || undefined,
        auto_renew: autoRenew,
      };
      return purchaseService(data, idempotencyKey.current);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-licenses'] });
      onClose();
      router.push('/marketplace/licenses');
    },
  });

  const toggleAddon = (addonId: number) => {
    setSelectedAddons(prev =>
      prev.includes(addonId) ? prev.filter(id => id !== addonId) : [...prev, addonId]
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200 p-4">
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 rounded-3xl bg-card/80 backdrop-blur-3xl border border-white/15 shadow-[0_20px_80px_-20px_rgba(0,0,0,0.6)] animate-in zoom-in-95 duration-200">
        {/* شريط علوي */}
        <div className="absolute top-0 left-0 right-0 h-1 rounded-t-3xl bg-gradient-to-r from-primary to-secondary" />

        {/* زر الإغلاق */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 p-1 rounded-lg hover:bg-white/10 transition-colors"
        >
          <X className="w-4 h-4 text-muted-foreground/60" />
        </button>

        {/* الهيدر */}
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-xl bg-primary/20 text-primary">
            <DollarSign className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-foreground/90">شراء الخدمة</h3>
            <p className="text-xs text-muted-foreground/50">{service.name}</p>
          </div>
        </div>

        <div className="space-y-4">
          {/* خطة الاشتراك */}
          <div>
            <label className="text-sm font-medium text-foreground/80">اختر خطة الاشتراك</label>
            <div className="grid grid-cols-3 gap-2 mt-1.5">
              {(['BASIC', 'PROFESSIONAL', 'ENTERPRISE'] as SubscriptionPlan[]).map((plan) => (
                <button
                  key={plan}
                  type="button"
                  onClick={() => setSelectedPlan(plan)}
                  className={cn(
                    "p-3 rounded-xl border transition-all duration-200 text-center",
                    selectedPlan === plan
                      ? "border-primary/50 bg-primary/20 text-primary"
                      : "border-white/10 bg-white/5 text-muted-foreground/70 hover:bg-white/10"
                  )}
                >
                  <div className="font-medium">{planLabels[plan]}</div>
                  <div className="text-xs text-muted-foreground/50">
                    {planPrices[plan] > 0 ? `${planPrices[plan]} MR_USDT` : 'مجاني'}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* الإضافات */}
          {addons.length > 0 && (
            <div>
              <label className="text-sm font-medium text-foreground/80">الإضافات</label>
              <div className="space-y-1.5 mt-1.5">
                {addons.map((addon) => (
                  <button
                    key={addon.id}
                    type="button"
                    onClick={() => toggleAddon(addon.id)}
                    className={cn(
                      "flex items-center justify-between w-full p-3 rounded-xl border transition-all duration-200 text-sm",
                      selectedAddons.includes(addon.id)
                        ? "border-primary/50 bg-primary/10 text-foreground/80"
                        : "border-white/10 bg-white/5 text-muted-foreground/60 hover:bg-white/10"
                    )}
                  >
                    <span>{addon.name}</span>
                    <span className="text-primary">
                      {selectedAddons.includes(addon.id) && <Check className="w-4 h-4 inline mr-1" />}
                      {addon.price_mrusdt > 0 ? `${addon.price_mrusdt} MR_USDT` : 'مجاني'}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* النطاق المخصص */}
          <div>
            <label className="text-sm font-medium text-foreground/80">النطاق المخصص (اختياري)</label>
            <input
              type="text"
              value={customDomain}
              onChange={(e) => setCustomDomain(e.target.value)}
              placeholder="مثال: my-app.eppne.com"
              className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            />
          </div>

          {/* التجديد التلقائي */}
          <div className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10">
            <label className="flex items-center gap-2 text-sm text-foreground/80 cursor-pointer">
              <input
                type="checkbox"
                checked={autoRenew}
                onChange={(e) => setAutoRenew(e.target.checked)}
                className="w-4 h-4 rounded border-white/20 bg-white/5"
              />
              تفعيل التجديد التلقائي
            </label>
            <span className="text-[10px] text-muted-foreground/40">سيتم تجديد الاشتراك تلقائياً كل عام</span>
          </div>

          {/* ملخص السعر */}
          <div className="p-4 rounded-2xl bg-primary/5 border border-primary/20">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground/60">الإجمالي</span>
              <span className="text-xl font-bold text-primary">{totalPrice.toFixed(2)} MR_USDT</span>
            </div>
            <div className="text-[10px] text-muted-foreground/40 mt-1">
              شامل رسوم الخدمة الأساسية والإضافات المختارة
            </div>
          </div>

          {/* أزرار الإجراء */}
          <div className="flex gap-3 pt-2">
            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
            >
              {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              {mutation.isPending ? 'جاري الشراء...' : 'تأكيد الشراء'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl border border-white/10 hover:bg-white/5 transition-colors text-foreground/70"
            >
              إلغاء
            </button>
          </div>

          {/* ملاحظة Idempotency */}
          <div className="text-[10px] text-muted-foreground/30 text-center">
            🔒 معرف العملية: {idempotencyKey.current.slice(0, 8)}... (لمنع التكرار)
          </div>
        </div>
      </div>
    </div>
  );
}