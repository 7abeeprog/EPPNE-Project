"""
مسارات (Endpoints) قطاع الأتمتة – إنشاء وإدارة سير العمل، التشغيل اليدوي،
webhook، وجلب سجلات التنفيذ.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, status, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, cast
import uuid

from app.core.errors import PermissionDeniedError, NotFoundError, ValidationError
from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant
from app.domains.identity.models import User
from app.domains.automation.service import AutomationService, run_workflow_background
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
@rate_limit(max_requests=10, window_seconds=60)
async def create_workflow(
    data: WorkflowCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إنشاء سير عمل جديد (Workflow)."""
    service = AutomationService(db)
    workflow = await service.create_workflow(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return workflow


@router.get("/workflows", response_model=List[WorkflowResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def list_workflows(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    include_inactive: bool = False,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """قائمة سير العمل الخاصة بالمستأجر الحالي."""
    service = AutomationService(db)
    workflows = await service.list_workflows(
        tenant_id=cast(int, tenant.id),
        user_id=cast(int, current_user.id),
        skip=skip,
        limit=limit,
        include_inactive=include_inactive
    )
    return workflows


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def get_workflow(
    workflow_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب تفاصيل سير عمل معين."""
    service = AutomationService(db)
    workflow = await service.get_workflow(
        workflow_id=workflow_id,
        user_id=cast(int, current_user.id)
    )
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.put("/workflows/{workflow_id}", response_model=WorkflowResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_workflow(
    workflow_id: int,
    data: WorkflowUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """تحديث سير عمل (الاسم، العقد، الإعدادات)."""
    service = AutomationService(db)
    try:
        updated = await service.update_workflow(
            workflow_id=workflow_id,
            user_id=cast(int, current_user.id),
            data=data.model_dump(exclude_unset=True)
        )
        return updated
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="Not authorized")
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")


@router.delete("/workflows/{workflow_id}")
@rate_limit(max_requests=5, window_seconds=60)
async def delete_workflow(
    workflow_id: int,
    soft: bool = True,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """حذف سير عمل (حذف منطقي أو دائم)."""
    service = AutomationService(db)
    try:
        await service.delete_workflow(
            workflow_id=workflow_id,
            user_id=cast(int, current_user.id),
            soft=soft
        )
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="Not authorized")
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"message": "Workflow deleted"}


# ========== 2. تشغيل سير العمل (Triggers) ==========

@router.post("/workflows/{workflow_id}/trigger")
@rate_limit(max_requests=10, window_seconds=60)
async def trigger_workflow_manual(
    workflow_id: int,
    data: ExecutionTrigger,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """تشغيل سير العمل يدوياً (MANUAL trigger)."""
    service = AutomationService(db)
    try:
        execution = await service.trigger_workflow_manual(
            workflow_id=workflow_id,
            user_id=cast(int, current_user.id),
            payload=data.trigger_payload or {},
            request_ip=request.client.host if request.client else None,
            request_user_agent=request.headers.get("user-agent")
        )
        # التنفيذ الفعلي في الخلفية
        background_tasks.add_task(
            run_workflow_background,
            db,
            workflow_id,
            "manual",
            data.trigger_payload or {},
            request.client.host if request.client else None,
            request.headers.get("user-agent")
        )
        return {"message": "Workflow triggered manually", "workflow_id": workflow_id, "execution_id": execution.id}
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="Not authorized")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# 🟢 Webhook Trigger – مع Rate Limiting و Idempotency
# ============================================================
@router.post("/webhook/{path}")
@rate_limit(max_requests=100, window_seconds=60)
async def webhook_trigger(
    path: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """
    نقطة نهاية Webhook لتشغيل سير العمل (يتم تحديد المسار تلقائياً عند الإنشاء).
    تدعم Idempotency عبر Header اختياري.
    """
    service = AutomationService(db)
    
    try:
        payload = await request.json()
    except:
        payload = {}

    result = await service.handle_webhook_trigger(
        path=path,
        payload=payload,
        request_ip=request.client.host if request.client else None,
        request_user_agent=request.headers.get("user-agent"),
        idempotency_key=idempotency_key
    )

    # تشغيل سير العمل في الخلفية
    background_tasks.add_task(
        run_workflow_background,
        db,
        cast(int, result.get("workflow_id")),
        "webhook",
        payload,
        request.client.host if request.client else None,
        request.headers.get("user-agent")
    )

    return result


# ============================================================
# 🆕 نقطة نهاية جلب الوكلاء المتاحين (للعقدة AI_AGENT)
# ============================================================
@router.get("/ai-agents")
@rate_limit(max_requests=20, window_seconds=60)
async def list_available_agents(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب قائمة الوكلاء المتاحين للمستخدم الحالي لاستخدامها في عقدة AI_AGENT.
    """
    service = AutomationService(db)
    return await service.list_available_agents(
        tenant_id=cast(int, tenant.id),
        user_id=cast(int, current_user.id)
    )


# ========== 3. سجلات التنفيذ (Executions & Logs) ==========

@router.get("/workflows/{workflow_id}/executions", response_model=List[ExecutionResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def get_workflow_executions(
    workflow_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب جميع تنفيذات سير العمل."""
    service = AutomationService(db)
    try:
        executions = await service.list_executions(
            workflow_id=workflow_id,
            user_id=cast(int, current_user.id),
            skip=skip,
            limit=limit,
            status_filter=status_filter
        )
        return executions
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.get("/executions/{execution_id}", response_model=ExecutionResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def get_execution(
    execution_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب تفاصيل تنفيذ معين."""
    service = AutomationService(db)
    execution = await service.get_execution(
        execution_id=execution_id,
        user_id=cast(int, current_user.id)
    )
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@router.get("/executions/{execution_id}/logs", response_model=List[NodeLogResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def get_execution_logs(
    execution_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب سجلات العقد لتنفيذ معين."""
    service = AutomationService(db)
    try:
        logs = await service.get_execution_logs(
            execution_id=execution_id,
            user_id=cast(int, current_user.id)
        )
        return logs
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="Not authorized")
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Execution not found")


# ========== 4. إدارة الأسرار (Secrets) ==========

@router.post("/secrets", response_model=SecretResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_secret(
    data: SecretCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """تخزين سر (مثل API key) مشفر داخل قاعدة البيانات."""
    service = AutomationService(db)
    secret = await service.create_secret(
        tenant_id=cast(int, current_user.tenant_id),
        name=data.name,
        value=data.value
    )
    return secret


@router.get("/secrets", response_model=List[SecretResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def list_secrets(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """قائمة الأسرار (بدون الكشف عن القيم)."""
    service = AutomationService(db)
    secrets = await service.list_secrets(tenant_id=cast(int, current_user.tenant_id))
    return secrets


@router.delete("/secrets/{secret_name}")
@rate_limit(max_requests=10, window_seconds=60)
async def delete_secret(
    secret_name: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """حذف سر."""
    service = AutomationService(db)
    await service.delete_secret(
        tenant_id=cast(int, current_user.tenant_id),
        name=secret_name
    )
    return {"message": "Secret deleted"}