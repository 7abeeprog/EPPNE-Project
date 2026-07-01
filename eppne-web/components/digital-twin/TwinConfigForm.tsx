// components/digital-twin/TwinConfigForm.tsx
'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { updateTwinConfig } from '@/services/digital-twin';
import { Loader2, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { TwinAccessLevel, TwinCapability } from '@/types/digital-twin';

const accessLevels: { value: TwinAccessLevel; label: string; description: string }[] = [
  { value: 'PRIVATE', label: 'خاص', description: 'فقط أنت' },
  { value: 'FAMILY', label: 'العائلة', description: 'أفراد العائلة المسجلون' },
  { value: 'PAID_ONLY', label: 'مدفوع', description: 'من يدفع رسوم التفاعل' },
  { value: 'PUBLIC', label: 'عام', description: 'الجميع' },
];

const capabilities: { value: TwinCapability; label: string }[] = [
  { value: 'CHAT', label: 'محادثة' },
  { value: 'MEETING', label: 'حضور اجتماعات' },
  { value: 'FINANCE', label: 'استشارات مالية' },
  { value: 'SIGN', label: 'توقيع إلكتروني' },
  { value: 'LEGACY', label: 'إدارة الإرث' },
];

interface TwinConfigFormProps {
  initialConfig: {
    id: number;
    global_access_level: TwinAccessLevel;
    interaction_fee_mrusdt: number;
    subscription_monthly_mrusdt: number;
    capabilities: TwinCapability[];
    max_spending_limit: number;
    is_active: boolean;
  };
}

export default function TwinConfigForm({ initialConfig }: TwinConfigFormProps) {
  const queryClient = useQueryClient();
  const [config, setConfig] = useState(initialConfig);

  const mutation = useMutation({
    mutationFn: (data: typeof config) => updateTwinConfig(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['twin-config'] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate(config);
  };

  const toggleCapability = (cap: TwinCapability) => {
    setConfig((prev) => ({
      ...prev,
      capabilities: prev.capabilities.includes(cap)
        ? prev.capabilities.filter((c) => c !== cap)
        : [...prev.capabilities, cap],
    }));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 p-6">
      <div className="space-y-4">
        {/* مستوى الوصول */}
        <div>
          <label className="text-sm font-medium text-foreground/80">مستوى الوصول</label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-1.5">
            {accessLevels.map((level) => (
              <button
                key={level.value}
                type="button"
                onClick={() => setConfig((prev) => ({ ...prev, global_access_level: level.value }))}
                className={cn(
                  "p-3 rounded-xl border transition-all duration-200 text-sm text-right",
                  config.global_access_level === level.value
                    ? "border-primary/50 bg-primary/20 text-primary"
                    : "border-white/10 bg-white/5 text-muted-foreground/70 hover:bg-white/10"
                )}
              >
                <div className="font-medium">{level.label}</div>
                <div className="text-[10px] text-muted-foreground/50">{level.description}</div>
              </button>
            ))}
          </div>
        </div>

        {/* الرسوم */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-foreground/80">رسوم التفاعل (الدقيقة)</label>
            <input
              type="number"
              step="0.01"
              value={config.interaction_fee_mrusdt}
              onChange={(e) =>
                setConfig((prev) => ({ ...prev, interaction_fee_mrusdt: parseFloat(e.target.value) || 0 }))
              }
              className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-foreground/80">الاشتراك الشهري (MR_USDT)</label>
            <input
              type="number"
              step="0.01"
              value={config.subscription_monthly_mrusdt}
              onChange={(e) =>
                setConfig((prev) => ({ ...prev, subscription_monthly_mrusdt: parseFloat(e.target.value) || 0 }))
              }
              className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
            />
          </div>
        </div>

        {/* القدرات */}
        <div>
          <label className="text-sm font-medium text-foreground/80">القدرات</label>
          <div className="flex flex-wrap gap-2 mt-1.5">
            {capabilities.map((cap) => (
              <button
                key={cap.value}
                type="button"
                onClick={() => toggleCapability(cap.value)}
                className={cn(
                  "px-3 py-1.5 rounded-xl border transition-all duration-200 text-sm",
                  config.capabilities.includes(cap.value)
                    ? "border-primary/50 bg-primary/20 text-primary"
                    : "border-white/10 bg-white/5 text-muted-foreground/60 hover:bg-white/10"
                )}
              >
                {cap.label}
              </button>
            ))}
          </div>
        </div>

        {/* الحد الأقصى للإنفاق */}
        <div>
          <label className="text-sm font-medium text-foreground/80">الحد الأقصى للإنفاق الشهري (MR_USDT)</label>
          <input
            type="number"
            step="0.01"
            value={config.max_spending_limit}
            onChange={(e) =>
              setConfig((prev) => ({ ...prev, max_spending_limit: parseFloat(e.target.value) || 0 }))
            }
            className="w-full mt-1.5 px-3 py-2.5 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          />
          <p className="text-[10px] text-muted-foreground/40 mt-1">0 يعني عدم وجود حد</p>
        </div>

        {/* حالة التوأم */}
        <div className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10">
          <label className="flex items-center gap-2 text-sm text-foreground/80 cursor-pointer">
            <input
              type="checkbox"
              checked={config.is_active}
              onChange={(e) => setConfig((prev) => ({ ...prev, is_active: e.target.checked }))}
              className="w-4 h-4 rounded border-white/20 bg-white/5"
            />
            تفعيل التوأم الرقمي
          </label>
          {config.is_active && (
            <span className="text-xs text-emerald-500/70 flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              نشط
            </span>
          )}
        </div>
      </div>

      {/* أزرار الإجراء */}
      <div className="flex gap-3 pt-4 border-t border-white/10">
        <button
          type="submit"
          disabled={mutation.isPending}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300 disabled:opacity-50"
        >
          {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'حفظ الإعدادات'}
        </button>
      </div>
    </form>
  );
}