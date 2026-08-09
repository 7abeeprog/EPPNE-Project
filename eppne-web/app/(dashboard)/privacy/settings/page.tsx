// app/(dashboard)/privacy/settings/page.tsx
"use client";

import { motion } from "framer-motion";
import { Shield, Monitor, AlertCircle } from "lucide-react";
import { PrivacySettingsForm } from "@/components/privacy/PrivacySettingsForm";
import { SessionsList } from "@/components/identity/SessionsList";
import { usePrivacySettings } from "@/hooks/privacy/usePrivacySettings";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

// ✅ تعريف الحركات
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

export default function PrivacySettingsPage() {
    const { data: settings, isLoading, error, refetch } = usePrivacySettings();

    // ✅ حالة التحميل
    if (isLoading) {
        return (
            <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-4xl mx-auto relative">
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(139,92,246,0.05),_transparent_80%)] pointer-events-none -z-10" />

                {/* Skeleton للهيدر */}
                <div className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10">
                    <Skeleton className="h-10 w-48 bg-primary/10" />
                    <Skeleton className="h-6 w-72 mt-2 bg-primary/10" />
                </div>

                {/* Skeleton للنموذج */}
                <div className="space-y-6 bg-card/40 backdrop-blur-xl border border-white/10 rounded-[2rem] p-8 shadow-lg">
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="flex items-center justify-between p-4 bg-background/40 rounded-xl border border-white/5">
                            <div className="space-y-2">
                                <Skeleton className="h-5 w-32 bg-primary/10" />
                                <Skeleton className="h-4 w-48 bg-primary/10" />
                            </div>
                            <Skeleton className="h-6 w-12 bg-primary/10 rounded-full" />
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    // ✅ معالجة الأخطاء
    if (error) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] p-6 text-center">
                <div className="p-6 bg-destructive/10 rounded-full mb-6 border border-destructive/20">
                    <AlertCircle className="h-16 w-16 text-destructive" />
                </div>
                <h2 className="text-3xl font-bold mb-2">فشل في تحميل الإعدادات</h2>
                <p className="text-muted-foreground text-lg mb-8 max-w-md">
                    {error.message || "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."}
                </p>
                <Button
                    onClick={() => refetch()}
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
            className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-4xl mx-auto relative"
        >
            {/* خلفية نيون زجاجية */}
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(139,92,246,0.05),_transparent_80%)] pointer-events-none -z-10" />

            {/* رأس الصفحة */}
            <motion.div
                variants={itemVariants}
                className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10"
            >
                <div className="absolute top-0 right-0 w-72 h-72 bg-purple-500/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse" />
                <div className="flex items-center gap-6">
                    <div className="p-4 bg-purple-500/10 rounded-2xl border border-purple-500/20 shadow-inner">
                        <Shield className="h-12 w-12 text-purple-500" />
                    </div>
                    <div>
                        <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-purple-500 drop-shadow-sm">
                            إعدادات الخصوصية
                        </h1>
                        <p className="text-muted-foreground mt-2 text-lg md:text-xl font-medium">
                            تحكم في كيفية معالجة بياناتك ومشاركتها مع المنصة.
                        </p>
                    </div>
                </div>
            </motion.div>

            {/* نموذج إعدادات الخصوصية */}
            <motion.div variants={itemVariants}>
                <PrivacySettingsForm initialSettings={settings} />
            </motion.div>

            {/* 🟢 قسم الجلسات النشطة */}
            <motion.div variants={itemVariants}>
              <Card className="border-white/10 bg-card/40 backdrop-blur-xl shadow-lg rounded-[2rem] overflow-hidden">
                <CardContent className="p-6 md:p-8">
                  <h2 className="text-2xl font-black flex items-center gap-3 text-foreground mb-6">
                    <Monitor className="h-6 w-6 text-primary" />
                    الجلسات النشطة
                  </h2>
                  <SessionsList />
                </CardContent>
              </Card>
            </motion.div>
        </motion.div>
    );
}