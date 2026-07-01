// components/commerce/ProductGrid.tsx
"use client";

import { useRef, useCallback } from "react";
import { useProducts } from "@/hooks/commerce/useProducts";
import { ProductCard } from "./ProductCard";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Loader2, Inbox, AlertCircle } from "lucide-react";

interface ProductGridProps {
  storeId: number;
  limit?: number;
}

export function ProductGrid({ storeId, limit = 12 }: ProductGridProps) {
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
    useProducts(storeId, limit);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
          <Skeleton key={i} className="h-80 rounded-[2rem] bg-card/40 border border-white/5" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 bg-destructive/10 rounded-[2rem] border border-destructive/20 text-center">
        <AlertCircle className="mx-auto h-12 w-12 text-destructive mb-4" />
        <p className="text-destructive font-bold">فشل في تحميل المنتجات</p>
        <p className="text-muted-foreground mt-2">{error.message}</p>
        <Button variant="outline" className="mt-4" onClick={() => window.location.reload()}>
          إعادة المحاولة
        </Button>
      </div>
    );
  }

  const products = data?.pages.flatMap((page) => page.data) || [];

  if (products.length === 0) {
    return (
      <div className="text-center py-20 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-primary/20">
        <Inbox className="mx-auto h-16 w-16 text-primary/30 mb-4 animate-pulse" />
        <h3 className="text-2xl font-black text-foreground">لا توجد منتجات</h3>
        <p className="text-muted-foreground mt-2 text-lg">المتجر فارغ حالياً. تابعنا قريباً!</p>
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {products.map((product, index) => (
          <ProductCard key={product.id} product={product} index={index} />
        ))}
      </div>

      <div ref={lastElementRef} className="h-4" />

      {isFetchingNextPage && (
        <div className="flex justify-center py-4">
          <Loader2 className="h-8 w-8 text-primary animate-spin" />
        </div>
      )}

      {!hasNextPage && products.length > 0 && (
        <p className="text-center text-sm text-muted-foreground py-4">
          لقد وصلت إلى نهاية المنتجات.
        </p>
      )}
    </>
  );
}