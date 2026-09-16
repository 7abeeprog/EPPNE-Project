# app/domains/achievements/schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime

from app.domains.achievements.models import AchievementCategory, AchievementTriggerType


# ============================================================
# تعريفات الإنجازات (Achievement Definitions)
# ============================================================

class AchievementDefinitionCreate(BaseModel):
    name: str = Field(description="اسم الإنجاز")
    description: str = Field(description="وصف الإنجاز")
    category: AchievementCategory = Field(description="تصنيف الإنجاز")
    icon_url: Optional[str] = Field(default=None, description="رابط أيقونة الإنجاز")
    points_value: int = Field(default=0, ge=0, description="عدد النقاط الممنوحة")
    trigger_type: AchievementTriggerType = Field(
        default=AchievementTriggerType.MANUAL,
        description="نوع المُحفِّز — MANUAL في هذه المرحلة فقط، AUTO_EVENT للتخزين المستقبلي بلا تفعيل فعلي",
    )
    trigger_event_name: Optional[str] = Field(default=None, description="اسم الحدث المُحفِّز (AUTO_EVENT، غير مُفعَّل بعد)")
    trigger_threshold: Optional[int] = Field(default=None, description="عتبة التفعيل (AUTO_EVENT، غير مُفعَّل بعد)")
    is_active: bool = Field(default=True)


class AchievementDefinitionResponse(BaseModel):
    id: int
    tenant_id: int
    name: str
    description: str
    category: AchievementCategory
    icon_url: Optional[str]
    points_value: int
    trigger_type: AchievementTriggerType
    trigger_event_name: Optional[str]
    trigger_threshold: Optional[int]
    is_active: bool
    created_by: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# منح الإنجازات (User Achievements)
# ============================================================

class AchievementGrantRequest(BaseModel):
    user_id: int = Field(description="المستخدم المستفيد من الإنجاز")
    achievement_definition_id: int = Field(description="تعريف الإنجاز المطلوب منحه")


class UserAchievementResponse(BaseModel):
    id: int
    tenant_id: int
    user_id: int
    achievement_definition_id: int
    granted_at: datetime
    granted_by: Optional[int]
    source_event_name: Optional[str]
    source_payload: Optional[Dict[str, Any]]
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# إحصائيات (Stats — Admin)
# ============================================================

class AchievementCategoryStatItem(BaseModel):
    category: AchievementCategory = Field(description="تصنيف الإنجاز")
    count: int = Field(description="عدد الإنجازات الممنوحة فعليًا (UserAchievement) لهذه الفئة")


class AchievementTopUserItem(BaseModel):
    user_id: int
    user_name: str
    achievement_count: int = Field(description="عدد الإنجازات الممنوحة لهذا المستخدم")


class AchievementDefinitionStatItem(BaseModel):
    achievement_definition_id: int
    achievement_name: str
    count: int = Field(description="عدد المستخدمين اللي حققوا هذا التعريف فعليًا (UserAchievement)")
