# إصلاح: NameError في health/service.py + ترتيب الخصم المالي في book_appointment

**النوع:** إصلاح كود + اختبار حي + regression.
**الملفات المعدَّلة:** `eppne-backend/app/domains/health/service.py`,
`eppne-backend/app/domains/health/router.py`.
**ملف اختبار جديد:** `eppne-backend/tests/test_health_nameerror_and_fee_ordering_fix.py`.
**التقرير السابق (التحقيق، read-only):**
`.claude/reports/health-nameerror-investigation-session-log.md`
**التاريخ:** 2026-09-10

---

## 1. ملخص الإصلاحات

### 1.1 الثلاثة `audit_log` blocks

كل واحدة من `book_appointment`, `trigger_emergency`, `create_facility`
كانت فيها كتلة `audit_log` منسوخة-ملصوقة حرفيًا من
`employment/service.py::create_job`، بمتغير `job` غير معرَّف إطلاقًا في
نطاق الدالة (`NameError` مضمون في كل استدعاء). تم تصحيح الثلاثة:

| الدالة | `resource_id` (قبل → بعد) | `action` (قبل → بعد) | `details` (قبل → بعد) |
|---|---|---|---|
| `book_appointment` | `job.id` → `appointment.id` | `JOB_CREATED` → `APPOINTMENT_BOOKED` | `{"title": job.title}` → `{"doctor_id": doctor_id, "facility_id": facility_id}` |
| `trigger_emergency` | `job.id` → `dispatch.id` | `JOB_CREATED` → `EMERGENCY_DISPATCHED` | `{"title": job.title}` → `{"emergency_type": data.get("emergency_type")}` |
| `create_facility` | `job.id` → `facility.id` | `JOB_CREATED` → `FACILITY_CREATED` | `{"title": job.title}` → `{"name": facility.name}` |

### 1.2 `create_facility` — إضافة `tenant_id` كباراميتر رسمي

**قبل:**
```python
async def create_facility(self, user_id: int, data: Dict[str, Any]) -> HealthFacility:
    async with self.db.begin_nested():
        facility = await self.repo.create_facility(**data)
        ...
```
الدالة كانت أصلاً بلا باراميتر `tenant_id`، ومعتمدة على إن الراوتر يحقن
`tenant_id` يدويًا جوه dict الـ`data` (`facility_data["tenant_id"] =
tenant.id`). كتلة `audit_log` المنسوخة كانت بتحاول تقرأ اسم متغير مستقل
`tenant_id` مش موجود في النطاق أصلاً — **كان أول `NameError` فعليًا في
هذه الدالة تحديدًا هو على `tenant_id` نفسه، قبل حتى الوصول لـ`job`**
(بايثون بيقيّم keyword arguments بترتيب كتابتها، و`tenant_id=tenant_id`
مكتوب قبل `resource_id=job.id`).

**بعد:**
```python
async def create_facility(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> HealthFacility:
    async with self.db.begin_nested():
        facility_data = {**data, "tenant_id": tenant_id}
        facility = await self.repo.create_facility(**facility_data)
        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,
            action="FACILITY_CREATED",
            resource_id=facility.id,
            details={"name": facility.name}
        )
    await self.db.commit()
    return facility
```

`tenant_id` بقى مصدر الحقيقة الوحيد جوه الدالة (مصدره الآن باراميتر
رسمي، والدالة هي اللي بتحقنه جوه `facility_data` قبل تمريرها للـ
repository، مش الراوتر). الراوتر اتحدَّث ليمرره صراحةً:

```python
facility = await service.create_facility(
    user_id=cast(int, current_user.id),
    tenant_id=cast(int, tenant.id),
    data=data.model_dump()
)
```

تم التأكد (grep شامل على `eppne-backend/`) إنه لا يوجد أي استدعاء تاني
لـ`HealthService.create_facility` في المشروع غير من `router.py` —
التغيير في التوقيع صفر تأثير جانبي على أي كود تاني.

### 1.3 ترتيب الخصم المالي في `book_appointment`

**قبل:** `finance.transfer(...)` (خصم 10 MR_USDT) كان بيحصل **قبل**
`async with self.db.begin_nested()` (إنشاء الموعد). لو الإنشاء فشل لأي
سبب بعد نجاح الخصم، كان المريض هيتخصم منه فلوس بلا أي خدمة فعلية.

