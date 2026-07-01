// components/privacy/ProcessErasureModal.tsx
"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ErasureRequest } from "@/types/privacy";
import { useProcessErasureRequest } from "@/hooks/privacy/useErasureRequests";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, ShieldAlert, CheckCircle, XCircle, X, AlertTriangle } from "lucide-react";
import { toast } from "sonner";

interface ProcessErasureModalProps {
    isOpen: boolean;
    onClose: () => void;
    request: ErasureRequest | null;
}

const MODULES_LABELS: Record<string, string> = {
    identity: "الهوية",
    academy: "الأكاديمية",
    finance: "المالية",
    commerce: "التجارة",
    health: "الصحة",
    iot: "إنترنت الأشياء",
    realestate: "العقارات",
    all: "جميع القطاعات",
};

export function ProcessErasureModal({ isOpen, onClose, request }: ProcessErasureModalProps) {
    const [notes, setNotes] = useState("");
    const [action, setAction] = useState<"approve" | "reject" | null>(null);
    const [isConfirmOpen, setIsConfirmOpen] = useState(false);
    const processMutation = useProcessErasureRequest();

    // إعادة تعيين الحالة عند فتح المودال
    useEffect(() => {
        if (isOpen) {
            setNotes("");
            setAction(null);
            setIsConfirmOpen(false);
        }
    }, [isOpen]);

    const handleAction = (selectedAction: "approve" | "reject") => {
        setAction(selectedAction);
        setIsConfirmOpen(true);
    };

    const handleConfirm = () => {
        if (!request || !action) return;

        const approve = action === "approve";

        processMutation.mutate(
            {
                requestId: request.id,
                approve,
                notes: notes || undefined,
            },
            {
                onSuccess: () => {
                    toast.success(approve ? "تم قبول الطلب بنجاح" : "تم رفض الطلب");
                    onClose();
                },
                onError: (error) => {
                    // الخطأ يتم معالجته في الـ Service
                },
            }
        );
    };

    if (!request) return null;

    return (
        <>
            <AnimatePresence>
                {isOpen && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-md p-4 animate-in fade-in duration-300">
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            className="bg-card/90 backdrop-blur-3xl border border-primary/20 shadow-[0_0_50px_-10px_rgba(var(--primary-rgb),0.2)] rounded-[2.5rem] p-8 md:p-10 max-w-lg w-full"
                        >
                            <div className="flex items-start justify-between mb-6">
                                <div className="flex items-center gap-4">
                                    <div className="p-3 bg-primary/10 rounded-full border border-primary/20">
                                        <ShieldAlert className="h-8 w-8 text-primary" />
                                    </div>
                                    <div>
                                        <h3 className="text-2xl font-black text-foreground">معالجة الطلب</h3>
                                        <p className="text-sm text-muted-foreground">مراجعة طلب محو البيانات</p>
                                    </div>
                                </div>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="rounded-full hover:bg-destructive/10"
                                    onClick={onClose}
                                    disabled={processMutation.isPending}
                                >
                                    <X className="h-5 w-5" />
                                </Button>
                            </div>

                            <div className="space-y-4 mb-6">
                                <div className="p-4 bg-background/40 rounded-xl border border-white/5">
                                    <p className="text-sm text-muted-foreground">القطاع المستهدف</p>
                                    <p className="text-lg font-black text-foreground">
                                        {MODULES_LABELS[request.target_module] || request.target_module}
                                    </p>
                                </div>
                                <div className="p-4 bg-background/40 rounded-xl border border-white/5">
                                    <p className="text-sm text-muted-foreground">المستخدم</p>
                                    <p className="text-lg font-black text-foreground">#{request.user_id}</p>
                                </div>
                                {request.reason && (
                                    <div className="p-4 bg-background/40 rounded-xl border border-white/5">
                                        <p className="text-sm text-muted-foreground">سبب الطلب</p>
                                        <p className="text-foreground font-medium">{request.reason}</p>
                                    </div>
                                )}
                                <div className="p-4 bg-background/40 rounded-xl border border-white/5">
                                    <p className="text-sm text-muted-foreground">تاريخ الطلب</p>
                                    <p className="text-foreground font-bold">
                                        {new Date(request.created_at).toLocaleString("ar-EG")}
                                    </p>
                                </div>
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <Label className="font-bold text-lg text-foreground">ملاحظات المشرف (اختياري)</Label>
                                    <Textarea
                                        placeholder="أضف ملاحظات حول سبب القبول أو الرفض..."
                                        value={notes}
                                        onChange={(e) => setNotes(e.target.value)}
                                        className="mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner text-lg resize-none"
                                        rows={3}
                                        disabled={processMutation.isPending}
                                    />
                                </div>

                                <div className="flex gap-4 pt-4">
                                    <Button
                                        variant="outline"
                                        onClick={() => handleAction("reject")}
                                        disabled={processMutation.isPending}
                                        className="flex-1 h-14 rounded-xl border-destructive/30 text-destructive hover:bg-destructive hover:text-white font-bold text-lg transition-all"
                                    >
                                        <XCircle className="mr-2 h-5 w-5" />
                                        رفض
                                    </Button>
                                    <Button
                                        onClick={() => handleAction("approve")}
                                        disabled={processMutation.isPending}
                                        className="flex-1 h-14 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-lg shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:shadow-[0_0_30px_rgba(16,185,129,0.5)] transition-all"
                                    >
                                        <CheckCircle className="mr-2 h-5 w-5" />
                                        قبول
                                    </Button>
                                </div>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>

            {/* ✅ Confirmation Modal للتأكيد النهائي */}
            <AnimatePresence>
                {isConfirmOpen && (
                    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-background/90 backdrop-blur-md p-4 animate-in fade-in duration-300">
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            className="bg-card/90 backdrop-blur-3xl border border-destructive/20 shadow-[0_0_50px_-10px_rgba(239,68,68,0.2)] rounded-[2.5rem] p-8 md:p-10 max-w-md w-full"
                        >
                            <div className="flex items-center gap-4 mb-6">
                                <div className="p-3 bg-destructive/10 rounded-full border border-destructive/20">
                                    <AlertTriangle className="h-8 w-8 text-destructive" />
                                </div>
                                <div>
                                    <h3 className="text-2xl font-black text-foreground">تأكيد الإجراء</h3>
                                    <p className="text-sm text-muted-foreground">
                                        {action === "approve" ? "قبول طلب المحو" : "رفض طلب المحو"}
                                    </p>
                                </div>
                            </div>

                            <p className="text-muted-foreground mb-6">
                                {action === "approve"
                                    ? "سيتم حذف جميع بيانات المستخدم في القطاع المحدد بشكل نهائي. هذا الإجراء غير قابل للتراجع."
                                    : "سيتم رفض طلب المحو ولن يتم حذف أي بيانات."}
                            </p>

                            <div className="flex gap-4">
                                <Button
                                    variant="ghost"
                                    onClick={() => setIsConfirmOpen(false)}
                                    className="flex-1 h-14 rounded-xl text-lg font-bold"
                                    disabled={processMutation.isPending}
                                >
                                    إلغاء
                                </Button>
                                <Button
                                    onClick={handleConfirm}
                                    disabled={processMutation.isPending}
                                    className={`flex-1 h-14 rounded-xl text-lg font-bold text-white ${action === "approve"
                                            ? "bg-emerald-600 hover:bg-emerald-500 shadow-[0_0_20px_rgba(16,185,129,0.3)]"
                                            : "bg-destructive hover:bg-destructive/90 shadow-[0_0_20px_rgba(239,68,68,0.3)]"
                                        }`}
                                >
                                    {processMutation.isPending ? (
                                        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                    ) : null}
                                    {action === "approve" ? "تأكيد القبول" : "تأكيد الرفض"}
                                </Button>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </>
    );
}