// components/sovereign-entities/WalletActions.tsx
'use client';

import { useState, useRef, useEffect } from 'react';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import { depositToEntity, transferFromEntity, generateIdempotencyKey } from '@/services/sovereign-entities';
import ConfirmationModal from '@/components/ui/ConfirmationModal';
import { Loader2, ArrowUpRight, ArrowDownLeft } from 'lucide-react';
import { cn } from '@/lib/utils';

interface WalletActionsProps {
  entityId: number;
  entityName: string;
  primaryColor: string;
  currentBalance: number;
}

export default function WalletActions({ entityId, entityName, primaryColor, currentBalance }: WalletActionsProps) {
  const queryClient = useQueryClient();
  const [isDepositModalOpen, setIsDepositModalOpen] = useState(false);
  const [isTransferModalOpen, setIsTransferModalOpen] = useState(false);
  const [amount, setAmount] = useState('');
  const [recipientAddress, setRecipientAddress] = useState('');
  const [notes, setNotes] = useState('');
  const [depositLoading, setDepositLoading] = useState(false);
  const [transferLoading, setTransferLoading] = useState(false);

  // توليد Idempotency Key لكل عملية عند تحميل المكون
  const depositKeyRef = useRef<string>('');
  const transferKeyRef = useRef<string>('');

  useEffect(() => {
    depositKeyRef.current = generateIdempotencyKey({ type: 'deposit', entityId, timestamp: Date.now() });
    transferKeyRef.current = generateIdempotencyKey({ type: 'transfer', entityId, timestamp: Date.now() });
  }, [entityId]);

  // Mutations
  const depositMutation = useMutation({
    mutationFn: (data: { amount: number; currency: string; notes?: string }) =>
      depositToEntity(entityId, data, depositKeyRef.current),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entity-balance', entityId] });
      setIsDepositModalOpen(false);
      setAmount('');
      setNotes('');
      setDepositLoading(false);
    },
    onError: () => setDepositLoading(false),
  });

  const transferMutation = useMutation({
    mutationFn: (data: { to_address: string; amount: number; currency: string; notes?: string }) =>
      transferFromEntity(entityId, data, transferKeyRef.current),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entity-balance', entityId] });
      setIsTransferModalOpen(false);
      setAmount('');
      setRecipientAddress('');
      setNotes('');
      setTransferLoading(false);
    },
    onError: () => setTransferLoading(false),
  });

  // التأكيد النهائي للإيداع
  const confirmDeposit = () => {
    const numAmount = parseFloat(amount);
    if (isNaN(numAmount) || numAmount <= 0) return;
    setDepositLoading(true);
    depositMutation.mutate({
      amount: numAmount,
      currency: 'MR_USDT',
      notes: notes || 'إيداع في المحفظة',
    });
  };

  // التأكيد النهائي للتحويل
  const confirmTransfer = () => {
    const numAmount = parseFloat(amount);
    if (isNaN(numAmount) || numAmount <= 0) return;
    if (numAmount > currentBalance) {
      alert('الرصيد غير كافٍ');
      return;
    }
    setTransferLoading(true);
    transferMutation.mutate({
      to_address: recipientAddress,
      amount: numAmount,
      currency: 'MR_USDT',
      notes: notes || 'تحويل من المحفظة',
    });
  };

  return (
    <div className="space-y-4">
      {/* الأزرار */}
      <div className="flex flex-wrap gap-3">
        <button
          onClick={() => setIsDepositModalOpen(true)}
          className="flex-1 min-w-[120px] flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500/20 text-emerald-500 border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors font-medium"
        >
          <ArrowDownLeft className="w-4 h-4" />
          إيداع
        </button>
        <button
          onClick={() => setIsTransferModalOpen(true)}
          className="flex-1 min-w-[120px] flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors font-medium"
        >
          <ArrowUpRight className="w-4 h-4" />
          تحويل
        </button>
      </div>

      {/* Modal الإيداع */}
      <ConfirmationModal
        isOpen={isDepositModalOpen}
        onClose={() => { setIsDepositModalOpen(false); setDepositLoading(false); }}
        onConfirm={confirmDeposit}
        title="تأكيد الإيداع"
        message={`أنت على وشك إيداع المبلغ في محفظة "${entityName}". يرجى التأكد من المبلغ قبل التأكيد.`}
        confirmText={depositLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'تأكيد الإيداع'}
        type="info"
        entityName={entityName}
        primaryColor={primaryColor}
        requiresTyping={false}
      >
        {/* محتوى مخصص للنموذج داخل الـ Modal */}
        <div className="space-y-3 mt-4">
          <div>
            <label className="text-xs text-muted-foreground/60">المبلغ (MR_USDT)</label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              min="0.01"
              step="0.01"
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              autoFocus
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground/60">ملاحظات (اختياري)</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="سبب الإيداع"
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            />
          </div>
        </div>
      </ConfirmationModal>

      {/* Modal التحويل */}
      <ConfirmationModal
        isOpen={isTransferModalOpen}
        onClose={() => { setIsTransferModalOpen(false); setTransferLoading(false); }}
        onConfirm={confirmTransfer}
        title="تأكيد التحويل"
        message={`أنت على وشك تحويل مبلغ من محفظة "${entityName}". الرصيد الحالي: ${currentBalance.toFixed(2)} MR_USDT.`}
        confirmText={transferLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'تأكيد التحويل'}
        type="danger"
        entityName={entityName}
        primaryColor={primaryColor}
        requiresTyping={true}
      >
        <div className="space-y-3 mt-4">
          <div>
            <label className="text-xs text-muted-foreground/60">المستلم (عنوان المحفظة)</label>
            <input
              type="text"
              value={recipientAddress}
              onChange={(e) => setRecipientAddress(e.target.value)}
              placeholder="0x..."
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              required
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground/60">المبلغ (MR_USDT)</label>
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              min="0.01"
              step="0.01"
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              required
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground/60">ملاحظات (اختياري)</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="سبب التحويل"
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            />
          </div>
          <div className="text-xs text-amber-500/70">
            الرصيد المتوقع بعد العملية: {(currentBalance - (parseFloat(amount) || 0)).toFixed(2)} MR_USDT
          </div>
        </div>
      </ConfirmationModal>
    </div>
  );
}