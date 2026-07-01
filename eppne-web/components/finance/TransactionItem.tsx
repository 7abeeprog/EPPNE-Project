// components/finance/TransactionItem.tsx
"use client";

import { motion } from "framer-motion";
import { Transaction } from "@/types/finance";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { CURRENCY_LABELS, CURRENCY_ICONS } from "@/types/finance";
import { ArrowUpRight, ArrowDownLeft, RefreshCw, Plus, CreditCard } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface TransactionItemProps {
  transaction: Transaction;
  index?: number;
}

const TX_TYPE_CONFIG = {
  TRANSFER: {
    icon: ArrowUpRight,
    label: "تحويل",
    className: "bg-blue-500/10 text-blue-500 border-blue-500/20",
  },
  SWAP_OUT: {
    icon: RefreshCw,
    label: "صرافة (خروج)",
    className: "bg-purple-500/10 text-purple-500 border-purple-500/20",
  },
  SWAP_IN: {
    icon: RefreshCw,
    label: "صرافة (دخول)",
    className: "bg-purple-500/10 text-purple-500 border-purple-500/20",
  },
  MINT: {
    icon: Plus,
    label: "سك عملات",
    className: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
  },
  COURSE_PURCHASE: {
    icon: CreditCard,
    label: "شراء كورس",
    className: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  },
  COMMERCE_PAYMENT: {
    icon: CreditCard,
    label: "دفع تجاري",
    className: "bg-rose-500/10 text-rose-500 border-rose-500/20",
  },
};

const STATUS_CONFIG = {
  COMPLETED: {
    label: "مكتمل",
    className: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
  },
  PENDING: {
    label: "قيد الانتظار",
    className: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  },
  FAILED: {
    label: "فشل",
    className: "bg-destructive/10 text-destructive border-destructive/20",
  },
  REVERSED: {
    label: "ملغى",
    className: "bg-muted/10 text-muted-foreground border-white/10",
  },
};

export function TransactionItem({ transaction, index = 0 }: TransactionItemProps) {
  const typeConfig = TX_TYPE_CONFIG[transaction.tx_type as keyof typeof TX_TYPE_CONFIG] || TX_TYPE_CONFIG.TRANSFER;
  const statusConfig = STATUS_CONFIG[transaction.status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.COMPLETED;
  const Icon = typeConfig.icon;
  const isOutgoing = transaction.tx_type === 'TRANSFER' || transaction.tx_type === 'SWAP_OUT';
  const amountColor = transaction.status === 'COMPLETED' ? (isOutgoing ? 'text-destructive' : 'text-emerald-500') : 'text-muted-foreground';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03, type: "spring", stiffness: 300, damping: 24 }}
    >
      <Card className="border-white/10 bg-card/40 backdrop-blur-md rounded-[2rem] hover:border-primary/40 hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] transition-all group">
        <CardContent className="p-4 md:p-6 flex items-center justify-between gap-4">
          <div className="flex items-center gap-4 min-w-0">
            <div className={`p-3 rounded-xl border ${typeConfig.className} shrink-0 group-hover:scale-110 transition-transform`}>
              <Icon className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-3 flex-wrap">
                <h4 className="font-bold text-foreground truncate">{typeConfig.label}</h4>
                <Badge className={`${statusConfig.className} border font-bold shrink-0`}>
                  {statusConfig.label}
                </Badge>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground mt-1">
                {/* ✅ إضافة Tooltip لعرض الـ tx_hash الكامل عند التمرير */}
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="font-mono bg-background/30 px-2 py-0.5 rounded border border-white/5 cursor-help">
                        {transaction.tx_hash.slice(0, 12)}...
                      </span>
                    </TooltipTrigger>
                    <TooltipContent className="bg-card/90 backdrop-blur-xl border-white/10 p-3 rounded-xl max-w-md">
                      <p className="text-xs font-mono break-all text-foreground">
                        {transaction.tx_hash}
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                {transaction.notes && (
                  <span className="truncate max-w-[150px]">• {transaction.notes}</span>
                )}
                <span>• {new Date(transaction.created_at).toLocaleString('ar-EG')}</span>
              </div>
            </div>
          </div>

          <div className="text-right shrink-0">
            <p className={`text-lg md:text-xl font-black ${amountColor}`}>
              {isOutgoing ? '-' : '+'}
              {transaction.amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })} {transaction.currency}
            </p>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}