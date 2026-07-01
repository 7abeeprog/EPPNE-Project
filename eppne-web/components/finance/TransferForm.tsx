// components/finance/TransferForm.tsx
"use client";

import { useState, useMemo } from "react";
import { useTransfer } from "@/hooks/finance/useTransfer";
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
import { Loader2, Send, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { ConfirmationModal } from "./ConfirmationModal";

// ✅ حد المبلغ الكبير للتأكيد المزدوج
const LARGE_AMOUNT_THRESHOLD = 10000;

export function TransferForm({ balances }: { balances: Record<string, number> }) {
  const [receiverEmail, setReceiverEmail] = useState("");
  const [currency, setCurrency] = useState<string>("MR_USDT");
  const [amount, setAmount] = useState<string>("");
  const [notes, setNotes] = useState("");
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);

  const transferMutation = useTransfer();

  const amountNumber = parseFloat(amount) || 0;
  const isLargeAmount = amountNumber >= LARGE_AMOUNT_THRESHOLD;
  const hasSufficientBalance = balances[currency] >= amountNumber;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!receiverEmail.trim() || !amount || amountNumber <= 0) {
      toast.error("يرجى إدخال جميع البيانات المطلوبة.");
      return;
    }
    if (!hasSufficientBalance) {
      toast.error(`الرصيد غير كافٍ. الرصيد المتاح: ${balances[currency] || 0} ${currency}`);
      return;
    }
    // ✅ تأكيد مزدوج للمبالغ الكبيرة
    if (isLargeAmount) {
      setIsConfirmOpen(true);
      return;
    }
    executeTransfer();
  };

  const executeTransfer = () => {
    transferMutation.mutate(
      {
        receiver_email: receiverEmail.trim(),
        currency,
        amount: amountNumber,
        notes: notes.trim() || undefined,
      },
      {
        onSuccess: () => {
          setReceiverEmail("");
          setAmount("");
          setNotes("");
          setIsConfirmOpen(false);
        },
      }
    );
  };

  const maxBalance = balances[currency] || 0;

  // ✅ تحقق من صحة المبلغ
  const isAmountValid = amountNumber > 0 && amountNumber <= maxBalance;

  return (
    <>
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <Label className="font-bold text-lg text-foreground">البريد الإلكتروني للمستلم</Label>
          <Input
            type="email"
            placeholder="أدخل بريد المستلم..."
            value={receiverEmail}
            onChange={(e) => setReceiverEmail(e.target.value)}
            className="h-14 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner text-lg rtl:text-right"
            disabled={transferMutation.isPending}
          />
        </div>

        <div>
          <Label className="font-bold text-lg text-foreground">العملة</Label>
          <Select value={currency} onValueChange={setCurrency} disabled={transferMutation.isPending}>
            <SelectTrigger className="w-full h-14 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner text-lg">
              <SelectValue placeholder="اختر العملة" />
            </SelectTrigger>
            <SelectContent className="bg-card/90 backdrop-blur-xl border-white/10">
              {SUPPORTED_CURRENCIES.map((curr) => (
                <SelectItem key={curr} value={curr}>
                  {CURRENCY_LABELS[curr] || curr} ({balances[curr] || 0} متاح)
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label className="font-bold text-lg text-foreground">المبلغ</Label>
          <div className="relative mt-2">
            <Input
              type="number"
              step="0.00000001"
              min="0"
              placeholder="أدخل المبلغ..."
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className={`h-14 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner text-lg rtl:text-right pr-16 ${
                amount && !isAmountValid ? "border-destructive/50 focus:border-destructive" : ""
              }`}
              disabled={transferMutation.isPending}
            />
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-sm font-bold text-muted-foreground">
              {currency}
            </span>
          </div>
          {amount && !isAmountValid && (
            <p className="text-sm text-destructive font-bold mt-2">
              المبلغ غير صالح. الحد الأقصى: {maxBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })} {currency}
            </p>
          )}
          {isLargeAmount && isAmountValid && (
            <p className="text-sm text-amber-500 font-bold mt-2 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              هذا المبلغ كبير. سيُطلب منك تأكيد العملية.
            </p>
          )}
        </div>

        <div>
          <Label className="font-bold text-lg text-foreground">ملاحظات (اختياري)</Label>
          <Input
            placeholder="أضف ملاحظة..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="h-14 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner text-lg rtl:text-right"
            disabled={transferMutation.isPending}
          />
        </div>

        <Button
          type="submit"
          disabled={
            transferMutation.isPending ||
            !receiverEmail.trim() ||
            !amount ||
            !isAmountValid
          }
          className="w-full h-14 text-lg font-black rounded-xl bg-primary hover:bg-primary/90 shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.5)] transition-all hover:scale-[1.02]"
        >
          {transferMutation.isPending ? (
            <>
              <Loader2 className="ml-2 h-6 w-6 animate-spin" />
              جاري التحويل...
            </>
          ) : (
            <>
              <Send className="ml-2 h-6 w-6" />
              تحويل
            </>
          )}
        </Button>
      </form>

      {/* ✅ Confirmation Modal للمبالغ الكبيرة */}
      <ConfirmationModal
        isOpen={isConfirmOpen}
        onClose={() => setIsConfirmOpen(false)}
        onConfirm={executeTransfer}
        isProcessing={transferMutation.isPending}
        isWarning={isLargeAmount}
        title="تأكيد التحويل"
        description={`أنت على وشك تحويل مبلغ كبير إلى ${receiverEmail}`}
        details={[
          { label: "المستلم", value: receiverEmail },
          { label: "العملة", value: CURRENCY_LABELS[currency] || currency },
          { label: "المبلغ", value: `${amountNumber.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })} ${currency}`, highlight: true },
          { label: "الرصيد المتاح", value: `${maxBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })} ${currency}` },
          ...(notes ? [{ label: "ملاحظات", value: notes }] : []),
        ]}
        confirmLabel="تأكيد التحويل"
        cancelLabel="إلغاء"
      />
    </>
  );
}