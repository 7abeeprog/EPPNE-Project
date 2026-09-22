# app/domains/admin/schemas.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AIKillSwitchToggle(BaseModel):
    suspend: bool = Field(..., description="True = إيقاف كل استدعاءات الـ AI على مستوى المنصة، False = استئنافها")


class AIKillSwitchStatus(BaseModel):
    suspended: Optional[bool] = Field(
        None,
        description="None = الحالة غير معروفة (Redis غير متاح) — البوابة تعمل حينها fail-open (الـ AI يعمل)."
    )
    redis_reachable: bool
    changed_by_user_id: Optional[int] = None
    changed_by_tenant_id: Optional[int] = None
    changed_at: Optional[datetime] = None


class AIKillSwitchToggleResponse(AIKillSwitchStatus):
    previous_suspended: Optional[bool] = None
    message: str
