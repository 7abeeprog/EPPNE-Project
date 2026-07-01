// app/(dashboard)/affiliate/page.tsx
"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { useAffiliateProfile, useAffiliateStats, useAffiliateDashboard } from "@/hooks/affiliate/useAffiliate";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Users,
  TrendingUp,
  DollarSign,
  MousePointerClick,
  Link2,
  Gift,
  Wallet,
  Plus,
  ArrowRight,
  Crown,
  Sparkles,
} from "lucide-react";

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

export default function AffiliateDashboard() {
  const { data: profile, isLoading: profileLoading } = useAffiliateProfile();
  const { data: stats, isLoading: statsLoading } = useAffiliateStats();
  const { data: dashboard, isLoading: dashboardLoading } = useAffiliateDashboard();

  const isLoading = profileLoading || statsLoading || dashboardLoading;

  // بطاقات الإحصائيات
  const statCards = [
    {
      title: "إجمالي الأرباح",
      value: stats?.total_earned ? `${stats.total_earned.toFixed(2)} MR_USDT` : "0 MR_USDT",
      icon: DollarSign,
      color: "text-emerald-500",
      bg: "bg-emerald-500/10",
    },
    {
      title: "الأرباح المعلقة",
      value: stats?.pending_earned ? `${stats.pending_earned.toFixed(2)} MR_USDT` : "0 MR_USDT",
      icon: Wallet,
      color: "text-amber-500",
      bg: "bg-amber-500/10",
    },
    {
      title: "الإحالات الناجحة",
      value: stats?.total_conversions || 0,
      icon: Users,
      color: "text-blue-500",
      bg: "bg-blue-500/10",
    },
    {
      title: "معدل التحويل",
      value: stats?.conversion_rate ? `${stats.conversion_rate.toFixed(1)}%` : "0%",
      icon: TrendingUp,
      color: "text-purple-500",
      bg: "bg-purple-500/10",
    },
  ];

  if (isLoading) {
    return (
      <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto">
        <Skeleton className="h-48 w-full rounded-[2rem] bg-card/40" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-36 rounded-[2rem] bg-card/40 border border-white/5" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-80 rounded-[2rem] bg-card/40" />
          <Skeleton className="h-80 rounded-[2rem] bg-card/40" />
        </div>
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
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(245,158,11,0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* رأس الصفحة */}
      <motion.div
        variants={itemVariants}
        className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10"
      >
        <div className="absolute top-0 right-0 w-72 h-72 bg-amber-500/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse" />
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="flex items-center gap-6">
            <div className="p-4 bg-amber-500/10 rounded-2xl border border-amber-500/20 shadow-inner">
              <Gift className="h-12 w-12 text-amber-500" />
            </div>
            <div>
              <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-amber-500 drop-shadow-sm">
                نظام الإحالة السيادي
              </h1>
              <p className="text-muted-foreground mt-2 text-lg md:text-xl font-medium">
                أرباحك من دعوة الأصدقاء والمستخدمين إلى المنصة
              </p>
              {profile?.referral_code && (
                <div className="flex items-center gap-3 mt-3">
                  <span className="text-sm font-bold text-muted-foreground">كود الدعوة الخاص بك:</span>
                  <Badge className="bg-primary/20 text-primary border-primary/30 font-mono text-lg px-4 py-2">
                    {profile.referral_code}
                  </Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="rounded-xl hover:bg-primary/10"
                    onClick={() => {
                      navigator.clipboard.writeText(profile.referral_code);
                      toast.success("تم نسخ كود الدعوة!");
                    }}
                  >
                    نسخ
                  </Button>
                </div>
              )}
            </div>
          </div>
          <div className="flex gap-3">
            <Link href="/affiliate/links">
              <Button variant="outline" className="h-14 px-6 rounded-xl border-white/10 hover:bg-primary/10 font-bold">
                <Link2 className="ml-2 h-5 w-5" />
                روابطي
              </Button>
            </Link>
            <Link href="/affiliate/commissions">
              <Button className="h-14 px-8 rounded-xl bg-amber-600 hover:bg-amber-500 font-bold shadow-[0_0_20px_rgba(245,158,11,0.3)]">
                <Wallet className="ml-2 h-5 w-5" />
                سحب الأرباح
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
              <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-amber-500/30 hover:shadow-[0_0_30px_rgba(245,158,11,0.1)] transition-all group">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className={`p-3 ${stat.bg} rounded-xl border border-white/5 group-hover:scale-110 transition-transform`}>
                      <stat.icon className={`h-6 w-6 ${stat.color}`} />
                    </div>
                  </div>
                  <p className="text-2xl md:text-3xl font-black text-foreground drop-shadow-sm">{stat.value}</p>
                  <p className="text-sm text-muted-foreground font-bold mt-1">{stat.title}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* العمولات الأخيرة والروابط الأكثر استخداماً */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* العمولات الأخيرة */}
        <motion.div variants={itemVariants}>
          <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-black flex items-center gap-3 text-foreground">
                  <DollarSign className="h-6 w-6 text-emerald-500" />
                  آخر العمولات
                </h2>
                <Link href="/affiliate/commissions">
                  <Button variant="ghost" size="sm" className="rounded-xl font-bold text-muted-foreground hover:text-primary">
                    عرض الكل <ArrowRight className="mr-2 h-4 w-4" />
                  </Button>
                </Link>
              </div>

              {!dashboard?.recent_commissions?.length ? (
                <div className="text-center py-12 bg-background/30 rounded-xl border border-dashed border-primary/20">
                  <Gift className="mx-auto h-12 w-12 text-primary/30 mb-4" />
                  <p className="text-muted-foreground font-medium">لا توجد عمولات حتى الآن</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {dashboard.recent_commissions.slice(0, 5).map((commission) => (
                    <div
                      key={commission.id}
                      className="flex items-center justify-between p-3 bg-background/40 rounded-xl border border-white/5 hover:border-amber-500/30 transition-all"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="p-2 bg-amber-500/10 rounded-lg border border-amber-500/20">
                          <Gift className="h-4 w-4 text-amber-500" />
                        </div>
                        <div className="min-w-0">
                          <p className="font-bold text-sm text-foreground truncate">
                            المستوى {commission.referral_level} – {commission.product?.title || `منتج #${commission.product_id}`}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {new Date(commission.created_at).toLocaleDateString("ar-EG")}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-black text-emerald-500">
                          +{commission.commission_amount.toFixed(2)} {commission.currency}
                        </p>
                        <Badge className={`${
                          commission.status === "PENDING" ? "bg-amber-500/10 text-amber-500 border-amber-500/20" :
                          commission.status === "PAID" ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" :
                          "bg-muted/10 text-muted-foreground border-white/10"
                        } border text-xs`}>
                          {commission.status === "PENDING" ? "معلقة" :
                           commission.status === "PAID" ? "مدفوعة" :
                           commission.status === "CONFIRMED" ? "مؤكدة" : "ملغاة"}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* الروابط الأكثر استخداماً */}
        <motion.div variants={itemVariants}>
          <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-black flex items-center gap-3 text-foreground">
                  <Link2 className="h-6 w-6 text-blue-500" />
                  روابطي الأكثر استخداماً
                </h2>
                <Link href="/affiliate/links">
                  <Button variant="ghost" size="sm" className="rounded-xl font-bold text-muted-foreground hover:text-primary">
                    عرض الكل <ArrowRight className="mr-2 h-4 w-4" />
                  </Button>
                </Link>
              </div>

              {!dashboard?.top_links?.length ? (
                <div className="text-center py-12 bg-background/30 rounded-xl border border-dashed border-primary/20">
                  <Link2 className="mx-auto h-12 w-12 text-primary/30 mb-4" />
                  <p className="text-muted-foreground font-medium">لا توجد روابط دعوة</p>
                  <Link href="/affiliate/links/create">
                    <Button size="sm" className="mt-4 rounded-xl">
                      <Plus className="h-4 w-4 ml-1" />
                      إنشاء رابط
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-3">
                  {dashboard.top_links.slice(0, 5).map((link) => (
                    <div
                      key={link.id}
                      className="flex items-center justify-between p-3 bg-background/40 rounded-xl border border-white/5 hover:border-blue-500/30 transition-all"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
                          <Link2 className="h-4 w-4 text-blue-500" />
                        </div>
                        <div className="min-w-0">
                          <p className="font-bold text-sm text-foreground truncate">
                            {link.target || "رابط عام"}
                          </p>
                          {link.product && (
                            <p className="text-xs text-muted-foreground truncate">
                              {link.product.title}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="flex items-center gap-3">
                          <div className="text-center">
                            <p className="font-black text-sm text-foreground">{link.clicks}</p>
                            <p className="text-xs text-muted-foreground">نقرة</p>
                          </div>
                          <div className="text-center">
                            <p className="font-black text-sm text-emerald-500">{link.conversions}</p>
                            <p className="text-xs text-muted-foreground">تحويل</p>
                          </div>
                        </div>
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
          <Link href="/affiliate/links/create">
            <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-amber-500/50 hover:shadow-[0_0_30px_rgba(245,158,11,0.15)] transition-all group">
              <CardContent className="p-6 text-center">
                <div className="p-3 bg-amber-500/10 rounded-xl border border-amber-500/20 w-fit mx-auto mb-3 group-hover:scale-110 transition-transform">
                  <Link2 className="h-6 w-6 text-amber-500" />
                </div>
                <p className="font-bold text-sm">إنشاء رابط دعوة</p>
              </CardContent>
            </Card>
          </Link>

          <Link href="/affiliate/tree">
            <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-amber-500/50 hover:shadow-[0_0_30px_rgba(245,158,11,0.15)] transition-all group">
              <CardContent className="p-6 text-center">
                <div className="p-3 bg-amber-500/10 rounded-xl border border-amber-500/20 w-fit mx-auto mb-3 group-hover:scale-110 transition-transform">
                  <Users className="h-6 w-6 text-amber-500" />
                </div>
                <p className="font-bold text-sm">شجرة الإحالة</p>
              </CardContent>
            </Card>
          </Link>

          <Link href="/affiliate/commissions">
            <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-amber-500/50 hover:shadow-[0_0_30px_rgba(245,158,11,0.15)] transition-all group">
              <CardContent className="p-6 text-center">
                <div className="p-3 bg-amber-500/10 rounded-xl border border-amber-500/20 w-fit mx-auto mb-3 group-hover:scale-110 transition-transform">
                  <Wallet className="h-6 w-6 text-amber-500" />
                </div>
                <p className="font-bold text-sm">سحب العمولات</p>
              </CardContent>
            </Card>
          </Link>

          <Link href="/affiliate/guidelines">
            <Card className="border-white/10 bg-card/40 backdrop-blur-xl rounded-[2rem] hover:border-amber-500/50 hover:shadow-[0_0_30px_rgba(245,158,11,0.15)] transition-all group">
              <CardContent className="p-6 text-center">
                <div className="p-3 bg-amber-500/10 rounded-xl border border-amber-500/20 w-fit mx-auto mb-3 group-hover:scale-110 transition-transform">
                  <Crown className="h-6 w-6 text-amber-500" />
                </div>
                <p className="font-bold text-sm">دليل الداعي السيادي</p>
              </CardContent>
            </Card>
          </Link>
        </div>
      </motion.div>
    </motion.div>
  );
}