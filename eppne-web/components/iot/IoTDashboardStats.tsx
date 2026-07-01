// components/iot/IoTDashboardStats.tsx
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { iotService } from '@/services/iot.service';
import { SmartAsset } from '@/types/iot';

export function IoTDashboardStats() {
  const { data: assets = [], isLoading } = useQuery({
    queryKey: ['iot-assets'],
    queryFn: () => iotService.getAssets({ limit: 1000 }),
    staleTime: 1000 * 60 * 2,
  });

  const stats = useMemo(() => {
    const total = assets.length;
    const online = assets.filter(a => a.is_online).length;
    const critical = assets.filter(a => a.health_status === 'CRITICAL_FAILURE').length;
    const bioUnits = assets.filter(a => a.asset_class === 'SMART_BIO_UNIT').length;
    return { total, online, critical, bioUnits };
  }, [assets]);

  if (isLoading) return <div className="grid grid-cols-4 gap-4"><div className="h-20 glass-card animate-pulse" /></div>;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div className="glass-card p-4 rounded-2xl border border-white/10 backdrop-blur-xl">
        <p className="text-white/50 text-sm">إجمالي الأصول</p>
        <p className="text-3xl font-bold text-white">{stats.total}</p>
      </div>
      <div className="glass-card p-4 rounded-2xl border border-green-500/20 backdrop-blur-xl">
        <p className="text-white/50 text-sm">🟢 متصلة</p>
        <p className="text-3xl font-bold text-green-400">{stats.online}</p>
      </div>
      <div className="glass-card p-4 rounded-2xl border border-red-500/20 backdrop-blur-xl">
        <p className="text-white/50 text-sm">🔴 أعطال حرجة</p>
        <p className="text-3xl font-bold text-red-400">{stats.critical}</p>
      </div>
      <div className="glass-card p-4 rounded-2xl border border-neon-blue/20 backdrop-blur-xl">
        <p className="text-white/50 text-sm">⚡ وحدات طاقة حيوية</p>
        <p className="text-3xl font-bold text-neon-blue">{stats.bioUnits}</p>
      </div>
    </div>
  );
}