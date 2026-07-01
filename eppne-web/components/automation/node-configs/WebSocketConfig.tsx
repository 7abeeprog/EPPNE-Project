// components/automation/node-configs/WebSocketConfig.tsx
'use client';

import { useCallback } from 'react';

interface WebSocketConfigProps {
  config: Record<string, any>;
  onChange: (key: string, value: any) => void;
}

const WS_ACTIONS = [
  { value: 'send', label: 'إرسال رسالة' },
  { value: 'receive', label: 'استقبال رسالة' },
  { value: 'send_and_receive', label: 'إرسال واستقبال' },
  { value: 'listen', label: 'الاستماع المستمر' },
];

export default function WebSocketConfig({ config, onChange }: WebSocketConfigProps) {
  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs text-muted-foreground/60">عنوان WebSocket</label>
        <input
          type="text"
          value={config.url || ''}
          onChange={(e) => onChange('url', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/80"
          placeholder="wss://api.example.com/ws"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground/60">الإجراء (Action)</label>
        <select
          value={config.action || 'send'}
          onChange={(e) => onChange('action', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm text-foreground/80"
        >
          {WS_ACTIONS.map((a) => (
            <option key={a.value} value={a.value}>{a.label}</option>
          ))}
        </select>
      </div>
      {config.action !== 'receive' && (
        <div>
          <label className="text-xs text-muted-foreground/60">الرسالة المراد إرسالها</label>
          <textarea
            value={config.message || ''}
            onChange={(e) => onChange('message', e.target.value)}
            rows={3}
            className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/70"
            placeholder='{"type": "subscribe", "channel": "{{channel_id}}"}'
          />
        </div>
      )}
      <div>
        <label className="text-xs text-muted-foreground/60">المفتاح لحفظ الرد في السياق</label>
        <input
          type="text"
          value={config.save_response_to || 'ws_response'}
          onChange={(e) => onChange('save_response_to', e.target.value)}
          className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm font-mono text-foreground/80"
          placeholder="ws_response"
        />
        <p className="text-[10px] text-muted-foreground/40 mt-1">
          سيتم تخزين الرد في {'{{'}ws_response{'}}'} (أو المفتاح الذي تحدده)
        </p>
      </div>
    </div>
  );
}