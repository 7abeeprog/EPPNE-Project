// app/(dashboard)/store/cart/page.tsx
"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCartStore } from "@/store/cart-store";
import { useAuthStore } from "@/store/auth-store";
import { CommerceService } from "@/services/commerce.service";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ShoppingCart, Trash2, Plus, Minus, ArrowRight, ShoppingBag } from "lucide-react";
import { toast } from "sonner";

export default function CartPage() {
  const router = useRouter();
  const { user } = useAuthStore();
  const { items, updateQuantity, removeItem, clearCart, getTotalItems, getTotalPrice } = useCartStore();
  const [isLoading, setIsLoading] = useState(true);
  const [storeId] = useState(1); // سيتم جلبه من الـ Tenant

  // ✅ إعادة بناء الكائنات الكاملة للـ CartItems (لأن persist خزنها جزئياً)
  useEffect(() => {
    const restoreCartItems = async () => {
      if (items.length === 0) {
        setIsLoading(false);
        return;
      }
      try {
        // جلب تفاصيل المنتجات والمتغيرات بناءً على المعرفات المخزنة
        // هنا نفترض أن لدينا طريقة لجلب المنتجات حسب المعرفات
        // يمكن استخدام batch API
        setIsLoading(false);
      } catch (error) {
        toast.error("فشل تحميل تفاصيل السلة");
        setIsLoading(false);
      }
    };
    restoreCartItems();
  }, []);

  const totalPrice = getTotalPrice();
  const totalItems = getTotalItems();

  if (isLoading) {
    return (
      <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-5xl mx-auto">
        <Skeleton className="h-32 w-full rounded-[2rem] bg-card/40" />
        <Skeleton className="h-64 w-full rounded-[2rem] bg-card/40" />
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
        <div className="p-6 bg-primary/10 rounded-full mb-6 border border-primary/20">
          <ShoppingCart className="h-16 w-16 text-primary/50" />
        </div>
        <h2 className="text-3xl font-black text-foreground mb-2">سلتك فارغة</h2>
        <p className="text-muted-foreground text-lg mb-8">ابدأ بالتسوق الآن واكتشف منتجاتنا السيادية</p>
        <Link href="/store">
          <Button size="lg" className="rounded-xl h-14 px-8 font-bold">
            <ShoppingBag className="ml-2 h-5 w-5" />
            استكشف المتجر
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-5xl mx-auto relative"
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(16,185,129,0.05),_transparent_80%)] pointer-events-none -z-10" />

      <div className="flex items-center justify-between">
        <h1 className="text-3xl md:text-4xl font-black text-foreground flex items-center gap-3">
          <ShoppingCart className="h-8 w-8 text-primary" />
          سلة التسوق ({totalItems} منتج)
        </h1>
        <Button variant="ghost" onClick={clearCart} className="text-destructive hover:bg-destructive/10">
          <Trash2 className="h-4 w-4 ml-1" />
          تفريغ السلة
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-4">
          {items.map((item) => {
            const variant = item.variant;
            const product = variant?.product;
            const price = variant?.discount_price || variant?.price_mrusdt || 0;

            return (
              <Card key={item.variant_id} className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] overflow-hidden">
                <CardContent className="p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h4 className="font-bold text-foreground truncate">{product?.title || `منتج #${item.variant_id}`}</h4>
                    <p className="text-sm text-muted-foreground truncate">
                      {variant?.sku || 'SKU غير متاح'} • {variant?.attributes ? JSON.stringify(variant.attributes) : ''}
                    </p>
                    <p className="text-lg font-black text-primary mt-1">
                      {price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })} MR_USDT
                    </p>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 bg-background/50 rounded-xl border border-white/10 p-1">
                      <button
                        onClick={() => updateQuantity(item.variant_id, item.quantity - 1)}
                        className="p-2 rounded-lg hover:bg-primary/10 transition-colors"
                        disabled={item.quantity <= 1}
                      >
                        <Minus className="h-4 w-4" />
                      </button>
                      <span className="font-black w-8 text-center">{item.quantity}</span>
                      <button
                        onClick={() => updateQuantity(item.variant_id, item.quantity + 1)}
                        className="p-2 rounded-lg hover:bg-primary/10 transition-colors"
                        disabled={variant?.stock_quantity !== undefined && item.quantity >= variant.stock_quantity}
                      >
                        <Plus className="h-4 w-4" />
                      </button>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => removeItem(item.variant_id)}
                      className="text-destructive hover:bg-destructive/10 rounded-xl"
                    >
                      <Trash2 className="h-5 w-5" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="lg:col-span-1">
          <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden sticky top-8">
            <CardContent className="p-6 space-y-6">
              <h3 className="text-2xl font-black text-foreground">ملخص الطلب</h3>

              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">المنتجات ({totalItems})</span>
                  <span className="font-bold">{totalPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })} MR_USDT</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">الشحن</span>
                  <span className="font-bold text-emerald-500">مجاني</span>
                </div>
                <div className="border-t border-border/50 pt-3 flex justify-between text-lg font-black">
                  <span>الإجمالي</span>
                  <span className="text-primary">{totalPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })} MR_USDT</span>
                </div>
              </div>

              <Link href={`/store/checkout?storeId=${storeId}`}>
                <Button
                  className="w-full h-14 text-lg font-black rounded-xl bg-primary hover:bg-primary/90 shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.5)] transition-all"
                >
                  إتمام الشراء <ArrowRight className="mr-2 h-5 w-5" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </motion.div>
  );
}