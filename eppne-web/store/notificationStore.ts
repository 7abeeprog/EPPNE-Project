// store/notificationStore.ts
import { create } from 'zustand';

interface NotificationState {
  unreadCount: number;
  isWsConnected: boolean;
  setUnreadCount: (count: number) => void;
  incrementUnread: () => void;
  decrementUnread: () => void;
  setWsConnected: (status: boolean) => void;
}

export const useNotificationStore = create<NotificationState>((set) => ({
  unreadCount: 0,
  isWsConnected: false,
  setUnreadCount: (count) => set({ unreadCount: count }),
  incrementUnread: () => set((state) => ({ unreadCount: state.unreadCount + 1 })),
  decrementUnread: () => set((state) => ({ unreadCount: Math.max(0, state.unreadCount - 1) })),
  setWsConnected: (status) => set({ isWsConnected: status }),
}));