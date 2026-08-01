# app/domains/ai_governance/router.py
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, cast
from datetime import datetime, timedelta

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, get_current_tenant
from app.domains.identity.models import User
from app.domains.ai_governance.service import AIGovernanceService
from app.domains.ai_governance.schemas import (
    AgentQuotaCreate,
    AgentQuotaResponse,
    AgentRateLimitUpdate,
    AgentRateLimitResponse,
    AgentUsageSummary,
    AgentAuditLogResponse,
    AgentQuotaRemainingResponse,
)
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/ai-governance", tags=["AI Agent Governance"])


@router.post("/agents/{agent_id}/quotas", response_model=AgentQuotaResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def set_agent_quota(
    agent_id: int,
    data: AgentQuotaCreate,
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = AIGovernanceService(db, cast(int, tenant.id))
    quota = await service.set_quota(
        admin_id=cast(int, current_user.id),
        agent_id=agent_id,
        quota_data=data.model_dump(),
        ip_address=request.client.host if request.client else None
    )
    return quota


@router.get("/agents/{agent_id}/quotas", response_model=list[AgentQuotaResponse])
async def get_agent_quotas(
    agent_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AIGovernanceService(db, cast(int, tenant.id))
    if not await service._check_agent_ownership(agent_id, cast(int, current_user.id)):
        if not getattr(current_user, "system_role", "") in ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]:
            raise HTTPException(status_code=403, detail="Access denied to this agent's quotas")
    return await service.get_agent_quotas(agent_id)


@router.get("/agents/{agent_id}/quotas/remaining", response_model=AgentQuotaRemainingResponse)
async def get_agent_remaining_quotas(
    agent_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AIGovernanceService(db, cast(int, tenant.id))
    if not await service._check_agent_ownership(agent_id, cast(int, current_user.id)):
        if not getattr(current_user, "system_role", "") in ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]:
            raise HTTPException(status_code=403, detail="Access denied")
    remaining = await service.get_remaining_quotas(agent_id)
    return remaining


@router.post("/agents/{agent_id}/quotas/reset", status_code=204)
@rate_limit(max_requests=10, window_seconds=60)
async def reset_agent_quotas(
    agent_id: int,
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = AIGovernanceService(db, cast(int, tenant.id))
    await service.reset_quotas(
        agent_id=agent_id,
        admin_id=cast(int, current_user.id),
        ip_address=request.client.host if request.client else None
    )
    return None


@router.put("/agents/{agent_id}/rate-limit", response_model=AgentRateLimitResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def update_rate_limit(
    agent_id: int,
    data: AgentRateLimitUpdate,
    request: Request,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = AIGovernanceService(db, cast(int, tenant.id))
    limits = await service.update_rate_limits(
        agent_id=agent_id,
        admin_id=cast(int, current_user.id),
        data=data.model_dump(exclude_unset=True),
        ip_address=request.client.host if request.client else None
    )
    return limits


@router.get("/agents/{agent_id}/rate-limit", response_model=Optional[AgentRateLimitResponse])
async def get_rate_limit(
    agent_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AIGovernanceService(db, cast(int, tenant.id))
    if not await service._check_agent_ownership(agent_id, cast(int, current_user.id)):
        if not getattr(current_user, "system_role", "") in ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]:
            raise HTTPException(status_code=403, detail="Access denied")
    limits = await service.get_rate_limits(agent_id)
    if not limits:
        raise HTTPException(status_code=404, detail="Rate limits not found for this agent")
    return limits


@router.get("/agents/{agent_id}/audit-logs", response_model=list[AgentAuditLogResponse])
async def get_agent_audit_logs(
    agent_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = AIGovernanceService(db, cast(int, tenant.id))
    result = await service.get_audit_logs(
        agent_id=agent_id,
        skip=skip,
        limit=limit
    )
    return result.data


@router.get("/agents/{agent_id}/usage-summary", response_model=AgentUsageSummary)
async def get_usage_summary(
    agent_id: int,
    period: str = Query("MONTHLY", description="DAILY, WEEKLY, MONTHLY, YEARLY"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = AIGovernanceService(db, cast(int, tenant.id))
    now = datetime.utcnow()
    period_map = {
        "DAILY": 1,
        "WEEKLY": 7,
        "MONTHLY": 30,
        "YEARLY": 365,
    }
    days = period_map.get(period.upper(), 30)
    start_date = now - timedelta(days=days)

    return await service.get_usage_summary(
        agent_id=agent_id,
        start_date=start_date,
        end_date=now,
        period=period.upper()
    )


@router.post("/agents/{agent_id}/check-and-consume")
async def check_and_consume(
    agent_id: int,
    action_type: str,
    tokens: int,
    cost: float,
    user_id: int,
    request_tokens: int = 0,
    completion_tokens: int = 0,
    idempotency_key: Optional[str] = None,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    from decimal import Decimal
    service = AIGovernanceService(db, cast(int, tenant.id))
    try:
        result = await service.check_and_consume(
            agent_id=agent_id,
            user_id=user_id,
            action_type=action_type,
            tokens=tokens,
            cost=Decimal(str(cost)),
            idempotency_key=idempotency_key,
            request_tokens=request_tokens,
            completion_tokens=completion_tokens
        )
        return {"allowed": result["allowed"], "idempotent": result.get("idempotent", False)}
    except Exception as e:
        retry_after = getattr(e, "retry_after", None)
        return {"allowed": False, "error": str(e), "retry_after": retry_after}