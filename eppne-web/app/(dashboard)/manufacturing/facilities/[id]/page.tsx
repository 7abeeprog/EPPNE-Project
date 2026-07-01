// app/(dashboard)/manufacturing/facilities/[id]/page.tsx
'use client';

import { useParams } from 'next/navigation';
import { useFacility } from '@/hooks/manufacturing/useFacilities';
import { useProductionLines } from '@/hooks/manufacturing/useProductionLines';
import { usePendingMaintenance } from '@/hooks/manufacturing/usePendingMaintenance';
import MaintenanceRadar from '@/components/manufacturing/MaintenanceRadar';
import { Loader2, ArrowLeft, MapPin, Factory, Wrench, Package, Plus } from 'lucide-react';
import Link from 'next/link';

export default function FacilityDetailPage() {
  const params = useParams();
  const facilityId = parseInt(params.id as string);

  const { data: facility, isLoading: facilityLoading } = useFacility(facilityId);
  const { data: lines, isLoading: linesLoading } = useProductionLines(facilityId);

  if (facilityLoading || linesLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!facility) {
    return <div className="p-6 text-center text-muted-foreground/60">المنشأة غير موجودة</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <Link href="/manufacturing" className="flex items-center gap-2 text-sm text-muted-foreground/60 hover:text-foreground/80 transition-colors">
        <ArrowLeft className="w-4 h-4" />
        العودة إلى التصنيع
      </Link>

      <div className="p-6 rounded-3xl bg-card/20 backdrop-blur-2xl border border-white/10">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground/90">{facility.name}</h1>
            <p className="text-sm text-muted-foreground/60 flex items-center gap-2 mt-1">
              <Factory className="w-4 h-4" />
              {facility.facility_type}
              {facility.location_gps && (
                <>
                  <span className="text-muted-foreground/30">|</span>
                  <MapPin className="w-4 h-4" />
                  {facility.location_gps.lat.toFixed(4)}, {facility.location_gps.lng.toFixed(4)}
                </>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className={cn(
              "text-xs px-2 py-0.5 rounded-full border",
              facility.is_active ? "border-emerald-500/30 text-emerald-500" : "border-red-500/30 text-red-500"
            )}>
              {facility.is_active ? 'نشط' : 'موقف'}
            </span>
            <span className="text-xs text-muted-foreground/50">
              درجة الامتثال: {facility.safety_compliance_score}%
            </span>
          </div>
        </div>
      </div>

      {/* خطوط الإنتاج */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-foreground/80">⚙️ خطوط الإنتاج</h2>
          <Link
            href={`/manufacturing/lines/create?facility=${facilityId}`}
            className="text-xs text-primary/70 hover:text-primary flex items-center gap-1"
          >
            <Plus className="w-3 h-3" />
            إضافة خط
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {lines?.map((line) => (
            <div key={line.id} className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
              <h4 className="font-medium text-foreground/80">{line.name}</h4>
              <p className="text-sm text-muted-foreground/60">السعة: {line.hourly_capacity} وحدة/ساعة</p>
              <div className="flex items-center gap-2 mt-2">
                <span className={cn(
                  "text-xs px-2 py-0.5 rounded-full border",
                  line.is_active ? "border-emerald-500/30 text-emerald-500" : "border-red-500/30 text-red-500"
                )}>
                  {line.is_active ? 'نشط' : 'موقف'}
                </span>
                <Link
                  href={`/manufacturing/lines/${line.id}`}
                  className="text-xs text-primary/70 hover:text-primary"
                >
                  إدارة
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* الصيانة التنبؤية */}
      <div>
        <h2 className="text-lg font-semibold text-foreground/80 mb-3 flex items-center gap-2">
          <Wrench className="w-5 h-5 text-primary" />
          رادار الصيانة التنبؤية
        </h2>
        <MaintenanceRadar lineId={lines?.[0]?.id || 0} />
      </div>
    </div>
  );
}