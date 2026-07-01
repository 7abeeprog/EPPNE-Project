# app/domains/ai_governance/router.py
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any
from datetime import datetime, timedelta

from app.core.database import get_db
from app.api.deps import get_current_superuser, get_current_tenant
from app.domains.identity.models import User
from app.domains.ai_governance.service import AIGovernanceService
from app.domains.ai_governance.repository import AIGovernanceRepository
from app.domains.ai_governance.schemas import *
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/ai-governance", tags=["AI Agent Governance"])


# ============================================================
# 1. إدارة الحصص (Quotas)
# ============================================================

@router.post("/agents/{agent_id}/quotas", response_model=AgentQuotaResponse)
@rate_limit(max_requests=20, window=60)
async def set_agent_quota(
    agent_id: int,
    data: AgentQuotaCreate,
    request: Request,
    tenant: Any = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    تعيين حصة لوكيل (يتطلب صلاحيات مشرف).
    """
    service = AIGovernanceService(db)
    quota = await service.set_quota(
        admin_id=current_user.id,
        tenant_id=tenant.id,
        agent_id=agent_id,
        quota_data=data.model_dump(),
        ip_address=request.client.host
    )
    return quota


@router.get("/agents/{agent_id}/quotas", response_model=list[AgentQuotaResponse])
async def get_agent_quotas(
    agent_id: int,
    tenant: Any = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب جميع الحصص النشطة لوكيل معين.
    """
    repo = AIGovernanceRepository(db)
    return await repo.get_active_quotas(agent_id, tenant.id)


# ============================================================
# 2. حدود المعدل (Rate Limits)
# ============================================================

@router.put("/agents/{agent_id}/rate-limit", response_model=AgentRateLimitResponse)
@rate_limit(max_requests=20, window=60)
async def update_rate_limit(
    agent_id: int,
    data: AgentRateLimitUpdate,
    request: Request,
    tenant: Any = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    تحديث حدود المعدل للوكيل (يتطلب صلاحيات مشرف).
    """
    repo = AIGovernanceRepository(db)
    limits = await repo.update_rate_limits(
        agent_id=agent_id,
        tenant_id=tenant.id,
        data=data.model_dump(exclude_unset=True)
    )
    return limits


# ============================================================
# 3. سجلات التدقيق (Audit Logs)
# ============================================================

@router.get("/agents/{agent_id}/audit-logs", response_model=list[AgentAuditLogResponse])
async def get_agent_audit_logs(
    agent_id: int,
    skip: int = 0,
    limit: int = 100,
    tenant: Any = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب سجلات التدقيق لوكيل معين (يتطلب صلاحيات مشرف).
    """
    repo = AIGovernanceRepository(db)
    return await repo.get_audit_logs(agent_id, tenant.id, skip, limit)


# ============================================================
# 4. ملخص الاستخدام (Usage Summary)
# ============================================================

@router.get("/agents/{agent_id}/usage-summary", response_model=AgentUsageSummary)
async def get_usage_summary(
    agent_id: int,
    period: str = "MONTHLY",
    tenant: Any = Depends(get_current_tenant),
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

    summary = await service.repo.get_usage_summary(agent_id, tenant.id, start_date, now)
    return {
        "agent_id": agent_id,
        "total_requests": summary["total_requests"],
        "total_tokens": summary["total_tokens"],
        "total_cost_mrusdt": summary["total_cost"],
        "avg_response_time_ms": summary["avg_response_time"],
        "period": period.upper()
    }