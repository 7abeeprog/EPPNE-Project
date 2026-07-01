// components/iot/AssetCard.tsx
import { SmartAsset } from '@/types/iot';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { iotService } from '@/services/iot.service';

export function AssetCard({ asset }: { asset: SmartAsset }) {
  const queryClient = useQueryClient();
  const statusColor = asset.is_online ? 'bg-green-400 shadow-green-400/50' : 'bg-gray-500';
  const healthColor = asset.health_status === 'EXCELLENT' ? 'text-green-400' : 
                      asset.health_status === 'CRITICAL_FAILURE' ? 'text-red-400' : 'text-yellow-400';

  const toggleOnline = useMutation({
    mutationFn: () => iotService.updateAsset(asset.id, { is_online: !asset.is_online }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['iot-assets'] }),
  });

  return (
    <div className="glass-card p-4 rounded-2xl border border-white/10 backdrop-blur-xl hover:border-neon-blue/30 transition-all group">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-white font-bold">{asset.asset_code}</h3>
          <p className="text-white/40 text-sm">{asset.asset_class.replace('_', ' ')}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${statusColor} shadow-lg animate-pulse`}></span>
          <span className={`text-xs ${healthColor}`}>{asset.health_status}</span>
        </div>
      </div>
      {asset.location_gps && (
        <p className="text-xs text-white/30 mt-2">📍 {asset.location_gps.lat}, {asset.location_gps.lng}</p>
      )}
      <div className="mt-3 flex gap-2">
        <button onClick={() => toggleOnline.mutate()} className="text-xs px-3 py-1 bg-white/10 rounded-lg text-white/70 hover:bg-white/20 transition-all">
          {asset.is_online ? '🟢 تعطيل' : '🔴 تفعيل'}
        </button>
        <button className="text-xs px-3 py-1 bg-white/10 rounded-lg text-white/70 hover:bg-white/20 transition-all">
          عرض القراءات
        </button>
      </div>
    </div>
  );
}