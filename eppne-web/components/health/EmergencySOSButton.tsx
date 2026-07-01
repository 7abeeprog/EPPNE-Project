// components/health/EmergencySOSButton.tsx
'use client';

import { useState, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { callEmergency } from '@/services/health';
import { useHealthStore } from '@/store/healthStore';
import { Loader2, Phone, MapPin, AlertTriangle, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { v4 as uuidv4 } from 'uuid';

interface EmergencySOSButtonProps {
  className?: string;
}

export default function EmergencySOSButton({ className }: EmergencySOSButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [emergencyType, setEmergencyType] = useState<'MEDICAL_CRITICAL' | 'BIO_HAZARD' | 'ATHLETIC_INJURY'>('MEDICAL_CRITICAL');
  const [location, setLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [isGettingLocation, setIsGettingLocation] = useState(false);
  const { setActiveEmergency } = useHealthStore();

  const [idempotencyKey] = useState(() => `emergency-${uuidv4()}`);

  const mutation = useMutation({
    mutationFn: () => {
      if (!location) throw new Error('الموقع غير متاح');
      return callEmergency(
        {
          emergency_type: emergencyType,
          gps_location: location,
          vital_signs_on_route: {},
        },
        idempotencyKey
      );
    },
    onSuccess: (response) => {
      setActiveEmergency(response.data);
      setIsOpen(false);
    },
  });

  const getLocation = useCallback(() => {
    setIsGettingLocation(true);
    if (!navigator.geolocation) {
      alert('متصفحك لا يدعم تحديد الموقع الجغرافي');
      setIsGettingLocation(false);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
        });
        setIsGettingLocation(false);
      },
      (err) => {
        alert(`فشل في تحديد الموقع: ${err.message}`);
        setIsGettingLocation(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }, []);

  const handleEmergencyCall = () => {
    if (!location) {
      getLocation();
      return;
    }
    mutation.mutate();
  };

  return (
    <div className={cn("relative", className)}>
      {/* زر SOS الرئيسي */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "relative w-16 h-16 rounded-full flex items-center justify-center",
          "bg-red-500 text-white shadow-[0_0_60px_rgba(239,68,68,0.4)]",
          "hover:shadow-[0_0_80px_rgba(239,68,68,0.6)] transition-all duration-300",
          "animate-pulse hover:animate-none",
          "border-2 border-white/20"
        )}
      >
        <Phone className="w-8 h-8" />
        <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 animate-ping" />
      </button>

      {/* النافذة المنبثقة */}
      {isOpen && (
        <div className="absolute bottom-20 left-1/2 -translate-x-1/2 w-80 p-4 rounded-2xl bg-card/90 backdrop-blur-3xl border border-red-500/30 shadow-[0_20px_80px_-20px_rgba(0,0,0,0.6)] animate-in zoom-in-95 duration-200">
          <button
            onClick={() => setIsOpen(false)}
            className="absolute top-2 right-2 p-1 rounded-lg hover:bg-white/10 transition-colors"
          >
            <X className="w-4 h-4 text-muted-foreground/60" />
          </button>

          <h4 className="text-lg font-bold text-foreground/90 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            نداء طوارئ
          </h4>

          <div className="mt-3 space-y-3">
            <div>
              <label className="text-xs text-muted-foreground/60">نوع الطوارئ</label>
              <select
                value={emergencyType}
                onChange={(e) => setEmergencyType(e.target.value as any)}
                className="w-full mt-1 px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-primary/30 outline-none text-sm"
              >
                <option value="MEDICAL_CRITICAL">حرج طبي</option>
                <option value="BIO_HAZARD">خطر بيولوجي</option>
                <option value="ATHLETIC_INJURY">إصابة رياضية</option>
              </select>
            </div>

            <div className="flex items-center gap-2 text-xs">
              <MapPin className="w-4 h-4 text-primary/60" />
              <span className="text-muted-foreground/60">
                {location ? `📍 ${location.lat.toFixed(6)}, ${location.lng.toFixed(6)}` : '⚠️ الموقع غير متاح'}
              </span>
              {!location && (
                <button
                  onClick={getLocation}
                  disabled={isGettingLocation}
                  className="text-primary hover:underline text-xs"
                >
                  {isGettingLocation ? 'جاري التحديد...' : 'تحديد الموقع'}
                </button>
              )}
            </div>

            <button
              onClick={handleEmergencyCall}
              disabled={mutation.isPending || !location}
              className={cn(
                "w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-bold text-white transition-all duration-300",
                "bg-red-500 hover:bg-red-600 shadow-[0_0_30px_rgba(239,68,68,0.3)]",
                "disabled:opacity-50 disabled:cursor-not-allowed"
              )}
            >
              {mutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Phone className="w-4 h-4" />
              )}
              {mutation.isPending ? 'جاري الإرسال...' : 'إرسال النداء'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}