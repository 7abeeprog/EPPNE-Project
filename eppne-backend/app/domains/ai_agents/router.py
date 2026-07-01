# app/domains/ai_agents/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser
from app.domains.identity.models import User
from app.domains.ai_agents.service import AIAgentsService
from app.domains.ai_agents.repository import AIAgentsRepository
from app.domains.ai_agents.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/ai", tags=["Sovereign AI Agents"])


# ============================================================
# 1. إدارة الوكلاء (Agents)
# ============================================================

@router.post("/agents", response_model=AIAgentResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window=60)
async def create_agent(
    data: AIAgentCreate,
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = AIAgentsService(db)
    agent = await service.create_agent(
        owner_id=current_user.id,
        tenant_id=tenant.id,
        data=data.model_dump()
    )
    return agent


@router.get("/agents", response_model=list[AIAgentResponse])
async def list_agents(
    role: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AIAgentsRepository(db)
    agents = await repo.list_agents(
        tenant_id=tenant.id,
        owner_id=current_user.id,
        role=role,
        status=status,
        skip=skip,
        limit=min(limit, 200)
    )
    return agents


@router.get("/agents/{agent_id}", response_model=AIAgentResponse)
async def get_agent(
    agent_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AIAgentsRepository(db)
    agent = await repo.get_agent_by_owner(agent_id, current_user.id, tenant.id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or you don't have permission.")
    return agent


@router.post("/agents/{agent_id}/execute")
@rate_limit(max_requests=20, window=60)
async def execute_agent_action(
    agent_id: int,
    action_type: str,
    payload: dict,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AIAgentsService(db)
    result = await service.execute_agent_action(
        agent_id=agent_id,
        tenant_id=tenant.id,
        action_type=action_type,
        payload=payload,
        executor_user_id=current_user.id,
        idempotency_key=idempotency_key
    )
    return result


@router.patch("/agents/{agent_id}/status", response_model=AIAgentResponse)
@rate_limit(max_requests=10, window=60)
async def update_agent_status(
    agent_id: int,
    status_data: AgentStatusUpdate,
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AIAgentsService(db)
    agent = await service.update_agent_status(
        agent_id=agent_id,
        tenant_id=tenant.id,
        status=status_data.status,
        executor_user_id=current_user.id
    )
    return agent


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit(max_requests=5, window=60)
async def delete_agent(
    agent_id: int,
    soft: bool = True,
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    repo = AIAgentsRepository(db)
    agent = await repo.get_agent(agent_id, tenant.id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await repo.delete_agent(agent_id, tenant.id, soft=soft)
    return None


# ============================================================
# 2. الموافقات البشرية (Human-in-the-loop)
# ============================================================

@router.get("/approvals/pending", response_model=list[ApprovalResponse])
async def get_pending_approvals(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AIAgentsRepository(db)
    approvals = await repo.get_pending_approvals(current_user.id, tenant.id)
    return approvals


@router.post("/approvals/{approval_id}/resolve")
@rate_limit(max_requests=10, window=60)
async def resolve_approval(
    approval_id: int,
    resolution: ApprovalResolution,
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AIAgentsService(db)
    approval = await service.resolve_approval(
        approval_id=approval_id,
        tenant_id=tenant.id,
        human_approver_id=current_user.id,
        resolution=resolution.model_dump()
    )
    return {
        "message": f"Approval {approval.status}",
        "approval_id": approval.id,
        "status": approval.status
    }


@router.get("/approvals", response_model=list[ApprovalResponse])
async def list_approvals(
    agent_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AIAgentsRepository(db)
    approvals = await repo.list_approvals(
        tenant_id=tenant.id,
        agent_id=agent_id,
        status=status,
        skip=skip,
        limit=min(limit, 200)
    )
    return approvals


@router.get("/approvals/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AIAgentsRepository(db)
    approval = await repo.get_approval(approval_id, tenant.id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found.")
    return approval


# ============================================================
# 3. التحليلات والإحصائيات (Analytics)
# ============================================================

@router.get("/agents/{agent_id}/analytics")
async def get_agent_analytics(
    agent_id: int,
    days: int = 30,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AIAgentsService(db)
    analytics = await service.get_agent_analytics(agent_id, tenant.id, days)
    return analytics


@router.get("/agents/{agent_id}/status", response_model=AgentStatusResponse)
async def get_agent_status(
    agent_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AIAgentsService(db)
    status_info = await service.get_agent_status(agent_id, tenant.id)
    return status_info


# ============================================================
# 🆕 4. استخدامات الـ AI للمستأجر (SaaS Dashboard)
# ============================================================

@router.get("/usage")
async def get_ai_usage(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AIAgentsRepository(db)
    service = AIAgentsService(db)
    
    subscription = await repo.get_tenant_subscription(tenant.id)
    features = subscription.features or {} if subscription else {}
    
    current_agents = await repo.count_agents(tenant.id)
    monthly_calls = await repo.count_monthly_calls(tenant.id)
    monthly_cost = await repo.get_monthly_ai_cost(tenant.id)
    max_agents = features.get("max_agents", 0)
    monthly_limit = features.get("monthly_ai_calls", 0)
    
    return {
        "subscription_status": subscription.status if subscription else "NO_SUBSCRIPTION",
        "max_agents": max_agents,
        "current_agents": current_agents,
        "monthly_calls_limit": monthly_limit,
        "monthly_calls_used": monthly_calls,
        "monthly_calls_remaining": max(0, monthly_limit - monthly_calls),
        "monthly_cost_mrusdt": float(monthly_cost),
        "features": features,
    }