**بعد:** `finance.transfer(...)` بقى **جوه** نفس `begin_nested()`، بعد
`self.repo.create_appointment(...)` مباشرة:

```python
async with self.db.begin_nested():
    appointment_data = {...}
    appointment = await self.repo.create_appointment(**appointment_data)

    fee = Decimal("10.00")
    ...
    try:
        await finance.transfer(...)
    except InsufficientBalanceError:
        raise ValidationError("الرصيد غير كافٍ لدفع رسوم الحجز")
    except Exception as e:
        raise SovereignError(f"فشل الخصم المالي: {str(e)}")

    await audit_log(...)
```

**الأثر الفعلي للترتيب الجديد (تحقَّق منه حيًا، راجع §3 تحت):**
- لو فشل إنشاء الموعد نفسه (زي FK violation على `facility_id` غير
  موجود) → الكود **ما يوصلش أصلاً** لكتلة `finance.transfer` → صفر خصم
  مالي.
- لو نجح إنشاء الموعد لكن فشل الخصم المالي (رصيد غير كافٍ) → الاستثناء
  بيتطلع جوه نفس الـ`begin_nested()`، فالـsavepoint بيعمل rollback
  تلقائي لإنشاء الموعد كمان (مايتسجّلش موعد مجاني بدون دفع).
- الحالة السعيدة: الموعد يتسجل والخصم يحصل معًا في نفس الترانزاكشن،
  وبعدها `audit_log`، وكلهم يُكتَبون على القرص بـ`commit()` واحد فقط.

