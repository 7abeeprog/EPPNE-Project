// components/automation/node-configs/TransformConfig.tsx
'use client';

import { useCallback } from 'react';

interface TransformConfigProps {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}

export default function TransformConfig({ config, onChange }: TransformConfigProps) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted-foreground/60">قالب التحويل (Template) - JSON</label>
        <textarea
          value={JSON.stringify(config.template || {}, null, 2)}
          onChange={(e) => {
            try {
              const parsed = JSON.parse(e.target.value);
              onChange('template', parsed);
            } catch {
              // تجاهل أثناء الكتابة
            }
          }}
          rows={8}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/70"
          placeholder={`{
  "full_name": "{{node_1.first_name}} {{node_1.last_name}}",
  "total": "{{node_2.amount}}",
  "formatted": "Hello, {{node_1.first_name}}!"
}`}
        />
        <p className="text-[10px] text-muted-foreground/40 mt-1">
          استخدم {'{{'}node_id.path{'}}'} للإشارة إلى مخرجات عقد أخرى
        </p>
      </div>
    </div>
  );
}