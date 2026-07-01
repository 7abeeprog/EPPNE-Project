import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface Notification {
  id: string;
  title: string;
  body: string;
  data?: any;
  isRead: boolean;
  createdAt: string;
}

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (notification: Omit<Notification, "isRead" | "createdAt"> & { createdAt?: string }) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  clearAll: () => void;
  incrementUnread: () => void;
}

export const useNotificationStore = create<NotificationState>()(
  persist(
    (set) => ({
      notifications: [],
      unreadCount: 0,

      addNotification: (notification) => {
        const newNotif: Notification = {
          ...notification,
          isRead: false,
          createdAt: notification.createdAt || new Date().toISOString(),
          // 🟢 تم التحديث: استخدام المولد القياسي الآمن بدلاً من Math.random
          id: notification.id || crypto.randomUUID(), 
        };
        
        set((state) => ({
          // الاحتفاظ بآخر 100 إشعار فقط لعدم إرهاق الذاكرة المحلية (ممتاز جداً)
          notifications: [newNotif, ...state.notifications].slice(0, 100),
          unreadCount: state.unreadCount + 1,
        }));
      },

      markAsRead: (id) => {
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, isRead: true } : n
          ),
          unreadCount: state.unreadCount > 0 ? state.unreadCount - 1 : 0,
        }));
      },

      markAllAsRead: () => {
        set((state) => ({
          notifications: state.notifications.map((n) => ({ ...n, isRead: true })),
          unreadCount: 0,
        }));
      },

      clearAll: () => {
        set({ notifications: [], unreadCount: 0 });
      },

      incrementUnread: () => {
        set((state) => ({ unreadCount: state.unreadCount + 1 }));
      },
    }),
    {
      name: "notification-storage",
      partialize: (state) => ({ notifications: state.notifications, unreadCount: state.unreadCount }),
    }
  )
);