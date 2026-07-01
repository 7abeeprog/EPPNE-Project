// components/tenders-auctions/SubmitBidModal.tsx
'use client';

import { useState } from 'react';
import { useSubmitBid } from '@/hooks/tenders-auctions/useBids';
import { X, Loader2, FileText, Lock } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';

interface SubmitBidModalProps {
  isOpen: boolean;
  onClose: () => void;
  tenderId: number;
}

export default function SubmitBidModal({ isOpen, onClose, tenderId }: SubmitBidModalProps) {
  const [technicalEnvelope, setTechnicalEnvelope] = useState('{}');
  const [encryptedFinancial, setEncryptedFinancial] = useState('');

  const submitBid = useSubmitBid();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const idempotencyKey = `bid-${tenderId}-${uuidv4()}`;
    submitBid.mutate(
      {
        data: {
          tender_id: tenderId,
          technical_envelope: JSON.parse(technicalEnvelope),
          encrypted_financial_envelope: encryptedFinancial,
        },
        idempotencyKey,
      },
      {
        onSuccess: () => {
          onClose();
          setTechnicalEnvelope('{}');
          setEncryptedFinancial('');
        },
      }
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200 p-4">
      <div className="relative w-full max-w-lg p-6 rounded-3xl bg-card/80 backdrop-blur-3xl border border-white/15 shadow-[0_20px_80px_-20px_rgba(0,0,0,0.6)] animate-in zoom-in-95 duration-200">
        <button onClick={onClose} className="absolute top-3 right-3 p-1 rounded-lg hover:bg-white/10 transition-colors">
          <X className="w-4 h-4 text-muted-foreground/60" />
        </button>

        <h3 className="text-lg font-bold text-foreground/90 flex items-center gap-2">
          <FileText className="w-5 h-5 text-primary" />
          تقديم عطاء
        </h3>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="text-sm text-muted-foreground/60">المظروف الفني (JSON)</label>
            <textarea
              value={technicalEnvelope}
              onChange={(e) => setTechnicalEnvelope(e.target.value)}
              rows={5}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono"
              placeholder='{"qualifications": "...", "approach": "..."}'
              required
            />
          </div>

          <div>
            <label className="text-sm text-muted-foreground/60">المظروف المالي (مشفر)</label>
            <textarea
              value={encryptedFinancial}
              onChange={(e) => setEncryptedFinancial(e.target.value)}
              rows={3}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono"
              placeholder="النص المشفر للمبلغ والعروض المالية"
              required
            />
            <p className="text-xs text-muted-foreground/40 mt-1">يجب أن يكون مشفراً بمفتاح العميل (سيتم فكه بعد التقييم الفني)</p>
          </div>

          <button
            type="submit"
            disabled={submitBid.isPending}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
          >
            {submitBid.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Lock className="w-4 h-4" />}
            تقديم العطاء
          </button>
        </form>
      </div>
    </div>
  );
}