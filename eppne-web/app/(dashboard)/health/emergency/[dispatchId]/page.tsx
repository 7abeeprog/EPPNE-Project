// app/(dashboard)/health/emergency/[dispatchId]/page.tsx
'use client';

import { useParams } from 'next/navigation';
import { useEffect } from 'react';
import { useHealthStore } from '@/store/healthStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

export default function EmergencyStatusPage() {
  const { dispatchId } = useParams();
  const { currentEmergency, fetchEmergencyStatus, isLoading } = useHealthStore();

  useEffect(() => {
    if (dispatchId) {
      fetchEmergencyStatus(Number(dispatchId));
    }
  }, [dispatchId, fetchEmergencyStatus]);

  if (isLoading) {
    return (
      <div className="container mx-auto py-8 max-w-2xl">
        <Skeleton className="h-10 w-48 mb-4" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!currentEmergency) {
    return (
      <div className="container mx-auto py-8 text-center text-muted-foreground">
        لم يتم العثور على بلاغ بهذا الرقم.
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>تفاصيل بلاغ الطوارئ #{currentEmergency.id}</span>
            <Badge variant={currentEmergency.status === 'COMPLETED' ? 'success' : 'default'}>
              {currentEmergency.status}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <span className="font-medium">نوع الطوارئ:</span>{' '}
            <span>{currentEmergency.emergency_type}</span>
          </div>
          <div>
            <span className="font-medium">الموقع:</span>{' '}
            <span>
              خط عرض: {currentEmergency.gps_location.lat?.toFixed(6)}،
              خط طول: {currentEmergency.gps_location.lng?.toFixed(6)}
            </span>
          </div>
          <div>
            <span className="font-medium">وقت الإرسال:</span>{' '}
            <span>{new Date(currentEmergency.dispatch_time).toLocaleString('ar-EG')}</span>
          </div>
          {currentEmergency.arrival_time && (
            <div>
              <span className="font-medium">وقت الوصول المتوقع:</span>{' '}
              <span>{new Date(currentEmergency.arrival_time).toLocaleString('ar-EG')}</span>
            </div>
          )}
          {currentEmergency.facility_id && (
            <div>
              <span className="font-medium">المنشأة الصحية:</span>{' '}
              <span>#{currentEmergency.facility_id}</span>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}