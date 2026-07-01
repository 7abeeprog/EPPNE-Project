// services/tourism-sports.ts
import api from '@/lib/axios';
import type {
  TourismDestination,
  TourismProgram,
  ProgramParticipant,
  EntertainmentEvent,
  NFTTicket,
  SportsOrganization,
  PlayerProfile,
  PlayerTransfer,
  Tournament,
  SportsMatch,
  TourismSportsStats,
  DestinationType,
  ProgramTier,
  EventType,
  TicketTier,
  SportCategory,
  SportsEntityType,
  TournamentFormat,
} from '@/types/tourism-sports';

// ========== Destinations ==========
export const getDestinations = (params?: { destination_type?: DestinationType }) =>
  api.get<TourismDestination[]>('/tourism-sports/destinations', { params });

export const getDestination = (id: number) => api.get<TourismDestination>(`/tourism-sports/destinations/${id}`);

export const createDestination = (data: {
  name: string;
  destination_type: DestinationType;
  planet_body?: string;
  gps_location?: { lat: number; lng: number };
  description?: string;
}) => api.post<TourismDestination>('/tourism-sports/destinations', data);

// ========== Programs ==========
export const getPrograms = () => api.get<TourismProgram[]>('/tourism-sports/programs');

export const getProgram = (id: number) => api.get<TourismProgram>(`/tourism-sports/programs/${id}`);

export const bookProgram = (programId: number, idempotencyKey?: string) =>
  api.post<ProgramParticipant>(
    `/tourism-sports/programs/${programId}/book`,
    {},
    { headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {} }
  );

// ========== Events ==========
export const getEvents = () => api.get<EntertainmentEvent[]>('/tourism-sports/events');

export const getEvent = (id: number) => api.get<EntertainmentEvent>(`/tourism-sports/events/${id}`);

export const purchaseTicket = (
  data: { event_id: number; tier: TicketTier; require_vip_transport?: boolean },
  idempotencyKey?: string
) =>
  api.post<NFTTicket>('/tourism-sports/tickets/purchase', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

// ========== Tickets ==========
export const getMyTickets = () => api.get<NFTTicket[]>('/tourism-sports/tickets/my');

// ========== Sports Organizations ==========
export const getSportsOrganizations = (params?: { org_type?: SportsEntityType }) =>
  api.get<SportsOrganization[]>('/tourism-sports/sports/organizations', { params });

export const getSportsOrg = (id: number) => api.get<SportsOrganization>(`/tourism-sports/sports/organizations/${id}`);

export const createSportsOrg = (data: {
  name: string;
  org_type: SportsEntityType;
  main_sport?: string;
}) => api.post<SportsOrganization>('/tourism-sports/sports/organizations', data);

// ========== Players ==========
export const getPlayers = (params?: { club_id?: number; sport_category?: SportCategory }) =>
  api.get<PlayerProfile[]>('/tourism-sports/sports/players', { params });

export const getPlayer = (id: number) => api.get<PlayerProfile>(`/tourism-sports/sports/players/${id}`);

export const createPlayerProfile = (data: {
  sport_category: SportCategory;
  position_or_role?: string;
  market_value_mrusdt?: number;
}) => api.post<PlayerProfile>('/tourism-sports/sports/players/profile', data);

// ========== Transfers ==========
export const getTransfers = (params?: { status?: TransferStatus }) =>
  api.get<PlayerTransfer[]>('/tourism-sports/sports/transfers', { params });

export const placeTransferBid = (
  data: {
    player_id: number;
    from_club_id: number;
    to_club_id: number;
    facilitating_agency_id?: number;
    bid_amount_mrusdt: number;
    agency_fee_percentage?: number;
    contract_duration_months: number;
  },
  idempotencyKey?: string
) =>
  api.post<PlayerTransfer>('/tourism-sports/sports/transfers/bid', data, {
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
  });

// ========== Tournaments ==========
export const getTournaments = () => api.get<Tournament[]>('/tourism-sports/sports/tournaments');

export const getTournament = (id: number) => api.get<Tournament>(`/tourism-sports/sports/tournaments/${id}`);

export const createTournament = (data: {
  name: string;
  sport_category: SportCategory;
  format: TournamentFormat;
  prize_pool_mrusdt?: number;
  start_date: string;
  organizer_agency_id?: number;
}) => api.post<Tournament>('/tourism-sports/sports/tournaments', data);

// ========== Matches ==========
export const getMatches = (params?: { tournament_id?: number; status?: MatchStatus }) =>
  api.get<SportsMatch[]>('/tourism-sports/sports/matches', { params });

// ========== Stats ==========
export const getTourismSportsStats = () => api.get<TourismSportsStats>('/tourism-sports/stats');