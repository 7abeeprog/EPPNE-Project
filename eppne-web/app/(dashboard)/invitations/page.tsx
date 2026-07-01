// app/(dashboard)/invitations/page.tsx
'use client';

import { useInvitationStats } from '@/hooks/invitations/useStats';
import { useLeads } from '@/hooks/invitations/useLeads';
import { useCampaigns } from '@/hooks/invitations/useCampaigns';
import { useTickets } from '@/hooks/invitations/useTickets';
import { Loader2, Mail, Users, Megaphone, Ticket, TrendingUp, Clock } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

export default function InvitationsDashboard() {
  const { data: stats, isLoading: statsLoading } = useInvitationStats();
  const { data: leads, isLoading: leadsLoading } = useLeads({ status: 'NEW', limit: 5 });
  const { data: campaigns, isLoading: campaignsLoading } = useCampaigns({ status: 'ACTIVE', limit: 5 });
  const { data: tickets, isLoading: ticketsLoading } = useTickets({ status: 'OPEN', limit: 5 });

  const isLoading = statsLoading || leadsLoading || campaignsLoading || ticketsLoading;

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const statCards = [
    { label: 'الدعوات المرسلة', value: stats?.sent_invitations || 0, icon: Mail, color: 'text-blue-500' },
    { label: 'نسبة التحويل', value: `${stats?.conversion_rate?.toFixed(1) || 0}%`, icon: TrendingUp, color: 'text-emerald-500' },
    { label: 'العملاء المحتملون', value: stats?.total_leads || 0, icon: Users, color: 'text-amber-500' },
    { label: 'الحملات النشطة', value: stats?.active_campaigns || 0, icon: Megaphone, color: 'text-purple-500' },
    { label: 'تذاكر مفتوحة', value: stats?.open_tickets || 0, icon: Ticket, color: 'text-red-500' },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">📧 خدمة العملاء والتسويق</h1>
          <p className="text-sm text-muted-foreground/70">إدارة العملاء المحتملين، الحملات، والدعوات الذكية</p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/invitations/invitations/create"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
          >
            <Mail className="w-4 h-4" />
            دعوة جديدة
          </Link>
          <Link
            href="/invitations/leads/create"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors"
          >
            <Users className="w-4 h-4" />
            عميل جديد
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {statCards.map((stat, idx) => (
          <div key={idx} className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
            <div className="flex items-center gap-2">
              <stat.icon className={cn("w-4 h-4", stat.color)} />
              <span className="text-xs text-muted-foreground/50">{stat.label}</span>
            </div>
            <p className="mt-2 text-lg font-bold text-foreground/90">{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          href="/invitations/leads"
          className="p-6 rounded-2xl bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <Users className="w-8 h-8 mx-auto text-blue-500" />
          <h3 className="mt-2 font-medium">العملاء المحتملون</h3>
          <p className="text-sm text-muted-foreground/50">إدارة العملاء والتفاعلات</p>
        </Link>
        <Link
          href="/invitations/campaigns"
          className="p-6 rounded-2xl bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <Megaphone className="w-8 h-8 mx-auto text-purple-500" />
          <h3 className="mt-2 font-medium">الحملات التسويقية</h3>
          <p className="text-sm text-muted-foreground/50">إنشاء وإدارة الحملات</p>
        </Link>
        <Link
          href="/invitations/tickets"
          className="p-6 rounded-2xl bg-gradient-to-br from-red-500/10 to-orange-500/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <Ticket className="w-8 h-8 mx-auto text-red-500" />
          <h3 className="mt-2 font-medium">تذاكر الدعم</h3>
          <p className="text-sm text-muted-foreground/50">إدارة طلبات الدعم الفني</p>
        </Link>
      </div>
    </div>
  );
}