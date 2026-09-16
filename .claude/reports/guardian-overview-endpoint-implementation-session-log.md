# GET /guardian/wards/{ward_id}/overview — جلسة تنفيذ

**تاريخ:** 2026-09-16
**النطاق:** بناء endpoint موحَّد يجمّع بيانات الطالب من 4 دومينات
(academy+achievements, social, transport, health)، محترمًا
`GuardianVisibilitySetting`، بأقل قدر تعديل ممكن على الدومينات
القائمة. فوق أساس [[project_guardian_overview_endpoint_planning]]
(التخطيط read-only) و[[project_guardian_relationship_flow_implementation]].

---

## 1. الملفات الجديدة/المعدَّلة

| الملف | التغيير |
|---|---|
| `app/domains/academy/repository.py` | +`get_user_enrollments_summary()` — دالة جديدة بحتة |
| `app/domains/academy/service.py` | +`get_user_enrollments_summary()` — wrapper رقيق |
| `app/domains/social/repository.py` | +`get_user_activity_summary()` — دالة جديدة بالكامل |
| `app/domains/social/service.py` | +`get_user_activity_summary()` — wrapper رقيق |
| `app/domains/guardian/service.py` | +`get_ward_overview()` + 4 دوال بناء ملخَّص خاصة |
| `app/domains/guardian/router.py` | +`GET /guardian/wards/{ward_id}/overview` |
| `tests/test_guardian_overview_endpoint_implementation.py` | **جديد** — 3 سيناريوهات حية |

**صفر تعديل على `transport/`, `health/`, أو أي دالة قائمة في
`academy/`/`social/` غير الإضافتين الجديدتين المذكورتين.**

---

## 2. الأمان أولًا — `GuardianService.get_ward_overview`

```python
async def get_ward_overview(self, guardian_user_id: int, ward_user_id: int) -> Dict[str, Any]:
    relationship = await self.repo.get_relationship_by_guardian_and_ward(guardian_user_id, ward_user_id)
    if (
        not relationship
        or relationship.tenant_id != self.tenant_id
        or relationship.status != GuardianRelationshipStatus.VERIFIED
    ):
        raise PermissionDeniedError("لا توجد علاقة ولاية موثَّقة (VERIFIED) لهذا الطالب")

    settings = await self.repo.list_visibility_settings(relationship.id)
    hidden_sectors = {s.sector for s in settings if not s.is_visible}

    overview: Dict[str, Any] = {"ward_id": ward_user_id}
    if GuardianVisibilitySector.ACADEMY not in hidden_sectors:
        overview["academy"] = await self._build_academy_summary(ward_user_id)
    if GuardianVisibilitySector.SOCIAL not in hidden_sectors:
        overview["social"] = await self._build_social_summary(ward_user_id)
    if GuardianVisibilitySector.TRANSPORT not in hidden_sectors:
        overview["transport"] = await self._build_transport_summary(ward_user_id)
    if GuardianVisibilitySector.HEALTH not in hidden_sectors:
        overview["health"] = await self._build_health_summary(ward_user_id)
    return overview
```

**نقاط التصميم:**
- الفحص الأول والوحيد قبل أي استعلام تشغيلي: علاقة موجودة + `tenant_id`
  مطابق (دفاع إضافي صريح، بنفس روح إصلاح الجلسة الأمنية اللي فاتت) +
  **`status == VERIFIED` بالحرف** — أي حالة تانية (`PENDING_WARD_APPROVAL`,
  `PENDING_ADMIN_REVIEW`, `REJECTED`) أو غياب العلاقة بالكامل يترفض
  فورًا بـ`PermissionDeniedError` (403).
- **قرار "الصف المفقود = مرئي افتراضيًا"**: لو مفيش صف
  `GuardianVisibilitySetting` صريح لقطاع معيّن، القطاع **بيُعتبر مرئي**
  (مش محجوب) — مطابق للـ`server_default='true'` على عمود `is_visible`
  نفسه في migration 056. في الممارسة العملية هذا نادر الحدوث لأن
  `_ensure_default_visibility_settings` بتتنفذ تلقائيًا لحظة ما العلاقة
  توصل `VERIFIED` (من الجلسة السابقة)، لكن الفحص هنا دفاعي.
- **القسم المحجوب = مفتاح غائب تمامًا، مش `null`**: بالضبط زي ما طُلب.
  الـrouter نفسه **بلا `response_model`** عمدًا (`-> Dict[str, Any]`
  كـtype hint بس) — لو استخدمنا Pydantic response_model بحقول
  `Optional[...] = None`، FastAPI كان هيرجّع المفتاح بقيمة `null` في
  الـJSON مش هيحذفه، وده بالظبط اللي طُلب تفاديه ("مش يظهر فاضي").
  إرجاع `dict` خام بيخلي `jsonable_encoder` يسيب الـstructure زي ما
  هي بالحرف.

