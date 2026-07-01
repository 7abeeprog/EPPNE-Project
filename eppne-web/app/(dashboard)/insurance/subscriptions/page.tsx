// app/(dashboard)/insurance/subscriptions/page.tsx
'use client';

import { useMySubscriptions } from '@/hooks/insurance/useSubscriptions';
import SubscriptionCard from '@/components/insurance/SubscriptionCard';
import { Loader2, FileText } from 'lucide-react';

export default function SubscriptionsPage() {
  const { data: subscriptions, isLoading } = useMySubscriptions();

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-foreground/90">📋 اشتراكاتي التأمينية</h1>
      {subscriptions?.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground/60">
          <FileText className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">لا توجد اشتراكات</p>
          <p className="text-sm">تصفح البوالص وابدأ بالاشتراك</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {subscriptions?.map((sub) => (
            <SubscriptionCard key={sub.id} subscription={sub} />
          ))}
        </div>
      )}
    </div>
  );
}