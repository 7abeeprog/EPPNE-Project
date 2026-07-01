// components/automation/node-configs/CreateEntityConfig.tsx
'use client';

const ENTITY_TYPES = [
  { value: 'ENTERPRISE', label: 'شركة' },
  { value: 'STATE_GOVERNMENT', label: 'دولة/حكومة' },
  { value: 'MINISTRY_AUTHORITY', label: 'وزارة/هيئة' },
  { value: 'INTERNATIONAL_ORGANIZATION', label: 'منظمة دولية' },
  { value: 'NGO_CIVIL_SOCIETY', label: 'منظمة مجتمع مدني' },
  { value: 'ACADEMIC_INSTITUTION', label: 'مؤسسة أكاديمية' },
];

interface CreateEntityConfigProps {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}

export default function CreateEntityConfig({ config, onChange }: CreateEntityConfigProps) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted-foreground/60">اسم الكيان</label>
        <input
          type="text"
          value={config.name || ''}
          onChange={(e) => onChange('name', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          placeholder="شركة التقنية الحديثة"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">نوع الكيان</label>
        <select
          value={config.entity_type || 'ENTERPRISE'}
          onChange={(e) => onChange('entity_type', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
        >
          {ENTITY_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">البريد الإلكتروني الرسمي</label>
        <input
          type="email"
          value={config.official_email || ''}
          onChange={(e) => onChange('official_email', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          placeholder="contact@company.com"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">الدولة</label>
        <input
          type="text"
          value={config.country_of_origin || ''}
          onChange={(e) => onChange('country_of_origin', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          placeholder="السعودية"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">معرف المنشئ (created_by)</label>
        <input
          type="number"
          value={config.created_by || ''}
          onChange={(e) => onChange('created_by', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          placeholder="{{trigger_payload.user_id}}"
        />
        <p className="text-[10px] text-muted-foreground/40 mt-1">عادةً ما يكون معرف المستخدم الحالي</p>
      </div>
    </div>
  );
}