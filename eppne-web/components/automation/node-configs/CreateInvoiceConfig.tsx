// components/automation/node-configs/CreateInvoiceConfig.tsx
'use client';

interface CreateInvoiceConfigProps {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}

export default function CreateInvoiceConfig({ config, onChange }: CreateInvoiceConfigProps) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted-foreground/60">معرف الكيان</label>
        <input
          type="number"
          value={config.entity_id || ''}
          onChange={(e) => onChange('entity_id', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          placeholder="{{trigger_payload.entity_id}}"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">المبلغ</label>
        <input
          type="number"
          step="0.01"
          value={config.amount || ''}
          onChange={(e) => onChange('amount', parseFloat(e.target.value) || 0)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          placeholder="1000.00"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">تاريخ الاستحقاق</label>
        <input
          type="date"
          value={config.due_date || ''}
          onChange={(e) => onChange('due_date', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">الوصف (اختياري)</label>
        <input
          type="text"
          value={config.description || ''}
          onChange={(e) => onChange('description', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          placeholder="فاتورة شهرية"
        />
      </div>
    </div>
  );
}