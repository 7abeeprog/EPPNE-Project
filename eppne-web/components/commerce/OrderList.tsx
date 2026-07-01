// components/commerce/OrderList.tsx
"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useOrders } from "@/hooks/commerce/useOrders";
import { OrderCard } from "./OrderCard";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Loader2, Inbox, AlertCircle } from "lucide-react";

export function OrderList() {
  const [skip, setSkip] = useState(0);
  const limit = 10;

  const { data, isLoading, error, refetch } = useOrders(skip, limit);

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

  if (isLoading) {
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
        <p className="text-destructive font-bold">فشل في تحميل الطلبات</p>
        <p className="text-muted-foreground mt-2">{error.message}</p>
        <Button variant="outline" className="mt-4" onClick={() => refetch()}>
          إعادة المحاولة
        </Button>
      </div>
    );
  }

  if (!data || data.data.length === 0) {
    return (
      <div className="text-center py-20 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-primary/20">
        <Inbox className="mx-auto h-16 w-16 text-primary/30 mb-4 animate-pulse" />
        <h3 className="text-2xl font-black text-foreground">لا توجد طلبات</h3>
        <p className="text-muted-foreground mt-2 text-lg">ابدأ بتسوق المنتجات السيادية.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        {data.data.map((order, index) => (
          <OrderCard key={order.id} order={order} index={index} />
        ))}
      </div>

      <div className="flex justify-between items-center pt-4 border-t border-border/50">
        <Button
          variant="outline"
          onClick={handlePrevious}
          disabled={skip === 0}
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
          disabled={skip + limit >= data.total}
          className="rounded-xl border-white/10 hover:bg-primary/10 font-bold"
        >
          التالي
        </Button>
      </div>
    </div>
  );
}