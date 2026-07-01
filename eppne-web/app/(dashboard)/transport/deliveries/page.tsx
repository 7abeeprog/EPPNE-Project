// app/(dashboard)/transport/deliveries/page.tsx
'use client';

import { useState } from 'react';
import { useMyDeliveries, useCreateDelivery, usePayDelivery, useCompleteDelivery } from '@/hooks/transport/useDeliveries';
import { useTrips } from '@/hooks/transport/useTrips';
import { Loader2, Plus, Package, MapPin, CheckCircle, XCircle, Truck, Search, Eye, ChevronDown, ChevronUp, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns/ar';
import { v4 as uuidv4 } from 'uuid';

export default function DeliveriesPage() {
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    receiver_id: 0,
    pickup_address: { address: '', lat: 0, lng: 0 },
    dropoff_address: { address: '', lat: 0, lng: 0 },
    estimated_distance_km: undefined as number | undefined,
    delivery_fee_mrusdt: 0,
  });
  const [expandedTask, setExpandedTask] = useState<number | null>(null);

  const { data: deliveries, isLoading: deliveriesLoading } = useMyDeliveries();
  const { data: trips } = useTrips({ status: 'SCHEDULED' });

  const createDelivery = useCreateDelivery();
  const payDelivery = usePayDelivery();
  const completeDelivery = useCompleteDelivery();

  const isLoading = deliveriesLoading;

  const handleCreate = () => {
    createDelivery.mutate(formData);
    setShowForm(false);
    setFormData({ receiver_id: 0, pickup_address: { address: '', lat: 0, lng: 0 }, dropoff_address: { address: '', lat: 0, lng: 0 }, estimated_distance_km: undefined, delivery_fee_mrusdt: 0 });
  };

  const handlePay = (taskId: number) => {
    const idempotencyKey = `delivery-pay-${taskId}-${uuidv4()}`;
    payDelivery.mutate({ taskId, idempotencyKey });
  };

  const handleComplete = (taskId: number) => {
    const proof = prompt('أدخل رابط إثبات التسليم (صورة/توقيع):');
    if (proof) {
      completeDelivery.mutate({ taskId, proofHash: proof });
    }
  };

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
            <Package className="w-6 h-6 text-primary" />
            مهام التوصيل
          </h1>
          <p className="text-sm text-muted-foreground/70">إدارة مهام التوصيل</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          مهمة توصيل جديدة
        </button>
      </div>

      {showForm && (
        <div className="p-6 rounded-2xl bg-card/30 backdrop-blur-xl border border-white/10 space-y-4">
          <h3 className="text-lg font-semibold text-foreground/90">✏️ إنشاء مهمة توصيل</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-muted-foreground/60">معرف المستلم</label>
              <input
                type="number"
                value={formData.receiver_id}
                onChange={(e) => setFormData({ ...formData, receiver_id: parseInt(e.target.value) })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="معرف المستلم"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">رسوم التوصيل (MR_USDT)</label>
              <input
                type="number"
                step="0.01"
                value={formData.delivery_fee_mrusdt}
                onChange={(e) => setFormData({ ...formData, delivery_fee_mrusdt: parseFloat(e.target.value) || 0 })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="0.00"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">عنوان الاستلام</label>
              <input
                type="text"
                value={formData.pickup_address.address}
                onChange={(e) => setFormData({ ...formData, pickup_address: { ...formData.pickup_address, address: e.target.value } })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="عنوان الاستلام"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">عنوان التسليم</label>
              <input
                type="text"
                value={formData.dropoff_address.address}
                onChange={(e) => setFormData({ ...formData, dropoff_address: { ...formData.dropoff_address, address: e.target.value } })}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                placeholder="عنوان التسليم"
              />
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              onClick={handleCreate}
              disabled={createDelivery.isPending || !formData.receiver_id || !formData.pickup_address.address || !formData.dropoff_address.address}
              className="px-6 py-2 rounded-xl bg-primary text-primary-foreground font-medium disabled:opacity-50 flex items-center gap-2"
            >
              {createDelivery.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              إنشاء
            </button>
            <button
              onClick={() => { setShowForm(false); setFormData({ receiver_id: 0, pickup_address: { address: '', lat: 0, lng: 0 }, dropoff_address: { address: '', lat: 0, lng: 0 }, estimated_distance_km: undefined, delivery_fee_mrusdt: 0 }); }}
              className="px-6 py-2 rounded-xl border border-white/10 hover:bg-white/5 transition-colors"
            >
              إلغاء
            </button>
          </div>
        </div>
      )}

      {deliveries?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <Package className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد مهام توصيل</p>
          <p className="text-sm">أنشئ مهمة توصيل جديدة للبدء</p>
        </div>
      ) : (
        <div className="space-y-3">
          {deliveries?.map((task) => {
            const isExpanded = expandedTask === task.id;

            return (
              <div
                key={task.id}
                className={cn(
                  "rounded-2xl border transition-all duration-300 bg-card/20 backdrop-blur-sm",
                  task.status === 'DELIVERED' ? "border-emerald-500/30" : "border-white/10",
                  isExpanded && "border-primary/30 shadow-[0_0_40px_-15px_rgba(var(--primary-rgb),0.15)]"
                )}
              >
                <div
                  className="flex items-center gap-4 p-4 cursor-pointer"
                  onClick={() => setExpandedTask(isExpanded ? null : task.id)}
                >
                  <div className={cn(
                    "flex-shrink-0 w-3 h-3 rounded-full",
                    task.status === 'DELIVERED' ? "bg-emerald-500" :
                    task.status === 'ASSIGNED' ? "bg-blue-500" :
                    task.status === 'PICKED_UP' ? "bg-amber-500" :
                    "bg-gray-500"
                  )} />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3">
                      <h4 className="font-medium text-foreground/80">
                        طرد #{task.id}
                      </h4>
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
                    <div className="flex flex-wrap items-center gap-3 mt-0.5 text-xs text-muted-foreground/50">
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3 h-3" />
                        {task.pickup_address.address} → {task.dropoff_address.address}
                      </span>
                      {task.estimated_distance_km && (
                        <span className="flex items-center gap-1">
                          <Truck className="w-3 h-3" />
                          {task.estimated_distance_km} كم
                        </span>
                      )}
                      {task.delivery_fee_mrusdt > 0 && (
                        <span className="text-primary/70">{task.delivery_fee_mrusdt} MR_USDT</span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {task.status === 'PENDING' && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handlePay(task.id); }}
                        disabled={payDelivery.isPending}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors text-sm disabled:opacity-50"
                      >
                        {payDelivery.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle className="w-3 h-3" />}
                        دفع
                      </button>
                    )}
                    {task.status === 'ASSIGNED' || task.status === 'PICKED_UP' ? (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleComplete(task.id); }}
                        disabled={completeDelivery.isPending}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-emerald-500/20 text-emerald-500 border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors text-sm disabled:opacity-50"
                      >
                        {completeDelivery.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle className="w-3 h-3" />}
                        تسليم
                      </button>
                    ) : null}
                    <button className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
                      <Eye className="w-4 h-4 text-muted-foreground/50" />
                    </button>
                  </div>

                  <button className="p-1 rounded-lg hover:bg-white/10 transition-colors">
                    {isExpanded ? <ChevronUp className="w-4 h-4 text-muted-foreground/50" /> : <ChevronDown className="w-4 h-4 text-muted-foreground/50" />}
                  </button>
                </div>

                {isExpanded && (
                  <div className="px-4 pb-4 pt-0 border-t border-white/5 space-y-3">
                    <div className="grid grid-cols-2 gap-3 pt-3">
                      <div className="p-3 rounded-xl bg-white/5">
                        <p className="text-xs text-muted-foreground/50">المرسل</p>
                        <p className="text-sm font-medium text-foreground/80">#{task.sender_id}</p>
                      </div>
                      <div className="p-3 rounded-xl bg-white/5">
                        <p className="text-xs text-muted-foreground/50">المستلم</p>
                        <p className="text-sm font-medium text-foreground/80">#{task.receiver_id}</p>
                      </div>
                      <div className="p-3 rounded-xl bg-white/5">
                        <p className="text-xs text-muted-foreground/50">رسوم التوصيل</p>
                        <p className="text-sm font-medium text-foreground/80">{task.delivery_fee_mrusdt} MR_USDT</p>
                      </div>
                      <div className="p-3 rounded-xl bg-white/5">
                        <p className="text-xs text-muted-foreground/50">المسافة المقدرة</p>
                        <p className="text-sm font-medium text-foreground/80">{task.estimated_distance_km || '—'} كم</p>
                      </div>
                    </div>
                    {task.delivery_proof_hash && (
                      <div className="p-3 rounded-xl bg-white/5 border border-white/5">
                        <p className="text-xs text-muted-foreground/50">إثبات التسليم</p>
                        <p className="text-sm font-mono text-foreground/70 truncate">{task.delivery_proof_hash}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}