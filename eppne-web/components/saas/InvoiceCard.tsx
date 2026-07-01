// components/saas/InvoiceCard.tsx
"use client";

import { motion } from "framer-motion";
import { Invoice } from "@/types/saas";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CalendarDays, CreditCard, Eye, CheckCircle, XCircle, AlertCircle, Clock, Download } from "lucide-react";

interface InvoiceCardProps {
  invoice: Invoice;
  onView: () => void;
  onPay: () => void;
  onCancel: () => void;
  index?: number;
}

const STATUS_CONFIG: Record<string, { label: string; className: string; icon: any }> = {
  PENDING: {
    label: "معلقة",
    className: "bg-amber-500/10 text-amber-500 border-amber-500/20",
    icon: Clock,
  },
  PAID: {
    label: "مدفوعة",
    className: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
    icon: CheckCircle,
  },
  FAILED: {
    label: "فاشلة",
    className: "bg-destructive/10 text-destructive border-destructive/20",
    icon: XCircle,
  },
  CANCELLED: {
    label: "ملغاة",
    className: "bg-muted/10 text-muted-foreground border-white/10",
    icon: XCircle,
  },
};

export function InvoiceCard({ invoice, onView, onPay, onCancel, index = 0 }: InvoiceCardProps) {
  const config = STATUS_CONFIG[invoice.status] || STATUS_CONFIG.PENDING;
  const StatusIcon = config.icon;
  const isPending = invoice.status === "PENDING";
  const isPaid = invoice.status === "PAID";

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
                {invoice.invoice_number}
              </h4>
              <Badge className={`${config.className} border font-bold shrink-0`}>
                <StatusIcon className="h-3 w-3 ml-1" />
                {config.label}
              </Badge>
            </div>

            <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <CalendarDays className="h-4 w-4" />
                تاريخ الإنشاء: {new Date(invoice.created_at).toLocaleDateString("ar-EG")}
              </span>
              {invoice.due_date && (
                <span className="flex items-center gap-1">
                  <CalendarDays className="h-4 w-4" />
                  يستحق: {new Date(invoice.due_date).toLocaleDateString("ar-EG")}
                </span>
              )}
              {invoice.paid_at && (
                <span className="flex items-center gap-1 text-emerald-500">
                  <CheckCircle className="h-4 w-4" />
                  دُفع: {new Date(invoice.paid_at).toLocaleDateString("ar-EG")}
                </span>
              )}
              <span className="font-bold text-amber-500">
                {invoice.amount.toLocaleString()} {invoice.currency}
              </span>
            </div>

            {invoice.items && invoice.items.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-1">
                {invoice.items.slice(0, 3).map((item, idx) => (
                  <Badge key={idx} variant="outline" className="border-white/10 text-xs">
                    {item.service} – {item.period} ({item.amount} {item.currency})
                  </Badge>
                ))}
                {invoice.items.length > 3 && (
                  <Badge variant="outline" className="border-white/10 text-xs">
                    +{invoice.items.length - 3} أخرى
                  </Badge>
                )}
              </div>
            )}
          </div>

          <div className="flex gap-2 shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={onView}
              className="rounded-xl border-white/10 hover:bg-primary/10 font-bold"
            >
              <Eye className="h-4 w-4 ml-1" />
              تفاصيل
            </Button>
            {isPending && (
              <>
                <Button
                  size="sm"
                  onClick={onPay}
                  className="rounded-xl bg-emerald-600 hover:bg-emerald-500 font-bold text-white"
                >
                  <CheckCircle className="h-4 w-4 ml-1" />
                  دفع
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onCancel}
                  className="rounded-xl border-destructive/30 text-destructive hover:bg-destructive hover:text-white font-bold"
                >
                  <XCircle className="h-4 w-4 ml-1" />
                  إلغاء
                </Button>
              </>
            )}
            {isPaid && (
              <Button
                variant="outline"
                size="sm"
                className="rounded-xl border-white/10 hover:bg-primary/10 font-bold"
              >
                <Download className="h-4 w-4 ml-1" />
                تحميل PDF
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}