// app/(dashboard)/saas/plans/page.tsx
"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import { usePlans, useCreatePlan, useUpdatePlan, useDeletePlan } from "@/hooks/saas";
import { useServices } from "@/hooks/saas";
import { PlanCard } from "@/components/saas/PlanCard";
import { PlanComparison } from "@/components/saas/PlanComparison";
import { CreatePlanModal } from "@/components/saas/CreatePlanModal";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Search, Plus, Package, AlertCircle, Filter } from "lucide-react";
import { Input } from "@/components/ui/input";
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

export default function PlansPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedServiceId, setSelectedServiceId] = useState<number | undefined>();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingPlan, setEditingPlan] = useState<any>(null);
  const [viewMode, setViewMode] = useState<"grid" | "comparison">("grid");

  const { data: services, isLoading: isServicesLoading } = useServices();
  const { data: plans, isLoading: isPlansLoading, error: plansError } = usePlans(selectedServiceId);
  const createPlan = useCreatePlan();
  const updatePlan = useUpdatePlan();
  const deletePlan = useDeletePlan();

  const isLoading = isServicesLoading || isPlansLoading;

  // تصفية الخطط حسب البحث
  const filteredPlans = plans?.filter((plan) =>
    plan.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    plan.code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (isLoading) {
    return (
      <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto">
        <Skeleton className="h-48 w-full rounded-[2rem] bg-card/40" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-96 rounded-[2rem] bg-card/40 border border-white/5" />
          ))}
        </div>
      </div>
    );
  }

  if (plansError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
        <div className="p-6 bg-destructive/10 rounded-full mb-6 border border-destructive/20">
          <AlertCircle className="h-16 w-16 text-destructive" />
        </div>
        <h2 className="text-3xl font-bold mb-2">فشل في تحميل الخطط</h2>
        <p className="text-muted-foreground text-lg mb-8 max-w-md">
          {plansError.message || "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."}
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
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(16,185,129,0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* رأس الصفحة */}
      <motion.div
        variants={itemVariants}
        className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10"
      >
        <div className="absolute top-0 right-0 w-72 h-72 bg-emerald-500/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse" />
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="flex items-center gap-6">
            <div className="p-4 bg-emerald-500/10 rounded-2xl border border-emerald-500/20 shadow-inner">
              <Package className="h-12 w-12 text-emerald-500" />
            </div>
            <div>
              <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-emerald-500 drop-shadow-sm">
                خطط التسعير
              </h1>
              <p className="text-muted-foreground mt-2 text-lg md:text-xl font-medium">
                إدارة خطط التسعير للخدمات المختلفة
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={() => setViewMode(viewMode === "grid" ? "comparison" : "grid")}
              className="h-14 px-6 rounded-xl border-white/10 hover:bg-primary/10 font-bold"
            >
              {viewMode === "grid" ? "مقارنة الخطط" : "عرض شبكي"}
            </Button>
            <Button
              onClick={() => {
                setEditingPlan(null);
                setIsModalOpen(true);
              }}
              className="h-14 px-8 rounded-xl bg-emerald-600 hover:bg-emerald-500 font-bold shadow-[0_0_20px_rgba(16,185,129,0.3)]"
            >
              <Plus className="ml-2 h-5 w-5" />
              خطة جديدة
            </Button>
          </div>
        </div>
      </motion.div>

      {/* شريط البحث والفلترة */}
      <motion.div variants={itemVariants}>
        <div className="flex flex-col md:flex-row gap-4 bg-card/30 backdrop-blur-xl p-4 rounded-2xl border border-white/10">
          <div className="relative flex-1">
            <Search className="absolute right-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <Input
              placeholder="ابحث عن خطة..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-12 bg-background/50 border-white/10 pr-12 rounded-xl focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500/50 transition-colors"
            />
          </div>
          <div className="flex gap-3">
            <Select
              value={selectedServiceId?.toString()}
              onValueChange={(val) => setSelectedServiceId(val ? parseInt(val) : undefined)}
            >
              <SelectTrigger className="w-48 h-12 bg-background/50 border-white/10 rounded-xl">
                <SelectValue placeholder="كل الخدمات" />
              </SelectTrigger>
              <SelectContent className="bg-card/90 backdrop-blur-xl border-white/10">
                <SelectItem value="">كل الخدمات</SelectItem>
                {services?.map((service) => (
                  <SelectItem key={service.id} value={service.id.toString()}>
                    {service.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </motion.div>

      {/* عرض الخطط */}
      <motion.div variants={itemVariants}>
        {filteredPlans?.length === 0 ? (
          <div className="text-center py-20 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-primary/20">
            <Package className="mx-auto h-16 w-16 text-primary/30 mb-4 animate-pulse" />
            <h3 className="text-2xl font-black text-foreground">
              {searchQuery ? "لا توجد خطط تطابق البحث" : "لا توجد خطط"}
            </h3>
            <p className="text-muted-foreground mt-2 text-lg">
              {searchQuery ? "جرب تغيير كلمات البحث" : "قم بإضافة خطة جديدة للخدمات"}
            </p>
          </div>
        ) : viewMode === "grid" ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredPlans?.map((plan, index) => {
              const service = services?.find((s) => s.id === plan.service_id);
              return (
                <PlanCard
                  key={plan.id}
                  plan={plan}
                  serviceName={service?.name || "خدمة غير معروفة"}
                  onEdit={() => {
                    setEditingPlan(plan);
                    setIsModalOpen(true);
                  }}
                  onDelete={() => {
                    if (confirm(`هل أنت متأكد من حذف خطة "${plan.name}"؟`)) {
                      deletePlan.mutate(plan.id);
                    }
                  }}
                  index={index}
                />
              );
            })}
          </div>
        ) : (
          <PlanComparison plans={filteredPlans || []} services={services || []} />
        )}
      </motion.div>

      {/* نافذة إنشاء/تعديل الخطة */}
      <CreatePlanModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditingPlan(null);
        }}
        plan={editingPlan}
        services={services || []}
        onSubmit={(data) => {
          if (editingPlan) {
            updatePlan.mutate({ planId: editingPlan.id, payload: data });
          } else {
            createPlan.mutate(data);
          }
          setIsModalOpen(false);
          setEditingPlan(null);
        }}
        isSubmitting={createPlan.isPending || updatePlan.isPending}
      />
    </motion.div>
  );
}