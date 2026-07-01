// components/insurance/SubmitClaimModal.tsx
'use client';

import { useState } from 'react';
import { useSubmitClaim } from '@/hooks/insurance/useClaims';
import { useMySubscriptions } from '@/hooks/insurance/useSubscriptions';
import { X, Loader2, AlertTriangle, Upload } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';

interface SubmitClaimModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SubmitClaimModal({ isOpen, onClose }: SubmitClaimModalProps) {
  const [formData, setFormData] = useState({
    subscription_id: 0,
    incident_date: '',
    incident_description: '',
    evidence_urls: [] as string[],
    claimed_amount_mrusdt: 0,
  });
  const [evidenceInput, setEvidenceInput] = useState('');

  const { data: subscriptions } = useMySubscriptions({ status: 'ACTIVE' });
  const submitClaim = useSubmitClaim();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const idempotencyKey = `claim-${uuidv4()}`;
    submitClaim.mutate(
      {
        data: {
          ...formData,
          incident_date: new Date(formData.incident_date).toISOString(),
          evidence_urls: formData.evidence_urls.filter(Boolean),
        },
        idempotencyKey,
      },
      {
        onSuccess: () => {
          onClose();
          setFormData({
            subscription_id: 0,
            incident_date: '',
            incident_description: '',
            evidence_urls: [],
            claimed_amount_mrusdt: 0,
          });
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
          <AlertTriangle className="w-5 h-5 text-amber-500" />
          مطالبة جديدة
        </h3>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="text-sm text-muted-foreground/60">الاشتراك</label>
            <select
              value={formData.subscription_id}
              onChange={(e) => setFormData({ ...formData, subscription_id: parseInt(e.target.value) })}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              required
            >
              <option value="">اختر اشتراكاً</option>
              {subscriptions?.map((sub) => (
                <option key={sub.id} value={sub.id}>
                  بوليصة #{sub.policy_id} - {sub.subscriber_user_id ? `مستخدم #${sub.subscriber_user_id}` : `كيان #${sub.id}`}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-sm text-muted-foreground/60">تاريخ الحادث</label>
            <input
              type="date"
              value={formData.incident_date}
              onChange={(e) => setFormData({ ...formData, incident_date: e.target.value })}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              required
            />
          </div>

          <div>
            <label className="text-sm text-muted-foreground/60">المبلغ المطالب به (MR_USDT)</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={formData.claimed_amount_mrusdt}
              onChange={(e) => setFormData({ ...formData, claimed_amount_mrusdt: parseFloat(e.target.value) || 0 })}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              required
            />
          </div>

          <div>
            <label className="text-sm text-muted-foreground/60">وصف الحادث</label>
            <textarea
              value={formData.incident_description}
              onChange={(e) => setFormData({ ...formData, incident_description: e.target.value })}
              rows={3}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm resize-none"
              placeholder="وصف تفصيلي للحادث..."
              required
            />
          </div>

          <div>
            <label className="text-sm text-muted-foreground/60">الأدلة (روابط)</label>
            <div className="flex gap-2 mt-1">
              <input
                type="text"
                value={evidenceInput}
                onChange={(e) => setEvidenceInput(e.target.value)}
                placeholder="رابط الصورة/المستند"
                className="flex-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              />
              <button
                type="button"
                onClick={() => {
                  if (evidenceInput) {
                    setFormData({ ...formData, evidence_urls: [...formData.evidence_urls, evidenceInput] });
                    setEvidenceInput('');
                  }
                }}
                className="px-3 py-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors"
              >
                <Upload className="w-4 h-4" />
              </button>
            </div>
            {formData.evidence_urls.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {formData.evidence_urls.map((url, idx) => (
                  <span key={idx} className="text-xs bg-white/5 px-2 py-1 rounded-full flex items-center gap-1">
                    📎 {url.slice(0, 20)}...
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, evidence_urls: formData.evidence_urls.filter((_, i) => i !== idx) })}
                      className="text-red-500/50 hover:text-red-500"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={submitClaim.isPending}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
          >
            {submitClaim.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <AlertTriangle className="w-4 h-4" />}
            تقديم المطالبة
          </button>
        </form>
      </div>
    </div>
  );
}