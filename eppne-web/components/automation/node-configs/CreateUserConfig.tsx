// components/automation/node-configs/CreateUserConfig.tsx
'use client';

interface CreateUserConfigProps {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}

export default function CreateUserConfig({ config, onChange }: CreateUserConfigProps) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted-foreground/60">البريد الإلكتروني</label>
        <input
          type="email"
          value={config.email || ''}
          onChange={(e) => onChange('email', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          placeholder="user@example.com"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">كلمة المرور</label>
        <input
          type="password"
          value={config.password || ''}
          onChange={(e) => onChange('password', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          placeholder="••••••••"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">الدور</label>
        <select
          value={config.role || 'USER'}
          onChange={(e) => onChange('role', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
        >
          <option value="USER">مستخدم عادي</option>
          <option value="ADMIN">مدير</option>
          <option value="INSTRUCTOR">مدرب</option>
          <option value="ENTERPRISE">مؤسسة</option>
        </select>
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">الاسم (اختياري)</label>
        <input
          type="text"
          value={config.name || ''}
          onChange={(e) => onChange('name', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
          placeholder="أحمد محمد"
        />
      </div>
    </div>
  );
}