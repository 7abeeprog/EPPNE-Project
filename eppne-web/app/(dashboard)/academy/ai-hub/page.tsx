// app/(dashboard)/academy/ai-hub/page.tsx
"use client";

import { useMemo } from "react";
import { motion, Variants } from "framer-motion";
import {
  BrainCircuit,
  Zap,
  Target,
  Sparkles,
  Award,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

// ✅ استبدال store بالهوكات الجديدة
import { useDigitalTwin, useBadges } from "@/hooks/academy-queries";
import { DigitalTwin, Badge } from "@/types/academy";
import { handleError } from "@/lib/error-handler";

// ✅ تعريف الحركات باستخدام Variants
const containerVars: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const itemVars: Variants = {
  hidden: { opacity: 0, y: 20 },
  show: {
    opacity: 1,
    y: 0,
    transition: { type: "spring", stiffness: 300, damping: 24 },
  },
};

// ✅ دالة مساعدة لترجمة نوع الشارة
const getBadgeEmoji = (type: string): string => {
  switch (type) {
    case "GOLD":
      return "🥇";
    case "SILVER":
      return "🥈";
    case "BRONZE":
      return "🥉";
    case "PLATINUM":
      return "💎";
    default:
      return "🏅";
  }
};

export default function AIHubPage() {
  // ✅ 1. جلب التوأم الرقمي
  const {
    data: digitalTwin,
    isLoading: isTwinLoading,
    error: twinError,
  } = useDigitalTwin();

  // ✅ 2. جلب الشارات (مع Pagination)
  const {
    data: badgesData,
    isLoading: isBadgesLoading,
    error: badgesError,
  } = useBadges(0, 10);

  const badges = badgesData?.data || [];

  // ✅ 3. معالجة الأخطاء
  if (twinError) {
    const error = handleError(twinError, "جلب التوأم الرقمي");
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
        <div className="p-6 bg-destructive/10 rounded-full mb-6 border border-destructive/20">
          <AlertCircle className="h-16 w-16 text-destructive" />
        </div>
        <h2 className="text-3xl font-bold mb-2">فشل في تحميل التوأم الرقمي</h2>
        <p className="text-muted-foreground text-lg mb-8 max-w-md">{error.message}</p>
        <Button
          onClick={() => window.location.reload()}
          size="lg"
          className="rounded-xl h-14 px-8"
        >
          إعادة المحاولة
        </Button>
      </div>
    );
  }

  // ✅ 4. حالة التحميل
  if (isTwinLoading || !digitalTwin) {
    return (
      <div className="flex flex-col items-center justify-center h-[80vh] p-6">
        <Loader2 className="h-16 w-16 text-primary animate-spin opacity-50 mb-4" />
        <Skeleton className="h-4 w-64 mb-2" />
        <p className="text-muted-foreground">جاري مزامنة التوأم الرقمي الخاص بك...</p>
      </div>
    );
  }

  const twin = digitalTwin as DigitalTwin;
  const recommendations = twin.ai_recommendations || [];

  return (
    <motion.div
      variants={containerVars}
      initial="hidden"
      animate="show"
      className="space-y-8 p-4 md:p-6 max-w-7xl mx-auto"
    >
      {/* 🟢 رأس الصفحة مع تأثير النيون */}
      <motion.div
        variants={itemVars}
        className="relative overflow-hidden rounded-3xl bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_30px_-10px_rgba(var(--primary-rgb),0.3)] p-8"
      >
        <div className="absolute top-0 right-0 w-64 h-64 bg-primary/20 blur-[100px] rounded-full pointer-events-none -z-10" />
        <div className="flex items-center gap-4">
          <div className="p-4 bg-primary/10 rounded-2xl border border-primary/30 shadow-[0_0_15px_rgba(var(--primary-rgb),0.2)]">
            <BrainCircuit className="h-10 w-10 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl md:text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-foreground to-primary">
              التوأم الرقمي التعليمي
            </h1>
            <p className="text-muted-foreground mt-1 text-lg">
              الذكاء الاصطناعي يحلل نمط تعلمك ويرسم مسارك السيادي.
            </p>
          </div>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* 🟢 نمط التعلم */}
        <motion.div
          variants={itemVars}
          className="backdrop-blur-xl bg-card/60 border border-white/10 rounded-2xl p-6 shadow-sm hover:shadow-[0_0_20px_-5px_rgba(var(--primary-rgb),0.3)] transition-all hover:-translate-y-1"
        >
          <div className="flex items-center gap-2 mb-4 text-primary">
            <Zap className="h-5 w-5" />
            <h3 className="font-bold text-lg">نمط التعلم المهيمن</h3>
          </div>
          <div className="text-4xl font-black uppercase tracking-wider opacity-80">
            {twin.learning_style === "VISUAL"
              ? "بصري 👁️"
              : twin.learning_style === "AUDITORY"
              ? "سمعي 🎧"
              : twin.learning_style === "KINESTHETIC"
              ? "حركي 🏃"
              : "متكيف 🔄"}
          </div>
          <p className="text-sm text-muted-foreground mt-4">
            نقوم بتخصيص عرض الدروس لتتناسب مع سرعة استيعابك.
          </p>
        </motion.div>

        {/* 🟢 الخريطة الإدراكية */}
        <motion.div
          variants={itemVars}
          className="md:col-span-2 backdrop-blur-xl bg-card/60 border border-white/10 rounded-2xl p-6 shadow-sm relative overflow-hidden hover:shadow-[0_0_20px_-5px_rgba(var(--primary-rgb),0.2)] transition-all"
        >
          <Sparkles className="absolute top-4 left-4 h-6 w-6 text-primary/40 animate-pulse" />
          <h3 className="font-bold flex items-center gap-2 mb-6 text-lg">
            <Target className="h-5 w-5 text-primary" />
            الخريطة الإدراكية
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="bg-emerald-500/10 border border-emerald-500/20 p-4 rounded-xl shadow-inner">
              <span className="text-xs text-emerald-500 font-bold uppercase block mb-1">
                نقاط القوة
              </span>
              <p className="font-medium">
                {twin.cognitive_map?.strengths || "تحليل مستمر..."}
              </p>
            </div>
            <div className="bg-orange-500/10 border border-orange-500/20 p-4 rounded-xl shadow-inner">
              <span className="text-xs text-orange-500 font-bold uppercase block mb-1">
                مناطق التطوير
              </span>
              <p className="font-medium">
                {twin.cognitive_map?.weak_areas || "تحليل مستمر..."}
              </p>
            </div>
          </div>
          {recommendations.length > 0 && (
            <div className="mt-4 p-4 bg-primary/5 border border-primary/20 rounded-xl">
              <span className="text-xs text-primary font-bold uppercase block mb-1">
                💡 توصيات الذكاء الاصطناعي
              </span>
              <ul className="list-disc list-inside text-sm text-muted-foreground">
                {recommendations.slice(0, 3).map((rec: string, idx: number) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ul>
            </div>
          )}
        </motion.div>
      </div>

      {/* 🟢 قسم الشارات (Badges) */}
      <motion.div variants={itemVars} className="w-full">
        <div className="flex items-center gap-2 mb-6">
          <Award className="h-6 w-6 text-amber-500" />
          <h2 className="text-2xl font-bold">الشارات السيادية المكتسبة</h2>
        </div>

        {isBadgesLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-24 rounded-2xl bg-card/40" />
            ))}
          </div>
        ) : badgesError ? (
          <div className="p-4 bg-destructive/10 rounded-xl border border-destructive/20 text-center">
            <p className="text-destructive font-bold">
              {handleError(badgesError, "جلب الشارات").message}
            </p>
          </div>
        ) : badges.length === 0 ? (
          <div className="text-center py-12 bg-card/20 backdrop-blur-sm rounded-[2rem] border border-dashed border-primary/20">
            <Award className="mx-auto h-16 w-16 text-primary/20 mb-4 animate-pulse" />
            <p className="text-muted-foreground text-lg">لم تحصل على أي شارات بعد</p>
            <p className="text-sm text-muted-foreground/70">
              أكمل الدروس واجتز الاختبارات لتحصل على شارات سيادية.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {badges.map((badge: Badge) => (
              <Card
                key={badge.id}
                className="bg-card/60 backdrop-blur-xl border border-white/10 rounded-2xl hover:border-amber-500/50 hover:shadow-[0_0_20px_rgba(245,158,11,0.15)] transition-all group"
              >
                <CardContent className="p-4 text-center">
                  <div className="text-4xl mb-2 group-hover:scale-110 transition-transform">
                    {getBadgeEmoji(badge.badge_type)}
                  </div>
                  <h4 className="font-bold text-sm">{badge.title}</h4>
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                    {badge.description}
                  </p>
                  <p className="text-xs text-amber-500 font-bold mt-2">
                    +{badge.xp_reward} XP
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}