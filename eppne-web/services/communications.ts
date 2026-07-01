// services/communications.ts
import api from '@/lib/axios';
import type { Notification, MailboxItem, MailMessage } from '@/types/communications';

export const getNotifications = (params?: { is_read?: boolean; skip?: number; limit?: number }) =>
  api.get<Notification[]>('/communications/notifications/me', { params });

export const markNotificationRead = (notificationId: number) =>
  api.post<Notification>(`/communications/notifications/${notificationId}/read`);

export const getInbox = (params?: { skip?: number; limit?: number }) =>
  api.get<MailboxItem[]>('/communications/mail/inbox', { params });

export const getSent = (params?: { skip?: number; limit?: number }) =>
  api.get<MailboxItem[]>('/communications/mail/sent', { params });

export const sendMail = (data: { recipient_id: number; subject: string; body_text: string; is_certified?: boolean }) =>
  api.post<MailMessage>('/communications/mail/send', data);

export const moveToTrash = (itemId: number) => api.post(`/communications/mail/move-to-trash/${itemId}`);
export const restoreFromTrash = (itemId: number) => api.post(`/communications/mail/restore/${itemId}`);
export const archiveMessage = (itemId: number) => api.post(`/communications/mail/archive/${itemId}`);
export const starMessage = (itemId: number) => api.post(`/communications/mail/star/${itemId}`);
export const markMailRead = (itemId: number) => api.post(`/communications/mail/mark-read/${itemId}`);