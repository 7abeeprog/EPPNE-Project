// hooks/ai-agents/useApprovalWebSocket.ts
import { useEffect, useRef, useState, useCallback } from 'react';
import { useAIAgentStore } from '@/store/aiAgentStore';
import type { ApprovalRequest } from '@/types/ai-agents';

export function useApprovalWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const { addPendingApproval, removePendingApproval } = useAIAgentStore();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);

  const connect = useCallback(() => {
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}/ws/approvals`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('🔗 WebSocket متصل للقناة البشرية (Approvals)');
      setIsConnected(true);
      reconnectAttempt.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'new_approval') {
          // 🔥 إضافة طلب موافقة جديد
          addPendingApproval(data.approval);
        } else if (data.type === 'approval_resolved') {
          // 🔥 إزالة الطلب المحسوم
          removePendingApproval(data.approval_id);
        }
      } catch (error) {
        console.error('خطأ في رسالة WebSocket', error);
      }
    };

    ws.onclose = () => {
      console.log('🔌 WebSocket مفصول للقناة البشرية');
      setIsConnected(false);
      
      // إعادة اتصال أسي
      const delay = Math.min(1000 * (2 ** reconnectAttempt.current), 30000);
      setTimeout(() => {
        reconnectAttempt.current += 1;
        connect();
      }, delay);
    };

    ws.onerror = (error) => {
      console.error('خطأ في WebSocket للقناة البشرية', error);
      ws.close();
    };
  }, [addPendingApproval, removePendingApproval]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { isConnected };
}