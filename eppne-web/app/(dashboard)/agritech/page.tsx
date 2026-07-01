// app/(dashboard)/agritech/page.tsx
'use client';

import { useFarms } from '@/hooks/agritech/useFarms';
import { useWeatherAlerts } from '@/hooks/agritech/useSensors';
import { useAgritechStats } from '@/hooks/agritech/useStats';
import FarmCard from '@/components/agritech/FarmCard';
import WeatherAlertCard from '@/components/agritech/WeatherAlertCard';
import AIRecommendationCard from '@/components/agritech/AIRecommendationCard';
import { Loader2, Plus, Sprout, Leaf, AlertTriangle, Sparkles } from 'lucide-react';
import Link from 'next/link';

export default function AgritechDashboard() {
  const { data: farms, isLoading: farmsLoading } = useFarms({ limit: 6 });
  const { data: alerts } = useWeatherAlerts();
  const { data: stats } = useAgritechStats();

  if (farmsLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const criticalAlerts = alerts?.filter((a) => a.severity === 'CRITICAL') || [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90 flex items-center gap-2">
            🌾 التكنولوجيا الزراعية
          </h1>
          <p className="text-sm text-muted-foreground/70">إدارة المزارع الذكية، المحاصيل، والثروة الحيوانية</p>
        </div>
        <Link
          href="/agritech/farms/create"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          مزرعة جديدة
        </Link>
      </div>

      {/* تنبيهات الذكاء الاصطناعي */}
      {criticalAlerts.length > 0 && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/30">
          <h3 className="text-sm font-medium text-red-500 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            تنبيهات عاجلة من وكيل الذكاء الاصطناعي
          </h3>
          <div className="mt-2 space-y-2">
            {criticalAlerts.slice(0, 3).map((alert) => (
              <div key={alert.id} className="text-sm text-red-500/80 flex items-center gap-2">
                <span>•</span>
                {alert.message}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* المزارع */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-foreground/80 flex items-center gap-2">
            <Sprout className="w-5 h-5 text-primary" />
            مزارعك
            <span className="text-sm font-normal text-muted-foreground/50">
              ({farms?.length || 0})
            </span>
          </h2>
          <Link href="/agritech/farms" className="text-xs text-primary/70 hover:text-primary">
            عرض الكل
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {farms?.slice(0, 6).map((farm) => (
            <FarmCard key={farm.id} farm={farm} />
          ))}
        </div>
      </div>

      {/* توصيات الذكاء الاصطناعي */}
      <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
        <h3 className="text-sm font-medium text-foreground/70 flex items-center gap-2 mb-3">
          <Sparkles className="w-4 h-4 text-primary" />
          توصيات وكيل الذكاء الاصطناعي
        </h3>
        <div className="space-y-2">
          <AIRecommendationCard
            recommendation={{
              id: '1',
              type: 'IRRIGATE',
              title: 'ري عاجل مطلوب',
              description: 'انخفاض الرطوبة في المنطقة الشمالية إلى 25%، يُنصح بالري الفوري',
              priority: 'HIGH',
              created_at: new Date().toISOString(),
            }}
          />
          <AIRecommendationCard
            recommendation={{
              id: '2',
              type: 'FERTILIZE',
              title: 'تسميد التربة',
              description: 'نسبة النتروجين منخفضة في الحقل الجنوبي، يُنصح بإضافة سماد عضوي',
              priority: 'MEDIUM',
              created_at: new Date().toISOString(),
            }}
          />
        </div>
      </div>
    </div>
  );
}