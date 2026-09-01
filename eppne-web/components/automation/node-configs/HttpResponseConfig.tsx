// components/automation/node-configs/HttpResponseConfig.tsx
'use client';

export default function HttpResponseConfig({
  config,
  onChange,
}: {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted-foreground/60">رمز الحالة (Status Code)</label>
        <input
          type="number"
          value={config.status_code ?? 200}
          onChange={(e) => onChange('status_code', parseInt(e.target.value) || 200)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">محتوى الرد (Body، JSON)</label>
        <textarea
          value={typeof config.body === 'string' ? config.body : JSON.stringify(config.body || {}, null, 2)}
          onChange={(e) => onChange('body', e.target.value)}
          rows={5}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/70"
          placeholder={`{"success": true, "order_id": "{{trigger_payload.order_id}}"}`}
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">هيدرز إضافية (JSON، اختياري)</label>
        <textarea
          value={typeof config.headers === 'string' ? config.headers : JSON.stringify(config.headers || {}, null, 2)}
          onChange={(e) => onChange('headers', e.target.value)}
          rows={3}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/70"
          placeholder={`{"X-Custom-Header": "value"}`}
        />
        <p className="text-[10px] text-muted-foreground/40 mt-1">
          استخدم {'{{'}...{'}}'} لإدراج متغيرات من السياق
        </p>
      </div>
    </div>
  );
}
