// components/arbitration-syndicates/JuryVoteModal.tsx
'use client';

import { useState } from 'react';
import { useJuryVote } from '@/hooks/arbitration-syndicates/useJuryVote';
import { X, Loader2, ThumbsUp, ThumbsDown, Scale } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';

interface JuryVoteModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: number;
}

export default function JuryVoteModal({ isOpen, onClose, caseId }: JuryVoteModalProps) {
  const [vote, setVote] = useState<boolean | null>(null);
  const [justification, setJustification] = useState('');

  const juryVote = useJuryVote();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (vote === null) return;
    const idempotencyKey = `jury-${caseId}-${uuidv4()}`;
    juryVote.mutate(
      {
        caseId,
        data: { vote, justification: justification || undefined },
        idempotencyKey,
      },
      {
        onSuccess: () => {
          onClose();
          setVote(null);
          setJustification('');
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
          <Scale className="w-5 h-5 text-primary" />
          تصويت المحلف
        </h3>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => setVote(true)}
              className={cn(
                "flex-1 py-3 rounded-xl border transition-all flex items-center justify-center gap-2",
                vote === true ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-500" : "border-white/10 text-muted-foreground/60"
              )}
            >
              <ThumbsUp className="w-4 h-4" />
              لصالح المدعي
            </button>
            <button
              type="button"
              onClick={() => setVote(false)}
              className={cn(
                "flex-1 py-3 rounded-xl border transition-all flex items-center justify-center gap-2",
                vote === false ? "border-red-500/50 bg-red-500/10 text-red-500" : "border-white/10 text-muted-foreground/60"
              )}
            >
              <ThumbsDown className="w-4 h-4" />
              لصالح المدعى عليه
            </button>
          </div>

          <div>
            <label className="text-sm text-muted-foreground/60">التبرير (اختياري)</label>
            <textarea
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              rows={3}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm resize-none"
              placeholder="اذكر سبب تصويتك..."
            />
          </div>

          <button
            type="submit"
            disabled={juryVote.isPending || vote === null}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
          >
            {juryVote.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Scale className="w-4 h-4" />}
            تأكيد التصويت
          </button>
        </form>
      </div>
    </div>
  );
}