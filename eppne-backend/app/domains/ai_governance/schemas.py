from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.ai_governance.models import UsagePeriod, LimitType


class AgentQuotaCreate(BaseModel):
    limit_type: LimitType
    period: UsagePeriod
    limit_value: Decimal


class AgentQuotaResponse(AgentQuotaCreate):
    id: int
    agent_id: int
    current_usage: Decimal
    reset_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AgentRateLimitUpdate(BaseModel):
    requests_per_minute: Optional[int] = None
    requests_per_hour: Optional[int] = None
    concurrent_limit: Optional[int] = None


class AgentRateLimitResponse(BaseModel):
    agent_id: int
    requests_per_minute: int
    requests_per_hour: int
    concurrent_limit: int
    model_config = ConfigDict(from_attributes=True)


class AgentUsageSummary(BaseModel):
    agent_id: int
    total_requests: int
    total_tokens: int
    total_cost_mrusdt: float
    avg_response_time_ms: float
    period: str


class AgentAuditLogResponse(BaseModel):
    id: int
    agent_id: int
    admin_user_id: int
    action: str
    old_value: Optional[Dict[str, Any]]
    new_value: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)