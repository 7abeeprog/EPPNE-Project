// components/privacy/PendingErasureRequests.tsx
"use client";

import { useState } from "react";
import { motion, Variants } from "framer-motion"; // تم إضافة Variants هنا
import { usePendingErasureRequests } from "@/hooks/privacy/useErasureRequests";
import { ErasureRequest } from "@/types/privacy";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
    CheckCircle,
    XCircle,
    Clock,
    CalendarDays,
    User,
    AlertCircle,
    Loader2,
    Inbox,
} from "lucide-react";
import { ProcessErasureModal } from "./ProcessErasureModal";

// ✅ تعريف الحركات مع النوع الصريح
const cardVariants: Variants = {
    hidden: { opacity: 0, y: 20 },
    show: {
        opacity: 1,
        y: 0,
        transition: { type: "spring", stiffness: 300, damping: 24 },
    },
};

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

// ❌ تم إزالة دالة handleProcess الخاطئة التي كانت هنا خارج المكون

export function PendingErasureRequests() {
    // ✅ تعريف الـ States في بداية المكون
    const [skip, setSkip] = useState(0);
    const [selectedRequest, setSelectedRequest] = useState<ErasureRequest | null>(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const limit = 10;

    const { data, isLoading, error, refetch, isFetching } = usePendingErasureRequests(skip, limit);

    const handleNext = () => {
        if (data && skip + limit < data.total) {
            setSkip((prev) => prev + limit);
        }
    };

    const handlePrevious = () => {
        if (skip > 0) {
            setSkip((prev) => prev - limit);
        }
    };

    // ✅ الدالة الصحيحة موجودة هنا داخل النطاق (Scope) الصحيح
    const handleProcess = (request: ErasureRequest) => {
        setSelectedRequest(request);
        setIsModalOpen(true);
    };

    const handleModalClose = () => {
        setIsModalOpen(false);
        setSelectedRequest(null);
        refetch();
    };

    if (isLoading && !data) {
        return (
            <div className="space-y-4">
                {[1, 2, 3, 4].map((i) => (
                    <Skeleton key={i} className="h-40 rounded-[2rem] bg-card/40 border border-white/5" />
                ))}
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-8 bg-destructive/10 rounded-[2rem] border border-destructive/20 text-center">
                <AlertCircle className="mx-auto h-12 w-12 text-destructive mb-4" />
                <p className="text-destructive font-bold">فشل في تحميل الطلبات المعلقة</p>
                <p className="text-muted-foreground mt-2">{error.message}</p>
                <Button variant="outline" className="mt-4" onClick={() => refetch()}>
                    إعادة المحاولة
                </Button>
            </div>
        );
    }

    if (!data || data.data.length === 0) {
        return (
            <div className="text-center py-20 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-emerald-500/20">
                <Inbox className="mx-auto h-16 w-16 text-emerald-500/30 mb-4 animate-pulse" />
                <h3 className="text-2xl font-black text-foreground">لا توجد طلبات معلقة</h3>
                <p className="text-muted-foreground mt-2 text-lg">
                    جميع الطلبات تمت معالجتها. عودة إلى وضع الراحة.
                </p>
            </div>
        );
    }

    return (
        <>
            <div className="space-y-6">
                {/* ✅ شريط المعلومات */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-background/30 p-4 rounded-2xl border border-white/5">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-amber-500/10 rounded-lg border border-amber-500/20">
                            <Clock className="h-5 w-5 text-amber-500 animate-pulse" />
                        </div>
                        <div>
                            <p className="font-bold text-lg text-foreground">طلبات معلقة</p>
                            <p className="text-sm text-muted-foreground">
                                {data.total} طلب {data.total > 1 ? "ينتظرون" : "ينتظر"} المعالجة
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        {isFetching && <Loader2 className="h-4 w-4 animate-spin" />}
                        <span>
                            عرض {skip + 1} - {Math.min(skip + limit, data.total)} من {data.total}
                        </span>
                    </div>
                </div>

                {/* ✅ قائمة الطلبات */}
                <div className="space-y-4">
                    {data.data.map((request, index) => (
                        <motion.div
                            key={request.id}
                            variants={cardVariants}
                            initial="hidden"
                            animate="show"
                            transition={{ delay: index * 0.05 }}
                        >
                            <Card className="border-white/10 bg-card/40 backdrop-blur-md rounded-[2rem] hover:border-amber-500/50 hover:shadow-[0_0_30px_rgba(245,158,11,0.15)] transition-all group overflow-hidden">
                                <CardContent className="p-6 md:p-8">
                                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                        <div className="flex-1 space-y-3">
                                            {/* الرأس: القطاع + الحالة */}
                                            <div className="flex flex-wrap items-center gap-3">
                                                <h3 className="text-2xl font-black text-foreground group-hover:text-amber-500 transition-colors">
                                                    {MODULES_LABELS[request.target_module] || request.target_module}
                                                </h3>
                                                <Badge className="bg-amber-500/10 text-amber-500 border-amber-500/20 font-bold">
                                                    <Clock className="h-3 w-3 ml-1 animate-pulse" />
                                                    قيد الانتظار
                                                </Badge>
                                            </div>

                                            {/* تفاصيل الطلب */}
                                            <div className="flex flex-wrap items-center gap-4 text-sm">
                                                <div className="flex items-center gap-2 bg-background/40 px-4 py-2 rounded-xl border border-white/5 shadow-inner">
                                                    <User className="h-4 w-4 text-muted-foreground" />
                                                    <span className="font-bold">المستخدم #{request.user_id}</span>
                                                </div>
                                                {request.reason && (
                                                    <div className="flex items-center gap-2 bg-background/40 px-4 py-2 rounded-xl border border-white/5 shadow-inner">
                                                        <span className="text-muted-foreground">السبب:</span>
                                                        <span className="font-medium text-foreground line-clamp-1 max-w-[200px]">
                                                            {request.reason}
                                                        </span>
                                                    </div>
                                                )}
                                                <div className="flex items-center gap-2 bg-background/40 px-4 py-2 rounded-xl border border-white/5 shadow-inner">
                                                    <CalendarDays className="h-4 w-4 text-muted-foreground" />
                                                    <span className="font-bold">
                                                        {new Date(request.created_at).toLocaleDateString("ar-EG")}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>

                                        {/* أزرار الإجراءات */}
                                        <div className="flex gap-2 shrink-0">
                                            <Button
                                                onClick={() => handleProcess(request)}
                                                className="rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold shadow-[0_0_15px_rgba(16,185,129,0.2)] hover:shadow-[0_0_25px_rgba(16,185,129,0.4)] transition-all"
                                            >
                                                <CheckCircle className="h-4 w-4 ml-1" />
                                                قبول
                                            </Button>
                                            <Button
                                                onClick={() => handleProcess(request)}
                                                variant="outline"
                                                className="rounded-xl border-destructive/30 text-destructive hover:bg-destructive hover:text-white font-bold transition-all"
                                            >
                                                <XCircle className="h-4 w-4 ml-1" />
                                                رفض
                                            </Button>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </motion.div>
                    ))}
                </div>

                {/* ✅ أزرار Pagination */}
                <div className="flex justify-between items-center pt-4 border-t border-border/50">
                    <Button
                        variant="outline"
                        onClick={handlePrevious}
                        disabled={skip === 0 || isFetching}
                        className="rounded-xl border-white/10 hover:bg-primary/10 font-bold"
                    >
                        السابق
                    </Button>
                    <span className="text-sm text-muted-foreground font-bold">
                        صفحة {Math.floor(skip / limit) + 1} / {Math.ceil(data.total / limit)}
                    </span>
                    <Button
                        variant="outline"
                        onClick={handleNext}
                        disabled={skip + limit >= data.total || isFetching}
                        className="rounded-xl border-white/10 hover:bg-primary/10 font-bold"
                    >
                        التالي
                    </Button>
                </div>
            </div>

            {/* ✅ نافذة معالجة الطلب */}
            <ProcessErasureModal
                isOpen={isModalOpen}
                onClose={handleModalClose}
                request={selectedRequest}
            />
        </>
    );
}