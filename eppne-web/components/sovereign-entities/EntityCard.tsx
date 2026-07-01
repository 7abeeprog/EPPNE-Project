// components/sovereign-entities/EntityCard.tsx
'use client';

import Link from 'next/link';
import Image from 'next/image';
import { Building2, Wallet, CheckCircle, Clock, XCircle, Users } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SovereignEntity } from '@/types/sovereign-entities';

interface EntityCardProps {
  entity: SovereignEntity;
  isActive?: boolean;
}

const kybStatusMap = {
  PENDING: { label: 'قيد الانتظار', icon: Clock, className: 'text-amber-500 border-amber-500/30' },
  UNDER_REVIEW: { label: 'قيد المراجعة', icon: Clock, className: 'text-blue-500 border-blue-500/30' },
  VERIFIED: { label: 'موثق', icon: CheckCircle, className: 'text-emerald-500 border-emerald-500/30' },
  REJECTED: { label: 'مرفوض', icon: XCircle, className: 'text-red-500 border-red-500/30' },
  SUSPENDED: { label: 'معلق', icon: XCircle, className: 'text-orange-500 border-orange-500/30' },
};

export default function EntityCard({ entity, isActive = false }: EntityCardProps) {
  const StatusIcon = kybStatusMap[entity.kyb_status].icon;

  return (
    <Link
      href={`/sovereign-entities/${entity.id}`}
      className={cn(
        "group relative block p-5 rounded-2xl transition-all duration-300",
        "bg-card/30 backdrop-blur-xl border border-white/10",
        "hover:bg-card/50 hover:border-primary/30 hover:shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.2)]",
        isActive && "border-primary/50 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)]"
      )}
      style={{
        '--entity-primary': entity.primary_color || '#8CC63F',
      } as React.CSSProperties}
    >
      {/* شريط لوني علوي */}
      <div 
        className="absolute top-0 left-0 right-0 h-1 rounded-t-2xl"
        style={{ backgroundColor: entity.primary_color || '#8CC63F' }}
      />

      <div className="flex items-start gap-4">
        {/* الشعار */}
        <div className="w-14 h-14 rounded-xl overflow-hidden bg-white/5 border border-white/10 flex-shrink-0">
          {entity.logo_url ? (
            <Image src={entity.logo_url} alt={entity.name} width={56} height={56} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-2xl">
              <Building2 className="w-6 h-6 text-foreground/30" />
            </div>
          )}
        </div>

        {/* المحتوى */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h3 className="font-semibold text-foreground/90 truncate group-hover:text-primary transition-colors">
                {entity.name}
              </h3>
              <p className="text-xs text-muted-foreground/70 truncate">
                {entity.entity_type.replace(/_/g, ' ')} • {entity.country_of_origin}
              </p>
            </div>
            <div className={cn(
              "flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border",
              kybStatusMap[entity.kyb_status].className
            )}>
              <StatusIcon className="w-3 h-3" />
              {kybStatusMap[entity.kyb_status].label}
            </div>
          </div>

          {/* الصف السفلي: الرصيد + عدد الممثلين */}
          <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground/60">
            <span className="flex items-center gap-1">
              <Wallet className="w-3 h-3" />
              {entity.treasury_balance_mrusdt.toFixed(2)} MR_USDT
            </span>
            <span className="flex items-center gap-1">
              <Users className="w-3 h-3" />
              {/* عدد الممثلين سيتم جلبه من بيانات إضافية أو نقدر نضيفه في الـ API */}
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}