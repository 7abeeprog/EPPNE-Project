// components/marketplace/ServiceCard.tsx
'use client';

import Link from 'next/link';
import Image from 'next/image';
import { Building2, Tag, Star, ShoppingCart } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { MarketplaceService } from '@/types/marketplace';

interface ServiceCardProps {
  service: MarketplaceService;
  className?: string;
}

const serviceTypeIcons: Record<string, string> = {
  RIDE_HAILING: '🚗',
  DELIVERY: '📦',
  E_COMMERCE: '🛍️',
  TOURISM_BOOKING: '✈️',
  EDUCATION_PLATFORM: '📚',
  JOB_MARKETPLACE: '💼',
  SOCIAL_NETWORK: '🌐',
  HEALTHCARE_PORTAL: '🏥',
  REAL_ESTATE: '🏠',
  EVENT_MANAGEMENT: '🎪',
  CUSTOM: '⚙️',
};

const serviceTypeLabels: Record<string, string> = {
  RIDE_HAILING: 'تطبيق نقل ركاب',
  DELIVERY: 'تطبيق توصيل',
  E_COMMERCE: 'متجر إلكتروني',
  TOURISM_BOOKING: 'حجز سياحي',
  EDUCATION_PLATFORM: 'منصة تعليمية',
  JOB_MARKETPLACE: 'منصة توظيف',
  SOCIAL_NETWORK: 'شبكة اجتماعية',
  HEALTHCARE_PORTAL: 'بوابة صحية',
  REAL_ESTATE: 'منصة عقارات',
  EVENT_MANAGEMENT: 'إدارة فعاليات',
  CUSTOM: 'مخصص',
};

export default function ServiceCard({ service, className }: ServiceCardProps) {
  const basePrice = service.base_price_mrusdt || 0;
  const hasSubscription = service.subscription_price_basic_mrusdt > 0;

  return (
    <Link
      href={`/marketplace/services/${service.id}`}
      className={cn(
        "group block p-5 rounded-2xl transition-all duration-300",
        "bg-card/30 backdrop-blur-xl border border-white/10",
        "hover:bg-card/50 hover:border-primary/30 hover:shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.2)]",
        className
      )}
    >
      {/* أيقونة الخدمة */}
      <div className="relative w-full h-32 rounded-xl overflow-hidden mb-4 bg-white/5 flex items-center justify-center text-6xl">
        {service.thumbnail_url ? (
          <Image
            src={service.thumbnail_url}
            alt={service.name}
            fill
            className="object-cover group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <span>{serviceTypeIcons[service.service_type] || '📦'}</span>
        )}
        {service.is_featured && (
          <span className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-primary/80 text-white text-[10px] font-medium backdrop-blur-sm">
            <Star className="w-3 h-3 inline mr-0.5" />
            مميز
          </span>
        )}
      </div>

      {/* المحتوى */}
      <div className="space-y-2">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-semibold text-foreground/90 text-lg line-clamp-1 group-hover:text-primary transition-colors">
              {service.name}
            </h3>
            <p className="text-xs text-muted-foreground/50">
              {serviceTypeLabels[service.service_type] || service.service_type}
            </p>
          </div>
          <span className="text-sm font-bold text-primary/80 whitespace-nowrap">
            {basePrice > 0 ? `${basePrice} MR_USDT` : hasSubscription ? 'اشتراك' : 'مجاني'}
          </span>
        </div>

        <p className="text-sm text-muted-foreground/60 line-clamp-2">
          {service.description || 'لا يوجد وصف'}
        </p>

        <div className="flex items-center gap-3 pt-2 border-t border-white/5 text-xs text-muted-foreground/40">
          <span>الإصدار {service.version}</span>
          {service.requires_modules.length > 0 && (
            <span>• {service.requires_modules.length} وحدات مطلوبة</span>
          )}
        </div>
      </div>
    </Link>
  );
}