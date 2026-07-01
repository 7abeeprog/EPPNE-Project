// components/communications/NotificationList.tsx
'use client';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getNotifications, markNotificationRead } from '@/services/communications';
import { useNotificationStore } from '@/store/notificationStore';
import { formatDistanceToNow } from 'date-fns/ar';
import { cn } from '@/lib/utils';
import { Loader2, CheckCircle2, Circle } from 'lucide-react';

const priorityColors = { LOW: 'border-blue-500/30', NORMAL: 'border-white/10', HIGH: 'border-amber-500/50 shadow-amber-500/10', CRITICAL: 'border-red-500 shadow-[0_0_30px_rgba(239,68,68,0.3)]' };

export default function NotificationList({ onItemClick }: { onItemClick?: () => void }) {
  const queryClient = useQueryClient();
  const { unreadCount, setUnreadCount, decrementUnread } = useNotificationStore();
  const { data, isLoading } = useQuery({ queryKey: ['notifications', 'me'], queryFn: () => getNotifications({ limit: 50 }).then(r => r.data), staleTime: 2 * 60 * 1000, gcTime: 5 * 60 * 1000 });
  const unread = data?.filter(n => !n.is_read).length || 0;
  if (unread !== unreadCount) setUnreadCount(unread);
  const { mutate: markRead } = useMutation({ mutationFn: markNotificationRead, onSuccess: (_, id) => { queryClient.invalidateQueries({ queryKey: ['notifications'] }); decrementUnread(); } });
  if (isLoading) return <div className="flex justify-center p-6"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;
  if (!data?.length) return <div className="text-center text-muted-foreground p-6 text-sm">📭 لا توجد إشعارات</div>;
  return <div className="space-y-1">{data.map((n) => <div key={n.id} onClick={() => { if (!n.is_read) markRead(n.id); onItemClick?.(); }} className={cn("relative p-3 rounded-xl cursor-pointer transition-all duration-200 border-l-4", priorityColors[n.priority], n.is_read ? "bg-white/5 hover:bg-white/10" : "bg-primary/5 hover:bg-primary/10 border-primary/30")}><div className="flex items-start gap-3">{n.is_read ? <CheckCircle2 className="w-4 h-4 mt-1 text-muted-foreground/50" /> : <Circle className="w-4 h-4 mt-1 text-primary fill-primary/30 animate-pulse" />}<div className="flex-1 min-w-0"><div className="flex items-center justify-between gap-2"><p className={cn("text-sm font-medium truncate", n.is_read ? "text-foreground/70" : "text-foreground")}>{n.title}</p><span className="text-[10px] text-muted-foreground/50 whitespace-nowrap">{formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}</span></div><p className="text-xs text-muted-foreground/70 line-clamp-2 mt-0.5">{n.body}</p></div></div></div>)}</div>;
}