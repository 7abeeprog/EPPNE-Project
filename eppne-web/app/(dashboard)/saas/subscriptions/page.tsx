// app/(dashboard)/saas/subscriptions/page.tsx
"use client";

import { motion } from "framer-motion";
import { useState } from "react";
import { useSubscriptions, useCancelSubscription, useRenewSubscription } from "@/hooks/saas";
import { SubscriptionCard } from "@/components/saas/SubscriptionCard";
import { SubscribeModal } from "@/components/saas/SubscribeModal";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Search, Users, Plus, AlertCircle, Filter } from "lucide-react";
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

export default function SubscriptionsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [skip, setSkip] = useState(0);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const limit = 10;

  const { data: subscriptions, isLoading, error, refetch } = useSubscriptions(skip, limit, statusFilter);
  const cancelSubscription = useCancelSubscription();
  const renewSubscription = useRenewSubscription();

  // تصفية حسب البحث
  const filteredSubscriptions = subscriptions?.data?.filter((sub) =>
    sub.plan?.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    sub.tenant_id?.toString().includes(searchQuery)
  );

  const handleNext = () => {
    if (subscriptions && skip + limit < subscriptions.total) {
      setSkip((prev) => prev + limit);
    }
  };

  const handlePrevious = () => {
    if (skip > 0) {
      setSkip((prev) => prev - limit);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-5xl mx-auto">
        <Skeleton className="h-48 w-full rounded-[2rem] bg-card/40" />
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
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
        <h2 className="text-3xl font-bold mb-2">فشل في تحميل الاشتراكات</h2>
        <p className="text-muted-foreground text-lg mb-8 max-w-md">
          {error.message || "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."}
        </p>
        <Button onClick={() => refetch()} size="lg" className="rounded-xl h-14 px-8">
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
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(59,130,246,0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* رأس الصفحة */}
      <motion.div
        variants={itemVariants}
        className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10"
      >
        <div className="absolute top-0 right-0 w-72 h-72 bg-blue-500/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse" />
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="flex items-center gap-6">
            <div className="p-4 bg-blue-500/10 rounded-2xl border border-blue-500/20 shadow-inner">
              <Users className="h-12 w-12 text-blue-500" />
            </div>
            <div>
              <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-blue-500 drop-shadow-sm">
                الاشتراكات
              </h1>
              <p className="text-muted-foreground mt-2 text-lg md:text-xl font-medium">
                إدارة اشتراكات العملاء في الخدمات المختلفة
              </p>
            </div>
          </div>
          <Button
            onClick={() => setIsModalOpen(true)}
            className="h-14 px-8 rounded-xl bg-blue-600 hover:bg-blue-500 font-bold shadow-[0_0_20px_rgba(59,130,246,0.3)]"
          >
            <Plus className="ml-2 h-5 w-5" />
            اشتراك جديد
          </Button>
        </div>
      </motion.div>

      {/* شريط البحث والفلترة */}
      <motion.div variants={itemVariants}>
        <div className="flex flex-col md:flex-row gap-4 bg-card/30 backdrop-blur-xl p-4 rounded-2xl border border-white/10">
          <div className="relative flex-1">
            <Search className="absolute right-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <Input
              placeholder="ابحث عن اشتراك..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-12 bg-background/50 border-white/10 pr-12 rounded-xl focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 transition-colors"
            />
          </div>
          <div className="flex gap-3">
            <Select
              value={statusFilter}
              onValueChange={(val) => {
                setStatusFilter(val || undefined);
                setSkip(0);
              }}
            >
              <SelectTrigger className="w-48 h-12 bg-background/50 border-white/10 rounded-xl">
                <SelectValue placeholder="كل الحالات" />
              </SelectTrigger>
              <SelectContent className="bg-card/90 backdrop-blur-xl border-white/10">
                <SelectItem value="">كل الحالات</SelectItem>
                <SelectItem value="ACTIVE">نشط</SelectItem>
                <SelectItem value="TRIAL">تجريبي</SelectItem>
                <SelectItem value="PAST_DUE">متأخر</SelectItem>
                <SelectItem value="EXPIRED">منتهي</SelectItem>
                <SelectItem value="CANCELLED">ملغي</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </motion.div>

      {/* قائمة الاشتراكات */}
      <motion.div variants={itemVariants}>
        {filteredSubscriptions?.length === 0 ? (
          <div className="text-center py-20 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-primary/20">
            <Users className="mx-auto h-16 w-16 text-primary/30 mb-4 animate-pulse" />
            <h3 className="text-2xl font-black text-foreground">
              {searchQuery ? "لا توجد اشتراكات تطابق البحث" : "لا توجد اشتراكات"}
            </h3>
            <p className="text-muted-foreground mt-2 text-lg">
              {searchQuery ? "جرب تغيير كلمات البحث" : "قم بإضافة اشتراك جديد للعميل"}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredSubscriptions?.map((subscription, index) => (
              <SubscriptionCard
                key={subscription.id}
                subscription={subscription}
                onCancel={() => {
                  if (confirm("هل أنت متأكد من إلغاء هذا الاشتراك؟")) {
                    cancelSubscription.mutate(subscription.id);
                  }
                }}
                onRenew={() => {
                  renewSubscription.mutate(subscription.id);
                }}
                index={index}
              />
            ))}
          </div>
        )}
      </motion.div>

      {/* Pagination */}
      {subscriptions && subscriptions.total > limit && (
        <motion.div variants={itemVariants}>
          <div className="flex justify-between items-center pt-4 border-t border-border/50">
            <Button
              variant="outline"
              onClick={handlePrevious}
              disabled={skip === 0}
              className="rounded-xl border-white/10 hover:bg-primary/10 font-bold"
            >
              السابق
            </Button>
            <span className="text-sm text-muted-foreground font-bold">
              صفحة {Math.floor(skip / limit) + 1} / {Math.ceil(subscriptions.total / limit)}
            </span>
            <Button
              variant="outline"
              onClick={handleNext}
              disabled={skip + limit >= subscriptions.total}
              className="rounded-xl border-white/10 hover:bg-primary/10 font-bold"
            >
              التالي
            </Button>
          </div>
        </motion.div>
      )}

      {/* نافذة إنشاء اشتراك */}
      <SubscribeModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => {
          refetch();
          setIsModalOpen(false);
        }}
      />
    </motion.div>
  );
}