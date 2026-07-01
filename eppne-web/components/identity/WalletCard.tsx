// components/identity/WalletCard.tsx
"use client";

import { motion } from "framer-motion";
import { useWallet } from "@/hooks/identity/useWallet";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Wallet, Shield, ShieldAlert, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";

const CURRENCY_LABELS: Record<string, string> = {
  MR_POUND: "الجنيه السيادي",
  MR_USDT: "الدولار السيادي",
  MR7: "نبت 7",
  NBT: "نبت",
  MRX: "ماركس",
};

const CURRENCY_COLORS: Record<string, string> = {
  MR_POUND: "text-emerald-500",
  MR_USDT: "text-blue-500",
  MR7: "text-amber-500",
  NBT: "text-purple-500",
  MRX: "text-rose-500",
};

export function WalletCard() {
  const { data: wallet, isLoading, error } = useWallet();

  if (isLoading) {
    return (
      <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
        <CardContent className="p-6 md:p-8">
          <Skeleton className="h-8 w-32 mb-6 bg-primary/10" />
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-16 w-full rounded-xl bg-card/40" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
        <CardContent className="p-6 md:p-8 text-center">
          <ShieldAlert className="mx-auto h-12 w-12 text-destructive mb-4" />
          <p className="text-destructive font-bold">فشل في جلب بيانات المحفظة</p>
          <p className="text-muted-foreground mt-2">{error.message}</p>
        </CardContent>
      </Card>
    );
  }

  if (!wallet) {
    return (
      <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
        <CardContent className="p-6 md:p-8 text-center">
          <Wallet className="mx-auto h-12 w-12 text-muted-foreground/30 mb-4" />
          <p className="text-muted-foreground">لا توجد محفظة مرتبطة بهذا الحساب.</p>
        </CardContent>
      </Card>
    );
  }

  const balances = wallet.balances || {};
  const totalValue = Object.values(balances).reduce((acc, val) => acc + val, 0);

  return (
    <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
      <CardContent className="p-6 md:p-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-xl border border-primary/20">
              <Wallet className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h2 className="text-2xl font-black text-foreground">محفظتي</h2>
              <p className="text-sm text-muted-foreground">إدارة أرصدتك الرقمية</p>
            </div>
          </div>
          <Badge
            className={`${
              wallet.is_frozen
                ? "bg-destructive/10 text-destructive border-destructive/20"
                : "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
            } border font-bold`}
          >
            {wallet.is_frozen ? (
              <>
                <ShieldAlert className="h-3 w-3 ml-1" />
                مجمدة
              </>
            ) : (
              <>
                <Shield className="h-3 w-3 ml-1" />
                نشطة
              </>
            )}
          </Badge>
        </div>

        <div className="bg-primary/5 rounded-xl border border-primary/20 p-4 mb-6">
          <p className="text-sm font-bold text-muted-foreground">إجمالي الرصيد</p>
          <p className="text-3xl md:text-4xl font-black text-primary drop-shadow-sm">
            {totalValue.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 8 })} MR_USDT
          </p>
        </div>

        <div className="space-y-3">
          {Object.entries(balances).map(([currency, amount]) => (
            <div
              key={currency}
              className="flex items-center justify-between p-4 bg-background/40 rounded-xl border border-white/5 hover:border-primary/30 transition-all group"
            >
              <div>
                <p className="font-bold text-foreground">
                  {CURRENCY_LABELS[currency] || currency}
                </p>
                <p className="text-xs text-muted-foreground">{currency}</p>
              </div>
              <div className={`text-xl font-black ${CURRENCY_COLORS[currency] || "text-primary"}`}>
                {amount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 8 })}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}