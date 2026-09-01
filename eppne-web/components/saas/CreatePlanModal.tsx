// components/saas/CreatePlanModal.tsx
"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
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
import { Loader2, X, Package } from "lucide-react";
import type { ServiceCatalog, ServicePlan } from "@/types/saas";

interface CreatePlanModalProps {
  isOpen: boolean;
  onClose: () => void;
  plan: ServicePlan | null;
  services: ServiceCatalog[];
  onSubmit: (data: Omit<ServicePlan, "id" | "created_at" | "updated_at">) => void;
  isSubmitting: boolean;
}

const emptyForm = {
  service_id: "",
  name: "",
  code: "",
  price_monthly: "",
  price_yearly: "",
  currency: "MR_USDT",
  features: "",
  max_users: "10",
  max_products: "50",
  max_courses: "20",
};

export function CreatePlanModal({ isOpen, onClose, plan, services, onSubmit, isSubmitting }: CreatePlanModalProps) {
  const [form, setForm] = useState(emptyForm);

  useEffect(() => {
    if (plan) {
      setForm({
        service_id: String(plan.service_id),
        name: plan.name,
        code: plan.code,
        price_monthly: String(plan.price_monthly),
        price_yearly: String(plan.price_yearly),
        currency: plan.currency,
        features: plan.features.join(", "),
        max_users: String(plan.max_users),
        max_products: String(plan.max_products),
        max_courses: String(plan.max_courses),
      });
    } else {
      setForm(emptyForm);
    }
  }, [plan, isOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.service_id || !form.name || !form.code) return;
    onSubmit({
      service_id: parseInt(form.service_id),
      name: form.name,
      code: form.code,
      price_monthly: parseFloat(form.price_monthly) || 0,
      price_yearly: parseFloat(form.price_yearly) || 0,
      currency: form.currency,
      features: form.features.split(",").map((f) => f.trim()).filter(Boolean),
      max_users: parseInt(form.max_users) || 0,
      max_products: parseInt(form.max_products) || 0,
      max_courses: parseInt(form.max_courses) || 0,
      is_active: plan?.is_active ?? true,
    });
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-md p-4 animate-in fade-in duration-300">
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="bg-card/90 backdrop-blur-3xl border border-primary/20 shadow-[0_0_50px_-10px_rgba(var(--primary-rgb),0.2)] rounded-[2.5rem] p-8 md:p-10 max-w-lg w-full max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-xl border border-primary/20">
                  <Package className="h-6 w-6 text-primary" />
                </div>
                <h3 className="text-2xl font-black text-foreground">{plan ? "تعديل الخطة" : "خطة جديدة"}</h3>
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

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label className="font-bold text-foreground">الخدمة</Label>
                <Select value={form.service_id} onValueChange={(v) => setForm({ ...form, service_id: v })}>
                  <SelectTrigger className="w-full h-12 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner">
                    <SelectValue placeholder="اختر الخدمة..." />
                  </SelectTrigger>
                  <SelectContent className="bg-card/90 backdrop-blur-xl border-white/10">
                    {services.map((service) => (
                      <SelectItem key={service.id} value={service.id.toString()}>
                        {service.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="font-bold text-foreground">اسم الخطة</Label>
                  <Input
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    className="h-12 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner"
                    required
                  />
                </div>
                <div>
                  <Label className="font-bold text-foreground">الكود</Label>
                  <Input
                    value={form.code}
                    onChange={(e) => setForm({ ...form, code: e.target.value })}
                    placeholder="pro، enterprise..."
                    className="h-12 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="font-bold text-foreground">السعر الشهري</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={form.price_monthly}
                    onChange={(e) => setForm({ ...form, price_monthly: e.target.value })}
                    className="h-12 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner"
                    required
                  />
                </div>
                <div>
                  <Label className="font-bold text-foreground">السعر السنوي</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={form.price_yearly}
                    onChange={(e) => setForm({ ...form, price_yearly: e.target.value })}
                    className="h-12 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner"
                    required
                  />
                </div>
              </div>

              <div>
                <Label className="font-bold text-foreground">الميزات (مفصولة بفاصلة)</Label>
                <Input
                  value={form.features}
                  onChange={(e) => setForm({ ...form, features: e.target.value })}
                  placeholder="ميزة 1, ميزة 2, ميزة 3"
                  className="h-12 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <Label className="font-bold text-foreground text-sm">الحد الأقصى للمستخدمين</Label>
                  <Input
                    type="number"
                    value={form.max_users}
                    onChange={(e) => setForm({ ...form, max_users: e.target.value })}
                    className="h-12 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner"
                  />
                </div>
                <div>
                  <Label className="font-bold text-foreground text-sm">الحد الأقصى للمنتجات</Label>
                  <Input
                    type="number"
                    value={form.max_products}
                    onChange={(e) => setForm({ ...form, max_products: e.target.value })}
                    className="h-12 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner"
                  />
                </div>
                <div>
                  <Label className="font-bold text-foreground text-sm">الحد الأقصى للكورسات</Label>
                  <Input
                    type="number"
                    value={form.max_courses}
                    onChange={(e) => setForm({ ...form, max_courses: e.target.value })}
                    className="h-12 mt-2 bg-background/50 border-white/10 rounded-xl focus:border-primary shadow-inner"
                  />
                </div>
              </div>

              <Button
                type="submit"
                disabled={isSubmitting || !form.service_id || !form.name || !form.code}
                className="w-full h-14 text-lg font-black rounded-xl bg-primary hover:bg-primary/90 shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.5)] transition-all hover:scale-[1.02]"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="ml-2 h-6 w-6 animate-spin" />
                    جارٍ الحفظ...
                  </>
                ) : (
                  <>
                    <Package className="ml-2 h-6 w-6" />
                    {plan ? "حفظ التعديلات" : "إنشاء الخطة"}
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
