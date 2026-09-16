"""
Regression test لجلسة `health-nameerror-and-fee-ordering-fix`.
تقرير التحقيق (قبل الإصلاح): .claude/reports/health-nameerror-investigation-session-log.md
تقرير الإصلاح: .claude/reports/health-nameerror-and-fee-ordering-fix-session-log.md

السبب الجذري (كان): كتلة `audit_log(...)` بالكامل اتنسخت-لصقت حرفيًا من
`employment/service.py::create_job` في 3 دوال مختلفة في `health/service.py`
(`book_appointment`, `trigger_emergency`, `create_facility`) بلا ما حد
يستبدل المتغير `job` بالكائن الفعلي، ولا `action="JOB_CREATED"` باسم مناسب.
النتيجة: `NameError` مضمون الحدوث في كل استدعاء بلا استثناء للثلاثة —
الثلاثة أحياء ومربوطة بـ`POST /appointments`, `POST /emergency`,
`POST /facilities` (health/router.py)، بدون أي تغطية اختبارات سابقة.

إضافة إلى ذلك، `create_facility` كانت أصلاً بلا باراميتر `tenant_id` رسمي
في توقيعها (كانت بتعتمد على مفتاح `tenant_id` جوه `data` dict، بينما كتلة
`audit_log` المنسوخة كانت بتحاول تقرأ اسم متغير مستقل `tenant_id` مش
موجود في النطاق إطلاقًا — أول NameError فعليًا في الدالة دي كان على
`tenant_id` نفسه، قبل ما يوصل لـ`job`).

**الإصلاح:**
1. الثلاثة `audit_log` blocks اتصححوا: `resource_id`/`details` بقوا
   بيشيروا للكائن الصحيح فعليًا (`appointment`/`dispatch`/`facility`)،
   و`action` بقى مناسب دلاليًا (`APPOINTMENT_BOOKED`/
   `EMERGENCY_DISPATCHED`/`FACILITY_CREATED`).
2. `create_facility` بقى ليها باراميتر `tenant_id: int` رسمي، والراوتر
   اتحدَّث ليمرره صراحةً (`tenant_id=cast(int, tenant.id)`) بدل حقنه يدويًا
   جوه dict الـ`data`.
3. `book_appointment`: كتلة `finance.transfer(...)` (خصم رسوم الحجز)
   اتنقلت لتكون *بعد* نجاح إنشاء الموعد جوه نفس `begin_nested()` بدل ما
   كانت قبله — لو فشل الخصم المالي، الـsavepoint بيتراجع عن إنشاء الموعد
   كمان (مايتسجّلش موعد مجاني)، ولو فشل إنشاء الموعد نفسه لأي سبب (زي FK
   violation)، الكود مايوصلش أصلاً لخصم أي رسوم (بعكس الترتيب القديم اللي
   كان بيخصم الرسوم الأول بغض النظر عن نجاح الإنشاء بعدين).

منهجية التحقق: استدعاء دوال الراوتر (`book_appointment`, `call_emergency`,
`create_facility` من `health/router.py`) *مباشرة* — نفس أسلوب
`test_trigger_renewals_endpoint_missing_commit.py` — عشان نتحقق من الـ
endpoint الفعلي (مش الـservice layer بس)، بجلسة DB حقيقية (`db` fixture)
وتحقق مستقل عبر `AsyncSessionLocal()` منفصلة تمامًا للتأكد من commit حقيقي
على القرص.
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels
from app.core.database import AsyncSessionLocal

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User
from app.domains.identity.repository import WalletRepository

from app.domains.finance.models import Wallet, Transaction, AuditLog as FinanceAuditLog

from app.domains.health.router import book_appointment, call_emergency, create_facility
from app.domains.health.repository import HealthRepository
from app.domains.health.service import ENTITY_TYPE
from app.domains.health.schemas import (
    MedicalAppointmentCreate, EmergencyDispatchCreate, HealthFacilityCreate,
)
from app.domains.health.models import (
    HealthFacility, MedicalAppointment, EmergencyDispatch,
    FacilityCategory, EmergencyType, AppointmentStatus, DispatchStatus,
)
from app.domains.sovereign_entities.models import SovereignEntity, SovereignEntityType
from app.core.models import EntityMembership, EntityMembershipRole

TENANT_ID = 1


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str, mr_usdt: Decimal = Decimal("0")) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    user = await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )
    if mr_usdt > 0:
        wallet_repo = WalletRepository(db)
        wallet = await wallet_repo.get_by_user_id(user.id, TENANT_ID)
        assert wallet is not None
        await wallet_repo.update_balances(wallet.id, {"MR_USDT": float(mr_usdt)})
    return user


async def _cleanup_users_and_finance(db, user_ids):
    if not user_ids:
        return
    await db.execute(delete(Transaction).where(Transaction.sender_id.in_(user_ids)))
    await db.execute(delete(FinanceAuditLog).where(FinanceAuditLog.user_id.in_(user_ids)))
    await db.execute(delete(Wallet).where(Wallet.user_id.in_(user_ids)))
    await db.execute(delete(User).where(User.id.in_(user_ids)))
    await db.commit()


# ============================================================
# 1) create_facility — NameError + tenant_id param مفقود
# ============================================================

@pytest.mark.asyncio
async def test_create_facility_endpoint_persists_with_correct_audit_data(db):
    """قبل الإصلاح: NameError على tenant_id (أول حاجة بتتقيَّم في الاستدعاء)
    ثم على job — 500 مضمون. بعد الإصلاح: لازم ينجح فعليًا، ويتسجل tenant_id
    الصحيح على الصف، ويكون audit_log قابل للتنفيذ بلا استثناء.

    محدَّث لجلسة `health-entity-membership-implementation` (2026-09-14):
    create_facility بقى بيتطلب entity_id + عضوية صالحة (OWNER/
    EXECUTIVE_DIRECTOR) في الكيان السيادي — راجع
    test_health_entity_membership_full_implementation.py لسيناريوهات
    العضوية الكاملة (غير عضو / SET NULL)."""
    admin = await _create_user(db, "p_health_facility_admin")
    suffix = _suffix()
    entity = SovereignEntity(
        tenant_id=TENANT_ID,
        name=f"REGTEST-HEALTHFAC-NAMEERROR-ENTITY-{suffix}",
        entity_type=SovereignEntityType.ENTERPRISE,
        country_of_origin="EG",
        official_email=f"regtest-healthfac-nameerror-entity-{suffix}@eppne.com",
        created_by=admin.id,
    )
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    db.add(EntityMembership(
        entity_type=ENTITY_TYPE, entity_id=entity.id,
        user_id=admin.id, tenant_id=TENANT_ID, role=EntityMembershipRole.OWNER,
    ))
    await db.commit()

    tenant = SimpleNamespace(id=TENANT_ID)
    data = HealthFacilityCreate(
        entity_id=entity.id,
        name=f"REGTEST-Clinic-{suffix}",
        facility_category=FacilityCategory.CLINIC,
        specialties=["general"],
    )

    try:
        facility = await create_facility(data=data, tenant=tenant, current_user=admin, db=db)
        assert facility.id is not None
        assert facility.name == data.name
        assert facility.tenant_id == TENANT_ID
        assert facility.entity_id == entity.id

        async with AsyncSessionLocal() as independent_db:
            row = (await independent_db.execute(
                select(HealthFacility).where(HealthFacility.id == facility.id)
            )).scalar_one_or_none()
            assert row is not None, "المنشأة لازم تُحفَظ فعليًا (commit حقيقي بعد نجاح audit_log)"
            assert row.tenant_id == TENANT_ID
            assert row.name == data.name
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(HealthFacility).where(HealthFacility.name == data.name))
            await cleanup_db.execute(delete(EntityMembership).where(
                EntityMembership.entity_type == ENTITY_TYPE,
                EntityMembership.entity_id == entity.id,
                EntityMembership.user_id == admin.id,
            ))
            await cleanup_db.execute(delete(SovereignEntity).where(SovereignEntity.id == entity.id))
            await cleanup_db.commit()
        await _cleanup_users_and_finance(db, [admin.id])


# ============================================================
# 2) trigger_emergency — NameError على job
# ============================================================

@pytest.mark.asyncio
async def test_trigger_emergency_endpoint_persists_with_correct_audit_data(db):
    """قبل الإصلاح: 500 مضمون (NameError على job) في كل استدعاء. بعد
    الإصلاح: لازم ينجح، ويتسجل patient_id = caller_id (data.patient_id
    غير ممرَّر)، والحالة PENDING."""
    caller = await _create_user(db, "p_health_emergency_caller")
    tenant = SimpleNamespace(id=TENANT_ID)
    data = EmergencyDispatchCreate(
        emergency_type=EmergencyType.MEDICAL_CRITICAL,
        gps_location={"lat": 30.0, "lng": 31.0},
    )

    try:
        dispatch = await call_emergency(
            data=data, request=None, idempotency_key=None,
            tenant=tenant, current_user=caller, db=db,
        )
        assert dispatch.id is not None
        assert dispatch.status == DispatchStatus.PENDING
        assert dispatch.patient_id == caller.id

        async with AsyncSessionLocal() as independent_db:
            row = (await independent_db.execute(
                select(EmergencyDispatch).where(EmergencyDispatch.id == dispatch.id)
            )).scalar_one_or_none()
            assert row is not None, "البلاغ لازم يُحفَظ فعليًا (commit حقيقي بعد نجاح audit_log)"
            assert row.emergency_type == EmergencyType.MEDICAL_CRITICAL
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(EmergencyDispatch).where(EmergencyDispatch.patient_id == caller.id))
            await cleanup_db.commit()
        await _cleanup_users_and_finance(db, [caller.id])


# ============================================================
# 3) book_appointment — NameError + ترتيب الخصم المالي
# ============================================================

@pytest.mark.asyncio
async def test_book_appointment_endpoint_success_charges_fee_exactly_once(db):
    """المسار السعيد: قبل الإصلاح 500 مضمون (NameError). بعد الإصلاح لازم
    الموعد يتسجل، والرسوم (10 MR_USDT) تُخصم من المريض بالظبط مرة واحدة،
    وده كله بعد نجاح إنشاء الموعد (نفس الـsavepoint)."""
    patient = await _create_user(db, "p_health_appt_patient", mr_usdt=Decimal("100"))
    doctor = await _create_user(db, "p_health_appt_doctor")
    tenant = SimpleNamespace(id=TENANT_ID)

    health_repo = HealthRepository(db)
    facility = await health_repo.create_facility(
        tenant_id=TENANT_ID,
        name=f"REGTEST-ApptFacility-{_suffix()}",
        facility_category=FacilityCategory.CLINIC,
    )
    await db.commit()

    data = MedicalAppointmentCreate(
        doctor_id=doctor.id,
        facility_id=facility.id,
        appointment_time=datetime.now(timezone.utc) + timedelta(days=1),
    )

    try:
        # ملحوظة: idempotency_key=None عمدًا — تمريره كأي قيمة غير فارغة
        # هنا بيصطدم ببج منفصل تمامًا (check_idempotency بترجع True لما
        # المفتاح *جديد* عبر SETNX، لكن _validate_idempotency بتتعامل مع
        # أي قيمة truthy كـ"نتيجة مخزنة" وترجعها فورًا)، فبتقصّر الدالة
        # كاملة لترجع True بدل الموعد الحقيقي. ده خارج نطاق هذا الإصلاح
        # (موثَّق في تقرير الجلسة، غير ملموس هنا).
        appointment = await book_appointment(
            data=data, request=None, idempotency_key=None,
            tenant=tenant, current_user=patient, db=db,
        )
        assert appointment.id is not None
        assert appointment.status == AppointmentStatus.SCHEDULED
        assert appointment.patient_user_id == patient.id

        async with AsyncSessionLocal() as independent_db:
            appt_row = (await independent_db.execute(
                select(MedicalAppointment).where(MedicalAppointment.id == appointment.id)
            )).scalar_one_or_none()
            assert appt_row is not None, "الموعد لازم يُحفَظ فعليًا (commit حقيقي بعد نجاح audit_log)"

            wallet_repo = WalletRepository(independent_db)
            wallet = await wallet_repo.get_by_user_id(patient.id, TENANT_ID)
            assert Decimal(str(wallet.balances.get("MR_USDT"))) == Decimal("90.00"), (
                "المفروض يتخصم 10 MR_USDT بالظبط (رسوم الحجز) بعد نجاح إنشاء الموعد"
            )

            tx = (await independent_db.execute(
                select(Transaction).where(Transaction.sender_id == patient.id)
            )).scalar_one_or_none()
            assert tx is not None
            assert Decimal(str(tx.amount)) == Decimal("10.00")
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(MedicalAppointment).where(MedicalAppointment.doctor_id == doctor.id))
            await cleanup_db.execute(delete(HealthFacility).where(HealthFacility.id == facility.id))
            await cleanup_db.commit()
        await _cleanup_users_and_finance(db, [patient.id, doctor.id])


@pytest.mark.asyncio
async def test_book_appointment_fee_not_charged_when_appointment_creation_fails(db):
    """يتحقق تحديدًا من إصلاح ترتيب الخصم المالي: لو فشل إنشاء الموعد
    (هنا: facility_id غير موجود → FK violation عند flush())، لازم الرسوم
    ما تتخصمش خالص — قبل إصلاح الترتيب، كان الخصم بيحصل *قبل* محاولة
    الإنشاء، فكان بيفضل نافذًا حتى لو فشل الإنشاء بعده."""
    patient = await _create_user(db, "p_health_appt_fail_patient", mr_usdt=Decimal("100"))
    doctor = await _create_user(db, "p_health_appt_fail_doctor")
    tenant = SimpleNamespace(id=TENANT_ID)

    nonexistent_facility_id = 2_147_483_647  # أقصى int32 — شبه مؤكد مش موجود
    data = MedicalAppointmentCreate(
        doctor_id=doctor.id,
        facility_id=nonexistent_facility_id,
        appointment_time=datetime.now(timezone.utc) + timedelta(days=1),
    )

    try:
        with pytest.raises(IntegrityError):
            await book_appointment(
                data=data, request=None, idempotency_key=None,
                tenant=tenant, current_user=patient, db=db,
            )

        async with AsyncSessionLocal() as independent_db:
            wallet_repo = WalletRepository(independent_db)
            wallet = await wallet_repo.get_by_user_id(patient.id, TENANT_ID)
            assert Decimal(str(wallet.balances.get("MR_USDT"))) == Decimal("100.00"), (
                "الرسوم ما كانش المفروض تتخصم — إنشاء الموعد فشل قبل الوصول لكتلة الخصم المالي"
            )

            appt_row = (await independent_db.execute(
                select(MedicalAppointment).where(MedicalAppointment.doctor_id == doctor.id)
            )).scalar_one_or_none()
            assert appt_row is None, "مفروض ما يتسجلش أي موعد نتيجة فشل الـFK"

            tx = (await independent_db.execute(
                select(Transaction).where(Transaction.sender_id == patient.id)
            )).scalar_one_or_none()
            assert tx is None, "مفروض ما يتسجلش أي تحويل مالي نتيجة فشل إنشاء الموعد"
    finally:
        await _cleanup_users_and_finance(db, [patient.id, doctor.id])
