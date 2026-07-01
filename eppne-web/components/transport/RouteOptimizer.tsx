// components/transport/RouteOptimizer.tsx
'use client';

import { useState } from 'react';
import { useOptimizeRoute } from '@/hooks/transport/useRoutes';
import { Loader2, Sparkles, MapPin, Clock, Ruler, Leaf } from 'lucide-react';
import { cn } from '@/lib/utils';

interface RouteOptimizerProps {
  startHubId: number;
  endHubId: number;
  onOptimized: (data: any) => void;
  className?: string;
}

export default function RouteOptimizer({
  startHubId,
  endHubId,
  onOptimized,
  className,
}: RouteOptimizerProps) {
  const [optimizedRoute, setOptimizedRoute] = useState<any>(null);

  const optimizeMutation = useOptimizeRoute();

  const handleOptimize = () => {
    optimizeMutation.mutate(
      { startHubId, endHubId },
      {
        onSuccess: (data) => {
          setOptimizedRoute(data);
          onOptimized(data);
        },
      }
    );
  };

  return (
    <div className={cn("p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10", className)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-primary" />
          <h4 className="font-medium text-foreground/80">محسن المسارات بالذكاء الاصطناعي</h4>
        </div>
        <button
          onClick={handleOptimize}
          disabled={optimizeMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors text-sm disabled:opacity-50"
        >
          {optimizeMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {optimizeMutation.isPending ? 'جاري التحسين...' : 'تحسين المسار'}
        </button>
      </div>

      {optimizeMutation.isPending && (
        <div className="mt-4 flex items-center justify-center gap-2 text-sm text-muted-foreground/60">
          <Loader2 className="w-4 h-4 animate-spin" />
          جاري حساب المسار الأمثل...
        </div>
      )}

      {optimizedRoute && (
        <div className="mt-4 p-4 rounded-xl bg-white/5 border border-white/10 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground/60">المسافة المحسنة</span>
            <span className="text-foreground/80 font-medium flex items-center gap-1">
              <Ruler className="w-4 h-4 text-primary" />
              {optimizedRoute.distance_km} كم
            </span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground/60">الزمن المتوقع</span>
            <span className="text-foreground/80 font-medium flex items-center gap-1">
              <Clock className="w-4 h-4 text-primary" />
              {optimizedRoute.estimated_duration_minutes} دقيقة
            </span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground/60">توفير الكربون</span>
            <span className="text-emerald-500 font-medium flex items-center gap-1">
              <Leaf className="w-4 h-4" />
              {(optimizedRoute.carbon_saved || 0).toFixed(2)} كجم CO₂
            </span>
          </div>
          {optimizedRoute.waypoints && optimizedRoute.waypoints.length > 0 && (
            <div className="mt-2 pt-2 border-t border-white/5">
              <p className="text-xs text-muted-foreground/50">📍 نقاط وسيطة مقترحة</p>
              {optimizedRoute.waypoints.map((wp: any, idx: number) => (
                <div key={idx} className="flex items-center gap-2 text-xs text-foreground/60 mt-1">
                  <MapPin className="w-3 h-3 text-primary/60" />
                  {wp.name || `نقطة ${idx + 1}`}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}