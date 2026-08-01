# app/domains/identity/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import cast
import uuid
from pydantic import BaseModel, SecretStr

from app.core.database import get_db
from app.domains.identity.schemas import UserCreate, UserResponse, UserLogin, UserUpdate
from app.domains.identity.service import UserService
from app.api.deps import get_current_user, get_current_tenant
from app.core.rate_limiter import rate_limit
from app.core.config import settings
from app.core.logging_conf import logger
from app.domains.identity.models import User

router = APIRouter(prefix="/identity", tags=["Sovereign Identity"])

class ChangePasswordRequest(BaseModel):
    old_password: SecretStr
    new_password: SecretStr

class DeleteAccountRequest(BaseModel):
    password: SecretStr

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def register(user_in: UserCreate, request: Request, tenant_id: int = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    service = UserService(db, tenant_id)
    idempotency_key = request.headers.get("X-Idempotency-Key") or f"REG-{uuid.uuid4().hex[:12].upper()}"
    try:
        user = await service.register(user_in, idempotency_key)
        return user
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login")
@rate_limit(max_requests=20, window_seconds=60)
async def login(response: Response, request: Request, login_data: UserLogin, tenant_id: int = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    service = UserService(db, tenant_id)
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    user = await service.authenticate(login_data.username_or_email, login_data.password.get_secret_value(), ip=ip, user_agent=ua)
    if not user or not user.is_active:  # type: ignore
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="بيانات الدخول غير صحيحة")
    
    tokens = await service.generate_tokens(user)
    secure_flag = settings.ENVIRONMENT == "production"
    response.set_cookie("access_token", tokens["access_token"], httponly=True, secure=secure_flag, samesite="strict", max_age=15*60)
    response.set_cookie("refresh_token", tokens["refresh_token"], httponly=True, secure=secure_flag, samesite="strict", max_age=7*24*60*60)
    return {"access_token": tokens["access_token"], "token_type": "bearer", "message": "تم تسجيل الدخول بنجاح", "user_id": cast(int, user.id), "user": user}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user), tenant_id: int = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    service = UserService(db, tenant_id)
    return await service.get_current_user(user_id=cast(int, current_user.id))

@router.put("/me", response_model=UserResponse)
async def update_me(user_in: UserUpdate, current_user: User = Depends(get_current_user), tenant_id: int = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    service = UserService(db, tenant_id)
    return await service.update_user(user_id=cast(int, current_user.id), data=user_in)

@router.post("/logout")
@rate_limit(max_requests=20, window_seconds=60)
async def logout(request: Request, response: Response, tenant_id: int = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            service = UserService(db, tenant_id)
            await service.revoke_specific_refresh_token(refresh_token)
        except Exception as e:
            logger.warning(f"Failed to revoke refresh token: {str(e)}")
    response.delete_cookie("access_token", path="/", samesite="strict")
    response.delete_cookie("refresh_token", path="/", samesite="strict")
    return {"message": "تم تسجيل الخروج وتدمير الجلسة وإبطال التوكن بنجاح"}

@router.post("/refresh")
@rate_limit(max_requests=15, window_seconds=60)
async def refresh_token_endpoint(request: Request, response: Response, tenant_id: int = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="توكن التجديد مفقود")
    service = UserService(db, tenant_id)
    try:
        new_tokens = await service.refresh_tokens(refresh_token)
        secure_flag = settings.ENVIRONMENT == "production"
        response.set_cookie("access_token", new_tokens["access_token"], httponly=True, secure=secure_flag, samesite="strict", max_age=15*60)
        response.set_cookie("refresh_token", new_tokens["refresh_token"], httponly=True, secure=secure_flag, samesite="strict", max_age=7*24*60*60)
        return {"message": "تم تجديد الصلاحية بنجاح"}
    except Exception as e:
        logger.warning(f"Refresh token failed: {str(e)}")
        response.delete_cookie("access_token", path="/", samesite="strict")
        response.delete_cookie("refresh_token", path="/", samesite="strict")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="انتهت صلاحية الجلسة، يرجى تسجيل الدخول مجدداً")

@router.post("/revoke-all")
@rate_limit(max_requests=5, window_seconds=300)
async def revoke_all_sessions(request: Request, current_user: User = Depends(get_current_user), tenant_id: int = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    service = UserService(db, tenant_id)
    revoked_count = await service.revoke_all_sessions(user_id=cast(int, current_user.id))
    return {"message": f"تم إبطال جميع الجلسات ({revoked_count} جلسة)", "revoked_count": revoked_count}

@router.put("/me/password", status_code=status.HTTP_200_OK)
@rate_limit(max_requests=10, window_seconds=300)
async def change_password(request_data: ChangePasswordRequest, current_user: User = Depends(get_current_user), tenant_id: int = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    service = UserService(db, tenant_id)
    success = await service.change_password(user_id=cast(int, current_user.id), old_password=request_data.old_password.get_secret_value(), new_password=request_data.new_password.get_secret_value())
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="فشل تغيير كلمة المرور")
    return {"message": "تم تغيير كلمة المرور بنجاح، سيتم إبطال جميع الجلسات الحالية"}

@router.delete("/me", status_code=status.HTTP_200_OK)
@rate_limit(max_requests=3, window_seconds=300)
async def soft_delete_account(request_data: DeleteAccountRequest, current_user: User = Depends(get_current_user), tenant_id: int = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    service = UserService(db, tenant_id)
    success = await service.soft_delete_account(user_id=cast(int, current_user.id), password=request_data.password.get_secret_value())
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="فشل حذف الحساب")
    return {"message": "تم تعطيل الحساب وإبطال جميع الجلسات بنجاح.", "account_status": "disabled"}