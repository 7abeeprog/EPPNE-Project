// components/digital-twin/TimeCapsuleForm.tsx
'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createTimeCapsule } from '@/services/digital-twin';
import { Loader2, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TimeCapsuleFormProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function TimeCapsuleForm({ isOpen, onClose }: TimeCapsuleFormProps) {
  const queryClient = useQueryClient();
  const [encryptedPayload, setEncryptedPayload] = useState('');
  const [videoWillIpfs, setVideoWillIpfs] = useState('');
  const [heartbeatInterval, setHeartbeatInterval] = useState(90);
  const [beneficiaries, setBeneficiaries] = useState<{ user_id: string; share: number; wallet: string }[]>([]);
  const [newBeneficiary, setNewBeneficiary] = useState({ user_id: '', share: 100, wallet: '' });

  const mutation = useMutation({
    mutationFn: () =>
      createTimeCapsule(
        {
          encrypted_payload_hash: encryptedPayload,
          video_will_ipfs: videoWillIpfs || undefined,
          heartbeat_interval_days: heartbeatInterval,
        },
        beneficiaries.map(b => ({
          beneficiary_user_id: parseInt(b.user_id),
          access_share_percentage: b.share,
          heir_wallet_address: b.wallet,
        }))
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['time-capsule'] });
      onClose();
    },
  });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200 p-4">
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 rounded-3xl bg-card/80 backdrop-blur-3xl border border-white/15 shadow-[0_20px_80px_-20px_rgba(0,0,0,0.6)] animate-in zoom-in-95 duration-200">
        <button onClick={onClose} className="absolute top-3 right-3 p-1 rounded-lg hover:bg-white/10 transition-colors">
          <X className="w-4 h-4 text-muted-foreground/60" />
        </button>

        <h3 className="text-lg font-bold text-foreground/90 mb-4">📦 إنشاء خزنة زمنية</h3>

        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-foreground/80">المحتوى المشفر (IPFS Hash)</label>
            <input
              type="text"
              value={encryptedPayload}
              onChange={(e) => setEncryptedPayload(e.target.value)}
              className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              placeholder="Qm..."
              required
            />
          </div>

          <div>
            <label className="text-sm font-medium text-foreground/80">فيديو الوصية (IPFS) - اختياري</label>
            <input
              type="text"
              value={videoWillIpfs}
              onChange={(e) => setVideoWillIpfs(e.target.value)}
              className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              placeholder="Qm..."
            />
          </div>

          <div>
            <label className="text-sm font-medium text-foreground/80">الفاصل الزمني للنبضات (أيام)</label>
            <input
              type="number"
              value={heartbeatInterval}
              onChange={(e) => setHeartbeatInterval(parseInt(e.target.value) || 90)}
              className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              min="1"
              max="365"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-foreground/80">المستفيدون</label>
            <div className="flex gap-2 mt-1.5">
              <input
                type="number"
                placeholder="معرف المستخدم"
                value={newBeneficiary.user_id}
                onChange={(e) => setNewBeneficiary(prev => ({ ...prev, user_id: e.target.value }))}
                className="flex-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              />
              <input
                type="number"
                placeholder="النسبة %"
                value={newBeneficiary.share}
                onChange={(e) => setNewBeneficiary(prev => ({ ...prev, share: parseInt(e.target.value) || 0 }))}
                className="w-24 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              />
              <input
                type="text"
                placeholder="المحفظة"
                value={newBeneficiary.wallet}
                onChange={(e) => setNewBeneficiary(prev => ({ ...prev, wallet: e.target.value }))}
                className="flex-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono"
              />
              <button
                onClick={() => {
                  if (newBeneficiary.user_id && newBeneficiary.share > 0 && newBeneficiary.wallet) {
                    setBeneficiaries(prev => [...prev, { ...newBeneficiary }]);
                    setNewBeneficiary({ user_id: '', share: 100, wallet: '' });
                  }
                }}
                className="px-4 py-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors"
              >
                +
              </button>
            </div>
            {beneficiaries.map((b, idx) => (
              <div key={idx} className="flex items-center gap-2 mt-1.5 text-sm bg-white/5 p-2 rounded-xl">
                <span>المستخدم #{b.user_id}</span>
                <span className="text-muted-foreground/50">—</span>
                <span>{b.share}%</span>
                <span className="text-muted-foreground/50 font-mono text-xs truncate">{b.wallet}</span>
                <button
                  onClick={() => setBeneficiaries(prev => prev.filter((_, i) => i !== idx))}
                  className="text-red-500/50 hover:text-red-500 ml-auto"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>

          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !encryptedPayload || beneficiaries.length === 0}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
          >
            {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'إنشاء الخزنة'}
          </button>
        </div>
      </div>
    </div>
  );
}