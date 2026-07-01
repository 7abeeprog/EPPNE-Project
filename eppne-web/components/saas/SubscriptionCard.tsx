// components/saas/SubscriptionCard.tsx
"use client";

import { motion } from "framer-motion";
import { TenantSubscription } from "@/types/saas";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CalendarDays, CreditCard, Clock, CheckCircle, XCircle, AlertCircle, RefreshCw, Trash2 } from "lucide-react";

interface SubscriptionCardProps {
  subscription: TenantSubscription;
  onCancel: () => void;
  onRenew: () => void;
  index?: number;
}

const STATUS_CONFIG: Record<string, { label: string; className: string; icon: any }> = {
  ACTIVE: {
    label: "نشط",
    className: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
    icon: CheckCircle,
  },
  TRIAL: {
    label: "فترة تجريبية",
    className: "bg-blue-500/10 text-blue-500 border-blue-500/20",
    icon: Clock,
  },
  PAST_DUE: {
    label: "متأخر",
    className: "bg-amber-500/10 text-amber-500 border-amber-500/20",
    icon: AlertCircle,
  },
  EXPIRED: {
    label: "منتهي",
    className: "bg-destructive/10 text-destructive border-destructive/20",
    icon: XCircle,
  },
  CANCELLED: {
    label: "ملغي",
    className: "bg-muted/10 text-muted-foreground border-white/10",
    icon: XCircle,
  },
};

export function SubscriptionCard({ subscription, onCancel, onRenew, index = 0 }: SubscriptionCardProps) {
  const config = STATUS_CONFIG[subscription.status] || STATUS_CONFIG.ACTIVE;
  const StatusIcon = config.icon;
  const isActive = subscription.status === "ACTIVE" || subscription.status === "TRIAL";
  const isPastDue = subscription.status === "PAST_DUE";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, type: "spring", stiffness: 300, damping: 24 }}
    >
      <Card className="border-white/10 bg-card/40 backdrop-blur-md rounded-[2rem] hover:border-primary/40 hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] transition-all group">
        <CardContent className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex-1 space-y-2">
            <div className="flex flex-wrap items-center gap-3">
              <h4 className="font-black text-lg text-foreground">
                {subscription.plan?.name || "خطة غير معروفة"}
              </h4>
              <Badge className={`${config.className} border font-bold shrink-0`}>
                <StatusIcon className="h-3 w-3 ml-1" />
                {config.label}
              </Badge>
              {subscription.auto_renew && isActive && (
                <Badge variant="outline" className="border-white/10 text-xs font-bold">
                  تجديد تلقائي
                </Badge>
              )}
              {subscription.grace_period_end_date && isPastDue && (
                <Badge className="bg-amber-500/10 text-amber-500 border-amber-500/20 font-bold">
                  فترة سماح حتى {new Date(subscription.grace_period_end_date).toLocaleDateString("ar-EG")}
                </Badge>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <CalendarDays className="h-4 w-4" />
                بدأ: {new Date(subscription.start_date).toLocaleDateString("ar-EG")}
              </span>
              {subscription.end_date && (
                <span className="flex items-center gap-1">
                  <CalendarDays className="h-4 w-4" />
                  ينتهي: {new Date(subscription.end_date).toLocaleDateString("ar-EG")}
                </span>
              )}
              {subscription.next_billing_date && (
                <span className="flex items-center gap-1">
                  <CreditCard className="h-4 w-4" />
                  الفاتورة القادمة: {new Date(subscription.next_billing_date).toLocaleDateString("ar-EG")}
                </span>
              )}
              <span className="font-bold text-primary">
                {subscription.plan?.price_monthly} {subscription.plan?.currency}
              </span>
            </div>
          </div>

          <div className="flex gap-2 shrink-0">
            {isActive && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onRenew}
                  className="rounded-xl border-primary/30 text-primary hover:bg-primary hover:text-white font-bold"
                >
                  <RefreshCw className="h-4 w-4 ml-1" />
                  تجديد
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onCancel}
                  className="rounded-xl border-destructive/30 text-destructive hover:bg-destructive hover:text-white font-bold"
                >
                  <Trash2 className="h-4 w-4 ml-1" />
                  إلغاء
                </Button>
              </>
            )}
            {subscription.status === "EXPIRED" && (
              <Button
                size="sm"
                onClick={onRenew}
                className="rounded-xl bg-primary hover:bg-primary/90 font-bold"
              >
                <RefreshCw className="h-4 w-4 ml-1" />
                إعادة الاشتراك
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}