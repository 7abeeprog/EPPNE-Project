// components/social/CreateOccasionModal.tsx
'use client';

import { useState } from 'react';
import { useCreateOccasion } from '@/hooks/social/useOccasions';
import { X, Loader2, Calendar } from 'lucide-react';

interface CreateOccasionModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CreateOccasionModal({ isOpen, onClose }: CreateOccasionModalProps) {
  const [formData, setFormData] = useState({
    occasion_type: 'BIRTHDAY',
    title: '',
    description: '',
    occasion_date: '',
    is_public: false,
    remind_days_before: 7,
  });

  const createOccasion = useCreateOccasion();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createOccasion.mutate(
      {
        ...formData,
        occasion_date: new Date(formData.occasion_date).toISOString(),
      },
      {
        onSuccess: () => {
          onClose();
          setFormData({ occasion_type: 'BIRTHDAY', title: '', description: '', occasion_date: '', is_public: false, remind_days_before: 7 });
        },
      }
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200 p-4">
      <div className="relative w-full max-w-md p-6 rounded-3xl bg-card/80 backdrop-blur-3xl border border-white/15 shadow-[0_20px_80px_-20px_rgba(0,0,0,0.6)] animate-in zoom-in-95 duration-200">
        <button onClick={onClose} className="absolute top-3 right-3 p-1 rounded-lg hover:bg-white/10 transition-colors">
          <X className="w-4 h-4 text-muted-foreground/60" />
        </button>

        <h3 className="text-lg font-bold text-foreground/90 flex items-center gap-2">
          <Calendar className="w-5 h-5 text-primary" />
          إضافة مناسبة
        </h3>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="text-sm text-muted-foreground/60">نوع المناسبة</label>
            <select
              value={formData.occasion_type}
              onChange={(e) => setFormData({ ...formData, occasion_type: e.target.value })}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            >
              <option value="BIRTHDAY">عيد ميلاد</option>
              <option value="WEDDING">عيد زواج</option>
              <option value="ANNIVERSARY">ذكرى</option>
              <option value="GRADUATION">تخرج</option>
              <option value="CUSTOM">مناسبة مخصصة</option>
            </select>
          </div>

          <div>
            <label className="text-sm text-muted-foreground/60">العنوان</label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              placeholder="مثلاً: عيد ميلاد أحمد"
            />
          </div>

          <div>
            <label className="text-sm text-muted-foreground/60">الوصف (اختياري)</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={2}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm resize-none"
              placeholder="تفاصيل المناسبة"
            />
          </div>

          <div>
            <label className="text-sm text-muted-foreground/60">التاريخ</label>
            <input
              type="date"
              value={formData.occasion_date}
              onChange={(e) => setFormData({ ...formData, occasion_date: e.target.value })}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              required
            />
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-muted-foreground/60 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.is_public}
                onChange={(e) => setFormData({ ...formData, is_public: e.target.checked })}
                className="w-4 h-4 rounded border-white/20 bg-white/5"
              />
              مناسبة عامة (تظهر للأصدقاء)
            </label>
          </div>

          <div>
            <label className="text-sm text-muted-foreground/60">التذكير قبل (أيام)</label>
            <input
              type="number"
              min="1"
              max="30"
              value={formData.remind_days_before}
              onChange={(e) => setFormData({ ...formData, remind_days_before: parseInt(e.target.value) || 7 })}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            />
          </div>

          <button
            type="submit"
            disabled={createOccasion.isPending}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
          >
            {createOccasion.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            إضافة المناسبة
          </button>
        </form>
      </div>
    </div>
  );
}