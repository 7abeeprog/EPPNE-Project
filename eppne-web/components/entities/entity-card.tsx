// components/entities/entity-card.tsx
"use client";

import Link from "next/link";
import { Building2, CheckCircle, Clock, XCircle, Wallet, ShieldCheck, ArrowUpLeft } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SovereignEntity, KYBStatus } from "@/types/entity";

interface EntityCardProps {
  entity: SovereignEntity;
}

// 🟢 توحيد الشارات السيادية مع إضاءات النيون الزجاجية
const statusConfig: Record<KYBStatus, { label: string; color: string; icon: any }> = {
  VERIFIED: { label: "موثق سيادياً", color: "bg-emerald-500/10 border-emerald-500/30 text-emerald-500", icon: ShieldCheck },
  REJECTED: { label: "مرفوض", color: "bg-red-500/10 border-red-500/30 text-red-500", icon: XCircle },
  PENDING: { label: "قيد المراجعة", color: "bg-amber-500/10 border-amber-500/30 text-amber-500", icon: Clock },
  UNDER_REVIEW: { label: "قيد التدقيق", color: "bg-blue-500/10 border-blue-500/30 text-blue-500", icon: Clock },
  SUSPENDED: { label: "معلق", color: "bg-orange-500/10 border-orange-500/30 text-orange-500", icon: XCircle },
};

export function EntityCard({ entity }: EntityCardProps) {
  const status = statusConfig[entity.kyb_status] || statusConfig.PENDING;
  const StatusIcon = status.icon;

  return (
    <div className="relative group overflow-hidden rounded-3xl bg-card/40 backdrop-blur-xl border border-white/10 transition-all duration-500 hover:-translate-y-1 hover:border-primary/30 hover:shadow-[0_15px_40px_rgba(var(--primary-rgb),0.15)] flex flex-col h-full">
      
      {/* 🟢 إضاءة خلفية نيون تتفاعل مع الماوس */}
      <div className="absolute top-0 right-0 w-40 h-40 bg-primary/10 blur-[60px] rounded-full pointer-events-none transition-opacity duration-500 opacity-40 group-hover:opacity-100" />

      {/* 🟢 رأس البطاقة */}
      <div className="p-5 flex flex-row items-start justify-between gap-4 relative z-10">
        <div className="flex items-center gap-3">
          <div className="h-12 w-12 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center shadow-inner overflow-hidden flex-shrink-0">
            {entity.logo_url ? (
              <img src={entity.logo_url} alt={entity.name} className="h-full w-full object-cover" />
            ) : (
              <Building2 className="h-6 w-6 text-primary" />
            )}
          </div>
          <div className="space-y-1">
            <h3 className="text-xl font-black text-foreground line-clamp-1">{entity.name}</h3>
            <p className="text-xs font-medium text-muted-foreground line-clamp-1">
              {entity.legal_name || "كيان قيد التأسيس"}
            </p>
          </div>
        </div>
      </div>

      {/* 🟢 محتوى البطاقة (الحالة والأرصدة) */}
      <div className="px-5 pb-5 flex-1 flex flex-col gap-4 relative z-10">
        
        {/* شارة التوثيق */}
        <div>
          <Badge variant="outline" className={`${status.color} backdrop-blur-md flex w-fit items-center gap-1.5 px-2.5 py-1 rounded-lg border shadow-sm`}>
            <StatusIcon className="h-3.5 w-3.5" />
            <span className="font-bold text-xs tracking-wide">{status.label}</span>
          </Badge>
        </div>

        {/* معلومات الخزينة والتاريخ */}
        <div className="grid grid-cols-2 gap-3 mt-auto pt-4 border-t border-white/5">
          <div className="flex flex-col gap-1 bg-background/40 p-2.5 rounded-xl border border-white/5 shadow-inner">
            <div className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1.5">
              <Wallet className="h-3 w-3 text-emerald-500" /> الخزينة (MR_USDT)
            </div>
            <div className="text-sm font-mono font-black text-foreground">
              {entity.treasury_balance_mrusdt.toLocaleString()}
            </div>
          </div>
          
          <div className="flex flex-col gap-1 bg-background/40 p-2.5 rounded-xl border border-white/5 shadow-inner">
            <div className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1.5">
              <Clock className="h-3 w-3 text-primary/70" /> تاريخ التأسيس
            </div>
            <div className="text-sm font-medium text-foreground">
              {new Date(entity.created_at).toLocaleDateString("ar-EG")}
            </div>
          </div>
        </div>
      </div>

      {/* 🟢 ذيل البطاقة (الإجراءات) */}
      <div className="p-3 mt-auto relative z-10">
        <Link href={`/entities/${entity.id}`} className="w-full block">
          <Button variant="outline" className="w-full rounded-xl bg-background/50 backdrop-blur-md border border-white/5 hover:bg-primary hover:text-primary-foreground hover:border-primary transition-all duration-300 font-bold group/btn h-11">
            إدارة الكيان السيادي
            <ArrowUpLeft className="mr-2 h-4 w-4 opacity-50 group-hover/btn:opacity-100 group-hover/btn:-translate-y-0.5 group-hover/btn:-translate-x-0.5 transition-transform" />
          </Button>
        </Link>
      </div>
    </div>
  );
}