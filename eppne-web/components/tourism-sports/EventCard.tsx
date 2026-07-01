// components/tourism-sports/EventCard.tsx
'use client';

import { Calendar, MapPin, DollarSign } from 'lucide-react';
import { format } from 'date-fns/ar';
import type { EntertainmentEvent } from '@/types/tourism-sports';

export default function EventCard({ event }: { event: EntertainmentEvent }) {
  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all">
      <h4 className="font-medium text-foreground/80">{event.title}</h4>
      <span className="text-xs px-2 py-0.5 rounded-full border-white/10 text-muted-foreground/60">
        {event.event_type}
      </span>
      <div className="mt-2 space-y-1 text-xs text-muted-foreground/50">
        <div className="flex items-center gap-2">
          <Calendar className="w-3 h-3" />
          {format(new Date(event.start_time), 'dd/MM/yyyy HH:mm')}
        </div>
        <div className="flex items-center gap-2">
          <MapPin className="w-3 h-3" />
          مكان #{event.venue_id}
        </div>
        <div className="flex items-center gap-2">
          <DollarSign className="w-3 h-3" />
          {event.base_ticket_price_mrusdt} MR_USDT
        </div>
      </div>
    </div>
  );
}