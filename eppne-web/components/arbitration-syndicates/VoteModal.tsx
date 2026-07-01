// components/arbitration-syndicates/VoteModal.tsx
'use client';

import { useState } from 'react';
import { useCastVote } from '@/hooks/arbitration-syndicates/useElections';
import { X, Loader2, Vote, User } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';

interface VoteModalProps {
  isOpen: boolean;
  onClose: () => void;
  electionId: number;
  candidates: { id: number; user_name?: string; user_id: number }[];
}

export default function VoteModal({ isOpen, onClose, electionId, candidates }: VoteModalProps) {
  const [selectedCandidate, setSelectedCandidate] = useState<number | null>(null);

  const castVote = useCastVote();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCandidate) return;
    const idempotencyKey = `vote-${electionId}-${uuidv4()}`;
    castVote.mutate(
      {
        electionId,
        data: { candidate_id: selectedCandidate },
        idempotencyKey,
      },
      {
        onSuccess: () => {
          onClose();
          setSelectedCandidate(null);
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
          <Vote className="w-5 h-5 text-primary" />
          التصويت في الانتخابات
        </h3>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div className="space-y-2">
            {candidates.map((candidate) => (
              <button
                key={candidate.id}
                type="button"
                onClick={() => setSelectedCandidate(candidate.id)}
                className={cn(
                  "w-full flex items-center gap-3 p-3 rounded-xl border transition-all",
                  selectedCandidate === candidate.id
                    ? "border-primary/50 bg-primary/10 text-primary"
                    : "border-white/10 text-foreground/70 hover:bg-white/5"
                )}
              >
                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold">
                  {candidate.user_name?.[0] || 'C'}
                </div>
                <div className="text-right">
                  <p className="font-medium">{candidate.user_name || `المرشح #${candidate.user_id}`}</p>
                </div>
                {selectedCandidate === candidate.id && (
                  <div className="mr-auto">
                    <CheckCircle className="w-4 h-4 text-primary" />
                  </div>
                )}
              </button>
            ))}
          </div>

          <button
            type="submit"
            disabled={castVote.isPending || !selectedCandidate}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
          >
            {castVote.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Vote className="w-4 h-4" />}
            تأكيد التصويت
          </button>
        </form>
      </div>
    </div>
  );
}