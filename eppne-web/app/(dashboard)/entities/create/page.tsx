// app/(dashboard)/entities/create/page.tsx
"use client";

import { useRouter } from "next/navigation";
import { useEntityStore } from "@/store/entity-store";
import { EntityForm, EntityFormValues } from "@/components/entities/entity-form";
import { toast } from "sonner";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function CreateEntityPage() {
  const router = useRouter();
  const { createEntity, isLoading } = useEntityStore();

  const onSubmit = async (data: EntityFormValues) => {
    try {
      const newEntity = await createEntity(data);
      toast.success("تم إنشاء الكيان بنجاح");
      router.push(`/entities/${newEntity.id}`);
    } catch (error: any) {
      toast.error(error.message || "فشل إنشاء الكيان");
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/entities">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold">إنشاء كيان جديد</h1>
          <p className="text-muted-foreground">
            سجل كيانك السيادي للوصول إلى خدمات المنصة المتقدمة
          </p>
        </div>
      </div>

      <div className="bg-card rounded-lg border p-6">
        <EntityForm onSubmit={onSubmit} isLoading={isLoading} submitLabel="إنشاء الكيان" />
      </div>
    </div>
  );
}