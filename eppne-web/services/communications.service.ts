// services/communications.service.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";

type NotificationCreate = components['schemas']['NotificationCreate'];
type NotificationResponse = components['schemas']['NotificationResponse'];
type DeviceRegister = components['schemas']['DeviceRegister'];
type MailMessageCreate = components['schemas']['MailMessageCreate'];
type MailMessageResponse = components['schemas']['MailMessageResponse'];
type MailboxItemResponse = components['schemas']['MailboxItemResponse'];
type CommunicationTemplateCreate = components['schemas']['CommunicationTemplateCreate'];
type CommunicationTemplateResponse = components['schemas']['CommunicationTemplateResponse'];

export const CommunicationsService = {
  // ==========================================
  // 1. الإشعارات (Notifications)
  // ==========================================
  sendNotification: async (data: NotificationCreate): Promise<NotificationResponse> => {
    try {
      const { data: result } = await apiClient.post<NotificationResponse>(
        "/communications/notifications/send",
        data,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إرسال الإشعار");
    }
  },

  getMyNotifications: async (params?: {
    is_read?: boolean | null;
    skip?: number;
    limit?: number;
  }): Promise<NotificationResponse[]> => {
    try {
      const { data } = await apiClient.get<NotificationResponse[]>("/communications/notifications/me", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الإشعارات");
    }
  },

  markNotificationRead: async (notificationId: number): Promise<NotificationResponse> => {
    try {
      const id = Number(notificationId);
      if (isNaN(id)) throw new Error("معرف الإشعار غير صحيح");
      const { data: result } = await apiClient.post<NotificationResponse>(
        `/communications/notifications/${id}/read`,
        undefined,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث حالة الإشعار");
    }
  },

  // ==========================================
  // 2. الأجهزة (Devices)
  // ==========================================
  registerDevice: async (data: DeviceRegister): Promise<Record<string, any>> => {
    try {
      const { data: result } = await apiClient.post<Record<string, any>>(
        "/communications/devices/register",
        data,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تسجيل الجهاز");
    }
  },

  // ==========================================
  // 3. البريد (Mail)
  // ==========================================
  sendMail: async (data: MailMessageCreate): Promise<MailMessageResponse> => {
    try {
      const { data: result } = await apiClient.post<MailMessageResponse>(
        "/communications/mail/send",
        data,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إرسال البريد");
    }
  },

  getInbox: async (params?: { skip?: number; limit?: number }): Promise<MailboxItemResponse[]> => {
    try {
      const { data } = await apiClient.get<MailboxItemResponse[]>("/communications/mail/inbox", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب صندوق الوارد");
    }
  },

  getSent: async (params?: { skip?: number; limit?: number }): Promise<MailboxItemResponse[]> => {
    try {
      const { data } = await apiClient.get<MailboxItemResponse[]>("/communications/mail/sent", {
        params,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب البريد المرسل");
    }
  },

  moveToTrash: async (itemId: number): Promise<void> => {
    try {
      const id = Number(itemId);
      if (isNaN(id)) throw new Error("معرف البريد غير صحيح");
      await apiClient.post(`/communications/mail/move-to-trash/${id}`, undefined, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل نقل البريد إلى المحذوفات");
    }
  },

  restoreFromTrash: async (itemId: number): Promise<void> => {
    try {
      const id = Number(itemId);
      if (isNaN(id)) throw new Error("معرف البريد غير صحيح");
      await apiClient.post(`/communications/mail/restore/${id}`, undefined, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل استعادة البريد");
    }
  },

  archiveMessage: async (itemId: number): Promise<void> => {
    try {
      const id = Number(itemId);
      if (isNaN(id)) throw new Error("معرف البريد غير صحيح");
      await apiClient.post(`/communications/mail/archive/${id}`, undefined, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل أرشفة البريد");
    }
  },

  starMessage: async (itemId: number): Promise<void> => {
    try {
      const id = Number(itemId);
      if (isNaN(id)) throw new Error("معرف البريد غير صحيح");
      await apiClient.post(`/communications/mail/star/${id}`, undefined, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل تمييز البريد");
    }
  },

  markMailRead: async (itemId: number): Promise<void> => {
    try {
      const id = Number(itemId);
      if (isNaN(id)) throw new Error("معرف البريد غير صحيح");
      await apiClient.post(`/communications/mail/mark-read/${id}`, undefined, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل تحديث حالة البريد");
    }
  },

  deletePermanently: async (itemId: number): Promise<void> => {
    try {
      const id = Number(itemId);
      if (isNaN(id)) throw new Error("معرف البريد غير صحيح");
      await apiClient.delete(`/communications/mail/permanent/${id}`, {
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل حذف البريد نهائياً");
    }
  },

  // ==========================================
  // 4. قوالب التواصل (Templates)
  // ==========================================
  listTemplates: async (headers?: { 'X-Tenant-ID'?: number }): Promise<CommunicationTemplateResponse[]> => {
    try {
      const { data } = await apiClient.get<CommunicationTemplateResponse[]>("/communications/templates", {
        headers,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب قوالب التواصل");
    }
  },

  createTemplate: async (
    data: CommunicationTemplateCreate,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<CommunicationTemplateResponse> => {
    try {
      const { data: result } = await apiClient.post<CommunicationTemplateResponse>(
        "/communications/templates",
        data,
        { headers, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء قالب التواصل");
    }
  },
};