// components/auth/SessionCard.tsx
"use client";

import { motion } from "framer-motion";
import type { SessionInfo } from "@/types/auth";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Monitor, Smartphone, Globe, Clock, CalendarDays, CheckCircle, XCircle } from "lucide-react";

interface SessionCardProps {
  session: SessionInfo;
  index?: number;
}

const getDeviceIcon = (userAgent?: string | null) => {
  if (!userAgent) return <Globe className="h-5 w-5" />;
  if (userAgent.includes("Mobile")) return <Smartphone className="h-5 w-5" />;
  return <Monitor className="h-5 w-5" />;
};

export function SessionCard({ session, index = 0 }: SessionCardProps) {
  const isActive = session.is_active && new Date(session.expires_at) > new Date();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, type: "spring", stiffness: 300, damping: 24 }}
    >
      <Card className="border-white/10 bg-card/40 backdrop-blur-md rounded-[2rem] hover:border-primary/40 hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] transition-all group">
        <CardContent className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-primary/10 rounded-xl border border-primary/20 group-hover:scale-110 transition-transform">
              {getDeviceIcon(session.user_agent ?? undefined)} {/* ✅ إصلاح السطر 34 */}
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h4 className="font-bold text-lg text-foreground">
                  {session.device_name ?? "جهاز غير معروف"} {/* ✅ إصلاح null */}
                </h4>
                <Badge
                  className={`${isActive
                      ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                      : "bg-muted/10 text-muted-foreground border-white/10"
                    } border font-bold`}
                >
                  {isActive ? (
                    <>
                      <CheckCircle className="h-3 w-3 ml-1" />
                      نشط
                    </>
                  ) : (
                    <>
                      <XCircle className="h-3 w-3 ml-1" />
                      منتهي
                    </>
                  )}
                </Badge>
              </div>
              <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground mt-1">
                {session.ip_address && (
                  <span className="font-mono bg-background/30 px-2 py-0.5 rounded border border-white/5">
                    {session.ip_address}
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {new Date(session.created_at).toLocaleString("ar-EG")}
                </span>
                <span className="flex items-center gap-1">
                  <CalendarDays className="h-3 w-3" />
                  ينتهي: {new Date(session.expires_at).toLocaleString("ar-EG")}
                </span>
              </div>
            </div>
          </div>
          {!isActive && (
            <span className="text-xs font-bold text-muted-foreground bg-background/30 px-3 py-1 rounded-full border border-white/5">
              تم تسجيل الخروج
            </span>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}