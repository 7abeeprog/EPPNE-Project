// components/communications/NotificationBell.tsx
'use client';
import { useState } from 'react';
import { Bell } from 'lucide-react';
import { useNotificationStore } from '@/store/notificationStore';
import { useWebSocket } from '@/hooks/communications/useWebSocket';
import NotificationList from './NotificationList';
import { cn } from '@/lib/utils';

export default function NotificationBell() {
  const { unreadCount, isWsConnected } = useNotificationStore();
  const [isOpen, setIsOpen] = useState(false);
  useWebSocket();

  return (
    <div className="relative">
      <button onClick={() => setIsOpen(!isOpen)} className={cn(
        "relative p-2 rounded-xl transition-all duration-300 bg-card/30 backdrop-blur-xl border border-white/10",
        "hover:bg-card/50 hover:border-primary/30 shadow-[0_0_30px_-10px_rgba(var(--primary-rgb),0.2)]",
        isWsConnected ? "shadow-primary/20" : "shadow-red-500/10"
      )}>
        <Bell className="w-5 h-5 text-foreground/80" />
        {unreadCount > 0 && <span className="absolute -top-1 -right-1 flex items-center justify-center w-5 h-5 text-[10px] font-bold text-white rounded-full bg-gradient-to-br from-primary to-primary/80 shadow-[0_0_20px_rgba(var(--primary-rgb),0.6)] animate-pulse">{unreadCount > 9 ? '9+' : unreadCount}</span>}
        <span className={cn("absolute -bottom-1 -right-1 w-2.5 h-2.5 rounded-full border-2 border-background", isWsConnected ? "bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.8)]" : "bg-red-500")} />
      </button>
      {isOpen && <div className="absolute left-0 mt-2 w-[380px] max-h-[500px] overflow-y-auto rounded-2xl bg-card/60 backdrop-blur-3xl border border-white/15 shadow-[0_20px_80px_-20px_rgba(0,0,0,0.6)] p-2 z-50"><NotificationList onItemClick={() => setIsOpen(false)} /></div>}
    </div>
  );
}