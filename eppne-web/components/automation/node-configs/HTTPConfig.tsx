// components/automation/node-configs/HTTPConfig.tsx
'use client';

import { useCallback } from 'react';
import { cn } from '@/lib/utils';

interface HTTPConfigProps {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}

const HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'];

export default function HTTPConfig({ config, onChange }: HTTPConfigProps) {
  const handleChange = useCallback(
    (key: string, value: any) => {
      onChange(key, value);
    },
    [onChange]
  );

  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted-foreground/60">الرابط (URL)</label>
        <input
          type="text"
          value={config.url || ''}
          onChange={(e) => handleChange('url', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80 font-mono"
          placeholder="https://api.example.com/endpoint"
        />
        <p className="text-[10px] text-muted-foreground/40 mt-1">
          استخدم {'{{'}node_id.output{'}}'} للإشارة إلى مخرجات عقدة سابقة
        </p>
      </div>

      <div>
        <label className="text-xs text-muted-foreground/60">طريقة الطلب (Method)</label>
        <select
          value={config.method || 'GET'}
          onChange={(e) => handleChange('method', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80"
        >
          {HTTP_METHODS.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="text-xs text-muted-foreground/60">الهيدر (Headers) - JSON</label>
        <textarea
          value={JSON.stringify(config.headers || {}, null, 2)}
          onChange={(e) => {
            try {
              const parsed = JSON.parse(e.target.value);
              handleChange('headers', parsed);
            } catch {
              // تجاهل أثناء الكتابة
            }
          }}
          rows={3}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/70"
          placeholder='{"Content-Type": "application/json"}'
        />
      </div>

      <div>
        <label className="text-xs text-muted-foreground/60">المحتوى (Body) - JSON أو نص</label>
        <textarea
          value={typeof config.body === 'string' ? config.body : JSON.stringify(config.body || {}, null, 2)}
          onChange={(e) => {
            try {
              const parsed = JSON.parse(e.target.value);
              handleChange('body', parsed);
            } catch {
              // إذا لم يكن JSON صالحاً، نعامله كنص
              handleChange('body', e.target.value);
            }
          }}
          rows={4}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/70"
          placeholder='{"key": "value"} أو نص عادي'
        />
        <p className="text-[10px] text-muted-foreground/40 mt-1">
          يمكنك استخدام {'{{'}node_id.output{'}}'} داخل النص
        </p>
      </div>
    </div>
  );
}