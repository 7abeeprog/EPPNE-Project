# app/domains/ai_governance/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime

from app.domains.ai_governance.repository import AIGovernanceRepository
from app.core.errors import PermissionDeniedError, NotFoundError, QuotaExceededError
from app.core.logging_conf import logger

class AIGovernanceService:
    """
    خدمة حوكمة الذكاء الاصطناعي (AI Governance).
    تعمل كنقطة تحكم (Choke-Point) لمراقبة الاستهلاك، تطبيق الحصص، ومنع تجاوز الحدود.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AIGovernanceRepository(db)

    # ============================================================
    # 1. إدارة الحصص (Quotas)
    # ============================================================

    async def set_quota(
        self,
        admin_id: int,
        tenant_id: int,
        agent_id: int,
        quota_data: dict,
        ip_address: str
    ) -> Any:
        """
        تعيين أو تحديث حصة وكيل معين (Quota) مع تسجيل إجراء التدقيق (Audit Log).
        """
        # 1. إنشاء أو تحديث الحصة
        quota = await self.repo.create_or_update_quota(
            tenant_id=tenant_id,
            agent_id=agent_id,
            **quota_data
        )

        # 2. تسجيل العملية في سجلات التدقيق (لأغراض الأمان والشفافية)
        await self.repo.create_audit_log(
            tenant_id=tenant_id,
            agent_id=agent_id,
            admin_user_id=admin_id,
            action="CHANGE_QUOTA",
            new_value=quota_data,
            ip_address=ip_address
        )

        logger.info(f"Admin {admin_id} updated quota for agent {agent_id} in tenant {tenant_id}")
        return quota

    # ============================================================
    # 2. نقطة الخنق والتنفيذ (Choke-Point & Execution Validation)
    # ============================================================

    async def check_and_consume(
        self,
        tenant_id: int,
        agent_id: int,
        user_id: int,
        action_type: str,
        tokens: int,
        cost: Decimal,
        idempotency_key: Optional[str] = None,
        request_tokens: int = 0,
        completion_tokens: int = 0
    ) -> bool:
        """
        التحقق من الحصص المتاحة وتسجيل الاستهلاك.
        تُستدعى هذه الدالة قبل أي عملية تنفيذ للذكاء الاصطناعي لضمان عدم تجاوز الحدود.
        """
        # 1. التحقق من Idempotency لمنع احتساب الاستهلاك مرتين لنفس الطلب
        if idempotency_key:
            existing_log = await self.repo.get_usage_log_by_idempotency(idempotency_key)
            if existing_log:
                logger.info(f"Idempotency key {idempotency_key} already processed for usage.")
                return True

        # 2. جلب جميع الحصص النشطة للوكيل
        active_quotas = await self.repo.get_active_quotas(agent_id=agent_id, tenant_id=tenant_id)

        # 3. التحقق من كل حصة (Tokens, Requests, Cost)
        for quota in active_quotas:
            usage_to_add = Decimal(0)
            
            if quota.limit_type.value == "REQUEST_COUNT":
                usage_to_add = Decimal(1)
            elif quota.limit_type.value == "TOKEN_COUNT":
                usage_to_add = Decimal(tokens)
            elif quota.limit_type.value == "COST_MRUSDT":
                usage_to_add = cost

            # التحقق مما إذا كان الاستهلاك الجديد سيتجاوز الحد المسموح
            if (quota.current_usage + usage_to_add) > quota.limit_value:
                logger.warning(
                    f"Agent {agent_id} exceeded {quota.limit_type} quota. "
                    f"Limit: {quota.limit_value}, Usage: {quota.current_usage + usage_to_add}"
                )
                return False  # تم تجاوز الحصة المسموح بها

            # تحديث الاستهلاك الحالي
            await self.repo.create_or_update_quota(
                tenant_id=tenant_id,
                agent_id=agent_id,
                current_usage=quota.current_usage + usage_to_add
            )

        # 4. تسجيل الاستهلاك الفعلي في الـ Logs
        await self.repo.create_usage_log(
            tenant_id=tenant_id,
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