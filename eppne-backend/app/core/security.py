# app/core/security.py
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt
from jose.exceptions import JWTError  # 🔥 التصحيح الأساسي
from passlib.context import CryptContext

from app.core.config import settings
from app.core.database import get_db
from app.domains.identity.models import User
from app.domains.identity.repository import UserRepository
from app.core.logging_conf import logger
from app.core.errors import AuthenticationError, PermissionDeniedError

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
    to_encode.update({"exp": expire, "typ": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "typ": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

def encrypt_ip(ip: str) -> str:
    if not ip:
        return ""
    return hashlib.sha256((ip + settings.SECRET_KEY).encode()).hexdigest()

# ========== دالة التوافق مع قطاع privacy ==========
async def is_privacy_officer(user_id: int) -> bool:
    """
    التحقق مما إذا كان المستخدم يمتلك صلاحية ضابط خصوصية.
    (مؤقتة لحين ربطها بـ RBAC الفعلي)
    """
    # TODO: استبدال هذا المنطق باستعلام فعلي من قاعدة البيانات
    return True

# ========== دوال المصادقة ==========
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")
    
    if payload.get("typ") != "access":
        raise AuthenticationError("Invalid token type")
    
    user_id = payload.get("sub")
    token_session_version = payload.get("sv")
    
    if not user_id:
        raise AuthenticationError("Invalid token payload")
    
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(int(user_id))
    
    if not user:
        raise AuthenticationError("User not found")
    # 🔥 استخدام is False لتجنب تحذيرات Pylance مع SQLAlchemy
    if user.is_active is False:
        raise AuthenticationError("User is inactive")
    if user.session_version != token_session_version:
        raise AuthenticationError("Session has been revoked")
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.is_active is False:
        raise AuthenticationError("User is inactive")
    return current_user

async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    allowed_roles = ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]
    if current_user.system_role not in allowed_roles:
        raise PermissionDeniedError("Superuser privileges required")
    return current_user

async def get_privacy_officer(
    current_user: User = Depends(get_current_active_user)
) -> User:
    allowed_roles = ["ADMIN", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]
    if current_user.system_role not in allowed_roles:
        raise PermissionDeniedError("Privacy Officer permissions required")
    return current_user

def require_roles(roles: List[str]):
    async def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.system_role not in roles:
            raise PermissionDeniedError(f"Required roles: {', '.join(roles)}")
        return current_user
    return role_checker