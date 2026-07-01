// components/privacy/ErasureRequestList.tsx
"use client";

import { useState } from "react";
import { useErasureRequests } from "@/hooks/privacy/useErasureRequests";
import { ErasureRequestCard } from "./ErasureRequestCard";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Filter, Loader2, Inbox, AlertCircle } from "lucide-react";
import { ErasureStatus } from "@/types/privacy"; // تأكد من استيراد النوع
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

interface ErasureRequestListProps {
    statusFilter?: string;
}

export function ErasureRequestList({ statusFilter = "" }: ErasureRequestListProps) {
    // تحديد النوع بدقة لـ status
    const [status, setStatus] = useState<ErasureStatus | "">(statusFilter as ErasureStatus | "");
    const [skip, setSkip] = useState(0);
    const limit = 10;

    const { data, isLoading, error, isFetching } = useErasureRequests(skip, limit, status || undefined);

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

    if (isLoading && !data) {
        return (
            <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-32 rounded-[2rem] bg-card/40 border border-white/5" />
                ))}
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-8 bg-destructive/10 rounded-[2rem] border border-destructive/20 text-center">
                <AlertCircle className="mx-auto h-12 w-12 text-destructive mb-4" />
                <p className="text-destructive font-bold">فشل في تحميل طلبات المحو</p>
                <p className="text-muted-foreground mt-2">{error.message}</p>
            </div>
        );
    }

    if (!data || data.data.length === 0) {
        return (
            <div className="text-center py-20 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-primary/20">
                <Inbox className="mx-auto h-16 w-16 text-primary/30 mb-4 animate-pulse" />
                <h3 className="text-2xl font-black text-foreground">لا توجد طلبات محو</h3>
                <p className="text-muted-foreground mt-2 text-lg">
                    {status ? "لا توجد طلبات تطابق الفلتر المحدد." : "قم بإنشاء طلبك الأول أعلاه."}
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div className="flex items-center gap-2">
                    <Filter className="h-5 w-5 text-muted-foreground" />
                    <span className="text-sm font-bold text-muted-foreground">فلترة حسب الحالة:</span>
                    <Select value={status} onValueChange={(val: ErasureStatus) => { setStatus(val); setSkip(0); }}>
                        <SelectTrigger className="w-44 h-10 bg-background/50 border-white/10 rounded-xl text-sm">
                            <SelectValue placeholder="جميع الحالات" />
                        </SelectTrigger>
                        <SelectContent className="bg-card/90 backdrop-blur-xl border-white/10">
                            <SelectItem value="">جميع الحالات</SelectItem>
                            <SelectItem value="PENDING">قيد الانتظار</SelectItem>
                            <SelectItem value="PROCESSING">جاري المعالجة</SelectItem>
                            <SelectItem value="COMPLETED">مكتمل</SelectItem>
                            <SelectItem value="REJECTED">مرفوض</SelectItem>
                            <SelectItem value="PARTIAL_ON_CHAIN">مكتمل جزئياً</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </div>

            <div className="space-y-4">
                {data.data.map((request, index) => (
                    <ErasureRequestCard key={request.id} request={request} index={index} />
                ))}
            </div>

            <div className="flex justify-between items-center pt-4 border-t border-border/50">
                <Button variant="outline" onClick={handlePrevious} disabled={skip === 0 || isFetching} className="rounded-xl">السابق</Button>
                <span className="text-sm text-muted-foreground font-bold">
                    صفحة {Math.floor(skip / limit) + 1} / {Math.ceil(data.total / limit)}
                </span>
                <Button variant="outline" onClick={handleNext} disabled={skip + limit >= data.total || isFetching} className="rounded-xl">التالي</Button>
            </div>
        </div>
    );
}