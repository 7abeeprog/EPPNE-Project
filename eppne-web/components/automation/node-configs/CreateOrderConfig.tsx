// components/automation/node-configs/CreateOrderConfig.tsx
'use client';

interface CreateOrderConfigProps {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}

export default function CreateOrderConfig({ config, onChange }: CreateOrderConfigProps) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted-foreground/60">معرف المنتج</label>
        <input
          type="number"
          value={config.product_id || ''}
          onChange={(e) => onChange('product_id', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          placeholder="123"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">الكمية</label>
        <input
          type="number"
          value={config.quantity || 1}
          onChange={(e) => onChange('quantity', parseInt(e.target.value) || 1)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          min="1"
          placeholder="1"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">معرف العميل</label>
        <input
          type="number"
          value={config.customer_id || ''}
          onChange={(e) => onChange('customer_id', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          placeholder="{{trigger_payload.user_id}}"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">معرف الكيان (اختياري)</label>
        <input
          type="number"
          value={config.entity_id || ''}
          onChange={(e) => onChange('entity_id', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          placeholder="{{trigger_payload.entity_id}}"
        />
      </div>
    </div>
  );
}