// app/(dashboard)/academy/quiz-results/[quizId]/page.tsx
"use client";

import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { motion, Variants } from "framer-motion";

// ✅ الهوكات الجديدة
import { useQuizResults } from "@/hooks/academy-queries";
import { handleError } from "@/lib/error-handler";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  HelpCircle,
  BrainCircuit,
  Award,
  Clock,
  BarChart3,
  Loader2,
  AlertCircle,
} from "lucide-react";

// ✅ تعريف الحركات باستخدام Variants
const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
};

const cardVariants: Variants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 300, damping: 24 },
  },
};

// ✅ واجهة نتيجة السؤال
interface QuestionResult {
  text: string;
  user_answer?: string;
  correct_answer?: string;
  is_correct: boolean;
}

// ✅ واجهة نتيجة الاختبار الكاملة
interface QuizResultData {
  score: number;
  passing_score: number;
  correct_answers: number;
  wrong_answers: number;
  total_questions: number;
  time_spent?: number; // بالثواني
  questions?: QuestionResult[];
  certificate_issued?: boolean;
}

// ✅ دالة تنسيق الوقت
const formatTime = (seconds?: number): string => {
  if (!seconds || seconds <= 0) return "—";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  if (mins === 0) return `${secs} ثانية`;
  return `${mins} دقيقة و ${secs} ثانية`;
};

