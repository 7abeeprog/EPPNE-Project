// components/saas/SubscribeModal.tsx
"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useServices, usePlans, useSubscribe } from "@/hooks/saas";
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
import { Switch } from "@/components/ui/switch";
import { Loader2, X, Users, CreditCard, Crown } from "lucide-react";

interface SubscribeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function SubscribeModal({ isOpen, onClose, onSuccess }: SubscribeModalProps) {
  const [selectedServiceId, setSelectedServiceId] = useState<string>("");
  const [selectedPlanId, setSelectedPlanId] = useState<string>("");
  const [tenantId, setTenantId] = useState<string>("");
  const [autoRenew, setAutoRenew] = useState(true);
  const [paymentMethod, setPaymentMethod] = useState("WALLET");

  const { data: services } = useServices();
  const { data: plans } = usePlans(selectedServiceId ? parseInt(selectedServiceId) : undefined);
  const subscribe = useSubscribe();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPlanId || !tenantId) return;

    subscribe.mutate(
      {
        plan_id: parseInt(selectedPlanId),
        payment_method: paymentMethod,
        auto_renew: autoRenew,
      },
      {
        onSuccess: () => {
          onSuccess();
          onClose();
        },
      }
    );
  };

  const selectedPlan = plans?.find((p) => p.id === parseInt(selectedPlanId));
  const selectedService = services?.find((s) => s.id === parseInt(selectedServiceId));

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-md p-4 animate-in fade-in duration-300">
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="bg-card/90 backdrop-blur-3xl border border-primary/20 shadow-[0_0_50px_-10px_rgba(var(--primary-rgb),0.2)] rounded-[2.5rem] p-8 md:p-10 max-w-lg w-full"
          >
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-xl border border-primary/20">
                  <Users className="h-6 w-6 text-primary" />
                </div>
                <h3 className="text-2xl font-black text-foreground">اشتراك جديد</h3>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="rounded-full hover:bg-destructive/10"
                onClick={onClose}
              >
                <X className="h-5 w-5" />
              </Button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <Label className="font-bold text-lg text-foreground">الخدمة</Label>
                <Select value={selectedServiceId} onValueChange={setSelectedServiceId}>
                  <SelectTrigger className="w-full h-14 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner text-lg">
                    <SelectValue placeholder="اختر الخدمة..." />
                  </SelectTrigger>
                  <SelectContent className="bg-card/90 backdrop-blur-xl border-white/10">
                    {services?.map((service) => (
                      <SelectItem key={service.id} value={service.id.toString()}>
                        {service.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label className="font-bold text-lg text-foreground">الخطة</Label>
                <Select
                  value={selectedPlanId}
                  onValueChange={setSelectedPlanId}
                  disabled={!selectedServiceId}
                >
                  <SelectTrigger className="w-full h-14 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner text-lg">
                    <SelectValue placeholder="اختر الخطة..." />
                  </SelectTrigger>
                  <SelectContent className="bg-card/90 backdrop-blur-xl border-white/10">
                    {plans?.map((plan) => (
                      <SelectItem key={plan.id} value={plan.id.toString()}>
                        {plan.name} – {plan.price_monthly} {plan.currency}
                        {plan.code === "enterprise" && " 👑"}
                        {plan.code === "pro" && " ⭐"}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {selectedPlan && (
                  <div className="mt-2 p-3 bg-primary/5 rounded-xl border border-primary/20">
                    <p className="text-sm text-muted-foreground">
                      <span className="font-bold">{selectedPlan.name}</span> – حتى {selectedPlan.max_users} مستخدم، {selectedPlan.max_products} منتج
                    </p>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {selectedPlan.features.slice(0, 3).map((feature) => (
                        <span key={feature} className="text-xs bg-background/50 px-2 py-1 rounded border border-white/5">
                          ✓ {feature}
                        </span>
                      ))}
                      {selectedPlan.features.length > 3 && (
                        <span className="text-xs text-muted-foreground">+{selectedPlan.features.length - 3}</span>
                      )}
                    </div>
                  </div>
                )}
              </div>

              <div>
                <Label className="font-bold text-lg text-foreground">معرف المستأجر</Label>
                <Input
                  type="number"
                  placeholder="أدخل معرف المستأجر..."
                  value={tenantId}
                  onChange={(e) => setTenantId(e.target.value)}
                  className="h-14 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner text-lg"
                  required
                />
              </div>

              <div>
                <Label className="font-bold text-lg text-foreground">طريقة الدفع</Label>
                <Select value={paymentMethod} onValueChange={setPaymentMethod}>
                  <SelectTrigger className="w-full h-14 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner text-lg">
                    <SelectValue placeholder="اختر طريقة الدفع..." />
                  </SelectTrigger>
                  <SelectContent className="bg-card/90 backdrop-blur-xl border-white/10">
                    <SelectItem value="WALLET">المحفظة السيادية</SelectItem>
                    <SelectItem value="VISA">بطاقة ائتمان</SelectItem>
                    <SelectItem value="AGENT">الدفع عبر الوكيل</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center justify-between p-4 bg-background/40 rounded-xl border border-white/5">
                <div>
                  <p className="font-bold text-foreground">التجديد التلقائي</p>
                  <p className="text-sm text-muted-foreground">سيتم تجديد الاشتراك تلقائياً في نهاية المدة</p>
                </div>
                <Switch
                  checked={autoRenew}
                  onCheckedChange={setAutoRenew}
                  className="data-[state=checked]:bg-primary"
                />
              </div>

              <Button
                type="submit"
                disabled={subscribe.isPending || !selectedPlanId || !tenantId}
                className="w-full h-14 text-lg font-black rounded-xl bg-primary hover:bg-primary/90 shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.5)] transition-all hover:scale-[1.02]"
              >
                {subscribe.isPending ? (
                  <>
                    <Loader2 className="ml-2 h-6 w-6 animate-spin" />
                    جاري الاشتراك...
                  </>
                ) : (
                  <>
                    <Crown className="ml-2 h-6 w-6" />
                    تأكيد الاشتراك
                  </>
                )}
              </Button>
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}