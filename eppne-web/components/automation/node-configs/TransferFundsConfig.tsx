// components/automation/node-configs/TransferFundsConfig.tsx
'use client';

interface TransferFundsConfigProps {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}

export default function TransferFundsConfig({ config, onChange }: TransferFundsConfigProps) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted-foreground/60">المحفظة المصدر</label>
        <input
          type="text"
          value={config.from_wallet || ''}
          onChange={(e) => onChange('from_wallet', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono"
          placeholder="0x1234567890abcdef"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">المحفظة الهدف</label>
        <input
          type="text"
          value={config.to_wallet || ''}
          onChange={(e) => onChange('to_wallet', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono"
          placeholder="0xabcdef1234567890"
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
          placeholder="500.00"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">ملاحظات (اختياري)</label>
        <input
          type="text"
          value={config.notes || ''}
          onChange={(e) => onChange('notes', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          placeholder="تحويل للمورد"
        />
      </div>
    </div>
  );
}