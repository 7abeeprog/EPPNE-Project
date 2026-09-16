# POST /guardian/wards/{ward_id}/message-instructor — جلسة تنفيذ

**تاريخ:** 2026-09-16
**النطاق:** بناء `service.py`/`router.py` كاملين لميزة "رسالة لمدرّس"،
بناءً على [[project_guardian_message_instructor_planning]] بالحرف. فوق
[[project_guardian_overview_endpoint_implementation]].

---

## 1. الملفات الجديدة/المعدَّلة

| الملف | التغيير |
|---|---|
| `app/domains/guardian/repository.py` | +`get_instructor_user_id(instructor_id)` — استعلام معزول جديد |
| `app/domains/guardian/service.py` | +`message_instructor()` |
| `app/domains/guardian/schemas.py` | +`GuardianMessageInstructorRequest` |
| `app/domains/guardian/router.py` | +`POST /guardian/wards/{ward_id}/message-instructor` |
| `tests/test_guardian_message_instructor_implementation.py` | **جديد** — 4 سيناريوهات حية |

**صفر تعديل على `academy/`, `communications/`, أو أي دومين تاني غير
`guardian/`** — مؤكَّد بمطابقة قائمة الملفات المعدَّلة.

---

## 2. `GuardianService.message_instructor` — المنطق الكامل

```python
async def message_instructor(self, guardian_user_id, ward_user_id, course_id, message_text) -> Notification:
    relationship = await self.repo.get_relationship_by_guardian_and_ward(guardian_user_id, ward_user_id)
    if (not relationship or relationship.tenant_id != self.tenant_id
            or relationship.status != GuardianRelationshipStatus.VERIFIED):
        raise PermissionDeniedError("لا توجد علاقة ولاية موثَّقة (VERIFIED) لهذا الطالب")

    settings = await self.repo.list_visibility_settings(relationship.id)
    academy_hidden = any(s.sector == GuardianVisibilitySector.ACADEMY and not s.is_visible for s in settings)
    if academy_hidden:
        raise PermissionDeniedError("قطاع الأكاديميا محجوب — لا يمكن التواصل مع مدرّس")

    academy_repo = AcademyRepository(self.db)
    enrollment = await academy_repo.get_enrollment(ward_user_id, course_id, self.tenant_id)
    if not enrollment:
        raise NotFoundError("الطالب غير مسجَّل في هذا الكورس")

    course = await academy_repo.get_course(course_id, self.tenant_id)
    if not course or course.instructor_id is None:
        raise NotFoundError("لا يوجد مدرّس مُسنَد لهذا الكورس")

    instructor_user_id = await self.repo.get_instructor_user_id(course.instructor_id)
    if not instructor_user_id:
        raise NotFoundError("لا يوجد مدرّس مُسنَد لهذا الكورس")

    comm_service = CommunicationsService(self.db)
    return await comm_service.send_notification(
        user_id=instructor_user_id, title="رسالة من ولي أمر أحد الطلاب",
        body=message_text, data={"course_id": course_id, "ward_id": ward_user_id, "guardian_id": guardian_user_id},
        channel=NotificationChannel.IN_APP, idempotency_key=None,
    )
```

**نفس فحص `get_ward_overview` بالحرف** (VERIFIED + tenant_id مطابق) +
فحص رؤية إضافي (`ACADEMY` لازم يكون مرئي) — بالضبط زي المطلوب. سلسلة
تحديد المدرّس تستخدم `AcademyRepository.get_enrollment`/`get_course`
مباشرة (بلا تعديل عليهما) — **إلا `get_instructor` نفسها، راجع قسم 3**.

### قرار `idempotency_key=None` — موثَّق في الكود

```python
# قرار مقصود: idempotency_key=None (بلا مفتاح إطلاقًا) — الرسائل مش
# عملية حساسة لإعادة محاولة (زي حجز/دفع) تحتاج حماية من تكرار غير
# مقصود. send_notification بتتخطى فحص الـidempotency بالكامل لو
# المفتاح None فبترجع صف Notification جديد في كل نداء — بالحرف
# المطلوب: "كل رسالة لازم تتبعت"، حتى لو نفس ولي الأمر بعت رسالتين
# متتاليتين بنفس النص لنفس المدرّس عن نفس الكورس.
```

---

## 3. ⚠️ اكتشاف باج schema حقيقي أثناء التحقق الحي — وليس تخطيطيًا

أول محاولة لتنفيذ الخطوة 4 بالحرف (`academy_repo.get_instructor(course.instructor_id,
self.tenant_id)`) فشلت فورًا. **تحقق معزول مباشر قبل أي استنتاج:**

