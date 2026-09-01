// components/zamakana/PledgeForm.tsx
'use client';

import { useState } from 'react';
import { usePledgeTime } from '@/hooks/zamakana/usePledges';
import { X, Loader2, Clock } from 'lucide-react';

interface PledgeFormProps {
  isOpen: boolean;
  onClose: () => void;
  campaignId: number;
}

export default function PledgeForm({ isOpen, onClose, campaignId }: PledgeFormProps) {
  const [pledgedHours, setPledgedHours] = useState('');
  const [skillCategory, setSkillCategory] = useState('');

  const pledgeTime = usePledgeTime();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const hours = Number(pledgedHours);
    if (!hours || hours <= 0) return;
    pledgeTime.mutate(
      {
        campaign_id: campaignId,
        pledged_hours: hours,
        skill_category: skillCategory || undefined,
      },
      {
        onSuccess: () => {
          onClose();
          setPledgedHours('');
          setSkillCategory('');
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
          <Clock className="w-5 h-5 text-primary" />
          تعهد بالساعات
        </h3>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="text-sm text-muted-foreground/60">عدد الساعات</label>
            <input
              type="number"
              min={0.5}
              step={0.5}
              value={pledgedHours}
              onChange={(e) => setPledgedHours(e.target.value)}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              placeholder="مثال: 5"
              required
            />
          </div>

          <div>
            <label className="text-sm text-muted-foreground/60">فئة المهارة (اختياري)</label>
            <input
              type="text"
              value={skillCategory}
              onChange={(e) => setSkillCategory(e.target.value)}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              placeholder="مثال: تصميم، برمجة، تعليم"
            />
          </div>

          <button
            type="submit"
            disabled={pledgeTime.isPending || !pledgedHours}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
          >
            {pledgeTime.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Clock className="w-4 h-4" />}
            تأكيد التعهد
          </button>
        </form>
      </div>
    </div>
  );
}
