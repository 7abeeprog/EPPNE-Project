// components/finance/ConfirmationModal.tsx
"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { X, AlertTriangle, CheckCircle, Loader2 } from "lucide-react";

interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  description: string;
  details: Array<{ label: string; value: string | number; highlight?: boolean }>;
  isProcessing?: boolean;
  isWarning?: boolean;
  confirmLabel?: string;
  cancelLabel?: string;
}

export function ConfirmationModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  details,
  isProcessing = false,
  isWarning = false,
  confirmLabel = "تأكيد",
  cancelLabel = "إلغاء",
}: ConfirmationModalProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-md p-4 animate-in fade-in duration-300">
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className={`bg-card/90 backdrop-blur-3xl border ${
              isWarning ? "border-destructive/30 shadow-[0_0_50px_-10px_rgba(239,68,68,0.2)]" : "border-primary/20 shadow-[0_0_50px_-10px_rgba(var(--primary-rgb),0.2)]"
            } rounded-[2.5rem] p-8 md:p-10 max-w-lg w-full`}
          >
            {/* الرأس */}
            <div className="flex items-start justify-between mb-6">
              <div className="flex items-center gap-4">
                <div
                  className={`p-3 rounded-full border ${
                    isWarning
                      ? "bg-destructive/10 border-destructive/20"
                      : "bg-primary/10 border-primary/20"
                  }`}
                >
                  {isWarning ? (
                    <AlertTriangle className="h-8 w-8 text-destructive" />
                  ) : (
                    <CheckCircle className="h-8 w-8 text-primary" />
                  )}
                </div>
                <div>
                  <h3 className={`text-2xl font-black ${isWarning ? "text-destructive" : "text-foreground"}`}>
                    {title}
                  </h3>
                  <p className="text-sm text-muted-foreground">{description}</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="rounded-full hover:bg-destructive/10"
                onClick={onClose}
                disabled={isProcessing}
              >
                <X className="h-5 w-5" />
              </Button>
            </div>

            {/* التفاصيل */}
            <div className="space-y-3 mb-6">
              {details.map((detail, index) => (
                <div
                  key={index}
                  className={`flex justify-between items-center p-3 rounded-xl border ${
                    detail.highlight
                      ? "bg-destructive/5 border-destructive/20"
                      : "bg-background/40 border-white/5"
                  }`}
                >
                  <span className="text-sm font-bold text-muted-foreground">{detail.label}</span>
                  <span
                    className={`text-lg font-black ${
                      detail.highlight ? "text-destructive" : "text-foreground"
                    }`}
                  >
                    {detail.value}
                  </span>
                </div>
              ))}
            </div>

            {/* تحذير المبلغ الكبير */}
            {isWarning && (
              <div className="p-4 bg-destructive/10 rounded-xl border border-destructive/20 mb-6">
                <p className="text-sm font-bold text-destructive flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  هذا المبلغ كبير. يرجى التأكد من صحة البيانات قبل المتابعة.
                </p>
              </div>
            )}

            {/* الأزرار */}
            <div className="flex gap-4">
              <Button
                variant="ghost"
                onClick={onClose}
                disabled={isProcessing}
                className="flex-1 h-14 rounded-xl text-lg font-bold hover:bg-destructive/10"
              >
                {cancelLabel}
              </Button>
              <Button
                onClick={onConfirm}
                disabled={isProcessing}
                className={`flex-1 h-14 rounded-xl text-lg font-bold text-white ${
                  isWarning
                    ? "bg-destructive hover:bg-destructive/90 shadow-[0_0_20px_rgba(239,68,68,0.3)]"
                    : "bg-primary hover:bg-primary/90 shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)]"
                }`}
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    جاري التنفيذ...
                  </>
                ) : (
                  confirmLabel
                )}
              </Button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}