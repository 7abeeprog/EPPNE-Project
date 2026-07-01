// components/insurance/ReviewClaimModal.tsx
'use client';

import { useState } from 'react';
import { useReviewClaim } from '@/hooks/insurance/useClaims';
import { X, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';

interface ReviewClaimModalProps {
  isOpen: boolean;
  onClose: () => void;
  claimId: number;
  onSuccess?: () => void;
}

export default function ReviewClaimModal({ isOpen, onClose, claimId, onSuccess }: ReviewClaimModalProps) {
  const [approve, setApprove] = useState(true);
  const [approvedAmount, setApprovedAmount] = useState<number | undefined>(undefined);
  const [notes, setNotes] = useState('');

  const reviewClaim = useReviewClaim();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const idempotencyKey = `review-${claimId}-${uuidv4()}`;
    reviewClaim.mutate(
      {
        claimId,
        data: {
          approve,
          approved_amount: approve ? approvedAmount : undefined,
          notes: notes || undefined,
        },
        idempotencyKey,
      },
      {
        onSuccess: () => {
          onClose();
          onSuccess?.();
          setApprovedAmount(undefined);
          setNotes('');
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
          <CheckCircle className="w-5 h-5 text-primary" />
          مراجعة المطالبة
        </h3>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => setApprove(true)}
              className={cn(
                "flex-1 py-2 rounded-xl border transition-all",
                approve ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-500" : "border-white/10 text-muted-foreground/60"
              )}
            >
              ✅ قبول
            </button>
            <button
              type="button"
              onClick={() => setApprove(false)}
              className={cn(
                "flex-1 py-2 rounded-xl border transition-all",
                !approve ? "border-red-500/50 bg-red-500/10 text-red-500" : "border-white/10 text-muted-foreground/60"
              )}
            >
              ❌ رفض
            </button>
          </div>

          {approve && (
            <div>
              <label className="text-sm text-muted-foreground/60">المبلغ المعتمد (MR_USDT)</label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={approvedAmount || ''}
                onChange={(e) => setApprovedAmount(parseFloat(e.target.value) || undefined)}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="اتركه فارغاً للموافقة على المبلغ المطالب به"
              />
            </div>
          )}

          <div>
            <label className="text-sm text-muted-foreground/60">ملاحظات (اختياري)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm resize-none"
              placeholder="سبب القبول أو الرفض..."
            />
          </div>

          <button
            type="submit"
            disabled={reviewClaim.isPending}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
          >
            {reviewClaim.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
            تأكيد المراجعة
          </button>
        </form>
      </div>
    </div>
  );
}