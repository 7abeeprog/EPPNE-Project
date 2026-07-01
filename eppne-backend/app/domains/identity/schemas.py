from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict, SecretStr
from app.core.enums import SovereignRank, KYCStatus, MarriageStatus, SystemRole

class UserBase(BaseModel):
    username: Optional[str] = Field(None, min_length=4, max_length=50)
    email: Optional[EmailStr] = None
    name_ar: Optional[str] = None
    name_en: Optional[str] = None
    birth_date: Optional[datetime] = None
    marriage_status: MarriageStatus = MarriageStatus.SINGLE
    language_preference: str = "ar"
    profile_metadata: Dict[str, Any] = {}
    preferences: Dict[str, Any] = {}

class UserCreate(UserBase):
    username: str = Field(..., min_length=4, max_length=50)
    email: EmailStr
    password: SecretStr = Field(..., min_length=8)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name_ar: Optional[str] = None
    name_en: Optional[str] = None
    marriage_status: Optional[MarriageStatus] = None
    language_preference: Optional[str] = None
    profile_metadata: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None
    primary_wallet: Optional[str] = Field(None, pattern="^0x[a-fA-F0-9]{40}$")
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    public_id: Optional[UUID] = None
    uid: Optional[str] = None
    did: Optional[str] = None
    sovereign_rank: SovereignRank
    system_role: SystemRole
    kyc_status: KYCStatus
    reputation_score: int
    is_active: bool
    balances: Dict[str, float]
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserLogin(BaseModel):
    username_or_email: str
    password: SecretStr

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"