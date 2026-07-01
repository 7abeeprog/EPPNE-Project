// app/(dashboard)/saas/feature-flags/page.tsx
"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import { useFeatureFlags, useToggleFeatureFlag } from "@/hooks/saas";
import { useServices } from "@/hooks/saas";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Settings, Search, AlertCircle, Sparkles, Flame, Zap, Shield } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: {
    opacity: 1,
    y: 0,
    transition: { type: "spring", stiffness: 300, damping: 24 },
  },
};

const featureIcons: Record<string, any> = {
  ai_recommendations: Sparkles,
  affiliate_10x: Flame,
  multi_store: Zap,
  advanced_certificates: Shield,
  product_scoped_affiliate: Zap,
  ai_content_generation: Sparkles,
  advanced_analytics: Flame,
};

const featureDescriptions: Record<string, string> = {
  ai_recommendations: "توصيات ذكاء اصطناعي مخصصة للمستخدمين",
  affiliate_10x: "نظام إحالة متعدد المستويات (حتى 10 مستويات)",
  multi_store: "إمكانية إنشاء متاجر متعددة تحت نفس المستأجر",
  advanced_certificates: "شهادات متقدمة مع توثيق على البلوكشين",
  product_scoped_affiliate: "إحالة مخصصة لكل منتج على حدة",
  ai_content_generation: "توليد محتوى تلقائي باستخدام الذكاء الاصطناعي",
  advanced_analytics: "تحليلات متقدمة مع تقارير تفصيلية",
};

export default function FeatureFlagsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedService, setSelectedService] = useState<string | undefined>();

  const { data: services, isLoading: isServicesLoading } = useServices();
  const { data: flags, isLoading: isFlagsLoading, error } = useFeatureFlags(selectedService);
  const toggleFeature = useToggleFeatureFlag();

  const isLoading = isServicesLoading || isFlagsLoading;

  // تصفية الميزات حسب البحث
  const filteredFlags = flags?.filter((flag) =>
    flag.feature_key.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (featureDescriptions[flag.feature_key]?.toLowerCase().includes(searchQuery.toLowerCase()) ?? false)
  );

  if (isLoading) {
    return (
      <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-5xl mx-auto">
        <Skeleton className="h-48 w-full rounded-[2rem] bg-card/40" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-32 rounded-[2rem] bg-card/40 border border-white/5" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
        <div className="p-6 bg-destructive/10 rounded-full mb-6 border border-destructive/20">
          <AlertCircle className="h-16 w-16 text-destructive" />
        </div>
        <h2 className="text-3xl font-bold mb-2">فشل في تحميل الميزات</h2>
        <p className="text-muted-foreground text-lg mb-8 max-w-md">
          {error.message || "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."}
        </p>
        <Button onClick={() => window.location.reload()} size="lg" className="rounded-xl h-14 px-8">
          إعادة المحاولة
        </Button>
      </div>
    );
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-5xl mx-auto relative"
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(139,92,246,0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* رأس الصفحة */}
      <motion.div
        variants={itemVariants}
        className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10"
      >
        <div className="absolute top-0 right-0 w-72 h-72 bg-purple-500/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse" />
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="flex items-center gap-6">
            <div className="p-4 bg-purple-500/10 rounded-2xl border border-purple-500/20 shadow-inner">
              <Settings className="h-12 w-12 text-purple-500" />
            </div>
            <div>
              <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-purple-500 drop-shadow-sm">
                الميزات التجريبية
              </h1>
              <p className="text-muted-foreground mt-2 text-lg md:text-xl font-medium">
                تفعيل أو تعطيل الميزات المتقدمة للخدمات المختلفة
              </p>
            </div>
          </div>
          <Badge className="bg-purple-500/20 text-purple-500 border-purple-500/30 font-bold px-4 py-2 text-sm">
            {flags?.filter(f => f.is_enabled).length || 0} ميزة مفعلة
          </Badge>
        </div>
      </motion.div>

      {/* شريط البحث والفلترة */}
      <motion.div variants={itemVariants}>
        <div className="flex flex-col md:flex-row gap-4 bg-card/30 backdrop-blur-xl p-4 rounded-2xl border border-white/10">
          <div className="relative flex-1">
            <Search className="absolute right-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <Input
              placeholder="ابحث عن ميزة..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-12 bg-background/50 border-white/10 pr-12 rounded-xl focus:border-purple-500 focus:ring-1 focus:ring-purple-500/50 transition-colors"
            />
          </div>
          <div className="flex gap-3">
            <Select
              value={selectedService}
              onValueChange={(val) => setSelectedService(val || undefined)}
            >
              <SelectTrigger className="w-48 h-12 bg-background/50 border-white/10 rounded-xl">
                <SelectValue placeholder="كل الخدمات" />
              </SelectTrigger>
              <SelectContent className="bg-card/90 backdrop-blur-xl border-white/10">
                <SelectItem value="">كل الخدمات</SelectItem>
                {services?.map((service) => (
                  <SelectItem key={service.id} value={service.code}>
                    {service.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </motion.div>

      {/* قائمة الميزات */}
      <motion.div variants={itemVariants}>
        {filteredFlags?.length === 0 ? (
          <div className="text-center py-20 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-primary/20">
            <Settings className="mx-auto h-16 w-16 text-primary/30 mb-4 animate-pulse" />
            <h3 className="text-2xl font-black text-foreground">
              {searchQuery ? "لا توجد ميزات تطابق البحث" : "لا توجد ميزات"}
            </h3>
            <p className="text-muted-foreground mt-2 text-lg">
              {searchQuery ? "جرب تغيير كلمات البحث" : "قم بتفعيل ميزات جديدة للخدمات"}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {filteredFlags?.map((flag, index) => {
              const service = services?.find((s) => s.id === flag.service_id);
              const Icon = featureIcons[flag.feature_key] || Settings;
              const description = featureDescriptions[flag.feature_key] || "ميزة متقدمة";

              return (
                <motion.div
                  key={`${flag.service_id}-${flag.feature_key}`}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <Card className={`border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] overflow-hidden transition-all hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] group ${
                    flag.is_enabled ? "border-primary/30" : ""
                  }`}>
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-4">
                          <div className={`p-3 rounded-xl border transition-colors ${
                            flag.is_enabled
                              ? "bg-primary/10 border-primary/20"
                              : "bg-background/50 border-white/10"
                          } group-hover:scale-110 transition-transform`}>
                            <Icon className={`h-6 w-6 ${
                              flag.is_enabled ? "text-primary" : "text-muted-foreground"
                            }`} />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <h4 className="font-black text-lg text-foreground">
                                {flag.feature_key.replace(/_/g, ' ')}
                              </h4>
                              {service && (
                                <Badge variant="outline" className="border-white/10 text-xs">
                                  {service.name}
                                </Badge>
                              )}
                            </div>
                            <p className="text-sm text-muted-foreground mt-1">
                              {description}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <Badge
                            className={`${
                              flag.is_enabled
                                ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                                : "bg-muted/10 text-muted-foreground border-white/10"
                            } border font-bold shrink-0`}
                          >
                            {flag.is_enabled ? "مفعّل" : "معطّل"}
                          </Badge>
                          <Switch
                            checked={flag.is_enabled}
                            onCheckedChange={(checked) => {
                              toggleFeature.mutate({
                                serviceCode: service?.code || "",
                                featureKey: flag.feature_key,
                                enabled: checked,
                              });
                            }}
                            disabled={toggleFeature.isPending}
                            className="data-[state=checked]:bg-primary"
                          />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}