// components/automation/node-configs/LoopConfig.tsx
'use client';

import { useCallback } from 'react';

interface LoopConfigProps {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}

export default function LoopConfig({ config, onChange }: LoopConfigProps) {
  const handleItemsChange = useCallback((value: string) => {
    try {
      // محاولة تحويل JSON إلى قائمة إذا كان صالحاً
      const parsed = JSON.parse(value);
      if (Array.isArray(parsed)) {
        onChange('items', parsed);
        return;
      }
    } catch {
      // إذا لم يكن JSON، نعتبره نصاً عادياً
    }
    onChange('items', value);
  }, [onChange]);

  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted-foreground/60">مصدر العناصر للتكرار</label>
        <textarea
          value={typeof config.items === 'string' ? config.items : JSON.stringify(config.items || [], null, 2)}
          onChange={(e) => handleItemsChange(e.target.value)}
          rows={4}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/70"
          placeholder='{{node_1.results}} أو ["item1", "item2"] أو [{"id": 1, "name": "Ali"}]'
        />
        <p className="text-[10px] text-muted-foreground/40 mt-1">
          يمكن أن يكون مصفوفة JSON أو مرجعاً لعقدة سابقة
        </p>
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">معرفات العقد التي ستُكرر (Loop Nodes)</label>
        <input
          type="text"
          value={config.loop_nodes?.join(', ') || ''}
          onChange={(e) => {
            const nodes = e.target.value.split(',').map(s => s.trim()).filter(Boolean);
            onChange('loop_nodes', nodes);
          }}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/80"
          placeholder="node_2, node_3, node_4"
        />
        <p className="text-[10px] text-muted-foreground/40 mt-1">
          أدخل معرفات العقد مفصولة بفواصل
        </p>
      </div>
      <div className="p-3 rounded-xl bg-white/5 border border-white/10">
        <p className="text-xs text-muted-foreground/60">
          🔄 لكل عنصر في المصدر، سيتم تنفيذ العقد المحددة بالترتيب
        </p>
      </div>
    </div>
  );
}