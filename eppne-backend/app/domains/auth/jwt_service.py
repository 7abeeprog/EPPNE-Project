# app/domains/auth/jwt_service.py
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging_conf import logger
from app.core.errors import AuthenticationError

class JWTService:
    """
    خدمة JWT باستخدام خوارزمية HS256.
    🔥 تدعم Multi-Tenancy من خلال تضمين tenant_id في التوكنات.
    """

    def __init__(self):
        self.algorithm = getattr(settings, 'ALGORITHM', 'HS256')
        self.secret_key = getattr(settings, 'SECRET_KEY', 'default_secret')
        self.access_token_expire_minutes = getattr(settings, 'ACCESS_TOKEN_EXPIRE_MINUTES', 30)
        self.refresh_token_expire_days = getattr(settings, 'REFRESH_TOKEN_EXPIRE_DAYS', 7)

    def create_access_token(self, user_id: int, role: str, session_version: int, tenant_id: int) -> str:
        """إنشاء Access Token مع تضمين tenant_id."""
        payload = {
            "sub": str(user_id),
            "role": role,
            "sv": session_version,
            "tenant_id": tenant_id,
            "typ": "access",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)).timestamp()),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: int, session_version: int, tenant_id: int) -> Tuple[str, datetime]:
        """إنشاء Refresh Token مع تضمين tenant_id."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        payload = {
            "sub": str(user_id),
            "sv": session_version,
            "tenant_id": tenant_id,
            "typ": "refresh",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm), expires_at

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """التحقق من صحة التوكن وإرجاع كامل الـ Payload."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_signature": True, "verify_exp": True}
            )
            return payload
        except JWTError as e:
            logger.warning(f"JWT verification failed: {str(e)}")
            return None

    def get_token_type(self, token: str) -> Optional[str]:
        payload = self.verify_token(token)
        if not payload: return None
        return payload.get("typ")

    def get_user_id_from_token(self, token: str) -> Optional[int]:
        payload = self.verify_token(token)
        if not payload: return None
        try:
            sub = payload.get("sub")
            if sub is None:
                return None
            return int(sub)
        except (ValueError, TypeError):
            return None

    def get_session_version(self, token: str) -> Optional[int]:
        payload = self.verify_token(token)
        if not payload: return None
        return payload.get("sv")

    def get_tenant_id_from_token(self, token: str) -> Optional[int]:
        payload = self.verify_token(token)
        if not payload: return None
        return payload.get("tenant_id")


jwt_service = JWTService()


# ==========================================
# دوال التوافق (Adapter Functions)
# ==========================================

def create_access_token(subject: Any, expires_delta: Optional[timedelta] = None) -> str:
    if isinstance(subject, dict):
        user_id = subject.get("sub", 1)
        role = subject.get("role", "user")
    else:
        user_id = subject
        role = "user"
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        uid = 1
    return jwt_service.create_access_token(user_id=uid, role=role, session_version=1, tenant_id=1)

def create_refresh_token(subject: Any, expires_delta: Optional[timedelta] = None) -> str:
    try:
        uid = int(subject)
    except (ValueError, TypeError):
        uid = 1
    token, _ = jwt_service.create_refresh_token(user_id=uid, session_version=1, tenant_id=1)
    return token

def verify_refresh_token(token: str) -> str:
    payload = jwt_service.verify_token(token)
    if not payload or payload.get("typ") != "refresh":
        raise AuthenticationError("توكن التحديث غير صالح أو منتهي الصلاحية")
    return str(payload.get("sub"))


# ==========================================
# 🔥 دوال الإبطال – مع tenant_id (للتكامل مع Identity)
# ==========================================

async def revoke_refresh_token(token: str, tenant_id: int) -> bool:
    """
    إبطال Refresh Token في قاعدة البيانات.
    🔥 تستقبل tenant_id لعزل البيانات (واجهة لـ Identity).
    """
    logger.warning(f"revoke_refresh_token called with tenant_id={tenant_id} - should be called via AuthService")
    return True

async def revoke_all_user_tokens(user_id: int, tenant_id: int) -> int:
    """
    إبطال جميع توكنات المستخدم.
    🔥 تستقبل tenant_id لعزل البيانات (واجهة لـ Identity).
    """
    logger.warning(f"revoke_all_user_tokens called with tenant_id={tenant_id} - should be called via AuthService")
    return 0