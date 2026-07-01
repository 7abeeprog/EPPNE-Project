// components/saas/ServiceCard.tsx
"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ServiceCatalog, ServiceAccessStatus } from "@/types/saas";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { CheckCircle, XCircle, Settings, Users, Package, Lock, Unlock, Loader2 } from "lucide-react";

interface ServiceCardProps {
  service: ServiceCatalog;
  plans: any[];
  isActive: boolean;
  onToggle?: () => void;
  isToggling?: boolean;
  accessStatus?: ServiceAccessStatus;
}

const iconMap: Record<string, any> = {
  academy: GraduationCap,
  commerce: Store,
  affiliate: Gift,
  logistics: Truck,
  hr: Users,
  ai: BrainCircuit,
};
// استخدام أيقونات بديلة إذا لم يتم استيرادها
const DefaultIcon = Package;

export function ServiceCard({ service, plans, isActive, onToggle, isToggling, accessStatus }: ServiceCardProps) {
  const Icon = iconMap[service.code] || DefaultIcon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 300, damping: 24 }}
    >
      <Card className={`border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] overflow-hidden transition-all hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] group ${
        !isActive ? "opacity-60" : ""
      }`}>
        <CardContent className="p-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-primary/10 rounded-xl border border-primary/20 group-hover:scale-110 transition-transform">
                <Icon className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h3 className="text-xl font-black text-foreground">{service.name}</h3>
                <p className="text-sm text-muted-foreground font-mono">{service.code}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {isActive ? (
                <Badge className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">
                  <CheckCircle className="h-3 w-3 ml-1" />
                  نشط
                </Badge>
              ) : (
                <Badge className="bg-muted/10 text-muted-foreground border-white/10">
                  <XCircle className="h-3 w-3 ml-1" />
                  غير نشط
                </Badge>
              )}
            </div>
          </div>

          <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
            {service.description || "خدمة سيادية متكاملة"}
          </p>

          {accessStatus && (
            <div className="flex items-center gap-2 mb-4 text-sm">
              {accessStatus.accessible ? (
                <span className="text-emerald-500 font-bold flex items-center gap-1">
                  <Unlock className="h-4 w-4" />
                  متاح للمستأجر
                </span>
              ) : (
                <span className="text-muted-foreground flex items-center gap-1">
                  <Lock className="h-4 w-4" />
                  غير متاح
                </span>
              )}
              {accessStatus.plan_name && (
                <Badge variant="outline" className="border-white/10 text-xs">
                  {accessStatus.plan_name}
                </Badge>
              )}
            </div>
          )}

          {plans && plans.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4">
              {plans.slice(0, 3).map((plan) => (
                <Badge key={plan.id} variant="outline" className="border-white/10 text-xs">
                  {plan.name} – {plan.price_monthly} {plan.currency}
                </Badge>
              ))}
              {plans.length > 3 && (
                <Badge variant="outline" className="border-white/10 text-xs">
                  +{plans.length - 3} أخرى
                </Badge>
              )}
            </div>
          )}

          <div className="flex items-center justify-between mt-4 pt-4 border-t border-border/50">
            <div className="flex items-center gap-3">
              <span className="text-sm font-bold text-muted-foreground">الحالة</span>
              <Switch
                checked={isActive}
                onCheckedChange={onToggle}
                disabled={isToggling}
                className="data-[state=checked]:bg-primary"
              />
              {isToggling && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
            </div>
            <Link href={`/saas/services/${service.id}`}>
              <Button variant="ghost" size="sm" className="rounded-xl hover:bg-primary/10 font-bold">
                <Settings className="h-4 w-4 ml-1" />
                إدارة
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}