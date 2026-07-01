// app/(dashboard)/academy/admin/certificates/page.tsx
"use client";

import { useState, useCallback, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { motion, Variants } from "framer-motion";

// ✅ الهوكات الجديدة
import {
  useOrganizationEntities,
  useCertificates,
  useRevokeCertificate,
  useReissueCertificate,
} from "@/hooks/academy-queries";
import { OrganizationEntity, Certificate } from "@/types/academy";
import { handleError } from "@/lib/error-handler";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Award,
  FileBadge,
  Network,
  Search,
  ShieldCheck,
  ShieldAlert,
  RefreshCw,
  Trash2,
  Loader2,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  User,
  Hash,
} from "lucide-react";

// ✅ تعريف الحركات باستخدام النوع الصحيح Variants
const cardVariants: Variants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 300, damping: 24 },
  },
};

export default function CertificatesDashboard() {
  const queryClient = useQueryClient();
  const [selectedOrgId, setSelectedOrgId] = useState<number | "">("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCertificate, setSelectedCertificate] = useState<Certificate | null>(
    null
  );
  const [isRevokeModalOpen, setIsRevokeModalOpen] = useState(false);
  const [revokeReason, setRevokeReason] = useState("");

  // ✅ 1. جلب الكيانات التنظيمية
  const {
    data: orgEntitiesData,
    isLoading: isOrgsLoading,
    error: orgsError,
  } = useOrganizationEntities(0, 100);

  const orgEntities = orgEntitiesData?.data || [];

  // ✅ 2. جلب الشهادات (مع Pagination)
  const {
    data: certificatesData,
    isLoading: isCertificatesLoading,
    error: certificatesError,
  } = useCertificates(selectedOrgId as number, 0, 50);

  const certificates = certificatesData?.data || [];

  // ✅ 3. محركات العمليات (Mutations)
  const revokeMutation = useRevokeCertificate();
  const reissueMutation = useReissueCertificate();

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

  // ✅ 5. تصفية الشهادات (useMemo)
  const filteredCertificates = useMemo(() => {
    if (!searchQuery.trim()) return certificates;
    return certificates.filter(
      (cert: Certificate) =>
        cert.user_id?.toString().includes(searchQuery.toLowerCase()) ||
        cert.certificate_hash?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        cert.course?.title?.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [certificates, searchQuery]);

  // ✅ 6. دوال الإجراءات
  const handleRevoke = useCallback(() => {
    if (!selectedCertificate || !revokeReason.trim()) {
      toast.error("يرجى إدخال سبب الإلغاء.");
      return;
    }

    revokeMutation.mutate(selectedCertificate.id, {
      onSuccess: () => {
        toast.success("تم إلغاء الشهادة بنجاح!");
        setIsRevokeModalOpen(false);
        setSelectedCertificate(null);
        setRevokeReason("");
        queryClient.invalidateQueries({
          queryKey: ["academy", "certificates", selectedOrgId],
        });
      },
      onError: (error) => {
        const err = handleError(error, "إلغاء الشهادة");
        toast.error(err.message);
      },
    });
  }, [selectedCertificate, revokeReason, revokeMutation, queryClient, selectedOrgId]);

  const handleReissue = useCallback(
    (certificateId: number) => {
      if (!confirm("هل أنت متأكد من إعادة إصدار هذه الشهادة؟ سيتم إنشاء نسخة جديدة."))
        return;

      reissueMutation.mutate(certificateId, {
        onSuccess: () => {
          toast.success("تم إعادة إصدار الشهادة بنجاح!");
          queryClient.invalidateQueries({
            queryKey: ["academy", "certificates", selectedOrgId],
          });
        },
        onError: (error) => {
          const err = handleError(error, "إعادة إصدار الشهادة");
          toast.error(err.message);
        },
      });
    },
    [reissueMutation, queryClient, selectedOrgId]
  );

  const getStatusBadge = (cert: Certificate) => {
    if (cert.is_revoked) {
      return (
        <Badge className="bg-destructive/10 text-destructive border-destructive/20 font-bold">
          <XCircle className="h-3 w-3 ml-1" /> ملغاة
        </Badge>
      );
    }
    return (
      <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 font-bold">
        <CheckCircle className="h-3 w-3 ml-1" /> سارية
      </Badge>
    );
  };

  return (
    <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* خلفية نيون زجاجية */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(245,158,11,0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* رأس الصفحة */}
      <div className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 w-full">
        <div className="absolute top-0 right-0 w-72 h-72 bg-amber-500/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse" />
        <div className="flex-1">
          <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-amber-500 flex items-center gap-4 drop-shadow-sm">
            <div className="p-3 bg-amber-500/10 rounded-2xl border border-amber-500/20 shadow-inner">
              <FileBadge className="h-10 w-10 text-amber-500" />
            </div>
            إدارة الشهادات السيادية
          </h1>
          <p className="text-muted-foreground mt-4 text-lg md:text-xl font-medium max-w-2xl">
            إدارة الشهادات الصادرة، إعادة الإصدار، الإلغاء، وتتبع الحالة.
          </p>
        </div>
      </div>

      {/* فلتر الكيان التنظيمي والبحث */}
      <Card className="w-full border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
        <CardContent className="p-8 space-y-6">
          <div className="flex flex-col md:flex-row items-end gap-6">
            <div className="flex-1 w-full">
              <Label className="text-xl font-bold flex items-center gap-2 mb-4 text-foreground">
                <Network className="h-6 w-6 text-amber-500" />
                حدد الكيان التنظيمي للشهادات:
              </Label>
              {isOrgsLoading ? (
                <Skeleton className="h-16 w-full rounded-2xl bg-background/50 border border-white/5" />
              ) : (
                <select
                  className="w-full h-16 px-5 text-xl bg-background/50 backdrop-blur-md border border-white/10 rounded-2xl focus:border-amber-500 focus:ring-1 focus:ring-amber-500/50 outline-none transition-all cursor-pointer shadow-inner"
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
          </div>

          {/* شريط البحث */}
          {selectedOrgId && (
            <div className="relative w-full">
              <Search className="absolute right-4 top-1/2 -translate-y-1/2 text-amber-500/50 h-5 w-5" />
              <Input
                placeholder="ابحث برقم الطالب، رمز الشهادة، أو اسم الكورس..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full h-14 pr-12 text-lg rounded-xl bg-background/50 border-white/10 focus:border-amber-500 focus:ring-1 focus:ring-amber-500/50 transition-all shadow-inner"
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* قائمة الشهادات */}
      {selectedOrgId && (
        <div className="w-full">
          {isCertificatesLoading ? (
            <div className="grid grid-cols-1 gap-6">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton
                  key={i}
                  className="h-40 rounded-[2rem] bg-card/40 border border-white/5"
                />
              ))}
            </div>
          ) : certificatesError ? (
            <div className="p-8 bg-destructive/10 rounded-[2rem] border border-destructive/20 text-center">
              <p className="text-destructive font-bold">
                {handleError(certificatesError, "جلب الشهادات").message}
              </p>
              <Button
                variant="outline"
                className="mt-4"
                onClick={() => window.location.reload()}
              >
                إعادة المحاولة
              </Button>
            </div>
          ) : filteredCertificates.length === 0 ? (
            <div className="text-center py-20 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-amber-500/20">
              <FileBadge className="mx-auto h-20 w-20 text-amber-500/30 mb-4 animate-pulse" />
              <h2 className="text-2xl font-bold text-foreground">
                {searchQuery ? "لا توجد شهادات تطابق البحث" : "لا توجد شهادات صادرة"}
              </h2>
              <p className="text-muted-foreground mt-2 text-lg">
                {searchQuery
                  ? "جرب كلمات بحث مختلفة."
                  : "سيتم إصدار الشهادات تلقائياً عند إكمال الطلاب للكورسات."}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredCertificates.map((cert: Certificate, index: number) => (
                <motion.div
                  key={cert.id}
                  variants={cardVariants}
                  initial="hidden"
                  animate="show"
                  transition={{ delay: index * 0.03 }}
                >
                  <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-amber-500/50 hover:shadow-[0_0_30px_rgba(245,158,11,0.15)] transition-all group overflow-hidden">
                    <CardContent className="p-6 md:p-8">
                      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                        <div className="flex-1 space-y-3">
                          <div className="flex flex-wrap items-center gap-3">
                            <h3 className="text-2xl font-black text-foreground group-hover:text-amber-500 transition-colors">
                              {cert.course?.title || `كورس #${cert.course_id}`}
                            </h3>
                            {getStatusBadge(cert)}
                          </div>

                          <div className="flex flex-wrap items-center gap-4 text-sm">
                            <div className="flex items-center gap-2 bg-background/40 px-4 py-2 rounded-xl border border-white/5 shadow-inner">
                              <User className="h-4 w-4 text-muted-foreground" />
                              <span className="font-bold">
                                الطالب #{cert.user_id}
                              </span>
                            </div>
                            <div className="flex items-center gap-2 bg-background/40 px-4 py-2 rounded-xl border border-white/5 shadow-inner">
                              <Award className="h-4 w-4 text-amber-500" />
                              <span className="font-bold text-amber-500">
                                {cert.grade}%
                              </span>
                            </div>
                            <div className="flex items-center gap-2 bg-background/40 px-4 py-2 rounded-xl border border-white/5 shadow-inner">
                              <Hash className="h-4 w-4 text-muted-foreground" />
                              <span className="font-mono text-xs font-bold truncate max-w-[200px]">
                                {cert.certificate_hash?.substring(0, 16)}...
                              </span>
                            </div>
                            <div className="flex items-center gap-2 bg-background/40 px-4 py-2 rounded-xl border border-white/5 shadow-inner">
                              <Clock className="h-4 w-4 text-muted-foreground" />
                              <span className="font-bold">
                                {new Date(cert.issued_at).toLocaleDateString("ar-EG")}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="flex gap-2 shrink-0">
                          <Button
                            variant="outline"
                            size="sm"
                            className="rounded-xl border-amber-500/30 text-amber-500 hover:bg-amber-500 hover:text-white transition-colors font-bold"
                            onClick={() => handleReissue(cert.id)}
                            disabled={reissueMutation.isPending}
                          >
                            {reissueMutation.isPending &&
                            reissueMutation.variables === cert.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <RefreshCw className="h-4 w-4 ml-1" />
                            )}
                            إعادة إصدار
                          </Button>
                          {!cert.is_revoked && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="rounded-xl border-destructive/30 text-destructive hover:bg-destructive hover:text-white transition-colors font-bold"
                              onClick={() => {
                                setSelectedCertificate(cert);
                                setRevokeReason("");
                                setIsRevokeModalOpen(true);
                              }}
                            >
                              <Trash2 className="h-4 w-4 ml-1" />
                              إلغاء
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* نافذة إلغاء الشهادة */}
      {isRevokeModalOpen && selectedCertificate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-md p-4 animate-in fade-in duration-300">
          <div className="bg-card/90 backdrop-blur-3xl border border-white/10 shadow-[0_0_50px_-10px_rgba(239,68,68,0.3)] rounded-[2.5rem] p-8 md:p-10 max-w-lg w-full animate-in zoom-in-95 duration-300">
            <h2 className="text-3xl font-black mb-4 flex items-center gap-3 border-b border-border/50 pb-6 text-foreground">
              <div className="p-2 bg-destructive/10 rounded-xl border border-destructive/20">
                <ShieldAlert className="h-8 w-8 text-destructive" />
              </div>
              إلغاء الشهادة
            </h2>

            <div className="space-y-6">
              <div className="p-4 bg-destructive/5 rounded-xl border border-destructive/20">
                <p className="font-bold">الشهادة: {selectedCertificate.course?.title}</p>
                <p className="text-sm text-muted-foreground">
                  الطالب #{selectedCertificate.user_id} • {selectedCertificate.grade}%
                </p>
              </div>

              <div>
                <Label className="font-bold text-lg">سبب الإلغاء</Label>
                <textarea
                  rows={3}
                  className="w-full p-4 mt-2 bg-background/50 border border-white/10 rounded-xl outline-none focus:border-destructive focus:ring-1 focus:ring-destructive/50 transition-all shadow-inner text-lg resize-none"
                  placeholder="أدخل سبب إلغاء الشهادة..."
                  value={revokeReason}
                  onChange={(e) => setRevokeReason(e.target.value)}
                />
              </div>

              <div className="flex justify-end gap-4 mt-8 pt-6 border-t border-border/50">
                <Button
                  variant="ghost"
                  onClick={() => {
                    setIsRevokeModalOpen(false);
                    setSelectedCertificate(null);
                    setRevokeReason("");
                  }}
                  className="rounded-xl h-14 px-8 text-lg font-bold"
                >
                  إلغاء الأمر
                </Button>
                <Button
                  onClick={handleRevoke}
                  disabled={revokeMutation.isPending || !revokeReason.trim()}
                  className="rounded-xl h-14 px-10 text-lg font-bold shadow-[0_0_20px_rgba(239,68,68,0.4)] hover:scale-105 transition-transform bg-destructive hover:bg-destructive/90"
                >
                  {revokeMutation.isPending ? (
                    <Loader2 className="w-6 h-6 animate-spin mr-2" />
                  ) : (
                    <ShieldAlert className="w-6 h-6 mr-2" />
                  )}
                  {revokeMutation.isPending ? "جاري الإلغاء..." : "اعتماد الإلغاء"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}