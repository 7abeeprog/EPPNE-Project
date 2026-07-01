// app/(dashboard)/privacy/admin/erasure/page.tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ShieldAlert, Users, Clock } from "lucide-react";
import { useAuthStore } from "@/store/auth-store";
import { PendingErasureRequests } from "@/components/privacy/PendingErasureRequests";
import { Button } from "@/components/ui/button";

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

// ✅ الصلاحيات المطلوبة
const ALLOWED_ROLES = ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"];

export default function AdminErasurePage() {
    const router = useRouter();
    const { user } = useAuthStore();
    const userRole = user?.system_role || "STUDENT";

    // ✅ التحقق من الصلاحيات (RBAC) وإعادة التوجيه
    useEffect(() => {
        if (!ALLOWED_ROLES.includes(userRole)) {
            router.replace("/privacy/erasure");
        }
    }, [userRole, router]);

    // ✅ إذا لم يكن مصرحاً، لا نعرض أي شيء (سيتم إعادة التوجيه)
    if (!ALLOWED_ROLES.includes(userRole)) {
        return null;
    }

    return (
        <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="show"
            className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative"
        >
            {/* خلفية نيون زجاجية */}
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(245,158,11,0.05),_transparent_80%)] pointer-events-none -z-10" />

            {/* رأس الصفحة */}
            <motion.div
                variants={itemVariants}
                className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10"
            >
                <div className="absolute top-0 right-0 w-72 h-72 bg-amber-500/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse" />
                <div className="flex items-center gap-6">
                    <div className="p-4 bg-amber-500/10 rounded-2xl border border-amber-500/20 shadow-inner">
                        <ShieldAlert className="h-12 w-12 text-amber-500" />
                    </div>
                    <div>
                        <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-amber-500 drop-shadow-sm">
                            لوحة تحكم الخصوصية
                        </h1>
                        <p className="text-muted-foreground mt-2 text-lg md:text-xl font-medium">
                            إدارة طلبات محو البيانات المعلقة.
                        </p>
                    </div>
                </div>
            </motion.div>

            {/* ✅ قائمة الطلبات المعلقة */}
            <motion.div variants={itemVariants}>
                <PendingErasureRequests />
            </motion.div>

            {/* ✅ روابط سريعة */}
            <motion.div variants={itemVariants}>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Button
                        variant="outline"
                        className="h-16 rounded-xl border-amber-500/30 text-amber-500 hover:bg-amber-500 hover:text-white transition-all font-bold text-lg"
                        onClick={() => router.push("/privacy/erasure")}
                    >
                        <Users className="mr-2 h-5 w-5" />
                        طلباتي
                    </Button>
                    <Button
                        variant="outline"
                        className="h-16 rounded-xl border-primary/30 text-primary hover:bg-primary hover:text-white transition-all font-bold text-lg"
                        onClick={() => router.push("/privacy/settings")}
                    >
                        <Clock className="mr-2 h-5 w-5" />
                        إعدادات الخصوصية
                    </Button>
                    <Button
                        variant="outline"
                        className="h-16 rounded-xl border-white/10 text-muted-foreground hover:bg-background/50 transition-all font-bold text-lg"
                        onClick={() => router.push("/dashboard")}
                    >
                        العودة إلى لوحة التحكم
                    </Button>
                </div>
            </motion.div>
        </motion.div>
    );
}