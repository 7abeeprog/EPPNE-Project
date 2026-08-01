# app/domains/ai_governance/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any, cast
from decimal import Decimal
from datetime import datetime

from app.domains.ai_governance.repository import AIGovernanceRepository
from app.domains.ai_governance.models import AgentQuota, AgentRateLimit, AgentAuditLog
from app.core.errors import PermissionDeniedError, NotFoundError, QuotaExceededError
from app.core.logging_conf import logger


class AIGovernanceService:
    """
    خدمة حوكمة الذكاء الاصطناعي (AI Governance).
    """
    def __init__(self, db: AsyncSession, tenant_id: int):  # ✅ إضافة tenant_id
        self.db = db
        self.tenant_id = tenant_id
        self.repo = AIGovernanceRepository(db)

    # ============================================================
    # 1. إدارة الحصص (Quotas)
    # ============================================================

    async def set_quota(
        self,
        admin_id: int,
        agent_id: int,
        quota_data: dict,
        ip_address: Optional[str] = None
    ) -> AgentQuota:
        async with self.db.begin_nested():
            quota = await self.repo.create_or_update_quota(
                tenant_id=self.tenant_id,
                agent_id=agent_id,
                **quota_data
            )

            await self.repo.create_audit_log(
                tenant_id=self.tenant_id,
                agent_id=agent_id,
                admin_user_id=admin_id,
                action="CHANGE_QUOTA",
                new_value=quota_data,
                ip_address=ip_address
            )

        logger.info(f"Admin {admin_id} updated quota for agent {agent_id}")
        return quota

    async def get_agent_quotas(self, agent_id: int) -> List[AgentQuota]:
        return await self.repo.get_active_quotas(agent_id=agent_id, tenant_id=self.tenant_id)

    # ============================================================
    # 2. حدود المعدل (Rate Limits)
    # ============================================================

    async def update_rate_limits(
        self,
        agent_id: int,
        admin_id: int,
        data: dict,
        ip_address: Optional[str] = None
    ) -> AgentRateLimit:
        async with self.db.begin_nested():
            old_limits = await self.repo.get_rate_limits(agent_id, self.tenant_id)

            limits = await self.repo.update_rate_limits(
                agent_id=agent_id,
                tenant_id=self.tenant_id,
                data=data
            )

            await self.repo.create_audit_log(
                tenant_id=self.tenant_id,
                agent_id=agent_id,
                admin_user_id=admin_id,
                action="CHANGE_RATE_LIMIT",
                old_value={
                    "requests_per_minute": old_limits.requests_per_minute if old_limits else None,
                    "requests_per_hour": old_limits.requests_per_hour if old_limits else None,
                    "concurrent_limit": old_limits.concurrent_limit if old_limits else None
                },
                new_value=data,
                ip_address=ip_address
            )

        return limits

    async def get_rate_limits(self, agent_id: int) -> Optional[AgentRateLimit]:
        return await self.repo.get_rate_limits(agent_id, self.tenant_id)

    # ============================================================
    # 3. سجلات التدقيق (Audit Logs) – تعيد List[AgentAuditLog]
    # ============================================================

    async def get_audit_logs(
        self,
        agent_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentAuditLog]:
        return await self.repo.get_audit_logs(agent_id, self.tenant_id, skip, limit)

    # ============================================================
    # 4. ملخص الاستخدام (Usage Summary)
    # ============================================================

    async def get_usage_summary(
        self,
        agent_id: int,
        start_date: datetime,
        end_date: datetime,
        period: str = "MONTHLY"
    ) -> dict:
        summary = await self.repo.get_usage_summary(
            agent_id=agent_id,
            tenant_id=self.tenant_id,
            start_date=start_date,
            end_date=end_date
        )
        return {
            "agent_id": agent_id,
            "total_requests": summary["total_requests"],
            "total_tokens": summary["total_tokens"],
            "total_cost_mrusdt": float(Decimal(str(summary["total_cost"]))),
            "avg_response_time_ms": float(Decimal(str(summary["avg_response_time"]))),
            "period": period
        }

    # ============================================================
    # 5. نقطة الخنق والتنفيذ (Choke-Point)
    # ============================================================

    async def check_and_consume(
        self,
        agent_id: int,
        user_id: int,
        action_type: str,
        tokens: int,
        cost: Decimal,
        idempotency_key: Optional[str] = None,
        request_tokens: int = 0,
        completion_tokens: int = 0
    ) -> bool:
        if idempotency_key:
            existing_log = await self.repo.get_usage_log_by_idempotency(idempotency_key)
            if existing_log:
                logger.info(f"Idempotency key {idempotency_key} already processed.")
                return True

        active_quotas = await self.repo.get_active_quotas(agent_id=agent_id, tenant_id=self.tenant_id)

        async with self.db.begin_nested():
            for quota in active_quotas:
                usage_to_add = Decimal(0)
                limit_type_str = quota.limit_type.value if hasattr(quota.limit_type, 'value') else str(quota.limit_type)

                if limit_type_str == "REQUEST_COUNT":
                    usage_to_add = Decimal('1')
                elif limit_type_str == "TOKEN_COUNT":
                    usage_to_add = Decimal(str(tokens))
                elif limit_type_str == "COST_MRUSDT":
                    usage_to_add = cost

                current_usage = cast(Decimal, quota.current_usage)
                limit_value = cast(Decimal, quota.limit_value)

                if (current_usage + usage_to_add) > limit_value:
                    logger.warning(f"Agent {agent_id} exceeded {limit_type_str} quota.")
                    return False

                await self.repo.create_or_update_quota(
                    tenant_id=self.tenant_id,
                    agent_id=agent_id,
                    current_usage=current_usage + usage_to_add
                )

            await self.repo.create_usage_log(
                tenant_id=self.tenant_id,
                agent_id=agent_id,
                user_id=user_id,
                action_type=action_type,
                request_tokens=request_tokens,
                completion_tokens=completion_tokens,
                total_tokens=tokens,
                cost_mrusdt=cost,
                idempotency_key=idempotency_key,
                status="SUCCESS"
            )

        return True

    # ============================================================
    # 6. إعادة تعيين الحصص
    # ============================================================

    async def reset_quotas(
        self,
        agent_id: int,
        admin_id: int,
        ip_address: Optional[str] = None
    ) -> None:
        async with self.db.begin_nested():
            await self.repo.reset_quota_usage(agent_id, self.tenant_id)

            await self.repo.create_audit_log(
                tenant_id=self.tenant_id,
                agent_id=agent_id,
                admin_user_id=admin_id,
                action="RESET_QUOTA",
                new_value={"current_usage": 0},
                ip_address=ip_address
            )

        logger.info(f"Admin {admin_id} reset quotas for agent {agent_id}")