# إصلاح أمني عاجل: غياب فلتر `tenant_id` في `HealthService.get_my_appointments`

**تاريخ:** 2026-09-16
**النطاق:** إصلاح عاجل ومعزول — `HealthService.get_my_appointments` +
`HealthRepository` المعادلة **بس**. اكتُشف كملاحظة جانبية أثناء جلسة
[[project_guardian_overview_endpoint_planning]] (فحص read-only)،
وطُلب إصلاحه فورًا كبند منفصل قبل أي متابعة على guardian.
**صفر لمس على أي كود أو ملف guardian في هذه الجلسة — تم التحقق
بالمطابقة المباشرة قبل وبعد.**

---

## 1. الدالة كاملة قبل الإصلاح — تأكيد دقيق لغياب `tenant_id`

### `HealthRepository.list_appointments` (`health/repository.py:96-102`، قبل التعديل)

```python
async def list_appointments(self, user_id: int, status: Optional[str] = None):
    query = select(MedicalAppointment).where(MedicalAppointment.patient_user_id == user_id)
    if status:
        query = query.where(MedicalAppointment.status == status)
    query = query.order_by(MedicalAppointment.appointment_time)
    result = await self.db.execute(query)
    return result.scalars().all()
```

**التوقيع بالكامل: `(self, user_id: int, status: Optional[str] = None)`
— لا يوجد باراميتر `tenant_id` على الإطلاق، لا في التوقيع ولا في جسم
الاستعلام.** الفلترة الوحيدة: `MedicalAppointment.patient_user_id ==
user_id`.

### `HealthService.get_my_appointments` (`health/service.py:292-294`، قبل التعديل)

```python
async def get_my_appointments(self, user_id: int, status_filter: Optional[str] = None) -> List[MedicalAppointment]:
    """جلب مواعيد المستخدم."""
    return list(await self.repo.list_appointments(user_id, status_filter))
```

نفس الغياب بالضبط — بتمرر `user_id`/`status_filter` بس. **وحتى
`HealthService` نفسها** (`health/service.py:43-44`) بتتبنى
`def __init__(self, db: AsyncSession)` **بلا `tenant_id` أصلًا** —
بعكس كل الدومينات التانية (`AcademyService(db, tenant_id)`,
`AchievementService(db, tenant_id)`, إلخ) اللي بتاخد `tenant_id` وقت
الإنشاء وتستخدمه ضمنيًا في كل استعلام.

### أين تُستخدم فعليًا؟

`GET /health/appointments` (`health/router.py:120-132`، قبل التعديل):

```python
service = HealthService(db)
appointments = await service.get_my_appointments(
    user_id=cast(int, current_user.id),
    status_filter=status_filter
)
```

اليوم، بما إن `user_id` دايمًا `current_user.id` (المستخدم بيشوف
مواعيده هو بس)، الفجوة **مش مستغَلة فعليًا في هذا المسار الوحيد
الحالي** — لكن الدالة نفسها **مفتوحة بالكامل لأي استغلال مستقبلي**:
أي كود جديد (زي endpoint موحَّد يستدعي بيانات مستخدم مختلف عبر
تينانتات، أو أي منطق cross-user) هيقدر يمرر `user_id` لمستخدم في
تينانت مختلف تمامًا ويرجعله مواعيده الطبية الحقيقية بلا أي حاجز — **لا
يوجد أي دفاع ثانٍ (defense-in-depth) في هذه الدالة نفسها**، بعكس كل
الدوال المكافئة في الدومينات التانية (`AcademyRepository.get_user_enrollments(user_id,
tenant_id, ...)` مثلًا بتفحص الاتنين معًا دايمًا).

**تأكيد إضافي:** دالة تانية غير مرتبطة، `get_health_carbon_footprint`
(`health/service.py:443-455`)، كانت بتستدعي نفس `repo.list_appointments(user_id)`
القديمة بنفس الفجوة — **لكنها dead code فعليًا** (تم التأكد بـgrep
شامل: صفر مستدعٍ لها من أي router أو أي مكان تاني في المشروع كله؛
الظهور الوحيد لاسمها في مكان تاني هو `"action":
"get_health_carbon_footprint"` كنص وصفي جامد داخل dict في
`process_voice_command` — مش استدعاء حقيقي).

---

## 2. الإصلاح — إضافة فلتر `tenant_id` إجباري (3 ملفات)

### `health/repository.py`

```python
from sqlalchemy import select, update, func, and_  # ← and_ جديد

async def list_appointments(self, user_id: int, tenant_id: int, status: Optional[str] = None):
    # ⚠️ إصلاح أمني عاجل (2026-09-16): tenant_id كان غائبًا تمامًا هنا قبل كده
    query = select(MedicalAppointment).where(
        and_(
            MedicalAppointment.patient_user_id == user_id,
            MedicalAppointment.tenant_id == tenant_id,
        )
    )
    if status:
        query = query.where(MedicalAppointment.status == status)
    query = query.order_by(MedicalAppointment.appointment_time)
    result = await self.db.execute(query)
    return result.scalars().all()
```

### `health/service.py` — موضعان

```python
async def get_my_appointments(self, user_id: int, tenant_id: int, status_filter: Optional[str] = None) -> List[MedicalAppointment]:
    """جلب مواعيد المستخدم — tenant_id إجباري لمنع تسريب عبر التينانتات."""
    return list(await self.repo.list_appointments(user_id, tenant_id, status_filter))
```

