# app/domains/auth/router.py
from fastapi import APIRouter, Depends, Request, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, cast
import json

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant
from app.domains.identity.models import User
from app.domains.auth.service import AuthService
from app.domains.auth.schemas import *
from app.core.rate_limiter import rate_limit
from app.core.redis_client import redis_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Sovereign Authentication"])


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
@rate_limit(max_requests=10, window_seconds=60)
async def login(
    data: LoginRequest,
    request: Request,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db, tenant_id)
    try:
        user = await service.authenticate_user(data.username, data.password)
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")
        result = await service.create_session(
            user=user,
            device_name=data.device_name,
            ip_address=ip,
            user_agent=ua
        )
        logger.info(f"User {user.id} logged in successfully")
        return result
    except Exception as e:
        logger.warning(f"Login failed for {data.username}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


@router.post("/refresh", response_model=RefreshTokenResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def refresh_access_token(
    data: RefreshTokenRequest,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db, tenant_id)
    try:
        result = await service.refresh_access_token(data.refresh_token)
        logger.info("Access token refreshed successfully")
        return result
    except Exception as e:
        logger.warning(f"Refresh token failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit(max_requests=20, window_seconds=60)
async def logout(
    data: LogoutRequest,
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db, tenant_id)
    revoked = await service.revoke_session(
        user_id=cast(int, current_user.id),
        refresh_token=data.refresh_token
    )
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refresh token not found or already revoked")
    await redis_client.delete(f"user:{current_user.id}:{tenant_id}")
    logger.info(f"User {current_user.id} logged out from device")
    return None


@router.post("/revoke-all", status_code=status.HTTP_200_OK, response_model=RevokeAllSessionsResponse)
@rate_limit(max_requests=5, window_seconds=300)
async def revoke_all_sessions(
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db, tenant_id)
    revoked_count = await service.revoke_all_sessions(user_id=cast(int, current_user.id))
    await redis_client.delete(f"user:{current_user.id}:{tenant_id}")
    logger.info(f"User {current_user.id} revoked all sessions ({revoked_count} tokens)")
    return {"message": "تم إبطال جميع الجلسات بنجاح", "revoked_count": revoked_count}


@router.get("/sessions", response_model=List[SessionInfoResponse])
@rate_limit(max_requests=10, window_seconds=60)
async def get_active_sessions(
    current_user: User = Depends(get_current_active_user),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    service = AuthService(db, tenant_id)
    tokens = await service.get_active_sessions(user_id=cast(int, current_user.id), skip=skip, limit=limit)
    return [
        {
            "id": t.id,
            "device_name": t.device_name,
            "ip_address": t.ip_address,
            "user_agent": t.user_agent,
            "created_at": t.created_at,
            "expires_at": t.expires_at,
            "is_active": not cast(bool, t.revoked) and not t.is_expired()
        }
        for t in tokens
    ]