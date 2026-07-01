// app/(dashboard)/saas/page.tsx
"use client";

import { motion } from "framer-motion";
import { useState, useEffect } from "react";
import Link from "next/link";
import { useServices, useSubscriptions } from "@/hooks/saas";
import { useInvoices } from "@/hooks/saas/useInvoices";
import { useDashboardStats } from "@/hooks/saas/useDashboard";
import {
  LayoutDashboard,
  Package,
  Users,
  CreditCard,
  TrendingUp,
  Settings,
  Plus,
  ArrowRight,
  Loader2,
  AlertCircle,
  CheckCircle,
  Clock,
  XCircle,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

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

export default function SaasDashboard() {
  const { data: stats, isLoading: isStatsLoading, error: statsError } = useDashboardStats();
  const { data: services, isLoading: isServicesLoading } = useServices();
  const { data: subscriptions, isLoading: isSubscriptionsLoading } = useSubscriptions(0, 10);
  const { data: invoices, isLoading: isInvoicesLoading } = useInvoices(0, 10);

  const isLoading = isStatsLoading || isServicesLoading || isSubscriptionsLoading || isInvoicesLoading;

  // إحصائيات سريعة
  const statCards = [
    {
      title: "الخدمات النشطة",
      value: stats?.active_services ?? services?.filter(s => s.is_active).length ?? 0,
      icon: Package,
      color: "text-blue-500",
      bg: "bg-blue-500/10",
      border: "border-blue-500/20",
    },
    {
      title: "الاشتراكات النشطة",
      value: stats?.active_subscriptions ?? subscriptions?.data?.filter(s => s.status === "ACTIVE").length ?? 0,
      icon: Users,
      color: "text-emerald-500",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/20",
    },
    {
      title: "الفواتير المعلقة",
      value: stats?.pending_invoices ?? invoices?.data?.filter(i => i.status === "PENDING").length ?? 0,
      icon: CreditCard,
      color: "text-amber-500",
      bg: "bg-amber-500/10",
      border: "border-amber-500/20",
    },
    {
      title: "الإيرادات الشهرية",
      value: stats?.monthly_revenue ? `${stats.monthly_revenue.toLocaleString()} ${stats.currency}` : "0 MR_USDT",
      icon: TrendingUp,
      color: "text-purple-500",
      bg: "bg-purple-500/10",
      border: "border-purple-500/20",
    },
  ];

  // حالة التحميل
  if (isLoading) {
    return (
      <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto">
        <Skeleton className="h-48 w-full rounded-[2rem] bg-card/40" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-36 rounded-[2rem] bg-card/40 border border-white/5" />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Skeleton className="h-80 rounded-[2rem] bg-card/40" />
          <Skeleton className="h-80 rounded-[2rem] bg-card/40" />
        </div>
      </div>
    );
  }

  // معالجة الأخطاء
  if (statsError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
        <div className="p-6 bg-destructive/10 rounded-full mb-6 border border-destructive/20">
          <AlertCircle className="h-16 w-16 text-destructive" />
        </div>
        <h2 className="text-3xl font-bold mb-2">فشل في تحميل لوحة التحكم</h2>
        <p className="text-muted-foreground text-lg mb-8 max-w-md">
          {statsError.message || "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."}
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
              <LayoutDashboard className="h-12 w-12 text-blue-500" />
            </div>
            <div>
              <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-blue-500 drop-shadow-sm">
                لوحة تحكم SaaS
              </h1>
              <p className="text-muted-foreground mt-2 text-lg md:text-xl font-medium">
                إدارة الخدمات، الاشتراكات، والفواتير لمنصتك السيادية
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <Link href="/saas/services">
              <Button variant="outline" className="h-14 px-6 rounded-xl border-white/10 hover:bg-primary/10 font-bold">
                <Settings className="ml-2 h-5 w-5" />
                إدارة الخدمات
              </Button>
            </Link>
            <Link href="/saas/subscriptions">
              <Button className="h-14 px-8 rounded-xl bg-primary hover:bg-primary/90 font-bold shadow-[0_0_20px_rgba(var(--primary-rgb),0.3)]">
                <Plus className="ml-2 h-5 w-5" />
                اشتراك جديد
              </Button>
            </Link>
          </div>
        </div>
      </motion.div>

      {/* بطاقات الإحصائيات */}
      <motion.div variants={itemVariants}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {statCards.map((stat, index) => (
            <motion.div key={index} variants={itemVariants}>
              <Card className={`border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:${stat.border} hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.1)] transition-all group`}>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className={`p-3 ${stat.bg} rounded-xl border ${stat.border} group-hover:scale-110 transition-transform`}>
                      <stat.icon className={`h-6 w-6 ${stat.color}`} />
                    </div>
                  </div>
                  <p className="text-3xl md:text-4xl font-black text-foreground drop-shadow-sm">{stat.value}</p>
                  <p className="text-sm text-muted-foreground font-bold mt-1">{stat.title}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* الاشتراكات الأخيرة والفواتير المعلقة */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* الاشتراكات الأخيرة */}
        <motion.div variants={itemVariants}>
          <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-black flex items-center gap-3 text-foreground">
                  <Users className="h-6 w-6 text-blue-500" />
                  آخر الاشتراكات
                </h2>
                <Link href="/saas/subscriptions">
                  <Button variant="ghost" size="sm" className="rounded-xl font-bold text-muted-foreground hover:text-primary">
                    عرض الكل <ArrowRight className="mr-2 h-4 w-4" />
                  </Button>
                </Link>
              </div>

              {subscriptions?.data?.length === 0 ? (
                <div className="text-center py-12 bg-background/30 rounded-xl border border-dashed border-primary/20">
                  <Users className="mx-auto h-12 w-12 text-primary/30 mb-4" />
                  <p className="text-muted-foreground font-medium">لا توجد اشتراكات بعد</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {subscriptions?.data?.slice(0, 5).map((sub) => (
                    <div key={sub.id} className="flex items-center justify-between p-3 bg-background/40 rounded-xl border border-white/5 hover:border-primary/30 transition-all">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="p-2 bg-primary/10 rounded-lg border border-primary/20">
                          <Users className="h-4 w-4 text-primary" />
                        </div>
                        <div className="min-w-0">
                          <p className="font-bold text-sm text-foreground truncate">
                            {sub.plan?.name || "خطة غير معروفة"}
                          </p>
                          <p className="text-xs text-muted-foreground truncate">
                            المستأجر #{sub.tenant_id}
                          </p>
                        </div>
                      </div>
                      <Badge className={`${
                        sub.status === "ACTIVE" ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" :
                        sub.status === "TRIAL" ? "bg-blue-500/10 text-blue-500 border-blue-500/20" :
                        sub.status === "PAST_DUE" ? "bg-amber-500/10 text-amber-500 border-amber-500/20" :
                        "bg-muted/10 text-muted-foreground border-white/10"
                      } border font-bold shrink-0`}>
                        {sub.status === "ACTIVE" && <CheckCircle className="h-3 w-3 ml-1" />}
                        {sub.status === "TRIAL" && <Clock className="h-3 w-3 ml-1" />}
                        {sub.status === "PAST_DUE" && <AlertCircle className="h-3 w-3 ml-1" />}
                        {sub.status === "EXPIRED" && <XCircle className="h-3 w-3 ml-1" />}
                        {sub.status === "CANCELLED" && <XCircle className="h-3 w-3 ml-1" />}
                        {sub.status === "ACTIVE" ? "نشط" :
                         sub.status === "TRIAL" ? "تجريبي" :
                         sub.status === "PAST_DUE" ? "متأخر" :
                         sub.status === "EXPIRED" ? "منتهي" :
                         sub.status === "CANCELLED" ? "ملغي" : sub.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* الفواتير المعلقة */}
        <motion.div variants={itemVariants}>
          <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-black flex items-center gap-3 text-foreground">
                  <CreditCard className="h-6 w-6 text-amber-500" />
                  الفواتير المعلقة
                </h2>
                <Link href="/saas/invoices">
                  <Button variant="ghost" size="sm" className="rounded-xl font-bold text-muted-foreground hover:text-primary">
                    عرض الكل <ArrowRight className="mr-2 h-4 w-4" />
                  </Button>
                </Link>
              </div>

              {invoices?.data?.filter(i => i.status === "PENDING").length === 0 ? (
                <div className="text-center py-12 bg-background/30 rounded-xl border border-dashed border-primary/20">
                  <CheckCircle className="mx-auto h-12 w-12 text-emerald-500/30 mb-4" />
                  <p className="text-muted-foreground font-medium">لا توجد فواتير معلقة</p>
                  <p className="text-xs text-muted-foreground/70 mt-1">جميع الفواتير مدفوعة</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {invoices?.data?.filter(i => i.status === "PENDING").slice(0, 5).map((invoice) => (
                    <div key={invoice.id} className="flex items-center justify-between p-3 bg-background/40 rounded-xl border border-white/5 hover:border-amber-500/30 transition-all">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="p-2 bg-amber-500/10 rounded-lg border border-amber-500/20">
                          <CreditCard className="h-4 w-4 text-amber-500" />
                        </div>
                        <div className="min-w-0">
                          <p className="font-bold text-sm text-foreground truncate">
                            {invoice.invoice_number}
                          </p>
                          <p className="text-xs text-muted-foreground truncate">
                            {new Date(invoice.created_at).toLocaleDateString("ar-EG")}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-black text-amber-500">
                          {invoice.amount.toLocaleString()} {invoice.currency}
                        </p>
                        {invoice.due_date && (
                          <p className="text-xs text-muted-foreground">
                            يستحق: {new Date(invoice.due_date).toLocaleDateString("ar-EG")}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* روابط سريعة */}
      <motion.div variants={itemVariants}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Link href="/saas/plans">
            <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-primary/50 hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] transition-all group">
              <CardContent className="p-6 text-center">
                <div className="p-3 bg-primary/10 rounded-xl border border-primary/20 w-fit mx-auto mb-3 group-hover:scale-110 transition-transform">
                  <Package className="h-6 w-6 text-primary" />
                </div>
                <p className="font-bold text-sm">خطط التسعير</p>
                <p className="text-xs text-muted-foreground">إدارة خطط الخدمات</p>
              </CardContent>
            </Card>
          </Link>

          <Link href="/saas/subscriptions">
            <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-primary/50 hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] transition-all group">
              <CardContent className="p-6 text-center">
                <div className="p-3 bg-primary/10 rounded-xl border border-primary/20 w-fit mx-auto mb-3 group-hover:scale-110 transition-transform">
                  <Users className="h-6 w-6 text-primary" />
                </div>
                <p className="font-bold text-sm">الاشتراكات</p>
                <p className="text-xs text-muted-foreground">إدارة اشتراكات العملاء</p>
              </CardContent>
            </Card>
          </Link>

          <Link href="/saas/invoices">
            <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-primary/50 hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] transition-all group">
              <CardContent className="p-6 text-center">
                <div className="p-3 bg-primary/10 rounded-xl border border-primary/20 w-fit mx-auto mb-3 group-hover:scale-110 transition-transform">
                  <CreditCard className="h-6 w-6 text-primary" />
                </div>
                <p className="font-bold text-sm">الفواتير</p>
                <p className="text-xs text-muted-foreground">إدارة الفواتير والمدفوعات</p>
              </CardContent>
            </Card>
          </Link>

          <Link href="/saas/feature-flags">
            <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-primary/50 hover:shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] transition-all group">
              <CardContent className="p-6 text-center">
                <div className="p-3 bg-primary/10 rounded-xl border border-primary/20 w-fit mx-auto mb-3 group-hover:scale-110 transition-transform">
                  <Settings className="h-6 w-6 text-primary" />
                </div>
                <p className="font-bold text-sm">الميزات التجريبية</p>
                <p className="text-xs text-muted-foreground">تفعيل/تعطيل الميزات</p>
              </CardContent>
            </Card>
          </Link>
        </div>
      </motion.div>
    </motion.div>
  );
}