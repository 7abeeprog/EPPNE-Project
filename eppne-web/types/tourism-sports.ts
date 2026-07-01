// types/tourism-sports.ts
export type DestinationType = 'LOCAL' | 'INTERNATIONAL' | 'CRUISE_PORT' | 'SPACE_STATION';
export type AccommodationType = 'HOTEL' | 'APARTMENT' | 'HOSTEL' | 'CRUISE_CABIN' | 'SPACE_POD' | 'RESORT';
export type ProgramTier = 'BUDGET' | 'STANDARD' | 'LUXURY' | 'VIP_INTERSTELLAR' | 'SCHOOL_TRIP';
export type ParticipantStatus = 'ENROLLED' | 'IN_TRAINING' | 'BOARDED' | 'COMPLETED' | 'DROPPED';
export type EventType = 'CONCERT' | 'SPORTS_MATCH' | 'BUSINESS_SUMMIT' | 'METAVERSE_EVENT';
export type TicketTier = 'GENERAL' | 'VIP' | 'VVIP_TRANSIT';
export type SportCategory = 'PHYSICAL' | 'MENTAL' | 'E_SPORTS' | 'HYBRID';
export type SportsEntityType = 'CLUB' | 'ACADEMY' | 'MARKETING_AGENCY';
export type TournamentFormat = 'LEAGUE' | 'KNOCKOUT' | 'GROUP_AND_KNOCKOUT';
export type MatchStatus = 'SCHEDULED' | 'LIVE' | 'FINISHED' | 'POSTPONED' | 'CANCELLED';
export type TransferStatus = 'BID_PLACED' | 'NEGOTIATING' | 'MEDICAL_REVIEW' | 'TERMS_AGREED' | 'COMPLETED' | 'CANCELLED';

export interface TourismDestination {
  id: number;
  tenant_id: number;
  name: string;
  destination_type: DestinationType;
  planet_body: string;
  gps_location?: { lat: number; lng: number };
  description?: string;
  is_active: boolean;
  created_at: string;
}

export interface TourismProgram {
  id: number;
  tenant_id: number;
  title: string;
  description?: string;
  program_tier: ProgramTier;
  required_certificate_id?: number;
  base_price_mrusdt: number;
  max_capacity: number;
  start_date: string;
  end_date: string;
  status: string;
  nft_collection_address?: string;
  escrow_contract_address?: string;
  created_at: string;
}

export interface ProgramParticipant {
  id: number;
  program_id: number;
  user_id: number;
  health_clearance: boolean;
  current_status: ParticipantStatus;
  ticket_nft_id?: string;
  payment_tx_hash?: string;
  created_at: string;
}

export interface EntertainmentEvent {
  id: number;
  tenant_id: number;
  venue_id: number;
  title: string;
  event_type: EventType;
  start_time: string;
  end_time: string;
  base_ticket_price_mrusdt: number;
  created_at: string;
}

export interface NFTTicket {
  id: number;
  tenant_id: number;
  event_id: number;
  owner_id: number;
  tier: TicketTier;
  assigned_vehicle_id?: number;
  nft_token_id: string;
  qr_code_data: string;
  purchase_price_mrusdt: number;
  created_at: string;
}

export interface SportsOrganization {
  id: number;
  tenant_id: number;
  entity_id?: number;
  owner_id: number;
  name: string;
  org_type: SportsEntityType;
  main_sport?: string;
  treasury_wallet_address?: string;
  created_at: string;
}

export interface PlayerProfile {
  id: number;
  tenant_id: number;
  user_id: number;
  club_id?: number;
  agency_id?: number;
  agent_user_id?: number;
  medical_profile_id?: number;
  sport_category: SportCategory;
  position_or_role?: string;
  performance_stats: Record<string, any>;
  market_value_mrusdt: number;
  is_insured: boolean;
  created_at: string;
}

export interface PlayerTransfer {
  id: number;
  tenant_id: number;
  player_id: number;
  from_club_id: number;
  to_club_id: number;
  facilitating_agency_id?: number;
  agent_user_id?: number;
  bid_amount_mrusdt: number;
  agency_fee_percentage: number;
  contract_duration_months: number;
  medical_ai_flag: boolean;
  medical_report_summary?: string;
  status: TransferStatus;
  smart_contract_tx?: string;
  created_at: string;
}

export interface Tournament {
  id: number;
  tenant_id: number;
  organizer_agency_id?: number;
  name: string;
  sport_category: SportCategory;
  format: TournamentFormat;
  prize_pool_mrusdt: number;
  start_date: string;
  is_active: boolean;
  standings_json: Record<string, any>;
  created_at: string;
}

export interface SportsMatch {
  id: number;
  tenant_id: number;
  tournament_id?: number;
  home_team_id: number;
  away_team_id: number;
  scheduled_time: string;
  status: MatchStatus;
  home_score: number;
  away_score: number;
  created_at: string;
}

// ========== UI Types ==========
export interface TourismSportsStats {
  total_destinations: number;
  total_programs: number;
  total_events: number;
  total_tickets_sold: number;
  total_players: number;
  active_transfers: number;
}