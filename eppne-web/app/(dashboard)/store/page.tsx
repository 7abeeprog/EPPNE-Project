// app/(dashboard)/store/page.tsx
"use client";

import { motion } from "framer-motion";
import { ShoppingBag, Search, Filter } from "lucide-react";
import { ProductGrid } from "@/components/commerce/ProductGrid";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useState } from "react";

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: {
    opacity: 1,
    y: 0,
    transition: { type: "spring", stiffness: 300, damping: 24 },
  },
};

export default function StorePage() {
  const [searchQuery, setSearchQuery] = useState("");
  const storeId = 1; // سيتم جلبه من الـ Tenant

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative"
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(59,130,246,0.05),_transparent_80%)] pointer-events-none -z-10" />

      <motion.div
        variants={itemVariants}
        className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10"
      >
        <div className="absolute top-0 right-0 w-72 h-72 bg-blue-500/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse" />
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="flex items-center gap-6">
            <div className="p-4 bg-blue-500/10 rounded-2xl border border-blue-500/20 shadow-inner">
              <ShoppingBag className="h-12 w-12 text-blue-500" />
            </div>
            <div>
              <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-blue-500 drop-shadow-sm">
                المتجر السيادي
              </h1>
              <p className="text-muted-foreground mt-2 text-lg md:text-xl font-medium">
                اكتشف منتجاتنا السيادية واحصل على أفضل العروض
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 w-full md:w-auto">
            <div className="relative flex-1 md:w-64">
              <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
              <Input
                placeholder="ابحث عن منتج..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-12 bg-background/50 border-white/10 pr-12 rounded-xl focus:border-primary focus:ring-1 focus:ring-primary/50 transition-colors"
              />
            </div>
          </div>
        </div>
      </motion.div>

      <motion.div variants={itemVariants}>
        <ProductGrid storeId={storeId} />
      </motion.div>
    </motion.div>
  );
}