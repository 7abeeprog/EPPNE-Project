# app/domains/ai_agents/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, cast, List
import uuid

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser
from app.domains.identity.models import User
from app.domains.ai_agents.service import AIAgentsService
from app.domains.ai_agents.schemas import (
    AIAgentCreate,
    AIAgentResponse,
    ApprovalResponse,
    ApprovalResolution,
    AgentStatusUpdate,
    AgentStatusResponse
)
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/ai", tags=["Sovereign AI Agents"])


# ============================================================
# 1. إدارة الوكلاء (Agents) - مع صلاحيات صارمة
# ============================================================

@router.post("/agents", response_model=AIAgentResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_agent(
    data: AIAgentCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = AIAgentsService(db, cast(int, tenant.id))
    agent = await service.create_agent(
        owner_id=cast(int, current_user.id),
        data=data.model_dump()
    )
    return agent


@router.get("/agents", response_model=List[AIAgentResponse])
async def list_agents(
    role: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AIAgentsService(db, cast(int, tenant.id))
    result = await service.list_agents(
        owner_id=cast(int, current_user.id),
        role=role,
        status=status,
        skip=skip,
        limit=min(limit, 200)
    )
    return result.data  # ✅ تم التعديل: items -> data


@router.get("/agents/{agent_id}", response_model=AIAgentResponse)
async def get_agent(
    agent_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AIAgentsService(db, cast(int, tenant.id))
    agent = await service.get_agent_by_owner(
        agent_id=agent_id,
        owner_id=cast(int, current_user.id)
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or you don't have permission.")
    return agent


@router.post("/agents/{agent_id}/execute")
@rate_limit(max_requests=20, window_seconds=60)
async def execute_agent_action(
    agent_id: int,
    action_type: str,
    payload: dict,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AIAgentsService(db, cast(int, tenant.id))
    result = await service.execute_agent_action(
        agent_id=agent_id,
        action_type=action_type,
        payload=payload,
        executor_user_id=cast(int, current_user.id),
        idempotency_key=idempotency_key or f"EXEC-{uuid.uuid4().hex[:12].upper()}"
    )
    return result


@router.patch("/agents/{agent_id}/status", response_model=AIAgentResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_agent_status(
    agent_id: int,
    status_data: AgentStatusUpdate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = AIAgentsService(db, cast(int, tenant.id))
    agent = await service.update_agent_status(
        agent_id=agent_id,
        status=status_data.status.value if hasattr(status_data.status, 'value') else str(status_data.status),
        executor_user_id=cast(int, current_user.id)
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit(max_requests=5, window_seconds=60)
async def delete_agent(
    agent_id: int,
    soft: bool = True,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = AIAgentsService(db, cast(int, tenant.id))
    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await service.delete_agent(
        agent_id=agent_id,
        soft=soft
    )
    return None


# ============================================================
# 2. الموافقات البشرية (Human-in-the-loop) - مع عزل صارم
# ============================================================

@router.get("/approvals/pending", response_model=List[ApprovalResponse])
async def get_pending_approvals(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AIAgentsService(db, cast(int, tenant.id))
    approvals = await service.get_pending_approvals(
        human_approver_id=cast(int, current_user.id)
    )
    return approvals


@router.post("/approvals/{approval_id}/resolve")
@rate_limit(max_requests=10, window_seconds=60)
async def resolve_approval(
    approval_id: int,
    resolution: ApprovalResolution,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AIAgentsService(db, cast(int, tenant.id))
    approval = await service.resolve_approval(
        approval_id=approval_id,
        human_approver_id=cast(int, current_user.id),
        resolution=resolution.model_dump()
    )
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found or you don't have permission.")
    return {
        "message": f"Approval {approval.status}",
        "approval_id": approval.id,
        "status": approval.status
    }


@router.get("/approvals", response_model=List[ApprovalResponse])
async def list_approvals(
    agent_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AIAgentsService(db, cast(int, tenant.id))
    result = await service.list_approvals(
        agent_id=agent_id,
        status=status,
        skip=skip,
        limit=min(limit, 200)
    )
    return result.data  # ✅ تم التعديل: items -> data


@router.get("/approvals/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AIAgentsService(db, cast(int, tenant.id))
    approval = await service.get_approval(approval_id)
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
    service = AIAgentsService(db, cast(int, tenant.id))
    analytics = await service.get_agent_analytics(
        agent_id=agent_id,
        days=days
    )
    return analytics


@router.get("/agents/{agent_id}/status", response_model=AgentStatusResponse)
async def get_agent_status(
    agent_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AIAgentsService(db, cast(int, tenant.id))
    status_info = await service.get_agent_status(agent_id)
    return status_info


# ============================================================
# 4. استخدامات الـ AI للمستأجر (SaaS Dashboard)
# ============================================================

@router.get("/usage")
async def get_ai_usage(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AIAgentsService(db, cast(int, tenant.id))
    usage = await service.get_ai_usage()
    return usage