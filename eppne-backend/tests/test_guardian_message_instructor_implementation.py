"""
regression test لجلسة `guardian-message-instructor-implementation`
(2026-09-16) — POST /guardian/wards/{ward_id}/message-instructor: يسمح
لولي أمر مُوثَّق (VERIFIED) يبعت رسالة لمدرّس كورس معيّن الطالب فعليًا
مسجَّل فيه، عبر `Course.instructor_id` (مش `LiveSession.instructor_id`
غير الموثوقة — راجع
.claude/reports/guardian-message-instructor-planning-session-log.md).

يغطي: علاقة VERIFIED + تسجيل فعلي + مدرّس مُسنَد → نجاح، صف Notification
حقيقي محفوظ للمدرّس؛ قطاع ACADEMY محجوب → 403؛ course_id الطالب مش
مسجَّل فيه → 404؛ كورس بلا مدرّس مُسنَد (instructor_id IS NULL) → 404.
"""
import uuid
from datetime import date

import pytest
from sqlalchemy import delete, insert, select

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.core.errors import NotFoundError, PermissionDeniedError

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.guardian.service import GuardianService
from app.domains.guardian.repository import GuardianRepository
from app.domains.guardian.models import (
    GuardianRelationship, GuardianVisibilitySetting,
    GuardianRelationshipType, GuardianVisibilitySector,
)

from app.domains.academy.models import OrganizationEntity, Course, Enrollment, Instructor
from app.domains.communications.models import Notification

TENANT_ID = 1
ADULT_BIRTH_DATE = date(1990, 1, 1)


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


async def _create_verified_relationship(db, guardian_id: int, ward_id: int) -> GuardianRelationship:
    service = GuardianService(db, TENANT_ID)
    relationship = await service.create_relationship_request(
        guardian_user_id=guardian_id, ward_user_id=ward_id,
        relationship_type=GuardianRelationshipType.FATHER,
    )
    return await service.approve_relationship(
        relationship_id=relationship.id, ward_user_id=ward_id,
        ward_birth_date_provided=ADULT_BIRTH_DATE,
    )


class _Fixtures:
    def __init__(self):
        self.org_entity_id = None
        self.instructor_id = None
        self.course_with_instructor_id = None
        self.course_without_instructor_id = None
        self.course_not_enrolled_id = None
        self.enrollment_ids = []


async def _build_courses(db, ward_id: int, instructor_user_id: int) -> _Fixtures:
    fx = _Fixtures()
    suffix = _suffix()

    org_entity = OrganizationEntity(tenant_id=TENANT_ID, name=f"REGTEST-ORG-MSG-{suffix}", entity_type="ACADEMY", is_active=True)
    db.add(org_entity)
    await db.flush()
    fx.org_entity_id = org_entity.id

    # ⚠️ INSERT عبر Core مباشرة (مش `db.add(Instructor(...))`) عمدًا —
    # الموديل (`academy/models.py`) بيعرّف عمود `tenant_id` على
    # `Instructor`، لكن جدول `academy_instructors` الفعلي في DB **بلا هذا
    # العمود إطلاقًا** (تأكَّد مباشرة عبر `\d academy_instructors` —
    # انحراف حقيقي موديل↔DB، غير مرتبط بهذه الجلسة، راجع تقرير الجلسة).
    # `db.add(Instructor(...))` عبر ORM بيولّد INSERT شامل لكل أعمدة
    # الموديل المُعرَّفة (بما فيها `tenant_id`، حتى لو مش مُمرَّرة صراحةً —
    # اتأكَّد بالفشل الفعلي) فيفشل بـ`UndefinedColumnError` فورًا. الحل
    # هنا: `insert()` من Core بيحدد الأعمدة الموجودة فعليًا في DB بس.
    result = await db.execute(
        insert(Instructor.__table__)
        .values(user_id=instructor_user_id, org_entity_id=org_entity.id, is_approved=True)
        .returning(Instructor.__table__.c.id)
    )
    fx.instructor_id = result.scalar_one()

    course_with_instructor = Course(
        tenant_id=TENANT_ID, org_entity_id=org_entity.id, instructor_id=fx.instructor_id,
        title=f"REGTEST-COURSE-WITH-INSTRUCTOR-{suffix}", is_active=True,
    )
    course_without_instructor = Course(
        tenant_id=TENANT_ID, org_entity_id=org_entity.id, instructor_id=None,
        title=f"REGTEST-COURSE-NO-INSTRUCTOR-{suffix}", is_active=True,
    )
    course_not_enrolled = Course(
        tenant_id=TENANT_ID, org_entity_id=org_entity.id, instructor_id=fx.instructor_id,
        title=f"REGTEST-COURSE-NOT-ENROLLED-{suffix}", is_active=True,
    )
    db.add_all([course_with_instructor, course_without_instructor, course_not_enrolled])
    await db.flush()
    fx.course_with_instructor_id = course_with_instructor.id
    fx.course_without_instructor_id = course_without_instructor.id
    fx.course_not_enrolled_id = course_not_enrolled.id

    enrollment_1 = Enrollment(tenant_id=TENANT_ID, user_id=ward_id, course_id=course_with_instructor.id, status="ACTIVE")
    enrollment_2 = Enrollment(tenant_id=TENANT_ID, user_id=ward_id, course_id=course_without_instructor.id, status="ACTIVE")
    db.add_all([enrollment_1, enrollment_2])
    await db.flush()
    fx.enrollment_ids = [enrollment_1.id, enrollment_2.id]

    await db.commit()
    return fx


