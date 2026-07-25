# app/core/security.py
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext

from app.core.config import settings
from app.core.database import get_db
from app.domains.identity.models import User
from app.domains.identity.repository import UserRepository
from app.core.logging_conf import logger
from app.core.errors import AuthenticationError, PermissionDeniedError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 🔥 auto_error=False للسماح بنقاط النهاية العامة (مثل الصحة)
security = HTTPBearer(auto_error=False)


# ============================================================
# 1. دوال التجزئة والمصادقة (Password Hashing)
# ============================================================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# ============================================================
# 2. إنشاء وتوقيع التوكنات (JWT)
# ============================================================
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    إنشاء توكن وصول (Access Token) مع إضافة `tenant_id` و `sector` إلى الـ Payload.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "typ": "access",
        "tenant_id": data.get("tenant_id"),  # 🔥 إضافة tenant_id
        "sector": data.get("sector"),        # 🔥 إضافة sector
    })
    return jwt.encode(to_encode, settings.SECRET_KEY.get_secret_value(), algorithm=settings.ALGORITHM)


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    إنشاء توكن تحديث (Refresh Token) مع معلومات الجلسة.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "typ": "refresh",
        "tenant_id": data.get("tenant_id"),
        "sector": data.get("sector"),
    })
    return jwt.encode(to_encode, settings.SECRET_KEY.get_secret_value(), algorithm=settings.ALGORITHM)


# ============================================================
# 3. فك تشفير التوكن والتحقق من صلاحيته
# ============================================================
def decode_token(token: str) -> Dict[str, Any]:
    """
    فك تشفير التوكن والتحقق من صلاحيته.
    يرفع `ExpiredSignatureError` إذا كان منتهي الصلاحية.
    يرفع `JWTError` إذا كان غير صالح.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except ExpiredSignatureError:
        logger.warning("⚠️ Token expired")
        raise
    except JWTError as e:
        logger.warning(f"⚠️ Invalid token: {e}")
        raise


def encrypt_ip(ip: str) -> str:
    """تشفير عنوان IP لتخزينه في السجلات بشكل آمن."""
    if not ip:
        return ""
    return hashlib.sha256((ip + settings.SECRET_KEY.get_secret_value()).encode()).hexdigest()


# ============================================================
# 4. اعتماديات المصادقة (Authentication Dependencies)
# ============================================================
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    استخراج المستخدم الحالي من التوكن مع التحقق من:
    - صحة التوكن وعدم انتهاء صلاحيته.
    - أن المستخدم موجود ونشط.
    - أن جلسة المستخدم لم تُلغَ (session_version).
    - أن المستخدم ينتمي إلى نفس المستأجر المذكور في التوكن.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # التحقق من نوع التوكن (يجب أن يكون access)
    if payload.get("typ") != "access":
        raise AuthenticationError("Invalid token type (must be access token)")

    user_id = payload.get("sub")
    token_session_version = payload.get("sv")
    token_tenant_id = payload.get("tenant_id")
    token_sector = payload.get("sector")

    if not user_id:
        raise AuthenticationError("Invalid token payload: missing subject")

    # جلب المستخدم من قاعدة البيانات
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(int(user_id))

    if not user:
        raise AuthenticationError("User not found")
    if not user.is_active:
        raise AuthenticationError("User is inactive")

    # 🔥 التحقق من أن المستخدم ينتمي إلى نفس المستأجر الموجود في التوكن
    if token_tenant_id is not None and user.tenant_id != token_tenant_id:
        logger.warning(f"⚠️ Tenant mismatch: token={token_tenant_id}, user={user.tenant_id}")
        raise AuthenticationError("Tenant mismatch")

    # 🔥 التحقق من أن جلسة المستخدم لم تُلغَ
    if user.session_version != token_session_version:
        raise AuthenticationError("Session has been revoked")

    # تخزين الـ sector و tenant_id في حالة الطلب لاستخدامهما في الـ Dependencies
    user._sector = token_sector  # إضافة حقل مؤقت للاستخدام الداخلي
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """التحقق من أن المستخدم نشط."""
    if not current_user.is_active:
        raise AuthenticationError("User is inactive")
    return current_user


# ============================================================
# 5. صلاحيات السوبر أدمن والمدير التنفيذي
# ============================================================
async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """التحقق من أن المستخدم لديه صلاحيات السوبر أدمن."""
    allowed_roles = ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]
    role_value = current_user.system_role.value if hasattr(current_user.system_role, "value") else current_user.system_role
    if role_value not in allowed_roles:
        raise PermissionDeniedError("Superuser privileges required")
    return current_user


# ============================================================
# 6. صلاحيات ضابط الخصوصية (Privacy Officer) - إصلاح C-04
# ============================================================
async def is_privacy_officer(user: User) -> bool:
    """
    التحقق الفعلي من أن المستخدم لديه دور PRIVACY_OFFICER.
    يستخدم Enum للمقارنة الآمنة.
    """
    # 🔥 استخراج قيمة الدور من Enum (إن وجد)
    role = getattr(user, "system_role", None)
    if role is None:
        return False
    role_value = role.value if hasattr(role, "value") else role
    allowed_roles = ["PRIVACY_OFFICER", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]
    return role_value in allowed_roles


async def get_privacy_officer(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Dependency للتحقق من أن المستخدم هو ضابط خصوصية.
    تستخدم في نقاط النهاية الحساسة (مثل تصدير البيانات، الموافقات).
    """
    if not await is_privacy_officer(current_user):
        raise PermissionDeniedError("Privacy Officer permissions required")
    return current_user


# ============================================================
# 7. 🔥 صلاحيات القطاعات (Sector Permissions) - C-01
# ============================================================
def require_sector(sector: str):
    """
    مصنع اعتمادية (Dependency Factory) للتحقق من أن المستخدم ينتمي إلى قطاع معين.
    يعتمد على حقل `sector` المخزن في التوكن (يُضاف أثناء إنشاء التوكن).
    
    الاستخدام:
        @router.get("/finance/balance", dependencies=[Depends(require_sector("finance"))])
    """
    async def sector_checker(current_user: User = Depends(get_current_active_user)):
        # 🔥 استخراج القطاع من التوكن (المخزن في الحقل المؤقت `_sector`)
        user_sector = getattr(current_user, "_sector", None)
        
        # إذا كان المستخدم سوبر أدمن، نسمح له بالوصول إلى كل القطاعات
        role_value = current_user.system_role.value if hasattr(current_user.system_role, "value") else current_user.system_role
        if role_value in ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]:
            return current_user
        
        if user_sector is None:
            # إذا لم يكن هناك قطاع في التوكن، نستخدم القيمة الافتراضية (أو نرفع خطأ)
            # يمكنك تعديل هذا حسب منطق عملك
            user_sector = "academy"  # افتراضي
        
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
    """
    مصنع اعتمادية للتحقق من أن المستخدم لديه دور من القائمة.
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)):
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
    محاولة استخراج المستخدم من التوكن مع إرجاع None إذا فشل.
    تستخدم في نقاط النهاية التي تسمح للضيوف (مثل محادثة AI).
    """
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except (HTTPException, AuthenticationError):
        return None