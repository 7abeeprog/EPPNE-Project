# app/domains/ai_agents/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import uuid
import json
import re
from decimal import Decimal
from typing import Optional
import bleach  # 🔥 تثبيت: pip install bleach

from app.domains.ai_agents.repository import AIAgentsRepository
from app.domains.finance.service import FinanceService
from app.domains.affiliate.service import AffiliateService
from app.core.errors import PermissionDeniedError, NotFoundError, IdempotencyError, QuotaExceededError
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.domains.ai_agents.models import AIAgent, AgentStatus, ApprovalStatus, AgentApprovalQueue

# 🔥 إضافات جديدة
from app.core.features import SystemFeatures
from app.core.logging import logger
from app.core.llm_factory import LLMFactory  # 🔥 مصنع النماذج اللغوية
from app.domains.ai_governance.service import AIGovernanceService  # 🔥 خدمة الحوكمة

# قائمة الأنواع المسموح بها لتقليل خطر الـ Prompt Injection
ALLOWED_ACTION_TYPES = {
    "TRANSFER_FUNDS", "SIGN_CONTRACT", "SHUTDOWN_FACTORY", "DEPLOY_CODE",
    "ANALYZE_SENSOR", "ASSIGN_COURSE", "ANALYZE_PROJECT", "FORECAST_FUNDING",
    "GENERATE_QUIZ", "GRADE_SUBMISSION", "SEND_EMAIL", "CREATE_TICKET",
    "SWARM_ORCHESTRATION"  # 🔥 إضافة نوع جديد لتنسيق الوكلاء
}


class AIAgentsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AIAgentsRepository(db)
        self.finance = FinanceService(db)
        self.affiliate_service = AffiliateService(db)
        self.event_bus = EventBus(redis_client)
        self.redis = redis_client

    # ============================================================
    # 0. التحقق من حالة النظام (Kill Switch)
    # ============================================================

    async def _check_system_status(self):
        """التحقق من حالة النظام العامة (Kill Switch)."""
        if await SystemFeatures.get_system_suspended():
            raise PermissionDeniedError(
                "System is temporarily suspended for maintenance. Please try again later."
            )

    # ============================================================
    # 1. دوال مساعدة للاشتراكات والحدود
    # ============================================================

    async def _get_tenant_subscription(self, tenant_id: int):
        """
        جلب اشتراك المستأجر (يفترض وجود نموذج Subscription).
        """
        try:
            from app.domains.subscriptions.models import TenantSubscription
            from sqlalchemy import select
            result = await self.db.execute(
                select(TenantSubscription).where(
                    TenantSubscription.tenant_id == tenant_id,
                    TenantSubscription.is_active == True
                )
            )
            subscription = result.scalar_one_or_none()
            if not subscription:
                return self._get_default_subscription()
            return subscription
        except ImportError:
            return self._get_default_subscription()

    def _get_default_subscription(self):
        """اشتراك افتراضي للاختبار."""
        class DefaultSubscription:
            features = {
                "ai_agents": True,
                "max_agents": 5,
                "monthly_ai_calls": 1000,
            }
        return DefaultSubscription()

    async def _get_subscription_features(self, tenant_id: int) -> dict:
        """جلب ميزات الاشتراك كـ dict."""
        subscription = await self._get_tenant_subscription(tenant_id)
        return getattr(subscription, "features", {
            "ai_agents": True,
            "max_agents": 5,
            "monthly_ai_calls": 1000,
        })

    async def _increment_monthly_calls(self, tenant_id: int, agent_id: int):
        """زيادة عداد المكالمات الشهرية."""
        key = f"ai_agent_calls:{tenant_id}:{datetime.utcnow().strftime('%Y-%m')}"
        await self.redis.incr(key)
        await self.redis.expire(key, 60 * 60 * 24 * 31)

    async def _count_monthly_calls(self, tenant_id: int) -> int:
        """جلب عدد المكالمات الشهرية للمستأجر."""
        key = f"ai_agent_calls:{tenant_id}:{datetime.utcnow().strftime('%Y-%m')}"
        value = await self.redis.get(key)
        return int(value) if value else 0

    # ============================================================
    # 2. دوال التحقق من SaaS والحدود
    # ============================================================

    async def _check_saas_limits(self, tenant_id: int):
        """التحقق من صلاحية الـ AI في خطة الاشتراك."""
        subscription = await self.repo.get_tenant_subscription(tenant_id)
        if not subscription:
            raise PermissionDeniedError("No active subscription found for this entity.")
        
        features = subscription.features or {}
        if not features.get("ai_agents", False):
            raise PermissionDeniedError("AI Agents feature is not included in your current plan.")
        
        return subscription, features

    async def _check_agent_quota(self, tenant_id: int, features: dict):
        """التحقق من عدم تجاوز الحد الأقصى للوكلاء."""
        max_agents = features.get("max_agents", 1)
        current_agents = await self.repo.count_agents(tenant_id)
        if current_agents >= max_agents:
            raise QuotaExceededError(
                f"You have reached the maximum limit of {max_agents} agents. "
                "Upgrade your plan to add more agents."
            )

    async def _check_monthly_calls_quota(self, tenant_id: int, features: dict):
        """التحقق من عدم تجاوز الحد الشهري للمكالمات."""
        monthly_limit = features.get("monthly_ai_calls", 100)
        current_calls = await self.repo.count_monthly_calls(tenant_id)
        if current_calls >= monthly_limit:
            raise QuotaExceededError(
                f"Monthly AI call limit of {monthly_limit} exceeded. "
                "Upgrade your plan or wait for next month."
            )

    # ============================================================
    # 3. إنشاء وكيل (مع التحقق من الاشتراك والحد الأقصى والإحالة)
    # ============================================================

    async def create_agent(self, owner_id: int, tenant_id: int, data: dict) -> AIAgent:
        """
        إنشاء وكيل جديد مع التحقق من صلاحية الاشتراك والحد الأقصى للوكلاء والإحالة.
        """
        # 🔥 0. التحقق من مفتاح القتل (أول طبقة دفاع)
        await self._check_system_status()

        # 🔥 1. التحقق من صلاحية SaaS والحد الأقصى
        subscription, features = await self._check_saas_limits(tenant_id)
        await self._check_agent_quota(tenant_id, features)

        # 🔥 2. التحقق من صلاحية إنشاء أدوار حساسة
        sensitive_roles = ["CEO", "SWARM_ORCHESTRATOR", "SURVIVAL_CRISIS"]
        if data.get("role") in sensitive_roles and owner_id != 1:
            raise PermissionDeniedError(f"Role {data.get('role')} requires special permissions.")

        # 🔥 3. تعقيم الـ system_prompt
        sanitized_prompt = bleach.clean(
            data.get("system_prompt", ""),
            tags=[],
            strip=True
        )
        data["system_prompt"] = sanitized_prompt

        # 🔥 4. ربط الإحالة (Affiliate)
        user = await self._get_user(owner_id)
        if user and user.referred_by:
            commission_amount = Decimal("5.00")
            await self.affiliate_service.register_commission(
                affiliate_id=user.referred_by,
                user_id=owner_id,
                amount=commission_amount,
                description=f"AI Agent creation: {data.get('name', 'Unknown Agent')}",
                status="PENDING"
            )

        # 🔥 5. إنشاء الوكيل
        agent = await self.repo.create_agent(
            owner_id=owner_id,
            tenant_id=tenant_id,
            **data
        )

        # 🔥 6. نشر حدث
        await self.event_bus.publish("agent.created", {
            "agent_id": agent.id,
            "tenant_id": tenant_id,
            "owner_id": owner_id,
            "name": agent.name,
            "role": agent.role.value
        })

        return agent

    # ============================================================
    # 4. تنفيذ مهمة وكيل (مع Idempotency والحد الشهري والفوترة والحوكمة)
    # ============================================================

    async def execute_agent_action(
        self,
        agent_id: int,
        tenant_id: int,
        action_type: str,
        payload: dict,
        executor_user_id: int,
        idempotency_key: Optional[str] = None
    ) -> dict:
        """
        تنفيذ مهمة بواسطة وكيل مع دعم Idempotency والتحقق من الصلاحيات والحد الشهري والفوترة والحوكمة.
        """
        # 🔥 0. التحقق من مفتاح القتل (أول طبقة دفاع)
        await self._check_system_status()

        redis_key = None

        # 🔥 1. التحقق من صلاحية SaaS والحدود الشهرية
        subscription, features = await self._check_saas_limits(tenant_id)
        await self._check_monthly_calls_quota(tenant_id, features)

        # 🔥 2. التحقق من Idempotency (قفل ذري)
        if idempotency_key:
            redis_key = f"idempotency_ai:{idempotency_key}"
            acquired = await self.redis.setnx(redis_key, json.dumps({"status": "processing"}))
            if not acquired:
                cached = await self.redis.get(redis_key)
                if cached:
                    return json.loads(cached)
                raise IdempotencyError("Request already being processed")
            await self.redis.expire(redis_key, 3600)

        try:
            # 🔥 3. التحقق من العزل السيادي والملكية
            agent = await self.repo.get_agent_by_owner(agent_id, executor_user_id, tenant_id)
            if not agent:
                raise NotFoundError("Agent not found or you don't have permission to access it.")
            if agent.status != AgentStatus.ACTIVE:
                raise PermissionDeniedError("Agent is not active.")

            # 🔥 4. التحقق من صحة نوع الإجراء
            if action_type not in ALLOWED_ACTION_TYPES:
                raise ValueError(f"Action type '{action_type}' is not allowed.")

            # 🔥 5. تعقيم الـ Payload
            sanitized_payload = self._sanitize_payload(payload)

            # 🔥 6. تسجيل المهمة (بدون تكلفة مبدئياً)
            task_log = await self.repo.create_task_log(
                tenant_id=tenant_id,
                agent_id=agent_id,
                user_id=executor_user_id,
                task_type=action_type,
                idempotency_key=idempotency_key,
                prompt_tokens=0,
                completion_tokens=0,
                cost_mrusdt=Decimal(0)
            )

            # 🔥 7. إذا كان الإجراء يحتاج موافقة بشرية
            sensitive_actions = ["TRANSFER_FUNDS", "SIGN_CONTRACT", "SHUTDOWN_FACTORY", "DEPLOY_CODE"]
            if agent.requires_human_approval and action_type in sensitive_actions:
                if idempotency_key:
                    existing = await self.repo.get_approval_by_idempotency(idempotency_key)
                    if existing:
                        result = {
                            "status": "PENDING_APPROVAL",
                            "approval_id": existing.id,
                            "message": "Approval request already exists for this key."
                        }
                        if redis_key:
                            await self.redis.setex(redis_key, 3600, json.dumps(result))
                        return result

                approval = await self.repo.create_approval_request(
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    human_approver_id=agent.owner_id,
                    action_type=action_type,
                    proposed_payload=sanitized_payload,
                    idempotency_key=idempotency_key,
                    status=ApprovalStatus.PENDING
                )

                await self.event_bus.publish("agent.approval.requested", {
                    "approval_id": approval.id,
                    "agent_id": agent_id,
                    "action_type": action_type,
                    "approver_id": agent.owner_id,
                    "tenant_id": tenant_id,
                    "timestamp": datetime.utcnow().isoformat()
                })

                result = {
                    "status": "PENDING_APPROVAL",
                    "approval_id": approval.id,
                    "message": "Action pending human approval."
                }
                if redis_key:
                    await self.redis.setex(redis_key, 3600, json.dumps(result))

                await self._increment_monthly_calls(tenant_id, agent_id)
                return result

            # 🔥 8. تنفيذ الإجراء تلقائياً (مع تمرير معلومات الحوكمة)
            result_data = await self._execute_action(
                agent=agent,
                action_type=action_type,
                payload=sanitized_payload,
                executor_user_id=executor_user_id,
                idempotency_key=idempotency_key,
                tenant_id=tenant_id
            )

            # 🔥 9. حساب التكلفة وتسجيلها
            cost_per_call = Decimal("0.01")
            total_cost = cost_per_call

            # تحديث سجل المهمة بالتكلفة الفعلية
            await self.repo.update_task_log_cost(task_log.id, total_cost)

            # 🔥 10. خصم التكلفة من محفظة العميل (إذا وُجدت)
            if agent.agent_wallet_address:
                await self.finance.transfer(
                    sender=agent.agent_wallet_address,
                    receiver="system_wallet",
                    amount=total_cost,
                    notes=f"AI Agent {agent.name} execution cost - {action_type}",
                    currency="MR_USDT"
                )

            # 🔥 11. زيادة عداد المكالمات الشهرية
            await self._increment_monthly_calls(tenant_id, agent_id)

            result = {
                "status": "EXECUTED",
                "result": result_data,
                "task_log_id": task_log.id,
                "cost": float(total_cost)
            }

            if redis_key:
                await self.redis.setex(redis_key, 3600, json.dumps(result))

            return result

        except Exception as e:
            if redis_key:
                await self.redis.delete(redis_key)
            raise

    # ============================================================
    # 5. معالج الإجراءات الداخلية (مع اختيار النموذج والحوكمة)
    # ============================================================

    async def _select_model(self, action_type: str, payload: dict) -> str:
        """
        اختيار النموذج الأنسب باستخدام نظام مايسترو متعدد المستويات.
        
        الأولويات:
        1. المهام الحرجة (مالية، تعاقدية) → Claude 3.5 Sonnet
        2. المهام المعقدة جداً (برمجة، تنسيق وكلاء) → Kimi K2.6
        3. المهام المعقدة (تحليل مالي، برمجة متوسطة) → GPT-4o
        4. المهام المتوسطة (تحليل، توصيات) → Gemini Pro
        5. المهام البسيطة (تصنيف، استخراج) → Gemini Flash
        """
        # 1. المهام الحرجة (مالية، تعاقدية) → Claude
        if action_type in ["TRANSFER_FUNDS", "SIGN_CONTRACT"]:
            return "claude-3.5-sonnet"
        
        # 2. المهام المعقدة جداً (برمجة، تنسيق وكلاء) → Kimi K2.6
        if action_type in ["DEPLOY_CODE", "SWARM_ORCHESTRATION"]:
            return "kimi-k2.6"
        
        # 3. المهام المعقدة (تحليل مالي، برمجة متوسطة) → GPT-4o
        if action_type in ["ANALYZE_PROJECT", "FORECAST_FUNDING"]:
            return "gpt-4o"
        
        # 4. المهام المتوسطة (تحليل، توصيات) → Gemini Pro
        if action_type in ["ANALYZE_SENSOR"]:
            return "gemini-1.5-pro"
        
        # 5. المهام البسيطة (تصنيف، استخراج) → Gemini Flash
        return "gemini-1.5-flash"

    async def _execute_action(
        self,
        agent: AIAgent,
        action_type: str,
        payload: dict,
        executor_user_id: int,
        idempotency_key: Optional[str],
        tenant_id: int
    ) -> dict:
        """
        تنفيذ الإجراء الفعلي مع اختيار النموذج المناسب واستدعاء LLM،
        مع التحقق من الحوكمة (Choke-Point) قبل التنفيذ.
        """
        safe_payload = self._sanitize_payload(payload)

        # ============================================================
        # 🔥 نقطة الخنق (Choke-Point): التحقق من الحوكمة
        # ============================================================
        governance_service = AIGovernanceService(self.db)

        # تقدير عدد التوكنات (يمكن جعله دقيقاً لاحقاً)
        estimated_tokens = len(str(safe_payload)) // 4  # تقريبي
        estimated_cost = Decimal(estimated_tokens) * Decimal("0.000001")  # سعر تقريبي لكل توكن

        allowed = await governance_service.check_and_consume(
            tenant_id=tenant_id,
            agent_id=agent.id,
            user_id=executor_user_id,
            action_type=action_type,
            tokens=estimated_tokens,
            cost=estimated_cost,
            idempotency_key=idempotency_key,
            request_tokens=estimated_tokens // 2,
            completion_tokens=estimated_tokens // 2
        )

        if not allowed:
            raise PermissionDeniedError("Agent quota exceeded. Please check your usage limits.")

        # ============================================================
        # 1. اختيار النموذج
        # ============================================================
        model = await self._select_model(action_type, safe_payload)

        # 2. استدعاء المحول المناسب عبر LLMFactory
        try:
            adapter = LLMFactory.get_llm(model)
            response = await adapter.generate_response(
                system_prompt=agent.system_prompt,
                user_prompt=safe_payload.get("prompt", ""),
                context=safe_payload.get("context", {})
            )
        except Exception as e:
            logger.error(f"LLM call failed for model {model}: {e}")
            # Fallback: استخدام محاكاة بسيطة
            response = {
                "status": "fallback",
                "message": f"LLM unavailable, using fallback for {action_type}",
                "data": {"simulated": True}
            }

        # 3. بناء النتيجة
        return {
            "model": model,
            "response": response,
            "action": action_type,
            "agent": agent.name
        }

    # ============================================================
    # 6. تعقيم الـ Payload (منع Prompt Injection و XSS)
    # ============================================================

    def _sanitize_payload(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            return {}

        sanitized = {}
        for key, value in payload.items():
            if isinstance(value, str):
                cleaned = bleach.clean(value, tags=[], strip=True)
                cleaned = re.sub(
                    r'(?i)(exec|eval|system|shell|cmd|drop|delete|truncate|alter|create|insert|update|grant|revoke)\s*\(',
                    '',
                    cleaned
                )
                cleaned = re.sub(r'(?i)(<script|javascript:|onload=|onerror=|onclick=)', '', cleaned)
                sanitized[key] = cleaned[:5000]

            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_payload(value)

            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_payload(item) if isinstance(item, dict)
                    else bleach.clean(str(item), tags=[], strip=True) if isinstance(item, str)
                    else item
                    for item in value
                ]

            elif isinstance(value, (int, float, bool)):
                sanitized[key] = value

            else:
                sanitized[key] = str(value)[:5000]

        return sanitized

    # ============================================================
    # 7. الموافقة البشرية (مع العزل السيادي و Idempotency)
    # ============================================================

    async def resolve_approval(
        self,
        approval_id: int,
        tenant_id: int,
        human_approver_id: int,
        resolution: dict
    ) -> AgentApprovalQueue:
        approval = await self.repo.get_approval(approval_id, tenant_id)
        if not approval:
            raise NotFoundError("Approval not found.")

        if approval.human_approver_id != human_approver_id:
            raise PermissionDeniedError("You are not authorized to approve this action.")

        if approval.status != ApprovalStatus.PENDING:
            raise PermissionDeniedError("This approval has already been resolved.")

        status = resolution.get("status")
        feedback = resolution.get("human_feedback")

        if status not in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.CANCELLED]:
            raise ValueError("Invalid status. Allowed: APPROVED, REJECTED, CANCELLED.")

        safe_feedback = bleach.clean(feedback or "", tags=[], strip=True)[:1000]

        resolved = await self.repo.resolve_approval(
            approval_id,
            tenant_id,
            status,
            safe_feedback
        )

        if status == ApprovalStatus.APPROVED:
            agent = await self.repo.get_agent(approval.agent_id, tenant_id)
            if agent:
                # تمرير معلومات الحوكمة (المستخدم الموافق، لا يوجد idempotency_key)
                await self._execute_action(
                    agent=agent,
                    action_type=approval.action_type,
                    payload=approval.proposed_payload,
                    executor_user_id=human_approver_id,
                    idempotency_key=None,
                    tenant_id=tenant_id
                )

        await self.event_bus.publish("agent.approval.resolved", {
            "approval_id": approval.id,
            "agent_id": approval.agent_id,
            "status": status,
            "resolved_by": human_approver_id,
            "tenant_id": tenant_id,
            "feedback": safe_feedback[:200] if safe_feedback else None,
            "timestamp": datetime.utcnow().isoformat()
        })

        return resolved

    # ============================================================
    # 8. دوال إضافية (استعلامات، إحصائيات، الفوترة الشهرية)
    # ============================================================

    async def _get_user(self, user_id: int):
        from app.domains.identity.repository import UserRepository
        user_repo = UserRepository(self.db)
        return await user_repo.get_user(user_id)

    async def generate_monthly_invoice(self, tenant_id: int):
        total_cost = await self.repo.get_monthly_ai_cost(tenant_id)
        if total_cost > 0:
            invoice = await self.finance.create_invoice(
                entity_id=tenant_id,
                amount=total_cost,
                description=f"AI Agents usage for {datetime.utcnow().strftime('%B %Y')}",
                due_date=datetime.utcnow() + timedelta(days=30)
            )
            return invoice
        return None

    async def get_agent_status(self, agent_id: int, tenant_id: int) -> dict:
        agent = await self.repo.get_agent(agent_id, tenant_id)
        if not agent:
            raise NotFoundError("Agent not found.")

        return {
            "id": agent.id,
            "name": agent.name,
            "role": agent.role.value,
            "status": agent.status.value,
            "requires_human_approval": agent.requires_human_approval,
            "can_execute_payments": agent.can_execute_payments,
            "can_sign_contracts": agent.can_sign_contracts,
            "interaction_cost_mrusdt": float(agent.interaction_cost_mrusdt)
        }

    async def get_agent_analytics(self, agent_id: int, tenant_id: int, days: int = 30) -> dict:
        agent = await self.repo.get_agent(agent_id, tenant_id)
        if not agent:
            raise NotFoundError("Agent not found.")

        return await self.repo.get_agent_usage_stats(agent_id, tenant_id, days)

    async def list_agents(
        self,
        tenant_id: int,
        owner_id: Optional[int] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> list:
        return await self.repo.list_agents(tenant_id, owner_id, role, status, skip, limit)

    async def update_agent_status(
        self,
        agent_id: int,
        tenant_id: int,
        status: str,
        executor_user_id: int
    ) -> AIAgent:
        agent = await self.repo.get_agent_by_owner(agent_id, executor_user_id, tenant_id)
        if not agent:
            raise NotFoundError("Agent not found or you don't have permission.")

        if status not in [s.value for s in AgentStatus]:
            raise ValueError(f"Invalid status. Allowed: {[s.value for s in AgentStatus]}")

        return await self.repo.update_agent_status(agent_id, tenant_id, status)