```python
repo = AcademyRepository(db)
result = await repo.get_instructor(1, 1)
```
```
FAILED: ProgrammingError ... UndefinedColumnError: column academy_instructors.tenant_id does not exist
```

**تأكيد بنيوي على DB مباشرة** (`\d academy_instructors`):
```
id, user_id, org_entity_id, bio, expertise_areas, revenue_share_percentage, is_approved, created_at, updated_at
```
**صفر عمود `tenant_id`** — رغم إن الموديل (`academy/models.py`)
بيعرّفه صراحةً (`nullable=False`). انحراف موديل↔DB قديم وموجود من قبل
هذه الجلسة بالكامل — **صفر علاقة بأي كود guardian**، اكتُشف بالصدفة
لأن `message_instructor` هو أول كود في المشروع يستدعي
`AcademyRepository.get_instructor()` فعليًا (تأكَّد: الدالة كانت
"موجودة بس غير مُختبَرة حيًا" من قبل).

### توقّف صريح وعرض الخيارات (لم يُتَّخذ قرار من طرف واحد)

بما إن هذا يبطّل حرفية التعليمة الأصلية (خطوة 4 بالضبط)، تم **إيقاف
التنفيذ وعرض 4 خيارات على المستخدم صراحةً** بدل قرار انفرادي يلمس دومين
تاني بلا إذن:
1. تجاوز الدالة المكسورة داخل `GuardianService` بس.
2. إصلاح `get_instructor` نفسها في `academy/repository.py` (حذف فلتر
   `tenant_id`).
3. إضافة migration لعمود `tenant_id` الناقص (الإصلاح "الصحيح" الكامل).
4. وقف التنفيذ بالكامل لحد جلسة منفصلة.

**قرار المستخدم:** خيار مُعدَّل عن (1) — تجاوز معزول تمامًا، لكن
**داخل `guardian/repository.py` نفسها** (دالة جديدة صغيرة)، **مش** جوّه
`GuardianService` مباشرة كما اقترحت أول مرة، **وصفر لمس على
`academy/repository.py` أو أي migration**.

### الحل المُنفَّذ

```python
# guardian/repository.py
async def get_instructor_user_id(self, instructor_id: int) -> Optional[int]:
    """يرجع user_id بتاع المدرّس. الأمان محقَّق مسبقًا عبر Course.tenant_id
    (الاستدعاء بيحصل بس بعد التأكد إن الكورس نفسه ينتمي لنفس الـtenant)،
    مش عبر فلتر مباشر هنا — Instructor نفسها مفيهاش tenant_id (باج
    schema موثَّق منفصل: backlog-academy-instructors-missing-tenant-id)."""
    result = await self.db.execute(
        select(Instructor.user_id).where(Instructor.id == instructor_id)
    )
    return result.scalar_one_or_none()
```

**لماذا آمن رغم غياب فلتر `tenant_id`:** الأمان مضمون transitively —
`get_course(course_id, self.tenant_id)` قبلها بالفعل فلترت بالـtenant
الصحيح (لو الكورس مش بتاع نفس الـtenant، هيترفض هناك بـ`NotFoundError`
قبل ما نوصل لهذه السطر أصلًا). `Course.instructor_id` FK يضمن إن
`instructor_id` المُمرَّر بيشير لصف `Instructor` حقيقي موجود بالفعل —
مفيش أي مسار يوصل لهذه الدالة بـ`instructor_id` من tenant مختلف.

**بند Backlog جديد اتفتح** (`backlog-academy-instructors-missing-tenant-id`,
🟡 أولوية متوسطة) — راجع `PROGRESS_LOG.md` للتفاصيل الكاملة (الأثر
على `create_instructor`/`get_instructor` نفسهما، والحل المتوقَّع
النهائي عبر migration منفصل).

---

## 4. `POST /guardian/wards/{ward_id}/message-instructor`

```python
@router.post("/wards/{ward_id}/message-instructor", response_model=NotificationResponse, status_code=201)
async def message_instructor(
    ward_id: int,
    data: GuardianMessageInstructorRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = GuardianService(db, cast(int, current_user.tenant_id))
    return await service.message_instructor(
        guardian_user_id=cast(int, current_user.id), ward_user_id=ward_id,
        course_id=data.course_id, message_text=data.message,
    )
```

`response_model=NotificationResponse` — أُعيد استخدام schema موجود
بالفعل في `communications/schemas.py` (بلا تكرار)، بعكس
`get_ward_overview` (اللي بلا `response_model` عمدًا لأسباب مختلفة —
استبعاد مفاتيح كاملة). هنا الرد شكله ثابت دايمًا (نجاح = صف Notification
واحد)، فـ`response_model` عادي مناسب.

`GuardianMessageInstructorRequest(course_id: int, message: str)` —
جسم الطلب بالحرف زي المطلوب.

