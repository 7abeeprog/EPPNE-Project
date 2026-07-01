// app/(dashboard)/academy/admin/sovereign-ops/page.tsx
"use client";

import { useState, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";

// ✅ استبدال apiClient بالهوكات الجديدة
import {
  useOrganizationEntities,
  useCourses,
  useLiveSessions,
  useIssueCertificate,
} from "@/hooks/academy-queries";
import { OrganizationEntity, Course, LiveSession, Certificate } from "@/types/academy";
import { handleError } from "@/lib/error-handler";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Radio,
  Award,
  ShieldCheck,
  CalendarClock,
  Link as LinkIcon,
  Plus,
  Hash,
  Network,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { toast } from "sonner";

export default function SovereignOpsDashboard() {
  const queryClient = useQueryClient();
  const [selectedOrgId, setSelectedOrgId] = useState<number | "">("");
  const [certData, setCertData] = useState({
    user_id: "",
    course_id: "",
    grade: "",
  });

  // ✅ 1. جلب الكيانات التنظيمية (مع Pagination)
  const {
    data: orgEntitiesData,
    isLoading: isOrgsLoading,
    error: orgsError,
  } = useOrganizationEntities(0, 100);

  const orgEntities = orgEntitiesData?.data || [];

  // ✅ 2. جلب الكورسات (مع Pagination)
  const {
    data: coursesData,
    isLoading: isCoursesLoading,
    error: coursesError,
  } = useCourses(0, 500);

  const courses = coursesData?.data || [];

  // ✅ 3. جلب الجلسات الحية (مع Pagination وتحديث تلقائي)
  const {
    data: liveSessionsData,
    isLoading: isLiveSessionsLoading,
    error: liveSessionsError,
  } = useLiveSessions(
    selectedOrgId as number,
    0,
    50,
    true // ✅ تفعيل التحديث التلقائي
  );

  const liveSessions = liveSessionsData?.data || [];

  // ✅ 4. جلب الشهادات (مع Pagination)
  const {
    data: certificatesData,
    isLoading: isCertsLoading,
    error: certsError,
  } = useQuery({
    queryKey: ["academy", "certificates", selectedOrgId],
    queryFn: () => AcademyService.getCertificates(selectedOrgId as number, 0, 20),
    enabled: !!selectedOrgId,
    staleTime: 2 * 60 * 1000,
  });

  const certificates = certificatesData?.data || [];

  // ✅ 5. محرك صك الشهادات (Mutation)
  const issueCertMutation = useIssueCertificate();

  // ✅ 6. معالجة الأخطاء
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

  // ✅ 7. دالة صك الشهادة
  const handleIssueCert = () => {
    if (!certData.user_id || !certData.course_id || !certData.grade) {
      toast.error("أكمل بيانات التتويج السيادي.");
      return;
    }

    issueCertMutation.mutate(
      {
        user_id: Number(certData.user_id),
        course_id: Number(certData.course_id),
        grade: Number(certData.grade),
      },
      {
        onSuccess: () => {
          toast.success("تم صك الشهادة السيادية وتشفيرها بنجاح! 🏆");
          queryClient.invalidateQueries({
            queryKey: ["academy", "certificates", selectedOrgId],
          });
          setCertData({ user_id: "", course_id: "", grade: "" });
        },
        onError: (error) => {
          const err = handleError(error, "صك الشهادة");
          toast.error(err.message);
        },
      }
    );
  };

  return (
    <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* خلفية نيون زجاجية */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(var(--primary-rgb),0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* رأس الصفحة */}
      <div className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-white/10 shadow-[0_0_40px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 w-full">
        <div className="absolute top-0 right-0 w-96 h-96 bg-primary/20 blur-[150px] rounded-full pointer-events-none -z-10 animate-pulse" />
        <div className="flex-1">
          <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-primary flex items-center gap-4 drop-shadow-sm">
            <div className="p-3 bg-primary/10 rounded-2xl border border-primary/20 shadow-inner">
              <ShieldCheck className="h-10 w-10 text-primary" />
            </div>
            العمليات والتتويج السيادي
          </h1>
          <p className="text-muted-foreground mt-4 text-lg md:text-xl font-medium max-w-2xl">
            إدارة البوابات الزمكانية (المحاضرات الحية)، وصك الشهادات الأكاديمية المشفرة.
          </p>
        </div>
      </div>

      {/* فلتر الكيان التنظيمي */}
      <Card className="w-full border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
        <CardContent className="p-8">
          <Label className="text-xl font-bold mb-4 flex items-center gap-2 text-foreground">
            <Network className="h-6 w-6 text-primary" />
            الكيان التنظيمي المستهدف للعمليات:
          </Label>
          {isOrgsLoading ? (
            <Skeleton className="h-16 w-full rounded-2xl bg-card/50 border border-white/5" />
          ) : (
            <select
              className="w-full h-16 px-5 text-xl bg-background/50 border border-white/10 rounded-2xl outline-none focus:border-primary focus:ring-1 focus:ring-primary/50 transition-all cursor-pointer shadow-inner"
              value={selectedOrgId}
              onChange={(e) => setSelectedOrgId(Number(e.target.value))}
            >
              <option value="" disabled>
                اختر الكيان لفتح العمليات...
              </option>
              {orgEntities.map((entity: OrganizationEntity) => (
                <option key={entity.id} value={entity.id}>
                  {entity.name}
                </option>
              ))}
            </select>
          )}
        </CardContent>
      </Card>

      {selectedOrgId && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 w-full animate-in fade-in slide-in-from-bottom-4 duration-500">
          {/* قسم البث الزمكاني (Live Sessions) */}
          <div className="space-y-6 bg-card/20 backdrop-blur-md p-6 rounded-[2rem] border border-white/5 shadow-inner">
            <div className="flex items-center justify-between border-b border-border/50 pb-4">
              <h2 className="text-2xl font-black flex items-center gap-3 text-foreground">
                <Radio className="text-rose-500 animate-pulse h-8 w-8" />
                الجدولة الزمكانية (Live)
              </h2>
              <Button
                size="sm"
                className="rounded-xl shadow-lg hover:scale-105 transition-transform bg-rose-600 hover:bg-rose-500 text-white"
              >
                <Plus className="h-4 w-4 mr-1" /> برمجة بث
              </Button>
            </div>

            {isLiveSessionsLoading ? (
              <div className="space-y-4">
                {[1, 2].map((i) => (
                  <Skeleton key={i} className="h-24 w-full rounded-2xl bg-card/50" />
                ))}
              </div>
            ) : liveSessionsError ? (
              <div className="p-6 bg-destructive/10 rounded-2xl border border-destructive/20 text-center">
                <p className="text-destructive font-bold">
                  {handleError(liveSessionsError, "جلب الجلسات الحية").message}
                </p>
              </div>
            ) : liveSessions.length === 0 ? (
              <div className="text-center py-16 border border-dashed border-rose-500/20 rounded-3xl bg-card/30 backdrop-blur-sm">
                <CalendarClock className="mx-auto h-16 w-16 text-rose-500/30 mb-4 animate-bounce" />
                <p className="text-muted-foreground text-lg">
                  لا توجد بوابات زمكانية مجدولة حالياً.
                </p>
              </div>
            ) : (
              <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-rose-500/20">
                {liveSessions.map((session: LiveSession) => (
                  <Card
                    key={session.id}
                    className="border-rose-500/20 bg-background/60 backdrop-blur-md rounded-2xl hover:border-rose-500/50 transition-colors group relative overflow-hidden"
                  >
                    <div className="absolute top-0 right-0 w-2 h-full bg-rose-500" />
                    <CardContent className="p-5 pl-6">
                      <div className="flex justify-between items-start mb-3">
                        <h3 className="font-bold text-lg group-hover:text-rose-500 transition-colors pr-3">
                          {session.title}
                        </h3>
                        <span className="bg-rose-500/10 text-rose-500 text-xs px-3 py-1 rounded-md font-black flex items-center gap-1 shadow-inner border border-rose-500/20">
                          <Radio className="h-3 w-3 animate-pulse" /> {session.session_type}
                        </span>
                      </div>
                      <div className="space-y-2 text-sm font-medium text-muted-foreground bg-card/40 p-3 rounded-xl border border-white/5">
                        <p className="flex items-center gap-2">
                          <CalendarClock className="h-4 w-4 text-primary" />
                          {new Date(session.scheduled_start).toLocaleString("ar-EG")}
                        </p>
                        {session.meeting_url && (
                          <p className="flex items-center gap-2">
                            <LinkIcon className="h-4 w-4 text-emerald-500" />
                            رابط القاعة السيادية مؤمن وجاهز
                          </p>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>

          {/* قسم التتويج وصك الشهادات */}
          <div className="space-y-6 bg-card/20 backdrop-blur-md p-6 rounded-[2rem] border border-white/5 shadow-inner">
            <h2 className="text-2xl font-black flex items-center gap-3 text-foreground border-b border-border/50 pb-4">
              <Award className="text-amber-500 h-8 w-8" />
              منصة التتويج السيادي
            </h2>

            <Card className="border-amber-500/30 bg-card/60 backdrop-blur-2xl rounded-[2rem] relative overflow-hidden shadow-[0_0_30px_rgba(245,158,11,0.1)]">
              <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-amber-600 to-amber-400" />
              <div className="absolute top-0 right-0 w-48 h-48 bg-amber-500/10 blur-[60px] rounded-full pointer-events-none" />
              <CardContent className="p-8 space-y-5 relative z-10">
                <div>
                  <Label className="font-bold text-muted-foreground">
                    رقم الهوية السيادية للطالب (User ID)
                  </Label>
                  <Input
                    type="number"
                    value={certData.user_id}
                    onChange={(e) =>
                      setCertData({ ...certData, user_id: e.target.value })
                    }
                    className="h-12 mt-2 bg-background/50 border-white/10 focus:border-amber-500 rounded-xl shadow-inner font-mono text-lg"
                    placeholder="مثال: 1042"
                  />
                </div>
                <div>
                  <Label className="font-bold text-muted-foreground">
                    المسار الأكاديمي المعتمد
                  </Label>
                  {isCoursesLoading ? (
                    <Skeleton className="h-12 w-full mt-2 rounded-xl" />
                  ) : coursesError ? (
                    <div className="p-3 bg-destructive/10 rounded-xl text-destructive text-sm mt-2">
                      {handleError(coursesError, "جلب الكورسات").message}
                    </div>
                  ) : (
                    <select
                      className="w-full h-12 px-4 mt-2 bg-background/50 border border-white/10 rounded-xl outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500/50 shadow-inner cursor-pointer"
                      value={certData.course_id}
                      onChange={(e) =>
                        setCertData({ ...certData, course_id: e.target.value })
                      }
                    >
                      <option value="" disabled>
                        -- اختر الكورس للتتويج --
                      </option>
                      {courses.map((c: Course) => (
                        <option key={c.id} value={c.id}>
                          {c.title}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
                <div>
                  <Label className="font-bold text-muted-foreground">
                    الدرجة النهائية (%)
                  </Label>
                  <Input
                    type="number"
                    value={certData.grade}
                    onChange={(e) =>
                      setCertData({ ...certData, grade: e.target.value })
                    }
                    className="h-12 mt-2 bg-background/50 border-white/10 focus:border-amber-500 rounded-xl shadow-inner font-mono text-lg"
                    placeholder="مثال: 95"
                  />
                </div>
                <Button
                  onClick={handleIssueCert}
                  disabled={issueCertMutation.isPending}
                  className="w-full h-14 mt-4 bg-amber-500 hover:bg-amber-600 text-white font-black text-lg rounded-xl shadow-[0_0_20px_rgba(245,158,11,0.4)] hover:scale-105 transition-transform"
                >
                  {issueCertMutation.isPending ? (
                    <Loader2 className="ml-2 h-6 w-6 animate-spin" />
                  ) : (
                    <ShieldCheck className="ml-2 h-6 w-6" />
                  )}
                  {issueCertMutation.isPending
                    ? "جاري التشفير والصك..."
                    : "صك الشهادة وتوثيقها"}
                </Button>
              </CardContent>
            </Card>

            {/* سجل الشهادات الصادرة مؤخراً */}
            {isCertsLoading ? (
              <div className="space-y-3 mt-6">
                <Skeleton className="h-16 w-full rounded-xl" />
              </div>
            ) : certsError ? (
              <div className="p-4 bg-destructive/10 rounded-xl text-destructive text-sm mt-4">
                {handleError(certsError, "جلب سجل الشهادات").message}
              </div>
            ) : certificates.length > 0 ? (
              <div className="space-y-3 mt-8">
                <h3 className="font-black text-sm text-muted-foreground uppercase tracking-wider mb-4 border-b border-border/50 pb-2">
                  سجل التوثيق الحديث
                </h3>
                {certificates.slice(0, 3).map((cert: Certificate, idx: number) => (
                  <div
                    key={idx}
                    className="p-4 bg-background/50 border border-white/5 rounded-xl flex items-center justify-between hover:bg-card/60 hover:border-amber-500/30 transition-colors shadow-sm group"
                  >
                    <div>
                      <p className="font-black text-sm text-foreground">
                        المجند #{cert.user_id}
                      </p>
                      <p className="text-xs text-muted-foreground font-mono flex items-center gap-1 mt-1 bg-background px-2 py-0.5 rounded border border-white/5">
                        <Hash className="h-3 w-3 text-amber-500" />
                        {cert.certificate_hash?.substring(0, 16) || "N/A"}...
                      </p>
                    </div>
                    <div className="text-left bg-amber-500/10 px-3 py-1.5 rounded-lg border border-amber-500/20">
                      <p className="font-black text-lg text-amber-500">{cert.grade}%</p>
                      <p className="text-[10px] font-bold text-amber-500/80 uppercase">
                        مُعتمدة
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}