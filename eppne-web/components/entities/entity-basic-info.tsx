// components/entities/entity-basic-info.tsx
"use client";

import { useState } from "react";
import { EntityForm, EntityFormValues } from "./entity-form";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SovereignEntity, KYBStatus } from "@/types/entity";
import { Pencil, CheckCircle, XCircle, Clock, ShieldCheck, Mail, Phone, MapPin, Globe, Fingerprint, Building, Wallet, FileText } from "lucide-react";
// 🟢 الترقية المعمارية: استخدام الهوك السيادي بدلاً من الـ Store
import { useEntityMutations } from "@/hooks/use-entities"; 

// ترقية تصميم حالات الـ KYB إلى شارات سيادية زجاجية متوهجة
const statusConfig: Record<KYBStatus, { label: string, color: string, icon: any }> = {
  VERIFIED: { label: "موثق سيادياً", color: "bg-emerald-500/10 border-emerald-500/30 text-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.2)]", icon: ShieldCheck },
  REJECTED: { label: "مرفوض", color: "bg-red-500/10 border-red-500/30 text-red-500 shadow-[0_0_15px_rgba(239,68,68,0.2)]", icon: XCircle },
  PENDING: { label: "قيد المراجعة", color: "bg-amber-500/10 border-amber-500/30 text-amber-500 shadow-[0_0_15px_rgba(245,158,11,0.2)]", icon: Clock },
  UNDER_REVIEW: { label: "قيد التدقيق", color: "bg-blue-500/10 border-blue-500/30 text-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.2)]", icon: Clock },
  SUSPENDED: { label: "معلق", color: "bg-orange-500/10 border-orange-500/30 text-orange-500 shadow-[0_0_15px_rgba(249,115,22,0.2)]", icon: XCircle },
};

