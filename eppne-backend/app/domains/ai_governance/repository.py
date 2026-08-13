# app/domains/ai_governance/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from decimal import Decimal
from typing import List, Optional, cast
from datetime import datetime

from app.domains.ai_governance.models import AgentQuota, AgentUsageLog, AgentRateLimit, AgentAuditLog
from app.domains.ai_governance.schemas import AgentAuditLogResponse
from app.domains.ai_agents.models import AIAgent
from app.core.pagination import PaginatedResponse
from app.core.errors import NotFoundError


class AIGovernanceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ========== Quotas (مع tenant_id) ==========
    async def create_or_update_quota(self, tenant_id: int, agent_id: int, **kwargs) -> AgentQuota:
        result = await self.db.execute(
            select(AgentQuota).where(
                and_(AgentQuota.agent_id == agent_id, AgentQuota.tenant_id == tenant_id)
            )
        )
        quota = result.scalar_one_or_none()
        
        if quota:
            for key, value in kwargs.items():
                setattr(quota, key, value)
        else:
            quota = AgentQuota(tenant_id=tenant_id, agent_id=agent_id, **kwargs)
            self.db.add(quota)

        await self.db.flush()
        await self.db.refresh(quota)
        return quota

    async def get_active_quotas(self, agent_id: int, tenant_id: int) -> List[AgentQuota]:
        result = await self.db.execute(
            select(AgentQuota).where(
                and_(
                    AgentQuota.agent_id == agent_id,
                    AgentQuota.tenant_id == tenant_id
                )
            )
        )
        return list(result.scalars().all())

    async def reset_quota_usage(self, agent_id: int, tenant_id: int) -> None:
        await self.db.execute(
            update(AgentQuota)
            .where(and_(AgentQuota.agent_id == agent_id, AgentQuota.tenant_id == tenant_id))
            .values(current_usage=0)
        )
        await self.db.flush()

    # ========== Usage Logs (مع tenant_id في Idempotency) ==========
    async def create_usage_log(self, **kwargs) -> AgentUsageLog:
        log = AgentUsageLog(**kwargs)
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log

    async def get_usage_log_by_idempotency(self, idempotency_key: str, tenant_id: int) -> Optional[AgentUsageLog]:
        result = await self.db.execute(
            select(AgentUsageLog).where(
                and_(
                    AgentUsageLog.idempotency_key == idempotency_key,
                    AgentUsageLog.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_usage_summary(
        self,
        agent_id: int,
        tenant_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> dict:
        result = await self.db.execute(
            select(
                func.count(AgentUsageLog.id).label("total_requests"),
                func.sum(AgentUsageLog.total_tokens).label("total_tokens"),
                func.sum(AgentUsageLog.cost_mrusdt).label("total_cost"),
                func.avg(AgentUsageLog.response_time_ms).label("avg_response_time")
            )
            .where(
                and_(
                    AgentUsageLog.agent_id == agent_id,
                    AgentUsageLog.tenant_id == tenant_id,
                    AgentUsageLog.created_at.between(start_date, end_date)
                )
            )
        )
        row = result.one()
        return {
            "total_requests": row.total_requests or 0,
            "total_tokens": row.total_tokens or 0,
            "total_cost": float(row.total_cost or 0),
            "avg_response_time": float(row.avg_response_time or 0),
        }

    # ========== Rate Limits (مع tenant_id) ==========
    async def update_rate_limits(self, agent_id: int, tenant_id: int, data: dict) -> AgentRateLimit:
        result = await self.db.execute(
            select(AgentRateLimit).where(
                and_(AgentRateLimit.agent_id == agent_id, AgentRateLimit.tenant_id == tenant_id)
            )
        )
        limit = result.scalar_one_or_none()
        
        if limit:
            for key, value in data.items():
                setattr(limit, key, value)
        else:
            limit = AgentRateLimit(agent_id=agent_id, tenant_id=tenant_id, **data)
            self.db.add(limit)

        await self.db.flush()
        await self.db.refresh(limit)
        return limit

    async def get_rate_limits(self, agent_id: int, tenant_id: int) -> Optional[AgentRateLimit]:
        result = await self.db.execute(
            select(AgentRateLimit).where(
                and_(
                    AgentRateLimit.agent_id == agent_id,
                    AgentRateLimit.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    # ========== Audit Logs (مع PaginatedResponse و AgentAuditLogResponse) ==========
    async def create_audit_log(self, **kwargs) -> AgentAuditLog:
        log = AgentAuditLog(**kwargs)
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log

    async def get_audit_logs(
        self,
        agent_id: int,
        tenant_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> PaginatedResponse[AgentAuditLogResponse]:
        query = (
            select(AgentAuditLog)
            .where(
                and_(AgentAuditLog.agent_id == agent_id, AgentAuditLog.tenant_id == tenant_id)
            )
            .order_by(AgentAuditLog.created_at.desc())
        )

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.offset(skip).limit(min(limit, 200))
        result = await self.db.execute(query)
        items = [AgentAuditLogResponse.model_validate(item) for item in result.scalars().all()]

        return PaginatedResponse[AgentAuditLogResponse](
            data=items,
            total=total,
            skip=skip,
            limit=limit
        )

    # ========== التحقق من وجود الوكيل ==========
    async def get_agent(self, agent_id: int, tenant_id: int) -> Optional[AIAgent]:
        result = await self.db.execute(
            select(AIAgent).where(
                and_(
                    AIAgent.id == agent_id,
                    AIAgent.tenant_id == tenant_id,
                    AIAgent.is_deleted == False
                )
            )
        )
        return result.scalar_one_or_none()