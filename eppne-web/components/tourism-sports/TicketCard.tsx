// components/tourism-sports/TicketCard.tsx
'use client';

import { QRCodeSVG } from 'qrcode.react';
import { format } from 'date-fns/ar';
import type { NFTTicket } from '@/types/tourism-sports';

export default function TicketCard({ ticket }: { ticket: NFTTicket }) {
  return (
    <div className="p-4 rounded-2xl bg-card/20 backdrop-blur-xl border border-white/10">
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-medium text-foreground/80">تذكرة #{ticket.id}</h4>
          <p className="text-xs text-muted-foreground/50">حدث #{ticket.event_id}</p>
          <span className="text-xs px-2 py-0.5 rounded-full border-primary/30 text-primary bg-primary/5">
            {ticket.tier}
          </span>
          <p className="text-xs text-muted-foreground/40 mt-1">
            {ticket.purchase_price_mrusdt} MR_USDT
          </p>
          <p className="text-xs text-muted-foreground/30 font-mono">
            NFT: {ticket.nft_token_id.slice(0, 16)}...
          </p>
        </div>
        <div className="bg-white p-2 rounded-lg">
          <QRCodeSVG value={ticket.qr_code_data} size={80} />
        </div>
      </div>
    </div>
  );
}