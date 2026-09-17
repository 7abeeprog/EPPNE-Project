"""
regression test لجلسة `guardian-overview-endpoint-implementation`
(2026-09-16) — GET /guardian/wards/{ward_id}/overview: endpoint موحَّد
يجمّع ملخصات خفيفة من 4 دومينات (academy+achievements, social,
transport, health) محترمًا GuardianVisibilitySetting. فوق أساس
[[project_guardian_relationship_flow_implementation]]. راجع:
.claude/reports/guardian-overview-endpoint-implementation-session-log.md

يغطي: علاقة VERIFIED كاملة + نشاط حقيقي في القطاعات الأربعة → الرد
يحتوي بيانات صحيحة من كل قطاع؛ حجب قطاع HEALTH → استبعاده تمامًا من
الرد (صفر مفتاح، مش قيمة فاضية)؛ علاقة PENDING_WARD_APPROVAL (مش
VERIFIED بعد) → 403؛ مستخدم بلا أي علاقة إطلاقًا → 403.

كل الـfixtures (كورس/تسجيل، تعريف إنجاز/منح، منشور/تعليق، محطة/أسطول/
مركبة/مسار/رحلة/حجز، منشأة/موعد) بتتعمل عبر إدخال ORM مباشر (بلا
المرور بمنطق الأعمال الكامل لكل دومين — زي رسوم الحجز/الدفع) لأن
الهدف اختبار طبقة guardian نفسها (التفويض + الرؤية + التجميع)، مش
إعادة اختبار كل دومين على حدة (له اختباراته المنفصلة بالفعل).
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.core.errors import PermissionDeniedError

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.guardian.service import GuardianService
from app.domains.guardian.repository import GuardianRepository
from app.domains.guardian.models import (
    GuardianRelationship, GuardianVisibilitySetting,
    GuardianRelationshipType, GuardianVisibilitySector,
)

from app.domains.academy.models import OrganizationEntity, Course, Enrollment
from app.domains.achievements.models import (
    AchievementDefinition, UserAchievement, AchievementCategory, AchievementTriggerType,
)
from app.domains.social.models import Post, PostComment, PostType
from app.domains.transport.models import (
    TransportHub, Fleet, Vehicle, Route, Trip, TripBooking, TransportType, TripCategory,
)
from app.domains.health.models import HealthFacility, MedicalAppointment, FacilityCategory, AppointmentStatus
from app.domains.sites.models import Site, SiteType

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
    approved = await service.approve_relationship(
        relationship_id=relationship.id, ward_user_id=ward_id,
        ward_birth_date_provided=ADULT_BIRTH_DATE,
    )
    return approved


class _Fixtures:
    """حاوية لكل الـids المُنشأة عبر الدومينات الأربعة — لتسهيل التنظيف."""
    def __init__(self):
        self.org_entity_id = None
        self.course_id = None
        self.enrollment_id = None
        self.achievement_definition_id = None
        self.user_achievement_id = None
        self.post_id = None
        self.comment_id = None
        self.hub_ids = []
        self.fleet_id = None
        self.vehicle_id = None
        self.route_id = None
        self.trip_id = None
        self.booking_id = None
        self.facility_id = None
        self.appointment_id = None
        self.health_site_id = None


async def _build_ward_activity(db, ward_id: int, doctor_id: int, driver_id: int) -> _Fixtures:
    fx = _Fixtures()
    suffix = _suffix()

    # ---- ACADEMY: كورس + تسجيل ----
    org_entity = OrganizationEntity(tenant_id=TENANT_ID, name=f"REGTEST-ORG-{suffix}", entity_type="ACADEMY", is_active=True)
    db.add(org_entity)
    await db.flush()
    fx.org_entity_id = org_entity.id

    course = Course(tenant_id=TENANT_ID, org_entity_id=org_entity.id, title=f"REGTEST-COURSE-{suffix}", is_active=True)
    db.add(course)
    await db.flush()
    fx.course_id = course.id

    enrollment = Enrollment(
        tenant_id=TENANT_ID, user_id=ward_id, course_id=course.id,
        progress_percentage=Decimal("45.00"), is_completed=False, status="ACTIVE",
    )
    db.add(enrollment)
    await db.flush()
    fx.enrollment_id = enrollment.id

    # ---- ACHIEVEMENTS ----
    definition = AchievementDefinition(
        tenant_id=TENANT_ID, name=f"REGTEST-BADGE-{suffix}", description="badge",
        category=AchievementCategory.TRAINING, points_value=10,
        trigger_type=AchievementTriggerType.MANUAL, is_active=True, created_by=doctor_id,
    )
    db.add(definition)
    await db.flush()
    fx.achievement_definition_id = definition.id

    user_achievement = UserAchievement(
        tenant_id=TENANT_ID, user_id=ward_id, achievement_definition_id=definition.id, granted_by=doctor_id,
    )
    db.add(user_achievement)
    await db.flush()
    fx.user_achievement_id = user_achievement.id

    # ---- SOCIAL: منشور + تعليق ----
    post = Post(tenant_id=TENANT_ID, author_id=ward_id, content=f"REGTEST-POST-{suffix}", post_type=PostType.TEXT)
    db.add(post)
    await db.flush()
    fx.post_id = post.id

    comment = PostComment(tenant_id=TENANT_ID, post_id=post.id, author_id=ward_id, content=f"REGTEST-COMMENT-{suffix}")
    db.add(comment)
    await db.flush()
    fx.comment_id = comment.id

    # ---- TRANSPORT: محطتان + أسطول + مركبة + مسار + رحلة + حجز ----
    hub_a = TransportHub(tenant_id=TENANT_ID, name=f"REGTEST-HUB-A-{suffix}", hub_type="BUS_STATION", gps_location={"lat": 30.0, "lng": 31.0})
    hub_b = TransportHub(tenant_id=TENANT_ID, name=f"REGTEST-HUB-B-{suffix}", hub_type="BUS_STATION", gps_location={"lat": 30.1, "lng": 31.1})
    db.add_all([hub_a, hub_b])
    await db.flush()
    fx.hub_ids = [hub_a.id, hub_b.id]

    fleet = Fleet(tenant_id=TENANT_ID, name=f"REGTEST-FLEET-{suffix}")
    db.add(fleet)
    await db.flush()
    fx.fleet_id = fleet.id

    vehicle = Vehicle(
        tenant_id=TENANT_ID, fleet_id=fleet.id, license_plate=f"REGTEST-{suffix}",
        vehicle_type=TransportType.BUS, capacity_passengers=40,
    )
    db.add(vehicle)
    await db.flush()
    fx.vehicle_id = vehicle.id

    route = Route(
        tenant_id=TENANT_ID, name=f"REGTEST-ROUTE-{suffix}", start_hub_id=hub_a.id, end_hub_id=hub_b.id,
        distance_km=Decimal("10.0"), estimated_duration_minutes=30,
    )
    db.add(route)
    await db.flush()
    fx.route_id = route.id

    trip_start = datetime.now(timezone.utc) + timedelta(days=1)
    trip = Trip(
        tenant_id=TENANT_ID, route_id=route.id, vehicle_id=vehicle.id, driver_id=driver_id,
        trip_category=TripCategory.PASSENGER, scheduled_start=trip_start, scheduled_end=trip_start + timedelta(hours=1),
    )
    db.add(trip)
    await db.flush()
    fx.trip_id = trip.id

    booking = TripBooking(
        tenant_id=TENANT_ID, trip_id=trip.id, passenger_id=ward_id, booking_type="SEAT",
        seats_count=1, fare_paid_mrusdt=Decimal("5.00"), status="CONFIRMED",
    )
    db.add(booking)
    await db.flush()
    fx.booking_id = booking.id

    # ---- HEALTH: منشأة + موعد ----
    health_site = Site(tenant_id=TENANT_ID, site_type=SiteType.HEALTH_FACILITY, name=f"REGTEST-HEALTH-SITE-{suffix}")
    db.add(health_site)
    await db.flush()
    fx.health_site_id = health_site.id

    facility = HealthFacility(tenant_id=TENANT_ID, site_id=health_site.id, name=f"REGTEST-CLINIC-{suffix}", facility_category=FacilityCategory.CLINIC)
    db.add(facility)
    await db.flush()
    fx.facility_id = facility.id

    appointment = MedicalAppointment(
        tenant_id=TENANT_ID, patient_user_id=ward_id, doctor_id=doctor_id, facility_id=facility.id,
        appointment_time=datetime.now(timezone.utc) + timedelta(days=2),
        appointment_type="CHECKUP", status=AppointmentStatus.SCHEDULED,
    )
    db.add(appointment)
    await db.flush()
    fx.appointment_id = appointment.id

    await db.commit()
    return fx


async def _cleanup_all(user_ids, relationship_id, fx: _Fixtures):
    async with AsyncSessionLocal() as cleanup_db:
        if fx.appointment_id:
            await cleanup_db.execute(delete(MedicalAppointment).where(MedicalAppointment.id == fx.appointment_id))
        if fx.facility_id:
            await cleanup_db.execute(delete(HealthFacility).where(HealthFacility.id == fx.facility_id))
        if fx.health_site_id:
            await cleanup_db.execute(delete(Site).where(Site.id == fx.health_site_id))
        if fx.booking_id:
            await cleanup_db.execute(delete(TripBooking).where(TripBooking.id == fx.booking_id))
        if fx.trip_id:
            await cleanup_db.execute(delete(Trip).where(Trip.id == fx.trip_id))
        if fx.route_id:
            await cleanup_db.execute(delete(Route).where(Route.id == fx.route_id))
        if fx.vehicle_id:
            await cleanup_db.execute(delete(Vehicle).where(Vehicle.id == fx.vehicle_id))
        if fx.fleet_id:
            await cleanup_db.execute(delete(Fleet).where(Fleet.id == fx.fleet_id))
        if fx.hub_ids:
            await cleanup_db.execute(delete(TransportHub).where(TransportHub.id.in_(fx.hub_ids)))
        if fx.comment_id:
            await cleanup_db.execute(delete(PostComment).where(PostComment.id == fx.comment_id))
        if fx.post_id:
            await cleanup_db.execute(delete(Post).where(Post.id == fx.post_id))
        if fx.user_achievement_id:
            await cleanup_db.execute(delete(UserAchievement).where(UserAchievement.id == fx.user_achievement_id))
        if fx.achievement_definition_id:
            await cleanup_db.execute(delete(AchievementDefinition).where(AchievementDefinition.id == fx.achievement_definition_id))
        if fx.enrollment_id:
            await cleanup_db.execute(delete(Enrollment).where(Enrollment.id == fx.enrollment_id))
        if fx.course_id:
            await cleanup_db.execute(delete(Course).where(Course.id == fx.course_id))
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
# 1) نظرة شاملة صحيحة + حجب قطاع HEALTH
# ============================================================

@pytest.mark.asyncio
async def test_overview_returns_all_sectors_then_excludes_hidden_health(db):
    guardian = await _create_user(db, "p_regtest_ov_guardian")
    ward = await _create_user(db, "p_regtest_ov_ward")
    doctor = await _create_user(db, "p_regtest_ov_doctor")
    driver = await _create_user(db, "p_regtest_ov_driver")
    guardian_id, ward_id, doctor_id, driver_id = guardian.id, ward.id, doctor.id, driver.id

    relationship = await _create_verified_relationship(db, guardian_id, ward_id)
    relationship_id = relationship.id
    fx = await _build_ward_activity(db, ward_id, doctor_id, driver_id)

    try:
        service = GuardianService(db, TENANT_ID)
        overview = await service.get_ward_overview(guardian_user_id=guardian_id, ward_user_id=ward_id)

        assert overview["ward_id"] == ward_id

        # ACADEMY
        assert len(overview["academy"]["enrollments"]) == 1
        enrollment_item = overview["academy"]["enrollments"][0]
        assert enrollment_item["course_title"].startswith("REGTEST-COURSE-")
        assert enrollment_item["progress_percentage"] == 45.0
        assert enrollment_item["is_completed"] is False

        assert len(overview["academy"]["achievements"]) == 1
        achievement_item = overview["academy"]["achievements"][0]
        assert achievement_item["name"].startswith("REGTEST-BADGE-")

        # SOCIAL
        assert overview["social"]["post_count"] == 1
        assert overview["social"]["comment_count"] == 1
        assert overview["social"]["last_activity_at"] is not None

        # TRANSPORT
        assert len(overview["transport"]) == 1
        assert overview["transport"][0]["status"] == "CONFIRMED"
        assert overview["transport"][0]["trip_date"] is not None

        # HEALTH
        assert len(overview["health"]) == 1
        assert overview["health"][0]["facility_name"].startswith("REGTEST-CLINIC-")
        assert overview["health"][0]["status"] == AppointmentStatus.SCHEDULED

        # ---- الآن الطالب يحجب قطاع HEALTH بس ----
        await service.update_visibility(
            relationship_id=relationship_id, ward_user_id=ward_id,
            settings=[{"sector": GuardianVisibilitySector.HEALTH, "is_visible": False}],
        )

        overview_after_hide = await service.get_ward_overview(guardian_user_id=guardian_id, ward_user_id=ward_id)
        assert "health" not in overview_after_hide  # استبعاد كامل، مش قيمة فاضية
        assert "academy" in overview_after_hide
        assert "social" in overview_after_hide
        assert "transport" in overview_after_hide
    finally:
        await _cleanup_all([guardian_id, ward_id, doctor_id, driver_id], relationship_id, fx)


# ============================================================
# 2) علاقة PENDING_WARD_APPROVAL (مش VERIFIED بعد) → 403
# ============================================================

@pytest.mark.asyncio
async def test_overview_rejected_for_pending_relationship(db):
    guardian = await _create_user(db, "p_regtest_ov_pending_guardian")
    ward = await _create_user(db, "p_regtest_ov_pending_ward")
    guardian_id, ward_id = guardian.id, ward.id

    service = GuardianService(db, TENANT_ID)
    relationship = await service.create_relationship_request(
        guardian_user_id=guardian_id, ward_user_id=ward_id,
        relationship_type=GuardianRelationshipType.MOTHER,
    )
    relationship_id = relationship.id

    try:
        with pytest.raises(PermissionDeniedError):
            await service.get_ward_overview(guardian_user_id=guardian_id, ward_user_id=ward_id)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(GuardianRelationship).where(GuardianRelationship.id == relationship_id))
            await cleanup_db.execute(delete(User).where(User.id.in_([guardian_id, ward_id])))
            await cleanup_db.commit()


# ============================================================
# 3) مستخدم بلا أي علاقة إطلاقًا → 403
# ============================================================

@pytest.mark.asyncio
async def test_overview_rejected_for_user_with_no_relationship(db):
    stranger = await _create_user(db, "p_regtest_ov_stranger")
    ward = await _create_user(db, "p_regtest_ov_unrelated_ward")
    stranger_id, ward_id = stranger.id, ward.id

    try:
        service = GuardianService(db, TENANT_ID)
        with pytest.raises(PermissionDeniedError):
            await service.get_ward_overview(guardian_user_id=stranger_id, ward_user_id=ward_id)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(User).where(User.id.in_([stranger_id, ward_id])))
            await cleanup_db.commit()
