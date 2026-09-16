# app/domains/guardian/router.py
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Optional, cast

from app.core.database import get_db
from app.core.security import get_current_active_user, get_current_superuser
from app.domains.identity.models import User
from app.domains.guardian.service import GuardianService
from app.domains.guardian.schemas import (
    UserLookupResponse,
    GuardianRelationshipRequestCreate,
    GuardianRelationshipApproveRequest,
    GuardianRelationshipRejectRequest,
    GuardianRelationshipReviewRequest,
    GuardianRelationshipResponse,
    GuardianVisibilityUpdateRequest,
    GuardianVisibilitySettingResponse,
    GuardianMessageInstructorRequest,
)
from app.domains.communications.schemas import NotificationResponse

router = APIRouter(prefix="/guardian", tags=["Guardian"])


# ============================================================
# 1. البحث عن مستخدم بتطابق تام
# ============================================================

@router.get("/find-user", response_model=UserLookupResponse)
async def find_user(
    email: Optional[str] = Query(default=None),
    username: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = GuardianService(db, cast(int, current_user.tenant_id))
    user = await service.find_user(email, username)
    return UserLookupResponse(user_id=cast(int, user.id), name=cast(str, user.username))


# ============================================================
# 2. طلب الربط — ولي الأمر
# ============================================================

@router.post(
    "/relationships",
    response_model=GuardianRelationshipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_relationship(
    data: GuardianRelationshipRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = GuardianService(db, cast(int, current_user.tenant_id))
    return await service.create_relationship_request(
        guardian_user_id=cast(int, current_user.id),
        ward_user_id=data.ward_user_id,
        relationship_type=data.relationship_type,
    )


# ============================================================
# 3. موافقة/رفض الطالب
# ============================================================

@router.post("/relationships/{relationship_id}/approve", response_model=GuardianRelationshipResponse)
async def approve_relationship(
    relationship_id: int,
    data: GuardianRelationshipApproveRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = GuardianService(db, cast(int, current_user.tenant_id))
    return await service.approve_relationship(
        relationship_id=relationship_id,
        ward_user_id=cast(int, current_user.id),
        ward_birth_date_provided=data.ward_birth_date_provided,
    )


@router.post("/relationships/{relationship_id}/reject", response_model=GuardianRelationshipResponse)
async def reject_relationship(
    relationship_id: int,
    data: GuardianRelationshipRejectRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = GuardianService(db, cast(int, current_user.tenant_id))
    return await service.reject_relationship(
        relationship_id=relationship_id,
        ward_user_id=cast(int, current_user.id),
        rejection_reason=data.rejection_reason,
    )


# ============================================================
# 4. مراجعة الأدمن
# ============================================================

@router.put("/relationships/{relationship_id}/review", response_model=GuardianRelationshipResponse)
async def review_relationship(
    relationship_id: int,
    data: GuardianRelationshipReviewRequest,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    service = GuardianService(db, cast(int, current_user.tenant_id))
    return await service.review_relationship(
        relationship_id=relationship_id,
        admin_id=cast(int, current_user.id),
        status=data.status,
        rejection_reason=data.rejection_reason,
    )


# ============================================================
# 5. تحكّم الطالب في الرؤية
# ============================================================

@router.put("/relationships/{relationship_id}/visibility", response_model=List[GuardianVisibilitySettingResponse])
async def update_visibility(
    relationship_id: int,
    data: GuardianVisibilityUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = GuardianService(db, cast(int, current_user.tenant_id))
    return await service.update_visibility(
        relationship_id=relationship_id,
        ward_user_id=cast(int, current_user.id),
        settings=[item.model_dump() for item in data.settings],
    )


# ============================================================
# 6. نظرة عامة موحَّدة على الطالب
# ============================================================

@router.get("/wards/{ward_id}/overview")
async def get_ward_overview(
    ward_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    # بلا response_model عمدًا: القطاع المحجوب لازم يختفي كـkey كامل من
    # الرد (مش يظهر بقيمة null) — راجع
    # .claude/reports/guardian-overview-endpoint-implementation-session-log.md
    service = GuardianService(db, cast(int, current_user.tenant_id))
    return await service.get_ward_overview(
        guardian_user_id=cast(int, current_user.id),
        ward_user_id=ward_id,
    )


# ============================================================
# 7. مراسلة مدرّس
# ============================================================

@router.post(
    "/wards/{ward_id}/message-instructor",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def message_instructor(
    ward_id: int,
    data: GuardianMessageInstructorRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = GuardianService(db, cast(int, current_user.tenant_id))
    return await service.message_instructor(
        guardian_user_id=cast(int, current_user.id),
        ward_user_id=ward_id,
        course_id=data.course_id,
        message_text=data.message,
    )