async def _cleanup_all(user_ids, relationship_id, fx: _Fixtures):
    async with AsyncSessionLocal() as cleanup_db:
        await cleanup_db.execute(delete(Notification).where(Notification.user_id.in_(user_ids)))
        if fx.enrollment_ids:
            await cleanup_db.execute(delete(Enrollment).where(Enrollment.id.in_(fx.enrollment_ids)))
        course_ids = [
            cid for cid in (fx.course_with_instructor_id, fx.course_without_instructor_id, fx.course_not_enrolled_id)
            if cid
        ]
        if course_ids:
            await cleanup_db.execute(delete(Course).where(Course.id.in_(course_ids)))
        if fx.instructor_id:
            await cleanup_db.execute(delete(Instructor).where(Instructor.id == fx.instructor_id))
        if fx.org_entity_id:
            await cleanup_db.execute(delete(OrganizationEntity).where(OrganizationEntity.id == fx.org_entity_id))
        if relationship_id:
            await cleanup_db.execute(
                delete(GuardianVisibilitySetting).where(GuardianVisibilitySetting.guardian_relationship_id == relationship_id)
            )
            await cleanup_db.execute(delete(GuardianRelationship).where(GuardianRelationship.id == relationship_id))
        await cleanup_db.execute(delete(User).where(User.id.in_(user_ids)))
        await cleanup_db.commit()


# ============================================================
# 1) نجاح كامل: تسجيل فعلي + مدرّس مُسنَد → صف Notification حقيقي
# ============================================================

@pytest.mark.asyncio
async def test_message_instructor_success_creates_real_notification(db):
    guardian = await _create_user(db, "p_regtest_msg_guardian")
    ward = await _create_user(db, "p_regtest_msg_ward")
    instructor_user = await _create_user(db, "p_regtest_msg_instructor")
    guardian_id, ward_id, instructor_user_id = guardian.id, ward.id, instructor_user.id

    relationship = await _create_verified_relationship(db, guardian_id, ward_id)
    relationship_id = relationship.id
    fx = await _build_courses(db, ward_id, instructor_user_id)

    try:
        service = GuardianService(db, TENANT_ID)
        message_text = f"REGTEST-MESSAGE-{_suffix()}"
        notification = await service.message_instructor(
            guardian_user_id=guardian_id, ward_user_id=ward_id,
            course_id=fx.course_with_instructor_id, message_text=message_text,
        )

        assert notification.user_id == instructor_user_id
        assert notification.body == message_text
        assert notification.data["course_id"] == fx.course_with_instructor_id
        assert notification.data["ward_id"] == ward_id
        assert notification.data["guardian_id"] == guardian_id

        # تحقق فعلي من DB — صف Notification حقيقي محفوظ، مش mock
        result = await db.execute(select(Notification).where(Notification.id == notification.id))
        stored = result.scalar_one_or_none()
        assert stored is not None
        assert stored.user_id == instructor_user_id
        assert stored.body == message_text
    finally:
        await _cleanup_all([guardian_id, ward_id, instructor_user_id], relationship_id, fx)


