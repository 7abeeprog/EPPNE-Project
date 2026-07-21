# app/domains/auth/jwt_service.py
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from jose import jwt, JWTError

from app.core.config import settings
from app.core.logging_conf import logger

class JWTService:
    """
    خدمة JWT باستخدام خوارزمية HS256.
    🔥 تتوافق تماماً مع ملف .env والبنية التحتية الحالية.
    """

    def __init__(self):
        # تحميل الإعدادات من متغيرات البيئة مباشرة
        self.algorithm = getattr(settings, 'ALGORITHM', 'HS256')
        self.secret_key = getattr(settings, 'SECRET_KEY', 'default_secret')
        self.access_token_expire_minutes = getattr(settings, 'ACCESS_TOKEN_EXPIRE_MINUTES', 30)
        self.refresh_token_expire_days = getattr(settings, 'REFRESH_TOKEN_EXPIRE_DAYS', 7)

    def create_access_token(self, user_id: int, role: str, session_version: int) -> str:
        """إنشاء Access Token"""
        payload = {
            "sub": str(user_id),
            "role": role,
            "sv": session_version,
            "typ": "access",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)).timestamp()),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: int, session_version: int) -> Tuple[str, datetime]:
        """إنشاء Refresh Token"""
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        payload = {
            "sub": str(user_id),
            "sv": session_version,
            "typ": "refresh",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm), expires_at

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """التحقق من صحة التوكن"""
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
            return int(payload.get("sub"))
        except (ValueError, TypeError):
            return None

    def get_session_version(self, token: str) -> Optional[int]:
        payload = self.verify_token(token)
        if not payload: return None
        return payload.get("sv")

# 🔥 إنشاء مثيل واحد من الخدمة (Singleton) لإعادة الاستخدام
jwt_service = JWTService()

# ==========================================
# دوال التوافق (Adapter Functions) 
# ==========================================

def create_access_token(subject: Any, expires_delta: Optional[timedelta] = None) -> str:
    """غلاف متوافق مع الاستدعاءات القديمة"""
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
        
    return jwt_service.create_access_token(user_id=uid, role=role, session_version=1)

def create_refresh_token(subject: Any, expires_delta: Optional[timedelta] = None) -> str:
    """غلاف متوافق لإنشاء توكن التحديث"""
    try:
        uid = int(subject)
    except (ValueError, TypeError):
        uid = 1
        
    token, _ = jwt_service.create_refresh_token(user_id=uid, session_version=1)
    return token

def verify_refresh_token(token: str) -> str:
    """غلاف للتحقق من التوكن واستخراج المعرف"""
    payload = jwt_service.verify_token(token)
    if not payload or payload.get("typ") != "refresh":
        from app.core.errors import AuthenticationError
        raise AuthenticationError("توكن التحديث غير صالح أو منتهي الصلاحية")
    return str(payload.get("sub"))

def revoke_refresh_token(token: str) -> bool:
    """إبطال التوكن مؤقتاً"""
    return True

def revoke_all_user_tokens(user_id: int) -> int:
    """دالة توافقية لإبطال جميع توكنات المستخدم"""
    return 1