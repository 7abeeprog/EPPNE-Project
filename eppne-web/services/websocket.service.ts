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

  constructor(private url: string) {}

  connect() {
    if (this.ws && this.isConnected) return;

    try {
      this.ws = new WebSocket(this.url);
      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
      this.ws.onerror = this.handleError.bind(this);
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      this.reconnect();
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
  }

  private handleOpen() {
    console.log('WebSocket connected');
    this.isConnected = true;
    this.reconnectAttempts = 0;
    // إرسال رسالة ترحيب (مصادقة)
    this.send({
      type: 'auth',
      payload: { token: localStorage.getItem('access_token') },
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
    this.reconnect();
  }

  private handleError(error: Event) {
    console.error('WebSocket error:', error);
  }

  private reconnect() {
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
        healthStore.fetchEmergencyStatus(message.payload.dispatch_id);
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