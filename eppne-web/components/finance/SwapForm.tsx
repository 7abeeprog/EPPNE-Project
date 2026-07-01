// components/finance/SwapForm.tsx
"use client";

import { useState, useEffect, useMemo } from "react";
import { useSwap } from "@/hooks/finance/useSwap";
import { useWallet } from "@/hooks/finance/useWallet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SUPPORTED_CURRENCIES, CURRENCY_LABELS } from "@/types/finance";
import { Loader2, RefreshCw, AlertTriangle, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { ConfirmationModal } from "./ConfirmationModal";
import { Skeleton } from "@/components/ui/skeleton";

// ✅ تحديد العملات المدعومة للصرافة (تجنب نقاط الولاء)
const SWAP_CURRENCIES = SUPPORTED_CURRENCIES.filter(c => c !== 'LOYALTY_POINTS');

export function SwapForm({ balances }: { balances: Record<string, number> }) {
  const [fromCurrency, setFromCurrency] = useState<string>("MR_USDT");
  const [toCurrency, setToCurrency] = useState<string>("MR_POUND");
  const [amountIn, setAmountIn] = useState<string>("");
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [rateError, setRateError] = useState<string | null>(null);

  const { data: wallet, isLoading: isWalletLoading, refetch } = useWallet();
  const swapMutation = useSwap();

  const amountNumber = parseFloat(amountIn) || 0;
  const maxBalance = balances[fromCurrency] || 0;
  const hasSufficientBalance = amountNumber > 0 && amountNumber <= maxBalance;

  // ✅ حساب سعر الصرف الفوري (مع معالجة الأخطاء)
  const [exchangeRate, setExchangeRate] = useState<number | null>(null);
  const [estimatedAmountOut, setEstimatedAmountOut] = useState<number | null>(null);
  const [isLoadingRate, setIsLoadingRate] = useState(false);

  // ✅ جلب سعر الصرف عند تغيير العملات أو المبلغ
  useEffect(() => {
    const fetchRate = async () => {
      if (!fromCurrency || !toCurrency || fromCurrency === toCurrency) {
        setExchangeRate(null);
        setEstimatedAmountOut(null);
        setRateError(null);
        return;
      }

      setIsLoadingRate(true);
      setRateError(null);

      try {
        const response = await fetch(`/api/finance/exchange-rate?from=${fromCurrency}&to=${toCurrency}`);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        
        if (!data.rate || data.rate <= 0) {
          throw new Error("سعر الصرف غير صالح");
        }

        setExchangeRate(data.rate);
        if (amountNumber > 0) {
          const estimated = amountNumber * data.rate;
          setEstimatedAmountOut(parseFloat(estimated.toFixed(8)));
        } else {
          setEstimatedAmountOut(null);
        }
      } catch (error) {
        console.error('Failed to fetch exchange rate:', error);
        setExchangeRate(null);
        setEstimatedAmountOut(null);
        // ✅ عرض رسالة خطأ واضحة للمستخدم
        setRateError("تعذر الوصول لأسعار الصرف، يرجى المحاولة لاحقاً");
        toast.error("تعذر الوصول لأسعار الصرف. سيتم استخدام سعر الصرف الافتراضي.");
      } finally {
        setIsLoadingRate(false);
      }
    };

    // ✅ استخدام setTimeout لتأخير جلب السعر أثناء الكتابة (Debounce)
    const timeoutId = setTimeout(fetchRate, 500);
    return () => clearTimeout(timeoutId);
  }, [fromCurrency, toCurrency, amountNumber]);

  // ✅ التحقق من صحة العملات
  const isValidSwap = fromCurrency !== toCurrency && hasSufficientBalance && exchangeRate !== null && exchangeRate > 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // ✅ التحقق من وجود خطأ في السعر
    if (rateError) {
      toast.error("لا يمكن تنفيذ الصرافة حالياً. يرجى المحاولة لاحقاً.");
      return;
    }

    if (!isValidSwap) {
      toast.error("يرجى التحقق من العملات والمبلغ المدخل.");
      return;
    }
    setIsConfirmOpen(true);
  };

  const executeSwap = () => {
    swapMutation.mutate(
      {
        from_currency: fromCurrency,
        to_currency: toCurrency,
        amount_in: amountNumber,
      },
      {
        onSuccess: () => {
          setAmountIn("");
          setIsConfirmOpen(false);
          refetch();
        },
      }
    );
  };

  const isLargeAmount = amountNumber >= 10000;

  return (
    <>
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <Label className="font-bold text-lg text-foreground">من العملة</Label>
            <Select
              value={fromCurrency}
              onValueChange={setFromCurrency}
              disabled={swapMutation.isPending}
            >
              <SelectTrigger className="w-full h-14 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner text-lg">
                <SelectValue placeholder="اختر العملة" />
              </SelectTrigger>
              <SelectContent className="bg-card/90 backdrop-blur-xl border-white/10">
                {SWAP_CURRENCIES.map((curr) => (
                  <SelectItem key={curr} value={curr}>
                    {CURRENCY_LABELS[curr] || curr} ({balances[curr] || 0} متاح)
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className="font-bold text-lg text-foreground">إلى العملة</Label>
            <Select
              value={toCurrency}
              onValueChange={setToCurrency}
              disabled={swapMutation.isPending}
            >
              <SelectTrigger className="w-full h-14 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner text-lg">
                <SelectValue placeholder="اختر العملة" />
              </SelectTrigger>
              <SelectContent className="bg-card/90 backdrop-blur-xl border-white/10">
                {SWAP_CURRENCIES.filter(c => c !== fromCurrency).map((curr) => (
                  <SelectItem key={curr} value={curr}>
                    {CURRENCY_LABELS[curr] || curr}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div>
          <Label className="font-bold text-lg text-foreground">المبلغ المراد صرافته</Label>
          <div className="relative mt-2">
            <Input
              type="number"
              step="0.00000001"
              min="0"
              placeholder="أدخل المبلغ..."
              value={amountIn}
              onChange={(e) => setAmountIn(e.target.value)}
              className={`h-14 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner text-lg rtl:text-right pr-16 ${
                amountIn && !hasSufficientBalance ? "border-destructive/50 focus:border-destructive" : ""
              }`}
              disabled={swapMutation.isPending}
            />
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-sm font-bold text-muted-foreground">
              {fromCurrency}
            </span>
          </div>
          {amountIn && !hasSufficientBalance && (
            <p className="text-sm text-destructive font-bold mt-2">
              الرصيد غير كافٍ. الحد الأقصى: {maxBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })} {fromCurrency}
            </p>
          )}
        </div>

        {/* ✅ عرض سعر الصرف الفوري مع معالجة الأخطاء */}
        {fromCurrency !== toCurrency && amountNumber > 0 && (
          <div className={`p-4 rounded-xl border ${rateError ? 'bg-destructive/5 border-destructive/20' : 'bg-primary/5 border-primary/20'}`}>
            <div className="flex justify-between items-center">
              <span className="text-sm font-bold text-muted-foreground">سعر الصرف الفوري</span>
              {isLoadingRate ? (
                <Skeleton className="h-6 w-32 bg-primary/10" />
              ) : rateError ? (
                <div className="flex items-center gap-2 text-destructive">
                  <AlertCircle className="h-5 w-5" />
                  <span className="text-sm font-bold">{rateError}</span>
                </div>
              ) : exchangeRate ? (
                <span className="text-lg font-black text-primary">
                  1 {fromCurrency} = {exchangeRate.toFixed(6)} {toCurrency}
                </span>
              ) : (
                <span className="text-sm font-bold text-muted-foreground">جاري التحميل...</span>
              )}
            </div>
            {estimatedAmountOut !== null && !isLoadingRate && !rateError && (
              <div className="flex justify-between items-center mt-2 pt-2 border-t border-border/50">
                <span className="text-sm font-bold text-muted-foreground">المبلغ المتوقع</span>
                <span className="text-xl font-black text-emerald-500">
                  {estimatedAmountOut.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })} {toCurrency}
                </span>
              </div>
            )}
          </div>
        )}

        <Button
          type="submit"
          disabled={
            swapMutation.isPending ||
            !isValidSwap ||
            fromCurrency === toCurrency ||
            exchangeRate === null ||
            exchangeRate <= 0 ||
            !!rateError
          }
          className="w-full h-14 text-lg font-black rounded-xl bg-primary hover:bg-primary/90 shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.5)] transition-all hover:scale-[1.02]"
        >
          {swapMutation.isPending ? (
            <>
              <Loader2 className="ml-2 h-6 w-6 animate-spin" />
              جاري الصرافة...
            </>
          ) : (
            <>
              <RefreshCw className="ml-2 h-6 w-6" />
              صرافة
            </>
          )}
        </Button>

        {/* ✅ عرض رسالة الخطأ أسفل الزر */}
        {rateError && (
          <p className="text-sm text-destructive font-bold text-center flex items-center justify-center gap-2">
            <AlertCircle className="h-4 w-4" />
            {rateError}
          </p>
        )}
      </form>

      {/* ✅ Confirmation Modal للصرافة */}
      <ConfirmationModal
        isOpen={isConfirmOpen}
        onClose={() => setIsConfirmOpen(false)}
        onConfirm={executeSwap}
        isProcessing={swapMutation.isPending}
        isWarning={isLargeAmount}
        title="تأكيد الصرافة"
        description={`أنت على وشك صرافة ${fromCurrency} إلى ${toCurrency}`}
        details={[
          { label: "من العملة", value: CURRENCY_LABELS[fromCurrency] || fromCurrency },
          { label: "إلى العملة", value: CURRENCY_LABELS[toCurrency] || toCurrency },
          { label: "المبلغ المرسل", value: `${amountNumber.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })} ${fromCurrency}` },
          { label: "سعر الصرف", value: exchangeRate ? `${exchangeRate.toFixed(6)}` : 'غير متاح' },
          { label: "المبلغ المستلم", value: estimatedAmountOut ? `${estimatedAmountOut.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })} ${toCurrency}` : 'جاري الحساب...', highlight: true },
        ]}
        confirmLabel="تأكيد الصرافة"
        cancelLabel="إلغاء"
      />
    </>
  );
}