// components/automation/node-configs/ConditionConfig.tsx
'use client';

import { useCallback } from 'react';

interface ConditionConfigProps {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}

const OPERATORS = [
  { value: 'eq', label: 'يساوي (==)' },
  { value: 'neq', label: 'لا يساوي (!=)' },
  { value: 'gt', label: 'أكبر من (>)' },
  { value: 'lt', label: 'أصغر من (<)' },
  { value: 'contains', label: 'يحتوي على' },
  { value: 'starts_with', label: 'يبدأ بـ' },
  { value: 'ends_with', label: 'ينتهي بـ' },
];

export default function ConditionConfig({ config, onChange }: ConditionConfigProps) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted-foreground/60">المعامل (Operator)</label>
        <select
          value={config.operator || 'eq'}
          onChange={(e) => onChange('operator', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80"
        >
          {OPERATORS.map((op) => (
            <option key={op.value} value={op.value}>
              {op.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="text-xs text-muted-foreground/60">القيمة الأولى (يسار)</label>
        <input
          type="text"
          value={config.left || ''}
          onChange={(e) => onChange('left', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/80"
          placeholder='{{node_1.output}} أو "نص" أو 123'
        />
      </div>

      <div>
        <label className="text-xs text-muted-foreground/60">القيمة الثانية (يمين)</label>
        <input
          type="text"
          value={config.right || ''}
          onChange={(e) => onChange('right', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/80"
          placeholder='{{node_2.output}} أو "نص" أو 123'
        />
      </div>

      <div className="p-3 rounded-xl bg-white/5 border border-white/10">
        <p className="text-xs text-muted-foreground/60">
          🔄 النتيجة ستكون <span className="text-primary font-mono">true</span> أو <span className="text-red-500 font-mono">false</span>
        </p>
      </div>
    </div>
  );
}