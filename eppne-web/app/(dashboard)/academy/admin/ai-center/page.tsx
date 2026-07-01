// app/(dashboard)/academy/admin/ai-center/page.tsx
"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { AcademyService } from "@/services/academy.service";
import { OrganizationEntity, DigitalTwin, CameraAnalysis } from "@/types/academy";
import { handleError } from "@/lib/error-handler";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import {
  BrainCircuit,
  Camera,
  Activity,
  Eye,
  Smile,
  User,
  Zap,
  Network,
  BarChart3,
  Loader2,
  AlertCircle,
} from "lucide-react";

export default function AICenterDashboard() {
  const [selectedOrgId, setSelectedOrgId] = useState<number | "">("");

  // ✅ 1. جلب الكيانات التنظيمية عبر AcademyService
  const {
    data: orgEntitiesData,
    isLoading: isOrgsLoading,
    error: orgsError,
  } = useQuery({
    queryKey: ["academy", "org-entities"],
    queryFn: () => AcademyService.getOrganizationEntities(0, 100),
    staleTime: 10 * 60 * 1000,
  });

  const orgEntities = orgEntitiesData?.data || [];

  // ✅ 2. جلب التوائم الرقمية للطلاب
  const {
    data: digitalTwinsData,
    isLoading: isTwinsLoading,
    error: twinsError,
  } = useQuery({
    queryKey: ["academy", "digital-twins"],
    queryFn: () => AcademyService.getDigitalTwins(0, 50),
    staleTime: 5 * 60 * 1000,
  });

  const digitalTwins = digitalTwinsData?.data || [];

  // ✅ 3. جلب قراءات الرؤية الحاسوبية (مع تحديث تلقائي)
  const {
    data: cameraAnalyticsData,
    isLoading: isCamerasLoading,
    error: camerasError,
  } = useQuery({
    queryKey: ["academy", "camera-analytics", selectedOrgId],
    queryFn: () =>
      AcademyService.getCameraAnalytics(
        selectedOrgId as number,
        0,
        20
      ),
    enabled: !!selectedOrgId,
    refetchInterval: 10000, // تحديث كل 10 ثوانٍ
    staleTime: 0,
  });

  const cameraAnalytics = cameraAnalyticsData?.data || [];

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

  return (
    <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700 relative">
      {/* خلفية نيون زجاجية */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(var(--primary-rgb),0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* رأس الصفحة */}
      <div className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-white/10 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 w-full">
        <div className="absolute top-0 right-0 w-96 h-96 bg-primary/20 blur-[150px] rounded-full pointer-events-none -z-10 animate-pulse duration-1000" />
        <div className="flex-1">
          <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-primary flex items-center gap-4 drop-shadow-sm">
            <div className="p-3 bg-primary/10 rounded-2xl border border-primary/20 shadow-[0_0_15px_rgba(var(--primary-rgb),0.3)]">
              <BrainCircuit className="h-10 w-10 text-primary animate-pulse" />
            </div>
            مركز العقل الاصطناعي والتوأمة
          </h1>
          <p className="text-muted-foreground mt-4 text-lg md:text-xl font-medium max-w-2xl">
            مراقبة حية لسلوك الطلاب عبر مستشعرات الكاميرات وإدارة الخرائط الإدراكية للتوائم الرقمية.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 w-full">
        {/* العمود الأول: مراقبة الكاميرات والسلوك */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="w-full border-white/10 bg-card/40 backdrop-blur-3xl shadow-[0_10px_40px_rgba(0,0,0,0.1)] rounded-[2rem] overflow-hidden">
            <CardContent className="p-8">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8 border-b border-border/50 pb-6">
                <Label className="text-2xl font-black flex items-center gap-3 text-foreground">
                  <Camera className="h-7 w-7 text-primary" />
                  قراءات الرؤية الحاسوبية
                </Label>

                {isOrgsLoading ? (
                  <Skeleton className="h-12 w-64 rounded-xl bg-primary/10" />
                ) : (
                  <select
                    className="h-12 px-4 bg-background/50 backdrop-blur-md border border-white/10 rounded-xl outline-none focus:border-primary focus:ring-1 focus:ring-primary/50 text-foreground transition-all cursor-pointer shadow-inner"
                    value={selectedOrgId}
                    onChange={(e) => setSelectedOrgId(Number(e.target.value))}
                  >
                    <option value="" disabled>
                      اختر الكيان التنظيمي...
                    </option>
                    {orgEntities.map((entity: OrganizationEntity) => (
                      <option key={entity.id} value={entity.id}>
                        {entity.name}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {!selectedOrgId ? (
                <div className="text-center py-20 border border-dashed border-primary/20 rounded-[2rem] bg-card/20 backdrop-blur-sm">
                  <Eye className="mx-auto h-16 w-16 text-primary/30 mb-4 animate-pulse" />
                  <p className="text-muted-foreground text-lg">
                    حدد الكيان التنظيمي لربط مستشعرات الكاميرات
                  </p>
                </div>
              ) : isCamerasLoading ? (
                <div className="space-y-4">
                  {[1, 2].map((i) => (
                    <Skeleton
                      key={i}
                      className="h-32 w-full rounded-2xl bg-card/50 border border-white/5"
                    />
                  ))}
                </div>
              ) : camerasError ? (
                <div className="p-8 bg-destructive/10 rounded-[2rem] border border-destructive/20 text-center">
                  <p className="text-destructive font-bold">
                    {handleError(camerasError, "جلب قراءات الكاميرات").message}
                  </p>
                  <Button
                    variant="outline"
                    className="mt-4"
                    onClick={() => window.location.reload()}
                  >
                    إعادة المحاولة
                  </Button>
                </div>
              ) : cameraAnalytics.length === 0 ? (
                <div className="text-center py-20 border border-dashed border-primary/20 rounded-[2rem] bg-card/20 backdrop-blur-sm">
                  <Activity className="mx-auto h-16 w-16 text-primary/30 mb-4" />
                  <p className="text-muted-foreground text-lg">
                    لا توجد قراءات حية مسجلة لهذا الكيان حالياً.
                  </p>
                </div>
              ) : (
                <div className="space-y-6">
                  {cameraAnalytics.map((cam: CameraAnalysis) => (
                    <div
                      key={cam.id}
                      className="p-6 bg-background/40 backdrop-blur-md rounded-[1.5rem] border border-white/10 shadow-sm flex flex-col gap-5 hover:border-primary/50 hover:shadow-[0_0_20px_rgba(var(--primary-rgb),0.15)] transition-all group"
                    >
                      <div className="flex justify-between items-center border-b border-border/50 pb-4">
                        <span className="font-bold font-mono text-sm bg-primary/10 text-primary px-4 py-1.5 rounded-lg border border-primary/20">
                          DEVICE ID: {cam.camera_device_id}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="flex h-3 w-3 relative">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                            <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500" />
                          </span>
                          <span className="text-xs font-bold text-muted-foreground">
                            {new Date(cam.timestamp).toLocaleString("ar-EG")}
                          </span>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="flex flex-col items-center justify-center p-4 bg-card/50 rounded-xl border border-white/5 shadow-inner group-hover:bg-card/80 transition-colors">
                          <User className="h-8 w-8 text-emerald-500 mb-2 drop-shadow-sm" />
                          <span className="text-3xl font-black">
                            {cam.detected_faces_count}
                          </span>
                          <span className="text-sm font-medium text-muted-foreground mt-1">
                            الوجوه المكتشفة
                          </span>
                        </div>
                        <div className="flex flex-col items-center justify-center p-4 bg-card/50 rounded-xl border border-white/5 shadow-inner group-hover:bg-card/80 transition-colors">
                          <Activity className="h-8 w-8 text-rose-500 mb-2 drop-shadow-sm" />
                          <span className="text-3xl font-black">
                            {Math.round(cam.attention_score || 0)}%
                          </span>
                          <span className="text-sm font-medium text-muted-foreground mt-1">
                            مؤشر الانتباه
                          </span>
                        </div>
                        <div className="flex flex-col items-center justify-center p-4 bg-card/50 rounded-xl border border-white/5 shadow-inner group-hover:bg-card/80 transition-colors">
                          <Smile className="h-8 w-8 text-purple-500 mb-2 drop-shadow-sm" />
                          <span className="text-3xl font-black">
                            {Math.round(cam.emotions_summary?.focused || 0)}%
                          </span>
                          <span className="text-sm font-medium text-muted-foreground mt-1">
                            نسبة التركيز (AI)
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* العمود الثاني: التوائم الرقمية */}
        <div className="space-y-6">
          <Card className="w-full h-full border-white/10 bg-card/40 backdrop-blur-3xl shadow-[0_10px_40px_rgba(0,0,0,0.1)] rounded-[2rem] overflow-hidden sticky top-8">
            <CardContent className="p-8">
              <h2 className="text-2xl font-black flex items-center gap-3 mb-8 text-foreground border-b border-border/50 pb-6">
                <div className="p-2 bg-primary/10 rounded-lg border border-primary/20">
                  <Zap className="h-5 w-5 text-primary" />
                </div>
                التوائم الرقمية للطلاب
              </h2>

              {isTwinsLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <Skeleton
                      key={i}
                      className="h-20 w-full rounded-2xl bg-card/50 border border-white/5"
                    />
                  ))}
                </div>
              ) : twinsError ? (
                <div className="p-6 bg-destructive/10 rounded-2xl border border-destructive/20 text-center">
                  <p className="text-destructive font-bold text-sm">
                    {handleError(twinsError, "جلب التوائم الرقمية").message}
                  </p>
                </div>
              ) : digitalTwins.length === 0 ? (
                <div className="text-center py-20 border border-dashed border-primary/20 rounded-[2rem] bg-card/20 backdrop-blur-sm">
                  <Network className="mx-auto h-16 w-16 text-primary/30 mb-4 animate-pulse" />
                  <p className="text-muted-foreground text-lg">
                    جاري بناء الخرائط الإدراكية...
                  </p>
                </div>
              ) : (
                <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-primary/20 scrollbar-track-transparent">
                  {digitalTwins.map((twin: DigitalTwin) => (
                    <div
                      key={twin.id}
                      className="p-5 bg-background/40 backdrop-blur-md rounded-2xl border border-white/10 hover:shadow-[0_0_20px_rgba(var(--primary-rgb),0.15)] hover:border-primary/40 transition-all group"
                    >
                      <div className="flex items-center gap-4 mb-4">
                        <div className="h-12 w-12 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/20 flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform">
                          <User className="h-6 w-6 text-primary" />
                        </div>
                        <div>
                          <p className="font-black text-foreground">
                            طالب #{twin.user_id}
                          </p>
                          <p className="text-sm text-emerald-500 font-bold bg-emerald-500/10 px-2 py-0.5 rounded-md inline-block mt-1">
                            النمط: {twin.learning_style || "غير محدد"}
                          </p>
                        </div>
                      </div>
                      <div className="pt-4 border-t border-white/5 flex justify-between items-center bg-card/30 -mx-5 -mb-5 px-5 pb-5 rounded-b-2xl">
                        <span className="text-xs font-bold text-muted-foreground flex items-center gap-1.5">
                          <BarChart3 className="h-4 w-4 text-primary" />
                          الخريطة الإدراكية نشطة
                        </span>
                        <button className="text-sm font-black text-primary hover:text-primary/80 transition-colors">
                          عرض التحليل
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}