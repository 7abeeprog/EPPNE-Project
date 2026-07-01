// components/commerce/ProductCard.tsx
"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import Image from "next/image";
import { Product } from "@/types/commerce";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ShoppingCart, Eye } from "lucide-react";
import { useCartStore } from "@/store/cart-store";
import { toast } from "sonner";

interface ProductCardProps {
  product: Product;
  index?: number;
}

export function ProductCard({ product, index = 0 }: ProductCardProps) {
  const { addItem } = useCartStore();
  const firstVariant = product.variants?.[0];

  const handleAddToCart = (e: React.MouseEvent) => {
    e.preventDefault();
    if (!firstVariant) {
      toast.error("هذا المنتج غير متوفر حالياً");
      return;
    }
    if (firstVariant.stock_quantity <= 0) {
      toast.error("المنتج غير متوفر في المخزون");
      return;
    }
    addItem(firstVariant, 1);
    toast.success(`تم إضافة ${product.title} إلى السلة 🛒`);
  };

  const price = firstVariant?.discount_price || firstVariant?.price_mrusdt || product.base_price_mrusdt;
  const hasDiscount = firstVariant?.discount_price && firstVariant.discount_price < firstVariant.price_mrusdt;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, type: "spring", stiffness: 300, damping: 24 }}
    >
      <Link href={`/store/product/${product.id}`}>
        <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-primary/40 hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] transition-all group h-full overflow-hidden">
          <div className="relative h-48 overflow-hidden bg-muted">
            {product.media_gallery?.[0] ? (
              <Image
                src={product.media_gallery[0]}
                alt={product.title}
                fill
                className="object-cover transition-transform duration-700 group-hover:scale-110"
                sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary/10 to-background">
                <span className="text-6xl opacity-20">📦</span>
              </div>
            )}
            {hasDiscount && (
              <Badge className="absolute top-3 right-3 bg-rose-500/90 text-white border-0 shadow-lg">
                خصم
              </Badge>
            )}
            {firstVariant?.stock_quantity === 0 && (
              <Badge className="absolute top-3 left-3 bg-destructive/90 text-white border-0 shadow-lg">
                غير متوفر
              </Badge>
            )}
          </div>

          <CardContent className="p-5 flex flex-col gap-3">
            <div className="flex-1">
              <h3 className="text-xl font-bold line-clamp-1 text-foreground group-hover:text-primary transition-colors">
                {product.title}
              </h3>
              <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                {product.description || "منتج أكاديمي سيادي"}
              </p>
            </div>

            <div className="flex items-center justify-between mt-2 pt-3 border-t border-border/50">
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground font-bold">السعر</span>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-black text-primary drop-shadow-sm">
                    {price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })}
                  </span>
                  <span className="text-xs font-bold text-muted-foreground">MR_USDT</span>
                </div>
                {hasDiscount && (
                  <span className="text-xs text-muted-foreground line-through">
                    {firstVariant?.price_mrusdt.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })} MR_USDT
                  </span>
                )}
              </div>

              <Button
                size="icon"
                onClick={handleAddToCart}
                disabled={firstVariant?.stock_quantity === 0 || !firstVariant}
                className="rounded-xl h-12 w-12 bg-primary hover:bg-primary/90 shadow-[0_0_15px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_25px_rgba(var(--primary-rgb),0.5)] transition-all"
              >
                <ShoppingCart className="h-5 w-5" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </Link>
    </motion.div>
  );
}