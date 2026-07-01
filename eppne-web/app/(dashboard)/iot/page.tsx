// app/(dashboard)/iot/page.tsx
'use client';

import { IoTDashboardStats } from '@/components/iot/IoTDashboardStats';
import { AssetsManager } from '@/components/iot/AssetsManager';
import { CarbonCreditPanel } from '@/components/iot/CarbonCreditPanel';
import { ReadingsChart } from '@/components/iot/ReadingsChart'; // افترض وجوده
import { MaintenanceLogs } from '@/components/iot/MaintenanceLogs';
import { useIoTStore } from '@/store/iot-store';

export default function IoTPage() {
  const { activeTab, setActiveTab } = useIoTStore();

  const tabs = [
    { id: 'dashboard', label: '📊 لوحة القيادة' },
    { id: 'assets', label: '📡 الأصول' },
    { id: 'carbon', label: '🌱 الكربون' },
    { id: 'readings', label: '📈 القراءات' },
    { id: 'maintenance', label: '🔧 الصيانة' },
  ];

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6" dir="rtl">
      <div className="text-center">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-neon-blue to-neon-purple bg-clip-text text-transparent">
          السيادة الذكية وإنترنت الأشياء 🌍
        </h1>
        <p className="text-white/50 mt-2">إدارة الأصول، القراءات اللحظية، وتسييل الكربون</p>
      </div>

      <IoTDashboardStats />

      <div className="flex flex-wrap gap-2 p-1 glass-card rounded-2xl border border-white/10">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex-1 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300
              ${activeTab === tab.id 
                ? 'bg-gradient-to-r from-neon-blue/30 to-neon-purple/30 text-white shadow-lg shadow-neon-blue/10' 
                : 'text-white/40 hover:text-white/80 hover:bg-white/5'
              }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="glass-card p-6 rounded-2xl border border-white/10 backdrop-blur-xl min-h-[400px]">
        {activeTab === 'dashboard' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <CarbonCreditPanel />
            <ReadingsChart />
          </div>
        )}
        {activeTab === 'assets' && <AssetsManager />}
        {activeTab === 'carbon' && <CarbonCreditPanel />}
        {activeTab === 'readings' && <ReadingsChart />}
        {activeTab === 'maintenance' && <MaintenanceLogs />}
      </div>
    </div>
  );
}