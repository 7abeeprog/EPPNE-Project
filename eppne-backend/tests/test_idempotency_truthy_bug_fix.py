"""
Regression test لجلسة `idempotency-truthy-bug-fix`.
تقرير الجلسة: .claude/reports/idempotency-truthy-bug-fix-session-log.md
اكتُشف أصلاً أثناء جلسة `health-nameerror-and-fee-ordering-fix` (راجع
`.claude/reports/health-nameerror-and-fee-ordering-fix-session-log.md` §2)
ووُثِّق كبند backlog في `PROGRESS_LOG.md`
(`backlog-idempotency-check-truthy-misinterpretation-health`).

**السبب الجذري (كان):** `check_idempotency()` (`app/core/idempotency.py`)
بترجع `True` لما المفتاح *جديد* (SETNX نجح) — مش لما فيه نتيجة سابقة
مخزَّنة. أربع نقاط استخدام كانت بتفسّر أي قيمة truthy على إنها "نتيجة
سابقة موجودة" وترجعها فورًا:
1. `health/service.py::_validate_idempotency` (يستخدمها `book_appointment`)
2. `health/service.py::trigger_emergency` (نسخة مكرَّرة من نفس المنطق مباشرة)
3. `communications/router.py::send_notification` (سطور 98-102 قديمًا)
4. `communications/router.py::send_mail` (سطور 210-214 قديمًا)

النتيجة: أول استخدام حقيقي لأي `Idempotency-Key` جديد كان بيرجّع `True`
(bool) فورًا بدل تنفيذ العملية — صفر إنشاء، صفر خصم، صفر audit، صفر
إرسال فعلي.

**الإصلاح المطبَّق (مختلف حسب الموضع، بعد فحص `safe_execute_with_idempotency`):**

- `safe_execute_with_idempotency()` (`app/core/idempotency.py:50-74`) اتفحصت
  كخيار أول مفضَّل — بترجع/تخزن أي نتيجة عبر `json.dumps(result,
  default=str)`. **مش مناسبة مباشرة** للأربع مواضع دي: التلاتة الأولى
  (`book_appointment`, `trigger_emergency`) بترجع كائنات SQLAlchemy ORM
  (`MedicalAppointment`/`EmergencyDispatch`) — تمريرها مباشرة لـ
  `store_idempotency_result` هيسربلها عبر `default=str` (بيرجع سترينج
  زي `<...MedicalAppointment object at 0x...>` بدل بيانات حقيقية)، وعند
  الاسترجاع (`get_idempotency_result`) هترجع نفس السترينج ده كنتيجة —
  باج جديد مختلف تمامًا (نتيجة غير قابلة لإعادة البناء) بدل الباج الحالي.
  استخدامها كان يحتاج تعديل إضافي (تخزين `{"id": obj.id}` بدل الكائن
  الكامل) على أي حال، فاختير **الإصلاح المحلي المباشر** بدل التفاف حول
  helper مش مصمم لهذا الشكل من النتائج.

- **`health/service.py` (موضعان 1+2):** `_validate_idempotency` صُححت
  لتستخدم `check_idempotency()` بشكل صحيح (`True` = مفتاح جديد → تابع
  التنفيذ)، وتقرأ النتيجة الحقيقية عبر `get_idempotency_result()`
  المنفصلة (كانت غير مُستخدَمة إطلاقًا في `_validate_idempotency` الأصلية
  رغم استيرادها الآن). `_store_idempotency` صُححت لتخزن `{"id":
  result.id}` بس (مش الكائن الكامل — نفس سبب استبعاد
  `safe_execute_with_idempotency` أعلاه)، وتُعاد جلب الكائن الحقيقي من DB
  بالـid عند التكرار (`self.repo.get_appointment`/`get_dispatch`). لو
  المفتاح محجوز لكن لسه مفيش نتيجة مخزَّنة (العملية الأصلية لسه قيد
  التنفيذ)، بترمي `IdempotencyError` (مسجَّلة أصلاً بـexception handler
  في `main.py` → 409 Conflict) بدل ما ترجع `None`/تتجاهل الحالة. كمان
  اتشالت الكتلة المكرَّرة جوه `trigger_emergency` (كانت نسخة طبق الأصل من
  نفس المنطق الغلط) واستُبدلت باستدعاء `_validate_idempotency` الموحَّدة
  — نفس السبب الجذري، نفس الإصلاح، مكان واحد بس دلوقتي.

- **`communications/router.py` (موضعان 3+4):** الإصلاح هنا مختلف عمدًا —
  `CommunicationsService.send_notification`/`send_mail`
  (`communications/service.py:54-57` و`135-138`) *أصلاً* بيعملوا تحقق
  Idempotency صحيح ومستقل تمامًا عبر عمود `idempotency_key` الفريد
  (`unique=True`) على جدولي `notifications`/`mail_messages` نفسهم
  (`repo.get_notification_by_idempotency`/`get_message_by_idempotency`)
  — بيرجعوا السجل الموجود فعليًا لو المفتاح مُستخدَم من قبل، **قبل** أي
  إنشاء جديد. طبقة `check_idempotency`/`store_idempotency_result` القديمة
  في الراوتر كانت طبقة Redis زيادة وغير ضرورية فوق هذا التحقق الصحيح
  أصلاً، وهي اللي كانت حاملة الباج. الإصلاح: **حذف الطبقة الزيادة
  بالكامل** (بدل محاولة تصحيحها) — الاعتماد صار فقط على تحقق الـservice
  الصحيح والمُختبَر مسبقًا، وصفر تعديل على `service.py` (لم يكن معطوبًا).
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select, delete

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels
from app.core.database import AsyncSessionLocal

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User
from app.domains.identity.repository import WalletRepository

from app.domains.finance.models import Wallet, Transaction, AuditLog as FinanceAuditLog

from app.domains.health.router import book_appointment, call_emergency
from app.domains.health.repository import HealthRepository
from app.domains.health.schemas import MedicalAppointmentCreate, EmergencyDispatchCreate
from app.domains.health.models import (
    HealthFacility, MedicalAppointment, EmergencyDispatch,
    FacilityCategory, EmergencyType,
)

from app.domains.communications.router import send_notification, send_mail
from app.domains.communications.schemas import NotificationCreate, MailMessageCreate
from app.domains.communications.models import Notification, MailMessage, MailThread, MailboxItem

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
# 1) health/service.py::book_appointment (_validate_idempotency)
# ============================================================

@pytest.mark.asyncio
async def test_book_appointment_first_call_executes_second_call_returns_same_appointment(db):
    """قبل الإصلاح: أول استدعاء بمفتاح جديد كان بيرجّع True فورًا (صفر
    حجز، صفر خصم). بعد الإصلاح: أول استدعاء لازم ينفّذ فعليًا، والتكرار
    بنفس المفتاح لازم يرجّع *نفس* الموعد بالظبط بلا حجز أو خصم إضافي."""
    patient = await _create_user(db, "p_idem_appt_patient", mr_usdt=Decimal("100"))
    doctor = await _create_user(db, "p_idem_appt_doctor")
    tenant = SimpleNamespace(id=TENANT_ID)

    health_repo = HealthRepository(db)
    facility = await health_repo.create_facility(
        tenant_id=TENANT_ID,
        name=f"REGTEST-IdemFacility-{_suffix()}",
        facility_category=FacilityCategory.CLINIC,
    )
    await db.commit()

    idem_key = f"REGTEST-IDEM-APPT-{_suffix()}"
    data = MedicalAppointmentCreate(
        doctor_id=doctor.id,
        facility_id=facility.id,
        appointment_time=datetime.now(timezone.utc) + timedelta(days=1),
    )

    try:
        first = await book_appointment(
            data=data, request=None, idempotency_key=idem_key,
            tenant=tenant, current_user=patient, db=db,
        )
        assert not isinstance(first, bool), "الباج القديم: أول استدعاء بمفتاح جديد رجع True بدل الموعد"
        assert first.id is not None
        assert first.status is not None

        second = await book_appointment(
            data=data, request=None, idempotency_key=idem_key,
            tenant=tenant, current_user=patient, db=db,
        )
        assert not isinstance(second, bool)
        assert second.id == first.id, "التكرار بنفس المفتاح لازم يرجّع نفس الموعد بالظبط، مش موعد جديد"

        async with AsyncSessionLocal() as independent_db:
            count = (await independent_db.execute(
                select(MedicalAppointment).where(MedicalAppointment.doctor_id == doctor.id)
            )).scalars().all()
            assert len(count) == 1, "لازم يتسجل موعد واحد بس، مش موعدين نتيجة التكرار"

            wallet_repo = WalletRepository(independent_db)
            wallet = await wallet_repo.get_by_user_id(patient.id, TENANT_ID)
            assert Decimal(str(wallet.balances.get("MR_USDT"))) == Decimal("90.00"), (
                "الرسوم لازم تُخصم مرة واحدة بس (10 MR_USDT) — التكرار ما يخصمش تاني"
            )
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(MedicalAppointment).where(MedicalAppointment.doctor_id == doctor.id))
            await cleanup_db.execute(delete(HealthFacility).where(HealthFacility.id == facility.id))
            await cleanup_db.commit()
        await _cleanup_users_and_finance(db, [patient.id, doctor.id])


# ============================================================
# 2) health/service.py::trigger_emergency (نفس النمط، جوّه الدالة مباشرة)
# ============================================================

@pytest.mark.asyncio
async def test_trigger_emergency_first_call_executes_second_call_returns_same_dispatch(db):
    """نفس منهجية الاختبار السابق لـ`trigger_emergency` — كانت الكتلة
    الداخلية (مش عبر _validate_idempotency) بنفس العيب بالحرف، واتحدَّثت
    لتستخدم الهيلبر الموحَّد المُصحَّح."""
    caller = await _create_user(db, "p_idem_emrg_caller")
    tenant = SimpleNamespace(id=TENANT_ID)

    idem_key = f"REGTEST-IDEM-EMRG-{_suffix()}"
    data = EmergencyDispatchCreate(
        emergency_type=EmergencyType.MEDICAL_CRITICAL,
        gps_location={"lat": 30.0, "lng": 31.0},
    )

    try:
        first = await call_emergency(
            data=data, request=None, idempotency_key=idem_key,
            tenant=tenant, current_user=caller, db=db,
        )
        assert not isinstance(first, bool), "الباج القديم: أول استدعاء بمفتاح جديد رجع True بدل البلاغ"
        assert first.id is not None

        second = await call_emergency(
            data=data, request=None, idempotency_key=idem_key,
            tenant=tenant, current_user=caller, db=db,
        )
        assert not isinstance(second, bool)
        assert second.id == first.id, "التكرار بنفس المفتاح لازم يرجّع نفس البلاغ بالظبط"

        async with AsyncSessionLocal() as independent_db:
            count = (await independent_db.execute(
                select(EmergencyDispatch).where(EmergencyDispatch.patient_id == caller.id)
            )).scalars().all()
            assert len(count) == 1, "لازم يتسجل بلاغ طوارئ واحد بس، مش اتنين نتيجة التكرار"
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(EmergencyDispatch).where(EmergencyDispatch.patient_id == caller.id))
            await cleanup_db.commit()
        await _cleanup_users_and_finance(db, [caller.id])


# ============================================================
# 3) communications/router.py::send_notification
# ============================================================

@pytest.mark.asyncio
async def test_send_notification_first_call_executes_second_call_returns_same_notification(db):
    """قبل الإصلاح: أول استدعاء بمفتاح جديد كان بيرجّع True فورًا (صفر
    إشعار مُسجَّل). بعد الحذف الكامل لطبقة Redis الزيادة والاعتماد على
    تحقق الـservice الصحيح (عمود idempotency_key الفريد)، أول استدعاء
    لازم ينفّذ فعليًا، والتكرار لازم يرجّع نفس الإشعار بلا تكرار."""
    sender = await _create_user(db, "p_idem_notif_sender")
    recipient = await _create_user(db, "p_idem_notif_recipient")

    idem_key = f"REGTEST-IDEM-NOTIF-{_suffix()}"
    data = NotificationCreate(
        user_id=recipient.id,
        title="REGTEST idempotency notification",
        body="test body",
        idempotency_key=idem_key,
    )

    try:
        first = await send_notification(data=data, request=None, current_user=sender, db=db)
        assert not isinstance(first, bool), "الباج القديم: أول استدعاء بمفتاح جديد رجع True بدل الإشعار"
        assert first.id is not None

        second = await send_notification(data=data, request=None, current_user=sender, db=db)
        assert not isinstance(second, bool)
        assert second.id == first.id, "التكرار بنفس المفتاح لازم يرجّع نفس الإشعار بالظبط"

        async with AsyncSessionLocal() as independent_db:
            count = (await independent_db.execute(
                select(Notification).where(Notification.user_id == recipient.id)
            )).scalars().all()
            assert len(count) == 1, "لازم يتسجل إشعار واحد بس، مش اتنين نتيجة التكرار"
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(Notification).where(Notification.user_id == recipient.id))
            await cleanup_db.commit()
        await _cleanup_users_and_finance(db, [sender.id, recipient.id])


# ============================================================
# 4) communications/router.py::send_mail
# ============================================================

@pytest.mark.asyncio
async def test_send_mail_first_call_executes_second_call_returns_same_message(db):
    """نفس منهجية `send_notification` أعلاه، لـ`send_mail`."""
    sender = await _create_user(db, "p_idem_mail_sender")
    recipient = await _create_user(db, "p_idem_mail_recipient")

    idem_key = f"REGTEST-IDEM-MAIL-{_suffix()}"
    data = MailMessageCreate(
        recipient_id=recipient.id,
        subject="REGTEST idempotency mail",
        body_text="test body",
        idempotency_key=idem_key,
    )

    try:
        first = await send_mail(data=data, request=None, current_user=sender, db=db)
        assert not isinstance(first, bool), "الباج القديم: أول استدعاء بمفتاح جديد رجع True بدل الرسالة"
        assert first.id is not None

        second = await send_mail(data=data, request=None, current_user=sender, db=db)
        assert not isinstance(second, bool)
        assert second.id == first.id, "التكرار بنفس المفتاح لازم يرجّع نفس الرسالة بالظبط"

        async with AsyncSessionLocal() as independent_db:
            count = (await independent_db.execute(
                select(MailMessage).where(MailMessage.sender_id == sender.id)
            )).scalars().all()
            assert len(count) == 1, "لازم تتسجل رسالة واحدة بس، مش اتنين نتيجة التكرار"
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            message_ids = (await cleanup_db.execute(
                select(MailMessage.id).where(MailMessage.sender_id == sender.id)
            )).scalars().all()
            thread_ids = (await cleanup_db.execute(
                select(MailMessage.thread_id).where(MailMessage.sender_id == sender.id)
            )).scalars().all()
            if message_ids:
                await cleanup_db.execute(delete(MailboxItem).where(MailboxItem.message_id.in_(message_ids)))
                await cleanup_db.execute(delete(MailMessage).where(MailMessage.id.in_(message_ids)))
            if thread_ids:
                await cleanup_db.execute(delete(MailThread).where(MailThread.id.in_([t for t in thread_ids if t])))
            await cleanup_db.commit()
        await _cleanup_users_and_finance(db, [sender.id, recipient.id])
