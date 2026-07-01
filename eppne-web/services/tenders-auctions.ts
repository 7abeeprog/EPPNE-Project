// services/tenders-auctions.ts
import api from '@/lib/axios';
import type {
  SovereignTender,
  TenderBid,
  SovereignAuction,
  LiveBid,
  TenderStatus,
  BidStatus,
  AuctionStatus,
} from '@/types/tenders-auctions';

// ========== Tenders ==========
export const getTenders = (params?: { status?: TenderStatus; entity_id?: number; skip?: number; limit?: number }) =>
  api.get<SovereignTender[]>('/tenders-auctions/tenders', { params });

export const getTender = (id: number) => api.get<SovereignTender>(`/tenders-auctions/tenders/${id}`);

export const createTender = (data: {
  entity_id: number;
  title: string;
  description: string;
  opening_date: string;
  closing_date: string;
  booklet_price_mrusdt?: number;
  bid_bond_mrusdt: number;
  estimated_value_mrusdt?: number;
  settlement_type?: string;
  min_sovereign_rank_required?: string;
}) => api.post<SovereignTender>('/tenders-auctions/tenders', data);

export const updateTender = (id: number, data: Partial<{
  title: string;
  description: string;
  closing_date: string;
  status: TenderStatus;
  estimated_value_mrusdt: number;
}>) => api.put<SovereignTender>(`/tenders-auctions/tenders/${id}`, data);

export const openTender = (id: number) => api.post(`/tenders-auctions/tenders/${id}/open`);

// ========== Bids ==========
export const submitBid = (
  data: {
    tender_id: number;
    technical_envelope: Record<string, any>;
    encrypted_financial_envelope: string;
  },
  idempotencyKey?: string
) =>
  api.post<TenderBid>('/tenders-auctions/bids', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

export const getTenderBids = (tenderId: number) =>
  api.get<TenderBid[]>(`/tenders-auctions/tenders/${tenderId}/bids`);

export const evaluateBid = (
  bidId: number,
  data: { technical_score: number },
  idempotencyKey?: string
) =>
  api.post<TenderBid>(`/tenders-auctions/bids/${bidId}/evaluate`, data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

// ========== Auctions ==========
export const getAuctions = (params?: { status?: AuctionStatus; asset_type?: string; skip?: number; limit?: number }) =>
  api.get<SovereignAuction[]>('/tenders-auctions/auctions', { params });

export const getAuction = (id: number) => api.get<SovereignAuction>(`/tenders-auctions/auctions/${id}`);

export const createAuction = (data: {
  entity_id: number;
  title: string;
  description?: string;
  start_time: string;
  end_time: string;
  starting_price_mrusdt: number;
  minimum_increment_mrusdt: number;
  reserve_price_mrusdt?: number;
  asset_type: string;
  asset_id: number;
}) => api.post<SovereignAuction>('/tenders-auctions/auctions', data);

export const startAuction = (id: number) => api.post(`/tenders-auctions/auctions/${id}/start`);

export const closeAuction = (id: number) => api.post(`/tenders-auctions/auctions/${id}/close`);

export const getAuctionBids = (auctionId: number, params?: { limit?: number }) =>
  api.get<LiveBid[]>(`/tenders-auctions/auctions/${auctionId}/bids`, { params });

export const placeBid = (
  auctionId: number,
  data: { bid_amount_mrusdt: number },
  idempotencyKey?: string
) =>
  api.post<LiveBid>(`/tenders-auctions/auctions/${auctionId}/bids`, data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

// ========== My Bids ==========
export const getMyBids = () => api.get<TenderBid[]>('/tenders-auctions/my-bids');