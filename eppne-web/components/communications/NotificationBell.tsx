// components/communications/NotificationBell.tsx
'use client';

import { useEffect, useState } from 'react';
import { useNotificationStore } from '@/store/notificationStore';
import { Bell, Check, Circle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useRouter } from 'next/navigation';

export const NotificationBell = () => {
  const router = useRouter();
  const { notifications, unreadCount, fetchNotifications, markAsRead } = useNotificationStore();
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
    }
  }, [isOpen, fetchNotifications]);

  const handleNotificationClick = (notification: any) => {
    // مارك كمقروء
    if (!notification.is_read) {
      markAsRead(notification.id);
    }
    // إعادة التوجيه بناءً على الـ data الموجودة في الإشعار (مثلاً: link إلى الصحة أو المالية)
    if (notification.data?.link) {
      router.push(notification.data.link);
    }
    setIsOpen(false);
  };

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs text-white">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80 max-h-96 overflow-y-auto">
        <DropdownMenuLabel className="flex justify-between items-center">
          <span>الإشعارات</span>
          {unreadCount > 0 && (
            <Button variant="ghost" size="sm" onClick={() => markAllAsRead()}>
              <Check className="mr-2 h-4 w-4" /> تحديد الكل كمقروء
            </Button>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {notifications.length === 0 ? (
          <div className="p-4 text-center text-muted-foreground text-sm">لا توجد إشعارات جديدة</div>
        ) : (
          notifications.map((notif) => (
            <DropdownMenuItem
              key={notif.id}
              className={`flex flex-col items-start p-3 cursor-pointer ${!notif.is_read ? 'bg-muted/50' : ''}`}
              onClick={() => handleNotificationClick(notif)}
            >
              <div className="flex items-start gap-2 w-full">
                {!notif.is_read && <Circle className="h-2 w-2 mt-1.5 text-blue-500 fill-blue-500 flex-shrink-0" />}
                <div className="flex-1">
                  <p className="text-sm font-medium">{notif.title}</p>
                  <p className="text-xs text-muted-foreground line-clamp-2">{notif.body}</p>
                  <p className="text-[10px] text-muted-foreground mt-1">
                    {new Date(notif.created_at).toLocaleString('ar-EG')}
                  </p>
                </div>
              </div>
            </DropdownMenuItem>
          ))
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem className="justify-center text-primary font-medium" onClick={() => router.push('/dashboard/communications/notifications')}>
          عرض جميع الإشعارات
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};