# app/domains/projects/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant
from app.domains.identity.models import User
from app.domains.projects.service import ProjectService
from app.domains.projects.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit
from app.core.pagination import PaginatedResponse
from app.domains.commerce.repository import CommerceRepository

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
    return await service.create_project(owner_id=current_user.id, tenant_id=tenant.id, data=data)

@router.get("/products", response_model=PaginatedResponse[ProjectResponse])
async def list_products(
    store_id: int,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    repo = CommerceRepository(db)
    return await repo.get_products_by_store(store_id, skip, limit)

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
    project = await service.repo.get_project(project_id, tenant.id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return await service.repo.update_project(project_id, tenant.id, **data.model_dump(exclude_unset=True))

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
    return await service.publish_project(project_id, current_user.id, tenant.id)

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
    project = await service.repo.get_project(project_id, tenant.id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    await service.repo.delete_project(project_id, tenant.id, soft=soft)
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
    return await service.repo.list_projects(tenant.id, project_type, status, country, skip, min(limit, 200))

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
    return await service.add_contribution(current_user.id, tenant.id, data, idempotency_key)

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
    return await service.approve_contribution(contribution_id, current_user.id, tenant.id, approve_data.approved, approve_data.notes)

@router.get("/contributions/{contribution_id}", response_model=ContributionResponse)
async def get_contribution(
    contribution_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    contrib = await service.repo.get_contribution(contribution_id, tenant.id)
    if not contrib:
        raise HTTPException(status_code=404, detail="Contribution not found")
    return contrib

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
    project = await service.repo.get_project(project_id, tenant.id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return await service.repo.create_milestone(tenant_id=tenant.id, project_id=project_id, **data.model_dump())

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
    return await service.complete_milestone(milestone_id, current_user.id, tenant.id, complete_data)

@router.get("/{project_id}/milestones", response_model=list[MilestoneResponse])
async def get_milestones(
    project_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    return await service.repo.get_milestones(project_id, tenant.id)

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
    await service.follow_project(current_user.id, project_id, tenant.id)
    return {"message": "Project followed successfully"}

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
    await service.unfollow_project(current_user.id, project_id, tenant.id)
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
    followers = await service.repo.get_followers(project_id, tenant.id, skip, min(limit, 200))
    return [{"user_id": f.user_id, "followed_at": f.created_at.isoformat() if f.created_at else None} for f in followers]

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
    return await service.add_project_update(project_id, current_user.id, tenant.id, data.title, data.content)

@router.get("/{project_id}/updates", response_model=list[ProjectUpdateResponse])
async def get_project_updates(
    project_id: int,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    return await service.repo.get_project_updates(project_id, tenant.id, skip, min(limit, 200))

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
    return await service.get_project_analytics(project_id, tenant.id)