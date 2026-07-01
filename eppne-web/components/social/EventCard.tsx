// components/social/EventCard.tsx
'use client';

import { useAttendEvent, useUnattendEvent } from '@/hooks/social/useEvents';
import { Calendar, MapPin, Users, Loader2 } from 'lucide-react';
import { format } from 'date-fns/ar';
import { cn } from '@/lib/utils';
import type { SocialEvent } from '@/types/social';

interface EventCardProps {
  event: SocialEvent;
}

export default function EventCard({ event }: EventCardProps) {
  const attend = useAttendEvent();
  const unattend = useUnattendEvent();

  const isPast = new Date(event.end_time) < new Date();

  return (
    <div className={cn(
      "p-4 rounded-2xl bg-card/20 backdrop-blur-xl border transition-all",
      isPast ? "border-white/5 opacity-60" : "border-white/10 hover:border-primary/20"
    )}>
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">{event.title}</h4>
          <p className="text-sm text-muted-foreground/60">{event.event_type}</p>
          <div className="mt-1 space-y-1 text-xs text-muted-foreground/50">
            <div className="flex items-center gap-2">
              <Calendar className="w-3 h-3" />
              {format(new Date(event.start_time), 'dd/MM/yyyy HH:mm')} - {format(new Date(event.end_time), 'HH:mm')}
            </div>
            {event.location_details && (
              <div className="flex items-center gap-2">
                <MapPin className="w-3 h-3" />
                {event.location_details.address || 'موقع غير محدد'}
              </div>
            )}
            <div className="flex items-center gap-2">
              <Users className="w-3 h-3" />
              {event.attendee_count || 0} مشارك
            </div>
          </div>
        </div>
        {!isPast && (
          event.is_attending ? (
            <button
              onClick={() => unattend.mutate(event.id)}
              disabled={unattend.isPending}
              className="px-3 py-1.5 rounded-xl text-xs border-red-500/30 text-red-500 hover:bg-red-500/10 transition-colors"
            >
              {unattend.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : 'إلغاء الحضور'}
            </button>
          ) : (
            <button
              onClick={() => attend.mutate(event.id)}
              disabled={attend.isPending}
              className="px-3 py-1.5 rounded-xl text-xs bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30 transition-colors"
            >
              {attend.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : 'حضور'}
            </button>
          )
        )}
      </div>
    </div>
  );
}