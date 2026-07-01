// types/tenders-auctions.ts
export type TenderStatus = 'DRAFT' | 'OPEN' | 'EVALUATING' | 'AWARDED' | 'CANCELLED';
export type BidStatus = 'SUBMITTED' | 'TECHNICAL_ACCEPTED' | 'TECHNICAL_REJECTED' | 'FINANCIAL_REVEALED' | 'WINNER' | 'LOSER';
export type AuctionStatus = 'SCHEDULED' | 'LIVE' | 'CLOSED_WITH_WINNER' | 'CLOSED_NO_WINNER' | 'CANCELLED';

export interface SovereignTender {
  id: number;
  tenant_id: number;
  entity_id: number;
  title: string;
  description: string;
  opening_date: string;
  closing_date: string;
  booklet_price_mrusdt: number;
  bid_bond_mrusdt: number;
  estimated_value_mrusdt?: number;
  settlement_type: string;
  min_sovereign_rank_required?: string;
  status: TenderStatus;
  smart_contract_address?: string;
  escrow_wallet_address?: string;
  created_by: number;
  created_at: string;
  updated_at: string;
  bids?: TenderBid[];
}

export interface TenderBid {
  id: number;
  tender_id: number;
  bidder_id: number;
  bidder_name?: string;
  technical_envelope: Record<string, any>;
  encrypted_financial_envelope: string;
  technical_score?: number;
  financial_amount_mrusdt?: number;
  status: BidStatus;
  bid_tx_hash?: string;
  created_at: string;
  updated_at: string;
}

export interface SovereignAuction {
  id: number;
  tenant_id: number;
  entity_id: number;
  title: string;
  description?: string;
  start_time: string;
  end_time: string;
  starting_price_mrusdt: number;
  minimum_increment_mrusdt: number;
  reserve_price_mrusdt?: number;
  current_highest_bid_mrusdt: number;
  current_winner_id?: number;
  asset_type: string;
  asset_id: number;
  status: AuctionStatus;
  auction_contract_address?: string;
  escrow_wallet_address?: string;
  created_by: number;
  created_at: string;
  updated_at: string;
  live_bids?: LiveBid[];
}

export interface LiveBid {
  id: number;
  auction_id: number;
  bidder_id: number;
  bidder_name?: string;
  bid_amount_mrusdt: number;
  bid_tx_hash?: string;
  created_at: string;
}

// ========== UI Types ==========
export interface TendersAuctionsStats {
  total_tenders: number;
  open_tenders: number;
  total_auctions: number;
  live_auctions: number;
  my_bids: number;
}