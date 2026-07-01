// app/(dashboard)/profile/page.tsx
"use client";

import { motion } from "framer-motion";
import { User, Settings, Shield, Wallet } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ProfileForm } from "@/components/identity/ProfileForm";
import { ChangePasswordForm } from "@/components/identity/ChangePasswordForm";
import { SessionsList } from "@/components/identity/SessionsList";
import { WalletCard } from "@/components/identity/WalletCard";
import { useUserProfile } from "@/hooks/identity/useUserProfile";
import { Skeleton } from "@/components/ui/skeleton";

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

export default function ProfilePage() {
  const { data: user, isLoading } = useUserProfile();

  if (isLoading) {
    return (
      <div className="flex flex-col w-full min-w-0 space-y-8 p-4 md:p-8 max-w-7xl mx-auto relative">
        <Skeleton className="h-32 w-full rounded-[2rem] bg-card/40" />
        <Skeleton className="h-96 w-full rounded-[2rem] bg-card/40" />
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
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(139,92,246,0.05),_transparent_80%)] pointer-events-none -z-10" />

      <motion.div
        variants={itemVariants}
        className="relative overflow-hidden rounded-[2rem] bg-card/40 backdrop-blur-2xl border border-primary/20 shadow-[0_0_50px_-15px_rgba(var(--primary-rgb),0.3)] p-8 md:p-10"
      >
        <div className="absolute top-0 right-0 w-72 h-72 bg-purple-500/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse" />
        <div className="flex items-center gap-6">
          <div className="p-4 bg-purple-500/10 rounded-2xl border border-purple-500/20 shadow-inner">
            <User className="h-12 w-12 text-purple-500" />
          </div>
          <div>
            <h1 className="text-3xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-foreground to-purple-500 drop-shadow-sm">
              ملفي الشخصي
            </h1>
            <p className="text-muted-foreground mt-2 text-lg md:text-xl font-medium">
              إدارة بياناتك الشخصية وإعدادات الحساب
            </p>
          </div>
        </div>
      </motion.div>

      <motion.div variants={itemVariants}>
        <Tabs defaultValue="profile" className="w-full">
          <TabsList className="bg-background/50 backdrop-blur-md border border-white/10 p-1 rounded-2xl w-full md:w-auto">
            <TabsTrigger
              value="profile"
              className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-bold"
            >
              <User className="ml-2 h-4 w-4" />
              الملف الشخصي
            </TabsTrigger>
            <TabsTrigger
              value="security"
              className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-bold"
            >
              <Shield className="ml-2 h-4 w-4" />
              الأمان
            </TabsTrigger>
            <TabsTrigger
              value="sessions"
              className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-bold"
            >
              <Settings className="ml-2 h-4 w-4" />
              الجلسات
            </TabsTrigger>
            <TabsTrigger
              value="wallet"
              className="rounded-xl data-[state=active]:bg-primary data-[state=active]:text-primary-foreground font-bold"
            >
              <Wallet className="ml-2 h-4 w-4" />
              المحفظة
            </TabsTrigger>
          </TabsList>

          <TabsContent value="profile" className="mt-6">
            <ProfileForm user={user} />
          </TabsContent>

          <TabsContent value="security" className="mt-6">
            <ChangePasswordForm />
          </TabsContent>

          <TabsContent value="sessions" className="mt-6">
            <SessionsList />
          </TabsContent>

          <TabsContent value="wallet" className="mt-6">
            <WalletCard />
          </TabsContent>
        </Tabs>
      </motion.div>
    </motion.div>
  );
}