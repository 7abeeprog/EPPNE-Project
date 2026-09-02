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
   * POST /tenders-auctions/tenders
   * تدعم X-Tenant-ID
   */
  createTender: async (data: TenderCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<TenderResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<TenderResponse>("/tenders-auctions/tenders", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المناقصة");
    }
  },

  /**
   * جلب قائمة المناقصات
   * GET /tenders-auctions/tenders
   * تدعم X-Tenant-ID
   */
  listTenders: async (
    params?: { status_filter?: string | null; project_id?: number | null; skip?: number; limit?: number },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<TenderResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<TenderResponse[]>("/tenders-auctions/tenders", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المناقصات");
    }
  },

  /**
   * جلب مناقصة واحدة
   * GET /tenders-auctions/tenders/{tender_id}
   * تدعم X-Tenant-ID
   */
  getTender: async (tenderId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<TenderResponse> => {
    try {
      const id = Number(tenderId);
      if (isNaN(id)) throw new Error("معرف المناقصة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<TenderResponse>(`/tenders-auctions/tenders/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المناقصة");
    }
  },

  /**
   * تحديث مناقصة
   * PATCH /tenders-auctions/tenders/{tender_id}
   * تدعم X-Tenant-ID
   */
  updateTender: async (
    tenderId: number,
    data: Partial<TenderCreate>,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<TenderResponse> => {
    try {
      const id = Number(tenderId);
      if (isNaN(id)) throw new Error("معرف المناقصة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.patch<TenderResponse>(`/tenders-auctions/tenders/${id}`, data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل تحديث المناقصة");
    }
  },

  /**
   * فتح مناقصة (نشرها)
   * POST /tenders-auctions/tenders/{tender_id}/open
   * تدعم X-Tenant-ID
   */
  openTender: async (tenderId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<TenderResponse> => {
    try {
      const id = Number(tenderId);
      if (isNaN(id)) throw new Error("معرف المناقصة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<TenderResponse>(
        `/tenders-auctions/tenders/${id}/open`,
        undefined,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل فتح المناقصة");
    }
  },

  /**
   * جلب عروض مناقصة معينة
   * GET /tenders-auctions/tenders/{tender_id}/bids
   * تدعم X-Tenant-ID
   */
  getTenderBids: async (
    tenderId: number,
    params?: { status_filter?: string | null },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<TenderBidResponse[]> => {
    try {
      const id = Number(tenderId);
      if (isNaN(id)) throw new Error("معرف المناقصة غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<TenderBidResponse[]>(`/tenders-auctions/tenders/${id}/bids`, {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب عروض المناقصة");
    }
  },

  /**
   * تقديم عرض في مناقصة
   * POST /tenders-auctions/bids
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
      const { data: result } = await apiClient.post<TenderBidResponse>("/tenders-auctions/bids", data, {
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
   * POST /tenders-auctions/bids/{bid_id}/evaluate
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
        `/tenders-auctions/bids/${id}/evaluate`,
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تقييم العرض");
    }
  },

  /**
   * جلب قائمة المزادات
   * GET /tenders-auctions/auctions
   * تدعم X-Tenant-ID
   */
  listAuctions: async (
    params?: { status_filter?: string | null; asset_type?: string | null; skip?: number; limit?: number },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<AuctionResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<AuctionResponse[]>("/tenders-auctions/auctions", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المزادات");
    }
  },

  /**
   * جلب مزاد واحد
   * GET /tenders-auctions/auctions/{auction_id}
   * تدعم X-Tenant-ID
   */
  getAuction: async (auctionId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<AuctionResponse> => {
    try {
      const id = Number(auctionId);
      if (isNaN(id)) throw new Error("معرف المزاد غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<AuctionResponse>(`/tenders-auctions/auctions/${id}`, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب المزاد");
    }
  },

  /**
   * بدء مزاد
   * POST /tenders-auctions/auctions/{auction_id}/start
   * تدعم X-Tenant-ID
   */
  startAuction: async (auctionId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<AuctionResponse> => {
    try {
      const id = Number(auctionId);
      if (isNaN(id)) throw new Error("معرف المزاد غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<AuctionResponse>(
        `/tenders-auctions/auctions/${id}/start`,
        undefined,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل بدء المزاد");
    }
  },

  /**
   * جلب عروض مزاد حي
   * GET /tenders-auctions/auctions/{auction_id}/bids
   * تدعم X-Tenant-ID
   */
  getAuctionBids: async (
    auctionId: number,
    limit?: number,
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<LiveBidResponse[]> => {
    try {
      const id = Number(auctionId);
      if (isNaN(id)) throw new Error("معرف المزاد غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<LiveBidResponse[]>(`/tenders-auctions/auctions/${id}/bids`, {
        params: { limit },
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب عروض المزاد");
    }
  },

  /**
   * إنشاء مزاد جديد
   * POST /tenders-auctions/auctions
   * تدعم X-Tenant-ID
   *
   * ملاحظة: النوع مكتوب يدويًا (بدل الاعتماد على `components['schemas']['AuctionCreate']`)
   * لأن الاسم متصادم مع schema مختلف تمامًا (تصادم أسماء عبر دومينات) في
   * api-types.ts المولَّد حاليًا — يحتاج قرار/إعادة توليد لاحقًا.
   */
  createAuction: async (
    data: {
      title: string;
      description?: string | null;
      asset_type: string;
      asset_id?: number | null;
      start_price_mrusdt: number | string;
      min_increment_mrusdt?: number | string;
      start_time: string;
      end_time: string;
    },
    headers?: { 'X-Tenant-ID'?: number }
  ): Promise<AuctionResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<AuctionResponse>("/tenders-auctions/auctions", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المزاد");
    }
  },

  /**
   * تقديم عرض في مزاد
   * POST /tenders-auctions/auctions/{auction_id}/bids
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
        `/tenders-auctions/auctions/${id}/bids`,
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
   * POST /tenders-auctions/auctions/{auction_id}/close
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
      await apiClient.post(`/tenders-auctions/auctions/${id}/close`, undefined, {
        headers: reqHeaders,
        withCredentials: true,
      });
    } catch (error) {
      throw handleError(error, "فشل إغلاق المزاد");
    }
  },
};