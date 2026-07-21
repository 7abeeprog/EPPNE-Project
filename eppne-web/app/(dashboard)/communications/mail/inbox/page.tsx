'use client';
import { useQuery } from '@tanstack/react-query';
import { CommunicationsService } from '@/services/communications.service';
import MailSidebar from '@/components/communications/MailSidebar';
import MailList from '@/components/communications/MailList';
import { Loader2 } from 'lucide-react';

export default function InboxPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['mail', 'inbox'],
    queryFn: () => CommunicationsService.getInbox({ limit: 50 }),
    staleTime: 2 * 60 * 1000,
    // ✅ إيقاف إعادة المحاولة التلقائية
    retry: false,
    // ✅ إيقاف إعادة الجلب عند التركيز على النافذة
    refetchOnWindowFocus: false,
  });

  // عرض رسالة خطأ واضحة إذا فشل الطلب
  if (error) {
    return (
      <div className="flex h-full gap-4 p-4">
        <MailSidebar active="inbox" />
        <div className="flex-1 rounded-2xl bg-card/30 backdrop-blur-2xl border border-white/10 p-4">
          <div className="flex flex-col items-center justify-center h-64 text-red-500">
            <p className="text-lg font-semibold">⚠️ فشل تحميل صندوق الوارد</p>
            <p className="text-sm text-muted-foreground">يرجى تحديث الصفحة أو المحاولة لاحقاً</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full gap-4 p-4">
      <MailSidebar active="inbox" />
      <div className="flex-1 rounded-2xl bg-card/30 backdrop-blur-2xl border border-white/10 p-4 overflow-y-auto">
        <h2 className="text-lg font-bold text-foreground/80 mb-4 flex items-center gap-2">
          📥 صندوق الوارد
          <span className="text-xs bg-primary/20 text-primary px-2 py-0.5 rounded-full">
            {data?.length || 0}
          </span>
        </h2>
        {isLoading ? (
          <div className="flex justify-center items-center h-32">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
          </div>
        ) : (
          <MailList items={data || []} />
        )}
      </div>
    </div>
  );
}