// components/automation/node-configs/EnrollCourseConfig.tsx
'use client';

interface EnrollCourseConfigProps {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}

export default function EnrollCourseConfig({ config, onChange }: EnrollCourseConfigProps) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted-foreground/60">معرف المستخدم</label>
        <input
          type="number"
          value={config.user_id || ''}
          onChange={(e) => onChange('user_id', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          placeholder="{{trigger_payload.user_id}}"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">معرف الكورس</label>
        <input
          type="number"
          value={config.course_id || ''}
          onChange={(e) => onChange('course_id', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          placeholder="456"
        />
      </div>
    </div>
  );
}