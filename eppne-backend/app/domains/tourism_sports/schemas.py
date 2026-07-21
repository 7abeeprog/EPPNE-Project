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
    name: str = Field(description="اسم الوجهة")
    destination_type: DestinationType = Field(description="نوع الوجهة")
    planet_body: str = Field(default="EARTH", description="الكوكب/الجسم السماوي")
    gps_location: Optional[Dict[str, float]] = Field(default=None, description="موقع GPS")
    description: Optional[str] = Field(default=None, description="وصف الوجهة")

class DestinationResponse(DestinationCreate):
    id: int = Field(description="معرف الوجهة")
    is_active: bool = Field(description="نشطة")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

class AccommodationCreate(BaseModel):
    destination_id: int = Field(description="معرف الوجهة")
    name: str = Field(description="اسم المنشأة")
    facility_type: AccommodationType = Field(description="نوع المنشأة")
    star_rating: int = Field(default=0, description="عدد النجوم")
    amenities: List[str] = Field(default=[], description="المرافق المتوفرة")
    smart_contract_address: Optional[str] = Field(default=None, description="عنوان العقد الذكي")

class AccommodationResponse(AccommodationCreate):
    id: int = Field(description="معرف المنشأة")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

class TourismProgramCreate(BaseModel):
    title: str = Field(description="عنوان البرنامج")
    description: Optional[str] = Field(default=None, description="وصف البرنامج")
    program_tier: ProgramTier = Field(description="فئة البرنامج")
    required_certificate_id: Optional[int] = Field(default=None, description="معرف الشهادة المطلوبة")
    base_price_mrusdt: Decimal = Field(description="السعر الأساسي")
    max_capacity: int = Field(description="السعة القصوى")
    start_date: datetime = Field(description="تاريخ البدء")
    end_date: datetime = Field(description="تاريخ الانتهاء")

    @field_validator("end_date")
    @classmethod
    def validate_end_after_start(cls, v, info):
        start = info.data.get("start_date")
        if start and v <= start:
            raise ValueError("end_date must be after start_date")
        return v

class TourismProgramResponse(TourismProgramCreate):
    id: int = Field(description="معرف البرنامج")
    status: str = Field(description="الحالة")
    nft_collection_address: Optional[str] = Field(default=None, description="عنوان مجموعة NFT")
    escrow_contract_address: Optional[str] = Field(default=None, description="عنوان عقد الضمان")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

class ProgramBookingCreate(BaseModel):
    program_id: int = Field(description="معرف البرنامج")

class ProgramBookingResponse(BaseModel):
    id: int = Field(description="معرف الحجز")
    program_id: int = Field(description="معرف البرنامج")
    user_id: int = Field(description="معرف المستخدم")
    health_clearance: bool = Field(description="موافقة صحية")
    current_status: ParticipantStatus = Field(description="الحالة الحالية")
    ticket_nft_id: Optional[str] = Field(default=None, description="معرف تذكرة NFT")
    payment_tx_hash: Optional[str] = Field(default=None, description="هاش معاملة الدفع")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

# ========== الترفيه ==========
class VenueCreate(BaseModel):
    name: str = Field(description="اسم المكان")
    location: str = Field(description="الموقع")
    max_capacity: int = Field(description="السعة القصوى")

class VenueResponse(VenueCreate):
    id: int = Field(description="معرف المكان")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

class EventCreate(BaseModel):
    venue_id: int = Field(description="معرف المكان")
    title: str = Field(description="عنوان الفعالية")
    event_type: EventType = Field(description="نوع الفعالية")
    start_time: datetime = Field(description="وقت البدء")
    end_time: datetime = Field(description="وقت الانتهاء")
    base_ticket_price_mrusdt: Decimal = Field(description="سعر التذكرة الأساسي")

    @field_validator("end_time")
    @classmethod
    def validate_end_after_start_time(cls, v, info):
        start = info.data.get("start_time")
        if start and v <= start:
            raise ValueError("end_time must be after start_time")
        return v

class EventResponse(EventCreate):
    id: int = Field(description="معرف الفعالية")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

