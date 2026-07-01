// components/iot/CarbonCreditPanel.tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { iotService } from '@/services/iot.service';

export function CarbonCreditPanel() {
  const queryClient = useQueryClient();

  const { data: readings = [], isLoading } = useQuery({
    queryKey: ['iot-readings'],
    queryFn: () => iotService.getReadings({ limit: 1000 }),
    staleTime: 1000 * 30,
  });

  const unsettled = readings.filter(r => r.carbon_credits_generated > 0 && !r.is_settled_on_chain);
  const totalCredits = unsettled.reduce((acc, r) => acc + r.carbon_credits_generated, 0);
  const totalValue = totalCredits * 50;

  const settleMutation = useMutation({
    mutationFn: () => iotService.settleCarbon(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['iot-readings'] });
      queryClient.invalidateQueries({ queryKey: ['wallet-balance'] });
      alert(`✅ تم تسييل ${data.total_credits_settled} طن كربون بقيمة ${data.monetary_value_added_mrusdt} MRUSDT`);
    },
    onError: (err: any) => alert('❌ فشل التسييل: ' + err.message),
  });

  if (isLoading) return <div>جاري تحميل الأرصدة...</div>;

  return (
    <div className="glass-card p-6 rounded-2xl border border-white/10 backdrop-blur-xl space-y-4">
      <h2 className="text-2xl font-bold text-white">🌱 أرصدة الكربون</h2>
      <div className="flex justify-between items-center">
        <div>
          <p className="text-white/50">إجمالي الأرصدة غير المسواة</p>
          <p className="text-3xl font-bold text-green-400">{totalCredits.toFixed(4)} طن</p>
          <p className="text-sm text-white/40">≈ {totalValue.toFixed(2)} MRUSDT</p>
        </div>
        <button
          onClick={() => settleMutation.mutate()}
          disabled={totalCredits === 0 || settleMutation.isPending}
          className="px-6 py-3 bg-gradient-to-r from-neon-blue to-neon-purple rounded-xl text-white font-bold shadow-lg shadow-neon-blue/20 hover:scale-105 transition-all disabled:opacity-50"
        >
          {settleMutation.isPending ? 'جاري التسييل...' : '💰 تسييل الكل'}
        </button>
      </div>
      <div className="mt-4 max-h-40 overflow-y-auto space-y-2">
        {unsettled.slice(0, 5).map(r => (
          <div key={r.id} className="flex justify-between text-sm border-b border-white/5 pb-2">
            <span className="text-white/60">الأصل #{r.asset_id}</span>
            <span className="text-green-300">{r.carbon_credits_generated} طن</span>
          </div>
        ))}
        {unsettled.length > 5 && <p className="text-white/30 text-xs">+ {unsettled.length - 5} قراءات أخرى...</p>}
      </div>
    </div>
  );
}