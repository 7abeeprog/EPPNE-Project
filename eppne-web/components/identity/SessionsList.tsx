// components/identity/SessionsList.tsx
"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useSessions, useRevokeAllSessions } from "@/hooks/identity/useSessions";
import { SessionCard } from "./SessionCard";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Loader2, AlertCircle, LogOut, Monitor } from "lucide-react";
import { toast } from "sonner";

export function SessionsList() {
  const [skip] = useState(0);
  const limit = 20;

  const { data: sessions, isLoading, error, refetch } = useSessions(skip, limit);
  const revokeAllMutation = useRevokeAllSessions();

  const handleRevokeAll = () => {
    if (!confirm("هل أنت متأكد من إبطال جميع الجلسات؟ سيتم تسجيل الخروج من جميع الأجهزة الأخرى.")) return;
    revokeAllMutation.mutate();
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-24 rounded-[2rem] bg-card/40 border border-white/5" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 bg-destructive/10 rounded-[2rem] border border-destructive/20 text-center">
        <AlertCircle className="mx-auto h-12 w-12 text-destructive mb-4" />
        <p className="text-destructive font-bold">فشل في تحميل الجلسات</p>
        <p className="text-muted-foreground mt-2">{error.message}</p>
        <Button variant="outline" className="mt-4" onClick={() => refetch()}>
          إعادة المحاولة
        </Button>
      </div>
    );
  }

  if (!sessions || sessions.length === 0) {
    return (
      <div className="text-center py-12 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-primary/20">
        <LogOut className="mx-auto h-12 w-12 text-primary/30 mb-4" />
        <h3 className="text-xl font-black text-foreground">لا توجد جلسات نشطة</h3>
        <p className="text-muted-foreground mt-2">جميع الأجهزة مسجلة الخروج.</p>
      </div>
    );
  }

  const activeSessions = sessions.filter(s => s.is_active);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-background/30 p-4 rounded-2xl border border-white/5">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg border border-primary/20">
            <Monitor className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="font-bold text-lg text-foreground">الجلسات النشطة</p>
            <p className="text-sm text-muted-foreground">
              {activeSessions.length} جلسة {activeSessions.length > 1 ? "نشطة" : "نشطة"}
            </p>
          </div>
        </div>
        {activeSessions.length > 1 && (
          <Button
            variant="destructive"
            size="sm"
            onClick={handleRevokeAll}
            disabled={revokeAllMutation.isPending}
            className="rounded-xl font-bold shadow-[0_0_15px_rgba(239,68,68,0.2)] hover:shadow-[0_0_25px_rgba(239,68,68,0.4)] transition-all"
          >
            {revokeAllMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin ml-1" />
            ) : (
              <LogOut className="h-4 w-4 ml-1" />
            )}
            إبطال جميع الجلسات
          </Button>
        )}
      </div>

      <div className="space-y-3">
        {sessions.map((session, index) => (
          <SessionCard key={session.id} session={session} index={index} />
        ))}
      </div>
    </div>
  );
}