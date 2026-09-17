"""
regression test لجلسة `health-appointments-tenant-isolation-fix`
(2026-09-16) — إصلاح أمني عاجل ومعزول تمامًا عن أي شغل guardian: كان
`HealthRepository.list_appointments`/`HealthService.get_my_appointments`
بيفلتروا مواعيد المستخدم بـ`patient_user_id` بس، **بلا أي فلتر
`tenant_id` إطلاقًا** — لو أي مسار مستقبلي استدعى الدالة دي بـ
`tenant_id` تاني (زي endpoint موحَّد يجمّع بيانات من عدة تينانتات، أو
أي منطق cross-user)، كانت هترجّع مواعيد المستخدم بغض النظر عن أي
تينانت. راجع:
.claude/reports/health-appointments-tenant-isolation-fix-session-log.md

يغطي: مستخدم بموعد طبي حقيقي في tenant_id=1 → استدعاء بـtenant_id=16
(مختلف) لازم يرجّع صفر نتائج (منع تسريب)، واستدعاء بـtenant_id=1
الصح لازم يرجّع الموعد عادي (صفر false negative من الإصلاح).
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.health.service import HealthService
from app.domains.health.repository import HealthRepository
from app.domains.health.models import MedicalAppointment, HealthFacility, FacilityCategory, AppointmentStatus
from app.domains.sites.models import Site, SiteType

TENANT_ID = 1
WRONG_TENANT_ID = 16


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


@pytest.mark.asyncio
async def test_get_my_appointments_isolates_by_tenant_id(db):
    patient = await _create_user(db, "p_regtest_health_patient")
    doctor = await _create_user(db, "p_regtest_health_doctor")
    patient_id, doctor_id = patient.id, doctor.id

    repo = HealthRepository(db)
    service = HealthService(db)
    facility_id = None
    appointment_id = None
    site_id = None
    try:
        site = Site(tenant_id=TENANT_ID, site_type=SiteType.HEALTH_FACILITY, name=f"REGTEST-HEALTH-SITE-{_suffix()}")
        db.add(site)
        await db.flush()
        site_id = site.id

        facility = await repo.create_facility(
            tenant_id=TENANT_ID,
            site_id=site_id,
            name=f"REGTEST-CLINIC-{_suffix()}",
            facility_category=FacilityCategory.CLINIC,
        )
        facility_id = facility.id

        appointment = await repo.create_appointment(
            tenant_id=TENANT_ID,
            patient_user_id=patient_id,
            doctor_id=doctor_id,
            facility_id=facility_id,
            appointment_time=datetime.now(timezone.utc) + timedelta(days=1),
            appointment_type="CHECKUP",
            status=AppointmentStatus.SCHEDULED,
        )
        appointment_id = appointment.id
        # commit إجباري قبل أي استعلام من session تانية في finally — نفس
        # سبب باج الـFK lock الموثَّق في جلسات guardian السابقة (INSERT
        # في medical_appointments بياخد قفل FOR KEY SHARE على صفوف
        # users/health_facilities المُشار إليها لحد ما الترانزاكشن تتقفل).
        await db.commit()

        # 1) tenant_id غلط (16) — لازم صفر نتائج، مش تسريب
        wrong_tenant_results = await service.get_my_appointments(
            user_id=patient_id, tenant_id=WRONG_TENANT_ID,
        )
        assert wrong_tenant_results == []

        # 2) tenant_id الصح (1) — الموعد لازم يظهر عادي
        correct_tenant_results = await service.get_my_appointments(
            user_id=patient_id, tenant_id=TENANT_ID,
        )
        assert len(correct_tenant_results) == 1
        assert correct_tenant_results[0].id == appointment_id
        assert correct_tenant_results[0].patient_user_id == patient_id
        assert correct_tenant_results[0].tenant_id == TENANT_ID
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            if appointment_id:
                await cleanup_db.execute(delete(MedicalAppointment).where(MedicalAppointment.id == appointment_id))
            if facility_id:
                await cleanup_db.execute(delete(HealthFacility).where(HealthFacility.id == facility_id))
            if site_id:
                await cleanup_db.execute(delete(Site).where(Site.id == site_id))
            await cleanup_db.execute(delete(User).where(User.id.in_([patient_id, doctor_id])))
            await cleanup_db.commit()
