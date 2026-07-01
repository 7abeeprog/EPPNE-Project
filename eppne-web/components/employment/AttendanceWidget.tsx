// components/employment/AttendanceWidget.tsx
'use client';

import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { checkIn, checkOut, getMyContract } from '@/services/employment';
import { useEmploymentStore } from '@/store/employmentStore';
import { Loader2, CheckCircle, Clock, MapPin, Smartphone } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function AttendanceWidget() {
  const queryClient = useQueryClient();
  const { isCheckingIn, setIsCheckingIn } = useEmploymentStore();
  const [location, setLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [deviceFingerprint, setDeviceFingerprint] = useState('');
  const [todayRecord, setTodayRecord] = useState<{ check_in?: string; check_out?: string } | null>(null);

  // جلب العقد النشط
  const { data: contract } = useQuery({
    queryKey: ['my-contract'],
    queryFn: () => getMyContract().then(res => res.data).catch(() => null),
  });

  // جلب الحضور اليومي
  // يمكن استدعاء API للحصول على تسجيل اليوم

  // الحصول على الموقع الجغرافي
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLocation({
            lat: pos.coords.latitude,
            lng: pos.coords.longitude,
          });
        },
        () => {
          // استخدام موقع افتراضي إذا لم يتمكن المستخدم من المشاركة
          setLocation({ lat: 30.0444, lng: 31.2357 });
        }
      );
    }
  }, []);

  // توليد بصمة الجهاز
  useEffect(() => {
    const fp = localStorage.getItem('device_fingerprint');
    if (fp) {
      setDeviceFingerprint(fp);
    } else {
      const newFp = `device-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      localStorage.setItem('device_fingerprint', newFp);
      setDeviceFingerprint(newFp);
    }
  }, []);

  const checkInMutation = useMutation({
    mutationFn: () => {
      if (!contract) throw new Error('لا يوجد عقد نشط');
      if (!location) throw new Error('لم يتم تحديد الموقع');
      return checkIn(contract.id, {
        latitude: location.lat,
        longitude: location.lng,
        device_fingerprint: deviceFingerprint,
      });
    },
    onSuccess: (data) => {
      setTodayRecord({ check_in: data.data.check_in });
      queryClient.invalidateQueries({ queryKey: ['attendance'] });
    },
  });

  const checkOutMutation = useMutation({
    mutationFn: () => {
      if (!contract) throw new Error('لا يوجد عقد نشط');
      return checkOut(contract.id);
    },
    onSuccess: (data) => {
      setTodayRecord({
        check_in: todayRecord?.check_in,
        check_out: data.data.check_out,
      });
      queryClient.invalidateQueries({ queryKey: ['attendance'] });
    },
  });

  if (!contract) {
    return (
      <div className="p-4 text-center text-muted-foreground/60">
        <p>لا يوجد عقد عمل نشط</p>
        <p className="text-sm">لست موظفاً في أي مؤسسة حالياً</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground/60">العقد النشط</span>
        <span className="text-foreground/80 font-medium">{contract.job_title}</span>
      </div>

      <div className="flex items-center gap-2 text-xs text-muted-foreground/50">
        <MapPin className="w-3 h-3" />
        {location ? `${location.lat.toFixed(4)}, ${location.lng.toFixed(4)}` : 'جاري تحديد الموقع...'}
        <Smartphone className="w-3 h-3 ml-2" />
        {deviceFingerprint ? '✓' : 'جاري...'}
      </div>

      <div className="flex gap-3">
        {!todayRecord?.check_in ? (
          <button
            onClick={() => checkInMutation.mutate()}
            disabled={checkInMutation.isPending || !location}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-emerald-500/20 text-emerald-500 border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
          >
            {checkInMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
            تسجيل الحضور
          </button>
        ) : !todayRecord?.check_out ? (
          <button
            onClick={() => checkOutMutation.mutate()}
            disabled={checkOutMutation.isPending}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors disabled:opacity-50"
          >
            {checkOutMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Clock className="w-4 h-4" />}
            تسجيل الانصراف
          </button>
        ) : (
          <div className="w-full text-center text-sm text-emerald-500/70 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
            ✅ تم تسجيل الحضور والانصراف اليوم
            <div className="text-xs text-muted-foreground/40 mt-1">
              {todayRecord.check_in && `دخول: ${new Date(todayRecord.check_in).toLocaleTimeString('ar-EG')}`}
              {todayRecord.check_out && ` | خروج: ${new Date(todayRecord.check_out).toLocaleTimeString('ar-EG')}`}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}