```python
async def get_health_carbon_footprint(self, user_id: int, tenant_id: int) -> Dict:
    """حساب البصمة الكربونية للخدمات الصحية المستخدمة من قبل المستخدم."""
    profile = await self.get_or_create_profile(user_id)
    appointments = await self.repo.list_appointments(user_id, tenant_id)
    ...
```

هذا التعديل الثاني **إجباري ميكانيكيًا** — لو مُتجاهَل، كان
`list_appointments(user_id)` (بمعامل واحد بس) هيرمي `TypeError` فورًا
لو `get_health_carbon_footprint` اتنادت يومًا ما (وهي حاليًا مش
متصلة بأي endpoint، فمفيش أي كود شغال اتأثر عمليًا، لكن ترك الدالة
مكسورة بلا داعٍ كان قرارًا سيئًا). **صفر تغيير في المنطق الفعلي لهذه
الدالة غير تمرير `tenant_id`** — لا استدعاء فعلي لها من أي مكان
(تأكَّد بـgrep قبل وبعد).

### `health/router.py`

```python
service = HealthService(db)
appointments = await service.get_my_appointments(
    user_id=cast(int, current_user.id),
    tenant_id=cast(int, current_user.tenant_id),  # ← جديد، من التوكن المُوثَّق
    status_filter=status_filter
)
```

`tenant_id` مصدره `current_user.tenant_id` (من الـJWT المُوثَّق عبر
`get_current_active_user`) — **مش من أي هيدر عميل** (بعكس
`get_current_tenant`/`X-Tenant-ID` المُستخدَمة في `book_appointment`
بنفس الملف، وهي نمط أضعف موجود بالفعل من قبل، غير مُلمَّس هنا، خارج
نطاق هذا الإصلاح المحدَّد بدقة).

---

## 3. الاختبار الحي

`tests/test_health_appointments_tenant_isolation_fix.py` — سيناريو
واحد شامل، عبر `HealthService`/`HealthRepository` مباشرة، فوق DB
حقيقية:

1. إنشاء مستخدم "مريض" ومستخدم "دكتور" في `tenant_id=1`.
2. إنشاء `HealthFacility` حقيقية في `tenant_id=1` (تفاديًا لاستخدام
   `book_appointment` الكامل، اللي بيتضمن خصم رسوم حقيقي من محفظة
   المستخدم — تعقيد غير مرتبط بما نختبره هنا، وهو **فلترة القراءة**
   بس).
3. إنشاء `MedicalAppointment` حقيقي، `tenant_id=1`، `patient_user_id`
   = المريض.
4. `commit()` صريح (نفس درس الـFK lock من جلسات guardian السابقة —
   INSERT في `medical_appointments` بياخد قفل `FOR KEY SHARE` على
   صفوف `users`/`health_facilities` المُشار إليها).
5. **`get_my_appointments(user_id=patient_id, tenant_id=16)`** →
   `assert result == []` — **قائمة فارغة فعليًا، صفر تسريب**. **PASSED**.
6. **`get_my_appointments(user_id=patient_id, tenant_id=1)`** →
   `assert len(result) == 1` والموعد المُرجَع هو نفسه بالضبط
   (`id`, `patient_user_id`, `tenant_id` مطابقين). **PASSED**.

**النتيجة: 1/1 نجح.** صفر بقايا بيانات بعد التنظيف (اتأكَّد مباشرة على
DB: `medical_appointments`, `health_facilities`, `users` كلهم
`count=0` لبيانات هذا الاختبار).

---

## 4. Regression

- **كل اختبارات health الحالية** (`test_health_entity_membership_full_implementation.py`
  + `test_health_nameerror_and_fee_ordering_fix.py`، 7 اختبارات —
  بما فيها `test_book_appointment_endpoint_success_charges_fee_exactly_once`
  اللي بيمر فعليًا عبر `book_appointment` الكامل مع خصم الرسوم):
  **7/7 نجحوا** — صفر تأثير على أي مسار حالي.
- **`pytest --collect-only`** على كامل `tests/` (233 اختبار، +1 من
  هذه الجلسة): صفر خطأ استيراد جديد؛ نفس الخطأ المسبق الوحيد
  (`ActionCommission` من `affiliate.models`، موثَّق من
  [[project_tourism_sports_entity_membership_implementation_closed]]،
  غير مرتبط بهذا الإصلاح إطلاقًا).

---

## 5. تأكيد العزل عن guardian

تم التحقق صراحةً: **الملفات المعدَّلة في هذه الجلسة هي فقط**:
- `eppne-backend/app/domains/health/repository.py`
- `eppne-backend/app/domains/health/service.py`
- `eppne-backend/app/domains/health/router.py`
- `eppne-backend/tests/test_health_appointments_tenant_isolation_fix.py` (جديد)

**صفر تعديل على `app/domains/guardian/` أو أي ملف يخصه في هذه
الجلسة.**

---

## الحالة النهائية

- **الثغرة مُصلَحة ومتحقَّق منها حيًا** — `tenant_id` بقى فلتر إجباري
  في `list_appointments`/`get_my_appointments`، مأخوذ من التوكن
  المُوثَّق دايمًا.
- **صفر regression** على أي مسار health حالي (7/7) أو على باقي
  المشروع (233 اختبار، صفر خطأ استيراد جديد).
- **صفر لمس على guardian** — مؤكَّد بالمطابقة المباشرة.
- **لم يُعمَل commit على git بعد** — بانتظار طلب المستخدم.
- **PROGRESS_LOG.md** اتحدَّث ببند أمني عاجل منفصل تمامًا عن كل بنود
  guardian.
