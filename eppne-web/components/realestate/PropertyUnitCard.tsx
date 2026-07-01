// components/realestate/PropertyUnitCard.tsx
'use client';

import Link from 'next/link';
import { Building2, MapPin, DollarSign, TrendingUp, Home } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { PropertyUnit } from '@/types/realestate';

interface PropertyUnitCardProps {
  unit: PropertyUnit;
  className?: string;
}

const propertyTypeIcons: Record<string, React.ReactNode> = {
  APARTMENT: <Home className="w-4 h-4" />,
  VILLA: <Building2 className="w-4 h-4" />,
  OFFICE: <Building2 className="w-4 h-4" />,
  RETAIL: <Building2 className="w-4 h-4" />,
  WAREHOUSE: <Building2 className="w-4 h-4" />,
  FACTORY: <Building2 className="w-4 h-4" />,
  LAND: <MapPin className="w-4 h-4" />,
};

const propertyTypeLabels: Record<string, string> = {
  APARTMENT: 'شقة',
  VILLA: 'فيلا',
  OFFICE: 'مكتب',
  RETAIL: 'محل تجاري',
  WAREHOUSE: 'مستودع',
  FACTORY: 'مصنع',
  LAND: 'أرض',
};

export default function PropertyUnitCard({ unit, className }: PropertyUnitCardProps) {
  return (
    <Link
      href={`/realestate/units/${unit.id}`}
      className={cn(
        "group block p-5 rounded-2xl transition-all duration-300",
        "bg-card/30 backdrop-blur-xl border border-white/10",
        "hover:bg-card/50 hover:border-primary/30 hover:shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.2)]",
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-primary/10 text-primary">
            {propertyTypeIcons[unit.property_type] || <Building2 className="w-5 h-5" />}
          </div>
          <div>
            <h4 className="font-medium text-foreground/90">{unit.unit_number}</h4>
            <p className="text-xs text-muted-foreground/50">
              {propertyTypeLabels[unit.property_type] || unit.property_type}
              {unit.floor_number !== null && ` • الطابق ${unit.floor_number}`}
            </p>
          </div>
        </div>
        <div className="text-right">
          {unit.is_available_for_sale && unit.sale_price_mrusdt && (
            <span className="text-sm font-bold text-primary">
              {unit.sale_price_mrusdt.toFixed(2)} MR_USDT
            </span>
          )}
          {unit.is_available_for_rent && unit.rent_per_month_mrusdt && (
            <span className="text-xs text-muted-foreground/60">
              {unit.rent_per_month_mrusdt.toFixed(2)} MR_USDT/شهر
            </span>
          )}
        </div>
      </div>

      <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground/50">
        <span className="flex items-center gap-1">
          <TrendingUp className="w-3 h-3" />
          {unit.area_sqm} م²
        </span>
        <span className={cn(
          "px-2 py-0.5 rounded-full border",
          unit.is_available_for_sale ? "border-emerald-500/30 text-emerald-500" : "border-red-500/30 text-red-500"
        )}>
          {unit.is_available_for_sale ? 'للبيع' : 'غير متاح'}
        </span>
      </div>
    </Link>
  );
}