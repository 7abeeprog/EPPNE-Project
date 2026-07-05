// app/(dashboard)/health/emergency/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useHealthStore } from '@/store/healthStore';
import { useAuth } from '@/hooks/auth/useAuth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { AlertCircle, Ambulance, MapPin, HeartPulse } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function EmergencyPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { callEmergency, currentEmergency, isLoading, error } = useHealthStore();
  
  const [emergencyType, setEmergencyType] = useState<'MEDICAL_CRITICAL' | 'BIO_HAZARD' | 'ATHLETIC_INJURY' | 'VETERINARY_EMERGENCY' | 'AGRICULTURAL_PLAGUE' | 'ALGAE_BLOOM'>('MEDICAL_CRITICAL');
  const [facilityId, setFacilityId] = useState<number | null>(null);
  const [gpsLocation, setGpsLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [isLocating, setIsLocating] = useState(false);

  // جلب الموقع الجغرافي تلقائياً
  const getLocation = () => {
    setIsLocating(true);
    if (!navigator.geolocation) {
      toast.error('متصفحك لا يدعم تحديد الموقع');
      setIsLocating(false);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setGpsLocation({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        });
        setIsLocating(false);
        toast.success('تم تحديد موقعك بنجاح');
      },
      (error) => {
        console.error('Geolocation error:', error);
        toast.error('فشل في تحديد الموقع، يرجى إدخاله يدوياً');
        setIsLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  // استدعاء الطوارئ
  const handleEmergencyCall = async () => {
    if (!gpsLocation) {
      toast.error('يرجى تحديد موقعك أولاً');
      return;
    }

    try {
      const response = await callEmergency({
        patient_id: user?.id,
        facility_id: facilityId,
        emergency_type: emergencyType,
        gps_location: { lat: gpsLocation.lat, lng: gpsLocation.lng },
        vital_signs_on_route: null,
      });

      toast.success('تم استدعاء الطوارئ بنجاح! سيتم توجيه الفريق الطبي فوراً.');
      router.push(`/dashboard/health/emergency/${response.id}`);
    } catch (err) {
      toast.error(error || 'حدث خطأ أثناء استدعاء الطوارئ');
    }
  };

  return (
    <div className="container mx-auto py-8 max-w-2xl">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-3 bg-red-100 rounded-full">
          <Ambulance className="h-8 w-8 text-red-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-red-700">🚨 استدعاء الطوارئ</h1>
          <p className="text-muted-foreground text-sm">في حالات الطوارئ الطبية أو الكوارث، نرجو استخدام هذا النموذج لتوجيه الفرق المختصة.</p>
        </div>
      </div>

      <Card className="border-red-200 shadow-lg">
        <CardHeader className="bg-red-50 border-b border-red-100">
          <CardTitle className="text-red-700 flex items-center gap-2">
            <AlertCircle className="h-5 w-5" />
            نموذج طلب الإسعاف
          </CardTitle>
          <CardDescription>يرجى تعبئة البيانات بدقة لتسريع عملية الاستجابة.</CardDescription>
        </CardHeader>

        <CardContent className="space-y-6 pt-6">
          {/* اختيار نوع الطوارئ */}
          <div className="space-y-2">
            <Label htmlFor="emergency-type">نوع الطوارئ *</Label>
            <Select
              value={emergencyType}
              onValueChange={(value) => setEmergencyType(value as any)}
            >
              <SelectTrigger id="emergency-type">
                <SelectValue placeholder="اختر نوع الطوارئ" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="MEDICAL_CRITICAL">🏥 حالة طبية حرجة</SelectItem>
                <SelectItem value="BIO_HAZARD">🧪 خطر بيولوجي</SelectItem>
                <SelectItem value="ATHLETIC_INJURY">🏃 إصابة رياضية</SelectItem>
                <SelectItem value="VETERINARY_EMERGENCY">🐾 طوارئ بيطرية</SelectItem>
                <SelectItem value="AGRICULTURAL_PLAGUE">🌾 آفة زراعية</SelectItem>
                <SelectItem value="ALGAE_BLOOM">🌊 ازدهار الطحالب</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* المنشأة الصحية (اختياري) */}
          <div className="space-y-2">
            <Label htmlFor="facility">المنشأة الصحية المستهدفة (اختياري)</Label>
            <Input
              id="facility"
              type="number"
              placeholder="معرف المنشأة (اختياري)"
              value={facilityId || ''}
              onChange={(e) => setFacilityId(e.target.value ? Number(e.target.value) : null)}
            />
            <p className="text-xs text-muted-foreground">إذا كنت تعرف أقرب مستشفى، أدخل معرفه.</p>
          </div>

          {/* الموقع الجغرافي */}
          <div className="space-y-2">
            <Label>الموقع الجغرافي *</Label>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={getLocation}
                disabled={isLocating}
                className="flex-1"
              >
                <MapPin className="mr-2 h-4 w-4" />
                {isLocating ? 'جاري تحديد الموقع...' : (gpsLocation ? 'تحديث الموقع' : 'تحديد موقعي الحالي')}
              </Button>
            </div>
            {gpsLocation && (
              <div className="bg-muted p-2 rounded text-sm">
                <span className="font-medium">العرض:</span> {gpsLocation.lat.toFixed(6)}،
                <span className="font-medium mr-2">الطول:</span> {gpsLocation.lng.toFixed(6)}
              </div>
            )}
            <p className="text-xs text-muted-foreground">نوصي بتشغيل GPS لتحديد الموقع بدقة.</p>
          </div>
        </CardContent>

        <CardFooter className="flex flex-col items-stretch gap-3 bg-red-50 border-t border-red-100">
          <Button
            onClick={handleEmergencyCall}
            disabled={isLoading || !gpsLocation}
            className="bg-red-600 hover:bg-red-700 text-white text-lg py-6"
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <span className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full" />
                جاري الإرسال...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Ambulance className="h-5 w-5" />
                استدعاء الطوارئ الآن
              </span>
            )}
          </Button>
          {!gpsLocation && (
            <p className="text-center text-sm text-red-500">⚠️ يجب تحديد الموقع الجغرافي أولاً</p>
          )}
        </CardFooter>
      </Card>

      {/* حالة الطوارئ الحالية (إذا وجدت) */}
      {currentEmergency && (
        <Card className="mt-6 border-green-200 bg-green-50">
          <CardHeader>
            <CardTitle className="text-green-700 flex items-center gap-2">
              <HeartPulse className="h-5 w-5" />
              حالة البلاغ الحالي
            </CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 gap-2 text-sm">
              <dt className="font-medium">رقم البلاغ:</dt>
              <dd>#{currentEmergency.id}</dd>
              <dt className="font-medium">الحالة:</dt>
              <dd className="font-bold text-blue-600">{currentEmergency.status}</dd>
              <dt className="font-medium">وقت الإرسال:</dt>
              <dd>{new Date(currentEmergency.dispatch_time).toLocaleString('ar-EG')}</dd>
              <dt className="font-medium">نوع الطوارئ:</dt>
              <dd>{currentEmergency.emergency_type}</dd>
            </dl>
          </CardContent>
        </Card>
      )}
    </div>
  );
}