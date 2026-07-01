// app/(dashboard)/store/orders/page.tsx
"use client";

import { motion } from "framer-motion";
import { Package, History } from "lucide-react";
import { OrderList } from "@/components/commerce/OrderList";

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

export default function OrdersPage() {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-5xl mx-auto relative"
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(139,92,246,0.05),_transparent_80%)] pointer-events-none -z-10" />

      <motion.div
        variants={itemVariants}
        className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10"
      >
        <div className="absolute top-0 right-0 w-72 h-72 bg-purple-500/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse" />
        <div className="flex items-center gap-6">
          <div className="p-4 bg-purple-500/10 rounded-2xl border border-purple-500/20 shadow-inner">
            <History className="h-12 w-12 text-purple-500" />
          </div>
          <div>
            <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-purple-500 drop-shadow-sm">
              طلباتي
            </h1>
            <p className="text-muted-foreground mt-2 text-lg md:text-xl font-medium">
              تتبع جميع طلباتك السابقة والحالية
            </p>
          </div>
        </div>
      </motion.div>

      <motion.div variants={itemVariants}>
        <OrderList />
      </motion.div>
    </motion.div>
  );
}