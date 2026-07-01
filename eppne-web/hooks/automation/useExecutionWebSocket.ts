// hooks/automation/useExecutionWebSocket.ts
import { useEffect, useRef, useState, useCallback } from 'react';

interface WebSocketMessage {
  type: 'execution_update' | 'node_update' | 'execution_complete';
  execution_id: number;
  data: any;
}

export function useExecutionWebSocket(executionId: number | null) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);

  const connect = useCallback(() => {
    if (!executionId) return;

    // بناء عنوان WebSocket (نفترض أن الباك إند يدعم ws://)
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}/ws/executions/${executionId}`;
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log(`🔗 WebSocket متصل للتنفيذ ${executionId}`);
      setIsConnected(true);
      reconnectAttempt.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLastMessage(data);
      } catch (error) {
        console.error('خطأ في تحليل رسالة WebSocket', error);
      }
    };

    ws.onclose = () => {
      console.log(`🔌 WebSocket مفصول للتنفيذ ${executionId}`);
      setIsConnected(false);
      
      // إعادة الاتصال الأسي (Exponential Backoff)
      const delay = Math.min(1000 * (2 ** reconnectAttempt.current), 30000);
      setTimeout(() => {
        reconnectAttempt.current += 1;
        connect();
      }, delay);
    };

    ws.onerror = (error) => {
      console.error('خطأ في WebSocket', error);
      ws.close();
    };
  }, [executionId]);

  useEffect(() => {
    if (executionId) {
      connect();
    }

    return () => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
    };
  }, [executionId, connect]);

  return { isConnected, lastMessage };
}