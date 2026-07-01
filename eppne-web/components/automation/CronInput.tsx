// components/automation/CronInput.tsx
'use client';

import { useState, useEffect, useCallback } from 'react';
import { CheckCircle, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

// @ts-ignore - cron-parser سيتم تثبيته
import * as cronParser from 'cron-parser';

interface CronInputProps {
  value: string;
  onChange: (cron: string) => void;
  className?: string;
}

const PRESET_CRONS = [
  { label: 'كل دقيقة', value: '* * * * *' },
  { label: 'كل 5 دقائق', value: '*/5 * * * *' },
  { label: 'كل ساعة', value: '0 * * * *' },
  { label: 'كل 6 ساعات', value: '0 */6 * * *' },
  { label: 'منتصف الليل يومياً', value: '0 0 * * *' },
  { label: 'كل يوم اثنين', value: '0 0 * * 1' },
  { label: 'أول يوم في الشهر', value: '0 0 1 * *' },
];

export default function CronInput({ value, onChange, className }: CronInputProps) {
  const [error, setError] = useState<string | null>(null);
  const [nextExecution, setNextExecution] = useState<string | null>(null);

  const validateCron = useCallback((cron: string) => {
    if (!cron || cron.trim() === '') {
      setError('الرجاء إدخال تعبير cron');
      setNextExecution(null);
      return;
    }
    try {
      const interval = cronParser.parseExpression(cron);
      const next = interval.next().toString();
      setNextExecution(next);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'تعبير cron غير صالح');
      setNextExecution(null);
    }
  }, []);

  useEffect(() => {
    if (value) validateCron(value);
  }, [value, validateCron]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    onChange(newValue);
    if (newValue) validateCron(newValue);
    else setError('الرجاء إدخال تعبير cron');
  };

  const handlePreset = (preset: string) => {
    onChange(preset);
    validateCron(preset);
  };

  return (
    <div className={cn("space-y-2", className)}>
      <div className="relative">
        <input
          type="text"
          value={value}
          onChange={handleChange}
          placeholder="* * * * *"
          className={cn(
            "w-full px-3 py-2 rounded-xl bg-white/5 border focus:outline-none text-sm font-mono text-foreground/80 transition-colors",
            error
              ? "border-red-500/50 focus:border-red-500/70"
              : value
              ? "border-emerald-500/50 focus:border-emerald-500/70"
              : "border-white/10 focus:border-primary/30"
          )}
        />
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground/40">
          {error ? <AlertCircle className="w-4 h-4 text-red-500" /> : value ? <CheckCircle className="w-4 h-4 text-emerald-500" /> : null}
        </span>
      </div>

      {/* الاختصارات */}
      <div className="flex flex-wrap gap-1.5">
        {PRESET_CRONS.map((preset) => (
          <button
            key={preset.value}
            onClick={() => handlePreset(preset.value)}
            className={cn(
              "px-2 py-0.5 rounded-full text-[10px] transition-all duration-200 border",
              value === preset.value
                ? "bg-primary/20 text-primary border-primary/30"
                : "bg-white/5 text-muted-foreground/60 border-white/5 hover:bg-white/10 hover:text-foreground/80"
            )}
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* نتيجة التحقق */}
      {error && <p className="text-[10px] text-red-500/70">{error}</p>}
      {nextExecution && !error && (
        <p className="text-[10px] text-muted-foreground/50">
          🕐 التنفيذ التالي: <span className="text-emerald-500/70">{nextExecution}</span>
        </p>
      )}
    </div>
  );
}