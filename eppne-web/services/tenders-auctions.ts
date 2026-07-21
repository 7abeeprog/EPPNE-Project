// services/tenders-auctions.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

type TenderCreate = components['schemas']['TenderCreate'];
type TenderResponse = components['schemas']['TenderResponse'];
type TenderBidCreate = components['schemas']['TenderBidCreate'];
type TenderBidResponse = components['schemas']['TenderBidResponse'];
type TenderBidEvaluate = components['schemas']['TenderBidEvaluate'];
type LiveBidCreate = components['schemas']['LiveBidCreate'];
type LiveBidResponse = components['schemas']['LiveBidResponse'];

export const TendersAuctionsService = {
  /**
   * إنشاء مناقصة جديدة
   * POST /tenders/social/tenders
   * تدعم X-Tenant-ID
   */
  createTender: async (data: TenderCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<TenderResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<TenderResponse>("/tenders/social/tenders", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المناقصة");
    }
  },

  /**
   * تقديم عرض في مناقصة
   * POST /tenders/social/bids
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  submitBid: async (
    data: TenderBidCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<TenderBidResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<TenderBidResponse>("/tenders/social/bids", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تقديم العرض");
    }
  },

  /**
   * تقييم عرض (لصاحب المناقصة)
   * POST /tenders/social/bids/{bid_id}/evaluate
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  evaluateBid: async (
    bidId: number,
    data: TenderBidEvaluate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<TenderBidResponse> => {
    try {
      const id = Number(bidId);
      if (isNaN(id)) throw new Error("معرف العرض غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<TenderBidResponse>(
        `/tenders/social/bids/${id}/evaluate`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تقييم العرض");
    }
  },

  /**
   * تقديم عرض في مزاد
   * POST /tenders/social/auctions/{auction_id}/bids
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  placeBid: async (
    auctionId: number,
    data: LiveBidCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<LiveBidResponse> => {
    try {
      const id = Number(auctionId);
      if (isNaN(id)) throw new Error("معرف المزاد غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<LiveBidResponse>(
        `/tenders/social/auctions/${id}/bids`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تقديم العرض في المزاد");
    }
  },

  /**
   * إغلاق مزاد
   * POST /tenders/social/auctions/{auction_id}/close
   * تدعم X-Tenant-ID
   */
  closeAuction: async (auctionId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<void> => {
    try {
      const id = Number(auctionId);
      if (isNaN(id)) throw new Error("معرف المزاد غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      await apiClient.post(`/tenders/social/auctions/${id}/close`, undefined, {
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل إغلاق المزاد");
    }
  },
};