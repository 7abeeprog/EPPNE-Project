// app/(dashboard)/auth/login/page.tsx
"use client";

import { motion } from "framer-motion";
import { Shield, Lock } from "lucide-react";
import { LoginForm } from "@/components/auth/LoginForm";
import Link from "next/link";

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

export default function LoginPage() {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className="min-h-screen flex items-center justify-center p-4 md:p-8 bg-background relative"
    >
      {/* خلفية نيون زجاجية */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(var(--primary-rgb),0.08),_transparent_70%)] pointer-events-none -z-10" />
      <div className="absolute top-0 right-0 w-96 h-96 bg-primary/10 blur-[120px] rounded-full pointer-events-none -z-10" />
      <div className="absolute bottom-0 left-0 w-72 h-72 bg-emerald-500/10 blur-[100px] rounded-full pointer-events-none -z-10" />

      <motion.div
        variants={itemVariants}
        className="w-full max-w-md"
      >
        <div className="text-center mb-8">
          <div className="inline-flex p-4 bg-primary/10 rounded-2xl border border-primary/20 shadow-[0_0_30px_rgba(var(--primary-rgb),0.15)] mb-4">
            <Shield className="h-12 w-12 text-primary" />
          </div>
          <h1 className="text-3xl md:text-4xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-primary">
            منصة EPPNE
          </h1>
          <p className="text-muted-foreground mt-2 text-lg font-medium">
            تسجيل الدخول إلى المنصة السيادية
          </p>
        </div>

        <LoginForm />

        <p className="text-center text-sm text-muted-foreground mt-6">
          ليس لديك حساب؟{' '}
          <Link href="/auth/register" className="text-primary font-bold hover:underline transition-colors">
            إنشاء حساب جديد
          </Link>
        </p>
      </motion.div>
    </motion.div>
  );
}