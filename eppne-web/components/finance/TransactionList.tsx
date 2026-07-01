// components/finance/TransactionList.tsx
"use client";

import { useRef, useCallback } from "react";
import { useTransactionHistory } from "@/hooks/finance/useTransactionHistory";
import { TransactionItem } from "./TransactionItem";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Loader2, Inbox, AlertCircle } from "lucide-react";

export function TransactionList() {
  const observerRef = useRef<IntersectionObserver | null>(null);
  const lastElementRef = useCallback(
    (node: HTMLDivElement | null) => {
      if (observerRef.current) observerRef.current.disconnect();
      observerRef.current = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      });
      if (node) observerRef.current.observe(node);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  const { data, isLoading, error, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useTransactionHistory(20);

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-24 rounded-[2rem] bg-card/40 border border-white/5" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 bg-destructive/10 rounded-[2rem] border border-destructive/20 text-center">
        <AlertCircle className="mx-auto h-12 w-12 text-destructive mb-4" />
        <p className="text-destructive font-bold">فشل في تحميل المعاملات</p>
        <p className="text-muted-foreground mt-2">{error.message}</p>
        <Button variant="outline" className="mt-4" onClick={() => window.location.reload()}>
          إعادة المحاولة
        </Button>
      </div>
    );
  }

  const transactions = data?.pages.flatMap((page) => page.data) || [];

  if (transactions.length === 0) {
    return (
      <div className="text-center py-20 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-primary/20">
        <Inbox className="mx-auto h-16 w-16 text-primary/30 mb-4 animate-pulse" />
        <h3 className="text-2xl font-black text-foreground">لا توجد معاملات</h3>
        <p className="text-muted-foreground mt-2 text-lg">ابدأ بإجراء أول عملية تحويل أو صرافة.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {transactions.map((transaction, index) => (
        <TransactionItem
          key={transaction.tx_hash}
          transaction={transaction}
          index={index}
        />
      ))}

      {/* عنصر المراقبة لـ Infinite Scroll */}
      <div ref={lastElementRef} className="h-4" />

      {isFetchingNextPage && (
        <div className="flex justify-center py-4">
          <Loader2 className="h-8 w-8 text-primary animate-spin" />
        </div>
      )}

      {!hasNextPage && transactions.length > 0 && (
        <p className="text-center text-sm text-muted-foreground py-4">
          لقد وصلت إلى نهاية سجل المعاملات.
        </p>
      )}
    </div>
  );
}