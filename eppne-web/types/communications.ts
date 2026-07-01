// types/communications.ts
export type NotificationPriority = 'LOW' | 'NORMAL' | 'HIGH' | 'CRITICAL';

export interface Notification {
  id: number;
  title: string;
  body: string;
  data: Record<string, any>;
  priority: NotificationPriority;
  is_read: boolean;
  created_at: string;
}

export interface MailMessage {
  id: number;
  sender_id: number;
  recipient_id: number;
  subject: string;
  body_text?: string;
  body_html?: string;
  is_certified: boolean;
  created_at: string;
}

export interface MailboxItem {
  id: number;
  message_id: number;
  folder: 'INBOX' | 'SENT' | 'DRAFTS' | 'TRASH' | 'ARCHIVE';
  is_read: boolean;
  is_starred: boolean;
  message: MailMessage;
}