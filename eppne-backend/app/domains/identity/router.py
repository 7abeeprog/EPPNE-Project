# app/domains/identity/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.domains.identity.schemas import UserCreate, UserResponse, UserLogin, UserUpdate
from app.domains.identity.service import UserService
from app.api.deps import get_current_user
from app.core.rate_limiter import rate_limit
from app.core.config import settings
from app.core.logging_conf import logger
import uuid

router = APIRouter(prefix="/identity", tags=["Sovereign Identity"])

# ✅ معدل الطلبات (حماية من الهجمات)
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)  # 10 طلبات في الدقيقة
async def register(
    user_in: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    إنشاء حساب جديد مع Idempotency Key (يُولد في الفرونت إند).
    🔥 معدل الطلبات: 10 طلبات لكل 60 ثانية (حماية من الهجمات).
    """
    service = UserService(db)

    # ✅ استخراج Idempotency Key من الهيدر
    idempotency_key = request.headers.get("X-Idempotency-Key")
    if not idempotency_key:
        # يمكن توليده تلقائياً، لكن يُفضل أن يُرسل من الفرونت إند
        idempotency_key = f"REG-{uuid.uuid4().hex[:12].upper()}"

    try:
        user = await service.register(user_in, idempotency_key)
        return user
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login")
@rate_limit(max_requests=20, window_seconds=60)  # 20 طلبات في الدقيقة
async def login(
    response: Response,
    request: Request,
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    تسجيل الدخول مع HttpOnly Cookies.
    🔥 معدل الطلبات: 20 طلب لكل 60 ثانية (حماية من هجمات القوة العمياء).
    """
    service = UserService(db)

    # ✅ تمرير IP و User-Agent لتحديث آخر تسجيل دخول
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    user = await service.authenticate(
        login_data.username_or_email,
        login_data.password.get_secret_value(),
        ip=ip,
        user_agent=ua
    )

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="بيانات الدخول غير صحيحة")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="الحساب غير نشط")

    tokens = await service.generate_tokens(user)

    # ✅ إعداد ملفات تعريف الارتباط مع secure=True في الإنتاج
    secure_flag = settings.ENVIRONMENT == "production"

    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=secure_flag,
        samesite="strict",
        max_age=15 * 60  # 15 دقيقة
    )

    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=secure_flag,
        samesite="strict",
        max_age=7 * 24 * 60 * 60  # 7 أيام
    )

    return {
        "message": "تم تسجيل الدخول بنجاح",
        "user_id": user.id,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "system_role": user.system_role.value,
            "sovereign_rank": user.sovereign_rank.value,
        }
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_me(
    user_in: UserUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = UserService(db)
    return await service.update_user(current_user.id, user_in)


@router.post("/logout")
@rate_limit(max_requests=20, window_seconds=60)
async def logout(request: Request, response: Response): # 👈 تمت إضافة request هنا
    """
    تسجيل الخروج مع تدمير الكوكيز.
    🔥 معدل الطلبات: 20 طلب لكل 60 ثانية.
    """
    response.delete_cookie("access_token", path="/", samesite="strict")
    response.delete_cookie("refresh_token", path="/", samesite="strict")
    return {"message": "تم تسجيل الخروج وتدمير الجلسة بنجاح"}

@router.post("/refresh")
@rate_limit(max_requests=15, window_seconds=60)
async def refresh_token_endpoint(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    تجديد Access Token باستخدام Refresh Token (مع Token Rotation).
    🔥 معدل الطلبات: 15 طلب لكل 60 ثانية.
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="توكن التجديد مفقود")

    service = UserService(db)

    try:
        new_tokens = await service.refresh_tokens(refresh_token)

        secure_flag = settings.ENVIRONMENT == "production"

        response.set_cookie(
            key="access_token",
            value=new_tokens["access_token"],
            httponly=True,
            secure=secure_flag,
            samesite="strict",
            max_age=15 * 60
        )

        response.set_cookie(
            key="refresh_token",
            value=new_tokens["refresh_token"],
            httponly=True,
            secure=secure_flag,
            samesite="strict",
            max_age=7 * 24 * 60 * 60
        )

        return {"message": "تم تجديد الصلاحية بنجاح"}

    except Exception as e:
        logger.warning(f"Refresh token failed: {str(e)}")
        response.delete_cookie("access_token", path="/", samesite="strict")
        response.delete_cookie("refresh_token", path="/", samesite="strict")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="انتهت صلاحية الجلسة، يرجى تسجيل الدخول مجدداً"
        )


@router.post("/revoke-all")
@rate_limit(max_requests=5, window_seconds=300)  # 5 طلبات لكل 5 دقائق
async def revoke_all_sessions(
    request: Request, # 👈 تمت إضافة request هنا
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    إبطال جميع جلسات المستخدم (تسجيل الخروج من جميع الأجهزة).
    🔥 معدل الطلبات: 5 طلبات لكل 5 دقائق (لحماية من الإساءة).
    """
    service = UserService(db)
    revoked_count = await service.revoke_all_sessions(current_user.id)
    return {
        "message": f"تم إبطال جميع الجلسات ({revoked_count} جلسة)",
        "revoked_count": revoked_count
    }