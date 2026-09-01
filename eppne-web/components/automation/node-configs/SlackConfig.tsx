// components/automation/node-configs/SlackConfig.tsx
'use client';

interface SlackConfigProps {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}

export default function SlackConfig({ config, onChange }: SlackConfigProps) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted-foreground/60">رابط Webhook</label>
        <input
          type="text"
          value={config.webhook_url || ''}
          onChange={(e) => onChange('webhook_url', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/80"
          placeholder="{{secrets.SLACK_WEBHOOK_URL}}"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">القناة (اختياري)</label>
        <input
          type="text"
          value={config.channel || ''}
          onChange={(e) => onChange('channel', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80"
          placeholder="#general"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">الرسالة</label>
        <textarea
          value={config.message || ''}
          onChange={(e) => onChange('message', e.target.value)}
          rows={3}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/70"
          placeholder="تم استلام طلب جديد رقم {{order.id}}"
        />
        <p className="text-[10px] text-muted-foreground/40 mt-1">
          استخدم {'{{'}...{'}}'} لإدراج متغيرات من السياق
        </p>
      </div>
    </div>
  );
}
