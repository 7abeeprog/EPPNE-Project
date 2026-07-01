// components/commerce/CheckoutForm.tsx
"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { useCheckout } from "@/hooks/commerce/useCheckout";
import { useCartStore } from "@/store/cart-store";
import { useWallet } from "@/hooks/finance/useWallet";
import { CommerceService } from "@/services/commerce.service";
import { Address } from "@/types/commerce";
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
import { Card, CardContent } from "@/components/ui/card";
import { Loader2, Wallet, Truck, CreditCard, User, MapPin, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { ConfirmationModal } from "@/components/finance/ConfirmationModal";
import { Skeleton } from "@/components/ui/skeleton";

// ✅ طرق الدفع المدعومة
const PAYMENT_METHODS = [
  { value: "WALLET_DEDUCTION", label: "المحفظة السيادية", icon: Wallet },
  { value: "AGENT", label: "الدفع عبر الوكيل", icon: User },
  { value: "VISA", label: "بطاقة ائتمان (فيزا)", icon: CreditCard },
  { value: "CASH_ON_DELIVERY", label: "الدفع عند الاستلام", icon: Truck },
];

interface CheckoutFormProps {
  storeId: number;
  affiliateCode?: string; // اختياري، سيتم استخراجه من الرابط إذا لم يُمرر
}

export function CheckoutForm({ storeId, affiliateCode: propAffiliateCode }: CheckoutFormProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  // ✅ الحصول على كود الإحالة من الرابط (مع إعطاء الأولوية للقيمة الممررة كـ prop)
  const affiliateCode = propAffiliateCode || searchParams.get('affiliate') || searchParams.get('ref');

  const { items, getTotalPrice, clearCart } = useCartStore();
  const { data: wallet, isLoading: isWalletLoading } = useWallet();
  const checkoutMutation = useCheckout();

  const [addresses, setAddresses] = useState<Address[]>([]);
  const [selectedAddressId, setSelectedAddressId] = useState<number | undefined>();
  const [settlementType, setSettlementType] = useState<string>("WALLET_DEDUCTION");
  const [isLoadingAddresses, setIsLoadingAddresses] = useState(true);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);

  // ✅ التحقق من الرصيد
  const totalPrice = getTotalPrice();
  const walletBalance = wallet?.balances?.["MR_USDT"] || 0;
  const hasSufficientBalance = settlementType === "WALLET_DEDUCTION" ? totalPrice <= walletBalance : true;
  const isFormValid = selectedAddressId && items.length > 0 && hasSufficientBalance;

  // ✅ جلب العناوين
  useEffect(() => {
    const fetchAddresses = async () => {
      try {
        const data = await CommerceService.getAddresses();
        setAddresses(data);
        const defaultAddress = data.find((a) => a.is_default);
        if (defaultAddress) setSelectedAddressId(defaultAddress.id);
      } catch (error) {
        toast.error("فشل جلب العناوين");
      } finally {
        setIsLoadingAddresses(false);
      }
    };
    fetchAddresses();
  }, []);

  // ✅ التحقق من الرصيد عند تغيير طريقة الدفع
  useEffect(() => {
    if (settlementType === "WALLET_DEDUCTION" && totalPrice > walletBalance) {
      toast.warning("رصيد المحفظة غير كافٍ. يرجى اختيار طريقة دفع أخرى.");
    }
  }, [settlementType, totalPrice, walletBalance]);

  const handleCheckout = () => {
    if (!isFormValid) {
      if (settlementType === "WALLET_DEDUCTION" && !hasSufficientBalance) {
        toast.error("رصيد المحفظة غير كافٍ لإتمام العملية");
      } else {
        toast.error("يرجى اختيار عنوان وطريقة دفع");
      }
      return;
    }
    setIsConfirmOpen(true);
  };

  const executeCheckout = () => {
    const payload = {
      store_id: storeId,
      items: items.map((item) => ({
        variant_id: item.variant_id,
        quantity: item.quantity,
      })),
      shipping_address_id: selectedAddressId,
      settlement_type: settlementType as any,
      affiliate_code: affiliateCode, // ✅ تمرير كود الإحالة (من prop أو الرابط)
      tenant_id: 1, // سيتم جلبه من الـ Auth
    };

    checkoutMutation.mutate(payload, {
      onSuccess: (data) => {
        setIsConfirmOpen(false);
        clearCart();
        router.push(`/store/orders`);
      },
    });
  };

  if (isLoadingAddresses || isWalletLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-64 w-full rounded-[2rem] bg-card/40" />
        <Skeleton className="h-20 w-full rounded-[2rem] bg-card/40" />
      </div>
    );
  }

  return (
    <>
      <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
        <CardContent className="p-6 md:p-8 space-y-6">
          {/* ✅ ملخص الطلب */}
          <div className="p-4 bg-primary/5 rounded-xl border border-primary/20">
            <h3 className="font-bold text-lg text-foreground mb-3">ملخص الطلب</h3>
            <div className="space-y-2">
              {items.map((item) => (
                <div key={item.variant_id} className="flex justify-between text-sm">
                  <span>
                    {item.variant?.product?.title || `منتج #${item.variant_id}`} × {item.quantity}
                  </span>
                  <span className="font-bold">
                    {((item.variant?.discount_price || item.variant?.price_mrusdt || 0) * item.quantity).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })} MR_USDT
                  </span>
                </div>
              ))}
              <div className="border-t border-border/50 pt-2 mt-2 flex justify-between font-bold text-lg">
                <span>الإجمالي</span>
                <span className="text-primary">{totalPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })} MR_USDT</span>
              </div>
            </div>
          </div>

          {/* ✅ الرصيد المتاح (للمحفظة) */}
          {settlementType === "WALLET_DEDUCTION" && (
            <div className={`p-4 rounded-xl border ${hasSufficientBalance ? "bg-emerald-500/5 border-emerald-500/20" : "bg-destructive/5 border-destructive/20"}`}>
              <div className="flex items-center justify-between">
                <span className="font-bold text-muted-foreground">الرصيد المتاح</span>
                <span className={`font-black ${hasSufficientBalance ? "text-emerald-500" : "text-destructive"}`}>
                  {walletBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })} MR_USDT
                </span>
              </div>
              {!hasSufficientBalance && (
                <p className="text-sm text-destructive font-bold mt-2 flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  الرصيد غير كافٍ. المطلوب: {totalPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })} MR_USDT
                </p>
              )}
            </div>
          )}

          {/* ✅ اختيار العنوان */}
          <div>
            <Label className="font-bold text-lg text-foreground flex items-center gap-2">
              <MapPin className="h-5 w-5 text-primary" />
              عنوان الشحن
            </Label>
            <Select
              value={selectedAddressId?.toString()}
              onValueChange={(val) => setSelectedAddressId(parseInt(val))}
            >
              <SelectTrigger className="w-full h-14 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner text-lg">
                <SelectValue placeholder="اختر عنوان..." />
              </SelectTrigger>
              <SelectContent className="bg-card/90 backdrop-blur-xl border-white/10">
                {addresses.map((addr) => (
                  <SelectItem key={addr.id} value={addr.id.toString()}>
                    {addr.street_line1}, {addr.city}, {addr.country}
                  </SelectItem>
                ))}
                <SelectItem value="new">➕ إضافة عنوان جديد</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* ✅ طريقة الدفع */}
          <div>
            <Label className="font-bold text-lg text-foreground flex items-center gap-2">
              <CreditCard className="h-5 w-5 text-primary" />
              طريقة الدفع
            </Label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-2">
              {PAYMENT_METHODS.map((method) => {
                const Icon = method.icon;
                const isSelected = settlementType === method.value;
                const isDisabled = method.value === "WALLET_DEDUCTION" && !hasSufficientBalance;

                return (
                  <button
                    key={method.value}
                    onClick={() => setSettlementType(method.value)}
                    disabled={isDisabled}
                    className={`p-4 rounded-xl border transition-all text-center ${
                      isSelected
                        ? "bg-primary/10 border-primary/50 shadow-[0_0_20px_rgba(var(--primary-rgb),0.15)]"
                        : isDisabled
                        ? "bg-muted/20 border-white/5 opacity-50 cursor-not-allowed"
                        : "bg-background/40 border-white/10 hover:border-primary/30"
                    }`}
                  >
                    <Icon className={`h-6 w-6 mx-auto mb-1 ${isSelected ? "text-primary" : "text-muted-foreground"}`} />
                    <p className={`text-xs font-bold ${isSelected ? "text-primary" : "text-muted-foreground"}`}>
                      {method.label}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* ✅ زر إتمام الشراء */}
          <Button
            onClick={handleCheckout}
            disabled={checkoutMutation.isPending || !isFormValid || items.length === 0}
            className="w-full h-14 text-lg font-black rounded-xl bg-primary hover:bg-primary/90 shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.5)] transition-all hover:scale-[1.02]"
          >
            {checkoutMutation.isPending ? (
              <>
                <Loader2 className="ml-2 h-6 w-6 animate-spin" />
                جاري إتمام الطلب...
              </>
            ) : (
              "إتمام الشراء"
            )}
          </Button>
        </CardContent>
      </Card>

      {/* ✅ Confirmation Modal */}
      <ConfirmationModal
        isOpen={isConfirmOpen}
        onClose={() => setIsConfirmOpen(false)}
        onConfirm={executeCheckout}
        isProcessing={checkoutMutation.isPending}
        isWarning={totalPrice > 10000}
        title="تأكيد الطلب"
        description="أنت على وشك إتمام عملية الشراء"
        details={[
          { label: "عدد المنتجات", value: items.reduce((acc, i) => acc + i.quantity, 0) },
          { label: "الإجمالي", value: `${totalPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 })} MR_USDT`, highlight: true },
          { label: "طريقة الدفع", value: PAYMENT_METHODS.find((m) => m.value === settlementType)?.label || settlementType },
        ]}
        confirmLabel="تأكيد الشراء"
        cancelLabel="إلغاء"
      />
    </>
  );
}