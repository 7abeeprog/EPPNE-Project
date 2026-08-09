// hooks/communications/useWebSocket.ts
import { useEffect, useRef } from 'react';
import { useNotificationStore } from '@/store/notificationStore';
import { useAuth } from '@/hooks/identity/useAuth';

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'wss://api.eppne.com';

export const useWebSocket = () => {
  const { token } = useAuth();
  const { setWsConnected, incrementUnread } = useNotificationStore();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);

  useEffect(() => {
    if (!token) return;
    const connect = () => {
      const ws = new WebSocket(`${WS_BASE}/communications/ws?token=${token}`);
      wsRef.current = ws;
      ws.onopen = () => { setWsConnected(true); reconnectAttempt.current = 0; };
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'notification') incrementUnread();
        } catch (e) { console.error('WebSocket error', e); }
      };
      ws.onclose = () => {
        setWsConnected(false);
        const delay = Math.min(1000 * (2 ** reconnectAttempt.current), 30000);
        setTimeout(() => { reconnectAttempt.current += 1; connect(); }, delay);
      };
    };
    connect();
    return () => { if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.close(); };
  }, [token]);
};