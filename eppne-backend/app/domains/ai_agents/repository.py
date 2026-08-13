# app/domains/ai_agents/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, delete
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, timedelta

from app.domains.ai_agents.models import AIAgent, AgentApprovalQueue, ApprovalStatus, AITaskLog
from app.domains.ai_agents.schemas import AIAgentResponse, ApprovalResponse, AITaskLogResponse
from app.core.errors import NotFoundError, PermissionDeniedError
from app.core.pagination import PaginatedResponse


class AIAgentsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ==========================================
    # 1. الوكلاء الرقميون (مع tenant_id)
    # ==========================================

    async def create_agent(self, **kwargs) -> AIAgent:
        agent = AIAgent(**kwargs)
        self.db.add(agent)
        await self.db.commit()
        await self.db.refresh(agent)
        return agent

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

    async def get_agent_by_owner(
        self,
        agent_id: int,
        owner_id: int,
        tenant_id: int
    ) -> Optional[AIAgent]:
        result = await self.db.execute(
            select(AIAgent).where(
                and_(
                    AIAgent.id == agent_id,
                    AIAgent.owner_id == owner_id,
                    AIAgent.tenant_id == tenant_id,
                    AIAgent.is_deleted == False
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_agents(
        self,
        tenant_id: int,
        owner_id: Optional[int] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> PaginatedResponse[AIAgentResponse]:
        query = select(AIAgent).where(
            and_(
                AIAgent.tenant_id == tenant_id,
                AIAgent.is_deleted == False
            )
        )
        if owner_id:
            query = query.where(AIAgent.owner_id == owner_id)
        if role:
            query = query.where(AIAgent.role == role)
        if status:
            query = query.where(AIAgent.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = [AIAgentResponse.model_validate(agent) for agent in result.scalars().all()]

        return PaginatedResponse[AIAgentResponse](
            data=items,
            total=total,
            skip=skip,
            limit=limit
        )

    async def update_agent_status(
        self,
        agent_id: int,
        tenant_id: int,
        status: str
    ) -> Optional[AIAgent]:
        agent = await self.get_agent(agent_id, tenant_id)
        if not agent:
            return None
        await self.db.execute(
            update(AIAgent).where(AIAgent.id == agent_id).values(status=status)
        )
        await self.db.commit()
        return await self.get_agent(agent_id, tenant_id)

    async def delete_agent(self, agent_id: int, tenant_id: int, soft: bool = True) -> bool:
        if soft:
            await self.db.execute(
                update(AIAgent)
                .where(and_(AIAgent.id == agent_id, AIAgent.tenant_id == tenant_id))
                .values(is_deleted=True, deleted_at=func.now())
            )
        else:
            await self.db.execute(
                delete(AIAgent).where(and_(AIAgent.id == agent_id, AIAgent.tenant_id == tenant_id))
            )
        await self.db.commit()
        return True

    # ==========================================
    # 2. صمام الأمان البشري (مع tenant_id)
    # ==========================================

    async def create_approval_request(self, tenant_id: int, **kwargs) -> AgentApprovalQueue:
        request = AgentApprovalQueue(tenant_id=tenant_id, **kwargs)
        self.db.add(request)
        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def get_approval_by_idempotency(self, idempotency_key: str, tenant_id: int) -> Optional[AgentApprovalQueue]:
        result = await self.db.execute(
            select(AgentApprovalQueue)
            .join(AIAgent, AgentApprovalQueue.agent_id == AIAgent.id)
            .where(
                and_(
                    AgentApprovalQueue.idempotency_key == idempotency_key,
                    AIAgent.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_pending_approvals(
        self,
        human_approver_id: int,
        tenant_id: int
    ) -> List[AgentApprovalQueue]:
        result = await self.db.execute(
            select(AgentApprovalQueue)
            .join(AIAgent, AgentApprovalQueue.agent_id == AIAgent.id)
            .where(
                and_(
                    AgentApprovalQueue.human_approver_id == human_approver_id,
                    AgentApprovalQueue.status == ApprovalStatus.PENDING,
                    AIAgent.tenant_id == tenant_id
                )
            )
            .order_by(AgentApprovalQueue.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_approval(self, approval_id: int, tenant_id: int) -> Optional[AgentApprovalQueue]:
        result = await self.db.execute(
            select(AgentApprovalQueue)
            .join(AIAgent, AgentApprovalQueue.agent_id == AIAgent.id)
            .where(
                and_(
                    AgentApprovalQueue.id == approval_id,
                    AIAgent.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def resolve_approval(
        self,
        approval_id: int,
        tenant_id: int,
        status: str,
        feedback: Optional[str] = None
    ) -> Optional[AgentApprovalQueue]:
        approval = await self.get_approval(approval_id, tenant_id)
        if not approval:
            return None
        values = {"status": status, "resolved_at": func.now()}
        if feedback:
            values["human_feedback"] = feedback
        await self.db.execute(
            update(AgentApprovalQueue).where(AgentApprovalQueue.id == approval_id).values(**values)
        )
        await self.db.flush()
        return await self.get_approval(approval_id, tenant_id)

    async def list_approvals(
        self,
        tenant_id: int,
        agent_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> PaginatedResponse[ApprovalResponse]:
        query = (
            select(AgentApprovalQueue)
            .join(AIAgent, AgentApprovalQueue.agent_id == AIAgent.id)
            .where(AIAgent.tenant_id == tenant_id)
        )
        if agent_id:
            query = query.where(AgentApprovalQueue.agent_id == agent_id)
        if status:
            query = query.where(AgentApprovalQueue.status == status)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(AgentApprovalQueue.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = [ApprovalResponse.model_validate(item) for item in result.scalars().all()]

        return PaginatedResponse[ApprovalResponse](
            data=items,
            total=total,
            skip=skip,
            limit=limit
        )

    # ==========================================
    # 3. سجل استهلاك الذكاء الاصطناعي (مع tenant_id)
    # ==========================================

    async def create_task_log(self, tenant_id: int, **kwargs) -> AITaskLog:
        log = AITaskLog(tenant_id=tenant_id, **kwargs)
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log

    async def get_task_log_by_idempotency(self, idempotency_key: str, tenant_id: int) -> Optional[AITaskLog]:
        result = await self.db.execute(
            select(AITaskLog).where(
                and_(
                    AITaskLog.idempotency_key == idempotency_key,
                    AITaskLog.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_task_log(self, log_id: int, tenant_id: int) -> Optional[AITaskLog]:
        result = await self.db.execute(
            select(AITaskLog).where(
                and_(AITaskLog.id == log_id, AITaskLog.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()

    async def list_task_logs(
        self,
        tenant_id: int,
        agent_id: Optional[int] = None,
        user_id: Optional[int] = None,
        task_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> PaginatedResponse[AITaskLogResponse]:
        query = select(AITaskLog).where(AITaskLog.tenant_id == tenant_id)
        if agent_id:
            query = query.where(AITaskLog.agent_id == agent_id)
        if user_id:
            query = query.where(AITaskLog.user_id == user_id)
        if task_type:
            query = query.where(AITaskLog.task_type == task_type)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(AITaskLog.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = [AITaskLogResponse.model_validate(item) for item in result.scalars().all()]

        return PaginatedResponse[AITaskLogResponse](
            data=items,
            total=total,
            skip=skip,
            limit=limit
        )

    async def get_agent_usage_stats(
        self,
        agent_id: int,
        tenant_id: int,
        days: int = 30
    ) -> dict:
        start_date = datetime.utcnow() - timedelta(days=days)

        cost_result = await self.db.execute(
            select(func.sum(AITaskLog.cost_mrusdt))
            .where(
                and_(
                    AITaskLog.agent_id == agent_id,
                    AITaskLog.tenant_id == tenant_id,
                    AITaskLog.created_at >= start_date
                )
            )
        )
        total_cost = cost_result.scalar() or 0

        count_result = await self.db.execute(
            select(func.count(AITaskLog.id))
            .where(
                and_(
                    AITaskLog.agent_id == agent_id,
                    AITaskLog.tenant_id == tenant_id,
                    AITaskLog.created_at >= start_date
                )
            )
        )
        total_tasks = count_result.scalar() or 0

        type_result = await self.db.execute(
            select(AITaskLog.task_type, func.count(AITaskLog.id))
            .where(
                and_(
                    AITaskLog.agent_id == agent_id,
                    AITaskLog.tenant_id == tenant_id,
                    AITaskLog.created_at >= start_date
                )
            )
            .group_by(AITaskLog.task_type)
        )
        tasks_by_type = {row[0]: row[1] for row in type_result.all()}

        return {
            "total_cost_mrusdt": float(total_cost),
            "total_tasks": total_tasks,
            "tasks_by_type": tasks_by_type,
            "days": days,
        }

    # ==========================================
    # دوال العد والحدود (مع tenant_id)
    # ==========================================

    async def count_agents(self, tenant_id: int) -> int:
        result = await self.db.execute(
            select(func.count(AIAgent.id))
            .where(
                and_(
                    AIAgent.tenant_id == tenant_id,
                    AIAgent.is_deleted == False
                )
            )
        )
        return result.scalar() or 0

    async def count_monthly_calls(self, tenant_id: int) -> int:
        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        result = await self.db.execute(
            select(func.count(AITaskLog.id))
            .where(
                and_(
                    AITaskLog.tenant_id == tenant_id,
                    AITaskLog.created_at >= start_of_month
                )
            )
        )
        return result.scalar() or 0

    async def get_monthly_ai_cost(self, tenant_id: int) -> Decimal:
        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        result = await self.db.execute(
            select(func.sum(AITaskLog.cost_mrusdt))
            .where(
                and_(
                    AITaskLog.tenant_id == tenant_id,
                    AITaskLog.created_at >= start_of_month
                )
            )
        )
        return result.scalar() or Decimal(0)

    async def get_tenant_subscription(self, tenant_id: int):
        from app.domains.saas.models import TenantSubscription
        result = await self.db.execute(
            select(TenantSubscription)
            .where(
                and_(
                    TenantSubscription.tenant_id == tenant_id,
                    TenantSubscription.status == "ACTIVE"
                )
            )
        )
        return result.scalar_one_or_none()

    # ==========================================
    # تحديث تكلفة المهمة
    # ==========================================

    async def update_task_log_cost(self, log_id: int, cost: Decimal) -> AITaskLog:
        await self.db.execute(
            update(AITaskLog)
            .where(AITaskLog.id == log_id)
            .values(cost_mrusdt=cost)
        )
        await self.db.commit()
        result = await self.db.execute(select(AITaskLog).where(AITaskLog.id == log_id))
        return result.scalar_one()

    # ==========================================
    # دوال نقاط التفتيش للفوترة (Checkpoints)
    # ==========================================

    async def get_last_billed_month(self, tenant_id: int) -> Optional[datetime]:
        from app.domains.saas.models import TenantSubscription
        result = await self.db.execute(
            select(TenantSubscription.last_billed_month)
            .where(TenantSubscription.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def update_last_billed_month(self, tenant_id: int, month: datetime):
        from app.domains.saas.models import TenantSubscription
        await self.db.execute(
            update(TenantSubscription)
            .where(TenantSubscription.tenant_id == tenant_id)
            .values(last_billed_month=month)
        )
        await self.db.commit()