// app/(dashboard)/academy/leaderboard/page.tsx
"use client";

import { useMemo } from "react";
import { motion, Variants } from "framer-motion";

// ✅ استبدال apiClient بالهوك الجديد
import { useLeaderboard } from "@/hooks/academy-queries";
import { LeaderboardEntry } from "@/types/academy";
import { handleError } from "@/lib/error-handler";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Trophy,
  Medal,
  Star,
  Flame,
  Crown,
  Loader2,
  AlertCircle,
} from "lucide-react";

// ✅ تعريف الحركات باستخدام Variants
const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
};

const headerVariants: Variants = {
  hidden: { opacity: 0, y: -30, scale: 0.95 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 300, damping: 25 },
  },
};

const cardVariants: Variants = {
  hidden: { opacity: 0, x: -20, scale: 0.95 },
  show: {
    opacity: 1,
    x: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 300, damping: 24 },
  },
};

export default function LeaderboardPage() {
  // ✅ 1. جلب لوحة الشرف (مع Pagination)
  const {
    data: leaderboardData,
    isLoading,
    error,
  } = useLeaderboard(50); // 50 متصدر

  const leaderboard = leaderboardData?.data || [];

  // ✅ 2. دالة تصنيف المراكز (محسّنة)
  const getRankStyling = useMemo(() => {
    return (rank: number) => {
      switch (rank) {
        case 1:
          return "bg-gradient-to-r from-amber-500/20 to-amber-500/5 backdrop-blur-2xl border-amber-500/50 shadow-[0_0_40px_rgba(245,158,11,0.3)] text-amber-500 hover:scale-[1.02] z-30";
        case 2:
          return "bg-gradient-to-r from-slate-400/20 to-slate-400/5 backdrop-blur-xl border-slate-400/50 shadow-[0_0_30px_rgba(148,163,184,0.3)] text-slate-400 hover:scale-[1.02] z-20";
        case 3:
          return "bg-gradient-to-r from-orange-500/20 to-orange-500/5 backdrop-blur-xl border-orange-500/50 shadow-[0_0_30px_rgba(249,115,22,0.3)] text-orange-500 hover:scale-[1.02] z-10";
        default:
          return "bg-card/40 backdrop-blur-md border-white/5 hover:border-primary/30 hover:shadow-[0_0_20px_rgba(var(--primary-rgb),0.15)] text-foreground";
      }
    };
  }, []);

  const getRankIcon = (rank: number) => {
    if (rank === 1)
      return (
        <Crown className="w-10 h-10 text-amber-500 drop-shadow-[0_0_15px_rgba(245,158,11,0.8)]" />
      );
    if (rank === 2)
      return (
        <Medal className="w-8 h-8 text-slate-400 drop-shadow-[0_0_10px_rgba(148,163,184,0.8)]" />
      );
    if (rank === 3)
      return (
        <Medal className="w-8 h-8 text-orange-500 drop-shadow-[0_0_10px_rgba(249,115,22,0.8)]" />
      );
    return (
      <span className="text-2xl font-black text-muted-foreground/50">#{rank}</span>
    );
  };

  // ✅ 3. معالجة الأخطاء
  if (error) {
    const err = handleError(error, "جلب لوحة الشرف");
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
        <div className="p-6 bg-destructive/10 rounded-full mb-6 border border-destructive/20">
          <AlertCircle className="h-16 w-16 text-destructive" />
        </div>
        <h2 className="text-3xl font-bold mb-2">فشل في تحميل لوحة الشرف</h2>
        <p className="text-muted-foreground text-lg mb-8 max-w-md">{err.message}</p>
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

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="flex flex-col w-full min-w-0 space-y-10 p-4 md:p-8 max-w-5xl mx-auto relative animate-in fade-in slide-in-from-bottom-4 duration-700"
    >
      {/* خلفية نيون زجاجية */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(var(--primary-rgb),0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* الهيدر التحفيزي */}
      <motion.div
        variants={headerVariants}
        className="relative rounded-[2.5rem] bg-card/40 backdrop-blur-2xl border border-white/10 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-10 md:p-16 overflow-hidden text-center flex flex-col items-center w-full"
      >
        <div className="absolute inset-0 bg-[url('/noise.png')] opacity-[0.03] mix-blend-overlay pointer-events-none" />
        <div className="absolute top-[-50%] left-[-10%] w-96 h-96 bg-primary/20 blur-[150px] rounded-full pointer-events-none animate-pulse duration-1000" />

        <div className="p-4 bg-primary/10 rounded-full border border-primary/20 shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] mb-6">
          <Trophy className="w-20 h-20 text-primary animate-bounce" />
        </div>

        <h1 className="text-4xl md:text-6xl font-black mb-4 bg-clip-text text-transparent bg-gradient-to-r from-foreground to-primary drop-shadow-sm">
          لوحة الشرف السيادية
        </h1>
        <p className="text-xl text-muted-foreground max-w-2xl font-medium">
          أباطرة الأكاديمية وصُناع المستقبل. يتم حساب المراكز اللحظية بناءً على نقاط
          الخبرة (XP) المكتسبة من التكليفات المعتمدة والتقييمات التكيفية.
        </p>
        {leaderboard.length > 0 && (
          <div className="mt-4 text-sm text-muted-foreground/70 bg-background/30 px-4 py-2 rounded-full border border-white/5">
            تحديث لحظي • {leaderboard.length} متصدر
          </div>
        )}
      </motion.div>

      {/* قائمة المتصدرين */}
      <motion.div variants={cardVariants} className="space-y-4 w-full">
        {isLoading ? (
          <div className="space-y-4">
            <div className="flex justify-center mb-8">
              <Loader2 className="h-10 w-10 text-primary animate-spin" />
            </div>
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton
                key={i}
                className={`h-28 w-full rounded-3xl bg-card/40 border border-white/5 ${
                  i === 1 ? "h-32" : ""
                }`}
              />
            ))}
          </div>
        ) : leaderboard.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="text-center p-16 bg-card/20 backdrop-blur-sm rounded-[2.5rem] border border-dashed border-white/10"
          >
            <Star className="w-16 h-16 text-primary/30 mx-auto mb-4 animate-pulse" />
            <p className="text-3xl font-black text-foreground mb-2">
              ساحة المنافسة تنتظر أول الأبطال!
            </p>
            <p className="text-lg text-muted-foreground font-medium">
              كن أول من يقتنص نقاط الخبرة ويتصدر المشهد السيادي.
            </p>
          </motion.div>
        ) : (
          leaderboard.map((player: LeaderboardEntry) => (
            <motion.div
              key={player.user_id}
              variants={cardVariants}
              whileHover={{ scale: 1.01 }}
              transition={{ type: "spring", stiffness: 400, damping: 25 }}
            >
              <Card
                className={`rounded-[2rem] transition-all duration-500 overflow-hidden relative ${getRankStyling(
                  player.rank
                )}`}
              >
                {/* تأثير اللمعان للأوائل */}
                {player.rank <= 3 && (
                  <div className="absolute top-0 left-[-100%] w-1/2 h-full bg-gradient-to-r from-transparent via-white/10 to-transparent skew-x-12 animate-[shimmer_3s_infinite]" />
                )}

                <CardContent className="p-6 md:p-8 flex items-center justify-between relative z-10">
                  <div className="flex items-center gap-6">
                    {/* أيقونة الترتيب */}
                    <div
                      className={`w-20 h-20 flex items-center justify-center rounded-[1.5rem] shadow-inner border border-white/10 ${
                        player.rank <= 3 ? "bg-background/40" : "bg-background/20"
                      }`}
                    >
                      {getRankIcon(player.rank)}
                    </div>

                    {/* بيانات الطالب */}
                    <div>
                      <h3
                        className={`text-2xl md:text-3xl font-black ${
                          player.rank <= 3 ? "" : "text-foreground"
                        }`}
                      >
                        المجند #{player.user_id}
                      </h3>
                      {player.rank <= 3 && (
                        <span className="text-sm font-black flex items-center gap-1 mt-2 opacity-90 bg-background/30 w-fit px-3 py-1 rounded-lg border border-white/10">
                          <Flame className="w-4 h-4 animate-pulse" /> تصنيف النخبة
                        </span>
                      )}
                      {player.username && (
                        <p className="text-sm text-muted-foreground mt-1">
                          {player.username}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* نقاط الخبرة XP */}
                  <div className="text-right flex flex-col items-end">
                    <div className="text-4xl md:text-5xl font-black drop-shadow-md tracking-tighter">
                      {Number(player.total_xp).toLocaleString("en-US")}
                    </div>
                    <span className="text-sm font-black opacity-70 tracking-widest uppercase mt-1">
                      نقطة (XP)
                    </span>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))
        )}
      </motion.div>
    </motion.div>
  );
}