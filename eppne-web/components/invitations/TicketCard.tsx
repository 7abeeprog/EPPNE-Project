// components/invitations/TicketCard.tsx
'use client';

import { Ticket, User, UserCog, MessageSquare, AlertTriangle } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ar } from 'date-fns/locale';
import { cn } from '@/lib/utils';
import TicketStatusBadge from './TicketStatusBadge';
import type { SupportTicket } from '@/types/invitations';

const priorityColor: Record<SupportTicket['priority'], string> = {
  LOW: 'text-muted-foreground/50',
  MEDIUM: 'text-blue-500',
  HIGH: 'text-amber-500',
  URGENT: 'text-red-500',
};

export default function TicketCard({ ticket, onClick }: { ticket: SupportTicket; onClick?: () => void }) {
  return (
    <div
      onClick={onClick}
      className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10 hover:border-primary/20 transition-all cursor-pointer"
    >
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80 flex items-center gap-2">
            <Ticket className="w-4 h-4 text-primary/60" />
            {ticket.subject}
          </h4>
          <p className="mt-1 text-sm text-muted-foreground/60 line-clamp-2">{ticket.description}</p>
          <div className="flex flex-wrap gap-2 mt-1 text-xs text-muted-foreground/50">
            {ticket.user_name && (
              <span className="flex items-center gap-1">
                <User className="w-3 h-3" />
                {ticket.user_name}
              </span>
            )}
            {ticket.assigned_to_name && (
              <span className="flex items-center gap-1">
                <UserCog className="w-3 h-3" />
                {ticket.assigned_to_name}
              </span>
            )}
          </div>
        </div>
        <TicketStatusBadge status={ticket.status} />
      </div>
      <div className="flex items-center justify-between mt-3 text-xs text-muted-foreground/50">
        <span className={cn("flex items-center gap-1", priorityColor[ticket.priority])}>
          <AlertTriangle className="w-3 h-3" />
          {ticket.priority}
        </span>
        {ticket.comments && ticket.comments.length > 0 && (
          <span className="flex items-center gap-1">
            <MessageSquare className="w-3 h-3" />
            {ticket.comments.length}
          </span>
        )}
        <span>{formatDistanceToNow(new Date(ticket.created_at), { addSuffix: true, locale: ar })}</span>
      </div>
    </div>
  );
}
