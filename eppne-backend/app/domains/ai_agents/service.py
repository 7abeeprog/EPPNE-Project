# app/domains/ai_agents/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List, cast
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import bleach

from app.domains.ai_agents.repository import AIAgentsRepository
from app.domains.ai_agents.models import AIAgent, AgentApprovalQueue, ApprovalStatus, AgentStatus, AITaskLog
from app.domains.ai_agents.schemas import (
    AIAgentCreate,
    AIAgentResponse,
    ApprovalResponse,
    ApprovalResolution,
    AgentStatusUpdate,
    AgentStatusResponse
)
from app.services.ai import ai_engine, AIModelId, TaskType
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.core.logging_conf import logger
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.idempotency import get_idempotency_result, store_idempotency_result
from app.domains.finance.service import FinanceService
from app.domains.identity.models import User
from app.core.pagination import PaginatedResponse


class AIAgentsService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = AIAgentsRepository(db)
        self.finance = FinanceService(db, tenant_id)
        self.event_bus = EventBus(cast(Any, redis_client))  # ✅ تجاهل النوع

    # ==========================================
    # دوال مساعدة (مع tenant_id)
    # ==========================================

    async def _check_tenant_access(self, resource_tenant_id: int):
        if self.tenant_id != resource_tenant_id:
            raise PermissionDeniedError("ليس لديك صلاحية الوصول لهذا المورد")

    async def _validate_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        if idempotency_key:
            cache_key = f"idempotency:{self.tenant_id}:{idempotency_key}"
            cached = await get_idempotency_result(cache_key)
            if cached is not None:
                return cached
        return None

    async def _store_idempotency(self, idempotency_key: str, result: Dict[str, Any]):
        if idempotency_key:
            cache_key = f"idempotency:{self.tenant_id}:{idempotency_key}"
            await store_idempotency_result(cache_key, result)

    # ==========================================
    # 1. إدارة الوكلاء (Agents) – مع tenant_id
    # ==========================================

    async def create_agent(self, owner_id: int, data: Dict[str, Any]) -> AIAgent:
        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)
        sanitized_prompt = bleach.clean(data.get("system_prompt", ""), tags=[], strip=True)

        agent = await self.repo.create_agent(
            owner_id=owner_id,
            tenant_id=self.tenant_id,
            name=sanitized_name,
            role=data["role"],
            system_prompt=sanitized_prompt,
            base_model=data.get("base_model", "gemini-1.5-pro"),
            can_execute_payments=data.get("can_execute_payments", False),
            can_sign_contracts=data.get("can_sign_contracts", False),
            requires_human_approval=data.get("requires_human_approval", True),
            interaction_cost_mrusdt=data.get("interaction_cost_mrusdt", Decimal('0.0'))
        )

        await audit_log(
            user_id=owner_id,
            action="AI_AGENT_CREATED",
            details={
                "name": agent.name,
                "role": agent.role.value if hasattr(agent.role, 'value') else str(agent.role),
                "tenant_id": self.tenant_id,
                "agent_id": agent.id
            }
        )

        await self.event_bus.publish("ai.agent.created", {
            "agent_id": agent.id,
            "tenant_id": self.tenant_id,
            "owner_id": owner_id,
            "name": agent.name
        })

        return agent

    async def list_agents(
        self,
        owner_id: Optional[int] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> PaginatedResponse[AIAgentResponse]:
        return await self.repo.list_agents(self.tenant_id, owner_id, role, status, skip, limit)

    async def get_agent(self, agent_id: int) -> Optional[AIAgent]:
        return await self.repo.get_agent(agent_id, self.tenant_id)

    async def get_agent_by_owner(self, agent_id: int, owner_id: int) -> Optional[AIAgent]:
        return await self.repo.get_agent_by_owner(agent_id, owner_id, self.tenant_id)

    async def update_agent_status(
        self,
        agent_id: int,
        status: str,
        executor_user_id: int
    ) -> Optional[AIAgent]:
        agent = await self.repo.get_agent(agent_id, self.tenant_id)
        if not agent:
            return None
        await self.repo.update_agent_status(agent_id, self.tenant_id, status)

        await audit_log(
            user_id=executor_user_id,
            action="AI_AGENT_STATUS_UPDATED",
            details={
                "agent_id": agent_id,
                "new_status": status,
                "tenant_id": self.tenant_id
            }
        )

        return await self.repo.get_agent(agent_id, self.tenant_id)

    async def delete_agent(self, agent_id: int, soft: bool = True) -> bool:
        return await self.repo.delete_agent(agent_id, self.tenant_id, soft)

    # ==========================================
    # 2. تنفيذ إجراءات الوكيل (مع Idempotency و tenant_id)
    # ==========================================

    async def execute_agent_action(
        self,
        agent_id: int,
        action_type: str,
        payload: Dict[str, Any],
        executor_user_id: int,
        idempotency_key: str
    ) -> Dict[str, Any]:
        cached = await self._validate_idempotency(idempotency_key)
        if cached:
            return cached

        agent = await self.repo.get_agent(agent_id, self.tenant_id)
        if not agent:
            raise NotFoundError(f"الوكيل {agent_id} غير موجود")
        if cast(str, agent.status) != AgentStatus.ACTIVE.value and cast(str, agent.status) != "ACTIVE":
            raise PermissionDeniedError(f"الوكيل {agent_id} غير نشط")

        sanitized_prompt = bleach.clean(payload.get("prompt", ""), tags=[], strip=True)
        sanitized_payload = {
            "prompt": sanitized_prompt,
            "language": payload.get("language", "ar"),
            "batch": payload.get("batch", False),
            "max_tokens": payload.get("max_tokens", 2048),
            "temperature": payload.get("temperature", 0.7),
        }

        try:
            task_type = TaskType.ARABIC_CHAT
            if action_type == "TRANSLATE":
                task_type = TaskType.TRANSLATION
            # إذا كان هناك أنواع أخرى، يمكن إضافتها هنا

            task_log = await self.repo.create_task_log(
                tenant_id=self.tenant_id,
                agent_id=agent_id,
                user_id=executor_user_id,
                task_type=task_type.value if hasattr(task_type, 'value') else str(task_type),
                idempotency_key=idempotency_key,
                prompt_tokens=0,
                completion_tokens=0,
                cost_mrusdt=Decimal('0.0'),
                settlement_type="WEB3_CRYPTO",
                used_model=agent.base_model
            )

            result = await ai_engine.generate(
                prompt=sanitized_prompt,
                system_prompt=cast(str, agent.system_prompt),
                language=sanitized_payload["language"],
                task_type=task_type,
                use_cache=True,
                use_batch=sanitized_payload["batch"],
                max_tokens=sanitized_payload["max_tokens"],
                temperature=sanitized_payload["temperature"],
            )

            if result and isinstance(result, dict):
                cost = result.get("cost_mrusdt", Decimal('0.0'))
                if cost:
                    await self.repo.update_task_log_cost(cast(int, task_log.id), Decimal(str(cost)))

        except Exception as e:
            logger.error(f"AI execution failed for agent {agent_id}: {e}")
            await self.repo.create_task_log(
                tenant_id=self.tenant_id,
                agent_id=agent_id,
                user_id=executor_user_id,
                task_type="ERROR",
                idempotency_key=idempotency_key,
                prompt_tokens=0,
                completion_tokens=0,
                cost_mrusdt=Decimal('0.0'),
                settlement_type="WEB3_CRYPTO",
                used_model=agent.base_model
            )
            raise

        if cast(bool, agent.requires_human_approval):
            approval = await self.repo.create_approval_request(
                tenant_id=self.tenant_id,
                agent_id=agent_id,
                human_approver_id=executor_user_id,
                action_type=action_type,
                proposed_payload=payload,
                idempotency_key=f"{idempotency_key}-approval"
            )

            response = {
                "status": "PENDING_APPROVAL",
                "approval_id": approval.id,
                "message": "الإجراء معلق بانتظار الموافقة البشرية",
                "result": result
            }
        else:
            response = {
                "status": "COMPLETED",
                "result": result
            }

        await self._store_idempotency(idempotency_key, response)

        await audit_log(
            user_id=executor_user_id,
            action="AI_AGENT_ACTION_EXECUTED",
            details={
                "agent_id": agent_id,
                "action_type": action_type,
                "status": response["status"],
                "approval_id": response.get("approval_id"),
                "tenant_id": self.tenant_id
            }
        )

        return response

    # ==========================================
    # 3. الموافقات البشرية (مع tenant_id)
    # ==========================================

    async def get_pending_approvals(self, human_approver_id: int) -> List[AgentApprovalQueue]:
        return await self.repo.get_pending_approvals(human_approver_id, self.tenant_id)

    async def resolve_approval(
        self,
        approval_id: int,
        human_approver_id: int,
        resolution: Dict[str, Any]
    ) -> Optional[AgentApprovalQueue]:
        approval = await self.repo.get_approval(approval_id, self.tenant_id)
        if not approval:
            return None

        if cast(int, approval.human_approver_id) != human_approver_id:
            raise PermissionDeniedError("ليس لديك صلاحية لحل هذا الطلب")

        if cast(str, approval.status) != ApprovalStatus.PENDING.value and cast(str, approval.status) != "PENDING":
            raise ValidationError(f"الطلب تم حله بالفعل (الحالة: {approval.status})")

        status_value = resolution["status"]
        feedback = resolution.get("human_feedback")

        async with self.db.begin_nested():
            updated_approval = await self.repo.resolve_approval(
                approval_id=approval_id,
                tenant_id=self.tenant_id,
                status=status_value,
                feedback=feedback
            )

            if status_value == "APPROVED" or status_value == ApprovalStatus.APPROVED.value:
                pass

        await self.db.commit()

        await audit_log(
            user_id=human_approver_id,
            action="AI_APPROVAL_RESOLVED",
            details={
                "approval_id": approval_id,
                "status": status_value,
                "feedback": feedback,
                "tenant_id": self.tenant_id
            }
        )

        return updated_approval

    async def list_approvals(
        self,
        agent_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> PaginatedResponse[ApprovalResponse]:
        return await self.repo.list_approvals(self.tenant_id, agent_id, status, skip, limit)

    async def get_approval(self, approval_id: int) -> Optional[AgentApprovalQueue]:
        return await self.repo.get_approval(approval_id, self.tenant_id)

    # ==========================================
    # 4. التحليلات والإحصائيات (مع tenant_id)
    # ==========================================

    async def get_agent_analytics(self, agent_id: int, days: int = 30) -> Dict[str, Any]:
        agent = await self.repo.get_agent(agent_id, self.tenant_id)
        if not agent:
            raise NotFoundError(f"الوكيل {agent_id} غير موجود")
        return await self.repo.get_agent_usage_stats(agent_id, self.tenant_id, days)

    async def get_agent_status(self, agent_id: int) -> Dict[str, Any]:
        agent = await self.repo.get_agent(agent_id, self.tenant_id)
        if not agent:
            raise NotFoundError(f"الوكيل {agent_id} غير موجود")
        return {
            "agent_id": agent.id,
            "status": agent.status,
            "last_active": None
        }

    # ==========================================
    # 5. استخدامات الـ AI للمستأجر (مع tenant_id)
    # ==========================================

    async def get_ai_usage(self) -> Dict[str, Any]:
        subscription = await self.repo.get_tenant_subscription(self.tenant_id)
        features = subscription.features if subscription else {}

        current_agents = await self.repo.count_agents(self.tenant_id)
        monthly_calls = await self.repo.count_monthly_calls(self.tenant_id)
        monthly_cost = await self.repo.get_monthly_ai_cost(self.tenant_id)

        max_agents = features.get("max_agents", 0) if features else 0
        monthly_limit = features.get("monthly_ai_calls", 0) if features else 0

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

    # ==========================================
    # 6. الفوترة الشهرية للـ AI (مع tenant_id)
    # ==========================================

    async def generate_monthly_invoice(self) -> Optional[Any]:
        from app.domains.invoicing.service import InvoicingService
        from datetime import timedelta

        try:
            monthly_cost = await self.repo.get_monthly_ai_cost(self.tenant_id)
            if monthly_cost == Decimal(0):
                logger.info(f"No AI usage for tenant {self.tenant_id}, skipping invoice.")
                return None

            invoicing = InvoicingService(self.db, self.tenant_id)
            invoice = await invoicing.create_invoice(
                entity_id=self.tenant_id,
                user_id=0,
                amount=monthly_cost,
                description=f"Monthly AI usage invoice for tenant {self.tenant_id}",
                due_date=datetime.utcnow() + timedelta(days=30),
                invoice_type="AI_USAGE",
                reference_id=self.tenant_id
            )
            return invoice
        except Exception as e:
            logger.error(f"Failed to generate monthly invoice for tenant {self.tenant_id}: {e}")
            raise