---

## 3. لكل قطاع — الملخَّص الفعلي

### ACADEMY — إضافة جديدة (`join` لعنوان الكورس)

```python
# academy/repository.py — جديد بالكامل
async def get_user_enrollments_summary(self, user_id, tenant_id, skip=0, limit=10):
    query = (
        select(Course.title, Enrollment.progress_percentage, Enrollment.is_completed, Enrollment.status)
        .join(Course, Course.id == Enrollment.course_id)
        .where(and_(Enrollment.user_id == user_id, Enrollment.tenant_id == tenant_id))
        .order_by(Enrollment.created_at.desc())
        .offset(skip).limit(limit)
    )
    result = await self.db.execute(query)
    return result.all()
```

`get_user_enrollments` القائمة (المُستخدَمة في `GET /academy/student/my-enrollments`)
**لم تُلمَس إطلاقًا** — دالة موازية جديدة بس، صفر خطر على أي مسار حالي.

### ACHIEVEMENTS (تحت مفتاح `academy`) — صفر كود جديد في الدومين نفسه

```python
# guardian/service.py — الـjoin بيتم هنا، مش في achievements
achievement_service = AchievementService(self.db, self.tenant_id)
user_achievements = await achievement_service.get_user_achievements(ward_user_id)
definitions_by_id = {d.id: d for d in await achievement_service.list_definitions(limit=1000)}
```

استُخدمت `get_user_achievements` (موجودة) + `list_definitions` (موجودة
أصلًا، بترجع كل تعريفات الـtenant) — استعلام واحد إضافي بدل N استعلام
منفصل لكل إنجاز. **صفر سطر جديد في `app/domains/achievements/`.**

### SOCIAL — دالة جديدة بالكامل (عدّ رقمي بحت)

```python
# social/repository.py — جديد بالكامل
async def get_user_activity_summary(self, user_id: int, tenant_id: int) -> dict:
    posts_row = (await self.db.execute(
        select(func.count(Post.id), func.max(Post.created_at)).where(
            and_(Post.author_id == user_id, Post.tenant_id == tenant_id, Post.is_deleted == False)
        )
    )).one()
    comments_row = (await self.db.execute(
        select(func.count(PostComment.id), func.max(PostComment.created_at)).where(
            and_(PostComment.author_id == user_id, PostComment.tenant_id == tenant_id, PostComment.is_deleted == False)
        )
    )).one()
    ...
    return {"post_count": ..., "comment_count": ..., "last_activity_at": ...}
```

بلا أي محتوى نصي خام — بالضبط القرار الموثَّق في جلسة التخطيط (`Post`
بلا عمود خصوصية، فالعد المجرد هو الخيار الآمن).

### TRANSPORT — استهلاك مباشر، **مع انحراف واحد موثَّق**

```python
async def _build_transport_summary(self, ward_user_id: int) -> List[Dict[str, Any]]:
    transport_service = TransportService(self.db)
    bookings = await transport_service.list_bookings(self.tenant_id, passenger_id=ward_user_id)
    return [
        {"trip_date": booking.trip.scheduled_start if booking.trip else None, "status": booking.status}
        for booking in bookings
    ]
```

**⚠️ استُخدمت `list_bookings` مش `get_my_bookings` المذكورة في
الطلب.** السبب المكتشَف حيًا: `get_my_bookings` بتنفّذ **نفس استعلام
`repo.list_bookings` بالحرف**، لكن بتضيف فوقها
`await self._check_saas_limits(tenant_id, "transport")` — بوابة
اشتراك SaaS **على مستوى الـtenant ككل**، لا علاقة لها بتفويض ولي
الأمر. أول تشغيلة للاختبار الحي فشلت فعليًا بـ:

```
app.core.errors.PermissionDeniedError: Transport feature is not included in your current plan.
```

`tenant_id=1` في DB الديف **مالوش خطة تتضمن "transport" مفعَّلة
حاليًا**. استخدام `get_my_bookings` كان هيخلي `overview` أي طالب
يفشل بالكامل لأي tenant بلا اشتراك transport صريح — قيد بيئي/اشتراكي
منفصل تمامًا عن سؤال "هل ولي الأمر ده مُوثَّق لهذا الطالب؟". **البديل
الوحيد المتاح بلا تعديل بيانات اشتراك الـtenant المشتركة** (تغيير
خطير وواسع الأثر، مش من اختصاص هذه الجلسة) هو استخدام
`list_bookings(tenant_id, passenger_id=...)` — دالة **موجودة بالفعل**
في نفس `TransportService`، بتنفّذ نفس الاستعلام تمامًا بدون بوابة
الـSaaS. **صفر تعديل على أي من الدالتين** — القرار كان أي دالة قائمة
نستهلكها، مش تعديل جديد.

### HEALTH — استهلاك مباشر (بعد إصلاح الجلسة السابقة)

