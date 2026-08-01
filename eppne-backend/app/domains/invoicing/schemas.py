# app/domains/invoicing/schemas.py
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

from app.domains.invoicing.models import InvoiceStatus, InvoiceType


class InvoiceBase(BaseModel):
    invoice_type: InvoiceType = Field(default=InvoiceType.SERVICE)
    amount: Decimal = Field(..., gt=0, description="مبلغ الفاتورة")
    currency: str = Field(default="MR_USDT", max_length=10)
    description: Optional[str] = Field(None, max_length=500)
    due_date: datetime = Field(..., description="تاريخ استحقاق الدفع")
    reference_id: Optional[int] = Field(None, description="معرف مرجعي (مثل order_id)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="بيانات إضافية (JSON)")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if v not in ["MR_USDT", "MR_POUND", "MR7", "NBT", "MRX", "USDT"]:
            raise ValueError("Currency must be a valid sovereign currency (MR_USDT, MR_POUND, etc.)")
        return v


class InvoiceCreate(InvoiceBase):
    tenant_id: int = Field(..., description="معرف المستأجر")
    user_id: Optional[int] = Field(0, description="معرف المستخدم (0 للفواتير النظامية)")
    idempotency_key: Optional[str] = Field(None, description="مفتاح عدم التكرار")


class InvoiceUpdate(BaseModel):
    status: Optional[InvoiceStatus] = None
    notes: Optional[str] = None
    paid_at: Optional[datetime] = None


class InvoiceResponse(InvoiceBase):
    id: int
    tenant_id: int
    user_id: Optional[int]
    invoice_number: str
    status: InvoiceStatus
    issue_date: datetime
    paid_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceListResponse(BaseModel):
    items: List[InvoiceResponse]
    total: int
    skip: int
    limit: int


class InvoiceFilter(BaseModel):
    status: Optional[InvoiceStatus] = None
    invoice_type: Optional[InvoiceType] = None
    user_id: Optional[int] = None
    reference_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None


class InvoiceStatsResponse(BaseModel):
    tenant_id: int
    total_pending: float
    total_paid: float
    total_overdue: float
    total_cancelled: float
    overdue_count: int
    currency: str
    updated_at: str