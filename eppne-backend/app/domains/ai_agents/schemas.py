from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.ai_agents.models import AgentRole, AgentStatus, ApprovalStatus

# ========== AI Agents ==========
class AIAgentCreate(BaseModel):
    name: str
    role: AgentRole
    system_prompt: str
    base_model: str = "gemini-1.5-pro"
    can_execute_payments: bool = False
    can_sign_contracts: bool = False
    requires_human_approval: bool = True
    interaction_cost_mrusdt: Decimal = 0

class AIAgentResponse(AIAgentCreate):
    id: int
    status: AgentStatus
    owner_id: Optional[int]
    tenant_id: Optional[int]
    agent_wallet_address: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Approval Queue ==========
class ApprovalAction(BaseModel):
    agent_id: int
    action_type: str
    proposed_payload: Dict[str, Any]

class ApprovalResponse(BaseModel):
    id: int
    agent_id: int
    human_approver_id: int
    action_type: str
    proposed_payload: Dict[str, Any]
    status: ApprovalStatus
    human_feedback: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)

class ApprovalResolution(BaseModel):
    status: ApprovalStatus  
    human_feedback: Optional[str] = None