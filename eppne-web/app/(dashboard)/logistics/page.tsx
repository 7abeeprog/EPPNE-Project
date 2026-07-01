// app/(dashboard)/logistics/page.tsx
'use client';

import { useLogisticsStats } from '@/hooks/logistics/useStats';
import { useWarehouses } from '@/hooks/logistics/useWarehouses';
import { useInventory } from '@/hooks/logistics/useInventory';
import { useLowStock } from '@/hooks/logistics/useInventory';
import { useEquipment } from '@/hooks/logistics/useEquipment';
import { Loader2, Warehouse, Package, Wrench, AlertTriangle, TrendingUp, Building2 } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

export default function LogisticsDashboard() {
  const { data: stats, isLoading: statsLoading } = useLogisticsStats();
  const { data: warehouses, isLoading: wLoading } = useWarehouses();
  const { data: inventory, isLoading: iLoading } = useInventory();
  const { data: lowStock, isLoading: lLoading } = useLowStock();
  const { data: equipment, isLoading: eLoading } = useEquipment();

  const isLoading = statsLoading || wLoading || iLoading || lLoading || eLoading;

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const statCards = [
    { label: 'المخازن النشطة', value: stats?.active_warehouses || 0, icon: Building2, color: 'text-blue-500' },
    { label: 'عناصر المخزون', value: stats?.total_inventory_items || 0, icon: Package, color: 'text-emerald-500' },
    { label: 'المعدات المتاحة', value: stats?.available_equipment || 0, icon: Wrench, color: 'text-amber-500' },
    { label: 'مخزون منخفض', value: stats?.low_stock_items || 0, icon: AlertTriangle, color: 'text-red-500' },
    { label: 'القيمة الإجمالية', value: `${stats?.total_value_mrusdt?.toFixed(2) || 0} MR_USDT`, icon: TrendingUp, color: 'text-purple-500' },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground/90">📦 اللوجيستيات والمخازن</h1>
          <p className="text-sm text-muted-foreground/70">إدارة المخازن، المخزون، والمعدات</p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/logistics/warehouses/create"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
          >
            <Building2 className="w-4 h-4" />
            مخزن جديد
          </Link>
          <Link
            href="/logistics/inventory/receive"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors"
          >
            <Package className="w-4 h-4" />
            استلام مخزون
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {statCards.map((stat, idx) => (
          <div key={idx} className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
            <div className="flex items-center gap-2">
              <stat.icon className={cn("w-4 h-4", stat.color)} />
              <span className="text-xs text-muted-foreground/50">{stat.label}</span>
            </div>
            <p className="mt-2 text-lg font-bold text-foreground/90">{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          href="/logistics/warehouses"
          className="p-6 rounded-2xl bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <Building2 className="w-8 h-8 mx-auto text-blue-500" />
          <h3 className="mt-2 font-medium">المخازن</h3>
          <p className="text-sm text-muted-foreground/50">إدارة المخازن والمناطق</p>
        </Link>
        <Link
          href="/logistics/inventory"
          className="p-6 rounded-2xl bg-gradient-to-br from-emerald-500/10 to-teal-500/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <Package className="w-8 h-8 mx-auto text-emerald-500" />
          <h3 className="mt-2 font-medium">المخزون</h3>
          <p className="text-sm text-muted-foreground/50">تتبع المنتجات والكميات</p>
        </Link>
        <Link
          href="/logistics/equipment"
          className="p-6 rounded-2xl bg-gradient-to-br from-amber-500/10 to-orange-500/10 border border-white/10 hover:border-primary/20 transition-all text-center"
        >
          <Wrench className="w-8 h-8 mx-auto text-amber-500" />
          <h3 className="mt-2 font-medium">المعدات</h3>
          <p className="text-sm text-muted-foreground/50">إدارة المعدات والصيانة</p>
        </Link>
      </div>

      {lowStock && lowStock.length > 0 && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/30">
          <h3 className="text-sm font-medium text-red-500 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            تنبيه: مخزون منخفض
          </h3>
          <div className="mt-2 space-y-1">
            {lowStock.slice(0, 3).map((item) => (
              <div key={item.id} className="text-sm text-red-500/80 flex items-center justify-between">
                <span>{item.product_name}</span>
                <span>{item.quantity} {item.unit} (الحد الأدنى: {item.min_stock_threshold})</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}