# app/api/deps.py
from typing import Optional, Annotated, List, Callable, Any
from fastapi import Depends, HTTPException, status, Cookie, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, ExpiredSignatureError

from app.core.database import get_db
from app.core.security import decode_token
from app.core.errors import PermissionDeniedError, NotFoundError
from app.domains.identity.repository import UserRepository
from app.domains.identity.models import User
from app.domains.saas.service import SaaSControlService


# ============================================================
# 📌 مصادقة التوكن (JWT)
# ============================================================
security = HTTPBearer(auto_error=False)

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    cookie_token: Optional[str] = Cookie(None, alias="access_token")
) -> User:
    """
    استخراج المستخدم الحالي من التوكن (يدعم Header و Cookie).
    - يرفع 401 إذا كان التوكن غير صالح أو منتهي الصلاحية.
    """
    access_token = auth.credentials if auth else cookie_token
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = decode_token(access_token)
        user_id: str = payload.get("sub")  # type: ignore
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token (missing subject)")
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    repo = UserRepository(db)
    user = await repo.get_by_id(int(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:  # type: ignore
        raise HTTPException(status_code=401, detail="User is inactive")
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """التحقق من أن المستخدم نشط."""
    if not current_user.is_active:  # type: ignore
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """التحقق من أن المستخدم لديه صلاحيات السوبر أدمن."""
    allowed_roles = ["EXECUTIVE_DIRECTOR", "SUPER_ADMIN"]
    current_role = getattr(current_user, "system_role", None)
    # ✅ إصلاح الخطأ: التحقق من None قبل الوصول إلى value
    if current_role is not None:
        role_value = current_role.value if hasattr(current_role, "value") else current_role
    else:
        role_value = None
    if role_value not in allowed_roles:  # type: ignore
        raise PermissionDeniedError("عذراً، هذا الإجراء يتطلب صلاحيات المدير التنفيذي.")
    return current_user


# ============================================================
# 🔥 صلاحيات القطاعات (Sector Permissions) - C-01
# ============================================================
def require_sector(sector: str) -> Callable:
    """
    مصنع اعتمادية (Dependency Factory) للتحقق من صلاحية المستخدم للوصول إلى قطاع معين.
    """
    async def sector_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        user_sector = getattr(current_user, "sector", None)
        if user_sector is None:
            role = getattr(current_user, "system_role", None)
            # ✅ إصلاح الخطأ: التحقق من None قبل الوصول إلى value
            if role is not None:
                role_value = role.value if hasattr(role, "value") else role
            else:
                role_value = None
            if role_value in ["EXECUTIVE_DIRECTOR", "SUPER_ADMIN"]:
                user_sector = "all"
            else:
                user_sector = "academy"
        
        if user_sector == "all":
            return current_user
        
        if user_sector != sector:  # type: ignore
            raise PermissionDeniedError(
                f"عذراً، لا تملك صلاحية الوصول إلى قطاع {sector}. قطاعك الحالي: {user_sector}"
            )
        return current_user
    
    return sector_checker


# ============================================================
# 🔥 صلاحيات ضابط الخصوصية (Privacy Officer) - C-04
# ============================================================
async def is_privacy_officer(user: User) -> bool:
    role = getattr(user, "system_role", None)
    if role is None:
        return False
    # ✅ إصلاح الخطأ: التحقق من None قبل الوصول إلى value
    role_value = role.value if hasattr(role, "value") else role
    allowed_roles = ["PRIVACY_OFFICER", "EXECUTIVE_DIRECTOR", "SUPER_ADMIN"]
    return role_value in allowed_roles  # type: ignore


async def get_current_privacy_officer(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    if not await is_privacy_officer(current_user):
        raise PermissionDeniedError(
            "عذراً، هذا الإجراء يتطلب صلاحيات ضابط الخصوصية."
        )
    return current_user


# ============================================================
# 🔥 التحقق من المستأجر (Tenant)
# ============================================================
class SimpleTenant:
    id: int


async def get_current_tenant(
    x_tenant_id: int = Header(default=1, alias="X-Tenant-ID")
) -> SimpleTenant:
    tenant = SimpleTenant()
    tenant.id = x_tenant_id
    return tenant


async def require_tenant_access(
    current_user: User = Depends(get_current_active_user),
    tenant: SimpleTenant = Depends(get_current_tenant),
) -> User:
    if current_user.tenant_id != tenant.id:
        raise PermissionDeniedError(
            f"عذراً، أنت لا تنتمي إلى المستأجر {tenant.id}. مستأجرك: {current_user.tenant_id}"
        )
    return current_user


# ============================================================
# 📌 صلاحيات الأدوار (RBAC)
# ============================================================
def require_roles(allowed_roles: List[str]):
    async def role_checker(current_user: User = Depends(get_current_active_user)):
        current_role = getattr(current_user, "system_role", None)
        # ✅ إصلاح الخطأ: التحقق من None قبل الوصول إلى value
        if current_role is not None:
            role_value = current_role.value if hasattr(current_role, "value") else current_role
        else:
            role_value = None
        if not role_value or role_value not in allowed_roles:  # type: ignore
            raise PermissionDeniedError("عذراً، لا تملك الصلاحيات الكافية.")
        return current_user
    return role_checker


async def get_current_instructor_or_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    allowed_roles = ["INSTRUCTOR", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR", "ADMIN"]
    current_role = getattr(current_user, "system_role", None)
    # ✅ إصلاح الخطأ: التحقق من None قبل الوصول إلى value
    if current_role is not None:
        role_value = current_role.value if hasattr(current_role, "value") else current_role
    else:
        role_value = None
    if role_value not in allowed_roles:  # type: ignore
        raise PermissionDeniedError("عذراً، هذا الإجراء مخصص للمدربين والإدارة فقط.")
    return current_user


# ============================================================
# 📌 صلاحية الاشتراك (Subscription)
# ============================================================
def require_subscription(service_code: str):
    async def subscription_checker(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ):
        service = SaaSControlService(db)
        await service.check_and_enforce_access(current_user.tenant_id, service_code)
        return current_user
    return subscription_checker


# ============================================================
# 📌 مستخدم اختياري (للضيوف)
# ============================================================
async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        repo = UserRepository(db)
        user = await repo.get_by_id(int(user_id))
        return user if user and user.is_active else None  # type: ignore
    except (JWTError, ExpiredSignatureError, ValueError):
        return None