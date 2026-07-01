// app/(dashboard)/social/occasions/page.tsx
'use client';

import { useState } from 'react';
import { useOccasions, useDeleteOccasion } from '@/hooks/social/useOccasions';
import CreateOccasionModal from '@/components/social/CreateOccasionModal';
import { Loader2, Plus, Trash2, Calendar } from 'lucide-react';
import { format } from 'date-fns/ar';

export default function OccasionsPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const { data: occasions, isLoading } = useOccasions();
  const deleteOccasion = useDeleteOccasion();

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground/90">📅 المناسبات والتذكيرات</h1>
        <button
          onClick={() => setCreateOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          مناسبة جديدة
        </button>
      </div>

      {occasions?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <Calendar className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد مناسبات</p>
          <p className="text-sm">أضف مناسباتك لتتلقى تذكيرات</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {occasions?.map((occ) => (
            <div key={occ.id} className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="font-medium text-foreground/80">{occ.title || occ.occasion_type}</h4>
                  <p className="text-sm text-muted-foreground/60">{occ.description}</p>
                  <p className="text-xs text-muted-foreground/40 mt-1">
                    {format(new Date(occ.occasion_date), 'dd/MM/yyyy')}
                  </p>
                  <p className="text-xs text-muted-foreground/40">
                    {occ.is_public ? '🌍 عامة' : '🔒 خاصة'}
                  </p>
                </div>
                <button
                  onClick={() => deleteOccasion.mutate(occ.id)}
                  className="p-1.5 rounded-lg hover:bg-red-500/10 transition-colors"
                >
                  <Trash2 className="w-4 h-4 text-red-500/50 hover:text-red-500" />
                </button>
              </div>
              <div className="mt-2 text-xs text-muted-foreground/30">
                تذكير قبل {occ.remind_days_before} يوم
              </div>
            </div>
          ))}
        </div>
      )}

      <CreateOccasionModal isOpen={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}