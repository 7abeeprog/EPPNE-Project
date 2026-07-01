// app/(dashboard)/privacy/erasure/page.tsx
"use client";

import { motion, Variants } from "framer-motion";
import { Trash2, Shield } from "lucide-react"; // تم إضافة Shield هنا
import { ErasureRequestForm } from "@/components/privacy/ErasureRequestForm";
import { ErasureRequestList } from "@/components/privacy/ErasureRequestList";

// ✅ تعريف الحركات
const containerVariants: Variants = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: { staggerChildren: 0.1 },
    },
};

const itemVariants: Variants = {
    hidden: { opacity: 0, y: 20 },
    show: {
        opacity: 1,
        y: 0,
        transition: { type: "spring", stiffness: 300, damping: 24 },
    },
};

export default function ErasurePage() {
    return (
        <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="show"
            className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative"
        >
            {/* خلفية نيون زجاجية */}
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(239,68,68,0.05),_transparent_80%)] pointer-events-none -z-10" />

            {/* رأس الصفحة */}
            <motion.div
                variants={itemVariants}
                className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10"
            >
                <div className="absolute top-0 right-0 w-72 h-72 bg-destructive/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse" />
                <div className="flex items-center gap-6">
                    <div className="p-4 bg-destructive/10 rounded-2xl border border-destructive/20 shadow-inner">
                        <Shield className="h-12 w-12 text-destructive" />
                    </div>
                    <div>
                        <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-destructive drop-shadow-sm">
                            طلبات محو البيانات
                        </h1>
                        <p className="text-muted-foreground mt-2 text-lg md:text-xl font-medium">
                            إدارة طلبات حذف بياناتك الشخصية من المنصة.
                        </p>
                    </div>
                </div>
            </motion.div>

            {/* نموذج إنشاء طلب المحو */}
            <motion.div variants={itemVariants}>
                <ErasureRequestForm />
            </motion.div>

            {/* قائمة طلبات المحو */}
            <motion.div variants={itemVariants}>
                <ErasureRequestList />
            </motion.div>
        </motion.div>
    );
}