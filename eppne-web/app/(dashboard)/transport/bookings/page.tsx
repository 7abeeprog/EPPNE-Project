// app/(dashboard)/transport/bookings/page.tsx
'use client';

import { useState } from 'react';
import { useMyBookings, useBookTrip, useCancelBooking } from '@/hooks/transport/useBookings';
import { useTrips } from '@/hooks/transport/useTrips';
import TripStatusBadge from '@/components/transport/TripStatusBadge';
import { Loader2, Calendar, User, Package, X, CheckCircle, XCircle, Clock, Search, Eye } from 'lucide-react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns/ar';
import { v4 as uuidv4 } from 'uuid';

export default function BookingsPage() {
  const [showForm, setShowForm] = useState(false);
  const [selectedTripId, setSelectedTripId] = useState<number | null>(null);
  const [seatsCount, setSeatsCount] = useState(1);
  const [bookingType, setBookingType] = useState<'PASSENGER' | 'FREIGHT'>('PASSENGER');
  const [weightKg, setWeightKg] = useState<number | undefined>(undefined);

  const { data: bookings, isLoading: bookingsLoading } = useMyBookings();
  const { data: trips, isLoading: tripsLoading } = useTrips({ status: 'SCHEDULED' });

  const bookTrip = useBookTrip();
  const cancelBooking = useCancelBooking();

  const isLoading = bookingsLoading || tripsLoading;

  const handleBook = () => {
    if (!selectedTripId) return;
    const idempotencyKey = `booking-${selectedTripId}-${uuidv4()}`;
    bookTrip.mutate({
      data: {
        trip_id: selectedTripId,
        booking_type: bookingType,
        seats_count: bookingType === 'PASSENGER' ? seatsCount : undefined,
        weight_kg: bookingType === 'FREIGHT' ? weightKg : undefined,
      },
      idempotencyKey,
    });
    setShowForm(false);
    setSelectedTripId(null);
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
            🎫 حجوزاتي
          </h1>
          <p className="text-sm text-muted-foreground/70">إدارة حجوزات الرحلات</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground font-medium shadow-[0_0_30px_rgba(var(--primary-rgb),0.3)] hover:shadow-[0_0_50px_rgba(var(--primary-rgb),0.5)] transition-all duration-300"
        >
          <Plus className="w-4 h-4" />
          حجز جديد
        </button>
      </div>

      {showForm && (
        <div className="p-6 rounded-2xl bg-card/30 backdrop-blur-xl border border-white/10 space-y-4">
          <h3 className="text-lg font-semibold text-foreground/90">✏️ حجز رحلة</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-muted-foreground/60">الرحلة</label>
              <select
                value={selectedTripId || ''}
                onChange={(e) => setSelectedTripId(parseInt(e.target.value))}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              >
                <option value="">اختر رحلة</option>
                {trips?.map((trip) => (
                  <option key={trip.id} value={trip.id}>
                    رحلة #{trip.id} - {format(new Date(trip.scheduled_start), 'dd/MM/yyyy HH:mm')}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground/60">نوع الحجز</label>
              <select
                value={bookingType}
                onChange={(e) => setBookingType(e.target.value as 'PASSENGER' | 'FREIGHT')}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              >
                <option value="PASSENGER">راكب</option>
                <option value="FREIGHT">شحن</option>
              </select>
            </div>
            {bookingType === 'PASSENGER' && (
              <div>
                <label className="text-sm text-muted-foreground/60">عدد الركاب</label>
                <input
                  type="number"
                  min="1"
                  value={seatsCount}
                  onChange={(e) => setSeatsCount(parseInt(e.target.value) || 1)}
                  className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                />
              </div>
            )}
            {bookingType === 'FREIGHT' && (
              <div>
                <label className="text-sm text-muted-foreground/60">الوزن (كجم)</label>
                <input
                  type="number"
                  min="0.1"
                  step="0.1"
                  value={weightKg || ''}
                  onChange={(e) => setWeightKg(parseFloat(e.target.value) || undefined)}
                  className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
                />
              </div>
            )}
          </div>
          <div className="flex gap-3 pt-2">
            <button
              onClick={handleBook}
              disabled={bookTrip.isPending || !selectedTripId}
              className="px-6 py-2 rounded-xl bg-primary text-primary-foreground font-medium disabled:opacity-50 flex items-center gap-2"
            >
              {bookTrip.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              تأكيد الحجز
            </button>
            <button
              onClick={() => { setShowForm(false); setSelectedTripId(null); }}
              className="px-6 py-2 rounded-xl border border-white/10 hover:bg-white/5 transition-colors"
            >
              إلغاء
            </button>
          </div>
        </div>
      )}

      {bookings?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <Ticket className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد حجوزات</p>
          <p className="text-sm">احجز رحلة للبدء</p>
        </div>
      ) : (
        <div className="space-y-3">
          {bookings?.map((booking) => (
            <div
              key={booking.id}
              className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-foreground/80">حجز #{booking.id}</h4>
                  <p className="text-xs text-muted-foreground/50 flex items-center gap-2">
                    <Calendar className="w-3 h-3" />
                    {booking.trip_id ? `رحلة #${booking.trip_id}` : 'غير محدد'}
                    {booking.booking_type === 'PASSENGER' ? ` · ${booking.seats_count} راكب` : ` · ${booking.weight_kg} كجم`}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={cn(
                    "text-xs px-2 py-0.5 rounded-full border",
                    booking.status === 'CONFIRMED' ? "border-emerald-500/30 text-emerald-500" :
                    booking.status === 'CHECKED_IN' ? "border-blue-500/30 text-blue-500" :
                    "border-red-500/30 text-red-500"
                  )}>
                    {booking.status === 'CONFIRMED' ? 'مؤكد' :
                     booking.status === 'CHECKED_IN' ? 'تم الدخول' :
                     'ملغي'}
                  </span>
                  {booking.fare_paid_mrusdt > 0 && (
                    <span className="text-xs text-primary/70">{booking.fare_paid_mrusdt} MR_USDT</span>
                  )}
                  {booking.status === 'CONFIRMED' && (
                    <button
                      onClick={() => cancelBooking.mutate(booking.id)}
                      className="p-1 rounded-lg hover:bg-red-500/10 transition-colors"
                    >
                      <X className="w-4 h-4 text-red-500/50 hover:text-red-500" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}