# ============================================================
# 2) قطاع ACADEMY محجوب → 403
# ============================================================

@pytest.mark.asyncio
async def test_message_instructor_rejected_when_academy_hidden(db):
    guardian = await _create_user(db, "p_regtest_msg_hidden_guardian")
    ward = await _create_user(db, "p_regtest_msg_hidden_ward")
    instructor_user = await _create_user(db, "p_regtest_msg_hidden_instructor")
    guardian_id, ward_id, instructor_user_id = guardian.id, ward.id, instructor_user.id

    relationship = await _create_verified_relationship(db, guardian_id, ward_id)
    relationship_id = relationship.id
    fx = await _build_courses(db, ward_id, instructor_user_id)

    try:
        service = GuardianService(db, TENANT_ID)
        await service.update_visibility(
            relationship_id=relationship_id, ward_user_id=ward_id,
            settings=[{"sector": GuardianVisibilitySector.ACADEMY, "is_visible": False}],
        )

        with pytest.raises(PermissionDeniedError):
            await service.message_instructor(
                guardian_user_id=guardian_id, ward_user_id=ward_id,
                course_id=fx.course_with_instructor_id, message_text="test",
            )
    finally:
        await _cleanup_all([guardian_id, ward_id, instructor_user_id], relationship_id, fx)


# ============================================================
# 3) course_id الطالب مش مسجَّل فيه → 404
# ============================================================

@pytest.mark.asyncio
async def test_message_instructor_rejected_for_course_not_enrolled(db):
    guardian = await _create_user(db, "p_regtest_msg_notenr_guardian")
    ward = await _create_user(db, "p_regtest_msg_notenr_ward")
    instructor_user = await _create_user(db, "p_regtest_msg_notenr_instructor")
    guardian_id, ward_id, instructor_user_id = guardian.id, ward.id, instructor_user.id

    relationship = await _create_verified_relationship(db, guardian_id, ward_id)
    relationship_id = relationship.id
    fx = await _build_courses(db, ward_id, instructor_user_id)

    try:
        service = GuardianService(db, TENANT_ID)
        with pytest.raises(NotFoundError):
            await service.message_instructor(
                guardian_user_id=guardian_id, ward_user_id=ward_id,
                course_id=fx.course_not_enrolled_id, message_text="test",
            )
    finally:
        await _cleanup_all([guardian_id, ward_id, instructor_user_id], relationship_id, fx)


# ============================================================
# 4) كورس بلا مدرّس مُسنَد (instructor_id IS NULL) → 404
# ============================================================

@pytest.mark.asyncio
async def test_message_instructor_rejected_for_course_without_instructor(db):
    guardian = await _create_user(db, "p_regtest_msg_noinstr_guardian")
    ward = await _create_user(db, "p_regtest_msg_noinstr_ward")
    instructor_user = await _create_user(db, "p_regtest_msg_noinstr_instructor")
    guardian_id, ward_id, instructor_user_id = guardian.id, ward.id, instructor_user.id

    relationship = await _create_verified_relationship(db, guardian_id, ward_id)
    relationship_id = relationship.id
    fx = await _build_courses(db, ward_id, instructor_user_id)

    try:
        service = GuardianService(db, TENANT_ID)
        with pytest.raises(NotFoundError):
            await service.message_instructor(
                guardian_user_id=guardian_id, ward_user_id=ward_id,
                course_id=fx.course_without_instructor_id, message_text="test",
            )
    finally:
        await _cleanup_all([guardian_id, ward_id, instructor_user_id], relationship_id, fx)
