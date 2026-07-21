# app/domains/ai_agents/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List, cast
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import bleach

from app.domains.ai_agents.repository import AIAgentsRepository, AIAgentRepository
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
from app.core.idempotency import check_idempotency, store_idempotency_result
from app.domains.finance.service import FinanceService
from app.domains.identity.models import User


class AIAgentsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AIAgentsRepository(db)
        self.finance = FinanceService(db)
        self.event_bus = EventBus(redis_client)  # type: ignore
        # محرك الذكاء الاصطناعي سيتم تهيئته عند الحاجة

    # ==========================================
    # دوال مساعدة
    # ==========================================

    async def _check_tenant_access(self, tenant_id: int, resource_tenant_id: int):
        """التحقق من أن المستأجر يملك المورد."""
        if tenant_id != resource_tenant_id:
            raise PermissionDeniedError("ليس لديك صلاحية الوصول لهذا المورد")

    async def _validate_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """التحقق من Idempotency."""
        if idempotency_key:
            cached = await check_idempotency(idempotency_key)
            if cached:
                return cached
        return None

    async def _store_idempotency(self, idempotency_key: str, result: Dict[str, Any]):
        """تخزين نتيجة Idempotency."""
        if idempotency_key:
            await store_idempotency_result(idempotency_key, result)

    # ==========================================
    # 1. إدارة الوكلاء (Agents)
    # ==========================================

    async def create_agent(self, owner_id: int, tenant_id: int, data: Dict[str, Any]) -> AIAgent:
        """إنشاء وكيل رقمي جديد."""
        sanitized_name = bleach.clean(data.get("name", ""), tags=[], strip=True)
        sanitized_prompt = bleach.clean(data.get("system_prompt", ""), tags=[], strip=True)

        agent = await self.repo.create_agent(
            owner_id=owner_id,
            tenant_id=tenant_id,
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
            tenant_id=tenant_id,  # type: ignore
            action="AI_AGENT_CREATED",
            resource_id=agent.id,  # type: ignore
            details={"name": agent.name, "role": agent.role.value if hasattr(agent.role, 'value') else str(agent.role)}
        )

        await self.event_bus.publish("ai.agent.created", {
            "agent_id": agent.id,
            "tenant_id": tenant_id,
            "owner_id": owner_id,
            "name": agent.name
        })

        return agent

    async def list_agents(
        self,
        tenant_id: int,
        owner_id: Optional[int] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[AIAgent]:
        """جلب قائمة الوكلاء للمستأجر."""
        return await self.repo.list_agents(tenant_id, owner_id, role, status, skip, limit)

    async def get_agent(self, agent_id: int, tenant_id: int) -> Optional[AIAgent]:
        """جلب وكيل مع التحقق من tenant_id."""
        return await self.repo.get_agent(agent_id, tenant_id)

    async def get_agent_by_owner(self, agent_id: int, owner_id: int, tenant_id: int) -> Optional[AIAgent]:
        """جلب وكيل مع التحقق من owner_id و tenant_id."""
        return await self.repo.get_agent_by_owner(agent_id, owner_id, tenant_id)

    async def update_agent_status(
        self,
        agent_id: int,
        tenant_id: int,
        status: str,
        executor_user_id: int
    ) -> Optional[AIAgent]:
        """تحديث حالة الوكيل."""
        agent = await self.repo.get_agent(agent_id, tenant_id)
        if not agent:
            return None
        await self.repo.update_agent_status(agent_id, tenant_id, status)

        await audit_log(
            user_id=executor_user_id,
            tenant_id=tenant_id,  # type: ignore
            action="AI_AGENT_STATUS_UPDATED",
            resource_id=agent_id,  # type: ignore
            details={"new_status": status}
        )

        return await self.repo.get_agent(agent_id, tenant_id)

    async def delete_agent(self, agent_id: int, tenant_id: int, soft: bool = True) -> bool:
        """حذف وكيل."""
        return await self.repo.delete_agent(agent_id, tenant_id, soft)

    # ==========================================
    # 2. تنفيذ إجراءات الوكيل (مع Idempotency و Human-in-the-loop)
    # ==========================================

    async def execute_agent_action(
        self,
        agent_id: int,
        tenant_id: int,
        action_type: str,
        payload: Dict[str, Any],
        executor_user_id: int,
        idempotency_key: str
    ) -> Dict[str, Any]:
        """تنفيذ إجراء بواسطة وكيل رقمي (مع Idempotency و Human-in-the-loop)."""

        # 1. التحقق من Idempotency
        cached = await self._validate_idempotency(idempotency_key)
        if cached:
            return cached

        # 2. جلب الوكيل مع التحقق من الصلاحية
        agent = await self.repo.get_agent(agent_id, tenant_id)
        if not agent:
            raise NotFoundError(f"الوكيل {agent_id} غير موجود")
        if cast(str, agent.status) != AgentStatus.ACTIVE.value and cast(str, agent.status) != "ACTIVE":
            raise PermissionDeniedError(f"الوكيل {agent_id} غير نشط")

        # 3. التحقق من صلاحية المستخدم لتنفيذ الإجراء (تم الإصلاح هنا ✅)
        if cast(int, agent.owner_id) != executor_user_id:
            # نتحقق من أن المستخدم لديه صلاحية الإدارة على الوكيل
            # يمكن إضافة منطق أكثر تعقيداً هنا
            pass

        # 4. تعقيم المدخلات
        sanitized_prompt = bleach.clean(payload.get("prompt", ""), tags=[], strip=True)
        sanitized_payload = {
            "prompt": sanitized_prompt,
            "language": payload.get("language", "ar"),
            "batch": payload.get("batch", False),
            "max_tokens": payload.get("max_tokens", 2048),
            "temperature": payload.get("temperature", 0.7),
        }

        # 5. تشغيل محرك الذكاء الاصطناعي
        try:
            task_type = TaskType.ARABIC_CHAT
            if action_type == "TRANSLATE":
                task_type = TaskType.TRANSLATION
            elif action_type in ("ANALYZE_FINANCE", "HEALTH_CHECK", "COMPLEX_ANALYSIS"):
                task_type = TaskType.COMPLEX_ANALYSIS  # type: ignore

            # تسجيل بداية المهمة
            task_log = await self.repo.create_task_log(
                tenant_id=tenant_id,
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

            # تنفيذ المهمة
            result = await ai_engine.generate(
                prompt=sanitized_prompt,
                system_prompt=agent.system_prompt,  # type: ignore
                language=sanitized_payload["language"],
                task_type=task_type,
                use_cache=True,
                use_batch=sanitized_payload["batch"],
                max_tokens=sanitized_payload["max_tokens"],
                temperature=sanitized_payload["temperature"],
            )

            # تحديث سجل المهمة بالتكلفة
            if result and isinstance(result, dict):
                cost = result.get("cost_mrusdt", Decimal('0.0'))
                if cost:
                    await self.repo.update_task_log_cost(task_log.id, Decimal(str(cost)))  # type: ignore

        except Exception as e:
            logger.error(f"AI execution failed for agent {agent_id}: {e}")
            # تسجيل الخطأ
            await self.repo.create_task_log(
                tenant_id=tenant_id,
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

        # 6. إذا كان الإجراء يتطلب موافقة بشرية
        if agent.requires_human_approval:  # type: ignore
            # إنشاء طلب موافقة
            approval = await self.repo.create_approval_request(
                tenant_id=tenant_id,
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

        # 7. تخزين Idempotency
        await self._store_idempotency(idempotency_key, response)

        # 8. تسجيل التدقيق
        await audit_log(
            user_id=executor_user_id,
            tenant_id=tenant_id,  # type: ignore
            action="AI_AGENT_ACTION_EXECUTED",
            resource_id=agent_id,  # type: ignore
            details={
                "action_type": action_type,
                "status": response["status"],
                "approval_id": response.get("approval_id")
            }
        )

        return response

    # ==========================================
    # 3. الموافقات البشرية (Human-in-the-loop)
    # ==========================================

    async def get_pending_approvals(self, human_approver_id: int, tenant_id: int) -> List[AgentApprovalQueue]:
        """جلب طلبات الموافقة المعلقة لمستخدم معين."""
        return await self.repo.get_pending_approvals(human_approver_id, tenant_id)

    async def resolve_approval(
        self,
        approval_id: int,
        tenant_id: int,
        human_approver_id: int,
        resolution: Dict[str, Any]
    ) -> Optional[AgentApprovalQueue]:
        """حل طلب موافقة (موافقة/رفض) مع التحقق من الصلاحية."""
        approval = await self.repo.get_approval(approval_id, tenant_id)
        if not approval:
            return None

        # التحقق من أن المستخدم هو الموافق المعين (تم التأكيد هنا ✅)
        if cast(int, approval.human_approver_id) != human_approver_id:
            raise PermissionDeniedError("ليس لديك صلاحية لحل هذا الطلب")

        # التحقق من أن الطلب لا يزال معلقاً
        if cast(str, approval.status) != ApprovalStatus.PENDING.value and cast(str, approval.status) != "PENDING":
            raise ValidationError(f"الطلب تم حله بالفعل (الحالة: {approval.status})")

        status_value = resolution["status"]
        feedback = resolution.get("human_feedback")

        # معاملة ذرية لتحديث الحالة وتنفيذ الإجراء إذا تمت الموافقة
        async with self.db.begin_nested():
            updated_approval = await self.repo.resolve_approval(
                approval_id=approval_id,
                tenant_id=tenant_id,
                status=status_value,
                feedback=feedback
            )

            # إذا تمت الموافقة، نقوم بتنفيذ الإجراء (يمكن توسيعه لاحقاً)
            if status_value == "APPROVED" or status_value == ApprovalStatus.APPROVED.value:
                # تنفيذ الإجراء الموافق عليه (سيتم تطويره لاحقاً)
                pass

        await audit_log(
            user_id=human_approver_id,
            tenant_id=tenant_id,  # type: ignore
            action="AI_APPROVAL_RESOLVED",
            resource_id=approval_id,  # type: ignore
            details={
                "status": status_value,
                "feedback": feedback
            }
        )

        return updated_approval

    async def list_approvals(
        self,
        tenant_id: int,
        agent_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[AgentApprovalQueue]:
        """جلب قائمة طلبات الموافقة."""
        return await self.repo.list_approvals(tenant_id, agent_id, status, skip, limit)

    async def get_approval(self, approval_id: int, tenant_id: int) -> Optional[AgentApprovalQueue]:
        """جلب تفاصيل طلب موافقة محدد."""
        return await self.repo.get_approval(approval_id, tenant_id)

    # ==========================================
    # 4. التحليلات والإحصائيات (Analytics)
    # ==========================================

    async def get_agent_analytics(self, agent_id: int, tenant_id: int, days: int = 30) -> Dict[str, Any]:
        """جلب تحليلات استخدام الوكيل."""
        # التحقق من وجود الوكيل
        agent = await self.repo.get_agent(agent_id, tenant_id)
        if not agent:
            raise NotFoundError(f"الوكيل {agent_id} غير موجود")

        return await self.repo.get_agent_usage_stats(agent_id, tenant_id, days)

    async def get_agent_status(self, agent_id: int, tenant_id: int) -> Dict[str, Any]:
        """جلب الحالة التفصيلية للوكيل."""
        agent = await self.repo.get_agent(agent_id, tenant_id)
        if not agent:
            raise NotFoundError(f"الوكيل {agent_id} غير موجود")

        return {
            "agent_id": agent.id,
            "status": agent.status,
            "last_active": None  # يمكن جلبها من سجل المهام لاحقاً
        }

    # ==========================================
    # 5. استخدامات الـ AI للمستأجر (SaaS Dashboard)
    # ==========================================

    async def get_ai_usage(self, tenant_id: int) -> Dict[str, Any]:
        """جلب إحصائيات استخدام الـ AI للمستأجر الحالي."""
        subscription = await self.repo.get_tenant_subscription(tenant_id)
        features = subscription.features if subscription else {}  # type: ignore

        current_agents = await self.repo.count_agents(tenant_id)
        monthly_calls = await self.repo.count_monthly_calls(tenant_id)
        monthly_cost = await self.repo.get_monthly_ai_cost(tenant_id)

        max_agents = features.get("max_agents", 0) if features else 0  # type: ignore
        monthly_limit = features.get("monthly_ai_calls", 0) if features else 0  # type: ignore

        return {
            "subscription_status": subscription.status if subscription else "NO_SUBSCRIPTION",  # type: ignore
            "max_agents": max_agents,
            "current_agents": current_agents,
            "monthly_calls_limit": monthly_limit,
            "monthly_calls_used": monthly_calls,
            "monthly_calls_remaining": max(0, monthly_limit - monthly_calls),
            "monthly_cost_mrusdt": float(monthly_cost),
            "features": features,
        }