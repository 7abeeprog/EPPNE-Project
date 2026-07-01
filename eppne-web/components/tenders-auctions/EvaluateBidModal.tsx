// components/tenders-auctions/EvaluateBidModal.tsx
'use client';

import { useState } from 'react';
import { useEvaluateBid } from '@/hooks/tenders-auctions/useEvaluateBid';
import { X, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';

interface EvaluateBidModalProps {
  isOpen: boolean;
  onClose: () => void;
  bidId: number;
}

export default function EvaluateBidModal({ isOpen, onClose, bidId }: EvaluateBidModalProps) {
  const [score, setScore] = useState(70);
  const evaluateBid = useEvaluateBid();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const idempotencyKey = `evaluate-${bidId}-${uuidv4()}`;
    evaluateBid.mutate(
      {
        bidId,
        data: { technical_score: score },
        idempotencyKey,
      },
      {
        onSuccess: () => {
          onClose();
          setScore(70);
        },
      }
    );
  };

  if (!isOpen) return null;

  const isAccepted = score >= 70;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200 p-4">
      <div className="relative w-full max-w-md p-6 rounded-3xl bg-card/80 backdrop-blur-3xl border border-white/15 shadow-[0_20px_80px_-20px_rgba(0,0,0,0.6)] animate-in zoom-in-95 duration-200">
        <button onClick={onClose} className="absolute top-3 right-3 p-1 rounded-lg hover:bg-white/10 transition-colors">
          <X className="w-4 h-4 text-muted-foreground/60" />
        </button>

        <h3 className="text-lg font-bold text-foreground/90 flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-primary" />
          تقييم العطاء
        </h3>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="text-sm text-muted-foreground/60">الدرجة الفنية (0-100)</label>
            <div className="flex items-center gap-4 mt-1.5">
              <input
                type="range"
                min="0"
                max="100"
                value={score}
                onChange={(e) => setScore(parseInt(e.target.value))}
                className="flex-1 accent-primary"
              />
              <span className={cn(
                "text-lg font-bold min-w-[50px] text-center",
                isAccepted ? "text-emerald-500" : "text-red-500"
              )}>
                {score}
              </span>
            </div>
            <p className="text-xs text-muted-foreground/40 mt-1">
              {isAccepted ? '✅ مقبول فنياً (≥70)' : '❌ مرفوض فنياً (<70)'}
            </p>
          </div>

          <button
            type="submit"
            disabled={evaluateBid.isPending}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
          >
            {evaluateBid.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
            تأكيد التقييم
          </button>
        </form>
      </div>
    </div>
  );
}