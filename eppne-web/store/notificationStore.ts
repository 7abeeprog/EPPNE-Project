// store/notificationStore.ts
import { create } from 'zustand';
import { CommunicationsService } from '@/services/communications.service';
import { components } from '@/src/lib/api-types';

// استيراد النوع من api-types لأنه لم يعد مُصدَّراً من communications.service
type NotificationResponse = components['schemas']['NotificationResponse'];

interface NotificationState {
  notifications: NotificationResponse[];
  unreadCount: number;
  isLoading: boolean;
  fetchNotifications: () => Promise<void>;
  markAsRead: (id: number) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  addNotification: (notification: NotificationResponse) => void; // للإشعارات الفورية (WebSocket)
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  unreadCount: 0,
  isLoading: false,

  fetchNotifications: async () => {
    set({ isLoading: true });
    try {
      // نجلب أول 50 إشعار غير مقروءة لعرضها في الجرس، ونستخدم is_read=false
      const data = await CommunicationsService.getMyNotifications({ is_read: false, limit: 50 });
      set({
        notifications: data,
        unreadCount: data.filter(n => !n.is_read).length,
        isLoading: false
      });
    } catch (error) {
      set({ isLoading: false });
      console.error('Failed to fetch notifications', error);
    }
  },

  markAsRead: async (id: number) => {
    try {
      // تم تغيير اسم الدالة إلى markMailRead كما هو موضح في الخطأ
      await CommunicationsService.markMailRead(id);
      // تحديث الحالة محلياً بدون إعادة جلب البيانات (Optimistic Update)
      set((state) => ({
        notifications: state.notifications.map(n =>
          n.id === id ? { ...n, is_read: true } : n
        ),
        unreadCount: Math.max(0, state.unreadCount - 1),
      }));
    } catch (error) {
      console.error('Failed to mark as read', error);
    }
  },

  markAllAsRead: async () => {
    // نمر على جميع الإشعارات غير المقروءة ونحدثها (يُفضل عمل API واحد، لكن لو غير موجود ننفذها حلقة)
    const unread = get().notifications.filter(n => !n.is_read);
    for (const n of unread) {
      // تم تغيير اسم الدالة إلى markMailRead هنا أيضاً
      await CommunicationsService.markMailRead(n.id);
    }
    // تحديث الحالة
    set((state) => ({
      notifications: state.notifications.map(n => ({ ...n, is_read: true })),
      unreadCount: 0,
    }));
  },

  addNotification: (notification: NotificationResponse) => {
    set((state) => ({
      notifications: [notification, ...state.notifications],
      unreadCount: state.unreadCount + 1,
    }));
  },
}));