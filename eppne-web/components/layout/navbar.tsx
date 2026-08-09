// components/layout/navbar.tsx
"use client";

import Link from "next/link";
import { ConnectWallet } from "@/components/web3/connect-wallet";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Bell, User, Settings, LogOut, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuthStore } from "@/store/auth-store";
import { useLogout } from "@/hooks/auth/useAuth";
import { useNotificationStore } from "@/store/notificationStore";
import { Badge } from "@/components/ui/badge";
import { NotificationBell } from "@/components/communications/NotificationBell";

export function Navbar() {
  const { user } = useAuthStore();
  const { unreadCount, notifications } = useNotificationStore();
  const logoutMutation = useLogout();

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/10 bg-background/40 backdrop-blur-2xl shadow-sm transition-all duration-300">
      
      {/* 🟢 خط نيون علوي خفيف يعكس طابع الـ Web3 */}
      <div className="absolute top-0 inset-x-0 h-[1px] bg-gradient-to-r from-transparent via-primary/50 to-transparent opacity-50" />

      <div className="flex h-20 items-center justify-between px-6 md:px-8">
        
        {/* المساحة اليسرى (يمكن استخدامها لاحقاً لفتات الخبز Breadcrumbs) */}
        <div className="flex-1" />

        {/* 🟢 المساحة اليمنى: أدوات القيادة */}
        <div className="flex items-center gap-3 md:gap-5">
          
          {/* محفظة Web3 (تختفي في الشاشات الصغيرة جداً) */}
          <div className="hidden sm:block">
            <ConnectWallet />
          </div>

          {/* زر الثيم الزجاجي */}
          <div className="bg-background/50 border border-white/5 rounded-full backdrop-blur-md shadow-inner">
            <ThemeToggle />
          </div>

          {/* 🟢 مركز الإشعارات السيادية - مكوّن مخصص */}
          <NotificationBell />

          {/* 🟢 الحساب التعريفي (User Profile) */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="relative h-10 w-10 rounded-full border border-primary/20 bg-primary/5 hover:bg-primary/20 transition-all shadow-[0_0_15px_rgba(var(--primary-rgb),0.15)] group">
                <User className="h-5 w-5 text-primary group-hover:scale-110 transition-transform" />
                <span className="absolute bottom-0 right-0 w-3 h-3 bg-emerald-500 border-2 border-background rounded-full shadow-sm" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-72 rounded-3xl bg-card/80 backdrop-blur-3xl border-white/10 shadow-[0_15px_40px_rgba(0,0,0,0.2)] p-2 animate-in fade-in zoom-in-95 duration-200">
              
              <div className="flex items-center gap-3 p-4 mb-2 bg-background/50 rounded-2xl border border-white/5 shadow-inner">
                <div className="h-12 w-12 rounded-xl bg-primary/20 flex items-center justify-center border border-primary/30 shrink-0">
                  <Shield className="h-6 w-6 text-primary" />
                </div>
                <div className="flex flex-col overflow-hidden">
                  <span className="text-base font-black text-foreground truncate">{user?.name_ar || user?.username || "قائد سيادي"}</span>
                  <span className="text-xs font-bold text-muted-foreground truncate">{user?.email || "sysadmin@eppne.com"}</span>
                </div>
              </div>

              <DropdownMenuSeparator className="bg-white/5" />
              
              <DropdownMenuItem asChild className="rounded-xl focus:bg-primary/10 cursor-pointer mb-1 p-3">
                <Link href="/profile" className="flex items-center gap-3 font-bold text-muted-foreground hover:text-foreground transition-colors">
                  <User className="h-4 w-4" /> الملف الشخصي
                </Link>
              </DropdownMenuItem>
              
              <DropdownMenuItem asChild className="rounded-xl focus:bg-primary/10 cursor-pointer mb-1 p-3">
                <Link href="/settings" className="flex items-center gap-3 font-bold text-muted-foreground hover:text-foreground transition-colors">
                  <Settings className="h-4 w-4" /> الإعدادات السيادية
                </Link>
              </DropdownMenuItem>

              <DropdownMenuSeparator className="bg-white/5" />
              
              <DropdownMenuItem
                onClick={() => logoutMutation.mutate()}
                disabled={logoutMutation.isPending}
                className="rounded-xl focus:bg-rose-500/10 focus:text-rose-500 cursor-pointer p-3 mt-1 group"
              >
                <div className="flex items-center gap-3 font-bold text-rose-500/80 group-hover:text-rose-500 transition-colors">
                  <LogOut className="h-4 w-4" /> إنهاء الجلسة الآمنة
                </div>
              </DropdownMenuItem>
              
            </DropdownMenuContent>
          </DropdownMenu>

        </div>
      </div>
    </header>
  );
}