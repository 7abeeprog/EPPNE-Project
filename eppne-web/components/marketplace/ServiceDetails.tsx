// components/marketplace/ServiceDetails.tsx
'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getService, getAddons } from '@/services/marketplace';
import { Loader2, DollarSign, Package, List, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';
import PurchaseModal from './PurchaseModal';
import type { MarketplaceService, ServiceAddon } from '@/types/marketplace';

interface ServiceDetailsProps {
  serviceId: number;
}

const pricingPlans = [
  { key: 'basic', label: 'أساسي', color: 'text-blue-500' },
  { key: 'professional', label: 'احترافي', color: 'text-primary' },
  { key: 'enterprise', label: 'مؤسسي', color: 'text-purple-500' },
];

export default function ServiceDetails({ serviceId }: ServiceDetailsProps) {
  const [showPurchase, setShowPurchase] = useState(false);

  const { data: service, isLoading: isLoadingService } = useQuery({
    queryKey: ['marketplace-service', serviceId],
    queryFn: () => getService(serviceId).then(res => res.data),
    staleTime: 2 * 60 * 1000,
  });

  const { data: addons, isLoading: isLoadingAddons } = useQuery({
    queryKey: ['marketplace-addons', serviceId],
    queryFn: () =>
      getAddons({ compatible_with: service?.service_type }).then(res => res.data),
    enabled: !!service,
    staleTime: 2 * 60 * 1000,
  });

  if (isLoadingService) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!service) {
    return (
      <div className="text-center py-16 text-muted-foreground/60">
        <p className="text-lg">الخدمة غير موجودة</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* الهيدر */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">{service.name}</h1>
          <p className="text-sm text-muted-foreground/60 mt-1">{service.description}</p>
        </div>
        <button
          onClick={() => setShowPurchase(true)}
          className="px-6 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          شراء الخدمة
        </button>
      </div>

      {/* معلومات سريعة */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3 rounded-xl bg-card/20 backdrop-blur-xl border border-white/10">
          <div className="text-xs text-muted-foreground/50">الإصدار</div>
          <div className="text-sm font-medium text-foreground/80">{service.version}</div>
        </div>
        <div className="p-3 rounded-xl bg-card/20 backdrop-blur-xl border border-white/10">
          <div className="text-xs text-muted-foreground/50">النوع</div>
          <div className="text-sm font-medium text-foreground/80">{service.service_type}</div>
        </div>
        <div className="p-3 rounded-xl bg-card/20 backdrop-blur-xl border border-white/10">
          <div className="text-xs text-muted-foreground/50">السعر الأساسي</div>
          <div className="text-sm font-medium text-foreground/80">
            {service.base_price_mrusdt > 0 ? `${service.base_price_mrusdt} MR_USDT` : 'مجاني'}
          </div>
        </div>
        <div className="p-3 rounded-xl bg-card/20 backdrop-blur-xl border border-white/10">
          <div className="text-xs text-muted-foreground/50">الحالة</div>
          <div className="text-sm font-medium text-foreground/80">
            {service.is_active ? '🟢 نشط' : '🔴 غير نشط'}
          </div>
        </div>
      </div>

      {/* خطط الأسعار */}
      <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <h3 className="text-sm font-medium text-foreground/70 mb-3">💰 خطط الاشتراك</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <span className="text-xs text-muted-foreground/50">أساسي</span>
            <p className="text-lg font-bold text-foreground/80">
              {service.subscription_price_basic_mrusdt > 0
                ? `${service.subscription_price_basic_mrusdt} MR_USDT`
                : 'مجاني'}
            </p>
            <span className="text-[10px] text-muted-foreground/40">/ شهر</span>
          </div>
          <div className="p-3 rounded-xl bg-primary/5 border border-primary/30 text-center">
            <span className="text-xs text-primary/70">احترافي</span>
            <p className="text-lg font-bold text-foreground/80">
              {service.subscription_price_pro_mrusdt > 0
                ? `${service.subscription_price_pro_mrusdt} MR_USDT`
                : 'مجاني'}
            </p>
            <span className="text-[10px] text-muted-foreground/40">/ شهر</span>
          </div>
          <div className="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
            <span className="text-xs text-muted-foreground/50">مؤسسي</span>
            <p className="text-lg font-bold text-foreground/80">
              {service.subscription_price_enterprise_mrusdt > 0
                ? `${service.subscription_price_enterprise_mrusdt} MR_USDT`
                : 'مجاني'}
            </p>
            <span className="text-[10px] text-muted-foreground/40">/ شهر</span>
          </div>
        </div>
      </div>

      {/* الإضافات المتاحة */}
      {addons && addons.length > 0 && (
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <h3 className="text-sm font-medium text-foreground/70 mb-3 flex items-center gap-2">
            <Package className="w-4 h-4 text-muted-foreground/50" />
            الإضافات المتاحة
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {addons.map((addon) => (
              <div key={addon.id} className="flex items-center justify-between p-2 rounded-xl bg-white/5 border border-white/5">
                <div>
                  <span className="text-sm text-foreground/80">{addon.name}</span>
                  <p className="text-[10px] text-muted-foreground/40">{addon.addon_type}</p>
                </div>
                <span className="text-xs font-medium text-primary">
                  {addon.price_mrusdt > 0 ? `${addon.price_mrusdt} MR_USDT` : 'مجاني'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* المتطلبات */}
      {service.requires_modules.length > 0 && (
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <h3 className="text-sm font-medium text-foreground/70 mb-2 flex items-center gap-2">
            <List className="w-4 h-4 text-muted-foreground/50" />
            الوحدات المطلوبة
          </h3>
          <div className="flex flex-wrap gap-2">
            {service.requires_modules.map((mod) => (
              <span key={mod} className="px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-xs text-muted-foreground/60">
                {mod}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* نافذة الشراء */}
      {showPurchase && (
        <PurchaseModal
          service={service}
          addons={addons || []}
          onClose={() => setShowPurchase(false)}
        />
      )}
    </div>
  );
}