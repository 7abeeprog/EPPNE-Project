// app/(dashboard)/digital-twin/page.tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { getTwinConfig, getTimeCapsule, getMilestones } from '@/services/digital-twin';
import { useTwinConfig } from '@/hooks/digital-twin/useTwinConfig';
import { Loader2, Bot, Shield, Clock, FileText, Heart, Users } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

export default function DigitalTwinDashboard() {
  const { data: config, isLoading: configLoading } = useQuery({
    queryKey: ['twin-config'],
    queryFn: () => getTwinConfig().then(res => res.data),
  });

  const { data: capsule } = useQuery({
    queryKey: ['time-capsule'],
    queryFn: () => getTimeCapsule().then(res => res.data),
  });

  const { data: milestones } = useQuery({
    queryKey: ['milestones'],
    queryFn: () => getMilestones().then(res => res.data),
  });

  if (configLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const cards = [
    {
      label: 'حالة التوأم',
      value: config?.is_active ? '🟢 نشط' : '🔴 غير نشط',
      icon: Bot,
      href: '/digital-twin/config',
      color: config?.is_active ? 'text-emerald-500' : 'text-red-500',
    },
    {
      label: 'الخزنة الزمنية',
      value: capsule?.status || 'غير منشأة',
      icon: Clock,
      href: '/digital-twin/legacy',
      color: capsule?.status === 'ALIVE' ? 'text-emerald-500' : 'text-amber-500',
    },
    {
      label: 'الوصية الرقمية',
      value: config?.id ? 'موجودة' : 'غير منشأة',
      icon: FileText,
      href: '/digital-twin/legacy',
      color: config?.id ? 'text-blue-500' : 'text-muted-foreground',
    },
    {
      label: 'المحطات الحيوية',
      value: `${milestones?.length || 0} محطة`,
      icon: Heart,
      href: '/digital-twin/milestones',
      color: 'text-rose-500',
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">🧬 التوأم الرقمي</h1>
          <p className="text-sm text-muted-foreground/70">نسختك الرقمية الذكية وإرثك السيادي</p>
        </div>
        <Link
          href="/digital-twin/config"
          className="px-4 py-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors text-sm font-medium"
        >
          ⚙️ إدارة التوأم
        </Link>
      </div>

      {/* البطاقات */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {cards.map((card, idx) => (
          <Link
            key={idx}
            href={card.href}
            className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all duration-300"
          >
            <div className="flex items-center gap-2">
              <card.icon className={cn("w-5 h-5", card.color)} />
              <span className="text-xs text-muted-foreground/50">{card.label}</span>
            </div>
            <p className={cn("mt-2 text-sm font-medium", card.color)}>{card.value}</p>
          </Link>
        ))}
      </div>

      {/* حالة أوراكل الموت */}
      <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <div className="flex items-center gap-2 text-sm text-muted-foreground/60">
          <Shield className="w-4 h-4" />
          <span>أوراكل الموت</span>
        </div>
        <div className="flex items-center gap-2 mt-1">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-sm text-foreground/80">المراقبة نشطة</span>
          <span className="text-xs text-muted-foreground/40 ml-2">
            آخر نبضة: {capsule?.last_heartbeat_at ? new Date(capsule.last_heartbeat_at).toLocaleDateString('ar-EG') : '—'}
          </span>
        </div>
      </div>

      {/* المحطات الحيوية الأخيرة */}
      {milestones && milestones.length > 0 && (
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <h3 className="text-sm font-medium text-foreground/70 mb-3">📜 آخر المحطات الحيوية</h3>
          <div className="space-y-2">
            {milestones.slice(0, 3).map((m) => (
              <div key={m.id} className="flex items-center justify-between text-sm border-b border-white/5 pb-2 last:border-0">
                <span className="text-foreground/80">{m.title}</span>
                <span className="text-xs text-muted-foreground/50">
                  {new Date(m.occurrence_date).toLocaleDateString('ar-EG')}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}