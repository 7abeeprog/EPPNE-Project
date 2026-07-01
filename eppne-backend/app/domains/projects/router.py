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

router = APIRouter(prefix="/projects", tags=["Sovereign Projects & Crowdfunding"])


# ==========================================
# 1. إدارة المشاريع (CRUD)
# ==========================================

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window=60)
async def create_project(
    data: ProjectCreate,
    request: Request,  # 🔥 للتدقيق الأمني
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إنشاء مشروع جديد (يتطلب tenant_id)."""
    service = ProjectService(db)
    project = await service.create_project(
        owner_id=current_user.id,
        tenant_id=tenant.id,
        data=data
    )
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """جلب تفاصيل مشروع مع التأكد من tenant_id."""
    service = ProjectService(db)
    project = await service.repo.get_project(project_id, tenant.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
@rate_limit(max_requests=20, window=60)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """تحديث مشروع (يتطلب التحقق من owner)."""
    service = ProjectService(db)
    project = await service.repo.get_project(project_id, tenant.id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    updated = await service.repo.update_project(
        project_id,
        tenant.id,
        **data.model_dump(exclude_unset=True)
    )
    return updated


@router.post("/{project_id}/publish", response_model=ProjectResponse)
@rate_limit(max_requests=5, window=60)
async def publish_project(
    project_id: int,
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """نشر المشروع (يطلق حدث project.published)."""
    service = ProjectService(db)
    project = await service.publish_project(project_id, current_user.id, tenant.id)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit(max_requests=10, window=60)
async def delete_project(
    project_id: int,
    soft: bool = True,
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """حذف مشروع (soft delete افتراضي)."""
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
    """قائمة المشاريع مع فلترة حسب tenant_id."""
    service = ProjectService(db)
    # منع جلب كميات كبيرة جداً
    safe_limit = min(limit, 200)
    projects = await service.repo.list_projects(
        tenant.id,
        project_type,
        status,
        country,
        skip,
        safe_limit
    )
    return projects


# ==========================================
# 3. المساهمات (Contributions)
# ==========================================

@router.post("/contributions", response_model=dict, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=20, window=60)
async def add_contribution(
    data: ContributionCreate,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    إضافة مساهمة جديدة مع دعم Idempotency.
    يرد dict (لأن الاستجابة قد تكون من Cache أو DB).
    """
    service = ProjectService(db)
    result = await service.add_contribution(
        contributor_id=current_user.id,
        tenant_id=tenant.id,
        data=data,
        idempotency_key=idempotency_key
    )
    return result


@router.post("/contributions/{contribution_id}/approve", response_model=ContributionResponse)
@rate_limit(max_requests=10, window=60)
async def approve_contribution(
    contribution_id: int,
    approve_data: ContributionApprove,
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """الموافقة على مساهمة أو رفضها."""
    service = ProjectService(db)
    contrib = await service.approve_contribution(
        contribution_id=contribution_id,
        owner_id=current_user.id,
        tenant_id=tenant.id,
        approved=approve_data.approved,
        notes=approve_data.notes
    )
    return contrib


@router.get("/contributions/{contribution_id}", response_model=ContributionResponse)
async def get_contribution(
    contribution_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب تفاصيل مساهمة معينة."""
    service = ProjectService(db)
    contrib = await service.repo.get_contribution(contribution_id, tenant.id)
    if not contrib:
        raise HTTPException(status_code=404, detail="Contribution not found")
    return contrib


# ==========================================
# 4. المراحل (Milestones)
# ==========================================

@router.post("/{project_id}/milestones", response_model=MilestoneResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window=60)
async def add_milestone(
    project_id: int,
    data: MilestoneCreate,
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إضافة مرحلة جديدة لمشروع."""
    service = ProjectService(db)
    project = await service.repo.get_project(project_id, tenant.id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    milestone = await service.repo.create_milestone(
        tenant_id=tenant.id,
        project_id=project_id,
        **data.model_dump()
    )
    return milestone


@router.post("/milestones/{milestone_id}/complete", response_model=MilestoneResponse)
@rate_limit(max_requests=5, window=60)
async def complete_milestone(
    milestone_id: int,
    complete_data: MilestoneComplete,
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إكمال مرحلة وإطلاق الأموال المرتبطة (يطلق حدث project.milestone.completed)."""
    service = ProjectService(db)
    milestone = await service.complete_milestone(
        milestone_id=milestone_id,
        owner_id=current_user.id,
        tenant_id=tenant.id,
        data=complete_data
    )
    return milestone


@router.get("/{project_id}/milestones", response_model=list[MilestoneResponse])
async def get_milestones(
    project_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """جلب جميع مراحل مشروع."""
    service = ProjectService(db)
    project = await service.repo.get_project(project_id, tenant.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    milestones = await service.repo.get_milestones(project_id, tenant.id)
    return milestones


# ==========================================
# 5. المتابعة (Follow)
# ==========================================

@router.post("/{project_id}/follow", response_model=FollowResponse)
@rate_limit(max_requests=20, window=60)
async def follow_project(
    project_id: int,
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """متابعة مشروع."""
    service = ProjectService(db)
    await service.follow_project(current_user.id, project_id, tenant.id)
    return {"message": "Project followed successfully"}


@router.delete("/{project_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit(max_requests=20, window=60)
async def unfollow_project(
    project_id: int,
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إلغاء متابعة مشروع."""
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
    """قائمة متابعي مشروع."""
    service = ProjectService(db)
    project = await service.repo.get_project(project_id, tenant.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    followers = await service.repo.get_followers(project_id, tenant.id, skip, min(limit, 200))
    return [
        {
            "user_id": f.user_id,
            "followed_at": f.created_at.isoformat() if f.created_at else None
        }
        for f in followers
    ]


# ==========================================
# 6. تحديثات المشروع (Updates)
# ==========================================

@router.post("/{project_id}/updates", response_model=ProjectUpdateResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window=60)
async def add_project_update(
    project_id: int,
    data: ProjectUpdateCreate,
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إضافة تحديث جديد للمشروع."""
    service = ProjectService(db)
    update_obj = await service.add_project_update(
        project_id=project_id,
        author_id=current_user.id,
        tenant_id=tenant.id,
        title=data.title,
        content=data.content
    )
    return update_obj


@router.get("/{project_id}/updates", response_model=list[ProjectUpdateResponse])
async def get_project_updates(
    project_id: int,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """جلب تحديثات مشروع معين."""
    service = ProjectService(db)
    project = await service.repo.get_project(project_id, tenant.id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    updates = await service.repo.get_project_updates(project_id, tenant.id, skip, min(limit, 200))
    return updates


# ==========================================
# 7. التحليلات (Analytics) مع Caching
# ==========================================

@router.get("/{project_id}/analytics", response_model=ProjectAnalyticsResponse)
async def get_analytics(
    project_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب تحليلات المشروع (مع Caching لمدة 5 دقائق).
    """
    service = ProjectService(db)
    analytics = await service.get_project_analytics(project_id, tenant.id)
    return analytics