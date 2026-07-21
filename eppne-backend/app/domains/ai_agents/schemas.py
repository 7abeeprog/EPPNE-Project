# app/domains/ai_agents/schemas.py
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
from app.domains.ai_agents.models import AgentRole, AgentStatus, ApprovalStatus


# ========== AI Agents ==========
class AIAgentCreate(BaseModel):
    name: str = Field(..., description="اسم الوكيل", min_length=1, max_length=255)
    role: AgentRole = Field(..., description="دور الوكيل")
    system_prompt: str = Field(..., description="الموجه النظامي للوكيل", min_length=1)
    base_model: str = Field(default="gemini-1.5-pro", description="النموذج الأساسي")
    can_execute_payments: bool = Field(default=False, description="هل يمكنه تنفيذ المدفوعات")
    can_sign_contracts: bool = Field(default=False, description="هل يمكنه توقيع العقود")
    requires_human_approval: bool = Field(default=True, description="هل يتطلب موافقة بشرية")
    interaction_cost_mrusdt: Decimal = Field(default=Decimal('0.0'), description="تكلفة التفاعل الواحد")


class AIAgentResponse(BaseModel):
    id: int
    name: str
    role: AgentRole
    status: AgentStatus
    system_prompt: str
    base_model: str
    can_execute_payments: bool
    can_sign_contracts: bool
    requires_human_approval: bool
    interaction_cost_mrusdt: Decimal
    owner_id: Optional[int] = None
    tenant_id: Optional[int] = None
    agent_wallet_address: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ========== Approval Queue ==========
class ApprovalAction(BaseModel):
    agent_id: int = Field(..., description="معرف الوكيل")
    action_type: str = Field(..., description="نوع الإجراء", min_length=1)
    proposed_payload: Dict[str, Any] = Field(..., description="البيانات المقترحة للتنفيذ")


class ApprovalResponse(BaseModel):
    id: int
    agent_id: int
    human_approver_id: int
    action_type: str
    proposed_payload: Dict[str, Any]
    status: ApprovalStatus
    human_feedback: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ApprovalResolution(BaseModel):
    status: ApprovalStatus = Field(..., description="الحالة الجديدة (APPROVED/REJECTED)")
    human_feedback: Optional[str] = Field(None, description="تعليق الموافق/الرافض", max_length=1000)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: ApprovalStatus) -> ApprovalStatus:
        if v not in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]:
            raise ValueError(f"الحالة غير مسموحة: {v}. يُسمح فقط بـ APPROVED أو REJECTED")
        return v


# ========== Status Updates ==========
class AgentStatusUpdate(BaseModel):
    status: AgentStatus = Field(..., description="الحالة الجديدة للوكيل")


class AgentStatusResponse(BaseModel):
    agent_id: int
    status: AgentStatus
    last_active: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ========== Task Logs (للتحليلات) ==========
class AITaskLogResponse(BaseModel):
    id: int
    tenant_id: int
    agent_id: Optional[int] = None
    user_id: Optional[int] = None
    task_type: str
    prompt_tokens: int
    completion_tokens: int
    cost_mrusdt: Decimal
    settlement_type: str
    payment_tx_hash: Optional[str] = None
    used_model: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)