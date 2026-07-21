# app/domains/ai_governance/router.py
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, cast
from datetime import datetime, timedelta

from app.core.database import get_db
from app.api.deps import get_current_superuser, get_current_tenant
from app.domains.identity.models import User
from app.domains.ai_governance.service import AIGovernanceService
from app.domains.ai_governance.schemas import (
    AgentQuotaCreate,
    AgentQuotaResponse,
    AgentRateLimitUpdate,
    AgentRateLimitResponse,
    AgentUsageSummary,
    AgentAuditLogResponse,
)
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/ai-governance", tags=["AI Agent Governance"])


# ============================================================
# 1. إدارة الحصص (Quotas)
# ============================================================

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
    """
    تعيين حصة لوكيل (يتطلب صلاحيات مشرف).
    """
    service = AIGovernanceService(db)
    quota = await service.set_quota(
        admin_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        agent_id=agent_id,
        quota_data=data.model_dump(),
        ip_address=request.client.host if request.client else None
    )
    return quota


@router.get("/agents/{agent_id}/quotas", response_model=list[AgentQuotaResponse])
async def get_agent_quotas(
    agent_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب جميع الحصص النشطة لوكيل معين (يتطلب صلاحيات مشرف).
    """
    service = AIGovernanceService(db)
    return await service.get_agent_quotas(
        agent_id=agent_id,
        tenant_id=cast(int, tenant.id)
    )


# ============================================================
# 2. حدود المعدل (Rate Limits)
# ============================================================

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
    """
    تحديث حدود المعدل للوكيل (يتطلب صلاحيات مشرف).
    """
    service = AIGovernanceService(db)
    limits = await service.update_rate_limits(
        agent_id=agent_id,
        tenant_id=cast(int, tenant.id),
        admin_id=cast(int, current_user.id),
        data=data.model_dump(exclude_unset=True),
        ip_address=request.client.host if request.client else None
    )
    return limits


@router.get("/agents/{agent_id}/rate-limit", response_model=Optional[AgentRateLimitResponse])
async def get_rate_limit(
    agent_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب حدود المعدل للوكيل (يتطلب صلاحيات مشرف).
    """
    service = AIGovernanceService(db)
    limits = await service.get_rate_limits(
        agent_id=agent_id,
        tenant_id=cast(int, tenant.id)
    )
    if not limits:
        raise HTTPException(status_code=404, detail="Rate limits not found for this agent")
    return limits


# ============================================================
# 3. سجلات التدقيق (Audit Logs)
# ============================================================

@router.get("/agents/{agent_id}/audit-logs", response_model=list[AgentAuditLogResponse])
async def get_agent_audit_logs(
    agent_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب سجلات التدقيق لوكيل معين (يتطلب صلاحيات مشرف).
    """
    service = AIGovernanceService(db)
    return await service.get_audit_logs(
        agent_id=agent_id,
        tenant_id=cast(int, tenant.id),
        skip=skip,
        limit=limit
    )


# ============================================================
# 4. ملخص الاستخدام (Usage Summary)
# ============================================================

@router.get("/agents/{agent_id}/usage-summary", response_model=AgentUsageSummary)
async def get_usage_summary(
    agent_id: int,
    period: str = Query("MONTHLY", description="DAILY, WEEKLY, MONTHLY, YEARLY"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب ملخص الاستخدام للوكيل في فترة زمنية محددة (يتطلب صلاحيات مشرف).
    الفترات المدعومة: DAILY, WEEKLY, MONTHLY, YEARLY (افتراضي: MONTHLY)
    """
    service = AIGovernanceService(db)
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
        tenant_id=cast(int, tenant.id),
        start_date=start_date,
        end_date=now,
        period=period.upper()
    )


# ============================================================
# 5. نقطة التحقق من الحصص (للخدمات الداخلية)
# ============================================================

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
    """
    نقطة تحقق داخلية للخدمات الأخرى للتحقق من الحصص وتسجيل الاستهلاك.
    هذه النقطة لا تتطلب صلاحيات لأنها تُستخدم من قبل وكلاء آخرين.
    """
    from decimal import Decimal
    service = AIGovernanceService(db)
    result = await service.check_and_consume(
        tenant_id=cast(int, tenant.id),
        agent_id=agent_id,
        user_id=user_id,
        action_type=action_type,
        tokens=tokens,
        cost=Decimal(str(cost)),
        idempotency_key=idempotency_key,
        request_tokens=request_tokens,
        completion_tokens=completion_tokens
    )
    return {"allowed": result}