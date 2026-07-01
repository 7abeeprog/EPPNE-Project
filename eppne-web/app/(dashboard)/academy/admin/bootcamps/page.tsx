// app/(dashboard)/academy/admin/bootcamps/page.tsx
"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AcademyService } from "@/services/academy.service";
import { OrganizationEntity, Bootcamp, Track, PaginatedResponse } from "@/types/academy";
import { handleError } from "@/lib/error-handler";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tent,
  Route,
  Plus,
  Network,
  Loader2,
  AlertCircle,
} from "lucide-react";

export default function BootcampsDashboard() {
  const queryClient = useQueryClient();
  const [selectedOrgId, setSelectedOrgId] = useState<number | "">("");
  const [isBootcampModalOpen, setIsBootcampModalOpen] = useState(false);
  const [isTrackModalOpen, setIsTrackModalOpen] = useState(false);

  const [bootcampData, setBootcampData] = useState({
    title: "",
    description: "",
    duration_days: 100,
  });
  const [trackData, setTrackData] = useState({
    title: "",
    description: "",
    bootcamp_id: "" as number | "",
  });

  // ✅ 1. جلب الكيانات التنظيمية
  const {
    data: orgEntitiesData,
    isLoading: isOrgsLoading,
    error: orgsError,
  } = useQuery({
    queryKey: ["academy", "org-entities", "bootcamps"],
    queryFn: () => AcademyService.getOrganizationEntities(0, 100),
    staleTime: 10 * 60 * 1000,
  });

  const orgEntities = orgEntitiesData?.data || [];

  // ✅ 2. جلب المعسكرات (مع Pagination)
  const {
    data: bootcampsData,
    isLoading: isBootcampsLoading,
    error: bootcampsError,
  } = useQuery({
    queryKey: ["academy", "bootcamps", selectedOrgId],
    queryFn: () =>
      AcademyService.getBootcamps(
        selectedOrgId as number,
        0,
        50
      ),
    enabled: !!selectedOrgId,
    staleTime: 2 * 60 * 1000,
  });

  const bootcamps = bootcampsData?.data || [];

  // ✅ 3. جلب المسارات (مع Pagination)
  const {
    data: tracksData,
    isLoading: isTracksLoading,
    error: tracksError,
  } = useQuery({
    queryKey: ["academy", "tracks", selectedOrgId],
    queryFn: () =>
      AcademyService.getTracks(
        selectedOrgId as number,
        undefined,
        0,
        50
      ),
    enabled: !!selectedOrgId,
    staleTime: 2 * 60 * 1000,
  });

  const tracks = tracksData?.data || [];

  // ✅ 4. محركات التأسيس (Mutations)
  const createBootcampMutation = useMutation({
    mutationFn: (data: any) => AcademyService.createBootcamp(data),
    onSuccess: () => {
      toast.success("تم تأسيس المعسكر السيادي بنجاح!");
      queryClient.invalidateQueries({
        queryKey: ["academy", "bootcamps", selectedOrgId],
      });
      setIsBootcampModalOpen(false);
      setBootcampData({ title: "", description: "", duration_days: 100 });
    },
    onError: (error) => {
      const err = handleError(error, "تأسيس المعسكر");
      toast.error(err.message);
    },
  });

  const createTrackMutation = useMutation({
    mutationFn: (data: any) => AcademyService.createTrack(data),
    onSuccess: () => {
      toast.success("تم شق المسار الأكاديمي بنجاح!");
      queryClient.invalidateQueries({
        queryKey: ["academy", "tracks", selectedOrgId],
      });
      setIsTrackModalOpen(false);
      setTrackData({ title: "", description: "", bootcamp_id: "" });
    },
    onError: (error) => {
      const err = handleError(error, "شق المسار");
      toast.error(err.message);
    },
  });

  // ✅ 5. معالجة الأخطاء
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

  // ✅ 6. دوال الحفظ
  const handleSaveBootcamp = () => {
    if (!selectedOrgId || !bootcampData.title.trim()) {
      toast.error("يرجى إكمال جميع البيانات المطلوبة.");
      return;
    }
    createBootcampMutation.mutate({
      ...bootcampData,
      org_entity_id: Number(selectedOrgId),
    });
  };

  const handleSaveTrack = () => {
    if (!selectedOrgId || !trackData.title.trim()) {
      toast.error("يرجى إكمال جميع البيانات المطلوبة.");
      return;
    }
    createTrackMutation.mutate({
      title: trackData.title,
      description: trackData.description,
      org_entity_id: Number(selectedOrgId),
      bootcamp_id: trackData.bootcamp_id ? Number(trackData.bootcamp_id) : null,
    });
  };

  return (
    <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700 relative">
      {/* خلفية نيون زجاجية */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(var(--primary-rgb),0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* رأس الصفحة */}
      <div className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_40px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 w-full">
        <div className="absolute top-0 right-0 w-72 h-72 bg-primary/20 blur-[150px] rounded-full pointer-events-none -z-10" />
        <div className="flex-1">
          <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-primary flex items-center gap-4">
            <div className="p-3 bg-primary/10 rounded-2xl border border-primary/20 shadow-inner">
              <Tent className="h-10 w-10 text-primary" />
            </div>
            إدارة المعسكرات والمسارات
          </h1>
          <p className="text-muted-foreground mt-4 text-lg md:text-xl font-medium">
            قم بتأسيس المعسكرات التدريبية وشق المسارات الأكاديمية السيادية (الحرة والمقيدة).
          </p>
        </div>
      </div>

      {/* اختيار الكيان التنظيمي */}
      <Card className="w-full border-primary/20 bg-card/60 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
        <CardContent className="p-8">
          <Label className="text-xl font-bold flex items-center gap-3 mb-6">
            <Network className="h-6 w-6 text-primary" />
            حدد الكيان التنظيمي للعمل عليه:
          </Label>
          {isOrgsLoading ? (
            <Skeleton className="h-16 w-full rounded-2xl bg-primary/5 border border-primary/10" />
          ) : (
            <select
              className="w-full h-16 px-5 text-xl bg-background/50 border border-primary/20 rounded-2xl focus:border-primary focus:ring-1 focus:ring-primary/50 outline-none transition-all cursor-pointer shadow-inner"
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
        </CardContent>
      </Card>

      {selectedOrgId && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 w-full">
          {/* قسم المعسكرات */}
          <div className="space-y-6 bg-card/20 backdrop-blur-md p-6 rounded-[2rem] border border-white/5 shadow-inner">
            <div className="flex items-center justify-between pb-4 border-b border-border/50">
              <h2 className="text-3xl font-black flex items-center gap-3">
                <Tent className="text-primary w-8 h-8" />
                المعسكرات
              </h2>
              <Button
                onClick={() => setIsBootcampModalOpen(true)}
                className="rounded-xl shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:scale-105 transition-transform h-12 px-6"
              >
                <Plus className="ml-2 h-5 w-5" />
                تأسيس معسكر
              </Button>
            </div>

            {isBootcampsLoading ? (
              <div className="space-y-4">
                {[1, 2].map((i) => (
                  <Skeleton key={i} className="h-32 w-full rounded-2xl bg-card/50" />
                ))}
              </div>
            ) : bootcampsError ? (
              <div className="p-6 bg-destructive/10 rounded-2xl border border-destructive/20 text-center">
                <p className="text-destructive font-bold">
                  {handleError(bootcampsError, "جلب المعسكرات").message}
                </p>
              </div>
            ) : bootcamps.length === 0 ? (
              <div className="text-center py-12 bg-background/40 rounded-3xl border border-dashed border-primary/20">
                <Tent className="h-12 w-12 text-primary/30 mx-auto mb-3" />
                <p className="text-muted-foreground font-medium">
                  لا توجد معسكرات في هذا الكيان.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {bootcamps.map((bc: Bootcamp) => (
                  <Card
                    key={bc.id}
                    className="border-primary/20 bg-background/60 backdrop-blur-xl rounded-2xl hover:border-primary/50 transition-colors group"
                  >
                    <CardContent className="p-6">
                      <h3 className="text-2xl font-black text-foreground group-hover:text-primary transition-colors">
                        {bc.title}
                      </h3>
                      <p className="text-muted-foreground mt-2 line-clamp-2">
                        {bc.description}
                      </p>
                      <div className="mt-4 inline-flex px-4 py-1.5 bg-primary/10 text-primary border border-primary/20 rounded-lg text-sm font-bold shadow-inner">
                        المدة: {bc.duration_days} يوم
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>

          {/* قسم المسارات */}
          <div className="space-y-6 bg-card/20 backdrop-blur-md p-6 rounded-[2rem] border border-white/5 shadow-inner">
            <div className="flex items-center justify-between pb-4 border-b border-border/50">
              <h2 className="text-3xl font-black flex items-center gap-3">
                <Route className="text-primary w-8 h-8" />
                المسارات
              </h2>
              <Button
                onClick={() => setIsTrackModalOpen(true)}
                variant="secondary"
                className="rounded-xl shadow-lg hover:scale-105 transition-transform h-12 px-6"
              >
                <Plus className="ml-2 h-5 w-5" />
                شق مسار
              </Button>
            </div>

            {isTracksLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-32 w-full rounded-2xl bg-card/50" />
                ))}
              </div>
            ) : tracksError ? (
              <div className="p-6 bg-destructive/10 rounded-2xl border border-destructive/20 text-center">
                <p className="text-destructive font-bold">
                  {handleError(tracksError, "جلب المسارات").message}
                </p>
              </div>
            ) : tracks.length === 0 ? (
              <div className="text-center py-12 bg-background/40 rounded-3xl border border-dashed border-primary/20">
                <Route className="h-12 w-12 text-primary/30 mx-auto mb-3" />
                <p className="text-muted-foreground font-medium">
                  لا توجد مسارات. قم بشق مسار حر أو اربطه بمعسكر.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {tracks.map((track: Track) => (
                  <Card
                    key={track.id}
                    className="border-primary/10 bg-background/60 backdrop-blur-xl rounded-2xl relative overflow-hidden group hover:border-primary/40 transition-colors"
                  >
                    <div
                      className={`absolute top-0 right-0 w-2 h-full transition-colors ${
                        track.bootcamp_id
                          ? "bg-primary group-hover:bg-primary/80"
                          : "bg-emerald-500 group-hover:bg-emerald-400"
                      }`}
                    />
                    <CardContent className="p-6">
                      <h3 className="text-xl font-black">{track.title}</h3>
                      <p className="text-muted-foreground mt-2 line-clamp-2">
                        {track.description}
                      </p>
                      <div className="mt-4 flex gap-2">
                        <span
                          className={`px-4 py-1.5 border rounded-lg text-xs font-bold shadow-inner ${
                            track.bootcamp_id
                              ? "bg-primary/10 text-primary border-primary/20"
                              : "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                          }`}
                        >
                          {track.bootcamp_id ? "مقيد بمعسكر" : "مسار حر (مستقل)"}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* نافذة المعسكر */}
      {isBootcampModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-md p-4 animate-in fade-in duration-300">
          <div className="bg-card/90 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-10px_rgba(var(--primary-rgb),0.3)] rounded-[2rem] p-8 max-w-md w-full animate-in zoom-in-95 duration-300">
            <h2 className="text-2xl font-black mb-6 flex items-center gap-2">
              <Tent className="text-primary w-6 h-6" />
              تأسيس معسكر جديد
            </h2>
            <div className="space-y-5">
              <div>
                <Label className="font-bold">عنوان المعسكر</Label>
                <Input
                  className="h-12 rounded-xl mt-2 bg-background/50 border-primary/20 focus:border-primary"
                  value={bootcampData.title}
                  onChange={(e) =>
                    setBootcampData({ ...bootcampData, title: e.target.value })
                  }
                  placeholder="مثال: معسكر البرمجة السيادي"
                />
              </div>
              <div>
                <Label className="font-bold">الوصف (اختياري)</Label>
                <Input
                  className="h-12 rounded-xl mt-2 bg-background/50 border-primary/20 focus:border-primary"
                  value={bootcampData.description}
                  onChange={(e) =>
                    setBootcampData({ ...bootcampData, description: e.target.value })
                  }
                  placeholder="وصف مختصر للمعسكر"
                />
              </div>
              <div>
                <Label className="font-bold">مدة المعسكر (بالأيام)</Label>
                <Input
                  type="number"
                  className="h-12 rounded-xl mt-2 bg-background/50 border-primary/20 focus:border-primary"
                  value={bootcampData.duration_days}
                  onChange={(e) =>
                    setBootcampData({
                      ...bootcampData,
                      duration_days: Number(e.target.value),
                    })
                  }
                  min={1}
                  max={365}
                />
              </div>
              <div className="flex justify-end gap-3 mt-8">
                <Button
                  variant="ghost"
                  className="rounded-xl h-12 px-6"
                  onClick={() => setIsBootcampModalOpen(false)}
                >
                  إلغاء
                </Button>
                <Button
                  onClick={handleSaveBootcamp}
                  disabled={createBootcampMutation.isPending}
                  className="rounded-xl h-12 px-8 shadow-lg"
                >
                  {createBootcampMutation.isPending ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    "اعتماد وتشفير"
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* نافذة المسار */}
      {isTrackModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-md p-4 animate-in fade-in duration-300">
          <div className="bg-card/90 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-10px_rgba(var(--primary-rgb),0.3)] rounded-[2rem] p-8 max-w-md w-full animate-in zoom-in-95 duration-300">
            <h2 className="text-2xl font-black mb-6 flex items-center gap-2">
              <Route className="text-primary w-6 h-6" />
              شق مسار جديد
            </h2>
            <div className="space-y-5">
              <div>
                <Label className="font-bold">عنوان المسار</Label>
                <Input
                  className="h-12 rounded-xl mt-2 bg-background/50 border-primary/20 focus:border-primary"
                  value={trackData.title}
                  onChange={(e) =>
                    setTrackData({ ...trackData, title: e.target.value })
                  }
                  placeholder="مثال: مسار تطوير الواجهات"
                />
              </div>
              <div>
                <Label className="font-bold">الوصف (اختياري)</Label>
                <Input
                  className="h-12 rounded-xl mt-2 bg-background/50 border-primary/20 focus:border-primary"
                  value={trackData.description}
                  onChange={(e) =>
                    setTrackData({ ...trackData, description: e.target.value })
                  }
                  placeholder="وصف مختصر للمسار"
                />
              </div>
              <div>
                <Label className="font-bold">التبعية (المرونة السيادية)</Label>
                <select
                  className="w-full h-12 px-4 mt-2 bg-background/50 border border-primary/20 rounded-xl outline-none focus:border-primary focus:ring-1 focus:ring-primary/50 cursor-pointer"
                  value={trackData.bootcamp_id}
                  onChange={(e) =>
                    setTrackData({
                      ...trackData,
                      bootcamp_id: e.target.value === "" ? "" : Number(e.target.value),
                    })
                  }
                >
                  <option value="" className="font-bold text-emerald-500">
                    مسار حر (مستقل للكيان)
                  </option>
                  {bootcamps.map((bc: Bootcamp) => (
                    <option key={bc.id} value={bc.id}>
                      داخل معسكر: {bc.title}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex justify-end gap-3 mt-8">
                <Button
                  variant="ghost"
                  className="rounded-xl h-12 px-6"
                  onClick={() => setIsTrackModalOpen(false)}
                >
                  إلغاء
                </Button>
                <Button
                  onClick={handleSaveTrack}
                  disabled={createTrackMutation.isPending}
                  className="rounded-xl h-12 px-8 shadow-lg"
                >
                  {createTrackMutation.isPending ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    "اعتماد وتشفير"
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}