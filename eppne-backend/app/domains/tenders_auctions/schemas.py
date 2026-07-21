# app/domains/tenders_auctions/schemas.py
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


# ========== المناقصات (Tenders) ==========
class TenderCreate(BaseModel):
    title: str = Field(description="عنوان المناقصة")
    description: str = Field(description="وصف المناقصة")
    scope_of_work: Dict[str, Any] = Field(description="نطاق العمل")
    estimated_budget_mrusdt: Decimal = Field(..., gt=0, description="الميزانية التقديرية")
    min_bid_mrusdt: Optional[Decimal] = Field(default=None, description="الحد الأدنى للعطاء")
    max_bid_mrusdt: Optional[Decimal] = Field(default=None, description="الحد الأعلى للعطاء")
    submission_start: datetime = Field(description="تاريخ بدء التقديم")
    submission_deadline: datetime = Field(description="تاريخ انتهاء التقديم")
    project_id: Optional[int] = Field(default=None, description="معرف المشروع المرتبط")

    @field_validator("submission_deadline")
    @classmethod
    def validate_dates(cls, v, info):
        if "submission_start" in info.data and v <= info.data["submission_start"]:
            raise ValueError("submission_deadline must be after submission_start")
        return v

class TenderResponse(TenderCreate):
    id: int = Field(description="معرف المناقصة")
    status: str = Field(description="الحالة")
    created_by: int = Field(description="معرف المنشئ")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    updated_at: datetime = Field(description="تاريخ التحديث")
    model_config = ConfigDict(from_attributes=True)

class TenderBidCreate(BaseModel):
    tender_id: int = Field(description="معرف المناقصة")
    technical_envelope: Dict[str, Any] = Field(description="المظروف الفني")
    encrypted_financial_envelope: str = Field(description="المظروف المالي المشفر")

class TenderBidResponse(BaseModel):
    id: int = Field(description="معرف العطاء")
    tender_id: int = Field(description="معرف المناقصة")
    bidder_id: int = Field(description="معرف مقدم العطاء")
    technical_envelope: Dict[str, Any] = Field(description="المظروف الفني")
    encrypted_financial_envelope: str = Field(description="المظروف المالي المشفر")
    technical_score: Optional[float] = Field(default=None, description="الدرجة الفنية")
    financial_amount_mrusdt: Optional[Decimal] = Field(default=None, description="المبلغ المالي")
    status: str = Field(description="الحالة")
    bid_tx_hash: Optional[str] = Field(default=None, description="هاش معاملة العطاء")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    updated_at: datetime = Field(description="تاريخ التحديث")
    model_config = ConfigDict(from_attributes=True)

class TenderBidEvaluate(BaseModel):
    technical_score: Decimal = Field(..., ge=0, le=100, description="الدرجة الفنية (0-100)")


# ========== المزادات (Auctions) ==========
class AuctionCreate(BaseModel):
    title: str = Field(description="عنوان المزاد")
    description: Optional[str] = Field(default=None, description="وصف المزاد")
    asset_type: str = Field(description="نوع الأصل (مثل land, property, equipment)")
    asset_id: Optional[int] = Field(default=None, description="معرف الأصل المرتبط")
    start_price_mrusdt: Decimal = Field(..., gt=0, description="سعر البداية")
    min_increment_mrusdt: Decimal = Field(default=Decimal('0.0'), description="الحد الأدنى للزيادة")
    start_time: datetime = Field(description="وقت بدء المزاد")
    end_time: datetime = Field(description="وقت انتهاء المزاد")

    @field_validator("end_time")
    @classmethod
    def validate_dates(cls, v, info):
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v

class AuctionResponse(AuctionCreate):
    id: int = Field(description="معرف المزاد")
    status: str = Field(description="الحالة")
    created_by: int = Field(description="معرف المنشئ")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    updated_at: datetime = Field(description="تاريخ التحديث")
    model_config = ConfigDict(from_attributes=True)

class LiveBidCreate(BaseModel):
    bid_amount_mrusdt: Decimal = Field(..., gt=0, description="قيمة المزايدة")

class LiveBidResponse(BaseModel):
    id: int = Field(description="معرف المزايدة")
    auction_id: int = Field(description="معرف المزاد")
    bidder_id: int = Field(description="معرف المزايد")
    bid_amount_mrusdt: Decimal = Field(description="قيمة المزايدة")
    bid_tx_hash: Optional[str] = Field(default=None, description="هاش معاملة المزايدة")
    created_at: datetime = Field(description="تاريخ المزايدة")
    model_config = ConfigDict(from_attributes=True)