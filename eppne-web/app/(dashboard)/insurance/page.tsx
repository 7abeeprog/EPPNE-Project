// app/(dashboard)/insurance/page.tsx
'use client';

import { usePolicies } from '@/hooks/insurance/usePolicies';
import { useMySubscriptions } from '@/hooks/insurance/useSubscriptions';
import { useMyClaims } from '@/hooks/insurance/useClaims';
import { useMyPensions } from '@/hooks/insurance/usePensions';
import { Loader2, Shield, FileText, AlertTriangle, DollarSign, Users } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

export default function InsuranceDashboard() {
  const { data: policies, isLoading: pLoading } = usePolicies({ is_active: true });
  const { data: subscriptions, isLoading: sLoading } = useMySubscriptions();
  const { data: claims, isLoading: cLoading } = useMyClaims();
  const { data: pensions, isLoading: peLoading } = useMyPensions();

  const isLoading = pLoading || sLoading || cLoading || peLoading;

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const stats = [
    { label: 'بوالص نشطة', value: policies?.length || 0, icon: Shield, color: 'text-blue-500' },
    { label: 'اشتراكاتي', value: subscriptions?.length || 0, icon: FileText, color: 'text-emerald-500' },
    { label: 'مطالباتي', value: claims?.length || 0, icon: AlertTriangle, color: 'text-amber-500' },
    { label: 'معاشاتي', value: pensions?.length || 0, icon: DollarSign, color: 'text-purple-500' },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">🛡️ التأمين السيادي</h1>
          <p className="text-sm text-muted-foreground/70">إدارة بوالص التأمين، الاشتراكات، والمطالبات</p>
        </div>
        <Link
          href="/insurance/policies"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Shield className="w-4 h-4" />
          استعراض البوالص
        </Link>
      </div>

      {/* الإحصائيات */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map((stat, idx) => (
          <div key={idx} className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
            <div className="flex items-center gap-2">
              <stat.icon className={cn("w-4 h-4", stat.color)} />
              <span className="text-xs text-muted-foreground/50">{stat.label}</span>
            </div>
            <p className="mt-2 text-lg font-bold text-foreground/90">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* روابط سريعة */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          href="/insurance/subscriptions"
          className="p-6 rounded-2xl bg-gradient-to-br from-emerald-500/10 to-teal-500/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <FileText className="w-8 h-8 mx-auto text-emerald-500" />
          <h3 className="mt-2 font-medium">اشتراكاتي</h3>
          <p className="text-sm text-muted-foreground/50">إدارة بوالصك النشطة</p>
        </Link>
        <Link
          href="/insurance/claims"
          className="p-6 rounded-2xl bg-gradient-to-br from-amber-500/10 to-orange-500/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <AlertTriangle className="w-8 h-8 mx-auto text-amber-500" />
          <h3 className="mt-2 font-medium">مطالباتي</h3>
          <p className="text-sm text-muted-foreground/50">تقديم ومتابعة المطالبات</p>
        </Link>
        <Link
          href="/insurance/pensions"
          className="p-6 rounded-2xl bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <DollarSign className="w-8 h-8 mx-auto text-purple-500" />
          <h3 className="mt-2 font-medium">معاشاتي</h3>
          <p className="text-sm text-muted-foreground/50">متابعة المعاشات الشهرية</p>
        </Link>
      </div>
    </div>
  );
}