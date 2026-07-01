// app/(dashboard)/academy/admin/cohorts/page.tsx
"use client";

import { useState, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

// ✅ استبدال enterprise-store بالهوكات الجديدة
import {
  useOrganizationEntities,
  useCohorts,
  useCreateCohort,
} from "@/hooks/academy-queries";
import { OrganizationEntity, Cohort } from "@/types/academy";
import { handleError } from "@/lib/error-handler";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Users,
  CalendarDays,
  Shield,
  Plus,
  Network,
  Clock,
  Loader2,
  AlertCircle,
} from "lucide-react";

export default function CohortsDashboard() {
  const queryClient = useQueryClient();
  const [selectedOrgId, setSelectedOrgId] = useState<number | "">("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [cohortData, setCohortData] = useState({
    name: "",
    start_date: "",
    end_date: "",
    max_capacity: "",
  });

  // ✅ 1. جلب الكيانات التنظيمية (مع Pagination)
  const {
    data: orgEntitiesData,
    isLoading: isOrgsLoading,
    error: orgsError,
  } = useOrganizationEntities(0, 100);

  const orgEntities = orgEntitiesData?.data || [];

  // ✅ 2. جلب الدفعات (مع Pagination)
  const {
    data: cohortsData,
    isLoading: isCohortsLoading,
    error: cohortsError,
  } = useCohorts(selectedOrgId as number, 0, 50);

  const cohorts = cohortsData?.data || [];

  // ✅ 3. محرك تأسيس الدفعة
  const createCohortMutation = useCreateCohort();

  // ✅ 4. معالجة الأخطاء
  if (orgsError) {
    const error = handleError(orgsError, "جلب الكيانات التنظيمية");
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

  // ✅ 5. دالة حفظ الدفعة
  const handleSaveCohort = () => {
    if (!selectedOrgId || !cohortData.name.trim()) {
      toast.error("يرجى إدخال اسم الدفعة واختيار الكيان.");
      return;
    }

    createCohortMutation.mutate(
      {
        name: cohortData.name.trim(),
        org_entity_id: Number(selectedOrgId),
        start_date: cohortData.start_date
          ? new Date(cohortData.start_date).toISOString()
          : undefined,
        end_date: cohortData.end_date
          ? new Date(cohortData.end_date).toISOString()
          : undefined,
        max_capacity: cohortData.max_capacity
          ? Number(cohortData.max_capacity)
          : undefined,
      },
      {
        onSuccess: () => {
          toast.success("تم تأسيس الدفعة السيادية بنجاح!");
          // إبطال Cache الخاص بالدفعات
          queryClient.invalidateQueries({
            queryKey: ["academy", "cohorts", selectedOrgId],
          });
          setIsModalOpen(false);
          setCohortData({
            name: "",
            start_date: "",
            end_date: "",
            max_capacity: "",
          });
        },
        onError: (error) => {
          const err = handleError(error, "تأسيس الدفعة");
          toast.error(err.message);
        },
      }
    );
  };

  return (
    <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* خلفية نيون زجاجية */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_right,_rgba(var(--primary-rgb),0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* رأس الصفحة */}
      <div className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 w-full group">
        <div className="absolute top-0 right-0 w-72 h-72 bg-primary/20 blur-[150px] rounded-full pointer-events-none -z-10 group-hover:scale-110 transition-transform duration-1000" />
        <div className="flex-1">
          <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-primary flex items-center gap-4 drop-shadow-sm">
            <div className="p-3 bg-primary/10 rounded-2xl border border-primary/20 shadow-inner">
              <CalendarDays className="h-10 w-10 text-primary" />
            </div>
            غرفة تحكم الزمكان (الدفعات)
          </h1>
          <p className="text-muted-foreground mt-4 text-lg md:text-xl font-medium max-w-2xl">
            سيطر على تدفق الطلاب، حدد سعة الدفعات، ونظم التواريخ الأكاديمية بدقة صارمة.
          </p>
        </div>
      </div>

      {/* فلتر الكيان التنظيمي */}
      <Card className="w-full border-primary/20 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
        <CardContent className="p-8 flex flex-col md:flex-row items-end gap-6">
          <div className="flex-1 w-full">
            <Label className="text-xl font-bold flex items-center gap-2 mb-4 text-foreground">
              <Network className="h-6 w-6 text-primary" />
              حدد الكيان التنظيمي المستضيف للدفعات:
            </Label>
            {isOrgsLoading ? (
              <Skeleton className="h-16 w-full rounded-2xl bg-card/50 border border-primary/10" />
            ) : (
              <select
                className="w-full h-16 px-5 text-xl bg-background/50 backdrop-blur-md border border-primary/20 rounded-2xl focus:border-primary focus:ring-1 focus:ring-primary/50 outline-none transition-all cursor-pointer shadow-inner"
                value={selectedOrgId}
                onChange={(e) => setSelectedOrgId(Number(e.target.value))}
              >
                <option value="" disabled>
                  اختر الكلية أو القسم...
                </option>
                {orgEntities.map((entity: OrganizationEntity) => (
                  <option key={entity.id} value={entity.id}>
                    {entity.name} ({entity.entity_type})
                  </option>
                ))}
              </select>
            )}
          </div>
          {selectedOrgId && (
            <Button
              onClick={() => setIsModalOpen(true)}
              size="lg"
              className="h-16 px-8 text-xl font-bold shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:scale-105 transition-all rounded-2xl w-full md:w-auto"
            >
              <Plus className="ml-2 h-6 w-6" />
              تأسيس دفعة جديدة
            </Button>
          )}
        </CardContent>
      </Card>

      {/* شبكة عرض الدفعات */}
      {selectedOrgId && (
        <div className="w-full animate-in fade-in slide-in-from-bottom-4 duration-500">
          {isCohortsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3].map((i) => (
                <Skeleton
                  key={i}
                  className="h-64 rounded-[2rem] bg-card/40 border border-white/5"
                />
              ))}
            </div>
          ) : cohortsError ? (
            <div className="p-8 bg-destructive/10 rounded-[2rem] border border-destructive/20 text-center">
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
            <div className="text-center py-20 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-primary/30">
              <Users className="mx-auto h-20 w-20 text-primary/20 mb-4 animate-pulse" />
              <h2 className="text-2xl font-bold text-foreground">لا توجد دفعات حالياً</h2>
              <p className="text-muted-foreground mt-2 text-lg">
                قم بتأسيس أول دفعة لبدء استقبال تسجيلات الطلاب.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {cohorts.map((cohort: Cohort) => (
                <Card
                  key={cohort.id}
                  className="border-white/10 bg-card/40 backdrop-blur-md rounded-[2rem] hover:border-primary/50 hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] transition-all group overflow-hidden relative"
                >
                  <div className="absolute top-0 right-0 w-2 h-full bg-primary/50 group-hover:bg-primary transition-colors" />
                  <CardContent className="p-8">
                    <div className="flex justify-between items-start mb-6 border-b border-border/50 pb-4">
                      <h3 className="text-2xl font-black text-foreground group-hover:text-primary transition-colors pr-3">
                        {cohort.name}
                      </h3>
                      <div className="p-2 bg-primary/10 rounded-lg border border-primary/20">
                        <Shield className="h-5 w-5 text-primary" />
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div className="flex justify-between items-center bg-background/40 p-4 rounded-xl border border-white/5 shadow-sm group-hover:bg-background/60 transition-colors">
                        <span className="text-sm font-bold flex items-center gap-2 text-muted-foreground">
                          <Users className="h-4 w-4 text-primary" />
                          السعة القصوى:
                        </span>
                        <span className="font-black text-lg text-foreground bg-primary/10 px-3 py-1 rounded-md border border-primary/20">
                          {cohort.max_capacity || "غير محدود"}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div className="flex flex-col bg-background/40 p-4 rounded-xl border border-white/5 shadow-sm">
                          <span className="text-xs font-bold flex items-center gap-1.5 text-muted-foreground mb-1">
                            <Clock className="h-3.5 w-3.5 text-emerald-500" />
                            البدء:
                          </span>
                          <span className="text-sm font-black text-foreground">
                            {cohort.start_date
                              ? new Date(cohort.start_date).toLocaleDateString(
                                  "ar-EG"
                                )
                              : "غير محدد"}
                          </span>
                        </div>
                        <div className="flex flex-col bg-background/40 p-4 rounded-xl border border-white/5 shadow-sm">
                          <span className="text-xs font-bold flex items-center gap-1.5 text-muted-foreground mb-1">
                            <CalendarDays className="h-3.5 w-3.5 text-rose-500" />
                            الانتهاء:
                          </span>
                          <span className="text-sm font-black text-foreground">
                            {cohort.end_date
                              ? new Date(cohort.end_date).toLocaleDateString(
                                  "ar-EG"
                                )
                              : "غير محدد"}
                          </span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* نافذة تأسيس الدفعة (Modal) */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-md p-4 animate-in fade-in duration-300">
          <div className="bg-card/90 backdrop-blur-3xl border border-primary/20 shadow-[0_0_50px_-10px_rgba(var(--primary-rgb),0.3)] rounded-[2rem] p-8 max-w-lg w-full animate-in zoom-in-95 duration-300">
            <h2 className="text-2xl font-black mb-6 flex items-center gap-3 border-b border-border/50 pb-4">
              <div className="p-2 bg-primary/10 rounded-xl">
                <Shield className="h-6 w-6 text-primary" />
              </div>
              تأسيس دفعة أكاديمية
            </h2>
            <div className="space-y-5">
              <div>
                <Label className="font-bold">الاسم الكودي للدفعة</Label>
                <Input
                  placeholder="مثال: دفعة رواد الذكاء الاصطناعي 2026"
                  className="h-12 rounded-xl mt-2 bg-background/50 border-primary/20 focus:border-primary"
                  value={cohortData.name}
                  onChange={(e) =>
                    setCohortData({ ...cohortData, name: e.target.value })
                  }
                />
              </div>
              <div>
                <Label className="font-bold">السعة القصوى (عدد المجندين/الطلاب)</Label>
                <Input
                  type="number"
                  min="1"
                  placeholder="اتركه فارغاً لعدد غير محدود"
                  className="h-12 rounded-xl mt-2 bg-background/50 border-primary/20 focus:border-primary font-mono text-lg"
                  value={cohortData.max_capacity}
                  onChange={(e) =>
                    setCohortData({
                      ...cohortData,
                      max_capacity: e.target.value,
                    })
                  }
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="font-bold">تاريخ البدء</Label>
                  <Input
                    type="date"
                    className="h-12 rounded-xl mt-2 bg-background/50 border-primary/20 focus:border-primary"
                    value={cohortData.start_date}
                    onChange={(e) =>
                      setCohortData({
                        ...cohortData,
                        start_date: e.target.value,
                      })
                    }
                  />
                </div>
                <div>
                  <Label className="font-bold">تاريخ الانتهاء</Label>
                  <Input
                    type="date"
                    className="h-12 rounded-xl mt-2 bg-background/50 border-primary/20 focus:border-primary"
                    value={cohortData.end_date}
                    onChange={(e) =>
                      setCohortData({
                        ...cohortData,
                        end_date: e.target.value,
                      })
                    }
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-8 pt-4 border-t border-border/50">
                <Button
                  variant="ghost"
                  onClick={() => setIsModalOpen(false)}
                  className="rounded-xl h-12 px-6"
                >
                  إلغاء
                </Button>
                <Button
                  onClick={handleSaveCohort}
                  disabled={createCohortMutation.isPending}
                  className="rounded-xl h-12 px-8 shadow-lg font-bold"
                >
                  {createCohortMutation.isPending ? (
                    <Loader2 className="w-5 h-5 animate-spin mr-2" />
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