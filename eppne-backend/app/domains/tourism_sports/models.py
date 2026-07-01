# app/domains/tourism_sports/models.py (الإصدار النهائي المتكامل)
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, JSON, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum

# ========== الأنواع المساعدة ==========
class DestinationType(str, enum.Enum):
    LOCAL = "LOCAL"
    INTERNATIONAL = "INTERNATIONAL"
    CRUISE_PORT = "CRUISE_PORT"
    SPACE_STATION = "SPACE_STATION"

class AccommodationType(str, enum.Enum):
    HOTEL = "HOTEL"
    APARTMENT = "APARTMENT"
    HOSTEL = "HOSTEL"
    CRUISE_CABIN = "CRUISE_CABIN"
    SPACE_POD = "SPACE_POD"
    RESORT = "RESORT"

class ProgramTier(str, enum.Enum):
    BUDGET = "BUDGET"
    STANDARD = "STANDARD"
    LUXURY = "LUXURY"
    VIP_INTERSTELLAR = "VIP_INTERSTELLAR"
    SCHOOL_TRIP = "SCHOOL_TRIP"

class ParticipantStatus(str, enum.Enum):
    ENROLLED = "ENROLLED"
    IN_TRAINING = "IN_TRAINING"
    BOARDED = "BOARDED"
    COMPLETED = "COMPLETED"
    DROPPED = "DROPPED"

class EventType(str, enum.Enum):
    CONCERT = "CONCERT"
    SPORTS_MATCH = "SPORTS_MATCH"
    BUSINESS_SUMMIT = "BUSINESS_SUMMIT"
    METAVERSE_EVENT = "METAVERSE_EVENT"

class TicketTier(str, enum.Enum):
    GENERAL = "GENERAL"
    VIP = "VIP"
    VVIP_TRANSIT = "VVIP_TRANSIT"

class SportCategory(str, enum.Enum):
    PHYSICAL = "PHYSICAL"
    MENTAL = "MENTAL"
    E_SPORTS = "E_SPORTS"
    HYBRID = "HYBRID"

class SportsEntityType(str, enum.Enum):
    CLUB = "CLUB"
    ACADEMY = "ACADEMY"
    MARKETING_AGENCY = "MARKETING_AGENCY"

class TournamentFormat(str, enum.Enum):
    LEAGUE = "LEAGUE"
    KNOCKOUT = "KNOCKOUT"
    GROUP_AND_KNOCKOUT = "GROUP_AND_KNOCKOUT"

class MatchStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"

class TransferStatus(str, enum.Enum):
    BID_PLACED = "BID_PLACED"
    NEGOTIATING = "NEGOTIATING"
    MEDICAL_REVIEW = "MEDICAL_REVIEW"
    TERMS_AGREED = "TERMS_AGREED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

