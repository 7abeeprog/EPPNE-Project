// app/(dashboard)/agritech/farms/[id]/page.tsx
'use client';

import { useParams } from 'next/navigation';
import { useFarm } from '@/hooks/agritech/useFarms';
import { useZones } from '@/hooks/agritech/useZones';
import { useWeatherAlerts } from '@/hooks/agritech/useSensors';
import FarmZoneCard from '@/components/agritech/FarmZoneCard';
import SoilSensorWidget from '@/components/agritech/SoilSensorWidget';
import WeatherAlertCard from '@/components/agritech/WeatherAlertCard';
import { Loader2, ArrowLeft, Sprout, Thermometer, Droplet, Shield, MapPin } from 'lucide-react';
import Link from 'next/link';

export default function FarmDetailPage() {
  const params = useParams();
  const farmId = parseInt(params.id as string);

  const { data: farm, isLoading: farmLoading } = useFarm(farmId);
  const { data: zones, isLoading: zonesLoading } = useZones(farmId);
  const { data: alerts } = useWeatherAlerts();

  const farmAlerts = alerts?.filter((a) => a.affected_farm_ids.includes(farmId));

  if (farmLoading || zonesLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!farm) {
    return <div className="p-6 text-center text-muted-foreground/60">المزرعة غير موجودة</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <Link href="/agritech/farms" className="flex items-center gap-2 text-sm text-muted-foreground/60 hover:text-foreground/80 transition-colors">
        <ArrowLeft className="w-4 h-4" />
        العودة إلى المزارع
      </Link>

      <div className="p-6 rounded-3xl bg-card/20 backdrop-blur-2xl border border-white/10">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground/90">{farm.name}</h1>
            <p className="text-sm text-muted-foreground/60 flex items-center gap-2 mt-1">
              <Sprout className="w-4 h-4" />
              {farm.farm_type}
              <span className="text-muted-foreground/30">|</span>
              <MapPin className="w-4 h-4" />
              {farm.total_area_acres} فدان
            </p>
          </div>
          <div className="flex items-center gap-2">
            {farm.has_insurance && (
              <span className="text-xs px-2 py-0.5 rounded-full border-emerald-500/30 text-emerald-500 bg-emerald-500/5 flex items-center gap-1">
                <Shield className="w-3 h-3" />
                مؤمنة
              </span>
            )}
          </div>
        </div>

        {/* تنبيهات المزرعة */}
        {farmAlerts && farmAlerts.length > 0 && (
          <div className="mt-4 space-y-2">
            {farmAlerts.map((alert) => (
              <WeatherAlertCard key={alert.id} alert={alert} />
            ))}
          </div>
        )}
      </div>

      {/* المناطق */}
      <div>
        <h2 className="text-lg font-semibold text-foreground/80 mb-3">📋 مناطق المزرعة</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {zones?.map((zone) => (
            <FarmZoneCard key={zone.id} zone={zone} />
          ))}
        </div>
      </div>

      {/* مستشعرات التربة */}
      {zones && zones.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-foreground/80 mb-3 flex items-center gap-2">
            <Thermometer className="w-5 h-5 text-primary" />
            قراءات المستشعرات
          </h2>
          <div className="space-y-4">
            {zones.slice(0, 2).map((zone) => (
              <div key={zone.id} className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
                <h4 className="text-sm font-medium text-foreground/70 mb-2">📍 {zone.zone_code}</h4>
                <SoilSensorWidget zoneId={zone.id} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}