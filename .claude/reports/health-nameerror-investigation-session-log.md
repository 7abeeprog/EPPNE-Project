# تحقيق: NameError في health/service.py (book_appointment, trigger_emergency, create_facility)

**النوع:** فحص read-only بحت — صفر تعديل كود.
**الملف المفحوص:** `eppne-backend/app/domains/health/service.py`
**التاريخ:** 2026-09-10

---

## الخلاصة السريعة

الدوال الثلاث حية 100% (مربوطة بـ endpoints فعلية في `health/router.py`،
مش كود ميت)، وكل واحدة فيها `NameError` مضمون الحدوث **في كل استدعاء بدون
استثناء** — الكود مستحيل ينفّذ الجزء الخاص بـ `audit_log` بنجاح أبدًا.

السبب: كتلة `audit_log(...)` كاملة (5 أسطر) اتنسخت حرفيًا من
`employment/service.py::create_job` (السطور 179-185 هناك) في ثلاث أماكن
مختلفة في `health/service.py`، من غير ما حد يستبدل المتغير `job` بالكائن
الفعلي اللي اتعمله (appointment / dispatch / facility)، ولا يستبدل الـ
`action="JOB_CREATED"` باسم مناسب للسياق.

---

## 1. `book_appointment` (health/service.py:203-269)

### الكود الكامل للدالة

```python
async def book_appointment(
    self,
    patient_id: int,
    tenant_id: int,
    data: Dict[str, Any],
    idempotency_key: Optional[str] = None
) -> MedicalAppointment:
    """حجز موعد طبي مع دعم Idempotency."""
    # 1. التحقق من Idempotency
    if idempotency_key:
        cached = await self._validate_idempotency(idempotency_key, MedicalAppointment)
        if cached:
            return cached

    doctor_id = data.get("doctor_id")
    facility_id = data.get("facility_id")
    appointment_time = data.get("appointment_time")

    # 2. خصم الرسوم (مع Idempotency للدفع)
    fee = Decimal("10.00")
    payment_idempotency = f"appointment_fee_{idempotency_key or uuid.uuid4().hex[:12]}"
    finance = FinanceService(self.db, tenant_id)
    try:
        await finance.transfer(
            sender_id=patient_id,
            receiver_email="health@eppne.com",
            currency="MR_USDT",
            amount=fee,
            idempotency_key=payment_idempotency,
            notes=f"رسوم حجز موعد طبي (دكتور ID: {doctor_id})"
        )
    except InsufficientBalanceError:
        raise ValidationError("الرصيد غير كافٍ لدفع رسوم الحجز")
    except Exception as e:
        raise SovereignError(f"فشل الخصم المالي: {str(e)}")

    # 3. إنشاء الموعد في معاملة ذرية
    async with self.db.begin_nested():
        appointment_data = {
            "tenant_id": tenant_id,
            "patient_user_id": patient_id,
            "doctor_id": doctor_id,
            "facility_id": facility_id,
            "department_id": data.get("department_id"),
            "appointment_time": appointment_time,
            "appointment_type": data.get("appointment_type", "CHECKUP"),
            "status": AppointmentStatus.SCHEDULED,
            "idempotency_key": idempotency_key
        }
        appointment = await self.repo.create_appointment(**appointment_data)

        # تسجيل التدقيق
        await audit_log(
        user_id=patient_id,
        tenant_id=tenant_id,  # type: ignore
        action="JOB_CREATED",
        resource_id=job.id,  # type: ignore
        details={"title": job.title}  # type: ignore
    )

    await self.db.commit()

    # تخزين Idempotency
    if idempotency_key:
        await self._store_idempotency(idempotency_key, appointment)

    return appointment
```

### المتغير غير المعرَّف

`job` — في `resource_id=job.id` و `details={"title": job.title}` (سطرين
259-260 في الملف).

- `tenant_id` هنا **معرَّف وصحيح** (باراميتر رسمي للدالة، سطر 206) — مفيش
  مشكلة فيه في هذه الدالة بالذات.
- الكائن الصحيح اللي كان لازم يتستخدم مكان `job` هو `appointment`
  (السطر 252: `appointment = await self.repo.create_appointment(**appointment_data)`)
  — القيمة الصح: `resource_id=appointment.id`, `details={"title": ...}`
  (الموعد مالوش `title`، فعلاً لازم حقل تاني بديل، زي
  `{"doctor_id": doctor_id, "facility_id": facility_id}`).

