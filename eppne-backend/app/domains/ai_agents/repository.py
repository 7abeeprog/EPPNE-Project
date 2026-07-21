# app/domains/ai_agents/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, delete
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, timedelta

from app.domains.ai_agents.models import AIAgent, AgentApprovalQueue, ApprovalStatus, AITaskLog
from app.core.errors import NotFoundError, PermissionDeniedError


class AIAgentsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ==========================================
    # 1. الوكلاء الرقميون (مع فرض العزل السيادي)
    # ==========================================

    async def create_agent(self, **kwargs) -> AIAgent:
        """إنشاء وكيل جديد (يتضمن tenant_id و owner_id)."""
        agent = AIAgent(**kwargs)
        self.db.add(agent)
        await self.db.commit()
        await self.db.refresh(agent)
        return agent

    async def get_agent(self, agent_id: int, tenant_id: int) -> Optional[AIAgent]:
        """جلب وكيل مع التأكد من tenant_id."""
        result = await self.db.execute(
            select(AIAgent).where(
                AIAgent.id == agent_id,
                AIAgent.tenant_id == tenant_id,
                AIAgent.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def get_agent_by_owner(
        self,
        agent_id: int,
        owner_id: int,
        tenant_id: int
    ) -> Optional[AIAgent]:
        """جلب وكيل مع التأكد من owner_id و tenant_id (للتحقق من الصلاحيات)."""
        result = await self.db.execute(
            select(AIAgent).where(
                AIAgent.id == agent_id,
                AIAgent.owner_id == owner_id,
                AIAgent.tenant_id == tenant_id,
                AIAgent.is_deleted == False
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
    ) -> List[AIAgent]:
        """قائمة الوكلاء مع فلترة حسب tenant_id وخيارات إضافية."""
        query = select(AIAgent).where(
            AIAgent.tenant_id == tenant_id,
            AIAgent.is_deleted == False
        )
        if owner_id:
            query = query.where(AIAgent.owner_id == owner_id)
        if role:
            query = query.where(AIAgent.role == role)
        if status:
            query = query.where(AIAgent.status == status)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_agent_status(
        self,
        agent_id: int,
        tenant_id: int,
        status: str
    ) -> Optional[AIAgent]:
        """تحديث حالة الوكيل مع التأكد من tenant_id."""
        agent = await self.get_agent(agent_id, tenant_id)
        if not agent:
            return None
        await self.db.execute(
            update(AIAgent).where(AIAgent.id == agent_id).values(status=status)
        )
        await self.db.commit()
        return await self.get_agent(agent_id, tenant_id)

    async def delete_agent(self, agent_id: int, tenant_id: int, soft: bool = True) -> bool:
        """حذف وكيل (soft delete اختياري) مع التأكد من tenant_id."""
        if soft:
            await self.db.execute(
                update(AIAgent)
                .where(AIAgent.id == agent_id, AIAgent.tenant_id == tenant_id)
                .values(is_deleted=True, deleted_at=func.now())
            )
        else:
            await self.db.execute(
                delete(AIAgent).where(AIAgent.id == agent_id, AIAgent.tenant_id == tenant_id)
            )
        await self.db.commit()
        return True

    # ==========================================
    # 2. صمام الأمان البشري (مع Idempotency والعزل)
    # ==========================================

    async def create_approval_request(self, **kwargs) -> AgentApprovalQueue:
        """إنشاء طلب موافقة جديد (يتضمن tenant_id و idempotency_key اختياري)."""
        request = AgentApprovalQueue(**kwargs)
        self.db.add(request)
        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def get_approval_by_idempotency(self, idempotency_key: str) -> Optional[AgentApprovalQueue]:
        """جلب طلب موافقة باستخدام idempotency_key (بدون tenant_id لأن المفتاح فريد عالمياً)."""
        result = await self.db.execute(
            select(AgentApprovalQueue).where(AgentApprovalQueue.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def get_pending_approvals(
        self,
        human_approver_id: int,
        tenant_id: int
    ) -> List[AgentApprovalQueue]:
        """جلب طلبات الموافقة المعلقة لمستخدم معين مع التأكد من tenant_id."""
        result = await self.db.execute(
            select(AgentApprovalQueue)
            .join(AIAgent, AgentApprovalQueue.agent_id == AIAgent.id)
            .where(
                AgentApprovalQueue.human_approver_id == human_approver_id,
                AgentApprovalQueue.status == ApprovalStatus.PENDING,
                AIAgent.tenant_id == tenant_id
            )
            .order_by(AgentApprovalQueue.created_at.desc())
        )
        return result.scalars().all()

    async def get_approval(self, approval_id: int, tenant_id: int) -> Optional[AgentApprovalQueue]:
        """جلب طلب موافقة مع التأكد من tenant_id."""
        result = await self.db.execute(
            select(AgentApprovalQueue)
            .join(AIAgent, AgentApprovalQueue.agent_id == AIAgent.id)
            .where(
                AgentApprovalQueue.id == approval_id,
                AIAgent.tenant_id == tenant_id
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
        """حل طلب موافقة (موافقة/رفض) مع التأكد من tenant_id."""
        approval = await self.get_approval(approval_id, tenant_id)
        if not approval:
            return None
        values = {"status": status, "resolved_at": func.now()}
        if feedback:
            values["human_feedback"] = feedback
        await self.db.execute(
            update(AgentApprovalQueue).where(AgentApprovalQueue.id == approval_id).values(**values)
        )
        await self.db.commit()
        return await self.get_approval(approval_id, tenant_id)

    async def list_approvals(
        self,
        tenant_id: int,
        agent_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[AgentApprovalQueue]:
        """قائمة طلبات الموافقة مع فلترة حسب tenant_id."""
        query = (
            select(AgentApprovalQueue)
            .join(AIAgent, AgentApprovalQueue.agent_id == AIAgent.id)
            .where(AIAgent.tenant_id == tenant_id)
        )
        if agent_id:
            query = query.where(AgentApprovalQueue.agent_id == agent_id)
        if status:
            query = query.where(AgentApprovalQueue.status == status)
        query = query.order_by(AgentApprovalQueue.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    # ==========================================
    # 3. سجل استهلاك الذكاء الاصطناعي (مع Idempotency والعزل)
    # ==========================================

    async def create_task_log(self, **kwargs) -> AITaskLog:
        """إنشاء سجل مهمة جديدة (يتضمن tenant_id و idempotency_key اختياري)."""
        log = AITaskLog(**kwargs)
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def get_task_log_by_idempotency(self, idempotency_key: str) -> Optional[AITaskLog]:
        """جلب سجل مهمة باستخدام idempotency_key (بدون tenant_id لأن المفتاح فريد عالمياً)."""
        result = await self.db.execute(
            select(AITaskLog).where(AITaskLog.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def get_task_log(self, log_id: int, tenant_id: int) -> Optional[AITaskLog]:
        """جلب سجل مهمة مع التأكد من tenant_id."""
        result = await self.db.execute(
            select(AITaskLog).where(AITaskLog.id == log_id, AITaskLog.tenant_id == tenant_id)
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
    ) -> List[AITaskLog]:
        """قائمة سجلات المهام مع فلترة حسب tenant_id."""
        query = select(AITaskLog).where(AITaskLog.tenant_id == tenant_id)
        if agent_id:
            query = query.where(AITaskLog.agent_id == agent_id)
        if user_id:
            query = query.where(AITaskLog.user_id == user_id)
        if task_type:
            query = query.where(AITaskLog.task_type == task_type)
        query = query.order_by(AITaskLog.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_agent_usage_stats(
        self,
        agent_id: int,
        tenant_id: int,
        days: int = 30
    ) -> dict:
        """إحصائيات استخدام الوكيل (إجمالي التكلفة، عدد المهام، إلخ)."""
        start_date = datetime.utcnow() - timedelta(days=days)

        # إجمالي التكلفة
        cost_result = await self.db.execute(
            select(func.sum(AITaskLog.cost_mrusdt))
            .where(
                AITaskLog.agent_id == agent_id,
                AITaskLog.tenant_id == tenant_id,
                AITaskLog.created_at >= start_date
            )
        )
        total_cost = cost_result.scalar() or 0

        # عدد المهام
        count_result = await self.db.execute(
            select(func.count(AITaskLog.id))
            .where(
                AITaskLog.agent_id == agent_id,
                AITaskLog.tenant_id == tenant_id,
                AITaskLog.created_at >= start_date
            )
        )
        total_tasks = count_result.scalar() or 0

        # عدد المهام حسب النوع
        type_result = await self.db.execute(
            select(AITaskLog.task_type, func.count(AITaskLog.id))
            .where(
                AITaskLog.agent_id == agent_id,
                AITaskLog.tenant_id == tenant_id,
                AITaskLog.created_at >= start_date
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
    # 🆕 دوال العد والحدود (للتحقق من الاشتراكات والحدود)
    # ==========================================

    async def count_agents(self, tenant_id: int) -> int:
        """عدد الوكلاء النشطين للمستأجر."""
        result = await self.db.execute(
            select(func.count(AIAgent.id))
            .where(
                AIAgent.tenant_id == tenant_id,
                AIAgent.is_deleted == False
            )
        )
        return result.scalar() or 0

    async def count_monthly_calls(self, tenant_id: int) -> int:
        """عدد المكالمات للشهر الحالي."""
        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        result = await self.db.execute(
            select(func.count(AITaskLog.id))
            .where(
                AITaskLog.tenant_id == tenant_id,
                AITaskLog.created_at >= start_of_month
            )
        )
        return result.scalar() or 0

    async def get_monthly_ai_cost(self, tenant_id: int) -> Decimal:
        """إجمالي تكلفة الـ AI للشهر الحالي."""
        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        result = await self.db.execute(
            select(func.sum(AITaskLog.cost_mrusdt))
            .where(
                AITaskLog.tenant_id == tenant_id,
                AITaskLog.created_at >= start_of_month
            )
        )
        return result.scalar() or Decimal(0)

    async def get_tenant_subscription(self, tenant_id: int):
        """جلب اشتراك المستأجر النشط مع الميزات."""
        from app.domains.saas.models import SaaSSubscription
        result = await self.db.execute(
            select(SaaSSubscription)
            .where(
                SaaSSubscription.tenant_id == tenant_id,
                SaaSSubscription.status == "ACTIVE"
            )
        )
        return result.scalar_one_or_none()

    # ==========================================
    # 🆕 تحديث تكلفة المهمة
    # ==========================================

    async def update_task_log_cost(self, log_id: int, cost: Decimal) -> AITaskLog:
        """تحديث حقل cost_mrusdt في سجل المهمة."""
        await self.db.execute(
            update(AITaskLog)
            .where(AITaskLog.id == log_id)
            .values(cost_mrusdt=cost)
        )
        await self.db.commit()
        result = await self.db.execute(select(AITaskLog).where(AITaskLog.id == log_id))
        return result.scalar_one()

    # ==========================================
    # 🆕 دوال نقاط التفتيش للفوترة (Checkpoints)
    # ==========================================

    async def get_last_billed_month(self, tenant_id: int) -> Optional[datetime]:
        """
        جلب آخر شهر تمت فوترته للمستأجر.
        يستخدم حقل last_billed_month في جدول SaaSSubscription.
        """
        from app.domains.saas.models import SaaSSubscription
        result = await self.db.execute(
            select(SaaSSubscription.last_billed_month)
            .where(SaaSSubscription.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def update_last_billed_month(self, tenant_id: int, month: datetime):
        """
        تحديث آخر شهر تمت فوترته للمستأجر.
        """
        from app.domains.saas.models import SaaSSubscription
        await self.db.execute(
            update(SaaSSubscription)
            .where(SaaSSubscription.tenant_id == tenant_id)
            .values(last_billed_month=month)
        )
        await self.db.commit()


# ==========================================
# الكلاس الجديد المطلوب حقنه (AIAgentRepository)
# ==========================================
class AIAgentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # يمكنك إضافة دوال CRUD الأساسية هنا لاحقاً، 
    # المهم الآن هو وجود الكلاس نفسه ليتوقف الخطأ
    async def get_by_id(self, agent_id: int):
        pass

    async def create(self, agent_data: dict):
        pass