// services/tourism-sports.ts
import { apiClient } from "@/lib/api-client";
import type { components } from "@/src/lib/api-types";
import { handleError } from "@/lib/error-handler";
import { generateIdempotencyKey } from "@/lib/utils";

type DestinationCreate = components['schemas']['DestinationCreate'];
type DestinationResponse = components['schemas']['DestinationResponse'];
type TourismProgramCreate = components['schemas']['TourismProgramCreate'];
type TourismProgramResponse = components['schemas']['TourismProgramResponse'];
type ProgramBookingResponse = components['schemas']['ProgramBookingResponse'];
type EventCreate = components['schemas']['EventCreate'];
type EventResponse = components['schemas']['EventResponse'];
type TicketPurchase = components['schemas']['TicketPurchase'];
type TicketResponse = components['schemas']['app__domains__tourism_sports__schemas__TicketResponse'];
type SportsOrgCreate = components['schemas']['SportsOrgCreate'];
type SportsOrgResponse = components['schemas']['SportsOrgResponse'];
type PlayerProfileCreate = components['schemas']['PlayerProfileCreate'];
type PlayerProfileResponse = components['schemas']['PlayerProfileResponse'];
type TransferBidCreate = components['schemas']['TransferBidCreate'];
type TransferBidResponse = components['schemas']['TransferBidResponse'];
type TournamentCreate = components['schemas']['TournamentCreate'];
type TournamentResponse = components['schemas']['TournamentResponse'];

export const TourismSportsService = {
  /**
   * جلب قائمة الوجهات
   * GET /tourism-sports/tourism-sports/destinations
   * تدعم X-Tenant-ID
   */
  listDestinations: async (params?: { destination_type?: string | null }, headers?: { 'X-Tenant-ID'?: number }): Promise<DestinationResponse[]> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data } = await apiClient.get<DestinationResponse[]>("/tourism-sports/tourism-sports/destinations", {
        params,
        headers: reqHeaders,
        withCredentials: true,
      });
      return data;
    } catch (error) {
      throw handleError(error, "فشل جلب الوجهات");
    }
  },

  /**
   * إنشاء وجهة جديدة
   * POST /tourism-sports/tourism-sports/destinations
   * تدعم X-Tenant-ID
   */
  createDestination: async (data: DestinationCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<DestinationResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<DestinationResponse>("/tourism-sports/tourism-sports/destinations", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الوجهة");
    }
  },

  /**
   * إنشاء برنامج سياحي جديد
   * POST /tourism-sports/tourism-sports/programs
   * تدعم X-Tenant-ID
   */
  createProgram: async (data: TourismProgramCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<TourismProgramResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<TourismProgramResponse>("/tourism-sports/tourism-sports/programs", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء البرنامج السياحي");
    }
  },

  /**
   * حجز برنامج سياحي
   * POST /tourism-sports/tourism-sports/programs/{program_id}/book
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  bookProgram: async (
    programId: number,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<ProgramBookingResponse> => {
    try {
      const id = Number(programId);
      if (isNaN(id)) throw new Error("معرف البرنامج غير صحيح");
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<ProgramBookingResponse>(
        `/tourism-sports/tourism-sports/programs/${id}/book`,
        undefined,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل حجز البرنامج السياحي");
    }
  },

  /**
   * إنشاء فعالية جديدة
   * POST /tourism-sports/tourism-sports/events
   * تدعم X-Tenant-ID
   */
  createEvent: async (data: EventCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<EventResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<EventResponse>("/tourism-sports/tourism-sports/events", data, {
        headers: reqHeaders,
        withCredentials: true,
      });
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء الفعالية");
    }
  },

  /**
   * شراء تذكرة
   * POST /tourism-sports/tourism-sports/tickets/purchase
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  buyTicket: async (
    data: TicketPurchase,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<TicketResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<TicketResponse>(
        "/tourism-sports/tourism-sports/tickets/purchase",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل شراء التذكرة");
    }
  },

  /**
   * إنشاء منظمة رياضية جديدة
   * POST /tourism-sports/tourism-sports/sports/organizations
   * تدعم X-Tenant-ID
   */
  createSportsOrg: async (data: SportsOrgCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<SportsOrgResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<SportsOrgResponse>(
        "/tourism-sports/tourism-sports/sports/organizations",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء المنظمة الرياضية");
    }
  },

  /**
   * إنشاء ملف لاعب جديد
   * POST /tourism-sports/tourism-sports/sports/players/profile
   */
  createPlayerProfile: async (data: PlayerProfileCreate): Promise<PlayerProfileResponse> => {
    try {
      const { data: result } = await apiClient.post<PlayerProfileResponse>(
        "/tourism-sports/tourism-sports/sports/players/profile",
        data,
        { withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء ملف اللاعب");
    }
  },

  /**
   * تقديم عرض انتقال لاعب
   * POST /tourism-sports/tourism-sports/sports/transfers/bid
   * تدعم Idempotency-Key و X-Tenant-ID
   */
  placeTransferBid: async (
    data: TransferBidCreate,
    headers?: { 'Idempotency-Key'?: string | null; 'X-Tenant-ID'?: number }
  ): Promise<TransferBidResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const idempotencyKey = headers?.['Idempotency-Key'] ?? generateIdempotencyKey();
      if (idempotencyKey) {
        reqHeaders['Idempotency-Key'] = idempotencyKey;
      }
      const { data: result } = await apiClient.post<TransferBidResponse>(
        "/tourism-sports/tourism-sports/sports/transfers/bid",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل تقديم عرض الانتقال");
    }
  },

  /**
   * إنشاء بطولة جديدة
   * POST /tourism-sports/tourism-sports/sports/tournaments
   * تدعم X-Tenant-ID
   */
  createTournament: async (data: TournamentCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<TournamentResponse> => {
    try {
      const reqHeaders: Record<string, string> = {};
      if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
        reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
      }
      const { data: result } = await apiClient.post<TournamentResponse>(
        "/tourism-sports/tourism-sports/sports/tournaments",
        data,
        { headers: reqHeaders, withCredentials: true }
      );
      return result;
    } catch (error) {
      throw handleError(error, "فشل إنشاء البطولة");
    }
  },
};