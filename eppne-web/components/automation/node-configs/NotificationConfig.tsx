// components/automation/node-configs/NotificationConfig.tsx
'use client';

import { useCallback } from 'react';

interface NotificationConfigProps {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}

export default function NotificationConfig({ config, onChange }: NotificationConfigProps) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted-foreground/60">معرف المستخدم (User ID)</label>
        <input
          type="text"
          value={config.user_id || ''}
          onChange={(e) => onChange('user_id', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/80"
          placeholder="{{trigger_payload.user_id}} أو 123"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">العنوان (Title)</label>
        <input
          type="text"
          value={config.title || ''}
          onChange={(e) => onChange('title', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80"
          placeholder="تم إتمام الطلب بنجاح"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">المحتوى (Body)</label>
        <textarea
          value={config.body || ''}
          onChange={(e) => onChange('body', e.target.value)}
          rows={3}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/70"
          placeholder="تم شحن طلبك رقم {{order.id}}"
        />
        <p className="text-[10px] text-muted-foreground/40 mt-1">
          استخدم {'{{'}...{'}}'} لإدراج متغيرات من السياق
        </p>
      </div>
    </div>
  );
}