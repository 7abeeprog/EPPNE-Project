// app/(dashboard)/academy/admin/live-sessions/page.tsx
"use client";

import { useState, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";

// ✅ الهوكات الجديدة
import {
  useOrganizationEntities,
  useLiveSessions,
  useCreateLiveSession,
  useUpdateLiveSession,
  useDeleteLiveSession,
} from "@/hooks/academy-queries";
import { OrganizationEntity, LiveSession } from "@/types/academy";
import { handleError } from "@/lib/error-handler";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Radio,
  Plus,
  Network,
  CalendarClock,
  Link as LinkIcon,
  Video,
  Users,
  Edit2,
  Trash2,
  Loader2,
  AlertCircle,
  Check,
  X,
  Clock,
} from "lucide-react";

// ✅ تعريف الحركات
const cardVariants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 300, damping: 24 },
  },
};

export default function LiveSessionsDashboard() {
  const queryClient = useQueryClient();
  const [selectedOrgId, setSelectedOrgId] = useState<number | "">("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSession, setEditingSession] = useState<LiveSession | null>(null);
  const [sessionData, setSessionData] = useState({
    title: "",
    description: "",
    scheduled_start: "",
    scheduled_end: "",
    session_type: "ONLINE" as "ONLINE" | "OFFLINE" | "HYBRID",
    location: "",
    meeting_url: "",
    instructor_id: 1, // TODO: جلب من المستخدم الحالي
    cohort_id: undefined as number | undefined,
  });

  // ✅ 1. جلب الكيانات التنظيمية
  const {
    data: orgEntitiesData,
    isLoading: isOrgsLoading,
    error: orgsError,
  } = useOrganizationEntities(0, 100);

  const orgEntities = orgEntitiesData?.data || [];

  // ✅ 2. جلب الجلسات الحية (مع Pagination وتحديث تلقائي)
  const {
    data: sessionsData,
    isLoading: isSessionsLoading,
    error: sessionsError,
  } = useLiveSessions(
    selectedOrgId as number,
    0,
    50,
    !!selectedOrgId ? 30000 : 0 // تحديث كل 30 ثانية إذا كان هناك كيان محدد
  );

  const sessions = sessionsData?.data || [];

  // ✅ 3. محركات العمليات (Mutations)
  const createMutation = useCreateLiveSession();
  const updateMutation = useUpdateLiveSession();
  const deleteMutation = useDeleteLiveSession();

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

  // ✅ 5. دوال الحفظ
  const handleSave = useCallback(() => {
    if (!selectedOrgId || !sessionData.title.trim()) {
      toast.error("يرجى إدخال عنوان الجلسة واختيار الكيان.");
      return;
    }

    const payload = {
      ...sessionData,
      org_entity_id: Number(selectedOrgId),
      scheduled_start: new Date(sessionData.scheduled_start).toISOString(),
      scheduled_end: new Date(sessionData.scheduled_end).toISOString(),
    };

    if (editingSession) {
      updateMutation.mutate(
        { sessionId: editingSession.id, data: payload },
        {
          onSuccess: () => {
            toast.success("تم تحديث الجلسة الحية بنجاح!");
            resetForm();
          },
          onError: (error) => {
            const err = handleError(error, "تحديث الجلسة");
            toast.error(err.message);
          },
        }
      );
    } else {
      createMutation.mutate(payload, {
        onSuccess: () => {
          toast.success("تم إنشاء الجلسة الحية بنجاح!");
          resetForm();
        },
        onError: (error) => {
          const err = handleError(error, "إنشاء الجلسة");
          toast.error(err.message);
        },
      });
    }
  }, [sessionData, selectedOrgId, editingSession, createMutation, updateMutation]);

  const handleDelete = useCallback(
    (sessionId: number) => {
      if (!confirm("هل أنت متأكد من حذف هذه الجلسة الحية؟")) return;
      deleteMutation.mutate(sessionId, {
        onSuccess: () => {
          toast.success("تم حذف الجلسة الحية بنجاح!");
        },
        onError: (error) => {
          const err = handleError(error, "حذف الجلسة");
          toast.error(err.message);
        },
      });
    },
    [deleteMutation]
  );

  const resetForm = () => {
    setIsModalOpen(false);
    setEditingSession(null);
    setSessionData({
      title: "",
      description: "",
      scheduled_start: "",
      scheduled_end: "",
      session_type: "ONLINE",
      location: "",
      meeting_url: "",
      instructor_id: 1,
      cohort_id: undefined,
    });
    queryClient.invalidateQueries({
      queryKey: ["academy", "live-sessions", selectedOrgId],
    });
  };

  const openEditModal = (session: LiveSession) => {
    setEditingSession(session);
    setSessionData({
      title: session.title,
      description: session.description || "",
      scheduled_start: new Date(session.scheduled_start).toISOString().slice(0, 16),
      scheduled_end: new Date(session.scheduled_end).toISOString().slice(0, 16),
      session_type: session.session_type,
      location: session.location || "",
      meeting_url: session.meeting_url || "",
      instructor_id: session.instructor_id,
      cohort_id: session.cohort_id || undefined,
    });
    setIsModalOpen(true);
  };

  const getSessionTypeLabel = (type: string) => {
    switch (type) {
      case "ONLINE":
        return "أونلاين";
      case "OFFLINE":
        return "حضوري";
      case "HYBRID":
        return "هجين";
      default:
        return type;
    }
  };

  const getSessionTypeColor = (type: string) => {
    switch (type) {
      case "ONLINE":
        return "bg-blue-500/10 text-blue-500 border-blue-500/20";
      case "OFFLINE":
        return "bg-emerald-500/10 text-emerald-500 border-emerald-500/20";
      case "HYBRID":
        return "bg-purple-500/10 text-purple-500 border-purple-500/20";
      default:
        return "bg-primary/10 text-primary border-primary/20";
    }
  };

  return (
    <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* خلفية نيون زجاجية */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(59,130,246,0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* رأس الصفحة */}
      <div className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 w-full">
        <div className="absolute top-0 right-0 w-72 h-72 bg-blue-500/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse" />
        <div className="flex-1">
          <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-blue-500 flex items-center gap-4 drop-shadow-sm">
            <div className="p-3 bg-blue-500/10 rounded-2xl border border-blue-500/20 shadow-inner">
              <Radio className="h-10 w-10 text-blue-500" />
            </div>
            إدارة الجلسات الحية
          </h1>
          <p className="text-muted-foreground mt-4 text-lg md:text-xl font-medium max-w-2xl">
            جدولة وإدارة المحاضرات المباشرة، البث المتزامن، والجلسات التفاعلية للطلاب.
          </p>
        </div>
      </div>

      {/* فلتر الكيان التنظيمي */}
      <Card className="w-full border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
        <CardContent className="p-8 flex flex-col md:flex-row items-end gap-6">
          <div className="flex-1 w-full">
            <Label className="text-xl font-bold flex items-center gap-2 mb-4 text-foreground">
              <Network className="h-6 w-6 text-blue-500" />
              حدد الكيان التنظيمي للجلسات:
            </Label>
            {isOrgsLoading ? (
              <Skeleton className="h-16 w-full rounded-2xl bg-background/50 border border-white/5" />
            ) : (
              <select
                className="w-full h-16 px-5 text-xl bg-background/50 backdrop-blur-md border border-white/10 rounded-2xl focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 outline-none transition-all cursor-pointer shadow-inner"
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
              onClick={() => {
                setEditingSession(null);
                setSessionData({
                  title: "",
                  description: "",
                  scheduled_start: "",
                  scheduled_end: "",
                  session_type: "ONLINE",
                  location: "",
                  meeting_url: "",
                  instructor_id: 1,
                  cohort_id: undefined,
                });
                setIsModalOpen(true);
              }}
              size="lg"
              className="h-16 px-8 text-xl font-bold shadow-[0_0_20px_rgba(59,130,246,0.3)] hover:scale-105 transition-all rounded-2xl w-full md:w-auto bg-blue-600 hover:bg-blue-500"
            >
              <Plus className="ml-2 h-6 w-6" />
              جدولة جلسة جديدة
            </Button>
          )}
        </CardContent>
      </Card>

      {/* قائمة الجلسات */}
      {selectedOrgId && (
        <div className="w-full">
          {isSessionsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton
                  key={i}
                  className="h-64 rounded-[2rem] bg-card/40 border border-white/5"
                />
              ))}
            </div>
          ) : sessionsError ? (
            <div className="p-8 bg-destructive/10 rounded-[2rem] border border-destructive/20 text-center">
              <p className="text-destructive font-bold">
                {handleError(sessionsError, "جلب الجلسات الحية").message}
              </p>
              <Button
                variant="outline"
                className="mt-4"
                onClick={() => window.location.reload()}
              >
                إعادة المحاولة
              </Button>
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-20 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-blue-500/20">
              <Radio className="mx-auto h-20 w-20 text-blue-500/30 mb-4 animate-pulse" />
              <h2 className="text-2xl font-bold text-foreground">
                لا توجد جلسات حية مجدولة
              </h2>
              <p className="text-muted-foreground mt-2 text-lg">
                قم بجدولة أول جلسة مباشرة لبدء التفاعل مع الطلاب.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {sessions.map((session: LiveSession, index: number) => (
                <motion.div
                  key={session.id}
                  variants={cardVariants}
                  initial="hidden"
                  animate="show"
                  transition={{ delay: index * 0.05 }}
                >
                  <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-blue-500/50 hover:shadow-[0_0_30px_rgba(59,130,246,0.15)] transition-all group overflow-hidden relative">
                    <div className="absolute top-0 right-0 w-2 h-full bg-blue-500/50 group-hover:bg-blue-500 transition-colors" />
                    <CardContent className="p-8">
                      <div className="flex justify-between items-start mb-4">
                        <div className="flex-1">
                          <h3 className="text-2xl font-black text-foreground group-hover:text-blue-500 transition-colors pr-3">
                            {session.title}
                          </h3>
                          <div className="flex flex-wrap gap-2 mt-2">
                            <Badge
                              className={`${getSessionTypeColor(
                                session.session_type
                              )} border font-bold`}
                            >
                              {getSessionTypeLabel(session.session_type)}
                            </Badge>
                            {session.cohort_id && (
                              <Badge className="bg-purple-500/10 text-purple-500 border-purple-500/20 font-bold">
                                <Users className="h-3 w-3 ml-1" />
                                دفعة #{session.cohort_id}
                              </Badge>
                            )}
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="hover:bg-blue-500/10 text-muted-foreground hover:text-blue-500 rounded-xl h-10 w-10"
                            onClick={() => openEditModal(session)}
                          >
                            <Edit2 className="h-5 w-5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="hover:bg-destructive/10 text-muted-foreground hover:text-destructive rounded-xl h-10 w-10"
                            onClick={() => handleDelete(session.id)}
                            disabled={deleteMutation.isPending}
                          >
                            {deleteMutation.isPending &&
                            deleteMutation.variables === session.id ? (
                              <Loader2 className="h-5 w-5 animate-spin" />
                            ) : (
                              <Trash2 className="h-5 w-5" />
                            )}
                          </Button>
                        </div>
                      </div>

                      {session.description && (
                        <p className="text-muted-foreground text-sm mb-4 line-clamp-2">
                          {session.description}
                        </p>
                      )}

                      <div className="space-y-3">
                        <div className="flex items-center gap-3 text-sm bg-background/40 p-3 rounded-xl border border-white/5 shadow-inner">
                          <CalendarClock className="h-5 w-5 text-blue-500" />
                          <span className="font-bold">
                            {new Date(session.scheduled_start).toLocaleString(
                              "ar-EG"
                            )}
                            {" - "}
                            {new Date(session.scheduled_end).toLocaleTimeString(
                              "ar-EG"
                            )}
                          </span>
                        </div>
                        {session.meeting_url && (
                          <div className="flex items-center gap-3 text-sm bg-background/40 p-3 rounded-xl border border-white/5 shadow-inner">
                            <LinkIcon className="h-5 w-5 text-emerald-500" />
                            <a
                              href={session.meeting_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-bold text-emerald-500 hover:underline truncate"
                            >
                              رابط الجلسة
                            </a>
                          </div>
                        )}
                        {session.location && (
                          <div className="flex items-center gap-3 text-sm bg-background/40 p-3 rounded-xl border border-white/5 shadow-inner">
                            <Video className="h-5 w-5 text-purple-500" />
                            <span className="font-bold">{session.location}</span>
                          </div>
                        )}
                      </div>

                      <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground border-t border-border/50 pt-4">
                        <Clock className="h-4 w-4" />
                        <span>
                          آخر تحديث:{" "}
                          {new Date(session.updated_at).toLocaleString("ar-EG")}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* نافذة إنشاء/تعديل الجلسة */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-md p-4 overflow-y-auto animate-in fade-in duration-300">
          <div className="bg-card/90 backdrop-blur-3xl border border-white/10 shadow-[0_0_50px_-10px_rgba(59,130,246,0.3)] rounded-[2.5rem] p-8 md:p-10 max-w-2xl w-full my-8 animate-in zoom-in-95 duration-300">
            <h2 className="text-3xl font-black mb-8 flex items-center gap-3 border-b border-border/50 pb-6 text-foreground">
              <div className="p-2 bg-blue-500/10 rounded-xl border border-blue-500/20">
                <Radio className="h-8 w-8 text-blue-500" />
              </div>
              {editingSession ? "تعديل الجلسة الحية" : "جدولة جلسة حية جديدة"}
            </h2>

            <div className="space-y-6">
              <div>
                <Label className="font-bold text-lg">عنوان الجلسة</Label>
                <Input
                  placeholder="مثال: محاضرة أساسيات الذكاء الاصطناعي"
                  value={sessionData.title}
                  onChange={(e) =>
                    setSessionData({ ...sessionData, title: e.target.value })
                  }
                  className="h-14 rounded-xl bg-background/50 border-white/10 focus:border-blue-500 shadow-inner text-lg mt-2"
                />
              </div>

              <div>
                <Label className="font-bold text-lg">الوصف (اختياري)</Label>
                <textarea
                  rows={3}
                  className="w-full p-4 mt-2 bg-background/50 border border-white/10 rounded-xl outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 transition-all shadow-inner text-lg resize-none"
                  placeholder="وصف الجلسة والمحاور الرئيسية..."
                  value={sessionData.description}
                  onChange={(e) =>
                    setSessionData({ ...sessionData, description: e.target.value })
                  }
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <Label className="font-bold text-lg">نوع الجلسة</Label>
                  <select
                    className="w-full h-14 px-4 mt-2 bg-background/50 border border-white/10 rounded-xl outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 transition-all cursor-pointer shadow-inner text-lg"
                    value={sessionData.session_type}
                    onChange={(e) =>
                      setSessionData({
                        ...sessionData,
                        session_type: e.target.value as "ONLINE" | "OFFLINE" | "HYBRID",
                      })
                    }
                  >
                    <option value="ONLINE">أونلاين (Zoom/Meet)</option>
                    <option value="OFFLINE">حضوري (قاعة)</option>
                    <option value="HYBRID">هجين (مدمج)</option>
                  </select>
                </div>
                <div>
                  <Label className="font-bold text-lg">المدرب (ID)</Label>
                  <Input
                    type="number"
                    placeholder="معرف المدرب"
                    value={sessionData.instructor_id}
                    onChange={(e) =>
                      setSessionData({
                        ...sessionData,
                        instructor_id: Number(e.target.value),
                      })
                    }
                    className="h-14 rounded-xl bg-background/50 border-white/10 focus:border-blue-500 shadow-inner text-lg mt-2 font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <Label className="font-bold text-lg">تاريخ ووقت البدء</Label>
                  <Input
                    type="datetime-local"
                    value={sessionData.scheduled_start}
                    onChange={(e) =>
                      setSessionData({
                        ...sessionData,
                        scheduled_start: e.target.value,
                      })
                    }
                    className="h-14 rounded-xl bg-background/50 border-white/10 focus:border-blue-500 shadow-inner text-lg mt-2"
                  />
                </div>
                <div>
                  <Label className="font-bold text-lg">تاريخ ووقت الانتهاء</Label>
                  <Input
                    type="datetime-local"
                    value={sessionData.scheduled_end}
                    onChange={(e) =>
                      setSessionData({
                        ...sessionData,
                        scheduled_end: e.target.value,
                      })
                    }
                    className="h-14 rounded-xl bg-background/50 border-white/10 focus:border-blue-500 shadow-inner text-lg mt-2"
                  />
                </div>
              </div>

              <div>
                <Label className="font-bold text-lg">رابط الجلسة (للجلسات الأونلاين)</Label>
                <Input
                  placeholder="https://zoom.us/..."
                  value={sessionData.meeting_url}
                  onChange={(e) =>
                    setSessionData({ ...sessionData, meeting_url: e.target.value })
                  }
                  className="h-14 rounded-xl bg-background/50 border-white/10 focus:border-blue-500 shadow-inner text-lg mt-2"
                />
              </div>

              <div>
                <Label className="font-bold text-lg">الموقع (للجلسات الحضورية)</Label>
                <Input
                  placeholder="مثال: القاعة الكبرى - الطابق الثالث"
                  value={sessionData.location}
                  onChange={(e) =>
                    setSessionData({ ...sessionData, location: e.target.value })
                  }
                  className="h-14 rounded-xl bg-background/50 border-white/10 focus:border-blue-500 shadow-inner text-lg mt-2"
                />
              </div>

              <div>
                <Label className="font-bold text-lg">الدفعة (اختياري)</Label>
                <Input
                  type="number"
                  placeholder="معرف الدفعة"
                  value={sessionData.cohort_id || ""}
                  onChange={(e) =>
                    setSessionData({
                      ...sessionData,
                      cohort_id: e.target.value ? Number(e.target.value) : undefined,
                    })
                  }
                  className="h-14 rounded-xl bg-background/50 border-white/10 focus:border-blue-500 shadow-inner text-lg mt-2 font-mono"
                />
              </div>

              <div className="flex justify-end gap-4 mt-8 pt-6 border-t border-border/50">
                <Button
                  variant="ghost"
                  onClick={resetForm}
                  className="rounded-xl h-14 px-8 text-lg font-bold"
                >
                  إلغاء الأمر
                </Button>
                <Button
                  onClick={handleSave}
                  disabled={
                    createMutation.isPending || updateMutation.isPending
                  }
                  className="rounded-xl h-14 px-10 text-lg font-bold shadow-[0_0_20px_rgba(59,130,246,0.4)] hover:scale-105 transition-transform bg-blue-600 hover:bg-blue-500"
                >
                  {createMutation.isPending || updateMutation.isPending ? (
                    <Loader2 className="w-6 h-6 animate-spin mr-2" />
                  ) : (
                    <Check className="w-6 h-6 mr-2" />
                  )}
                  {createMutation.isPending || updateMutation.isPending
                    ? "جاري الحفظ..."
                    : editingSession
                    ? "تحديث الجلسة"
                    : "جدولة الجلسة"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}