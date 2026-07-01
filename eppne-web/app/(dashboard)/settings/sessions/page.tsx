// app/(dashboard)/settings/sessions/page.tsx
"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useActiveSessions, useRevokeAllSessions } from "@/hooks/auth/useAuth";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Monitor,
  Smartphone,
  Tablet,
  Laptop,
  Clock,
  Shield,
  Loader2,
  AlertCircle,
  Trash2,
  LogOut,
} from "lucide-react";
import { toast } from "sonner";

// ✅ تعريف الحركات
const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  show: {
    opacity: 1,
    y: 0,
    transition: { type: "spring", stiffness: 300, damping: 24 },
  },
};

const getDeviceIcon = (userAgent?: string) => {
  if (!userAgent) return <Monitor className="h-5 w-5" />;
  const ua = userAgent.toLowerCase();
  if (ua.includes("mobile") || ua.includes("android") || ua.includes("iphone")) {
    return <Smartphone className="h-5 w-5" />;
  }
  if (ua.includes("tablet") || ua.includes("ipad")) {
    return <Tablet className="h-5 w-5" />;
  }
  if (ua.includes("mac") || ua.includes("windows") || ua.includes("linux")) {
    return <Laptop className="h-5 w-5" />;
  }
  return <Monitor className="h-5 w-5" />;
};

export default function SessionsPage() {
  const [skip] = useState(0);
  const limit = 20;
  const { data: sessions, isLoading, error, refetch } = useActiveSessions(skip, limit);
  const revokeAllMutation = useRevokeAllSessions();

  const handleRevokeAll = () => {
    if (!confirm("هل أنت متأكد من إبطال جميع الجلسات النشطة؟ سيتم تسجيل الخروج من جميع الأجهزة.")) return;
    revokeAllMutation.mutate();
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-24 rounded-[2rem] bg-card/40 border border-white/5" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 bg-destructive/10 rounded-[2rem] border border-destructive/20 text-center">
        <AlertCircle className="mx-auto h-12 w-12 text-destructive mb-4" />
        <p className="text-destructive font-bold">فشل في تحميل الجلسات النشطة</p>
        <p className="text-muted-foreground mt-2">{error.message}</p>
        <Button variant="outline" className="mt-4" onClick={() => refetch()}>
          إعادة المحاولة
        </Button>
      </div>
    );
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      {/* ✅ رأس الصفحة مع زر الإبطال */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-black text-foreground">الجلسات النشطة</h2>
          <p className="text-sm text-muted-foreground">
            {sessions?.length || 0} جلسة {sessions?.length !== 1 ? "نشطة" : "نشطة"}
          </p>
        </div>
        <Button
          onClick={handleRevokeAll}
          disabled={revokeAllMutation.isPending || !sessions || sessions.length === 0}
          variant="destructive"
          className="rounded-xl h-12 px-6 font-bold shadow-[0_0_20px_rgba(239,68,68,0.2)] hover:shadow-[0_0_30px_rgba(239,68,68,0.4)] transition-all"
        >
          {revokeAllMutation.isPending ? (
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
          ) : (
            <LogOut className="mr-2 h-5 w-5" />
          )}
          إبطال جميع الجلسات
        </Button>
      </div>

      {/* ✅ قائمة الجلسات */}
      {!sessions || sessions.length === 0 ? (
        <div className="text-center py-20 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-primary/20">
          <Shield className="mx-auto h-16 w-16 text-primary/30 mb-4 animate-pulse" />
          <h3 className="text-2xl font-black text-foreground">لا توجد جلسات نشطة</h3>
          <p className="text-muted-foreground mt-2 text-lg">
            أنت متصل فقط من هذا الجهاز حالياً.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {sessions.map((session, index) => (
            <motion.div
              key={session.id}
              variants={cardVariants}
              transition={{ delay: index * 0.03 }}
            >
              <Card className="border-white/10 bg-card/40 backdrop-blur-md rounded-[2rem] hover:border-primary/40 hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] transition-all group">
                <CardContent className="p-6 md:p-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-primary/10 rounded-xl border border-primary/20 group-hover:scale-110 transition-transform">
                      {getDeviceIcon(session.user_agent)}
                    </div>
                    <div>
                      <h4 className="font-bold text-lg text-foreground">
                        {session.device_name || "جهاز غير معروف"}
                      </h4>
                      <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                        <span>{session.ip_address || "IP غير معروف"}</span>
                        <span>•</span>
                        <span className="truncate max-w-[200px]">{session.user_agent || "متصفح غير معروف"}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="flex items-center gap-2">
                        <Clock className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm font-bold text-muted-foreground">
                          ينتهي في {new Date(session.expires_at).toLocaleDateString("ar-EG")}
                        </span>
                      </div>
                      <Badge
                        className={`mt-1 ${
                          session.is_active
                            ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                            : "bg-destructive/10 text-destructive border-destructive/20"
                        } border font-bold`}
                      >
                        {session.is_active ? "🟢 نشطة" : "🔴 منتهية"}
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  );
}