# ========== 1. السياحة: الوجهات والإقامة ==========
class TourismDestination(Base):
    __tablename__ = "tourism_destinations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    destination_type = Column(SQLEnum(DestinationType), nullable=False)
    planet_body = Column(String(50), default="EARTH")
    gps_location = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AccommodationFacility(Base):
    __tablename__ = "accommodation_facilities"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    destination_id = Column(Integer, ForeignKey("tourism_destinations.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    facility_type = Column(SQLEnum(AccommodationType), nullable=False)
    star_rating = Column(Integer, default=0)
    amenities = Column(JSON, default=list)
    smart_contract_address = Column(String(42), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AccommodationRoom(Base):
    __tablename__ = "accommodation_rooms"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    facility_id = Column(Integer, ForeignKey("accommodation_facilities.id"), nullable=False, index=True)
    room_number = Column(String(50), nullable=False)
    room_class = Column(String(50), nullable=False)
    capacity = Column(Integer, default=2)
    price_per_night_mrusdt = Column(Numeric(30, 8), nullable=False)
    room_access_nft = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_room_tenant_facility", "tenant_id", "facility_id"),
    )


class TourismProgram(Base):
    __tablename__ = "tourism_programs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    title = Column(String(255), nullable=False)
    description = Column(Text)
    program_tier = Column(SQLEnum(ProgramTier), nullable=False)
    required_certificate_id = Column(Integer, nullable=True)
    base_price_mrusdt = Column(Numeric(30, 8), nullable=False)
    max_capacity = Column(Integer, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="ANNOUNCED")
    nft_collection_address = Column(String(42), nullable=True)
    escrow_contract_address = Column(String(42), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_program_tenant", "tenant_id"),
        CheckConstraint("end_date > start_date", name="check_program_dates"),
    )


class ProgramParticipant(Base):
    __tablename__ = "program_participants"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    program_id = Column(Integer, ForeignKey("tourism_programs.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    health_clearance = Column(Boolean, default=True)
    current_status = Column(SQLEnum(ParticipantStatus), default=ParticipantStatus.ENROLLED)
    ticket_nft_id = Column(String(100), unique=True, nullable=True)
    payment_tx_hash = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_participant_tenant_program", "tenant_id", "program_id"),
    )


# ========== 2. الترفيه: الفعاليات والتذاكر ==========
class EntertainmentVenue(Base):
    __tablename__ = "entertainment_venues"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    entity_id = Column(Integer, nullable=True, index=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    max_capacity = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_venue_tenant", "tenant_id"),
    )


class EntertainmentEvent(Base):
    __tablename__ = "entertainment_events"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    venue_id = Column(Integer, ForeignKey("entertainment_venues.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    event_type = Column(SQLEnum(EventType), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    base_ticket_price_mrusdt = Column(Numeric(30, 8), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_event_tenant_venue", "tenant_id", "venue_id"),
        CheckConstraint("end_time > start_time", name="check_event_dates"),
    )


class NFTTicket(Base):
    __tablename__ = "nft_tickets"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    event_id = Column(Integer, ForeignKey("entertainment_events.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tier = Column(SQLEnum(TicketTier), nullable=False)
    assigned_vehicle_id = Column(Integer, nullable=True)
    nft_token_id = Column(String(100), unique=True, nullable=False)
    qr_code_data = Column(String(255), unique=True, nullable=False)
    purchase_price_mrusdt = Column(Numeric(30, 8), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_ticket_tenant_event", "tenant_id", "event_id"),
    )


# ========== 3. الرياضة: الأندية، اللاعبون، الانتقالات ==========
class SportsOrganization(Base):
    __tablename__ = "sports_organizations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    org_type = Column(SQLEnum(SportsEntityType), nullable=False)
    main_sport = Column(String(100), nullable=True)
    treasury_wallet_address = Column(String(42), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_sportsorg_tenant_owner", "tenant_id", "owner_id"),
    )


class PlayerProfile(Base):
    __tablename__ = "player_profiles"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    club_id = Column(Integer, ForeignKey("sports_organizations.id"), nullable=True, index=True)
    agency_id = Column(Integer, ForeignKey("sports_organizations.id"), nullable=True, index=True)
    agent_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    medical_profile_id = Column(Integer, nullable=True)
    sport_category = Column(SQLEnum(SportCategory), nullable=False)
    position_or_role = Column(String(100), nullable=True)
    performance_stats = Column(JSON, default=dict)
    market_value_mrusdt = Column(Numeric(30, 8), default=0)
    is_insured = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_player_tenant", "tenant_id"),
    )


class PlayerTransfer(Base):
    __tablename__ = "player_transfers"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    player_id = Column(Integer, ForeignKey("player_profiles.id"), nullable=False, index=True)
    from_club_id = Column(Integer, ForeignKey("sports_organizations.id"), nullable=False)
    to_club_id = Column(Integer, ForeignKey("sports_organizations.id"), nullable=False)
    facilitating_agency_id = Column(Integer, ForeignKey("sports_organizations.id"), nullable=True)
    agent_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    bid_amount_mrusdt = Column(Numeric(30, 8), nullable=False)
    agency_fee_percentage = Column(Numeric(5, 2), default=10.0)
    contract_duration_months = Column(Integer, nullable=False)
    medical_ai_flag = Column(Boolean, default=False)
    medical_report_summary = Column(Text, nullable=True)
    status = Column(SQLEnum(TransferStatus), default=TransferStatus.BID_PLACED)
    smart_contract_tx = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_transfer_tenant", "tenant_id"),
    )


class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    organizer_agency_id = Column(Integer, ForeignKey("sports_organizations.id"), nullable=True)
    name = Column(String(255), nullable=False)
    sport_category = Column(SQLEnum(SportCategory), nullable=False)
    format = Column(SQLEnum(TournamentFormat), nullable=False)
    prize_pool_mrusdt = Column(Numeric(30, 8), default=0)
    start_date = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    standings_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_tournament_tenant", "tenant_id"),
    )


class SportsMatch(Base):
    __tablename__ = "sports_matches"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=True, index=True)
    home_team_id = Column(Integer, ForeignKey("sports_organizations.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("sports_organizations.id"), nullable=False)
    scheduled_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(SQLEnum(MatchStatus), default=MatchStatus.SCHEDULED)
    home_score = Column(Integer, default=0)
    away_score = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_match_tenant_tournament", "tenant_id", "tournament_id"),
    )