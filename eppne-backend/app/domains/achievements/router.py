# app/domains/achievements/router.py
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, cast

from app.core.database import get_db
from app.core.security import get_current_active_user, get_current_superuser
from app.domains.identity.models import User
from app.domains.achievements.service import AchievementService
from app.domains.achievements.schemas import (
    AchievementDefinitionCreate,
    AchievementDefinitionResponse,
    AchievementGrantRequest,
    UserAchievementResponse,
    AchievementCategoryStatItem,
    AchievementTopUserItem,
    AchievementDefinitionStatItem,
)

router = APIRouter(prefix="/achievements", tags=["Achievements"])


# ============================================================
# 1. تعريفات الإنجازات (Admin)
# ============================================================

@router.post(
    "/definitions",
    response_model=AchievementDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_achievement_definition(
    data: AchievementDefinitionCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = AchievementService(db, tenant_id)
    return await service.create_definition(data, created_by=cast(int, current_user.id))


@router.get("/definitions", response_model=List[AchievementDefinitionResponse])
async def list_achievement_definitions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = AchievementService(db, tenant_id)
    return await service.list_definitions()


# ============================================================
# 2. المنح اليدوي (Admin)
# ============================================================

@router.post(
    "/grant",
    response_model=UserAchievementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def grant_achievement(
    data: AchievementGrantRequest,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = AchievementService(db, tenant_id)
    return await service.grant_achievement(
        user_id=data.user_id,
        achievement_definition_id=data.achievement_definition_id,
        granted_by=cast(int, current_user.id),
    )


# ============================================================
# 3. إنجازات مستخدم معيّن
# ============================================================

@router.get("/users/{user_id}", response_model=List[UserAchievementResponse])
async def get_user_achievements(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = AchievementService(db, tenant_id)
    return await service.get_user_achievements(user_id)


# ============================================================
# 4. إحصائيات (Admin)
# ============================================================

@router.get("/stats/by-category", response_model=List[AchievementCategoryStatItem])
async def get_achievements_stats_by_category(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = AchievementService(db, tenant_id)
    return await service.get_stats_by_category()


@router.get("/stats/top-users", response_model=List[AchievementTopUserItem])
async def get_achievements_stats_top_users(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = AchievementService(db, tenant_id)
    return await service.get_top_users(limit)


@router.get("/stats/by-definition", response_model=List[AchievementDefinitionStatItem])
async def get_achievements_stats_by_definition(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = cast(int, current_user.tenant_id)
    service = AchievementService(db, tenant_id)
    return await service.get_stats_by_definition()
