// components/finance/WalletHeader.tsx
"use client";

import { motion } from "framer-motion";
import { Wallet, Shield, Eye, EyeOff, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

interface WalletHeaderProps {
  totalValue?: number;
  isLoading?: boolean;
  isHidden?: boolean;
  onToggleVisibility?: () => void;
}

export function WalletHeader({
  totalValue,
  isLoading = false,
  isHidden = false,
  onToggleVisibility,
}: WalletHeaderProps) {
  return (
    <div className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10">
      <div className="absolute top-0 right-0 w-72 h-72 bg-emerald-500/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse" />
      <div className="absolute bottom-0 left-0 w-48 h-48 bg-blue-500/10 blur-[100px] rounded-full pointer-events-none -z-10" />

      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-primary/10 rounded-2xl border border-primary/20 shadow-inner">
            <Wallet className="h-8 w-8 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl md:text-3xl font-black text-foreground">محفظتي السيادية</h1>
            <p className="text-muted-foreground text-sm">إدارة أصولك وعملاتك الرقمية</p>
          </div>
        </div>

        <div className="flex items-center gap-4 w-full md:w-auto">
          {isLoading ? (
            <div className="space-y-2 w-full md:w-48">
              <Skeleton className="h-6 w-32 bg-primary/10" />
              <Skeleton className="h-8 w-24 bg-primary/10" />
            </div>
          ) : (
            <div className="text-right w-full md:w-auto">
              <p className="text-sm font-bold text-muted-foreground">إجمالي الرصيد</p>
              <div className="flex items-center justify-end gap-3">
                <span className="text-3xl md:text-4xl font-black bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-emerald-600 drop-shadow-sm">
                  {isHidden ? '••••••' : `${totalValue?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'} MR_USDT`}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onToggleVisibility}
                  className="rounded-full hover:bg-primary/10 h-10 w-10"
                >
                  {isHidden ? <EyeOff className="h-5 w-5 text-muted-foreground" /> : <Eye className="h-5 w-5 text-muted-foreground" />}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}