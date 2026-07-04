# app/core/security.py

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.database import get_db
from app.domains.auth.jwt_service import jwt_service
from app.domains.auth.repository import AuthRepository
from app.domains.identity.models import User
from app.domains.identity.repository import UserRepository
from app.core.logging_conf import logger
from app.core.errors import AuthenticationError, PermissionDeniedError


# ==========================================
# 🔒 إعدادات التشفير والأساسيات (Core Security)
# ==========================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


# ==========================================
# 🔥 الإضافات الأمنية لقطاع الخصوصية (Privacy Domain)
# ==========================================

async def is_privacy_officer(admin_id: int) -> bool:
    """
    التحقق مما إذا كان المستخدم يمتلك صلاحية ضابط خصوصية.
    (دالة مبدئية - يمكن الاستغناء عنها لاحقاً لصالح get_privacy_officer التي تعتمد على FastAPI Depends)
    """
    # TODO: استبدال هذا المنطق باستعلام فعلي من قاعدة البيانات للتحقق من الأدوار (Roles)
    return True 

def encrypt_ip(ip: str) -> str:
    """
    تشفير عنوان الـ IP باتجاه واحد (Hashing) للامتثال لقوانين الخصوصية.
    نستخدم SECRET_KEY الخاص بالنظام كـ Salt قوي لمنع هجمات فك التشفير (Rainbow Tables).
    """
    if not ip:
        return ""
    return hashlib.sha256((ip + settings.SECRET_KEY).encode()).hexdigest()


# ==========================================
# 🛡️ مصادقة المستخدمين (Authentication Dependencies)
# ==========================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    استخراج المستخدم الحالي من التوكن.
    🔥 يتم التحقق من:
    1. صحة التوكن (التوقيع والصلاحية).
    2. وجود المستخدم في قاعدة البيانات.
    3. نشاط المستخدم (is_active).
    4. مطابقة session_version.
    """
    token = credentials.credentials

    # 1. التحقق من صحة التوكن
    payload = jwt_service.verify_token(token)
    if not payload:
        raise AuthenticationError("Invalid or expired token")

    # 2. التحقق من نوع التوكن (Access Token فقط)
    if payload.get("typ") != "access":
        raise AuthenticationError("Invalid token type")

    # 3. استخراج user_id و session_version
    user_id = payload.get("sub")
    token_session_version = payload.get("sv")

    if not user_id:
        raise AuthenticationError("Invalid token payload")

    # 4. جلب المستخدم من قاعدة البيانات
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(int(user_id))

    if not user:
        raise AuthenticationError("User not found")

    if not user.is_active:
        raise AuthenticationError("User is inactive")

    # 5. 🔥 التحقق من session_version (إبطال الجلسات عن بُعد)
    if user.session_version != token_session_version:
        raise AuthenticationError("Session has been revoked")

    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    التحقق من أن المستخدم نشط.
    """
    if not current_user.is_active:
        raise AuthenticationError("User is inactive")
    return current_user

async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    التحقق من أن المستخدم هو Super Admin.
    """
    if not current_user.is_superuser and current_user.system_role not in ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]:
        raise PermissionDeniedError("Insufficient permissions")
    return current_user

async def get_privacy_officer(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    التحقق من أن المستخدم هو مسؤول الخصوصية.
    🔥 الصلاحيات المطلوبة: ADMIN, SUPER_ADMIN, EXECUTIVE_DIRECTOR
    """
    allowed_roles = ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]
    if current_user.system_role not in allowed_roles:
        raise PermissionDeniedError("Privacy Officer permissions required")
    return current_user


# ==========================================
# 🔑 التحكم في الوصول (RBAC Authorization)
# ==========================================

def require_roles(roles: List[str]):
    """
    مصنع دوال للتحقق من صلاحيات المستخدم (RBAC).
    🔥 يستخدم في الـ Routers: Depends(require_roles(["ADMIN", "SUPER_ADMIN"]))
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.system_role not in roles:
            raise PermissionDeniedError(f"Required roles: {', '.join(roles)}")
        return current_user
    return role_checker