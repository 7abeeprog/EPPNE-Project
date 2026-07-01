// components/automation/node-configs/EmailConfig.tsx
'use client';

interface EmailConfigProps {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}

export default function EmailConfig({ config, onChange }: EmailConfigProps) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted-foreground/60">المستلم (To)</label>
        <input
          type="email"
          value={config.to || ''}
          onChange={(e) => onChange('to', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80"
          placeholder="user@example.com"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">الموضوع (Subject)</label>
        <input
          type="text"
          value={config.subject || ''}
          onChange={(e) => onChange('subject', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80"
          placeholder="تأكيد الطلب #{{order.id}}"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">المحتوى (Body) - HTML مدعوم</label>
        <textarea
          value={config.body || ''}
          onChange={(e) => onChange('body', e.target.value)}
          rows={5}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/70"
          placeholder={`<h1>مرحباً {{user.name}}</h1><p>تم استلام طلبك</p>`}
        />
        <p className="text-[10px] text-muted-foreground/40 mt-1">
          يدعم HTML، استخدم {'{{'}...{'}}'} للمتغيرات
        </p>
      </div>
    </div>
  );
}