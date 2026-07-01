"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuthStore } from "@/store/auth-store";
import { useEffect, useState } from "react";
import { ShieldCheck, Wallet } from "lucide-react";

export default function DashboardPage() {
  const { user, fetchMe } = useAuthStore();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadUser = async () => {
      await fetchMe();
      setLoading(false);
    };
    loadUser();
  }, [fetchMe]);

  if (loading) {
    return <div className="p-8 text-center animate-pulse">جاري تأمين الاتصال وجلب البيانات السيادية...</div>;
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        
        {/* شريط الترحيب */}
        <div className="flex items-center space-x-4 space-x-reverse mb-8">
          <div className="p-3 bg-primary/10 rounded-full">
            <ShieldCheck className="w-8 h-8 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">مركز القيادة السيادي</h1>
            <p className="text-muted-foreground mt-1">
              مرحباً بك، {user?.email || "أيها القائد"}
            </p>
          </div>
        </div>

        {/* بداية تصميم المحفظة (Wallet Skeleton) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="col-span-1 md:col-span-2 shadow-lg border-primary/20 bg-gradient-to-br from-white to-slate-50 dark:from-slate-900 dark:to-slate-950">
            <CardHeader className="pb-2">
              <CardTitle className="text-xl flex items-center gap-2">
                <Wallet className="w-5 h-5 text-primary" />
                المحفظة السيادية (EPPNE Wallet)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mt-4">
                <p className="text-sm text-muted-foreground mb-1">الرصيد الإجمالي المتاح</p>
                <div className="text-4xl font-extrabold text-foreground tracking-tighter">
                  $0.00 <span className="text-lg text-muted-foreground font-normal">USDT</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

      </div>
    </div>
  );
}