### مقارنة بالدالة الأصلية في employment (`create_job`, سطور 161-186)

```python
async def create_job(self, employer_id: int, tenant_id: int, data: Dict[str, Any]) -> JobListing:
    """إنشاء وظيفة جديدة."""
    await self._check_saas_limits(tenant_id, "hr_management")
    sanitized_data = { ... "tenant_id": tenant_id }
    job = await self.repo.create_job_listing(employer_id=employer_id, **sanitized_data)
    await self._register_affiliate_commission(employer_id, tenant_id, "JOB_CREATED", Decimal(0))
    await audit_log(
        user_id=employer_id,
        tenant_id=tenant_id,
        action="JOB_CREATED",
        resource_id=job.id,
        details={"title": job.title},
    )
    return job
```

في الأصل، المتغير `job` معرَّف فعلاً في نفس النطاق مباشرة قبل استدعاء
`audit_log` (`job = await self.repo.create_job_listing(...)`)، و`JobListing`
فعلاً عنده حقل `title`. الكوبي-بيست نقل استدعاء `audit_log` بالكامل *بدون*
تعديل اسم المتغير من `job` إلى `appointment`، ولا تعديل `action` من
`"JOB_CREATED"` لحاجة زي `"APPOINTMENT_BOOKED"`. الفرق الجوهري اللي كسر
الكود: **الاعتماد الاسمي على `job` مش موجود في `book_appointment`** —
مفيش أي تعريف لمتغير اسمه `job` في نطاق الدالة دي إطلاقًا.

ملحوظة إضافية: مستوى المسافة البادئة (indentation) لكتلة `audit_log`
نفسها غلط كمان — مش نفس مستوى باقي الكود جوه `async with self.db.begin_nested():`
(4 مسافات إضافية بدل 8)، لكن ده لا يمنع التنفيذ لأن بايثون بيقبل أي
indentation ثابت لسطر الاستدعاء نفسه طالما متسق. المشكلة الحقيقية الوحيدة
اللي بتوقف التنفيذ هي `NameError` على `job`.

---

## 2. `trigger_emergency` (health/service.py:321-365)

### الكود الكامل للدالة

```python
async def trigger_emergency(
    self,
    caller_id: int,
    tenant_id: int,
    data: Dict[str, Any],
    idempotency_key: Optional[str] = None
) -> EmergencyDispatch:
    """استدعاء الطوارئ مع دعم Idempotency."""
    if idempotency_key:
        cached = await check_idempotency(idempotency_key)
        if cached:
            # نحاول جلب الكائن من قاعدة البيانات
            if isinstance(cached, dict) and "id" in cached:
                dispatch = await self.repo.get_dispatch(cached["id"])
                if dispatch:
                    return dispatch
            return cast(EmergencyDispatch, cached)

    async with self.db.begin_nested():
        dispatch_data = {
            "tenant_id": tenant_id,
            "patient_id": data.get("patient_id") or caller_id,
            "facility_id": data.get("facility_id"),
            "emergency_type": data.get("emergency_type"),
            "gps_location": data.get("gps_location"),
            "vital_signs_on_route": data.get("vital_signs_on_route"),
            "status": DispatchStatus.PENDING,
            "idempotency_key": idempotency_key
        }
        dispatch = await self.repo.create_dispatch(**dispatch_data)

        await audit_log(
        user_id=caller_id,
        tenant_id=tenant_id,  # type: ignore
        action="JOB_CREATED",
        resource_id=job.id,  # type: ignore
        details={"title": job.title}  # type: ignore
    )

    await self.db.commit()

    if idempotency_key:
        await self._store_idempotency(idempotency_key, dispatch)

    return dispatch
```

### المتغير غير المعرَّف

نفس الحالة بالضبط: `job` غير معرَّف (سطرين 356-357).

- `tenant_id` معرَّف وصحيح هنا كمان (باراميتر رسمي، سطر 324).
- الكائن الصحيح البديل: `dispatch` (سطر 350:
  `dispatch = await self.repo.create_dispatch(**dispatch_data)`).
  `EmergencyDispatch` مالوش حقل `title` منطقيًا — البديل المنطقي زي
  `{"emergency_type": ..., "facility_id": ...}`.
- `action="JOB_CREATED"` غلط دلاليًا هنا كمان — المفروض حاجة زي
  `"EMERGENCY_DISPATCHED"`.

### المقارنة بـ employment

