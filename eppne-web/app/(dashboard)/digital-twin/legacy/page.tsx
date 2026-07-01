// app/(dashboard)/digital-twin/legacy/page.tsx
'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTimeCapsule, createTimeCapsule, sendHeartbeat, createDigitalWill } from '@/services/digital-twin';
import { Loader2, Clock, Heart, FileText, Users, Plus, Send } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns/ar';

export default function LegacyPage() {
  const queryClient = useQueryClient();
  const [showCapsuleForm, setShowCapsuleForm] = useState(false);
  const [showWillForm, setShowWillForm] = useState(false);

  const { data: capsule, isLoading } = useQuery({
    queryKey: ['time-capsule'],
    queryFn: () => getTimeCapsule().then(res => res.data),
  });

  const heartbeatMutation = useMutation({
    mutationFn: sendHeartbeat,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['time-capsule'] }),
  });

  if (isLoading) {
    return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>;
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">🏛️ الإرث الرقمي</h1>
          <p className="text-sm text-muted-foreground/70">الخزنة الزمنية، الوصية، وإدارة الأصول بعد الوفاة</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowCapsuleForm(true)}
            className="px-4 py-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors text-sm font-medium"
          >
            <Plus className="w-4 h-4 inline mr-1" />
            خزنة جديدة
          </button>
        </div>
      </div>

      {/* حالة الخزنة الزمنية */}
      <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Clock className="w-5 h-5 text-primary/60" />
            <div>
              <h3 className="font-medium text-foreground/80">الخزنة الزمنية</h3>
              <p className="text-sm text-muted-foreground/60">
                {capsule ? `نشطة منذ ${formatDistanceToNow(new Date(capsule.created_at), { addSuffix: true })}` : 'غير منشأة'}
              </p>
            </div>
          </div>
          {capsule && (
            <button
              onClick={() => heartbeatMutation.mutate()}
              disabled={heartbeatMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/20 text-emerald-500 border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors text-sm"
            >
              {heartbeatMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Heart className="w-4 h-4" />}
              نبضة حياة
            </button>
          )}
        </div>

        {capsule && (
          <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div className="p-2 rounded-xl bg-white/5">
              <span className="text-muted-foreground/50">الحالة</span>
              <p className="text-foreground/80 font-medium">{capsule.status === 'ALIVE' ? '🟢 نشط' : '🔴 مفعل'}</p>
            </div>
            <div className="p-2 rounded-xl bg-white/5">
              <span className="text-muted-foreground/50">آخر نبضة</span>
              <p className="text-foreground/80 font-medium">
                {capsule.last_heartbeat_at ? formatDistanceToNow(new Date(capsule.last_heartbeat_at), { addSuffix: true }) : '—'}
              </p>
            </div>
            <div className="p-2 rounded-xl bg-white/5">
              <span className="text-muted-foreground/50">الفاصل الزمني</span>
              <p className="text-foreground/80 font-medium">كل {capsule.heartbeat_interval_days} يوم</p>
            </div>
          </div>
        )}
      </div>

      {/* الوصية الرقمية */}
      <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-blue-500/60" />
            <div>
              <h3 className="font-medium text-foreground/80">الوصية الرقمية</h3>
              <p className="text-sm text-muted-foreground/60">موثقة بتقنية NFT على السلسلة</p>
            </div>
          </div>
          <button
            onClick={() => setShowWillForm(true)}
            className="px-4 py-2 rounded-xl bg-blue-500/20 text-blue-500 border border-blue-500/30 hover:bg-blue-500/30 transition-colors text-sm"
          >
            إنشاء وصية
          </button>
        </div>
      </div>
    </div>
  );
}