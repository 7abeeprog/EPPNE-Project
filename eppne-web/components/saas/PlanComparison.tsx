// components/saas/PlanComparison.tsx
"use client";

import { motion } from "framer-motion";
import { ServicePlan, ServiceCatalog } from "@/types/saas";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Check, X, Crown, Sparkles } from "lucide-react";

interface PlanComparisonProps {
  plans: ServicePlan[];
  services: ServiceCatalog[];
}

export function PlanComparison({ plans, services }: PlanComparisonProps) {
  if (plans.length === 0) {
    return (
      <div className="text-center py-20 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-primary/20">
        <p className="text-muted-foreground text-lg">لا توجد خطط للمقارنة</p>
      </div>
    );
  }

  // جلب جميع الميزات الفريدة من جميع الخطط
  const allFeatures = Array.from(
    new Set(plans.flatMap((p) => p.features || []))
  );

  const getPlanIcon = (code: string) => {
    if (code === "enterprise") return <Crown className="h-5 w-5 text-amber-500" />;
    if (code === "pro") return <Sparkles className="h-5 w-5 text-blue-500" />;
    return null;
  };

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[800px]">
        <div className="grid grid-cols-[200px,1fr] gap-4">
          {/* الرأس */}
          <div className="p-4 flex items-center justify-end">
            <span className="font-bold text-lg text-muted-foreground">الميزات</span>
          </div>
          <div className="grid grid-cols-3 gap-4">
            {plans.map((plan) => {
              const service = services.find((s) => s.id === plan.service_id);
              const isPopular = plan.code === "pro";
              return (
                <div key={plan.id} className="text-center p-4">
                  <div className="flex items-center justify-center gap-2 mb-2">
                    {getPlanIcon(plan.code)}
                    <span className="font-black text-lg text-foreground">{plan.name}</span>
                  </div>
                  <p className="text-sm text-muted-foreground">{service?.name || "خدمة"}</p>
                  <div className="mt-2">
                    <span className="text-2xl font-black text-primary">{plan.price_monthly}</span>
                    <span className="text-sm text-muted-foreground"> {plan.currency}</span>
                  </div>
                  {isPopular && (
                    <Badge className="mt-2 bg-primary text-primary-foreground">الأكثر طلباً</Badge>
                  )}
                </div>
              );
            })}
          </div>

          {/* الصفوف */}
          {allFeatures.map((feature) => (
            <div key={feature} className="contents">
              <div className="p-4 flex items-center justify-end border-t border-border/50">
                <span className="text-sm font-medium text-muted-foreground">{feature}</span>
              </div>
              <div className="grid grid-cols-3 gap-4 border-t border-border/50">
                {plans.map((plan) => (
                  <div key={plan.id} className="p-4 flex items-center justify-center">
                    {plan.features?.includes(feature) ? (
                      <Check className="h-6 w-6 text-emerald-500" />
                    ) : (
                      <X className="h-6 w-6 text-destructive/50" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}

          {/* حدود الاستخدام */}
          <div className="p-4 flex items-center justify-end border-t border-border/50">
            <span className="text-sm font-medium text-muted-foreground">الحدود</span>
          </div>
          <div className="grid grid-cols-3 gap-4 border-t border-border/50">
            {plans.map((plan) => (
              <div key={plan.id} className="p-4 text-center text-sm">
                <div>👥 {plan.max_users} مستخدم</div>
                <div>📦 {plan.max_products} منتج</div>
                <div>📚 {plan.max_courses} كورس</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}