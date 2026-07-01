// app/(dashboard)/finance/wallet/page.tsx
"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useWallet } from "@/hooks/finance/useWallet";
import { WalletHeader } from "@/components/finance/WalletHeader";
import { BalanceCard } from "@/components/finance/BalanceCard";
import { TransferForm } from "@/components/finance/TransferForm";
import { SwapForm } from "@/components/finance/SwapForm";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { SUPPORTED_CURRENCIES, CURRENCY_LABELS } from "@/types/finance";
import { Loader2, Send, RefreshCw, History } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

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

export default function WalletPage() {
  const { data: wallet, isLoading, refetch } = useWallet();
  const [isBalanceHidden, setIsBalanceHidden] = useState(false);

  const balances = wallet?.balances || {};
  const totalValue = Object.values(balances).reduce((acc, val) => acc + val, 0);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6">
        <Loader2 className="h-12 w-12 text-primary animate-spin mb-4" />
        <p className="text-muted-foreground">جاري تحميل بيانات المحفظة...</p>
      </div>
    );
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative"
    >
      {/* خلفية نيون زجاجية */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(16,185,129,0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* رأس المحفظة */}
      <motion.div variants={itemVariants}>
        <WalletHeader
          totalValue={totalValue}
          isLoading={isLoading}
          isHidden={isBalanceHidden}
          onToggleVisibility={() => setIsBalanceHidden(!isBalanceHidden)}
        />
      </motion.div>

      {/* الأرصدة */}
      <motion.div variants={itemVariants}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {SUPPORTED_CURRENCIES.map((currency, index) => (
            <BalanceCard
              key={currency}
              currency={currency}
              balance={balances[currency] || 0}
              index={index}
            />
          ))}
        </div>
      </motion.div>

      {/* العمليات المالية */}
      <motion.div variants={itemVariants}>
        <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
          <CardContent className="p-6 md:p-8">
            <Tabs defaultValue="transfer" className="w-full">
              <TabsList className="bg-background/50 backdrop-blur-md border border-white/10 p-1 rounded-2xl w-full md:w-auto">
                <TabsTrigger
                  value="transfer"
                  className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-bold"
                >
                  <Send className="ml-2 h-4 w-4" />
                  تحويل
                </TabsTrigger>
                <TabsTrigger
                  value="swap"
                  className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-bold"
                >
                  <RefreshCw className="ml-2 h-4 w-4" />
                  صرافة
                </TabsTrigger>
                <TabsTrigger
                  value="history"
                  className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-bold"
                >
                  <History className="ml-2 h-4 w-4" />
                  سجل المعاملات
                </TabsTrigger>
              </TabsList>

              <TabsContent value="transfer" className="mt-6">
                <TransferForm balances={balances} />
              </TabsContent>

              <TabsContent value="swap" className="mt-6">
                <SwapForm balances={balances} />
              </TabsContent>

              <TabsContent value="history" className="mt-6">
                <Link href="/finance/history">
                  <Button
                    variant="outline"
                    className="w-full h-14 rounded-xl border-primary/30 text-primary hover:bg-primary hover:text-white font-bold text-lg transition-all"
                  >
                    <History className="ml-2 h-5 w-5" />
                    عرض جميع المعاملات
                  </Button>
                </Link>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}