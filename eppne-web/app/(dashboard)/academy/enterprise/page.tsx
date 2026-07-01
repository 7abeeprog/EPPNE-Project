// app/(dashboard)/academy/enterprise/page.tsx
"use client";

import { useState, useCallback, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";

// ✅ استبدال apiClient بالهوكات الجديدة
import {
  useOrganizationEntities,
  useCohorts,
  useCreateCohort,
} from "@/hooks/academy-queries";
import { OrganizationEntity, Cohort } from "@/types/academy";
import { handleError } from "@/lib/error-handler";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Building2,
  Users,
  Plus,
  ShieldCheck,
  Loader2,
  Network,
  AlertCircle,
} from "lucide-react";
import { toast } from "sonner";

export default function EnterpriseDashboard() {
  const queryClient = useQueryClient();
  const [selectedEntityId, setSelectedEntityId] = useState<number | "">("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [cohortData, setCohortData] = useState({
    name: "",
    start_date: "",
    max_capacity: 50,
  });

  // ✅ 1. جلب الكيانات التنظيمية (مع Pagination)
  const {
    data: entitiesData,
    isLoading: isEntitiesLoading,
    error: entitiesError,
  } = useOrganizationEntities(0, 100);

  const entities = entitiesData?.data || [];

  // ✅ 2. جلب الدفعات (مع Pagination و enabled)
  const {
    data: cohortsData,
    isLoading: isCohortsLoading,
    error: cohortsError,
  } = useCohorts(
    selectedEntityId as number,
    0,
    50,
    !!selectedEntityId
  );

  const cohorts = cohortsData?.data || [];

  // ✅ 3. محرك إنشاء الدفعات (Mutation)
  const createCohortMutation = useCreateCohort();

  // ✅ 4. معالجة الأخطاء
  if (entitiesError) {
    const error = handleError(entitiesError, "جلب الكيانات التنظيمية");
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
        <div className="p-6 bg-destructive/10 rounded-full mb-6 border border-destructive/20">
          <AlertCircle className="h-16 w-16 text-destructive" />
        </div>
        <h2 className="text-3xl font-bold mb-2">فشل في تحميل البيانات</h2>
        <p className="text-muted-foreground text-lg mb-8 max-w-md">{error.message}</p>
        <Button
          onClick={() => window.location.reload()}
          size="lg"
          className="rounded-xl h-14 px-8"
        >
          إعادة المحاولة
        </Button>
      </div>
    );
  }

  // ✅ 5. دالة إنشاء الدفعة (useCallback)
  const handleCreateCohort = useCallback(() => {
    if (!selectedEntityId || !cohortData.name.trim()) {
      toast.error("يرجى تحديد الكيان وإدخال اسم الدفعة أولاً.");
      return;
    }

    createCohortMutation.mutate(
      {
        org_entity_id: Number(selectedEntityId),
        name: cohortData.name.trim(),
        start_date: cohortData.start_date
          ? new Date(cohortData.start_date).toISOString()
          : undefined,
        max_capacity: Number(cohortData.max_capacity) || 50,
      },
      {
        onSuccess: () => {
          toast.success("تم تشكيل واعتماد الدفعة السيادية بنجاح! 🛡️");
          queryClient.invalidateQueries({
            queryKey: ["academy", "cohorts", selectedEntityId],
          });
          setIsModalOpen(false);
          setCohortData({ name: "", start_date: "", max_capacity: 50 });
        },
        onError: (error) => {
          const err = handleError(error, "إنشاء الدفعة");
          toast.error(err.message);
        },
      }
    );
  }, [selectedEntityId, cohortData, createCohortMutation, queryClient]);

  // ✅ 6. دالة اختيار الكيان
  const handleEntityChange = useCallback((value: string) => {
    setSelectedEntityId(value ? Number(value) : "");
  }, []);

  return (
    <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* خلفية نيون زجاجية */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(16,185,129,0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* الهيدر المؤسسي */}
      <div className="relative overflow-hidden bg-card/40 backdrop-blur-2xl border border-white/10 p-8 md:p-12 rounded-[2rem] shadow-[0_0_50px_-15px_rgba(16,185,129,0.2)] flex flex-col md:flex-row items-center gap-8 w-full">
        <div className="absolute top-0 right-0 w-72 h-72 bg-emerald-500/10 blur-[150px] rounded-full pointer-events-none -z-10 animate-pulse duration-1000" />

        <div className="p-5 bg-emerald-500/10 rounded-[2rem] border border-emerald-500/20 shadow-[0_0_20px_rgba(16,185,129,0.2)]">
          <Building2 className="w-16 h-16 text-emerald-500" />
        </div>
        <div className="flex-1 text-center md:text-right">
          <h1 className="text-4xl md:text-5xl font-black mb-4 flex items-center justify-center md:justify-start gap-3 bg-clip-text text-transparent bg-gradient-to-r from-foreground to-emerald-500 drop-shadow-sm">
            غرفة العمليات المؤسسية <ShieldCheck className="text-emerald-500 w-10 h-10 drop-shadow-md" />
          </h1>
          <p className="text-muted-foreground text-lg md:text-xl font-medium max-w-2xl">
            أدر هيكل جامعتك أو مدرستك، قم بتشكيل الدفعات (B2B)، وتابع تقدم الكيانات التابعة لك بمركزية تامة.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* قسم اختيار الكيان */}
        <Card className="col-span-1 border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] shadow-lg h-fit overflow-hidden">
          <CardContent className="p-8 space-y-6 relative">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-600 to-emerald-400" />
            <Label className="text-xl font-black flex items-center gap-2 text-foreground">
              <Network className="h-6 w-6 text-emerald-500" /> 1. حدد الكيان التابع
            </Label>

            {isEntitiesLoading ? (
              <Skeleton className="h-14 w-full rounded-xl bg-background/50 border border-white/5" />
            ) : (
              <select
                className="w-full h-14 px-4 text-lg bg-background/50 border border-white/10 rounded-xl outline-none focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 shadow-inner cursor-pointer transition-all"
                value={selectedEntityId}
                onChange={(e) => handleEntityChange(e.target.value)}
              >
                <option value="" disabled>-- قائمة الكيانات --</option>
                {entities.map((ent: OrganizationEntity) => (
                  <option key={ent.id} value={ent.id}>
                    {ent.name} ({ent.entity_type})
                  </option>
                ))}
              </select>
            )}

            {selectedEntityId && (
              <Button
                onClick={() => setIsModalOpen(true)}
                className="w-full h-14 text-lg font-black rounded-xl mt-6 bg-emerald-600 hover:bg-emerald-500 text-white shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:scale-105 transition-transform"
              >
                <Plus className="mr-2 h-6 w-6" /> تشكيل دفعة جديدة
              </Button>
            )}
          </CardContent>
        </Card>

        {/* قسم عرض الدفعات */}
        <div className="col-span-1 md:col-span-2 space-y-6 bg-card/20 backdrop-blur-md border border-white/5 p-8 rounded-[2rem] shadow-inner min-h-[400px]">
          <h2 className="text-2xl font-black mb-6 flex items-center gap-3 text-foreground border-b border-border/50 pb-4">
            <Users className="text-emerald-500 w-8 h-8" /> الدفعات المسجلة بالكيان
          </h2>

          {!selectedEntityId ? (
            <div className="text-center py-20 bg-background/30 rounded-[2rem] border border-dashed border-white/10">
              <Network className="w-16 h-16 mx-auto text-emerald-500/30 mb-4 animate-pulse" />
              <p className="text-muted-foreground text-lg font-medium">
                يرجى تحديد الكيان من القائمة الجانبية لاستعراض الدفعات.
              </p>
            </div>
          ) : isCohortsLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              {[1, 2].map((i) => (
                <Skeleton key={i} className="h-48 rounded-[2rem] bg-card/40 border border-white/5" />
              ))}
            </div>
          ) : cohortsError ? (
            <div className="p-6 bg-destructive/10 rounded-2xl border border-destructive/20 text-center">
              <p className="text-destructive font-bold">
                {handleError(cohortsError, "جلب الدفعات").message}
              </p>
              <Button
                variant="outline"
                className="mt-4"
                onClick={() => window.location.reload()}
              >
                إعادة المحاولة
              </Button>
            </div>
          ) : cohorts.length === 0 ? (
            <div className="text-center py-20 bg-background/30 rounded-[2rem] border border-dashed border-emerald-500/20">
              <Users className="w-16 h-16 mx-auto text-emerald-500/30 mb-4" />
              <p className="text-muted-foreground text-lg font-medium">
                الخزانة فارغة. لا توجد دفعات حالية في هذا الكيان.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 animate-in fade-in">
              {cohorts.map((cohort: Cohort) => (
                <Card
                  key={cohort.id}
                  className="border-white/10 bg-card/40 backdrop-blur-xl hover:border-emerald-500/50 hover:shadow-[0_0_30px_rgba(16,185,129,0.15)] transition-all rounded-[2rem] group relative overflow-hidden"
                >
                  <div className="absolute top-0 right-0 w-2 h-full bg-emerald-500/50 group-hover:bg-emerald-500 transition-colors" />
                  <CardContent className="p-6">
                    <h3 className="text-2xl font-black mb-4 group-hover:text-emerald-500 transition-colors">
                      {cohort.name}
                    </h3>
                    <div className="space-y-3 mb-6">
                      <div className="flex justify-between items-center bg-background/40 p-3 rounded-xl border border-white/5 shadow-sm">
                        <span className="text-xs font-bold text-muted-foreground">
                          تاريخ البدء
                        </span>
                        <span className="font-bold text-sm">
                          {cohort.start_date
                            ? new Date(cohort.start_date).toLocaleDateString("ar-EG")
                            : "غير محدد"}
                        </span>
                      </div>
                      <div className="flex justify-between items-center bg-background/40 p-3 rounded-xl border border-white/5 shadow-sm">
                        <span className="text-xs font-bold text-muted-foreground">
                          السعة القصوى
                        </span>
                        <span className="font-black text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                          {cohort.max_capacity || "غير محدود"} مجند
                        </span>
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      className="w-full h-12 rounded-xl border-emerald-500/30 text-emerald-500 hover:bg-emerald-500 hover:text-white transition-colors font-bold shadow-md"
                    >
                      إدارة الطلاب والجدول
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* نافذة إنشاء دفعة سيادية (Modal) */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-md p-4 animate-in fade-in duration-300">
          <div className="bg-card/90 backdrop-blur-3xl border border-white/10 shadow-[0_0_50px_-10px_rgba(16,185,129,0.3)] rounded-[2.5rem] p-8 md:p-10 max-w-md w-full animate-in zoom-in-95 duration-300">
            <h2 className="text-3xl font-black mb-8 flex items-center gap-3 border-b border-border/50 pb-6">
              <div className="p-2 bg-emerald-500/10 rounded-xl border border-emerald-500/20">
                <ShieldCheck className="h-8 w-8 text-emerald-500" />
              </div>
              تشكيل دفعة جديدة
            </h2>
            <div className="space-y-5">
              <div>
                <Label className="font-bold text-lg">الاسم الكودي للدفعة</Label>
                <Input
                  placeholder="مثال: الفرقة الأولى - أمن سيبراني"
                  value={cohortData.name}
                  onChange={(e) =>
                    setCohortData({ ...cohortData, name: e.target.value })
                  }
                  className="h-14 bg-background/50 border-white/10 mt-2 rounded-xl focus:border-emerald-500 shadow-inner text-lg"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="font-bold text-lg">تاريخ البدء</Label>
                  <Input
                    type="date"
                    value={cohortData.start_date}
                    onChange={(e) =>
                      setCohortData({ ...cohortData, start_date: e.target.value })
                    }
                    className="h-14 bg-background/50 border-white/10 mt-2 rounded-xl focus:border-emerald-500 shadow-inner text-lg"
                  />
                </div>
                <div>
                  <Label className="font-bold text-lg">السعة القصوى</Label>
                  <Input
                    type="number"
                    min="1"
                    value={cohortData.max_capacity}
                    onChange={(e) =>
                      setCohortData({
                        ...cohortData,
                        max_capacity: Number(e.target.value),
                      })
                    }
                    className="h-14 bg-background/50 border-white/10 mt-2 rounded-xl focus:border-emerald-500 shadow-inner font-mono text-lg"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-4 mt-8 pt-6 border-t border-border/50">
                <Button
                  variant="ghost"
                  onClick={() => setIsModalOpen(false)}
                  className="rounded-xl h-14 px-6 text-lg font-bold"
                >
                  إلغاء الأمر
                </Button>
                <Button
                  onClick={handleCreateCohort}
                  disabled={createCohortMutation.isPending}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl h-14 px-8 text-lg font-bold shadow-[0_0_20px_rgba(16,185,129,0.4)] hover:scale-105 transition-transform"
                >
                  {createCohortMutation.isPending ? (
                    <Loader2 className="w-6 h-6 animate-spin mr-2" />
                  ) : null}
                  {createCohortMutation.isPending
                    ? "جاري التشفير..."
                    : "اعتماد الدفعة"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}