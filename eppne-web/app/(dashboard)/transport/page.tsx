// app/(dashboard)/transport/page.tsx
'use client';

import { useRouter } from 'next/navigation';
import { useTransportStats } from '@/hooks/transport/useTransportStats';
import { useMyTrips } from '@/hooks/transport/useTrips';
import { useMyDeliveries } from '@/hooks/transport/useDeliveries';
import TransportStatsCards from '@/components/transport/TransportStatsCards';
import TripStatusBadge from '@/components/transport/TripStatusBadge';
import CarbonFootprintBadge from '@/components/transport/CarbonFootprintBadge';
import { Loader2, Plus, ArrowRight, Truck, Package, MapPin } from 'lucide-react';
import Link from 'next/link';
import { format } from 'date-fns/ar';
import { cn } from '@/lib/utils';

export default function TransportDashboard() {
  const router = useRouter();
  const { data: stats, isLoading: statsLoading } = useTransportStats();
  const { data: trips, isLoading: tripsLoading } = useMyTrips({ limit: 5 });
  const { data: deliveries, isLoading: deliveriesLoading } = useMyDeliveries();

  const isLoading = statsLoading || tripsLoading || deliveriesLoading;

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90 flex items-center gap-2">
            🚛 النقل والمواصلات
          </h1>
          <p className="text-sm text-muted-foreground/70">إدارة الأساطيل، الرحلات، والتوصيل الذكي</p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/transport/trips/create"
            className="px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
          >
            <Plus className="w-4 h-4 inline mr-1" />
            رحلة جديدة
          </Link>
          <Link
            href="/transport/deliveries/create"
            className="px-4 py-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors"
          >
            <Package className="w-4 h-4 inline mr-1" />
            طرد جديد
          </Link>
        </div>
      </div>

      {/* الإحصائيات */}
      {stats && <TransportStatsCards stats={stats} />}

      {/* رحلاتي الأخيرة */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-foreground/70 flex items-center gap-2">
              <Truck className="w-4 h-4" />
              رحلاتي الأخيرة
            </h3>
            <Link href="/transport/trips" className="text-xs text-primary/70 hover:text-primary flex items-center gap-1">
              عرض الكل <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          {trips?.length === 0 ? (
            <div className="text-center py-6 text-muted-foreground/40 text-sm">
              لا توجد رحلات
            </div>
          ) : (
            <div className="space-y-2">
              {trips?.slice(0, 3).map((trip) => (
                <div
                  key={trip.id}
                  className="flex items-center justify-between p-2 rounded-xl hover:bg-white/5 transition-colors cursor-pointer"
                  onClick={() => router.push(`/transport/trips/${trip.id}`)}
                >
                  <div>
                    <p className="text-sm font-medium text-foreground/80">رحلة #{trip.id}</p>
                    <p className="text-xs text-muted-foreground/50">
                      {format(new Date(trip.scheduled_start), 'dd/MM/yyyy HH:mm')}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {trip.total_distance_km > 0 && (
                      <CarbonFootprintBadge
                        carbonKg={trip.carbon_footprint_kg}
                        distanceKm={trip.total_distance_km}
                        className="text-[10px]"
                      />
                    )}
                    <TripStatusBadge status={trip.status} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* مهام التوصيل الأخيرة */}
        <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-foreground/70 flex items-center gap-2">
              <Package className="w-4 h-4" />
              مهام التوصيل
            </h3>
            <Link href="/transport/deliveries" className="text-xs text-primary/70 hover:text-primary flex items-center gap-1">
              عرض الكل <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          {deliveries?.length === 0 ? (
            <div className="text-center py-6 text-muted-foreground/40 text-sm">
              لا توجد مهام توصيل
            </div>
          ) : (
            <div className="space-y-2">
              {deliveries?.slice(0, 3).map((task) => (
                <div
                  key={task.id}
                  className="flex items-center justify-between p-2 rounded-xl hover:bg-white/5 transition-colors cursor-pointer"
                  onClick={() => router.push(`/transport/deliveries/${task.id}`)}
                >
                  <div>
                    <p className="text-sm font-medium text-foreground/80">طرد #{task.id}</p>
                    <p className="text-xs text-muted-foreground/50 truncate max-w-[120px]">
                      {task.pickup_address.address} → {task.dropoff_address.address}
                    </p>
                  </div>
                  <span className={cn(
                    "text-xs px-2 py-0.5 rounded-full border",
                    task.status === 'DELIVERED' ? "border-emerald-500/30 text-emerald-500" :
                    task.status === 'ASSIGNED' ? "border-blue-500/30 text-blue-500" :
                    task.status === 'PICKED_UP' ? "border-amber-500/30 text-amber-500" :
                    "border-gray-500/30 text-gray-500"
                  )}>
                    {task.status === 'DELIVERED' ? 'تم التسليم' :
                     task.status === 'ASSIGNED' ? 'تم التعيين' :
                     task.status === 'PICKED_UP' ? 'تم الاستلام' :
                     'قيد الانتظار'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}