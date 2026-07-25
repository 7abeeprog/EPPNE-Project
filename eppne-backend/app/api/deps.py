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
        user_id: str = payload.get("sub")
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
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive")
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """التحقق من أن المستخدم نشط."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """التحقق من أن المستخدم لديه صلاحيات السوبر أدمن."""
    allowed_roles = ["EXECUTIVE_DIRECTOR", "SUPER_ADMIN"]
    current_role = getattr(current_user, "system_role", None)
    role_value = current_role.value if hasattr(current_role, "value") else current_role
    if role_value not in allowed_roles:
        raise PermissionDeniedError("عذراً، هذا الإجراء يتطلب صلاحيات المدير التنفيذي.")
    return current_user


# ============================================================
# 🔥 صلاحيات القطاعات (Sector Permissions) - C-01
# ============================================================
def require_sector(sector: str) -> Callable:
    """
    مصنع اعتمادية (Dependency Factory) للتحقق من صلاحية المستخدم للوصول إلى قطاع معين.
    
    الاستخدام:
        @router.get("/finance/balance", dependencies=[Depends(require_sector("finance"))])
    
    يعتمد على أن نموذج `User` يحتوي على حقل `sector` (أو `system_role` يحدد القطاع).
    إذا لم يكن الحقل موجوداً، يمكن استخدام `tenant_id` أو `system_role` لتحديد القطاع.
    """
    async def sector_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        # 🔥 استخراج القطاع من المستخدم (افترض أن User لديه حقل sector)
        user_sector = getattr(current_user, "sector", None)
        if user_sector is None:
            # إذا لم يكن هناك حقل sector، استخدم system_role أو tenant_id
            # هنا نعتبر أن المستخدمين في قطاع معين بناءً على دورهم أو مستأجرهم
            # يمكنك تعديل هذه المنطق حسب هيكل بياناتك الفعلي
            role = getattr(current_user, "system_role", None)
            role_value = role.value if hasattr(role, "value") else role
            # تعيين قطاع افتراضي بناءً على الدور (تعديل حسب الحاجة)
            if role_value in ["EXECUTIVE_DIRECTOR", "SUPER_ADMIN"]:
                user_sector = "all"  # السوبر أدمن لديه صلاحية كل القطاعات
            else:
                # افتراض أن القطاع مستمد من tenant_id أو دور المستخدم
                # هنا يمكنك إضافة منطق مخصص لربط الدور بالقطاع
                user_sector = "academy"  # افتراضي (يجب تعديله)
        
        # السماح للسوبر أدمن بالوصول إلى كل القطاعات
        if user_sector == "all":
            return current_user
        
        # التحقق من أن القطاع المطلوب يطابق قطاع المستخدم
        if user_sector != sector:
            raise PermissionDeniedError(
                f"عذراً، لا تملك صلاحية الوصول إلى قطاع {sector}. قطاعك الحالي: {user_sector}"
            )
        return current_user
    
    return sector_checker


# ============================================================
# 🔥 صلاحيات ضابط الخصوصية (Privacy Officer) - C-04
# ============================================================
async def is_privacy_officer(user: User) -> bool:
    """
    التحقق من أن المستخدم لديه دور PRIVACY_OFFICER.
    يتم استدعاؤها من داخل الـ Dependency.
    """
    # 🔥 إذا كان المستخدم لديه حقل `system_role` من نوع Enum
    role = getattr(user, "system_role", None)
    if role is None:
        return False
    role_value = role.value if hasattr(role, "value") else role
    allowed_roles = ["PRIVACY_OFFICER", "EXECUTIVE_DIRECTOR", "SUPER_ADMIN"]
    return role_value in allowed_roles


async def get_current_privacy_officer(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """
    Dependency للتحقق من أن المستخدم هو ضابط خصوصية أو لديه صلاحيات مشابهة.
    يستخدم في نقاط النهاية المتعلقة بالخصوصية (مثل تصدير البيانات، الموافقات).
    """
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
    """
    استخراج معرف المستأجر من الـ Header.
    القيمة الافتراضية 1 مناسبة للتطوير، لكن في الإنتاج يجب أن تكون إلزامية.
    """
    tenant = SimpleTenant()
    tenant.id = x_tenant_id
    return tenant


async def require_tenant_access(
    current_user: User = Depends(get_current_active_user),
    tenant: SimpleTenant = Depends(get_current_tenant),
) -> User:
    """
    التحقق من أن المستخدم ينتمي إلى نفس المستأجر المطلوب في الـ Header.
    """
    if current_user.tenant_id != tenant.id:
        raise PermissionDeniedError(
            f"عذراً، أنت لا تنتمي إلى المستأجر {tenant.id}. مستأجرك: {current_user.tenant_id}"
        )
    return current_user


# ============================================================
# 📌 صلاحيات الأدوار (RBAC) - موجودة بالفعل
# ============================================================
def require_roles(allowed_roles: List[str]):
    """
    مصنع اعتمادية للتحقق من أن المستخدم لديه دور من القائمة المسموحة.
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)):
        current_role = getattr(current_user, "system_role", None)
        role_value = current_role.value if hasattr(current_role, "value") else current_role
        if not role_value or role_value not in allowed_roles:
            raise PermissionDeniedError("عذراً، لا تملك الصلاحيات الكافية.")
        return current_user
    return role_checker


async def get_current_instructor_or_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    التحقق من أن المستخدم مدرب أو إداري.
    """
    allowed_roles = ["INSTRUCTOR", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR", "ADMIN"]
    current_role = getattr(current_user, "system_role", None)
    role_value = current_role.value if hasattr(current_role, "value") else current_role
    if role_value not in allowed_roles:
        raise PermissionDeniedError("عذراً، هذا الإجراء مخصص للمدربين والإدارة فقط.")
    return current_user


# ============================================================
# 📌 صلاحية الاشتراك (Subscription) - موجودة بالفعل
# ============================================================
def require_subscription(service_code: str):
    """
    مصنع اعتمادية للتحقق من أن المستأجر لديه اشتراك فعال في خدمة معينة.
    """
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
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    محاولة استخراج المستخدم من التوكن، مع إرجاع None إذا لم يكن موجوداً.
    تستخدم في نقاط النهاية التي تسمح للضيوف (مثل محادثة AI).
    """
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
        return user if user and user.is_active else None
    except (JWTError, ExpiredSignatureError, ValueError):
        return None