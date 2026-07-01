// components/finance/BalanceCard.tsx
"use client";

import { motion } from "framer-motion";
import { CURRENCY_LABELS, CURRENCY_ICONS, CURRENCY_COLORS, SupportedCurrency } from "@/types/finance";
import { Card, CardContent } from "@/components/ui/card";

interface BalanceCardProps {
  currency: SupportedCurrency;
  balance: number;
  index?: number;
}

export function BalanceCard({ currency, balance, index = 0 }: BalanceCardProps) {
  const label = CURRENCY_LABELS[currency] || currency;
  const icon = CURRENCY_ICONS[currency] || '💰';
  const colorClass = CURRENCY_COLORS[currency] || 'text-primary';

  // ✅ استخدام decimal.js أو big.js للدقة المالية
  const formattedBalance = balance.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 8,
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, type: "spring", stiffness: 300, damping: 24 }}
      className="h-full"
    >
      <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-primary/40 hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] transition-all group h-full">
        <CardContent className="p-6 flex flex-col h-full">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-xl border border-primary/20 group-hover:scale-110 transition-transform">
                <span className="text-2xl">{icon}</span>
              </div>
              <div>
                <p className="text-sm font-bold text-muted-foreground">{label}</p>
                <p className="text-xs text-muted-foreground/70">{currency}</p>
              </div>
            </div>
            <div className="p-2 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
              <span className="text-xs font-black text-emerald-500">نشط</span>
            </div>
          </div>

          <div className="mt-auto">
            <p className={`text-3xl md:text-4xl font-black ${colorClass} drop-shadow-sm`}>
              {formattedBalance}
            </p>
            <p className="text-xs text-muted-foreground mt-1">رصيد متاح</p>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
