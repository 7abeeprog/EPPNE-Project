// components/websocket-provider.tsx
'use client';

import { createContext, useContext, useEffect, useRef, ReactNode } from 'react';
import { getWebSocketService } from '@/services/websocket.service';
import { useAuth } from '@/hooks/auth/useAuth';
import { useNotificationStore } from '@/store/notificationStore';

interface WebSocketContextType {
  isConnected: boolean;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

export const WebSocketProvider = ({ children }: { children: ReactNode }) => {
  const { user, isAuthenticated } = useAuth();
  const wsService = useRef<any>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (isAuthenticated && user) {
      // تهيئة WebSocket
      wsService.current = getWebSocketService();
      setIsConnected(true);

      // الاشتراك في الإشعارات الفورية
      const handleNotification = (data: any) => {
        useNotificationStore.getState().addNotification(data);
      };
      wsService.current.subscribe('NOTIFICATION', handleNotification);

      return () => {
        wsService.current.unsubscribe('NOTIFICATION', handleNotification);
        wsService.current.disconnect();
        setIsConnected(false);
      };
    } else if (wsService.current) {
      wsService.current.disconnect();
      wsService.current = null;
      setIsConnected(false);
    }
  }, [isAuthenticated, user]);

  return (
    <WebSocketContext.Provider value={{ isConnected }}>
      {children}
    </WebSocketContext.Provider>
  );
};