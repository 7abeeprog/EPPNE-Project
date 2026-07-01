// components/iot/AssetsManager.tsx
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { iotService } from '@/services/iot.service';
import { useIoTStore } from '@/store/iot-store';
import { AssetCard } from './AssetCard';

export function AssetsManager() {
  const { filterAssetClass, toggleCreateModal, setFilterAssetClass } = useIoTStore();

  const { data: assets = [], isLoading } = useQuery({
    queryKey: ['iot-assets'],
    queryFn: () => iotService.getAssets({ limit: 1000 }),
    staleTime: 1000 * 60,
  });

  const filteredAssets = useMemo(() => {
    if (!filterAssetClass) return assets;
    return assets.filter(a => a.asset_class === filterAssetClass);
  }, [assets, filterAssetClass]);

  if (isLoading) return <div>جاري تحميل الأصول...</div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex gap-2 flex-wrap">
          <button onClick={() => setFilterAssetClass(null)} className="px-3 py-1 glass-card text-sm text-white/70 rounded-xl hover:bg-white/10">الكل</button>
          {['SURVEILLANCE', 'SMART_BIO_UNIT', 'ACCESS_GATE', 'HVAC', 'UTILITY_METER', 'INDUSTRIAL_ROBOT'].map(cls => (
            <button key={cls} onClick={() => setFilterAssetClass(cls)} className="px-3 py-1 glass-card text-sm text-white/70 rounded-xl hover:bg-white/10">
              {cls.replace('_', ' ')}
            </button>
          ))}
        </div>
        <button onClick={() => toggleCreateModal(true)} className="px-4 py-2 bg-neon-blue rounded-xl text-white font-bold shadow-lg shadow-neon-blue/20 hover:scale-105 transition-all">
          + إضافة أصل
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredAssets.map(asset => (
          <AssetCard key={asset.id} asset={asset} />
        ))}
      </div>
    </div>
  );
}