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
import { useNotificationStore } from "@/store/notification-store";
import { Badge } from "@/components/ui/badge";

export function Navbar() {
  const { user } = useAuthStore();
  const { unreadCount, notifications } = useNotificationStore();

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

          {/* 🟢 مركز الإشعارات السيادية */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="relative rounded-full h-10 w-10 bg-background/50 border border-white/5 hover:bg-primary/10 hover:text-primary transition-all shadow-inner">
                <Bell className="h-5 w-5" />
                {unreadCount > 0 && (
                  <Badge className="absolute -top-1 -right-1 px-1.5 min-w-5 h-5 flex items-center justify-center bg-rose-500 text-white rounded-full border-2 border-background animate-pulse shadow-[0_0_10px_rgba(244,63,94,0.6)]">
                    {unreadCount > 99 ? "99+" : unreadCount}
                  </Badge>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-[320px] md:w-[380px] rounded-3xl bg-card/80 backdrop-blur-3xl border-white/10 shadow-[0_15px_40px_rgba(0,0,0,0.2)] p-2 animate-in fade-in zoom-in-95 duration-200">
              <DropdownMenuLabel className="flex items-center gap-2 px-3 py-3 text-lg font-black text-foreground">
                <div className="p-1.5 bg-primary/10 rounded-lg border border-primary/20">
                  <Bell className="h-4 w-4 text-primary" />
                </div>
                مركز الإشعارات السيادية
              </DropdownMenuLabel>
              <DropdownMenuSeparator className="bg-white/5" />
              
              <div className="max-h-[350px] overflow-y-auto pr-1 custom-scrollbar">
                {notifications.length === 0 ? (
                  <div className="p-10 text-center flex flex-col items-center gap-3 opacity-70">
                    <div className="p-4 bg-muted/20 rounded-full">
                      <Bell className="h-8 w-8 text-muted-foreground/50" />
                    </div>
                    <span className="text-sm font-bold text-muted-foreground">لا توجد تحركات مسجلة حالياً</span>
                  </div>
                ) : (
                  notifications.slice(0, 5).map((notif) => (
                    <DropdownMenuItem key={notif.id} className="flex flex-col items-start p-3 mb-1.5 rounded-2xl focus:bg-primary/5 focus:text-foreground cursor-pointer transition-colors border border-transparent hover:border-white/5">
                      <div className="flex items-center gap-2 font-black text-sm mb-1 text-foreground/90">
                        <span className="w-2 h-2 rounded-full bg-primary animate-pulse shadow-[0_0_5px_rgba(var(--primary-rgb),0.8)]" />
                        {notif.title}
                      </div>
                      <div className="text-xs font-medium text-muted-foreground line-clamp-2 pl-4 leading-relaxed">
                        {notif.body}
                      </div>
                      <div className="text-[10px] font-bold text-muted-foreground/40 mt-2 pl-4 uppercase tracking-wider">
                        {new Date(notif.createdAt).toLocaleString('ar-EG')}
                      </div>
                    </DropdownMenuItem>
                  ))
                )}
              </div>
            </DropdownMenuContent>
          </DropdownMenu>

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
              
              <DropdownMenuItem className="rounded-xl focus:bg-rose-500/10 focus:text-rose-500 cursor-pointer p-3 mt-1 group">
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