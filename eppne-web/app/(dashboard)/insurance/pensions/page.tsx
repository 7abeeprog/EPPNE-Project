// app/(dashboard)/insurance/pensions/page.tsx
'use client';

import { useMyPensions } from '@/hooks/insurance/usePensions';
import PensionCard from '@/components/insurance/PensionCard';
import { Loader2, DollarSign } from 'lucide-react';

export default function PensionsPage() {
  const { data: pensions, isLoading } = useMyPensions();

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-foreground/90">💰 معاشاتي</h1>
      {pensions?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <DollarSign className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد معاشات</p>
          <p className="text-sm">سيظهر هنا معاشاتك النشطة</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {pensions?.map((pension) => (
            <PensionCard key={pension.id} pension={pension} />
          ))}
        </div>
      )}
    </div>
  );
}