class TicketPurchase(BaseModel):
    event_id: int = Field(description="معرف الفعالية")
    tier: TicketTier = Field(description="فئة التذكرة")
    require_vip_transport: bool = Field(default=False, description="طلب نقل VIP")

class TicketResponse(BaseModel):
    id: int = Field(description="معرف التذكرة")
    event_id: int = Field(description="معرف الفعالية")
    owner_id: int = Field(description="معرف المالك")
    tier: TicketTier = Field(description="فئة التذكرة")
    assigned_vehicle_id: Optional[int] = Field(default=None, description="معرف المركبة المخصصة")
    nft_token_id: str = Field(description="معرف توكن NFT")
    qr_code_data: str = Field(description="بيانات رمز QR")
    purchase_price_mrusdt: Decimal = Field(description="سعر الشراء")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

# ========== الرياضة ==========
class SportsOrgCreate(BaseModel):
    name: str = Field(description="اسم المنظمة")
    org_type: SportsEntityType = Field(description="نوع المنظمة")
    main_sport: Optional[str] = Field(default=None, description="الرياضة الرئيسية")

class SportsOrgResponse(SportsOrgCreate):
    id: int = Field(description="معرف المنظمة")
    owner_id: int = Field(description="معرف المالك")
    treasury_wallet_address: Optional[str] = Field(default=None, description="عنوان محفظة الخزينة")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

class PlayerProfileCreate(BaseModel):
    sport_category: SportCategory = Field(description="فئة الرياضة")
    position_or_role: Optional[str] = Field(default=None, description="المركز أو الدور")
    market_value_mrusdt: Decimal = Field(default=Decimal('0.0'), description="القيمة السوقية")

class PlayerProfileResponse(PlayerProfileCreate):
    id: int = Field(description="معرف الملف")
    user_id: int = Field(description="معرف المستخدم")
    club_id: Optional[int] = Field(default=None, description="معرف النادي")
    agency_id: Optional[int] = Field(default=None, description="معرف الوكالة")
    agent_user_id: Optional[int] = Field(default=None, description="معرف الوكيل")
    medical_profile_id: Optional[int] = Field(default=None, description="معرف الملف الطبي")
    performance_stats: Dict[str, Any] = Field(description="إحصائيات الأداء")
    is_insured: bool = Field(description="مؤمن")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

class TransferBidCreate(BaseModel):
    player_id: int = Field(description="معرف اللاعب")
    from_club_id: int = Field(description="معرف النادي البائع")
    to_club_id: int = Field(description="معرف النادي المشتري")
    facilitating_agency_id: Optional[int] = Field(default=None, description="معرف الوكالة الوسيطة")
    bid_amount_mrusdt: Decimal = Field(description="قيمة العرض")
    agency_fee_percentage: Decimal = Field(default=Decimal('10.0'), description="نسبة رسوم الوكالة")
    contract_duration_months: int = Field(description="مدة العقد بالأشهر")

class TransferBidResponse(TransferBidCreate):
    id: int = Field(description="معرف العرض")
    status: TransferStatus = Field(description="الحالة")
    medical_ai_flag: bool = Field(description="علامة الذكاء الاصطناعي الطبية")
    medical_report_summary: Optional[str] = Field(default=None, description="ملخص التقرير الطبي")
    smart_contract_tx: Optional[str] = Field(default=None, description="هاش معاملة العقد الذكي")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)

class TournamentCreate(BaseModel):
    organizer_agency_id: Optional[int] = Field(default=None, description="معرف الوكالة المنظمة")
    name: str = Field(description="اسم البطولة")
    sport_category: SportCategory = Field(description="فئة الرياضة")
    format: TournamentFormat = Field(description="نظام البطولة")
    prize_pool_mrusdt: Decimal = Field(default=Decimal('0.0'), description="مجموع الجوائز")
    start_date: datetime = Field(description="تاريخ البدء")

class TournamentResponse(TournamentCreate):
    id: int = Field(description="معرف البطولة")
    is_active: bool = Field(description="نشطة")
    standings_json: Dict[str, Any] = Field(description="جدول الترتيب")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)