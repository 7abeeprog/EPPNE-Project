// components/automation/node-configs/DatabaseConfig.tsx
'use client';

export default function DatabaseConfig({
  config,
  onChange,
}: {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted-foreground/60">سلسلة الاتصال (اختياري)</label>
        <input
          type="text"
          value={config.connection_string || ''}
          onChange={(e) => onChange('connection_string', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/80"
          placeholder="{{secrets.DB_CONNECTION_STRING}}"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">استعلام SQL</label>
        <textarea
          value={config.query || ''}
          onChange={(e) => onChange('query', e.target.value)}
          rows={6}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/70"
          placeholder={`UPDATE orders SET status = 'shipped' WHERE id = :order_id`}
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">المعاملات (JSON، اختياري)</label>
        <textarea
          value={typeof config.params === 'string' ? config.params : JSON.stringify(config.params || {}, null, 2)}
          onChange={(e) => onChange('params', e.target.value)}
          rows={3}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/70"
          placeholder={`{"order_id": "{{trigger_payload.order_id}}"}`}
        />
        <p className="text-[10px] text-muted-foreground/40 mt-1">
          استخدم {'{{'}...{'}}'} لإدراج متغيرات من السياق
        </p>
      </div>
    </div>
  );
}
