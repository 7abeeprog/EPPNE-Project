// app/(dashboard)/tourism-sports/page.tsx
'use client';

import { useDestinations } from '@/hooks/tourism-sports/useDestinations';
import { usePrograms } from '@/hooks/tourism-sports/usePrograms';
import { useEvents } from '@/hooks/tourism-sports/useEvents';
import { useTransfers } from '@/hooks/tourism-sports/useTransfers';
import { Loader2, Globe, Calendar, Ticket, Users, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

export default function TourismSportsDashboard() {
  const { data: destinations, isLoading: dLoading } = useDestinations();
  const { data: programs, isLoading: pLoading } = usePrograms();
  const { data: events, isLoading: eLoading } = useEvents();
  const { data: transfers, isLoading: tLoading } = useTransfers();

  const isLoading = dLoading || pLoading || eLoading || tLoading;

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const stats = [
    { label: 'الوجهات', value: destinations?.length || 0, icon: Globe, color: 'text-blue-500' },
    { label: 'البرامج', value: programs?.length || 0, icon: Calendar, color: 'text-emerald-500' },
    { label: 'الفعاليات', value: events?.length || 0, icon: Ticket, color: 'text-amber-500' },
    { label: 'الانتقالات النشطة', value: transfers?.filter(t => t.status === 'BID_PLACED' || t.status === 'NEGOTIATING').length || 0, icon: Users, color: 'text-purple-500' },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90 flex items-center gap-2">
            🌍 السياحة، الترفيه، والرياضة
          </h1>
          <p className="text-sm text-muted-foreground/70">استكشف الوجهات، الفعاليات، وعالم الرياضة</p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/tourism-sports/destinations"
            className="px-4 py-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors"
          >
            استكشف الوجهات
          </Link>
        </div>
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
          href="/tourism-sports/programs"
          className="p-6 rounded-2xl bg-gradient-to-br from-primary/10 to-secondary/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <Calendar className="w-8 h-8 mx-auto text-primary" />
          <h3 className="mt-2 font-medium">البرامج السياحية</h3>
          <p className="text-sm text-muted-foreground/50">احجز مغامرتك القادمة</p>
        </Link>
        <Link
          href="/tourism-sports/events"
          className="p-6 rounded-2xl bg-gradient-to-br from-amber-500/10 to-orange-500/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <Ticket className="w-8 h-8 mx-auto text-amber-500" />
          <h3 className="mt-2 font-medium">الفعاليات</h3>
          <p className="text-sm text-muted-foreground/50">احصل على تذاكر VIP</p>
        </Link>
        <Link
          href="/tourism-sports/sports/transfers"
          className="p-6 rounded-2xl bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <Users className="w-8 h-8 mx-auto text-purple-500" />
          <h3 className="mt-2 font-medium">سوق الانتقالات</h3>
          <p className="text-sm text-muted-foreground/50">صفقات اللاعبين</p>
        </Link>
      </div>
    </div>
  );
}