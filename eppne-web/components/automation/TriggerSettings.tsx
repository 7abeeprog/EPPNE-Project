// components/automation/TriggerSettings.tsx
'use client';

import { useCallback } from 'react';
import { Info, Copy, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import CronInput from './CronInput';

interface TriggerSettingsProps {
  triggerType: 'MANUAL' | 'WEBHOOK' | 'SCHEDULE' | 'EVENT';
  triggerConfig: Record<string, any>;
  webhookPath?: string | null;
  onChange: (type: string, config: Record<string, any>) => void;
  className?: string;
}

const EVENT_OPTIONS = [
  { value: 'order.created', label: 'طلب جديد (Order Created)' },
  { value: 'order.paid', label: 'تم دفع الطلب (Order Paid)' },
  { value: 'order.shipped', label: 'تم شحن الطلب (Order Shipped)' },
  { value: 'invoice.created', label: 'فاتورة جديدة (Invoice Created)' },
  { value: 'invoice.paid', label: 'فاتورة مدفوعة (Invoice Paid)' },
  { value: 'user.registered', label: 'مستخدم جديد (User Registered)' },
  { value: 'user.verified', label: 'تم التحقق من المستخدم (User Verified)' },
  { value: 'entity.kyb.submitted', label: 'رفع مستندات KYB' },
  { value: 'entity.kyb.verified', label: 'تم التحقق من KYB' },
  { value: 'course.enrolled', label: 'تسجيل في كورس' },
  { value: 'certificate.issued', label: 'إصدار شهادة' },
  { value: 'subscription.renewed', label: 'تجديد اشتراك' },
  { value: 'subscription.expired', label: 'انتهاء اشتراك' },
];

export default function TriggerSettings({
  triggerType,
  triggerConfig,
  webhookPath,
  onChange,
  className,
}: TriggerSettingsProps) {
  const handleTypeChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    const newType = e.target.value as 'MANUAL' | 'WEBHOOK' | 'SCHEDULE' | 'EVENT';
    const newConfig = {};
    // إعدادات افتراضية لكل نوع
    if (newType === 'SCHEDULE') newConfig.cron = '0 0 * * *';
    else if (newType === 'EVENT') newConfig.event = 'order.created';
    else if (newType === 'WEBHOOK') newConfig.method = 'POST';
    onChange(newType, newConfig);
  }, [onChange]);

  const handleConfigChange = useCallback((key: string, value: any) => {
    const newConfig = { ...triggerConfig, [key]: value };
    onChange(triggerType, newConfig);
  }, [triggerType, triggerConfig, onChange]);

  // نسخ مسار Webhook
  const copyWebhook = useCallback(() => {
    if (webhookPath) {
      const fullUrl = `${window.location.origin}/api/automation/webhook${webhookPath}`;
      navigator.clipboard?.writeText(fullUrl);
    }
  }, [webhookPath]);

  return (
    <div className={cn("space-y-4 p-4 rounded-2xl bg-card/20 backdrop-blur-sm border border-white/10", className)}>
      {/* اختيار نوع المشغل */}
      <div>
        <label className="text-xs text-muted-foreground/60">نوع المشغل</label>
        <select
          value={triggerType}
          onChange={handleTypeChange}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80"
        >
          <option value="MANUAL">🖐️ يدوي (Manual)</option>
          <option value="WEBHOOK">🔗 Webhook</option>
          <option value="SCHEDULE">⏰ جدول زمني (Schedule)</option>
          <option value="EVENT">📡 حدث نظام (Event)</option>
        </select>
      </div>

      {/* إعدادات حسب النوع */}
      {triggerType === 'MANUAL' && (
        <div className="p-3 rounded-xl bg-white/5 border border-white/10 flex items-center gap-2 text-sm text-muted-foreground/60">
          <Info className="w-4 h-4 shrink-0 text-primary/60" />
          سيتم تشغيل سير العمل هذا يدوياً فقط عبر زر "تشغيل" في الواجهة.
        </div>
      )}

      {triggerType === 'WEBHOOK' && (
        <div className="space-y-3">
          <div className="p-3 rounded-xl bg-white/5 border border-white/10">
            <label className="text-xs text-muted-foreground/60">مسار Webhook</label>
            <div className="flex items-center gap-2 mt-1">
              <code className="flex-1 px-3 py-2 rounded-lg bg-black/20 border border-white/10 text-sm font-mono text-foreground/80 truncate">
                {webhookPath || 'سيتم توليده عند حفظ سير العمل'}
              </code>
              {webhookPath && (
                <button
                  onClick={copyWebhook}
                  className="p-2 rounded-lg bg-primary/20 hover:bg-primary/30 transition-colors text-primary"
                  title="نسخ الرابط"
                >
                  <Copy className="w-4 h-4" />
                </button>
              )}
            </div>
            <p className="text-[10px] text-muted-foreground/40 mt-2">
              أرسل طلب POST إلى هذا المسار لتشغيل سير العمل
            </p>
          </div>
          <div>
            <label className="text-xs text-muted-foreground/60">طريقة الطلب (Method)</label>
            <select
              value={triggerConfig.method || 'POST'}
              onChange={(e) => handleConfigChange('method', e.target.value)}
              className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80"
            >
              <option value="POST">POST</option>
              <option value="GET">GET</option>
            </select>
          </div>
        </div>
      )}

      {triggerType === 'SCHEDULE' && (
        <div>
          <label className="text-xs text-muted-foreground/60">تعبير Cron</label>
          <CronInput
            value={triggerConfig.cron || ''}
            onChange={(value) => handleConfigChange('cron', value)}
          />
        </div>
      )}

      {triggerType === 'EVENT' && (
        <div>
          <label className="text-xs text-muted-foreground/60">الحدث المشغل</label>
          <select
            value={triggerConfig.event || 'order.created'}
            onChange={(e) => handleConfigChange('event', e.target.value)}
            className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80"
          >
            {EVENT_OPTIONS.map((ev) => (
              <option key={ev.value} value={ev.value}>{ev.label}</option>
            ))}
          </select>
          <p className="text-[10px] text-muted-foreground/40 mt-1">
            عند وقوع هذا الحدث في النظام، سيتم تشغيل سير العمل تلقائياً
          </p>
        </div>
      )}
    </div>
  );
}