export default function QuizResultsPage() {
  const params = useParams();
  const router = useRouter();
  const quizId = Number(params.quizId);

  // ✅ جلب نتائج الاختبار
  const {
    data: result,
    isLoading,
    error,
  } = useQuizResults(quizId);

  // ✅ معالجة الأخطاء
  if (error) {
    const err = handleError(error, "جلب نتائج الاختبار");
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
        <div className="p-6 bg-destructive/10 rounded-full mb-6 border border-destructive/20">
          <AlertCircle className="h-16 w-16 text-destructive" />
        </div>
        <h2 className="text-3xl font-bold mb-2">فشل في تحميل النتائج</h2>
        <p className="text-muted-foreground text-lg mb-8 max-w-md">{err.message}</p>
        <Button
          onClick={() => router.back()}
          size="lg"
          className="rounded-xl h-14 px-8"
        >
          العودة
        </Button>
      </div>
    );
  }

  if (isLoading || !result) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] p-6">
        <Loader2 className="h-12 w-12 text-primary animate-spin mb-4" />
        <Skeleton className="h-64 w-full max-w-3xl rounded-[2rem] bg-card/40" />
      </div>
    );
  }

  const data = result as QuizResultData;
  const isPassed = data.score >= data.passing_score;
  const questions = data.questions || [];

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="flex flex-col w-full min-w-0 space-y-6 p-4 md:p-8 max-w-4xl mx-auto relative"
    >
      {/* خلفية نيون زجاجية */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(16,185,129,0.05),_transparent_80%)] pointer-events-none -z-10" />

      {/* زر العودة */}
      <motion.div variants={cardVariants}>
        <Button
          variant="ghost"
          onClick={() => router.back()}
          className="group flex items-center gap-2 text-muted-foreground hover:text-primary w-fit"
        >
          <ArrowLeft className="h-5 w-5 transition-transform group-hover:-translate-x-1" />
          العودة
        </Button>
      </motion.div>

      {/* بطاقة النتيجة الرئيسية */}
      <motion.div variants={cardVariants}>
        <Card
          className={`border-white/10 backdrop-blur-2xl shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] rounded-[2.5rem] overflow-hidden ${
            isPassed
              ? "bg-emerald-500/10 border-emerald-500/30"
              : "bg-destructive/10 border-destructive/30"
          }`}
        >
          <CardContent className="p-8 md:p-12 text-center">
            <div className="flex justify-center mb-6">
              <div
                className={`p-4 rounded-full ${
                  isPassed
                    ? "bg-emerald-500/20 border border-emerald-500/30"
                    : "bg-destructive/20 border border-destructive/30"
                }`}
              >
                {isPassed ? (
                  <CheckCircle className="h-16 w-16 text-emerald-500" />
                ) : (
                  <XCircle className="h-16 w-16 text-destructive" />
                )}
              </div>
            </div>

            <h1 className="text-3xl md:text-5xl font-black mb-2">
              {isPassed ? "🎉 اجتزت الاختبار بنجاح!" : "لم تجتز الاختبار"}
            </h1>

            <div className="flex items-center justify-center gap-4 mt-4">
              <div className="text-6xl md:text-7xl font-black">
                {Math.round(data.score)}%
              </div>
              <div className="text-left">
                <Badge
                  className={`${
                    isPassed
                      ? "bg-emerald-500/20 text-emerald-500 border-emerald-500/30"
                      : "bg-destructive/20 text-destructive border-destructive/30"
                  } border font-bold text-sm px-4 py-1.5`}
                >
                  {isPassed ? "✅ معتمد" : "❌ غير معتمد"}
                </Badge>
                <p className="text-sm text-muted-foreground mt-1">
                  النجاح المطلوب: {data.passing_score}%
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
              <div className="p-4 bg-background/40 rounded-xl border border-white/5">
                <p className="text-2xl font-black">{data.correct_answers}</p>
                <p className="text-xs text-muted-foreground font-bold">إجابات صحيحة</p>
              </div>
              <div className="p-4 bg-background/40 rounded-xl border border-white/5">
                <p className="text-2xl font-black">{data.wrong_answers || 0}</p>
                <p className="text-xs text-muted-foreground font-bold">إجابات خاطئة</p>
              </div>
              <div className="p-4 bg-background/40 rounded-xl border border-white/5">
                <p className="text-2xl font-black">{data.total_questions}</p>
                <p className="text-xs text-muted-foreground font-bold">إجمالي الأسئلة</p>
              </div>
              <div className="p-4 bg-background/40 rounded-xl border border-white/5">
                <p className="text-2xl font-black">{formatTime(data.time_spent)}</p>
                <p className="text-xs text-muted-foreground font-bold">الوقت المستغرق</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* إحصائيات إضافية */}
      <motion.div variants={cardVariants}>
        <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
          <CardContent className="p-6 md:p-8">
            <h2 className="text-2xl font-black flex items-center gap-3 text-foreground mb-6">
              <BarChart3 className="h-6 w-6 text-primary" />
              تحليل الأداء
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-4 bg-background/40 rounded-xl border border-white/5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-muted-foreground">درجة النجاح</span>
                  <span className="font-black">{data.passing_score}%</span>
                </div>
                <div className="mt-2 w-full bg-background/50 rounded-full h-3 overflow-hidden border border-white/5">
                  <div
                    className={`h-full rounded-full transition-all duration-1000 ${
                      isPassed ? "bg-emerald-500" : "bg-destructive"
                    }`}
                    style={{ width: `${Math.min((data.score / data.passing_score) * 100, 100)}%` }}
                  />
                </div>
              </div>

              <div className="p-4 bg-background/40 rounded-xl border border-white/5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-muted-foreground">معدل الإجابات الصحيحة</span>
                  <span className="font-black">
                    {Math.round((data.correct_answers / data.total_questions) * 100)}%
                  </span>
                </div>
                <div className="mt-2 w-full bg-background/50 rounded-full h-3 overflow-hidden border border-white/5">
                  <div
                    className="h-full rounded-full transition-all duration-1000 bg-blue-500"
                    style={{
                      width: `${Math.round((data.correct_answers / data.total_questions) * 100)}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* تفاصيل الأسئلة */}
      {questions.length > 0 && (
        <motion.div variants={cardVariants}>
          <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
            <CardContent className="p-6 md:p-8">
              <h2 className="text-2xl font-black flex items-center gap-3 text-foreground mb-6">
                <HelpCircle className="h-6 w-6 text-primary" />
                تفاصيل الأسئلة
              </h2>

              <div className="space-y-4">
                {questions.map((q: QuestionResult, index: number) => (
                  <div
                    key={index}
                    className={`p-4 rounded-xl border ${
                      q.is_correct
                        ? "bg-emerald-500/5 border-emerald-500/20"
                        : "bg-destructive/5 border-destructive/20"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <p className="font-bold text-sm">
                          السؤال {index + 1}: {q.text}
                        </p>
                        <p className="text-sm text-muted-foreground mt-1">
                          إجابتك:{" "}
                          <span
                            className={q.is_correct ? "text-emerald-500 font-bold" : "text-destructive font-bold"}
                          >
                            {q.user_answer || "لم يجب"}
                          </span>
                        </p>
                        {!q.is_correct && q.correct_answer && (
                          <p className="text-sm text-emerald-500 font-bold mt-1">
                            الإجابة الصحيحة: {q.correct_answer}
                          </p>
                        )}
                      </div>
                      <div className="shrink-0">
                        {q.is_correct ? (
                          <CheckCircle className="h-6 w-6 text-emerald-500" />
                        ) : (
                          <XCircle className="h-6 w-6 text-destructive" />
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </motion.div>
  );
}