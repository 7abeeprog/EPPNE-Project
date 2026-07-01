// components/insurance/SubscribeModal.tsx
'use client';

import { useState } from 'react';
import { useSubscribe } from '@/hooks/insurance/useSubscriptions';
import { X, Loader2, Shield } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';

interface SubscribeModalProps {
  isOpen: boolean;
  onClose: () => void;
  policyId: number;
}

export default function SubscribeModal({ isOpen, onClose, policyId }: SubscribeModalProps) {
  const [formData, setFormData] = useState({
    subscriber_user_id: undefined as number | undefined,
    fleet_id: undefined as number | undefined,
    land_asset_id: undefined as number | undefined,
    project_id: undefined as number | undefined,
    bio_asset_id: undefined as number | undefined,
    shipment_id: undefined as number | undefined,
    employment_contract_id: undefined as number | undefined,
    beneficiaries_json: {} as Record<string, any>,
    start_date: '',
    end_date: '',
  });

  const subscribe = useSubscribe();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const idempotencyKey = `subscribe-${policyId}-${uuidv4()}`;
    subscribe.mutate(
      {
        data: {
          policy_id: policyId,
          ...formData,
          start_date: new Date(formData.start_date).toISOString(),
          end_date: formData.end_date ? new Date(formData.end_date).toISOString() : undefined,
        },
        idempotencyKey,
      },
      {
        onSuccess: () => {
          onClose();
          setFormData({
            subscriber_user_id: undefined,
            fleet_id: undefined,
            land_asset_id: undefined,
            project_id: undefined,
            bio_asset_id: undefined,
            shipment_id: undefined,
            employment_contract_id: undefined,
            beneficiaries_json: {},
            start_date: '',
            end_date: '',
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
          <Shield className="w-5 h-5 text-primary" />
          الاشتراك في البوليصة
        </h3>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="text-sm text-muted-foreground/60">نوع المؤمن له</label>
            <select
              onChange={(e) => {
                const val = e.target.value;
                setFormData({
                  ...formData,
                  subscriber_user_id: undefined,
                  fleet_id: undefined,
                  land_asset_id: undefined,
                  project_id: undefined,
                  bio_asset_id: undefined,
                  shipment_id: undefined,
                  employment_contract_id: undefined,
                  [val]: 1,
                });
              }}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            >
              <option value="">اختر النوع</option>
              <option value="subscriber_user_id">مستخدم</option>
              <option value="fleet_id">أسطول</option>
              <option value="land_asset_id">أرض</option>
              <option value="project_id">مشروع</option>
              <option value="bio_asset_id">أصل بيولوجي</option>
              <option value="shipment_id">شحنة</option>
              <option value="employment_contract_id">عقد عمل</option>
            </select>
          </div>

          <div>
            <label className="text-sm text-muted-foreground/60">معرف المؤمن له</label>
            <input
              type="number"
              placeholder="أدخل المعرف"
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            />
          </div>

          <div>
            <label className="text-sm text-muted-foreground/60">تاريخ البداية</label>
            <input
              type="date"
              value={formData.start_date}
              onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              required
            />
          </div>

          <div>
            <label className="text-sm text-muted-foreground/60">تاريخ النهاية (اختياري)</label>
            <input
              type="date"
              value={formData.end_date}
              onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            />
          </div>

          <button
            type="submit"
            disabled={subscribe.isPending}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
          >
            {subscribe.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
            تأكيد الاشتراك
          </button>
        </form>
      </div>
    </div>
  );
}