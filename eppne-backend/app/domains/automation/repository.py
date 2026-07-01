"""
مستودع قطاع الأتمتة – عمليات CRUD على سير العمل، التنفيذات، السجلات، والأسرار.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime
from cryptography.fernet import Fernet  # ✅ للتشفير

from app.domains.automation.models import (
    Workflow, WorkflowExecution, NodeExecutionLog, WorkflowSecret,
    ExecutionStatus
)
from app.core.errors import NotFoundError
from app.core.config import settings  # ✅ للحصول على مفتاح التشفير


class AutomationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
        # ✅ تهيئة مدير التشفير
        self.cipher = Fernet(settings.SECRET_ENCRYPTION_KEY)

    # ============================================================
    # 🔐 دوال تشفير مساعدة
    # ============================================================

    def _encrypt_value(self, plaintext: str) -> str:
        """تشفير قيمة نصية قبل التخزين في قاعدة البيانات."""
        if not plaintext:
            return plaintext
        return self.cipher.encrypt(plaintext.encode()).decode()

    def _decrypt_value(self, ciphertext: str) -> str:
        """فك تشفير قيمة مخزنة في قاعدة البيانات."""
        if not ciphertext:
            return ciphertext
        try:
            return self.cipher.decrypt(ciphertext.encode()).decode()
        except Exception:
            # في حال فشل فك التشفير، نعيد القيمة كما هي (للتوافق مع البيانات القديمة)
            return ciphertext

    # ==============================
    # 1. سير العمل (Workflows)
    # ==============================

    async def create_workflow(self, **kwargs) -> Workflow:
        workflow = Workflow(**kwargs)
        self.db.add(workflow)
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def get_workflow(self, workflow_id: int) -> Optional[Workflow]:
        result = await self.db.execute(select(Workflow).where(Workflow.id == workflow_id, Workflow.is_deleted == False))
        return result.scalar_one_or_none()

    async def get_workflow_by_webhook_path(self, path: str) -> Optional[Workflow]:
        result = await self.db.execute(
            select(Workflow).where(
                Workflow.webhook_path == path,
                Workflow.is_active == True,
                Workflow.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def list_workflows(self, tenant_id: int, skip: int = 0, limit: int = 50, include_inactive: bool = False) -> List[Workflow]:
        query = select(Workflow).where(Workflow.tenant_id == tenant_id, Workflow.is_deleted == False)
        if not include_inactive:
            query = query.where(Workflow.is_active == True)
        query = query.order_by(Workflow.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_workflow(self, workflow_id: int, **kwargs) -> Workflow:
        await self.db.execute(update(Workflow).where(Workflow.id == workflow_id).values(**kwargs))
        await self.db.commit()
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            raise NotFoundError("Workflow not found")
        return workflow

    async def delete_workflow(self, workflow_id: int, soft: bool = True) -> None:
        if soft:
            await self.db.execute(update(Workflow).where(Workflow.id == workflow_id).values(is_deleted=True, deleted_at=func.now()))
        else:
            await self.db.execute(delete(Workflow).where(Workflow.id == workflow_id))
        await self.db.commit()

    # ==============================
    # 2. تنفيذات سير العمل (Executions)
    # ==============================

    async def create_execution(self, **kwargs) -> WorkflowExecution:
        """
        إنشاء سجل تنفيذ جديد مع دعم الحقول الإضافية مثل trigger_ip و trigger_user_agent.
        """
        execution = WorkflowExecution(**kwargs)
        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def get_execution(self, execution_id: int) -> Optional[WorkflowExecution]:
        result = await self.db.execute(select(WorkflowExecution).where(WorkflowExecution.id == execution_id))
        return result.scalar_one_or_none()

    async def update_execution(self, execution_id: int, **kwargs) -> WorkflowExecution:
        await self.db.execute(update(WorkflowExecution).where(WorkflowExecution.id == execution_id).values(**kwargs))
        await self.db.commit()
        return await self.get_execution(execution_id)

    async def list_executions(self, workflow_id: int, skip: int = 0, limit: int = 50, status: Optional[str] = None) -> List[WorkflowExecution]:
        query = select(WorkflowExecution).where(WorkflowExecution.workflow_id == workflow_id)
        if status:
            query = query.where(WorkflowExecution.status == status)
        query = query.order_by(WorkflowExecution.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def increment_retry(self, execution_id: int) -> WorkflowExecution:
        execution = await self.get_execution(execution_id)
        if execution:
            execution.retry_count += 1
            execution.status = ExecutionStatus.RETRY
            await self.db.commit()
            await self.db.refresh(execution)
        return execution

    # ==============================
    # 3. سجلات العقد (Node Logs)
    # ==============================

    async def create_node_log(self, **kwargs) -> NodeExecutionLog:
        log = NodeExecutionLog(**kwargs)
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def update_node_log(self, log_id: int, **kwargs) -> NodeExecutionLog:
        await self.db.execute(update(NodeExecutionLog).where(NodeExecutionLog.id == log_id).values(**kwargs))
        await self.db.commit()
        result = await self.db.execute(select(NodeExecutionLog).where(NodeExecutionLog.id == log_id))
        return result.scalar_one()

    async def list_node_logs(self, execution_id: int) -> List[NodeExecutionLog]:
        result = await self.db.execute(
            select(NodeExecutionLog).where(NodeExecutionLog.execution_id == execution_id).order_by(NodeExecutionLog.started_at)
        )
        return result.scalars().all()

    # ============================================================
    # 4. الأسرار (Secrets) – مشفرة 🔐
    # ============================================================

    async def create_secret(self, **kwargs) -> WorkflowSecret:
        """
        إنشاء سر جديد مع تشفير القيمة قبل التخزين.
        """
        # ✅ تشفير القيمة قبل الحفظ
        if "value" in kwargs:
            kwargs["value_encrypted"] = self._encrypt_value(kwargs.pop("value"))

        secret = WorkflowSecret(**kwargs)
        self.db.add(secret)
        await self.db.commit()
        await self.db.refresh(secret)
        return secret

    async def get_secret(self, tenant_id: int, name: str) -> Optional[WorkflowSecret]:
        """
        جلب سر مع فك تشفير القيمة قبل الإرجاع.
        """
        result = await self.db.execute(
            select(WorkflowSecret).where(WorkflowSecret.tenant_id == tenant_id, WorkflowSecret.name == name)
        )
        secret = result.scalar_one_or_none()
        if secret and secret.value_encrypted:
            # ✅ فك تشفير القيمة قبل الإرجاع
            secret.value = self._decrypt_value(secret.value_encrypted)
        return secret

    async def list_secrets(self, tenant_id: int) -> List[WorkflowSecret]:
        """
        جلب قائمة الأسرار مع فك تشفير القيم.
        """
        result = await self.db.execute(
            select(WorkflowSecret).where(WorkflowSecret.tenant_id == tenant_id)
        )
        secrets = result.scalars().all()
        for secret in secrets:
            if secret.value_encrypted:
                secret.value = self._decrypt_value(secret.value_encrypted)
        return secrets

    async def delete_secret(self, tenant_id: int, name: str) -> None:
        await self.db.execute(
            delete(WorkflowSecret).where(WorkflowSecret.tenant_id == tenant_id, WorkflowSecret.name == name)
        )
        await self.db.commit()

    async def update_secret(self, tenant_id: int, name: str, new_value: str) -> Optional[WorkflowSecret]:
        """
        تحديث سر موجود (تغيير القيمة).
        """
        secret = await self.get_secret(tenant_id, name)
        if not secret:
            return None

        # تشفير القيمة الجديدة
        secret.value_encrypted = self._encrypt_value(new_value)
        secret.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(secret)

        # إرجاع القيمة المفككة
        secret.value = self._decrypt_value(secret.value_encrypted)
        return secret