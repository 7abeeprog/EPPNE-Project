// components/automation/node-configs/SQLConfig.tsx
'use client';

interface SQLConfigProps {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}

export default function SQLConfig({ config, onChange }: SQLConfigProps) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted-foreground/60">استعلام SQL</label>
        <textarea
          value={config.query || ''}
          onChange={(e) => onChange('query', e.target.value)}
          rows={6}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/70"
          placeholder={`SELECT * FROM users WHERE id = {{trigger_payload.user_id}}`}
        />
        <div className="flex items-center gap-2 mt-2">
          <span className="text-[10px] text-amber-500/70">⚠️</span>
          <span className="text-[10px] text-muted-foreground/40">
            يُسمح فقط باستعلامات <span className="text-primary font-mono">SELECT</span> افتراضياً
          </span>
        </div>
        <p className="text-[10px] text-muted-foreground/40 mt-1">
          استخدم {'{{'}...{'}}'} لإدراج متغيرات من السياق
        </p>
      </div>
    </div>
  );
}