---

## 5. الاختبار الحي

`tests/test_guardian_message_instructor_implementation.py` — 4
سيناريوهات، عبر `GuardianService` مباشرة، فوق DB حقيقية.

**ملحوظة على الـfixture:** إنشاء صف `Instructor` اضطر يستخدم
`insert()` من SQLAlchemy Core (`insert(Instructor.__table__).values(...)`)
**بدل** `db.add(Instructor(...))` العادي — لنفس سبب باج قسم 3 بالضبط:
الـORM بيولّد `INSERT` شامل لكل أعمدة الموديل المُعرَّفة (بما فيها
`tenant_id` الوهمي) حتى لو مش مُمرَّر صراحةً، فيفشل فورًا. `insert()`
من Core بيحدد الأعمدة الموجودة فعليًا في DB بس — تأكَّد بالفشل الفعلي
(نفس الخطأ بالحرف) قبل التحول لهذا الحل.

1. **`test_message_instructor_success_creates_real_notification`**:
   علاقة VERIFIED + تسجيل فعلي + مدرّس مُسنَد → نجاح، `notification.user_id
   == instructor_user_id`، **تحقق مباشر من DB** (مش mock) إن صف
   `Notification` حقيقي محفوظ بنفس النص. **PASSED**.
2. **`test_message_instructor_rejected_when_academy_hidden`**: قطاع
   `ACADEMY` محجوب → `PermissionDeniedError`. **PASSED**.
3. **`test_message_instructor_rejected_for_course_not_enrolled`**:
   `course_id` الطالب مش مسجَّل فيه → `NotFoundError`. **PASSED**.
4. **`test_message_instructor_rejected_for_course_without_instructor`**:
   كورس بلا مدرّس مُسنَد (`instructor_id IS NULL`) → `NotFoundError`.
   **PASSED**.

**النتيجة: 4/4 نجحوا** (16/16 مع كل ملفات guardian الأربعة معًا:
foundation + flow + overview + message-instructor).

### اكتشاف جانبي بيئي (مُصلَح ذاتيًا، غير مرتبط بالكود النهائي)

أول محاولتين للاختبار فشلتا (قبل الوصول للحل النهائي في قسم 3) —
وبما إن `_create_user` بتعمل `commit()` فوري (مستقل عن نجاح باقي
الاختبار)، والفشل كان بيحصل **قبل** الوصول لـ`try/finally` الخاص
بالتنظيف (نفس نمط `fx = await _build_...()` قبل `try:` المُستخدَم في
كل ملفات guardian السابقة)، تركت **36 مستخدم throwaway يتيم**. اتنضَّفوا
يدويًا بعد نجاح التشغيلة النهائية (`DELETE FROM users WHERE username
LIKE 'p_regtest_msg_%'`) — صفر بقايا بيانات حاليًا (اتأكَّد مباشرة).
لم يُعدَّل هيكل أي ملف اختبار سابق لتفادي هذا النمط — سابقة قائمة عبر
كل الملفات، خارج نطاق هذه الجلسة.

---

## 6. Regression

- **كل ملفات guardian الأربعة معًا** (foundation + flow + overview +
  message-instructor): **16/16 نجحوا**.
- **`pytest --collect-only`** على كامل `tests/` (240 اختبار، +4 من
  هذه الجلسة): صفر خطأ استيراد جديد؛ نفس الخطأ المسبق الوحيد
  (`ActionCommission`، غير مرتبط).
- **صفر تعديل على `academy/`, `communications/`** — مؤكَّد بمطابقة
  الملفات المعدَّلة (`guardian/repository.py`, `guardian/service.py`,
  `guardian/schemas.py`, `guardian/router.py` + ملف الاختبار الجديد
  بس).

---

## الحالة النهائية

- **الـendpoint مبني بالكامل ومتحقَّق منه حيًا**: `POST
  /guardian/wards/{ward_id}/message-instructor`، تفويض VERIFIED +
  رؤية ACADEMY، تحديد مدرّس عبر `Course.instructor_id` (مش
  `LiveSession`)، رسالة IN_APP بلا idempotency (قرار موثَّق).
- **باج schema حقيقي اتكشف حيًا، اتوقَّف التنفيذ، اتعرضت الخيارات على
  المستخدم صراحةً، واتحل بأضيق نطاق ممكن** — صفر لمس على `academy/`.
- **بند Backlog جديد اتفتح** (`backlog-academy-instructors-missing-tenant-id`)
  لتتبع الإصلاح الكامل المستقبلي.
- **لم يُعمَل commit على git بعد** — بانتظار طلب المستخدم.
- **PROGRESS_LOG.md** اتحدَّث بإدخالين: تنفيذ الميزة + بند Backlog
  الجديد.
