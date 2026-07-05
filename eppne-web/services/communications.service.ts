// services/communications.service.ts
import apiClient from '@/lib/api-client';

// تأكد من تطابق الـ Interface مع الـ Schema في الـ OpenAPI (NotificationResponse)
export interface NotificationResponse {
  id: number;
  user_id: number;
  title: string;
  body: string;
  data: Record<string, any>;
  priority: 'LOW' | 'NORMAL' | 'HIGH' | 'CRITICAL';
  is_read: boolean;
  created_at: string;
}

export const communicationsService = {
  // جلب الإشعارات (مع Pagination)
  getMyNotifications: (params?: { is_read?: boolean; skip?: number; limit?: number }) =>
    apiClient.get<NotificationResponse[]>('/api/communications/notifications/me', { params }),

  // تحديث حالة الإشعار كمقروء
  markAsRead: (notificationId: number) =>
    apiClient.post<NotificationResponse>(`/api/communications/notifications/${notificationId}/read`),

  // إنشاء إشعار جديد (يُستخدم داخلياً من قبل المشرفين أو الـ Webhooks)
  sendNotification: (data: { user_id: number; title: string; body: string; data?: object }) =>
    apiClient.post('/api/communications/notifications/send', data),
};