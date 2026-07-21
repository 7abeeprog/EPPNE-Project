// services/websocket.service.ts
import { useNotificationStore } from '@/store/notificationStore';
import { useHealthStore } from '@/store/healthStore';
import { useAgentStore } from '@/store/agentStore';
import { useDigitalTwinStore } from '@/store/digitalTwinStore';

type WebSocketMessage = {
  type: 'notification' | 'emergency_update' | 'agent_action' | 'twin_interaction';
  payload: any;
};

export class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout = 3000;
  private isConnected = false;
  private isConnecting = false; // منع التكرار
  private token: string | null = null;

  constructor(private url: string) { }

  // ✅ دالة جديدة لتعيين التوكن والاتصال بعد تسجيل الدخول
  setToken(token: string) {
    this.token = token;
    // إذا كان هناك توكن ولم يكن متصلاً، نبدأ الاتصال
    if (token && !this.isConnected && !this.isConnecting) {
      this.connect();
    }
  }

  connect() {
    // ❌ لا نسمح بالاتصال بدون توكن
    if (!this.token) {
      console.warn('WebSocket: No token provided, skipping connection.');
      return;
    }

    if (this.ws && this.isConnected) return;
    if (this.isConnecting) return; // منع تكرار المحاولات

    this.isConnecting = true;

    try {
      // إضافة التوكن في الـ URL (أو حسب طريقة المصادقة في الخادم)
      const wsUrl = `${this.url}?token=${encodeURIComponent(this.token)}`;
      this.ws = new WebSocket(wsUrl);
      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
      this.ws.onerror = this.handleError.bind(this);
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      this.isConnecting = false;
      this.reconnect();
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
    this.isConnecting = false;
  }

  private handleOpen() {
    console.log('WebSocket connected');
    this.isConnected = true;
    this.isConnecting = false;
    this.reconnectAttempts = 0;
    // إرسال رسالة ترحيب (مصادقة إضافية)
    this.send({
      type: 'auth',
      payload: { token: this.token },
    });
  }

  private handleMessage(event: MessageEvent) {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      this.processMessage(message);
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  private handleClose() {
    console.log('WebSocket disconnected');
    this.isConnected = false;
    this.isConnecting = false;
    this.reconnect();
  }

  private handleError(error: Event) {
    console.error('WebSocket error:', error);
    // لا نعيد المحاولة إذا كان الخطأ 403 (مرفوض) لأن التوكن غير صالح
    // يمكننا تجاهل هذا النوع من الأخطاء أو معالجته بشكل خاص
  }

  private reconnect() {
    // لا نعيد المحاولة بدون توكن
    if (!this.token) return;

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnect attempts reached');
      return;
    }
    this.reconnectAttempts++;
    setTimeout(() => {
      console.log(`Reconnecting... (attempt ${this.reconnectAttempts})`);
      this.connect();
    }, this.reconnectTimeout);
  }

  private send(data: any) {
    if (this.ws && this.isConnected) {
      this.ws.send(JSON.stringify(data));
    }
  }

  private processMessage(message: WebSocketMessage) {
    switch (message.type) {
      case 'notification':
        const notificationStore = useNotificationStore.getState();
        notificationStore.addNotification(message.payload);
        break;

      case 'emergency_update':
        const healthStore = useHealthStore.getState();
        //healthStore.fetchEmergencyStatus(message.payload.dispatch_id);
        break;

      case 'agent_action':
        const agentStore = useAgentStore.getState();
        agentStore.fetchPendingApprovals();
        break;

      case 'twin_interaction':
        const twinStore = useDigitalTwinStore.getState();
        twinStore.fetchConfig();
        twinStore.fetchMilestones();
        break;

      default:
        console.warn('Unknown WebSocket message type:', message.type);
    }
  }
}

// إنشاء instance واحد ليتم استخدامه في جميع أنحاء التطبيق
let wsService: WebSocketService | null = null;

export const getWebSocketService = (): WebSocketService => {
  if (!wsService) {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';
    wsService = new WebSocketService(wsUrl);
  }
  return wsService;
};