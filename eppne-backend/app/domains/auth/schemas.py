# app/domains/auth/schemas.py
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List
from datetime import datetime

# ==========================================
# 1. طلبات المصادقة
# ==========================================

class LoginRequest(BaseModel):
    """
    طلب تسجيل الدخول.
    """
    username: str = Field(description="اسم المستخدم أو البريد الإلكتروني")
    password: str = Field(description="كلمة المرور")
    device_name: Optional[str] = Field(default=None, description="اسم الجهاز (اختياري)")


class RefreshTokenRequest(BaseModel):
    """
    طلب تجديد Access Token.
    """
    refresh_token: str = Field(description="Refresh Token")


class LogoutRequest(BaseModel):
    """
    طلب تسجيل الخروج (اختياري).
    """
    refresh_token: str = Field(description="Refresh Token المراد إبطاله")


class RevokeAllSessionsRequest(BaseModel):
    """
    طلب إبطال جميع الجلسات.
    """
    confirm: bool = Field(description="تأكيد الإبطال")


# ==========================================
# 2. استجابات المصادقة
# ==========================================

class TokenResponse(BaseModel):
    """
    استجابة التوكنات (تسجيل الدخول، تجديد التوكن).
    """
    access_token: str = Field(description="Access Token (JWT)")
    refresh_token: str = Field(description="Refresh Token (JWT)")
    token_type: str = Field(default="Bearer", description="نوع التوكن")
    expires_in: int = Field(description="مدة صلاحية Access Token بالثواني")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJSUzI1NiIs...",
                "refresh_token": "eyJhbGciOiJSUzI1NiIs...",
                "token_type": "Bearer",
                "expires_in": 900
            }
        }
    )


class LoginResponse(TokenResponse):
    """
    استجابة تسجيل الدخول الكاملة (مع بيانات المستخدم).
    """
    user: dict = Field(description="بيانات المستخدم الأساسية")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJSUzI1NiIs...",
                "refresh_token": "eyJhbGciOiJSUzI1NiIs...",
                "token_type": "Bearer",
                "expires_in": 900,
                "user": {
                    "id": 1,
                    "username": "admin",
                    "email": "admin@eppne.com",
                    "role": "SUPER_ADMIN",
                    "sovereign_rank": "GOLD",
                    "tenant_id": 1
                }
            }
        }
    )


class RefreshTokenResponse(TokenResponse):
    """
    استجابة تجديد التوكن.
    """
    pass


class SessionInfoResponse(BaseModel):
    """
    معلومات الجلسة (للتدقيق والمراجعة).
    """
    id: int = Field(description="معرف جلسة Refresh Token")
    device_name: Optional[str] = Field(description="اسم الجهاز")
    ip_address: Optional[str] = Field(description="عنوان IP")
    user_agent: Optional[str] = Field(description="متصفح المستخدم")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    expires_at: datetime = Field(description="تاريخ الانتهاء")
    is_active: bool = Field(description="هل الجلسة نشطة (غير ملغاة)")

    model_config = ConfigDict(from_attributes=True)


class RevokeAllSessionsResponse(BaseModel):
    """
    استجابة إبطال جميع الجلسات.
    """
    message: str = Field(description="رسالة التأكيد")
    revoked_count: int = Field(description="عدد الجلسات الملغاة")
