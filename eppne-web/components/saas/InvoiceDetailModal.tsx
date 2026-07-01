// components/saas/InvoiceDetailModal.tsx
"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Invoice } from "@/types/saas";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { X, CalendarDays, CreditCard, CheckCircle, Clock, Download, Printer } from "lucide-react";

interface InvoiceDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  invoice: Invoice | null;
  onPay?: () => void;
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

export function InvoiceDetailModal({ isOpen, onClose, invoice, onPay }: InvoiceDetailModalProps) {
  if (!invoice) return null;

  const config = STATUS_CONFIG[invoice.status] || STATUS_CONFIG.PENDING;
  const StatusIcon = config.icon;
  const isPending = invoice.status === "PENDING";

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-md p-4 animate-in fade-in duration-300">
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="bg-card/90 backdrop-blur-3xl border border-primary/20 shadow-[0_0_50px_-10px_rgba(var(--primary-rgb),0.2)] rounded-[2.5rem] p-8 md:p-10 max-w-2xl w-full max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-2xl font-black text-foreground">تفاصيل الفاتورة</h3>
                <p className="text-sm text-muted-foreground">{invoice.invoice_number}</p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="rounded-full hover:bg-destructive/10"
                onClick={onClose}
              >
                <X className="h-5 w-5" />
              </Button>
            </div>

            {/* حالة الفاتورة */}
            <div className="flex items-center gap-3 p-4 bg-background/40 rounded-xl border border-white/5 mb-6">
              <Badge className={`${config.className} border font-bold`}>
                <StatusIcon className="h-3 w-3 ml-1" />
                {config.label}
              </Badge>
              {invoice.due_date && (
                <span className="text-sm text-muted-foreground">
                  يستحق: {new Date(invoice.due_date).toLocaleDateString("ar-EG")}
                </span>
              )}
            </div>

            {/* معلومات أساسية */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div className="p-4 bg-background/40 rounded-xl border border-white/5">
                <p className="text-xs text-muted-foreground font-bold">المبلغ</p>
                <p className="text-3xl font-black text-amber-500">
                  {invoice.amount.toLocaleString()} {invoice.currency}
                </p>
              </div>
              <div className="p-4 bg-background/40 rounded-xl border border-white/5">
                <p className="text-xs text-muted-foreground font-bold">تاريخ الإنشاء</p>
                <p className="text-lg font-black text-foreground">
                  {new Date(invoice.created_at).toLocaleDateString("ar-EG")}
                </p>
                <p className="text-xs text-muted-foreground">
                  {new Date(invoice.created_at).toLocaleTimeString("ar-EG")}
                </p>
              </div>
            </div>

            {/* بنود الفاتورة */}
            {invoice.items && invoice.items.length > 0 && (
              <div className="mb-6">
                <h4 className="font-bold text-lg text-foreground mb-3">البنود</h4>
                <div className="space-y-2">
                  {invoice.items.map((item, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-3 bg-background/40 rounded-xl border border-white/5"
                    >
                      <div>
                        <p className="font-bold text-sm text-foreground">{item.service}</p>
                        <p className="text-xs text-muted-foreground">{item.period}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-black text-sm">{item.amount} {item.currency}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* الإجمالي */}
            <div className="flex items-center justify-between p-4 bg-primary/5 rounded-xl border border-primary/20 mb-6">
              <span className="font-bold text-lg text-foreground">الإجمالي</span>
              <span className="text-2xl font-black text-primary">
                {invoice.amount.toLocaleString()} {invoice.currency}
              </span>
            </div>

            {/* الأزرار */}
            <div className="flex flex-wrap gap-3">
              {isPending && (
                <Button
                  onClick={onPay}
                  className="flex-1 h-14 rounded-xl bg-emerald-600 hover:bg-emerald-500 font-bold text-white shadow-[0_0_20px_rgba(16,185,129,0.3)]"
                >
                  <CheckCircle className="ml-2 h-5 w-5" />
                  دفع الفاتورة
                </Button>
              )}
              <Button
                variant="outline"
                className="flex-1 h-14 rounded-xl border-white/10 hover:bg-primary/10 font-bold"
              >
                <Printer className="ml-2 h-5 w-5" />
                طباعة
              </Button>
              {invoice.status === "PAID" && (
                <Button
                  variant="outline"
                  className="flex-1 h-14 rounded-xl border-white/10 hover:bg-primary/10 font-bold"
                >
                  <Download className="ml-2 h-5 w-5" />
                  تحميل PDF
                </Button>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}