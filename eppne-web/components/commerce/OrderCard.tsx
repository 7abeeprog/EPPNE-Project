// components/commerce/OrderCard.tsx
"use client";

import { motion } from "framer-motion";
import { Order } from "@/types/commerce";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CalendarDays, Package, CreditCard, Truck } from "lucide-react";

interface OrderCardProps {
  order: Order;
  index?: number;
}

const STATUS_CONFIG: Record<string, { label: string; className: string; icon: any }> = {
  PENDING_PAYMENT: {
    label: "في انتظار الدفع",
    className: "bg-amber-500/10 text-amber-500 border-amber-500/20",
    icon: CreditCard,
  },
  PAID: {
    label: "مدفوع",
    className: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
    icon: CreditCard,
  },
  PROCESSING: {
    label: "قيد التجهيز",
    className: "bg-blue-500/10 text-blue-500 border-blue-500/20",
    icon: Package,
  },
  SHIPPED: {
    label: "تم الشحن",
    className: "bg-purple-500/10 text-purple-500 border-purple-500/20",
    icon: Truck,
  },
  DELIVERED: {
    label: "تم التوصيل",
    className: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
    icon: Truck,
  },
  CANCELLED: {
    label: "ملغي",
    className: "bg-destructive/10 text-destructive border-destructive/20",
    icon: CreditCard,
  },
};

export function OrderCard({ order, index = 0 }: OrderCardProps) {
  const config = STATUS_CONFIG[order.status] || STATUS_CONFIG.PENDING_PAYMENT;
  const StatusIcon = config.icon;

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
                طلب #{order.id}
              </h4>
              <Badge className={`${config.className} border font-bold shrink-0`}>
                <StatusIcon className="h-3 w-3 ml-1" />
                {config.label}
              </Badge>
            </div>

            <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <CalendarDays className="h-4 w-4" />
                {new Date(order.created_at).toLocaleString("ar-EG")}
              </span>
              <span className="font-mono bg-background/30 px-2 py-0.5 rounded border border-white/5">
                {order.settlement_type}
              </span>
              <span className="font-bold text-primary">
                {order.total_amount_mrusdt.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 8 })} MR_USDT
              </span>
            </div>

            {order.items && order.items.length > 0 && (
              <div className="text-xs text-muted-foreground mt-1">
                {order.items.length} منتج • {order.items.reduce((acc, i) => acc + i.quantity, 0)} قطعة
              </div>
            )}
          </div>

          <div className="flex gap-2 shrink-0">
            <Badge variant="outline" className="border-white/10 text-muted-foreground font-bold">
              {order.status === "PAID" ? "✅ مدفوع" : "⏳ قيد المعالجة"}
            </Badge>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}