نفس التحليل تمامًا كـ `book_appointment` أعلاه — نفس كتلة الكود
الخماسية اتنسخت حرفيًا للمرة التانية، بنفس الغلطة (`job` مش موجود في
نطاق الدالة).

---

## 3. `create_facility` (health/service.py:380-392)

### الكود الكامل للدالة

```python
async def create_facility(self, user_id: int, data: Dict[str, Any]) -> HealthFacility:
    """إنشاء منشأة صحية جديدة (للمشرفين فقط)."""
    async with self.db.begin_nested():
        facility = await self.repo.create_facility(**data)
        await audit_log(
        user_id=user_id,
        tenant_id=tenant_id,  # type: ignore
        action="JOB_CREATED",
        resource_id=job.id,  # type: ignore
        details={"title": job.title}  # type: ignore
    )
    await self.db.commit()
    return facility
```

### المتغيرات غير المعرَّفة (اتنين مش واحد هنا)

1. **`tenant_id`** — الدالة دي أصلاً **مالهاش باراميتر `tenant_id` في
   توقيعها** (`create_facility(self, user_id: int, data: Dict[str, Any])`).
   الـ `tenant_id` بييجي فقط جوه الـ `data` dict (الراوتر بيحطه:
   `facility_data["tenant_id"] = tenant.id` في `router.py:221`)، وبيتوصّل
   للـ repository عن طريق `**data`. لكن السطر `tenant_id=tenant_id,` جوه
   `audit_log` بيحاول يقرأ اسم متغير مستقل اسمه `tenant_id` مش موجود في
   نطاق الدالة إطلاقًا — لا كباراميتر ولا كمتغير محلي. القيمة الصح كانت
   لازم تكون `tenant_id=data.get("tenant_id")` أو `facility.tenant_id`
   (بعد الإنشاء).
2. **`job`** — نفس مشكلة الدالتين اللي فوق: البديل الصحيح هو `facility`
   (سطر 383: `facility = await self.repo.create_facility(**data)`).
   تم التأكد من نموذج `HealthFacility` (`health/models.py:71-86`):
   الحقل الفعلي اسمه `name` مش `title` — يعني حتى لو استبدلنا `job`
   بـ `facility`، سطر `details={"title": job.title}` كان لازم كمان يتغير
   لـ `details={"title": facility.name}` أو مفتاح مختلف، وإلا كان
   هيطلع `AttributeError` بدل `NameError`.

### ترتيب حدوث الخطأ الفعلي

بايثون بيقيّم keyword arguments بترتيب كتابتها في الاستدعاء. في
`create_facility`، الترتيب هو: `user_id=user_id` (سليم) ثم
`tenant_id=tenant_id` — **ده أول `NameError` بيتطلع فعليًا** (`tenant_id`
غير معرَّف)، قبل ما بايثون يوصل أصلاً لسطر `resource_id=job.id`. يعني في
`create_facility` تحديدًا، أول استثناء هيكون `NameError: name 'tenant_id'
is not defined`، مش `job` زي الدالتين التانيين.

### المقارنة بـ employment

نفس كتلة الكود الخماسية اتنسخت للمرة التالتة، لكن هنا الكسر أعمق لأن
دالة `create_facility` (المستهدفة) حتى مافيهاش `tenant_id` كمدخل أصلاً —
عكس `create_job` الأصلية اللي `tenant_id` فيها باراميتر رسمي معرَّف من
الأول.

---

## 4. هل الدوال دي مُستدعاة فعليًا، ولا كود ميت؟

**الثلاثة أحياء 100% ومربوطين بـ endpoints حقيقية** — مش زي حالات تانية
شُخّصت قبل كده كـ"كود ميت" في المشروع. تأكيد بالـ grep:

| الدالة | Endpoint في router.py | الحماية (dependencies) |
|---|---|---|
| `book_appointment` | `POST /appointments` (router.py:100-117) | `get_current_active_user` + `get_current_tenant` |
| `trigger_emergency` | `POST /emergency` (router.py:170-187) | `get_current_active_user` + `get_current_tenant` |
| `create_facility` | `POST /facilities` (router.py:211-226) | `get_current_superuser` + `get_current_tenant` |

- لا يوجد أي استدعاء تاني للدوال التلاتة دي في المشروع كله غير من
  `router.py` (تم التأكد بـ grep شامل على `eppne-backend/`) — يعني
  المسار الوحيد للتنفيذ هو عبر الـ HTTP endpoints دي.
