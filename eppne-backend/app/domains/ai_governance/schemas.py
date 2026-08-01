# app/domains/ai_governance/schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.ai_governance.models import UsagePeriod, LimitType


class AgentQuotaCreate(BaseModel):
    limit_type: LimitType = Field(description="نوع الحصة (REQUEST_COUNT, TOKEN_COUNT, COST_MRUSDT)")
    period: UsagePeriod = Field(description="فترة الحصة (DAILY, WEEKLY, MONTHLY, YEARLY)")
    limit_value: Decimal = Field(description="قيمة الحد الأقصى")


class AgentQuotaResponse(AgentQuotaCreate):
    id: int
    agent_id: int
    current_usage: Decimal = Field(description="الاستهلاك الحالي")
    reset_at: datetime = Field(description="موعد إعادة تعيين العداد")

    model_config = ConfigDict(from_attributes=True)


class AgentQuotaRemainingResponse(BaseModel):
    quotas: Dict[str, Dict[str, Any]] = Field(description="تفاصيل الحصص المتبقية")


class AgentRateLimitUpdate(BaseModel):
    requests_per_minute: Optional[int] = Field(default=None, description="عدد الطلبات في الدقيقة")
    requests_per_hour: Optional[int] = Field(default=None, description="عدد الطلبات في الساعة")
    concurrent_limit: Optional[int] = Field(default=None, description="عدد الطلبات المتزامنة")


class AgentRateLimitResponse(BaseModel):
    agent_id: int
    requests_per_minute: int = Field(description="عدد الطلبات في الدقيقة")
    requests_per_hour: int = Field(description="عدد الطلبات في الساعة")
    concurrent_limit: int = Field(description="عدد الطلبات المتزامنة")

    model_config = ConfigDict(from_attributes=True)


class AgentUsageSummary(BaseModel):
    agent_id: int = Field(description="معرف الوكيل")
    total_requests: int = Field(description="إجمالي عدد الطلبات")
    total_tokens: int = Field(description="إجمالي عدد التوكنات")
    total_cost_mrusdt: float = Field(description="إجمالي التكلفة بـ MR_USDT")
    avg_response_time_ms: float = Field(description="متوسط زمن الاستجابة بالمللي ثانية")
    period: str = Field(description="الفترة الزمنية (DAILY, WEEKLY, MONTHLY, YEARLY)")


class AgentAuditLogResponse(BaseModel):
    id: int
    agent_id: int
    admin_user_id: int
    action: str = Field(description="نوع الإجراء (CREATE, UPDATE, SUSPEND, ACTIVATE, CHANGE_QUOTA)")
    old_value: Optional[Dict[str, Any]] = Field(default=None, description="القيمة القديمة")
    new_value: Optional[Dict[str, Any]] = Field(default=None, description="القيمة الجديدة")
    ip_address: Optional[str] = Field(default=None, description="عنوان IP")
    created_at: datetime = Field(description="وقت الإنشاء")

    model_config = ConfigDict(from_attributes=True)