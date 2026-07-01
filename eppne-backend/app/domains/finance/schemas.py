# app/domains/finance/schemas.py
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime

# ========== المحفظة ==========
class WalletBalanceResponse(BaseModel):
    balances: Dict[str, float]


# ========== المعاملات ==========
class TransferRequest(BaseModel):
    receiver_email: str
    currency: str = Field(..., description="MR_POUND, MR_USDT, MR7, NBT, MRX, LOYALTY_POINTS")
    amount: Decimal = Field(..., gt=0)
    notes: Optional[str] = None
    idempotency_key: Optional[str] = Field(None, description="مفتاح عدم التكرار (يُولد تلقائياً إذا لم يُقدم)")

    @field_validator("currency")
    def validate_currency(cls, v):
        allowed = ["MR_POUND", "MR_USDT", "MR7", "NBT", "MRX", "LOYALTY_POINTS"]
        if v not in allowed:
            raise ValueError(f"عملة غير مدعومة. المسموح: {allowed}")
        return v


class TransferResponse(BaseModel):
    tx_hash: str
    amount: float
    currency: str
    status: str
    created_at: datetime


class SwapRequest(BaseModel):
    from_currency: str
    to_currency: str
    amount_in: Decimal = Field(..., gt=0)
    idempotency_key: Optional[str] = Field(None, description="مفتاح عدم التكرار")


class SwapResponse(BaseModel):
    from_amount: float
    from_currency: str
    to_amount: float
    to_currency: str
    rate_applied: float
    tx_hash: str


class TransactionResponse(BaseModel):
    id: int
    tx_hash: str
    tx_type: str
    amount: float
    currency: str
    status: str
    notes: Optional[str]
    created_at: datetime
    sender_id: Optional[int] = None
    receiver_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# 🔥 استجابة Pagination
class PaginatedTransactionResponse(BaseModel):
    data: List[TransactionResponse]
    total: int
    skip: int
    limit: int


# ========== إعدادات النظام والبنك المركزي ==========
class CryptoModeToggle(BaseModel):
    mode: str = Field(..., pattern="^(FULL_CRYPTO|POINTS_ONLY)$")


class ExchangeRatesUpdate(BaseModel):
    rates: Dict[str, float]


class MintRequest(BaseModel):
    currency: str
    amount: Decimal = Field(..., gt=0)


class MaxSupplyUpdate(BaseModel):
    max_supply: Dict[str, float]