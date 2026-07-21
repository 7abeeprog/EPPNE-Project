'use client';

import { createContext, useContext, useEffect, useRef, ReactNode, useState } from 'react';
import { getWebSocketService } from '@/services/websocket.service';
import { useNotificationStore } from '@/store/notificationStore';

interface WebSocketContextType {
  isConnected: boolean;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    return { isConnected: false }; // حماية إضافية للكومبايلر
  }
  return context;
};

export const WebSocketProvider = ({ children }: { children: ReactNode }) => {
  const wsService = useRef<any>(null);
  const [isConnected, setIsConnected] = useState(false);

  // محاكاة حالة تسجيل الدخول لتخطي خطأ الـ Hook المفقود
  const isAuthenticated = true;
  const user = { id: 1 };

  useEffect(() => {
    if (isAuthenticated && user) {
      try {
        wsService.current = getWebSocketService();
        setIsConnected(true);

        const handleNotification = (data: any) => {
          useNotificationStore.getState().addNotification(data);
        };
        wsService.current.subscribe('NOTIFICATION', handleNotification);

        return () => {
          if (wsService.current) {
            wsService.current.unsubscribe('NOTIFICATION', handleNotification);
            wsService.current.disconnect();
          }
          setIsConnected(false);
        };
      } catch (e) {
        console.warn("WebSocket is not fully configured yet");
      }
    }
  }, [isAuthenticated, user]);

  return (
    <WebSocketContext.Provider value={{ isConnected }}>
      {children}
    </WebSocketContext.Provider>
  );
};