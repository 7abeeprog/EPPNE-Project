// app/(dashboard)/store/checkout/page.tsx
"use client";

import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { CheckoutForm } from "@/components/commerce/CheckoutForm";
import { Shield } from "lucide-react";

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

export default function CheckoutPage() {
  const searchParams = useSearchParams();
  const storeId = parseInt(searchParams.get('storeId') || '1');
  const affiliateCode = searchParams.get('affiliate') || undefined;

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-4xl mx-auto relative"
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(16,185,129,0.05),_transparent_80%)] pointer-events-none -z-10" />

      <motion.div
        variants={itemVariants}
        className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10"
      >
        <div className="absolute top-0 right-0 w-72 h-72 bg-emerald-500/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse" />
        <div className="flex items-center gap-6">
          <div className="p-4 bg-emerald-500/10 rounded-2xl border border-emerald-500/20 shadow-inner">
            <Shield className="h-12 w-12 text-emerald-500" />
          </div>
          <div>
            <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-emerald-500 drop-shadow-sm">
              إتمام الشراء
            </h1>
            <p className="text-muted-foreground mt-2 text-lg md:text-xl font-medium">
              تأكد من بياناتك وأكمل عملية الشراء بأمان
            </p>
          </div>
        </div>
      </motion.div>

      <motion.div variants={itemVariants}>
        <CheckoutForm storeId={storeId} affiliateCode={affiliateCode} />
      </motion.div>
    </motion.div>
  );
}