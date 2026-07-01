تم دمج الإضافة المطلوبة بالكامل داخل ملف `schemas.py` الخاص بقطاع السياحة والرياضة، مع الحفاظ على جميع النماذج والمسميات الأصلية، وإضافة:

- **`field_validator`** في `TourismProgramCreate` للتحقق من أن `end_date` بعد `start_date`.
- **`field_validator`** في `EventCreate` للتحقق من أن `end_time` بعد `start_time`.

الملف النهائي جاهز للإنتاج (انظر أدناه)، يليه **تقرير مختصر من سطر واحد** عن جاهزيته.

---

```python
# app/domains/tourism_sports/schemas.py (الإصدار النهائي المتكامل)
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.tourism_sports.models import (
    DestinationType, AccommodationType, ProgramTier, ParticipantStatus,
    EventType, TicketTier, SportCategory, SportsEntityType, TournamentFormat,
    MatchStatus, TransferStatus
)

# ========== السياحة ==========
class DestinationCreate(BaseModel):
    name: str
    destination_type: DestinationType
    planet_body: str = "EARTH"
    gps_location: Optional[Dict[str, float]] = None
    description: Optional[str] = None

class DestinationResponse(DestinationCreate):
    id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AccommodationCreate(BaseModel):
    destination_id: int
    name: str
    facility_type: AccommodationType
    star_rating: int = 0
    amenities: List[str] = []
    smart_contract_address: Optional[str] = None

class AccommodationResponse(AccommodationCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TourismProgramCreate(BaseModel):
    title: str
    description: Optional[str] = None
    program_tier: ProgramTier
    required_certificate_id: Optional[int] = None
    base_price_mrusdt: Decimal
    max_capacity: int
    start_date: datetime
    end_date: datetime

    @field_validator("end_date")
    def validate_end_after_start(cls, v, info):
        start = info.data.get("start_date")
        if start and v <= start:
            raise ValueError("end_date must be after start_date")
        return v

class TourismProgramResponse(TourismProgramCreate):
    id: int
    status: str
    nft_collection_address: Optional[str]
    escrow_contract_address: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ProgramBookingCreate(BaseModel):
    program_id: int

class ProgramBookingResponse(BaseModel):
    id: int
    program_id: int
    user_id: int
    health_clearance: bool
    current_status: ParticipantStatus
    ticket_nft_id: Optional[str]
    payment_tx_hash: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== الترفيه ==========
class VenueCreate(BaseModel):
    name: str
    location: str
    max_capacity: int

class VenueResponse(VenueCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class EventCreate(BaseModel):
    venue_id: int
    title: str
    event_type: EventType
    start_time: datetime
    end_time: datetime
    base_ticket_price_mrusdt: Decimal

    @field_validator("end_time")
    def validate_end_after_start_time(cls, v, info):
        start = info.data.get("start_time")
        if start and v <= start:
            raise ValueError("end_time must be after start_time")
        return v

class EventResponse(EventCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TicketPurchase(BaseModel):
    event_id: int
    tier: TicketTier
    require_vip_transport: bool = False

class TicketResponse(BaseModel):
    id: int
    event_id: int
    owner_id: int
    tier: TicketTier
    assigned_vehicle_id: Optional[int]
    nft_token_id: str
    qr_code_data: str
    purchase_price_mrusdt: Decimal
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== الرياضة ==========
class SportsOrgCreate(BaseModel):
    name: str
    org_type: SportsEntityType
    main_sport: Optional[str] = None

class SportsOrgResponse(SportsOrgCreate):
    id: int
    owner_id: int
    treasury_wallet_address: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PlayerProfileCreate(BaseModel):
    sport_category: SportCategory
    position_or_role: Optional[str] = None
    market_value_mrusdt: Decimal = 0

class PlayerProfileResponse(PlayerProfileCreate):
    id: int
    user_id: int
    club_id: Optional[int]
    agency_id: Optional[int]
    agent_user_id: Optional[int]
    medical_profile_id: Optional[int]
    performance_stats: Dict[str, Any]
    is_insured: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TransferBidCreate(BaseModel):
    player_id: int
    from_club_id: int
    to_club_id: int
    facilitating_agency_id: Optional[int] = None
    bid_amount_mrusdt: Decimal
    agency_fee_percentage: Decimal = 10.0
    contract_duration_months: int

class TransferBidResponse(TransferBidCreate):
    id: int
    status: TransferStatus
    medical_ai_flag: bool
    medical_report_summary: Optional[str]
    smart_contract_tx: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TournamentCreate(BaseModel):
    organizer_agency_id: Optional[int] = None
    name: str
    sport_category: SportCategory
    format: TournamentFormat
    prize_pool_mrusdt: Decimal = 0
    start_date: datetime

class TournamentResponse(TournamentCreate):
    id: int
    is_active: bool
    standings_json: Dict[str, Any]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

---

**تقرير جاهزية الملف (سطر واحد):**  
> ✅ الملف جاهز للإنتاج مع دمج `field_validator` للتحقق من صحة التواريخ في البرامج والفعاليات، والحفاظ على جميع النماذج والمسميات الأصلية، مع تحسين الأمان على مستوى التحقق من البيانات.