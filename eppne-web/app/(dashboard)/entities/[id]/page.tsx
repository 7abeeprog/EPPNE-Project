// app/(dashboard)/entities/[id]/page.tsx
"use client";

import React from "react";
import { useParams, useRouter } from "next/navigation";
import { useEntityStore } from "@/store/entity-store";
import { useEntityDetails } from "@/hooks/use-entities";
import { EntityTabs } from "@/components/entities/entity-tabs";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, Building2, ShieldCheck, Zap } from "lucide-react";
import Link from "next/link";

export default function EntityDetailPage() {
  const params = useParams();
  const router = useRouter();
  const entityId = parseInt(params.id as string);
  const { entity, isLoading, error } = useEntityDetails(entityId);
  const { clearCurrent } = useEntityStore();

  React.useEffect(() => {
    return () => clearCurrent();
  }, [clearCurrent]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] bg-card/20 rounded-3xl border border-rose-500/20">
        <ShieldCheck className="h-16 w-16 text-rose-500/50 mb-4" />
        <p className="text-rose-500 font-bold mb-4">{error}</p>
        <Button variant="outline" onClick={() => router.push("/entities")}>العودة للقيادة المركزية</Button>
      </div>
    );
  }

  if (isLoading || !entity) {
    return (
      <div className="space-y-8 animate-pulse">
        <div className="flex items-center gap-4">
          <Skeleton className="h-12 w-12 rounded-2xl" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
        <Skeleton className="h-[400px] w-full rounded-3xl" />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* 🟢 رأس الكيان السيادي */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 p-6 rounded-3xl bg-card/30 backdrop-blur-xl border border-white/10 shadow-[0_10px_30px_rgba(0,0,0,0.1)]">
        <div className="flex items-center gap-4">
          <Link href="/entities">
            <Button variant="ghost" size="icon" className="rounded-xl hover:bg-primary/10">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <div className="flex items-center gap-4">
            {entity.logo_url ? (
              <img src={entity.logo_url} alt={entity.name} className="h-16 w-16 rounded-2xl object-cover shadow-lg border border-white/10" />
            ) : (
              <div className="h-16 w-16 rounded-2xl bg-primary/10 flex items-center justify-center border border-primary/20">
                <Building2 className="h-8 w-8 text-primary" />
              </div>
            )}
            <div>
              <h1 className="text-3xl font-black text-foreground flex items-center gap-2">
                {entity.name}
                <Zap className="h-5 w-5 text-amber-500 fill-amber-500" />
              </h1>
              <p className="text-sm font-bold text-muted-foreground uppercase tracking-widest">{entity.legal_name || "كيان سيادي"}</p>
            </div>
          </div>
        </div>
        
        {/* 🟢 إجراءات سريعة */}
        <div className="flex gap-3">
          <Link href={`/entities/${entityId}/brand-builder`}>
            <Button className="rounded-xl font-bold bg-primary hover:bg-primary/90 shadow-[0_0_15px_rgba(var(--primary-rgb),0.3)]">
              استوديو البناء
            </Button>
          </Link>
        </div>
      </div>

      {/* 🟢 التبويبات السيادية */}
      <div className="bg-card/30 backdrop-blur-xl border border-white/10 rounded-3xl p-6 shadow-xl">
        <EntityTabs entity={entity} />
      </div>
    </div>
  );
}