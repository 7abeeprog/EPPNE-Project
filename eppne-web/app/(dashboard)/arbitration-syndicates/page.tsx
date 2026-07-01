// app/(dashboard)/arbitration-syndicates/page.tsx
'use client';

import { useMyCases } from '@/hooks/arbitration-syndicates/useCases';
import { useSyndicates } from '@/hooks/arbitration-syndicates/useSyndicates';
import { useElections } from '@/hooks/arbitration-syndicates/useElections';
import { useMyLicenses } from '@/hooks/arbitration-syndicates/useLicenses';
import { Loader2, Scale, Building2, Users, Vote } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

export default function ArbitrationSyndicatesDashboard() {
  const { data: cases, isLoading: cLoading } = useMyCases();
  const { data: syndicates, isLoading: sLoading } = useSyndicates();
  const { data: elections, isLoading: eLoading } = useElections({ status: 'VOTING' });
  const { data: licenses, isLoading: lLoading } = useMyLicenses();

  const isLoading = cLoading || sLoading || eLoading || lLoading;

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const stats = [
    { label: 'قضاياي', value: cases?.length || 0, icon: Scale, color: 'text-amber-500' },
    { label: 'النقابات', value: syndicates?.length || 0, icon: Building2, color: 'text-blue-500' },
    { label: 'تراخيصي', value: licenses?.length || 0, icon: Users, color: 'text-emerald-500' },
    { label: 'انتخابات مفتوحة', value: elections?.length || 0, icon: Vote, color: 'text-purple-500' },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">⚖️ نقابات التحكيم</h1>
          <p className="text-sm text-muted-foreground/70">العدالة الرقمية والحوكمة النقابية</p>
        </div>
        <Link
          href="/arbitration-syndicates/cases/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Scale className="w-4 h-4" />
          قضية جديدة
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
          href="/arbitration-syndicates/cases"
          className="p-6 rounded-2xl bg-gradient-to-br from-amber-500/10 to-orange-500/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <Scale className="w-8 h-8 mx-auto text-amber-500" />
          <h3 className="mt-2 font-medium">قضاياي</h3>
          <p className="text-sm text-muted-foreground/50">إدارة قضايا التحكيم</p>
        </Link>
        <Link
          href="/arbitration-syndicates/syndicates"
          className="p-6 rounded-2xl bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <Building2 className="w-8 h-8 mx-auto text-blue-500" />
          <h3 className="mt-2 font-medium">النقابات</h3>
          <p className="text-sm text-muted-foreground/50">استكشاف النقابات والانضمام</p>
        </Link>
        <Link
          href="/arbitration-syndicates/elections"
          className="p-6 rounded-2xl bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <Vote className="w-8 h-8 mx-auto text-purple-500" />
          <h3 className="mt-2 font-medium">الانتخابات</h3>
          <p className="text-sm text-muted-foreground/50">المشاركة في الانتخابات النقابية</p>
        </Link>
      </div>
    </div>
  );
}