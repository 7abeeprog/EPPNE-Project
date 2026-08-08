# app/core/security.py
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext

from app.core.config import settings
from app.core.database import get_db
from app.domains.identity.models import User
from app.domains.identity.repository import UserRepository
from app.core.logging_conf import logger, set_sector, get_sector
from app.core.errors import AuthenticationError, PermissionDeniedError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


# ============================================================
# 1. دوال التجزئة والمصادقة
# ============================================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# ============================================================
# 2. إنشاء وتوقيع التوكنات (JWT)
# ============================================================
def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    user_tenant_id: Optional[int] = None
) -> str:
    to_encode = data.copy()
    if "tenant_id" in data and user_tenant_id is not None and data["tenant_id"] != user_tenant_id:
        raise ValueError("Tenant ID mismatch: cannot create token for different tenant")
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "typ": "access",
        "tenant_id": data.get("tenant_id"),
        "sector": data.get("sector"),
    })
    return jwt.encode(to_encode, settings.SECRET_KEY.get_secret_value(), algorithm=settings.ALGORITHM)


def create_refresh_token(
    data: Dict[str, Any],
    user_tenant_id: Optional[int] = None
) -> str:
    to_encode = data.copy()
    if "tenant_id" in data and user_tenant_id is not None and data["tenant_id"] != user_tenant_id:
        raise ValueError("Tenant ID mismatch: cannot create refresh token for different tenant")
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "typ": "refresh",
        "tenant_id": data.get("tenant_id"),
        "sector": data.get("sector"),
    })
    return jwt.encode(to_encode, settings.SECRET_KEY.get_secret_value(), algorithm=settings.ALGORITHM)


# ============================================================
# 3. فك تشفير التوكن
# ============================================================
def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, settings.SECRET_KEY.get_secret_value(), algorithms=[settings.ALGORITHM])
    except ExpiredSignatureError:
        logger.warning("⚠️ Token expired")
        raise
    except JWTError as e:
        logger.warning(f"⚠️ Invalid token: {e}")
        raise


def encrypt_ip(ip: str) -> str:
    if not ip:
        return ""
    return hashlib.sha256((ip + settings.SECRET_KEY.get_secret_value()).encode()).hexdigest()


# ============================================================
# 4. اعتماديات المصادقة
# ============================================================
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
    cookie_token: Optional[str] = Cookie(None, alias="access_token"),
) -> User:
    """
    الحصول على المستخدم الحالي من التوكن (Header Bearer أو HttpOnly Cookie).
    """
    token = credentials.credentials if credentials else cookie_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(token)
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired", headers={"WWW-Authenticate": "Bearer"})
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"})

    if payload.get("typ") != "access":
        raise AuthenticationError("Invalid token type (must be access token)")

    user_id = payload.get("sub")
    token_session_version = payload.get("sv")
    token_tenant_id = payload.get("tenant_id")
    token_sector = payload.get("sector")

    if not user_id:
        raise AuthenticationError("Invalid token payload: missing subject")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(int(user_id), token_tenant_id)

    if not user:
        raise AuthenticationError("User not found")
    if not user.is_active:
        raise AuthenticationError("User is inactive")
    if token_tenant_id is not None and user.tenant_id != token_tenant_id:
        logger.warning(f"⚠️ Tenant mismatch: token={token_tenant_id}, user={user.tenant_id}")
        raise AuthenticationError("Tenant mismatch")
    if user.session_version != token_session_version:
        raise AuthenticationError("Session has been revoked")

    # 🔥 تخزين القطاع في السياق (ContextVar) لاستخدامه في require_sector
    set_sector(token_sector)

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise AuthenticationError("User is inactive")
    return current_user


# ============================================================
# 5. صلاحيات السوبر أدمن
# ============================================================
async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    role_value = current_user.system_role.value if hasattr(current_user.system_role, "value") else current_user.system_role
    if role_value not in ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]:
        raise PermissionDeniedError("Superuser privileges required")
    return current_user


# ============================================================
# 6. صلاحيات ضابط الخصوصية
# ============================================================
async def is_privacy_officer(user: User) -> bool:
    role = getattr(user, "system_role", None)
    if role is None:
        return False
    role_value = role.value if hasattr(role, "value") else role
    return role_value in ["PRIVACY_OFFICER", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]


async def get_privacy_officer(
    current_user: User = Depends(get_current_active_user)
) -> User:
    if not await is_privacy_officer(current_user):
        raise PermissionDeniedError("Privacy Officer permissions required")
    return current_user


# ============================================================
# 7. 🔥 صلاحيات القطاعات (المصححة باستخدام ContextVar)
# ============================================================
def require_sector(sector: str):
    """
    مصنع اعتمادية للتحقق من أن المستخدم ينتمي إلى قطاع معين.
    يُعيد دالة تبعية تتحقق وترفع استثناء إذا لم يتطابق القطاع،
    وتعيد `current_user` إذا نجحت.
    """
    async def sector_checker(current_user: User = Depends(get_current_active_user)) -> User:
        user_sector = get_sector()
        role_value = current_user.system_role.value if hasattr(current_user.system_role, "value") else current_user.system_role

        if role_value in ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]:
            return current_user

        if user_sector is None:
            raise PermissionDeniedError("User sector not defined. Please contact support.")

        if user_sector != sector:
            raise PermissionDeniedError(
                f"عذراً، لا تملك صلاحية الوصول إلى قطاع {sector}. قطاعك الحالي: {user_sector}"
            )
        return current_user
    return sector_checker


# ============================================================
# 8. التحقق من الأدوار (RBAC)
# ============================================================
def require_roles(roles: List[str]):
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        role_value = current_user.system_role.value if hasattr(current_user.system_role, "value") else current_user.system_role
        if role_value not in roles:
            raise PermissionDeniedError(f"Required roles: {', '.join(roles)}")
        return current_user
    return role_checker


# ============================================================
# 9. دوال مساعدة للتحقق من التوكن في نقاط النهاية العامة
# ============================================================
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    محاولة استخراج المستخدم من التوكن، مع إرجاع None إذا فشل.
    تستخدم في نقاط النهاية التي تسمح للضيوف.
    """
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except (HTTPException, AuthenticationError):
        return None