# app/domains/projects/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, cast

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant
from app.domains.identity.models import User
from app.domains.projects.service import ProjectService
from app.domains.projects.schemas import *
from app.domains.projects.models import ProjectType, ProjectStatus
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit
from app.core.pagination import PaginatedResponse

router = APIRouter(prefix="/projects", tags=["Sovereign Projects & Crowdfunding"])

# ==========================================
# 1. إدارة المشاريع (CRUD)
# ==========================================

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_project(
    request: Request,
    data: ProjectCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    user_id = cast(int, current_user.id)
    return await service.create_project(owner_id=user_id, tenant_id=cast(int, tenant.id), data=data)


@router.get("/products", response_model=PaginatedResponse)
async def list_products(
    store_id: int,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    return await service.list_products(store_id, skip, min(limit, 200))


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    return await service.get_project(project_id, cast(int, tenant.id))


@router.put("/{project_id}", response_model=ProjectResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def update_project(
    request: Request,
    project_id: int,
    data: ProjectUpdate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    user_id = cast(int, current_user.id)
    return await service.update_project(
        project_id, cast(int, tenant.id), user_id, data.model_dump(exclude_unset=True)
    )


@router.post("/{project_id}/publish", response_model=ProjectResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def publish_project(
    request: Request,
    project_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    user_id = cast(int, current_user.id)
    return await service.publish_project(project_id, user_id, cast(int, tenant.id))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit(max_requests=10, window_seconds=60)
async def delete_project(
    request: Request,
    project_id: int,
    soft: bool = True,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    user_id = cast(int, current_user.id)
    await service.delete_project(project_id, cast(int, tenant.id), user_id, soft=soft)
    return None


# ==========================================
# 2. قوائم المشاريع (Listings)
# ==========================================

@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    project_type: Optional[ProjectType] = None,
    status: Optional[ProjectStatus] = None,
    country: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    return await service.list_projects(
        cast(int, tenant.id),
        project_type.value if project_type else None,
        status.value if status else None,
        country,
        skip,
        min(limit, 200)
    )


# ==========================================
# 3. المساهمات (Contributions)
# ==========================================

@router.post("/contributions", response_model=dict, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=20, window_seconds=60)
async def add_contribution(
    request: Request,
    data: ContributionCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    user_id = cast(int, current_user.id)
    return await service.add_contribution(user_id, cast(int, tenant.id), data, idempotency_key)


@router.get("/contributions/{contribution_id}", response_model=ContributionResponse)
async def get_contribution(
    contribution_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    return await service.get_contribution(contribution_id, cast(int, tenant.id))


@router.post("/contributions/{contribution_id}/approve", response_model=ContributionResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def approve_contribution(
    request: Request,
    contribution_id: int,
    approve_data: ContributionApprove,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    user_id = cast(int, current_user.id)
    return await service.approve_contribution(
        contribution_id, user_id, cast(int, tenant.id), approve_data.approved, approve_data.notes
    )


# ==========================================
# 4. المراحل (Milestones)
# ==========================================

@router.post("/{project_id}/milestones", response_model=MilestoneResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def add_milestone(
    request: Request,
    project_id: int,
    data: MilestoneCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    user_id = cast(int, current_user.id)
    return await service.add_milestone(project_id, user_id, cast(int, tenant.id), data)


@router.post("/milestones/{milestone_id}/complete", response_model=MilestoneResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def complete_milestone(
    request: Request,
    milestone_id: int,
    complete_data: MilestoneComplete,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    user_id = cast(int, current_user.id)
    return await service.complete_milestone(milestone_id, user_id, cast(int, tenant.id), complete_data)


@router.get("/{project_id}/milestones", response_model=list[MilestoneResponse])
async def get_milestones(
    project_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    return await service.get_milestones(project_id, cast(int, tenant.id))


# ==========================================
# 5. المتابعة (Follow)
# ==========================================

@router.post("/{project_id}/follow", response_model=FollowResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def follow_project(
    request: Request,
    project_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    user_id = cast(int, current_user.id)
    await service.follow_project(user_id, project_id, cast(int, tenant.id))
    return {"user_id": user_id, "project_id": project_id, "created_at": datetime.utcnow()}


@router.delete("/{project_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit(max_requests=20, window_seconds=60)
async def unfollow_project(
    request: Request,
    project_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    user_id = cast(int, current_user.id)
    await service.unfollow_project(user_id, project_id, cast(int, tenant.id))
    return None


@router.get("/{project_id}/followers", response_model=list[dict])
async def get_followers(
    project_id: int,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    return await service.get_followers(project_id, cast(int, tenant.id), skip, min(limit, 200))


# ==========================================
# 6. تحديثات المشروع (Updates)
# ==========================================

@router.post("/{project_id}/updates", response_model=ProjectUpdateResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def add_project_update(
    request: Request,
    project_id: int,
    data: ProjectUpdateCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    user_id = cast(int, current_user.id)
    return await service.add_project_update(
        project_id, user_id, cast(int, tenant.id), data.title, data.content, data.media_urls
    )


@router.get("/{project_id}/updates", response_model=list[ProjectUpdateResponse])
async def get_project_updates(
    project_id: int,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    return await service.get_project_updates(project_id, cast(int, tenant.id), skip, min(limit, 200))


# ==========================================
# 7. التحليلات
# ==========================================

@router.get("/{project_id}/analytics", response_model=ProjectAnalyticsResponse)
async def get_analytics(
    project_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    analytics = await service.get_project_analytics(project_id, cast(int, tenant.id))
    return ProjectAnalyticsResponse(**analytics)