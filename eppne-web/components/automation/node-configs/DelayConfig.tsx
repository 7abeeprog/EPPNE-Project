// components/automation/node-configs/DelayConfig.tsx
'use client';

import { useCallback } from 'react';

interface DelayConfigProps {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}

export default function DelayConfig({ config, onChange }: DelayConfigProps) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted-foreground/60">مدة التأخير (بالثواني)</label>
        <input
          type="number"
          value={config.seconds || 5}
          onChange={(e) => onChange('seconds', parseInt(e.target.value) || 0)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80"
          min="0"
          max="86400"
          placeholder="5"
        />
        <p className="text-[10px] text-muted-foreground/40 mt-1">
          الحد الأقصى 86,400 ثانية (يوم واحد)
        </p>
      </div>
      <div className="p-3 rounded-xl bg-white/5 border border-white/10">
        <p className="text-xs text-muted-foreground/60">
          ⏳ سيتوقف التنفيذ هنا لمدة <span className="text-primary font-mono">{config.seconds || 5}</span> ثانية قبل المتابعة
        </p>
      </div>
    </div>
  );
}