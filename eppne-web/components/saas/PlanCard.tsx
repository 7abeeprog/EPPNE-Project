// components/saas/PlanCard.tsx
"use client";

import { motion } from "framer-motion";
import { ServicePlan } from "@/types/saas";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Edit2, Trash2, Check, X, Users, Package, Sparkles, Crown } from "lucide-react";

interface PlanCardProps {
  plan: ServicePlan;
  serviceName: string;
  onEdit: () => void;
  onDelete: () => void;
  index?: number;
}

const getPlanIcon = (code: string) => {
  if (code === "enterprise") return <Crown className="h-5 w-5 text-amber-500" />;
  if (code === "pro") return <Sparkles className="h-5 w-5 text-blue-500" />;
  return <Package className="h-5 w-5 text-primary" />;
};

const getPlanColor = (code: string) => {
  if (code === "enterprise") return "border-amber-500/30 bg-amber-500/5";
  if (code === "pro") return "border-blue-500/30 bg-blue-500/5";
  return "border-primary/20 bg-primary/5";
};

export function PlanCard({ plan, serviceName, onEdit, onDelete, index = 0 }: PlanCardProps) {
  const isPopular = plan.code === "pro";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, type: "spring", stiffness: 300, damping: 24 }}
      className="relative"
    >
      {isPopular && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-10">
          <Badge className="bg-primary text-primary-foreground px-4 py-1.5 rounded-full font-bold shadow-lg">
            الأكثر طلباً
          </Badge>
        </div>
      )}
      <Card className={`border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] overflow-hidden transition-all hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] group h-full ${getPlanColor(plan.code)}`}>
        <CardContent className="p-6 flex flex-col h-full">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-background/50 rounded-xl border border-white/10 group-hover:scale-110 transition-transform">
                {getPlanIcon(plan.code)}
              </div>
              <div>
                <h3 className="text-xl font-black text-foreground">{plan.name}</h3>
                <p className="text-xs text-muted-foreground">{serviceName}</p>
              </div>
            </div>
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="icon"
                onClick={onEdit}
                className="h-8 w-8 rounded-lg hover:bg-primary/10 text-muted-foreground hover:text-primary"
              >
                <Edit2 className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={onDelete}
                className="h-8 w-8 rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="mb-4">
            <div className="flex items-baseline gap-1">
              <span className="text-3xl font-black text-primary">{plan.price_monthly}</span>
              <span className="text-sm font-bold text-muted-foreground">{plan.currency}</span>
            </div>
            <p className="text-xs text-muted-foreground">شهرياً</p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              سنوياً: {plan.price_yearly} {plan.currency}
            </p>
          </div>

          <div className="flex-1 space-y-2 mb-4">
            <div className="flex items-center gap-2 text-sm">
              <Users className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">عدد المستخدمين: {plan.max_users}</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Package className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">المنتجات: {plan.max_products}</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Package className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">الكورسات: {plan.max_courses}</span>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 mb-4">
            {plan.features.slice(0, 3).map((feature) => (
              <Badge key={feature} variant="outline" className="border-white/10 text-xs">
                <Check className="h-3 w-3 ml-1 text-emerald-500" />
                {feature}
              </Badge>
            ))}
            {plan.features.length > 3 && (
              <Badge variant="outline" className="border-white/10 text-xs">
                +{plan.features.length - 3}
              </Badge>
            )}
          </div>

          <Button
            variant="outline"
            className="w-full h-12 rounded-xl border-white/10 hover:bg-primary/10 font-bold mt-auto"
          >
            عرض التفاصيل
          </Button>
        </CardContent>
      </Card>
    </motion.div>
  );
}