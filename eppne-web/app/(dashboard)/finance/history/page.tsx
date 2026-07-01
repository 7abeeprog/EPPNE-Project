// app/(dashboard)/finance/history/page.tsx
"use client";

import { motion } from "framer-motion";
import { History, ArrowLeft } from "lucide-react";
import { TransactionList } from "@/components/finance/TransactionList";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";

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

export default function HistoryPage() {
  const router = useRouter();

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative"
    >
      {/* خلفية نيون زجاجية */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(59,130,246,0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* رأس الصفحة */}
      <motion.div
        variants={itemVariants}
        className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10"
      >
        <div className="absolute top-0 right-0 w-72 h-72 bg-blue-500/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse" />
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="p-4 bg-blue-500/10 rounded-2xl border border-blue-500/20 shadow-inner">
              <History className="h-12 w-12 text-blue-500" />
            </div>
            <div>
              <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-blue-500 drop-shadow-sm">
                سجل المعاملات
              </h1>
              <p className="text-muted-foreground mt-2 text-lg md:text-xl font-medium">
                جميع عملياتك المالية في مكان واحد.
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            onClick={() => router.push('/finance/wallet')}
            className="rounded-xl hover:bg-primary/10"
          >
            <ArrowLeft className="ml-2 h-5 w-5" />
            العودة للمحفظة
          </Button>
        </div>
      </motion.div>

      {/* قائمة المعاملات */}
      <motion.div variants={itemVariants}>
        <TransactionList />
      </motion.div>
    </motion.div>
  );
}