// app/(dashboard)/tourism-sports/tickets/page.tsx
'use client';

import { useMyTickets } from '@/hooks/tourism-sports/useMyTickets';
import TicketCard from '@/components/tourism-sports/TicketCard';
import { Loader2 } from 'lucide-react';

export default function MyTicketsPage() {
  const { data: tickets, isLoading } = useMyTickets();

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-foreground/90">🎟️ تذاكري الرقمية (NFT)</h1>
      {tickets?.length === 0 ? (
        <p className="text-muted-foreground/60 text-center py-12">لا توجد تذاكر حتى الآن</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {tickets?.map((ticket) => (
            <TicketCard key={ticket.id} ticket={ticket} />
          ))}
        </div>
      )}
    </div>
  );
}