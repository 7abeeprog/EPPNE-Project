from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError

from app.core.database import get_db
from app.core.security import decode_token
from app.domains.identity.repository import UserRepository
from app.domains.identity.models import User
from fastapi import Header
from typing import Optional
from fastapi import Request

# استيراد خدمة الـ SaaS للتحكم في الاشتراكات
from app.domains.saas.service import SaaSControlService

# التعديل هنا: استخدام HTTPBearer الذي يظهر مربعاً بسيطاً لإدخال التوكن
security = HTTPBearer(auto_error=False)

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security), # قراءة التوكن من Swagger
    cookie_token: Optional[str] = Cookie(None, alias="access_token") # قراءة التوكن من الكوكيز
) -> User:
    # النظام هيستخدم التوكن من الهيدر لو موجود، ولو مش موجود هيدور في الكوكيز
    access_token = auth.credentials if auth else cookie_token
    
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    try:
        payload = decode_token(access_token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    repo = UserRepository(db)
    user = await repo.get_by_id(int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user

async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_superuser(current_user: Annotated[User, Depends(get_current_active_user)]) -> User:
    if current_user.system_role not in ["EXECUTIVE_DIRECTOR", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

# كلاس وهمي سريع لتمثيل المستأجر (الأكاديمية/الشركة) لتجنب تعقيدات الاستيراد المتبادل
class SimpleTenant:
    id: int

async def get_current_tenant(x_tenant_id: int = Header(default=1, alias="X-Tenant-ID")):
    """
    دالة تقوم بجلب رقم المستأجر من الـ Header في الـ API.
    افتراضياً تعطي القيمة 1 لكي يعمل النظام بسلاسة أثناء التطوير.
    """
    tenant = SimpleTenant()
    tenant.id = x_tenant_id
    return tenant

async def get_current_user_optional(request: Request) -> Optional[any]:
    """
    اعتمادية سيادية تسمح بمرور الزوار (الضيوف) دون حظرهم.
    في حال وجود Token سيتم استخراج المستخدم لاحقاً، 
    وإذا لم يوجد سيتم إرجاع None ليتعامل النظام معه كزائر.
    """
    # حالياً نمرر None لتسهيل دخول الضيوف لقمع المبيعات ومحادثة الـ AI
    # (يمكنك لاحقاً تطويرها لفحص الـ Authorization header)
    return None

# ============================================================
# ✅ Dependency محسّنة للتحقق من صلاحية الاشتراك في خدمة معينة
# ============================================================
async def require_subscription(
    service_code: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    ✅ Dependency للتحقق من صلاحية الاشتراك في خدمة معينة.
    الاستخدام: @router.post("/endpoint", dependencies=[Depends(require_subscription("academy"))])
    
    تعتمد هذه الدالة على مستخدم نشط مُصادق، ثم تستدعي خدمة SaaS للتحقق من:
    - وجود اشتراك فعّال للمستأجر (الـ Tenant) في الخدمة المطلوبة.
    - صلاحية الاشتراك من حيث التاريخ والحدود المسموحة (عدد المستخدمين، العمليات، إلخ).
    - في حال عدم توفر الصلاحية، يتم رفع استثناء HTTP 403 مع رسالة توضيحية.
    
    تُستخدم هذه الدالة كـ "Guard" على مستوى الـ endpoint لحماية الموارد الخاصة بالخدمات المدفوعة.
    """
    service = SaaSControlService(db)
    await service.check_and_enforce_access(current_user.tenant_id, service_code)
    return current_user