"""
مسارات (Endpoints) قطاع الأتمتة – إنشاء وإدارة سير العمل، التشغيل اليدوي،
webhook، وجلب سجلات التنفيذ.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant
from app.domains.identity.models import User
from app.domains.automation.repository import AutomationRepository
from app.domains.automation.service import run_workflow_background
from app.domains.automation.schemas import (
    WorkflowCreate, WorkflowUpdate, WorkflowResponse,
    ExecutionTrigger, ExecutionResponse, NodeLogResponse,
    SecretCreate, SecretResponse
)
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit
from app.core.idempotency import check_idempotency, store_idempotency_result

router = APIRouter(prefix="/automation", tags=["Automation Workflows"])


# ========== 1. إدارة سير العمل (Workflows) ==========

@router.post("/workflows", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    data: WorkflowCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إنشاء سير عمل جديد (Workflow)."""
    repo = AutomationRepository(db)
    webhook_path = None
    if data.trigger_type == "WEBHOOK":
        webhook_path = f"/webhook/{uuid.uuid4().hex}"
    workflow = await repo.create_workflow(
        tenant_id=tenant.id,
        created_by=current_user.id,
        webhook_path=webhook_path,
        **data.model_dump()
    )
    return workflow


@router.get("/workflows", response_model=List[WorkflowResponse])
async def list_workflows(
    skip: int = 0,
    limit: int = 50,
    include_inactive: bool = False,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """قائمة سير العمل الخاصة بالمستأجر الحالي."""
    repo = AutomationRepository(db)
    workflows = await repo.list_workflows(tenant.id, skip, limit, include_inactive)
    return workflows


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب تفاصيل سير عمل معين."""
    repo = AutomationRepository(db)
    workflow = await repo.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if workflow.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return workflow


@router.put("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: int,
    data: WorkflowUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """تحديث سير عمل (الاسم، العقد، الإعدادات)."""
    repo = AutomationRepository(db)
    workflow = await repo.get_workflow(workflow_id)
    if not workflow or workflow.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    updated = await repo.update_workflow(workflow_id, **data.model_dump(exclude_unset=True))
    return updated


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: int,
    soft: bool = True,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """حذف سير عمل (حذف منطقي أو دائم)."""
    repo = AutomationRepository(db)
    workflow = await repo.get_workflow(workflow_id)
    if not workflow or workflow.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    await repo.delete_workflow(workflow_id, soft=soft)
    return {"message": "Workflow deleted"}


# ========== 2. تشغيل سير العمل (Triggers) ==========

@router.post("/workflows/{workflow_id}/trigger")
async def trigger_workflow_manual(
    workflow_id: int,
    data: ExecutionTrigger,
    request: Request,  # 🔥 إضافة request للحصول على IP و User-Agent
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """تشغيل سير العمل يدوياً (MANUAL trigger)."""
    repo = AutomationRepository(db)
    workflow = await repo.get_workflow(workflow_id)
    if not workflow or workflow.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if workflow.trigger_type != "MANUAL":
        raise HTTPException(status_code=400, detail="This workflow is not configured for manual trigger")
    
    # 🔥 تمرير IP و User-Agent إلى الخلفية
    background_tasks.add_task(
        run_workflow_background,
        db,
        workflow_id,
        "manual",
        data.trigger_payload or {},
        request.client.host if request.client else None,
        request.headers.get("user-agent")
    )
    return {"message": "Workflow triggered manually", "workflow_id": workflow_id}


# ============================================================
# 🟢 Webhook Trigger – مع Rate Limiting و Idempotency
# ============================================================
@router.post("/webhook/{path}")
@rate_limit(max_requests=100, window=60)  # 100 طلب في الدقيقة لكل مسار
async def webhook_trigger(
    path: str,
    request: Request,  # 🔥 إضافة request للحصول على IP و User-Agent
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    نقطة نهاية Webhook لتشغيل سير العمل (يتم تحديد المسار تلقائياً عند الإنشاء).
    تدعم Idempotency عبر Header اختياري.
    """
    # التحقق من Idempotency (اختياري)
    if idempotency_key:
        cached = await check_idempotency(idempotency_key)
        if cached:
            return cached

    repo = AutomationRepository(db)
    full_path = f"/webhook/{path}"
    workflow = await repo.get_workflow_by_webhook_path(full_path)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found for this webhook path")
    
    # قراءة payload (JSON)
    try:
        payload = await request.json()
    except:
        payload = {}

    # 🔥 تمرير IP و User-Agent إلى الخلفية
    background_tasks.add_task(
        run_workflow_background,
        db,
        workflow.id,
        "webhook",
        payload,
        request.client.host if request.client else None,
        request.headers.get("user-agent")
    )

    # تحضير الاستجابة
    response_data = {"message": "Webhook received", "workflow_id": workflow.id}

    # تخزين نتيجة Idempotency (إن وُجد مفتاح)
    if idempotency_key:
        await store_idempotency_result(idempotency_key, response_data)

    return response_data


# ============================================================
# 🆕 نقطة نهاية جلب الوكلاء المتاحين (للعقدة AI_AGENT)
# ============================================================
@router.get("/ai-agents")
async def list_available_agents(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب قائمة الوكلاء المتاحين للمستخدم الحالي لاستخدامها في عقدة AI_AGENT.
    """
    from app.domains.ai_agents.repository import AIAgentsRepository
    repo = AIAgentsRepository(db)
    agents = await repo.list_agents(
        tenant_id=tenant.id,
        owner_id=current_user.id,
        status="ACTIVE"
    )
    return [
        {
            "id": agent.id,
            "name": agent.name,
            "role": agent.role.value,
            "can_execute_payments": agent.can_execute_payments,
            "can_sign_contracts": agent.can_sign_contracts,
        }
        for agent in agents
    ]


# ========== 3. سجلات التنفيذ (Executions & Logs) ==========

@router.get("/workflows/{workflow_id}/executions", response_model=List[ExecutionResponse])
async def get_workflow_executions(
    workflow_id: int,
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب جميع تنفيذات سير العمل."""
    repo = AutomationRepository(db)
    workflow = await repo.get_workflow(workflow_id)
    if not workflow or workflow.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    executions = await repo.list_executions(workflow_id, skip, limit, status_filter)
    return executions


@router.get("/executions/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب تفاصيل تنفيذ معين."""
    repo = AutomationRepository(db)
    execution = await repo.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    workflow = await repo.get_workflow(execution.workflow_id)
    if workflow.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return execution


@router.get("/executions/{execution_id}/logs", response_model=List[NodeLogResponse])
async def get_execution_logs(
    execution_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب سجلات العقد لتنفيذ معين."""
    repo = AutomationRepository(db)
    execution = await repo.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    workflow = await repo.get_workflow(execution.workflow_id)
    if workflow.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    logs = await repo.list_node_logs(execution_id)
    return logs


# ========== 4. إدارة الأسرار (Secrets) ==========

@router.post("/secrets", response_model=SecretResponse, status_code=status.HTTP_201_CREATED)
async def create_secret(
    data: SecretCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """تخزين سر (مثل API key) مشفر داخل قاعدة البيانات."""
    repo = AutomationRepository(db)
    existing = await repo.get_secret(tenant.id, data.name)
    if existing:
        raise HTTPException(status_code=400, detail="Secret with this name already exists")
    secret = await repo.create_secret(
        tenant_id=tenant.id,
        name=data.name,
        value_encrypted=data.value
    )
    return secret


@router.get("/secrets", response_model=List[SecretResponse])
async def list_secrets(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """قائمة الأسرار (بدون الكشف عن القيم)."""
    repo = AutomationRepository(db)
    secrets = await repo.list_secrets(tenant.id)
    return secrets


@router.delete("/secrets/{secret_name}")
async def delete_secret(
    secret_name: str,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """حذف سر."""
    repo = AutomationRepository(db)
    await repo.delete_secret(tenant.id, secret_name)
    return {"message": "Secret deleted"}