# app/domains/guardian/schemas.py
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional
from datetime import date, datetime

from app.domains.guardian.models import (
    GuardianRelationshipType, GuardianRelationshipStatus, GuardianVisibilitySector,
)


# ============================================================
# علاقة ولي الأمر (Guardian Relationship)
# ============================================================

class GuardianRelationshipCreate(BaseModel):
    guardian_user_id: int = Field(description="معرف ولي الأمر")
    ward_user_id: int = Field(description="معرف الطالب المشمول بالولاية")
    relationship_type: GuardianRelationshipType = Field(description="نوع العلاقة")
    ward_birth_date_provided: Optional[date] = Field(
        default=None, description="تاريخ ميلاد الطالب كما أُدخل وقت طلب الربط"
    )


class GuardianRelationshipRequestCreate(BaseModel):
    """جسم الطلب اللي بيبعته ولي الأمر فعليًا — `guardian_user_id` مش
    موجود عمدًا (بيتحدد دايمًا من `current_user`، مش من مدخلات العميل)."""
    ward_user_id: int = Field(description="معرف الطالب المشمول بالولاية (من GET /guardian/find-user)")
    relationship_type: GuardianRelationshipType = Field(description="نوع العلاقة")


class GuardianRelationshipApproveRequest(BaseModel):
    ward_birth_date_provided: date = Field(description="تاريخ ميلاد الطالب — يُدخله الطالب وقت الموافقة")


class GuardianRelationshipRejectRequest(BaseModel):
    rejection_reason: Optional[str] = Field(default=None, description="سبب رفض الطالب (اختياري)")


class GuardianRelationshipReviewRequest(BaseModel):
    status: GuardianRelationshipStatus = Field(description="قرار الأدمن — VERIFIED أو REJECTED فقط")
    rejection_reason: Optional[str] = Field(default=None, description="سبب الرفض (إجباري لو status=REJECTED)")

    @field_validator("status")
    @classmethod
    def _status_must_be_final_decision(cls, v: GuardianRelationshipStatus) -> GuardianRelationshipStatus:
        if v not in (GuardianRelationshipStatus.VERIFIED, GuardianRelationshipStatus.REJECTED):
            raise ValueError("status يجب أن يكون VERIFIED أو REJECTED فقط")
        return v


class GuardianRelationshipResponse(BaseModel):
    id: int
    tenant_id: int
    guardian_user_id: int
    ward_user_id: int
    relationship_type: GuardianRelationshipType
    status: GuardianRelationshipStatus
    initiated_by_user_id: int
    ward_birth_date_provided: Optional[date]
    verified_by: Optional[int]
    verified_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# إعدادات ظهور القطاعات (Visibility Settings)
# ============================================================

class GuardianVisibilitySettingCreate(BaseModel):
    sector: GuardianVisibilitySector = Field(description="القطاع")
    is_visible: bool = Field(default=True, description="هل هذا القطاع مرئي لولي الأمر؟")


class GuardianVisibilitySettingResponse(BaseModel):
    id: int
    guardian_relationship_id: int
    sector: GuardianVisibilitySector
    is_visible: bool
    model_config = ConfigDict(from_attributes=True)


class GuardianVisibilityUpdateRequest(BaseModel):
    settings: List[GuardianVisibilitySettingCreate] = Field(
        description="قائمة القطاعات المطلوب تحديث ظهورها (upsert لكل عنصر)"
    )


# ============================================================
# البحث عن مستخدم بتطابق تام (Exact-match lookup)
# ============================================================

class UserLookupResponse(BaseModel):
    user_id: int
    name: str = Field(description="اسم المستخدم (username)")
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# مراسلة مدرّس (Message Instructor)
# ============================================================

class GuardianMessageInstructorRequest(BaseModel):
    course_id: int = Field(description="الكورس اللي الطالب مسجَّل فيه — بيحدد أنهي مدرّس تحديدًا يستلم الرسالة")
    message: str = Field(min_length=1, description="نص الرسالة")
