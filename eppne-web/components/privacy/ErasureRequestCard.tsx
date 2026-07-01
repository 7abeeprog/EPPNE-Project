// components/privacy/ErasureRequestCard.tsx
"use client";

import { motion } from "framer-motion";
import { ErasureRequest } from "@/types/privacy";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
    Clock,
    CheckCircle,
    XCircle,
    Loader2,
    CalendarDays,
    Hash,
    Shield,
} from "lucide-react";

interface ErasureRequestCardProps {
    request: ErasureRequest;
    index?: number;
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

const STATUS_CONFIG = {
    PENDING: {
        label: "قيد الانتظار",
        icon: Clock,
        className: "bg-amber-500/10 text-amber-500 border-amber-500/20",
        dot: "bg-amber-500 animate-pulse",
    },
    PROCESSING: {
        label: "جاري المعالجة",
        icon: Loader2,
        className: "bg-blue-500/10 text-blue-500 border-blue-500/20",
        dot: "bg-blue-500 animate-spin",
    },
    COMPLETED: {
        label: "مكتمل",
        icon: CheckCircle,
        className: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
        dot: "bg-emerald-500",
    },
    PARTIAL_ON_CHAIN: {
        label: "مكتمل جزئياً",
        icon: Shield,
        className: "bg-purple-500/10 text-purple-500 border-purple-500/20",
        dot: "bg-purple-500",
    },
    REJECTED: {
        label: "مرفوض",
        icon: XCircle,
        className: "bg-destructive/10 text-destructive border-destructive/20",
        dot: "bg-destructive",
    },
};

export function ErasureRequestCard({ request, index = 0 }: ErasureRequestCardProps) {
    const status = STATUS_CONFIG[request.status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.PENDING;
    const StatusIcon = status.icon;
    const isPending = request.status === "PENDING" || request.status === "PROCESSING";

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05, type: "spring", stiffness: 300, damping: 24 }}
        >
            <Card className="border-white/10 bg-card/40 backdrop-blur-md rounded-[2rem] hover:border-primary/40 hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] transition-all group overflow-hidden">
                <CardContent className="p-6 md:p-8">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div className="flex-1 space-y-3">
                            {/* الرأس: القطاع + الحالة */}
                            <div className="flex flex-wrap items-center gap-3">
                                <h3 className="text-2xl font-black text-foreground group-hover:text-primary transition-colors">
                                    {MODULES_LABELS[request.target_module] || request.target_module}
                                </h3>
                                <Badge className={`${status.className} border font-bold shrink-0`}>
                                    <StatusIcon className={`h-3 w-3 ml-1 ${isPending ? "animate-spin" : ""}`} />
                                    {status.label}
                                </Badge>
                            </div>

                            {/* التفاصيل */}
                            <div className="flex flex-wrap items-center gap-4 text-sm">
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
                                {request.erasure_receipt_tx && (
                                    <div className="flex items-center gap-2 bg-background/40 px-4 py-2 rounded-xl border border-white/5 shadow-inner">
                                        <Hash className="h-4 w-4 text-muted-foreground" />
                                        <span className="font-mono text-xs font-bold truncate max-w-[150px]">
                                            {request.erasure_receipt_tx.slice(0, 16)}...
                                        </span>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* مؤشر الحالة الدائري */}
                        <div className="flex items-center gap-2 shrink-0">
                            <div className={`h-3 w-3 rounded-full ${status.dot}`} />
                            <span className="text-xs font-bold text-muted-foreground">
                                {new Date(request.created_at).toLocaleTimeString("ar-EG")}
                            </span>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </motion.div>
    );
}