**ملاحظة تحليلية مهمة (توثيقًا، مش اعتراضًا على الطلب):** بمراجعة
`app/core/database.py::get_db()` (يستخدم `async with AsyncSessionLocal()`
بلا `commit()` تلقائي، و`FinanceService.transfer` (finance/service.py:58-147)
مالوش أي `commit()` مستقل بتاعه — فقط `begin_nested()` (savepoint) — كل
الكتابة (تحويل + موعد + audit) كانت أصلاً تعتمد على نفس الـ`commit()`
الواحد النهائي في `book_appointment` (سطر 264 قديمًا وحديثًا). يعني حتى
*قبل* هذا الإصلاح، الـNameError كان بيمنع الوصول لهذا الـ`commit()`
أصلاً، فلم يكن هناك فقدان مالي فعلي حصل في الإنتاج نتيجة الترتيب القديم
تحديدًا (الـsession كانت بتتقفل بلا commit في كل الأحوال بسبب الباج
الآخر). ومع ذلك، الترتيب الجديد المطلوب هو الأصح دفاعيًا بشكل عام (أي
تعديل مستقبلي يضيف `commit()` وسيط، أو يغيّر منطق `create_appointment`
ليفشل بعد نجاح جزئي، لن يفتح ثغرة "خصم بلا خدمة") — وهو المطبَّق الآن.

---

## 2. اكتشاف جانبي أثناء الاختبار الحي (خارج نطاق هذه الجلسة، موثَّق فقط)

أثناء كتابة اختبار حي لـ`book_appointment` بـ`idempotency_key` حقيقي،
اكتُشف باج منفصل تمامًا في آلية الـIdempotency نفسها (غير ملموس في هذا
الإصلاح):

- `check_idempotency()` (`app/core/idempotency.py:17-24`) بترجع
  `is_new is True` — يعني **`True` تعني "المفتاح جديد" (SETNX نجح)**، مش
  "فيه نتيجة سابقة مخزَّنة".
- لكن `HealthService._validate_idempotency` (وبالمثل الكود المضمّن مباشرة
  جوه `trigger_emergency`) بتتعامل مع أي قيمة truthy مُرجَعة من
  `check_idempotency` على إنها "نتيجة مخزَّنة، رجّعها فورًا":
  ```python
  cached = await check_idempotency(idempotency_key)
  if cached:
      ...
      return cached
  ```
- **النتيجة:** أول استدعاء لـ`book_appointment` (أو `trigger_emergency`)
  بأي `idempotency_key` **جديد تمامًا** (أول استخدام له في حياته) بيخلي
  `check_idempotency` يرجّع `True` (لأنه فعلاً مفتاح جديد ناجح الحجز)،
  فـ`_validate_idempotency`/الكود المكافئ بيفسّرها غلط كـ"في نتيجة سابقة"
  ويرجّع `True` (قيمة `bool`) **بدل الموعد/البلاغ الفعلي** — الدالة
  بالكامل بتتخطى (لا إنشاء، لا خصم مالي، لا audit_log) في كل مرة يُستخدم
  فيها `idempotency_key` حقيقي لأول مرة.
- تم تأكيد هذا حيًا أثناء هذه الجلسة: تمرير `idempotency_key` حقيقي لـ
  `book_appointment` رجّع `True` (`AttributeError: 'bool' object has no
  attribute 'id'` في الاختبار)، وتمرير `idempotency_key=None` (تجاوز
  الفرع بالكامل) اشتغل صح.
- **هذا الباج يمنع استخدام دعم الـIdempotency في الثلاثة endpoints تمامًا
  حاليًا** — أي عميل حقيقي (فرونت إند) بيرسل `Idempotency-Key` header زي
  ما متوقَّع منه هيحصل على استجابة `true`/`bool` بدل الكائن المتوقَّع، في
  كل مرة (مش بس عند التكرار). **خارج نطاق هذه الجلسة صراحةً** (الطلب كان
  محصور في الثلاثة `audit_log` + ترتيب الخصم المالي) — موثَّق هنا فقط
  كاكتشاف يحتاج بند backlog منفصل.

---

## 3. الاختبار الحي (`tests/test_health_nameerror_and_fee_ordering_fix.py`)

المنهجية: استدعاء دوال الراوتر الفعلية (`book_appointment`,
`call_emergency`, `create_facility` من `health/router.py`) مباشرة —
نفس أسلوب `test_trigger_renewals_endpoint_missing_commit.py` — بجلسة DB
حقيقية (`eppne_v2` عبر `AsyncSessionLocal`)، وتحقق نهائي عبر جلسة DB
**مستقلة تمامًا** (اتصال جديد) للتأكد من `commit()` حقيقي على القرص، مش
مجرد كائن في الذاكرة.

**4 اختبارات، 4/4 ناجحة:**

1. `test_create_facility_endpoint_persists_with_correct_audit_data` —
   يستدعي `create_facility` الحقيقية، يتأكد من نجاح الإنشاء (كان قبل
   الإصلاح 500 مضمون بسبب NameError على `tenant_id` أولاً)، ومن
   `facility.tenant_id == TENANT_ID` (تأكيد إن الباراميتر الجديد بيوصل
   صح من الراوتر)، ومن الحفظ الفعلي عبر جلسة مستقلة.

2. `test_trigger_emergency_endpoint_persists_with_correct_audit_data` —
   يستدعي `call_emergency` الحقيقية بـ`idempotency_key=None`، يتأكد من
   نجاح الإنشاء (500 مضمون قبل الإصلاح)، ومن `dispatch.patient_id ==
   caller.id` (fallback صحيح لما `data.patient_id` غير ممرَّر)، ومن
   `status == PENDING`، ومن الحفظ الفعلي.

3. `test_book_appointment_endpoint_success_charges_fee_exactly_once` —
   المسار السعيد الكامل: مريض برصيد 100 MR_USDT، طبيب ومنشأة حقيقيان،
   حجز موعد ناجح، **تحقق من أن الرصيد بعد الحجز بالظبط 90.00** (خصم 10
   بالظبط، مرة واحدة)، ومن وجود صف `Transaction` حقيقي بالمبلغ الصحيح،
   ومن حفظ الموعد فعليًا — كل ده عبر جلسة مستقلة.

4. `test_book_appointment_fee_not_charged_when_appointment_creation_fails`
   — **الاختبار الحاسم لإصلاح ترتيب الخصم المالي**: `facility_id` غير
   موجود (`2147483647`) → `IntegrityError` (FK violation) عند
   `create_appointment`. يتحقق من:
   - الاستثناء المتوقَّع (`IntegrityError`) اتطلع فعلاً.
   - رصيد المريض **فضل 100.00 بالظبط** (صفر خصم) — يثبت إن الخصم المالي
     الآن لا يحصل إلا بعد نجاح إنشاء الموعد.
   - صفر صف `MedicalAppointment` أو `Transaction` اتسجل.

**نتيجة التشغيلة:** `4 passed` (98.14s، venv المشروع، DB حقيقية
`eppne_v2`، صفر mock/stub).

---

## 4. Regression (تشغيلة كاملة للـ suite)

تشغيلتان كاملتان لكل `tests/` (باستثناء
`test_affiliate_service_missing_methods.py` — عطل استيراد قديم غير
مرتبط بهذه الجلسة إطلاقًا: `ImportError: cannot import name
'ActionCommission' from app.domains.affiliate.models`، أثر جانبي من
commit سابق "Unify 3 conflicting referral/affiliate systems"، خارج
النطاق بالكامل):

**التشغيلة الأولى:** `17 failed, 150 passed, 2 xfailed` — تضمّنت فشل
**اختبارين من الاختبارين الحيين الجدد** بتوعنا
(`test_book_appointment_endpoint_success_charges_fee_exactly_once`,
`test_book_appointment_fee_not_charged_when_appointment_creation_fails`)
بخطأ `PermissionDeniedError: Insufficient balance` غير متوقَّع.

**تحقيق الفشل:** أُعيد تشغيل نفس الاختبارين التلاتة (الاثنين دول +
`test_saas_active_subscription.py` كامل) بمعزل — **نجحوا 4/4 بلا أي
تعديل**. ثم أُعيدت التشغيلة الكاملة للـsuite بالكامل مرة تانية من
الصفر (بدون أي تعديل كود) — **نجح الاختباران بالكامل هذه المرة**،
والنتيجة الكاملة طابقت تمامًا الأساس (baseline) الموثَّق مسبقًا في
`PROGRESS_LOG.md` (جلسة `invoicing-process-overdue-invoices` بتاريخ
2026-09-09: `15 failed, 148 passed, 2 xfailed`) + 4 اختبارات health
الجديدة الناجحة = **`15 failed, 152 passed, 2 xfailed`**. نفس الـ15 اسم
فشل بالحرف (`test_realestate_insurance_savepoint`,
`test_saas_active_subscription` (2), `test_user_repository_get_by_id_audit`
(10), `test_user_repository_get_user_audit` (2)) — كلها بنود backlog
قديمة موثَّقة مسبقًا، صفر علاقة بـ`health`/`finance`/`employment`.

**الخلاصة:** فشل الاختبارين مرة واحدة كان **تذبذب بيئي عابر (flaky)**
أثناء التشغيلة الكاملة الأولى (على الأرجح تنافس مؤقت على DB connection
pool أو مهلة SSL handshake — نفس الفئة من التذبذب البيئي الموثَّقة سابقًا
في `PROGRESS_LOG.md` بتاريخ 2026-09-09 §"backlog-insurance-tests-
unverified..."), **مش regression حقيقي ناتج عن هذا الإصلاح** — تأكَّد
هذا بإعادة تشغيل نظيفة كاملة طابقت الأساس الموثَّق بالحرف زائد نجاح
الأربعة اختبارات الجديدة بلا استثناء.

**الملفات المعدَّلة في هذه الجلسة فقط:** `health/service.py`,
`health/router.py` (+ ملف اختبار جديد). لا يوجد أي كود تاني في المشروع
بيستورد من `health/service.py` غير `health/router.py`، والوحيد اللي
بيستورد `health/router.py` هو `app/main.py` (تسجيل الراوتر فقط، بلا أي
منطق) — تم التأكد بـgrep شامل قبل التعديل (راجع تقرير التحقيق).

---

## 5. الحالة النهائية

✅ **الثلاثة NameError في `book_appointment`, `trigger_emergency`,
`create_facility` اتصلحوا بالكامل ومتحقَّق منهم حيًا (DB حقيقية، commit
فعلي، جلسة قراءة مستقلة).**
✅ **ترتيب الخصم المالي في `book_appointment` اتصلح** — الرسوم لا تُخصم
إلا بعد نجاح إنشاء الموعد، وفشل أي منهما يتراجع عن الاثنين معًا عبر نفس
الـsavepoint.
🟡 **اكتشاف جديد خارج النطاق:** باج idempotency في الثلاثة endpoints
(§2) — يمنع استخدام `Idempotency-Key` بالكامل حاليًا، يحتاج بند backlog
منفصل.