- **لا يوجد أي اختبار (`pytest`) يغطي أي واحدة من الثلاثة** — تم التأكد
  بـ grep على `eppne-backend/tests/` رجّع صفر نتائج لأي من
  `HealthService(`, `book_appointment`, `trigger_emergency`,
  `create_facility`. يعني الباج ده ما كانش هيتلقط بأي test suite موجود
  حاليًا.
- استخدام إضافي غير مباشر: `process_voice_command` (سطر 437-467) بيرجّع
  `action: "book_appointment"` و `action: "trigger_emergency"` كـ payload
  نصي لواجهة صوتية خارجية (مفيش استدعاء مباشر للدوال من هنا، مجرد نص).

### تأثير الـ NameError على حالة قاعدة البيانات

الثلاثة NameError بيحصلوا **جوه** `async with self.db.begin_nested():`
(بعد عملية الإنشاء `INSERT` وقبل `commit()` الخارجي). لما الاستثناء
يتطلع جوه الـ `async with`، الـ savepoint (`begin_nested`) بيعمل rollback
تلقائي لنفسه، فالسجل (`appointment` / `dispatch` / `facility`) **ما
بيتسجّلش فعليًا في قاعدة البيانات** رغم إن `self.repo.create_...` اتنفذ.
النتيجة: الـ endpoint الثلاثة بيرجّعوا 500 (NameError غير معالج) في **كل
استدعاء بدون استثناء واحد** — مفيش أي مسار نجاح ممكن حاليًا لأي من
الثلاثة:
- `POST /appointments` (حجز موعد طبي) — معطل بالكامل.
- `POST /emergency` (استدعاء طوارئ) — معطل بالكامل، وده الأخطر لأنه
  endpoint طوارئ طبية حرجة.
- `POST /facilities` (إنشاء منشأة صحية) — معطل بالكامل.

ملحوظة جانبية: في `book_appointment`، الخصم المالي عبر
`finance.transfer(...)` (سطر 226) بيحصل **قبل** كتلة `begin_nested()`
وبيتعمله commit مستقل (منطقيًا جوه `FinanceService.transfer`)، يعني
المستخدم ممكن يتخصم منه رسوم الحجز (10 MR_USDT) وبعدين الموعد نفسه
يفشل يتسجل بسبب الـ NameError اللي بعده — ده يحتاج فحص/إصلاح منفصل زي
تضارب مالي (رسوم مخصومة بدون خدمة)، لكنه خارج نطاق هذا التقرير
(read-only، بيوثّق بس).

---

## ملخص الفروق بين الحالات الثلاثة

| | `book_appointment` | `trigger_emergency` | `create_facility` |
|---|---|---|---|
| أول NameError فعليًا | `job` | `job` | `tenant_id` (قبل ما يوصل لـ `job`) |
| `tenant_id` معرَّف في نطاق الدالة؟ | ✅ نعم (باراميتر) | ✅ نعم (باراميتر) | ❌ لا — مفيش أصلاً |
| الكائن الصحيح بديل `job` | `appointment` | `dispatch` | `facility` |
| الكائن له حقل `title`؟ | ❌ لا | ❌ لا | ❌ لا — الحقل الفعلي `name` (`models.py:77`) |
| `action` الصحيح منطقيًا | `APPOINTMENT_BOOKED` أو مشابه | `EMERGENCY_DISPATCHED` أو مشابه | `FACILITY_CREATED` أو مشابه |
| مربوط بـ endpoint حي؟ | ✅ `POST /appointments` | ✅ `POST /emergency` | ✅ `POST /facilities` |
| مغطى بأي test؟ | ❌ لا | ❌ لا | ❌ لا |

---

**الخلاصة العامة:** مصدر الباج واحد ومتكرر — كتلة `audit_log` بتاعة
`employment/service.py::create_job` اتنسخت-لصقت 3 مرات في
`health/service.py` من غير تكييف اسم المتغير (`job` → الكائن الفعلي)
ولا الـ `action` string، وفي حالة `create_facility` كمان من غير تكييف
إن `tenant_id` مش موجود كباراميتر في الدالة المستهدفة أصلاً. الثلاثة
حية 100%، مربوطة بـ endpoints حقيقية بدون أي تغطية اختبارات، وبتفشل في
كل استدعاء بلا استثناء.

**لم يتم تعديل أي كود في هذا التحقيق (read-only بالكامل).**