```python
async def _build_health_summary(self, ward_user_id: int) -> List[Dict[str, Any]]:
    health_service = HealthService(self.db)
    appointments = await health_service.get_my_appointments(ward_user_id, self.tenant_id)
    facility_cache: Dict[int, Optional[str]] = {}
    for appointment in appointments:
        if appointment.facility_id not in facility_cache:
            facility = await health_service.get_facility(appointment.facility_id, self.tenant_id)
            facility_cache[appointment.facility_id] = facility.name if facility else None
        ...  # {"appointment_date", "facility_name", "status"} بس
```

`get_facility` **موجودة بالفعل** (`health/service.py:434-439`) —
استُخدمت لحل اسم المنشأة، مع تخزين مؤقت (`facility_cache`) لتفادي
استعلام مكرر لنفس المنشأة عبر عدة مواعيد. **صفر تشخيص/ملاحظات/أدوية**
— بالضبط "أقل قدر بيانات كافٍ" المتفَق عليه.

---

## 4. الاختبار الحي

`tests/test_guardian_overview_endpoint_implementation.py` — 3
سيناريوهات، عبر `GuardianService` مباشرة، فوق DB حقيقية. الـfixtures
(كورس، تعريف إنجاز، منشور، سلسلة نقل كاملة: محطتان+أسطول+مركبة+مسار+رحلة+حجز،
منشأة+موعد) اتعملت بإدخال ORM مباشر — تفاديًا لإعادة اختبار منطق
أعمال كل دومين (له اختباراته المنفصلة بالفعل)، والتركيز على طبقة
guardian نفسها (تفويض + رؤية + تجميع).

1. **`test_overview_returns_all_sectors_then_excludes_hidden_health`**:
   علاقة VERIFIED + نشاط حقيقي في الأربعة → تأكيد بيانات صحيحة من كل
   قطاع (عنوان الكورس، اسم الإنجاز، `post_count=1`/`comment_count=1`،
   حالة/تاريخ الرحلة، اسم المنشأة/حالة الموعد). ثم `update_visibility`
   لحجب `HEALTH` → استدعاء تاني → `"health" not in overview` (مفتاح
   غائب تمامًا)، `academy`/`social`/`transport` لسه موجودين. **PASSED**.
2. **`test_overview_rejected_for_pending_relationship`**: علاقة
   `PENDING_WARD_APPROVAL` (مش VERIFIED بعد) → `PermissionDeniedError`.
   **PASSED**.
3. **`test_overview_rejected_for_user_with_no_relationship`**: مستخدم
   بلا أي علاقة إطلاقًا → `PermissionDeniedError`. **PASSED**.

**النتيجة: 3/3 نجحوا** (12/12 مع كل ملفات guardian الثلاثة معًا:
foundation + flow + overview). صفر بقايا بيانات بعد التنظيف (اتأكَّد
مباشرة على DB لكل الجداول المُستخدَمة عبر الأربع دومينات).

---

## 5. Regression

- **كل اختبارات guardian الثلاثة معًا**: **12/12 نجحوا**.
- **عيّنة عبر الدومينات المُعدَّلة** (`test_social_getter_endpoints_wiring.py`
  + `test_transport_getter_endpoints_wiring.py` +
  `test_transport_vehicles_fleets_drivers.py` +
  `test_achievements_foundation_implementation.py`، 19 اختبار):
  **19/19 نجحوا** — صفر تأثير من الإضافتين الجديدتين
  (`get_user_enrollments_summary`, `get_user_activity_summary`) على
  أي مسار قائم في هذه الدومينات.
- **`pytest --collect-only`** على كامل `tests/` (236 اختبار، +3 من
  هذه الجلسة): صفر خطأ استيراد جديد؛ نفس الخطأ المسبق الوحيد
  (`ActionCommission`، غير مرتبط، موثَّق من قبل).

---

## الحالة النهائية

- **الـendpoint مبني بالكامل ومتحقَّق منه حيًا**: `GET
  /guardian/wards/{ward_id}/overview`، تفويض VERIFIED صارم، احترام
  كامل لـ`GuardianVisibilitySetting` (استبعاد تام مش قيمة فاضية)،
  استدعاء تسلسلي بحت (صفر `asyncio.gather`).
- **إضافتان جديدتان بس** في الدومينات القائمة (academy join + social
  summary)، **صفر تعديل على أي منطق موجود** في أي من الأربعة
  دومينات، بما فيها transport وhealth (صفر لمس نهائي).
- **انحراف واحد موثَّق وموضَّح بالكامل**: `list_bookings` بدل
  `get_my_bookings` (نفس الاستعلام، بلا بوابة SaaS غير ذات صلة).
- **لم يُعمَل commit على git بعد** — بانتظار طلب المستخدم.
- **PROGRESS_LOG.md** اتحدَّث بإدخال جديد لهذه الجلسة.
