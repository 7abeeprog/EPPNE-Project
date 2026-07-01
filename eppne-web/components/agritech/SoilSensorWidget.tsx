// components/agritech/SoilSensorWidget.tsx
'use client';

import { useSoilReadings } from '@/hooks/agritech/useSensors';
import { Loader2, Droplet, Thermometer, FlaskRound, Leaf } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SoilSensorWidgetProps {
  zoneId: number;
  className?: string;
}

export default function SoilSensorWidget({ zoneId, className }: SoilSensorWidgetProps) {
  const { data: readings, isLoading } = useSoilReadings(zoneId, { limit: 1 });

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-24">
        <Loader2 className="w-5 h-5 animate-spin text-primary" />
      </div>
    );
  }

  const reading = readings?.[0];

  if (!reading) {
    return (
      <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 text-center text-muted-foreground/50 text-sm">
        لا توجد قراءات مستشعرات
      </div>
    );
  }

  const metrics = [
    {
      label: 'الرطوبة',
      value: reading.moisture_percent ? `${reading.moisture_percent}%` : '—',
      icon: Droplet,
      color: 'text-blue-500',
      status: reading.moisture_percent && reading.moisture_percent < 30 ? 'warning' : reading.moisture_percent && reading.moisture_percent > 70 ? 'danger' : 'normal',
    },
    {
      label: 'درجة الحرارة',
      value: reading.temperature_celsius ? `${reading.temperature_celsius}°C` : '—',
      icon: Thermometer,
      color: 'text-amber-500',
      status: reading.temperature_celsius && reading.temperature_celsius > 40 ? 'warning' : 'normal',
    },
    {
      label: 'درجة الحموضة',
      value: reading.ph_level ? `${reading.ph_level}` : '—',
      icon: FlaskRound,
      color: 'text-purple-500',
      status: reading.ph_level && (reading.ph_level < 5.5 || reading.ph_level > 8.5) ? 'warning' : 'normal',
    },
    {
      label: 'النتروجين',
      value: reading.nitrogen_ppm ? `${reading.nitrogen_ppm} ppm` : '—',
      icon: Leaf,
      color: 'text-emerald-500',
      status: reading.nitrogen_ppm && reading.nitrogen_ppm < 20 ? 'warning' : 'normal',
    },
  ];

  return (
    <div className={cn("grid grid-cols-2 md:grid-cols-4 gap-3", className)}>
      {metrics.map((metric, idx) => (
        <div
          key={idx}
          className={cn(
            "p-3 rounded-xl bg-white/5 border transition-all",
            metric.status === 'warning' ? "border-amber-500/30 bg-amber-500/5" :
            metric.status === 'danger' ? "border-red-500/30 bg-red-500/5" :
            "border-white/10"
          )}
        >
          <div className="flex items-center gap-2">
            <metric.icon className={cn("w-4 h-4", metric.color)} />
            <span className="text-xs text-muted-foreground/50">{metric.label}</span>
          </div>
          <p className="mt-1 text-sm font-medium text-foreground/80">{metric.value}</p>
        </div>
      ))}
    </div>
  );
}