// app/(dashboard)/saas/services/page.tsx
"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import { useServices, useServiceAccess, useToggleService } from "@/hooks/saas";
import { ServiceCard } from "@/components/saas/ServiceCard";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Search, Plus, Package, AlertCircle, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

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

export default function ServicesPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState("all");

  const { data: services, isLoading: isServicesLoading, error: servicesError } = useServices();
  const { data: serviceAccess, isLoading: isAccessLoading } = useServiceAccess();
  const toggleService = useToggleService();

  const isLoading = isServicesLoading || isAccessLoading;

  // تصفية الخدمات حسب البحث والتبويب
  const filteredServices = services?.filter((service) => {
    const matchesSearch = service.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          service.code.toLowerCase().includes(searchQuery.toLowerCase());
    if (activeTab === "all") return matchesSearch;
    if (activeTab === "active") return matchesSearch && service.is_active;
    if (activeTab === "inactive") return matchesSearch && !service.is_active;
    return matchesSearch;
  });

  if (isLoading) {
    return (
      <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto">
        <Skeleton className="h-48 w-full rounded-[2rem] bg-card/40" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-64 rounded-[2rem] bg-card/40 border border-white/5" />
          ))}
        </div>
      </div>
    );
  }

  if (servicesError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
        <div className="p-6 bg-destructive/10 rounded-full mb-6 border border-destructive/20">
          <AlertCircle className="h-16 w-16 text-destructive" />
        </div>
        <h2 className="text-3xl font-bold mb-2">فشل في تحميل الخدمات</h2>
        <p className="text-muted-foreground text-lg mb-8 max-w-md">
          {servicesError.message || "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."}
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
      className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative"
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
              <Package className="h-12 w-12 text-purple-500" />
            </div>
            <div>
              <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-purple-500 drop-shadow-sm">
                كتالوج الخدمات
              </h1>
              <p className="text-muted-foreground mt-2 text-lg md:text-xl font-medium">
                إدارة جميع الخدمات المتاحة على المنصة السيادية
              </p>
            </div>
          </div>
          <Button className="h-14 px-8 rounded-xl bg-purple-600 hover:bg-purple-500 font-bold shadow-[0_0_20px_rgba(139,92,246,0.3)]">
            <Plus className="ml-2 h-5 w-5" />
            خدمة جديدة
          </Button>
        </div>
      </motion.div>

      {/* شريط البحث والتبويبات */}
      <motion.div variants={itemVariants}>
        <div className="flex flex-col md:flex-row gap-4 bg-card/30 backdrop-blur-xl p-4 rounded-2xl border border-white/10">
          <div className="relative flex-1">
            <Search className="absolute right-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <Input
              placeholder="ابحث عن خدمة..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-12 bg-background/50 border-white/10 pr-12 rounded-xl focus:border-purple-500 focus:ring-1 focus:ring-purple-500/50 transition-colors"
            />
          </div>
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full md:w-auto">
            <TabsList className="bg-background/50 backdrop-blur-md border border-white/10 p-1 rounded-xl h-12 w-full md:w-auto">
              <TabsTrigger
                value="all"
                className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-bold"
              >
                الكل
              </TabsTrigger>
              <TabsTrigger
                value="active"
                className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-bold"
              >
                نشط
              </TabsTrigger>
              <TabsTrigger
                value="inactive"
                className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-bold"
              >
                غير نشط
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </motion.div>

      {/* قائمة الخدمات */}
      <motion.div variants={itemVariants}>
        {filteredServices?.length === 0 ? (
          <div className="text-center py-20 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-primary/20">
            <Package className="mx-auto h-16 w-16 text-primary/30 mb-4 animate-pulse" />
            <h3 className="text-2xl font-black text-foreground">
              {searchQuery ? "لا توجد خدمات تطابق البحث" : "لا توجد خدمات"}
            </h3>
            <p className="text-muted-foreground mt-2 text-lg">
              {searchQuery ? "جرب تغيير كلمات البحث" : "قم بإضافة خدمة جديدة لبدء البيع"}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredServices?.map((service, index) => {
              const access = serviceAccess?.find((a) => a.service_id === service.id);
              return (
                <ServiceCard
                  key={service.id}
                  service={service}
                  plans={[]} // سيتم جلبها من API منفصل
                  isActive={service.is_active}
                  onToggle={() => {
                    toggleService.mutate({
                      serviceId: service.id,
                      isActive: !service.is_active,
                    });
                  }}
                  isToggling={toggleService.isPending}
                  accessStatus={access}
                />
              );
            })}
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}