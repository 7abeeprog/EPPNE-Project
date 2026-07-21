# app/domains/translation/router.py (الإصدار النهائي المتكامل)
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, cast

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant
from app.domains.identity.models import User
from app.domains.translation.service import TranslationService
from app.domains.translation.schemas import *
from app.domains.academy.models import AcademyTenant

router = APIRouter(prefix="/translation", tags=["Universal Translation"])


@router.post("/translate", response_model=TranslateResponse)
async def translate_text(
    request: Request,
    body: TranslateRequest,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = TranslationService(db)
    user_id = cast(int, current_user.id)
    return await service.translate(
        cast(int, tenant.id), user_id, body,  # ✅ cast
        ip=client_ip, ua=user_agent
    )


@router.post("/batch-translate", response_model=List[str])
async def batch_translate(
    request: Request,
    body: BatchTranslateRequest,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = TranslationService(db)
    user_id = cast(int, current_user.id)
    return await service.batch_translate(
        cast(int, tenant.id), user_id, body,  # ✅ cast
        ip=client_ip, ua=user_agent
    )


@router.post("/chat-translate", response_model=ChatTranslateResponse)
async def chat_translate(
    request: Request,
    body: ChatTranslateRequest,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    service = TranslationService(db)
    user_id = cast(int, current_user.id)
    return await service.chat_translate(
        cast(int, tenant.id), user_id, body,  # ✅ cast
        ip=client_ip, ua=user_agent
    )


@router.get("/languages", response_model=List[SupportedLanguageResponse])
async def get_supported_languages(
    db: AsyncSession = Depends(get_db)
):
    service = TranslationService(db)
    return await service.get_supported_languages()