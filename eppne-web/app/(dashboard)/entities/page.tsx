// app/(dashboard)/entities/page.tsx
"use client";

import { Plus, Building2 } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { EntityCard } from "@/components/entities/entity-card";
import { useMyEntities } from "@/hooks/use-entities";
import { Skeleton } from "@/components/ui/skeleton";

export default function EntitiesPage() {
  const { entities, isLoading, error } = useMyEntities();

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <p className="text-red-500 mb-4">{error}</p>
        <Button onClick={() => window.location.reload()}>إعادة المحاولة</Button>
      </div>
    );
  }

  if (isLoading && entities.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">الكيانات السيادية</h1>
          <p className="text-muted-foreground">إدارة الكيانات التي تمثلها أو تديرها</p>
        </div>
        <Link href="/entities/create">
          <Button>
            <Plus className="ml-2 h-4 w-4" />
            كيان جديد
          </Button>
        </Link>
      </div>

      {entities.length === 0 ? (
        <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
          <Building2 className="h-16 w-16 text-muted-foreground mb-4" />
          <h2 className="text-xl font-semibold">لا توجد كيانات بعد</h2>
          <p className="text-muted-foreground mt-2 mb-6">
            قم بإنشاء كيانك الأول لبدء إدارة مؤسستك على المنصة
          </p>
          <Link href="/entities/create">
            <Button>إنشاء كيان جديد</Button>
          </Link>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {entities.map((entity) => (
            <EntityCard key={entity.id} entity={entity} />
          ))}
        </div>
      )}
    </div>
  );
}