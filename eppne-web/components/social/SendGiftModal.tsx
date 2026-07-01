// components/social/SendGiftModal.tsx
'use client';

import { useState } from 'react';
import { useSendDigitalGift } from '@/hooks/social/useGifts';
import { useOccasions } from '@/hooks/social/useOccasions';
import { X, Loader2, Gift, Users } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';

interface SendGiftModalProps {
  isOpen: boolean;
  onClose: () => void;
  receiverId: number;
  receiverName?: string;
}

export default function SendGiftModal({ isOpen, onClose, receiverId, receiverName }: SendGiftModalProps) {
  const [formData, setFormData] = useState({
    gift_type: 'MESSAGE',
    gift_value_mrusdt: 0,
    gift_message: '',
    occasion_id: undefined as number | undefined,
    gift_metadata: {} as Record<string, any>,
  });

  const { data: occasions } = useOccasions();
  const sendGift = useSendDigitalGift();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const idempotencyKey = `gift-${receiverId}-${uuidv4()}`;
    sendGift.mutate(
      {
        data: {
          receiver_id: receiverId,
          occasion_id: formData.occasion_id,
          gift_type: formData.gift_type,
          gift_value_mrusdt: formData.gift_value_mrusdt,
          gift_message: formData.gift_message,
          gift_metadata: formData.gift_metadata,
        },
        idempotencyKey,
      },
      {
        onSuccess: () => {
          onClose();
          setFormData({ gift_type: 'MESSAGE', gift_value_mrusdt: 0, gift_message: '', occasion_id: undefined, gift_metadata: {} });
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
          <Gift className="w-5 h-5 text-primary" />
          إرسال هدية لـ {receiverName || `المستخدم #${receiverId}`}
        </h3>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="text-sm text-muted-foreground/60">نوع الهدية</label>
            <select
              value={formData.gift_type}
              onChange={(e) => setFormData({ ...formData, gift_type: e.target.value })}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            >
              <option value="MESSAGE">رسالة</option>
              <option value="VOUCHER">قسيمة شراء</option>
              <option value="CRYPTO">عملة رقمية</option>
              <option value="NFT">NFT</option>
            </select>
          </div>

          <div>
            <label className="text-sm text-muted-foreground/60">القيمة (MR_USDT)</label>
            <input
              type="number"
              step="0.01"
              value={formData.gift_value_mrusdt}
              onChange={(e) => setFormData({ ...formData, gift_value_mrusdt: parseFloat(e.target.value) || 0 })}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              placeholder="0.00"
            />
          </div>

          <div>
            <label className="text-sm text-muted-foreground/60">الرسالة</label>
            <textarea
              value={formData.gift_message}
              onChange={(e) => setFormData({ ...formData, gift_message: e.target.value })}
              rows={3}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm resize-none"
              placeholder="اكتب رسالتك..."
            />
          </div>

          <div>
            <label className="text-sm text-muted-foreground/60">المناسبة (اختياري)</label>
            <select
              value={formData.occasion_id || ''}
              onChange={(e) => setFormData({ ...formData, occasion_id: e.target.value ? parseInt(e.target.value) : undefined })}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            >
              <option value="">بدون مناسبة</option>
              {occasions?.map((occ) => (
                <option key={occ.id} value={occ.id}>{occ.title || occ.occasion_type}</option>
              ))}
            </select>
          </div>

          <button
            type="submit"
            disabled={sendGift.isPending}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
          >
            {sendGift.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Gift className="w-4 h-4" />}
            إرسال الهدية
          </button>
        </form>
      </div>
    </div>
  );
}