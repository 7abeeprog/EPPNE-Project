// components/privacy/ErasureRequestForm.tsx
"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useCreateErasureRequest } from "@/hooks/privacy/useErasureRequests";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { Loader2, Trash2, ShieldAlert, AlertTriangle, X } from "lucide-react";
import { toast } from "sonner";

// ✅ قائمة القطاعات المتاحة (تطابق valid_modules في الـ Backend)
const MODULES = [
    { value: "identity", label: "الهوية" },
    { value: "academy", label: "الأكاديمية" },
    { value: "finance", label: "المالية" },
    { value: "commerce", label: "التجارة" },
    { value: "health", label: "الصحة" },
    { value: "iot", label: "إنترنت الأشياء" },
    { value: "realestate", label: "العقارات" },
    { value: "all", label: "جميع القطاعات" },
];

export function ErasureRequestForm() {
    const [targetModule, setTargetModule] = useState<string>("");
    const [reason, setReason] = useState<string>("");
    const [isConfirmOpen, setIsConfirmOpen] = useState(false);
    const createMutation = useCreateErasureRequest();

    const handleSubmit = () => {
        if (!targetModule) {
            toast.error("يرجى اختيار القطاع المستهدف.");
            return;
        }
        setIsConfirmOpen(true);
    };

    const handleConfirm = () => {
        createMutation.mutate(
            { target_module: targetModule, reason: reason || undefined },
            {
                onSuccess: () => {
                    toast.success("تم إنشاء طلب المحو بنجاح!");
                    setTargetModule("");
                    setReason("");
                    setIsConfirmOpen(false);
                },
                onError: (error) => {
                    // الخطأ يتم معالجته في الـ Service عبر handleError
                },
            }
        );
    };

    return (
        <>
            <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
                <CardContent className="p-6 md:p-8">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="p-2 bg-destructive/10 rounded-xl border border-destructive/20">
                            <Trash2 className="h-6 w-6 text-destructive" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-black text-foreground">طلب محو البيانات</h2>
                            <p className="text-sm text-muted-foreground">
                                سيتم معالجة طلبك بواسطة فريق الخصوصية وقد يستغرق بعض الوقت.
                            </p>
                        </div>
                    </div>

                    <div className="space-y-5">
                        <div>
                            <Label className="font-bold text-lg text-foreground">القطاع المستهدف</Label>
                            <Select
                                value={targetModule}
                                onValueChange={setTargetModule}
                            >
                                <SelectTrigger className="w-full h-14 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-destructive focus:ring-1 focus:ring-destructive/50 shadow-inner text-lg">
                                    <SelectValue placeholder="اختر القطاع..." />
                                </SelectTrigger>
                                <SelectContent className="bg-card/90 backdrop-blur-xl border-white/10">
                                    {MODULES.map((module) => (
                                        <SelectItem key={module.value} value={module.value}>
                                            {module.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <p className="text-xs text-muted-foreground mt-2">
                                سيتم حذف جميع بياناتك في هذا القطاع بشكل نهائي.
                            </p>
                        </div>

                        <div>
                            <Label className="font-bold text-lg text-foreground">سبب الطلب (اختياري)</Label>
                            <Input
                                placeholder="اذكر سبب طلبك للمساعدة في تسريع المعالجة..."
                                value={reason}
                                onChange={(e) => setReason(e.target.value)}
                                className="h-14 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-destructive shadow-inner text-lg"
                            />
                        </div>

                        <Button
                            onClick={handleSubmit}
                            disabled={!targetModule || createMutation.isPending}
                            className="w-full h-14 text-lg font-bold rounded-xl bg-destructive hover:bg-destructive/90 text-white shadow-[0_0_20px_rgba(239,68,68,0.3)] hover:scale-105 transition-transform mt-4"
                        >
                            {createMutation.isPending ? (
                                <Loader2 className="mr-2 h-6 w-6 animate-spin" />
                            ) : (
                                <Trash2 className="mr-2 h-6 w-6" />
                            )}
                            {createMutation.isPending ? "جاري إرسال الطلب..." : "تقديم طلب المحو"}
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* ✅ Confirmation Modal */}
            <AnimatePresence>
                {isConfirmOpen && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-md p-4 animate-in fade-in duration-300">
                        <motion.div
                            initial={{ scale: 0.95, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            className="bg-card/90 backdrop-blur-3xl border border-destructive/20 shadow-[0_0_50px_-10px_rgba(239,68,68,0.2)] rounded-[2.5rem] p-8 md:p-10 max-w-lg w-full"
                        >
                            <div className="flex items-start justify-between mb-6">
                                <div className="flex items-center gap-4">
                                    <div className="p-3 bg-destructive/10 rounded-full border border-destructive/20">
                                        <AlertTriangle className="h-8 w-8 text-destructive" />
                                    </div>
                                    <div>
                                        <h3 className="text-2xl font-black text-foreground">تأكيد المحو</h3>
                                        <p className="text-sm text-muted-foreground">هذا الإجراء غير قابل للتراجع</p>
                                    </div>
                                </div>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="rounded-full hover:bg-destructive/10"
                                    onClick={() => setIsConfirmOpen(false)}
                                >
                                    <X className="h-5 w-5" />
                                </Button>
                            </div>

                            <div className="p-4 bg-destructive/5 rounded-xl border border-destructive/20 mb-6">
                                <p className="font-bold text-foreground">
                                    سيتم حذف جميع بياناتك في قطاع:
                                </p>
                                <p className="text-lg font-black text-destructive mt-1">
                                    {MODULES.find((m) => m.value === targetModule)?.label || targetModule}
                                </p>
                                {reason && (
                                    <p className="text-sm text-muted-foreground mt-2">
                                        السبب: {reason}
                                    </p>
                                )}
                            </div>

                            <p className="text-sm text-muted-foreground mb-6">
                                هذا الطلب سيُرسل إلى فريق الخصوصية للمراجعة. سيتم إعلامك عند اكتمال المعالجة.
                            </p>

                            <div className="flex gap-4">
                                <Button
                                    variant="ghost"
                                    onClick={() => setIsConfirmOpen(false)}
                                    className="flex-1 h-14 rounded-xl text-lg font-bold hover:bg-destructive/10"
                                >
                                    إلغاء
                                </Button>
                                <Button
                                    onClick={handleConfirm}
                                    disabled={createMutation.isPending}
                                    className="flex-1 h-14 rounded-xl text-lg font-bold bg-destructive hover:bg-destructive/90 text-white shadow-[0_0_20px_rgba(239,68,68,0.3)]"
                                >
                                    {createMutation.isPending ? (
                                        <Loader2 className="mr-2 h-6 w-6 animate-spin" />
                                    ) : (
                                        "تأكيد المحو"
                                    )}
                                </Button>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </>
    );
}