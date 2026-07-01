// components/tenders-auctions/CloseAuctionModal.tsx
'use client';

import { useCloseAuction } from '@/hooks/tenders-auctions/useCloseAuction';
import { X, Loader2, Gavel, AlertTriangle } from 'lucide-react';

interface CloseAuctionModalProps {
  isOpen: boolean;
  onClose: () => void;
  auctionId: number;
  onSuccess?: () => void;
}

export default function CloseAuctionModal({ isOpen, onClose, auctionId, onSuccess }: CloseAuctionModalProps) {
  const closeAuction = useCloseAuction();

  const handleClose = () => {
    closeAuction.mutate(auctionId, {
      onSuccess: () => {
        onClose();
        onSuccess?.();
      },
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200 p-4">
      <div className="relative w-full max-w-md p-6 rounded-3xl bg-card/80 backdrop-blur-3xl border border-red-500/30 shadow-[0_20px_80px_-20px_rgba(239,68,68,0.15)] animate-in zoom-in-95 duration-200">
        <button onClick={onClose} className="absolute top-3 right-3 p-1 rounded-lg hover:bg-white/10 transition-colors">
          <X className="w-4 h-4 text-muted-foreground/60" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-xl bg-red-500/10 text-red-500">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-foreground/90">إغلاق المزاد</h3>
            <p className="text-sm text-muted-foreground/60">هذا الإجراء نهائي ولا يمكن التراجع عنه</p>
          </div>
        </div>

        <div className="space-y-4">
          <p className="text-sm text-foreground/70">
            سيتم إنهاء المزاد. إذا كان هناك فائز، سيتم تحويل المبلغ تلقائياً إلى مالك الأصل.
          </p>

          <div className="flex gap-3">
            <button
              onClick={handleClose}
              disabled={closeAuction.isPending}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-red-500 text-white font-medium shadow-[0_0_30px_rgba(239,68,68,0.3)] hover:shadow-[0_0_50px_rgba(239,68,68,0.5)] transition-all duration-300 disabled:opacity-50"
            >
              {closeAuction.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Gavel className="w-4 h-4" />}
              تأكيد الإغلاق
            </button>
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2.5 rounded-xl border border-white/10 hover:bg-white/5 transition-colors text-foreground/70"
            >
              إلغاء
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}