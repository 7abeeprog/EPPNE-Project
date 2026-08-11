# app/domains/identity/schemas.py
from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict, SecretStr
from app.core.enums import SovereignRank, KYCStatus, MarriageStatus, SystemRole, InvitationStatus

class UserBase(BaseModel):
    username: Optional[str] = Field(default=None, min_length=4, max_length=50, description="اسم المستخدم")
    email: Optional[EmailStr] = Field(default=None, description="البريد الإلكتروني")
    name_ar: Optional[str] = Field(default=None, description="الاسم بالعربية")
    name_en: Optional[str] = Field(default=None, description="الاسم بالإنجليزية")
    birth_date: Optional[datetime] = Field(default=None, description="تاريخ الميلاد")
    marriage_status: MarriageStatus = Field(default=MarriageStatus.SINGLE, description="الحالة الاجتماعية")
    language_preference: str = Field(default="ar", description="اللغة المفضلة")
    profile_metadata: Dict[str, Any] = Field(default_factory=dict, description="بيانات إضافية")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="تفضيلات المستخدم")

class UserCreate(UserBase):
    username: str = Field(..., min_length=4, max_length=50, description="اسم المستخدم")  # type: ignore
    email: EmailStr = Field(description="البريد الإلكتروني")  # type: ignore
    password: SecretStr = Field(..., min_length=8, description="كلمة المرور")

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = Field(default=None, description="البريد الإلكتروني")
    name_ar: Optional[str] = Field(default=None, description="الاسم بالعربية")
    name_en: Optional[str] = Field(default=None, description="الاسم بالإنجليزية")
    marriage_status: Optional[MarriageStatus] = Field(default=None, description="الحالة الاجتماعية")
    language_preference: Optional[str] = Field(default=None, description="اللغة المفضلة")
    profile_metadata: Optional[Dict[str, Any]] = Field(default=None, description="بيانات إضافية")
    preferences: Optional[Dict[str, Any]] = Field(default=None, description="تفضيلات المستخدم")
    primary_wallet: Optional[str] = Field(default=None, pattern="^0x[a-fA-F0-9]{40}$", description="عنوان المحفظة")
    is_active: Optional[bool] = Field(default=None, description="هل الحساب نشط؟")

class UserResponse(UserBase):
    id: int
    public_id: Optional[UUID] = None
    uid: Optional[str] = None
    did: Optional[str] = None
    tenant_id: int
    sovereign_rank: SovereignRank
    system_role: SystemRole
    kyc_status: KYCStatus
    reputation_score: int
    is_active: bool
    balances: Optional[Dict[str, float]] = Field(default_factory=dict, description="أرصدة المحفظة")
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UserLogin(BaseModel):
    username_or_email: str = Field(description="اسم المستخدم أو البريد الإلكتروني")
    password: SecretStr = Field(description="كلمة المرور")

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = Field(default="bearer")

class SessionInfoResponse(BaseModel):
    id: int = Field(description="معرف جلسة Refresh Token")
    device_name: Optional[str] = Field(default=None, description="اسم الجهاز")
    ip_address: Optional[str] = Field(default=None, description="عنوان IP")
    user_agent: Optional[str] = Field(default=None, description="متصفح المستخدم")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    expires_at: datetime = Field(description="تاريخ الانتهاء")
    is_active: bool = Field(description="هل الجلسة نشطة (غير ملغاة)")

    model_config = ConfigDict(from_attributes=True)


class TenantInvitationCreate(BaseModel):
    email: Optional[EmailStr] = Field(default=None, description="ربط الدعوة بإيميل محدد (اختياري — فارغ = رابط عام)")
    product_id: Optional[int] = Field(default=None, description="المنتج المرتبط بالإحالة (اختياري)")
    max_uses: Optional[int] = Field(default=None, ge=1, description="الحد الأقصى للاستخدام؛ فارغ = بلا حد (رابط إحالة متكرر)")
    expires_at: Optional[datetime] = Field(default=None, description="تاريخ انتهاء الصلاحية (اختياري)")


class TenantInvitationResponse(BaseModel):
    id: int
    tenant_id: int
    has_token: bool = Field(description="الدعوة مرتبطة بتوكن صالح للاستخدام — القيمة الخام لا تُعرض هنا إطلاقًا")
    is_active: bool = Field(description="جاهزة للاستخدام الآن (status=PENDING + غير منتهية + لم تصل max_uses)")
    email: Optional[str] = None
    referrer_user_id: int
    product_id: Optional[int] = None
    status: InvitationStatus
    max_uses: Optional[int] = None
    current_uses: int
    expires_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    revoked_by_user_id: Optional[int] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TenantInvitationCreateResponse(TenantInvitationResponse):
    token: str = Field(description="القيمة الخام للتوكن — تظهر هنا فقط عند الإنشاء، غير قابلة للاسترجاع لاحقًا (مُخزَّن كـhash فقط)")


class InvitationRegisterRequest(UserCreate):
    token: str = Field(description="توكن الدعوة الخام (من الرابط اللي وصل للمستخدم)")