export function EntityBasicInfo({ entity }: { entity: SovereignEntity }) {
  const [isEditing, setIsEditing] = useState(false);
  
  // 🟢 استدعاء محركات البيانات السيادية مع تمرير معرف الكيان
  const { updateEntity } = useEntityMutations(entity.id);

  const onSubmit = (data: EntityFormValues) => {
    // الهوك السيادي يتكفل بإرسال البيانات، عرض الـ Toast، وتحديث الكاش تلقائياً!
    updateEntity.mutate(data, {
      onSuccess: () => setIsEditing(false),
    });
  };

  // 🟢 1. شاشة التحرير (Edit Mode) - بتصميم زجاجي
  if (isEditing) {
    return (
      <div className="w-full flex-1 rounded-[2rem] border border-primary/20 bg-card/40 backdrop-blur-2xl shadow-[0_0_40px_rgba(var(--primary-rgb),0.1)] animate-in fade-in zoom-in-95 duration-500 overflow-hidden relative">
        <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-transparent via-primary to-transparent opacity-50" />
        <div className="p-6 md:p-8 bg-muted/5 border-b border-white/5">
          <h2 className="text-2xl font-black flex items-center gap-2">
            <Pencil className="h-6 w-6 text-primary" />
            تحديث السجل السيادي
          </h2>
          <p className="text-muted-foreground mt-2 font-medium">الرجاء إدخال المعلومات الرسمية بدقة، هذه البيانات تخضع للتدقيق المالي (KYB)</p>
        </div>
        <div className="p-6 md:p-8">
          <EntityForm
            defaultValues={entity as any}
            onSubmit={onSubmit}
            isLoading={updateEntity.isPending} // 🟢 استخدام حالة التحميل من TanStack
            submitLabel="تشفير وحفظ البيانات"
          />
          <div className="mt-6 flex justify-end">
            <Button variant="ghost" onClick={() => setIsEditing(false)} className="rounded-xl hover:bg-destructive/10 hover:text-destructive transition-colors">
              إلغاء وتراجع
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const status = statusConfig[entity.kyb_status] || statusConfig.PENDING;
  const StatusIcon = status.icon;

  // 🟢 2. شاشة العرض الأساسية (Read Mode) - الهوية الزجاجية
  return (
    <div className="w-full rounded-[2rem] border border-white/10 bg-card/30 backdrop-blur-xl shadow-lg overflow-hidden relative transition-all duration-500 hover:border-white/20 hover:shadow-[0_8px_30px_rgba(0,0,0,0.12)]">
      {/* تأثير إضاءة خلفي خفيف */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 blur-[80px] rounded-full pointer-events-none" />

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 md:p-8 border-b border-white/5 bg-background/20 relative z-10">
        <div>
          <h2 className="text-2xl font-black flex items-center gap-3 text-foreground">
            <div className="p-2.5 bg-primary/10 rounded-xl border border-primary/20 shadow-inner">
              <Building className="h-6 w-6 text-primary" />
            </div>
            السجل الرسمي للكيان
          </h2>
          <p className="mt-2 text-sm text-muted-foreground font-medium">
            البيانات القانونية والمالية المشفرة في قواعد المنصة
          </p>
        </div>
        <Button onClick={() => setIsEditing(true)} className="w-full sm:w-auto font-bold rounded-xl shadow-lg hover:scale-105 transition-transform bg-primary text-primary-foreground">
          <Pencil className="ml-2 h-4 w-4" />
          تحديث السجل
        </Button>
      </div>

      <div className="p-6 md:p-8 relative z-10">
        {/* شبكة متجاوبة قوية */}
        <div className="grid gap-x-8 gap-y-8 grid-cols-1 md:grid-cols-2 xl:grid-cols-3">
          
          {/* 1. اسم الكيان */}
          <div className="space-y-1.5 p-4 rounded-2xl bg-background/40 border border-white/5 shadow-sm">
            <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Building className="h-4 w-4 text-primary/70" /> اسم الكيان
            </div>
            <div className="text-lg font-black text-foreground break-words">{entity.name}</div>
          </div>

          {/* 2. الاسم القانوني */}
          <div className="space-y-1.5 p-4 rounded-2xl bg-background/40 border border-white/5 shadow-sm">
            <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary/70" /> الاسم القانوني
            </div>
            <div className="text-lg font-medium text-foreground break-words">{entity.legal_name || "—"}</div>
          </div>

          {/* 3. حالة التحقق */}
          <div className="space-y-1.5 p-4 rounded-2xl bg-background/40 border border-white/5 shadow-sm">
            <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-primary/70" /> الحالة القانونية (KYB)
            </div>
            <div className="pt-1">
              <Badge variant="outline" className={`${status.color} backdrop-blur-md flex w-fit items-center gap-1.5 px-3 py-1.5 rounded-lg border`}>
                <StatusIcon className="h-4 w-4" />
                <span className="font-bold tracking-wide">{status.label}</span>
              </Badge>
            </div>
          </div>

          {/* 4. نوع الكيان */}
          <div className="space-y-1.5 p-4 rounded-2xl bg-background/40 border border-white/5 shadow-sm">
            <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Building className="h-4 w-4 text-primary/70" /> نوع الكيان
            </div>
            <div className="text-lg font-medium text-foreground">{entity.entity_type}</div>
          </div>

          {/* 5. رقم التسجيل */}
          <div className="space-y-1.5 p-4 rounded-2xl bg-background/40 border border-white/5 shadow-sm">
            <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Fingerprint className="h-4 w-4 text-primary/70" /> رقم التسجيل التجاري
            </div>
            <div className="text-lg font-mono text-foreground break-all">{entity.registration_number || "—"}</div>
          </div>

          {/* 6. الرقم الضريبي */}
          <div className="space-y-1.5 p-4 rounded-2xl bg-background/40 border border-white/5 shadow-sm">
            <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary/70" /> الرقم الضريبي
            </div>
            <div className="text-lg font-mono text-foreground break-all">{entity.tax_id || "—"}</div>
          </div>

          {/* 7. الدولة والمدينة */}
          <div className="space-y-1.5 p-4 rounded-2xl bg-background/40 border border-white/5 shadow-sm md:col-span-2 xl:col-span-1">
            <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Globe className="h-4 w-4 text-primary/70" /> الموقع الجغرافي
            </div>
            <div className="text-lg font-medium text-foreground">
              {entity.country_of_origin} {entity.city ? ` - ${entity.city}` : ""}
            </div>
          </div>

          {/* 8. العنوان */}
          <div className="space-y-1.5 p-4 rounded-2xl bg-background/40 border border-white/5 shadow-sm md:col-span-2 xl:col-span-2">
            <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <MapPin className="h-4 w-4 text-primary/70" /> العنوان التفصيلي
            </div>
            <div className="text-base font-medium text-foreground break-words">{entity.address || "—"}</div>
          </div>

          {/* 9. البريد والهاتف */}
          <div className="space-y-1.5 p-4 rounded-2xl bg-background/40 border border-white/5 shadow-sm">
            <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Mail className="h-4 w-4 text-primary/70" /> بيانات الاتصال
            </div>
            <div className="flex flex-col gap-1 pt-1">
              <div className="text-sm font-medium text-foreground break-all flex items-center gap-2"><Mail className="h-3 w-3 opacity-50"/> {entity.official_email}</div>
              {entity.official_phone && <div className="text-sm font-medium text-foreground flex items-center gap-2" dir="ltr"><Phone className="h-3 w-3 opacity-50"/> {entity.official_phone}</div>}
            </div>
          </div>

          {/* 10. الموقع الإلكتروني */}
          <div className="space-y-1.5 p-4 rounded-2xl bg-background/40 border border-white/5 shadow-sm">
            <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Globe className="h-4 w-4 text-primary/70" /> الموقع الإلكتروني
            </div>
            <div className="text-lg pt-1">
              {entity.website ? (
                <a href={entity.website} target="_blank" rel="noopener noreferrer" className="text-primary hover:text-primary/80 transition-colors font-bold break-all flex items-center gap-2">
                  {entity.website.replace(/^https?:\/\//, '')}
                </a>
              ) : (
                <span className="text-muted-foreground font-medium">—</span>
              )}
            </div>
          </div>

          {/* 11. عنوان المحفظة (Neon Web3 Style) */}
          <div className="space-y-2 md:col-span-2 xl:col-span-3 bg-emerald-500/5 p-5 rounded-2xl border border-emerald-500/20 shadow-[0_0_20px_rgba(16,185,129,0.05)] relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/0 via-emerald-500/5 to-emerald-500/0 opacity-0 group-hover:opacity-100 transition-opacity duration-1000" />
            <div className="text-xs font-bold uppercase tracking-wider text-emerald-600/80 dark:text-emerald-400/80 flex items-center gap-2 mb-1">
              <Wallet className="h-5 w-5 text-emerald-500" /> عنوان الخزينة السيادية (Web3 Wallet)
            </div>
            <div className="text-sm md:text-base font-mono font-black text-emerald-700 dark:text-emerald-300 break-all bg-emerald-500/10 p-3 rounded-xl border border-emerald-500/20">
              {entity.wallet_address || "لم يتم ربط محفظة لامركزية بعد"}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}