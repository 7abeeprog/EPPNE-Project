# GET /guardian/wards/{ward_id}/overview — جلسة تخطيط تصميم (read-only)

**تاريخ:** 2026-09-16
**النطاق:** فحص read-only بحت لتجهيز تصميم endpoint موحَّد يجمّع بيانات
الطالب من 4 دومينات (academy, social, transport, health)، محترمًا
`GuardianVisibilitySetting`. امتدادًا لـ
[[project_guardian_relationship_flow_implementation]] (المرحلة التانية
مبنية ومتحقَّق منها من قبل).
**ممنوع أي تعديل كود — تم الالتزام، صفر Edit/Write على كود المشروع.**

**منهجية الجلسة:** بحث موزَّع عبر subagent على الدومينات الخمسة
(academy, achievements, social, transport, health) بالتوازي مع بحث
مباشر على نمط الأداء (`asyncio.gather`)، ثم تحقق مباشر يدوي على أهم
الادعاءات الحساسة (ownership gaps، tenant scoping) قبل تضمينها هنا.

---

## 1. ACADEMY — كورسات + تقدّم + إنجازات

### كورسات مسجَّل فيها + تقدّم

**موجود وقابل لإعادة الاستخدام مباشرة:**

```python
# academy/service.py:436-437
async def get_user_enrollments(self, user_id: int, skip: int = 0, limit: int = 100):
    return await self.repo.get_user_enrollments(user_id, self.tenant_id, skip, limit)
```

```python
# academy/repository.py:513-529
async def get_user_enrollments(self, user_id, tenant_id, skip=0, limit=100) -> PaginatedResponse[EnrollmentResponse]:
    query = select(Enrollment).where(and_(Enrollment.user_id == user_id, Enrollment.tenant_id == tenant_id))...
```

مُستخدَمة فعليًا في `GET /academy/student/my-enrollments`
(`academy/router.py:251-261`) — بتاخد `user_id` صراحةً كمعامل، مش مربوطة
بـ`current_user` داخليًا، فقابلة للاستخدام فورًا بـ`ward_id`.

**النقص الوحيد:** `EnrollmentResponse` (`academy/schemas.py:265-283`)
بترجع `course_id` (رقم FK) **بس، مش عنوان الكورس** — الموديل `Enrollment`
مالوش `relationship()` لـ`Course` أصلًا، والاستعلام بلا `join`. لعرض
"الكورس الفلاني — 45%" بدل "كورس رقم 17 — 45%"، لازم **استعلام جديد
بسيط** يعمل `join` مع `Course.title` — إضافة صغيرة، مش إعادة بناء.

**الملخَّص المقترح للعرض** (أبسط شكل، استبعاد الحقول المالية/الإلغاء
غير اللازمة لولي الأمر — `payment_status`, `cancellation_reason/note`,
`refund_status/amount` كلها موجودة في `Enrollment` لكن زيادة عن اللزوم):

```
{course_title, progress_percentage, is_completed, status, last_accessed}
```

### إنجازات

**موجود ومؤكَّد** (دومين بنيناه إمبارح فعلًا):

```python
# achievements/service.py:101-102
async def get_user_achievements(self, user_id: int) -> List[UserAchievement]:
    return await self.repo.list_user_achievements(user_id, self.tenant_id)
```

**النقص:** نفس مشكلة الكورسات — `UserAchievementResponse`
(`achievements/schemas.py:54-63`) فيها `achievement_definition_id` (FK)
**بس، مش اسم الإنجاز**. `AchievementDefinition.name/description/icon_url`
(`achievements/models.py:29-59`) لازم `join` جديد لعرض "حقق: نجم
التدريب" بدل "إنجاز رقم 3". **استعلام جديد بسيط** لازم (`join`
`UserAchievement`↔`AchievementDefinition`).

**⚠️ ملاحظة أمان جانبية غير مرتبطة بميزة ولي الأمر (موجودة بالفعل،
غير مُصلَحة، خارج النطاق):** `GET /achievements/users/{user_id}`
(`achievements/router.py:79-87`) بتاخد `user_id` كـpath param وبتفحص
بس `get_current_active_user` (تسجيل دخول) — **صفر فحص إن
`user_id == current_user.id`**. أي مستخدم عادي في الـtenant يقدر يشوف
إنجازات أي مستخدم تاني اليوم عبر هذا الـendpoint. **مش خطر جديد تقدّمه
ميزة ولي الأمر** (الفجوة موجودة أصلًا)، لكن يستحق الإشارة كملاحظة
مستقلة — لم يُلمَس، خارج نطاق هذه الجلسة.

**الملخَّص المقترح:**
```
[{achievement_name, description, icon_url, points_value, granted_at}, ...]
```

---

## 2. SOCIAL — آخر نشاط، بلا كشف زيادة

### الفحص: هل فيه مفهوم خصوصية على مستوى المنشور؟

**لا — اكتشاف مهم.** فحص شامل لـ`social/models.py`: `Post`
(`models.py:35-68`) **بلا أي عمود `is_private`/`visibility`** — كل
منشور مرئي ضمنيًا على مستوى الـtenant بالكامل، بلا تحكم فردي. المفهوم
الوحيد للخصوصية في الدومين كله:
- `SocialGroup.privacy` (`PUBLIC/PRIVATE/SECRET`) — على مستوى المجموعة، مش المنشور الفردي.
- `UserOccasion.is_public` (`models.py:351`) — خاص بالتذكيرات/المناسبات، مش المنشورات.

**يعني: مفيش "منشور خاص" ممكن نستثنيه من عرض ولي الأمر — الحقل نفسه
غير موجود في الـschema.** أي تصميم "بلا كشف محتوى حساس زيادة عن اللزوم"
لازم يعتمد على **تقليل الحقول المعروضة نفسها** (مش فلترة خصوصية غير
موجودة أصلًا)، أو قرار منتجي منفصل: هل نعرض كل المنشورات، ولا نعرض
عدد بس بلا محتوى؟ **قرار خارج نطاق هذه الجلسة القرائية.**

### دالة جاهزة؟ لا — تحتاج بناء من الصفر

بحث شامل في `social/service.py`/`social/repository.py`: **صفر دالة
تفلتر بـ`author_id`** رغم إن العمود موجود على الموديل. المطابقة
الوحيدة لـ`author_id` في كامل الدومين هي `service.py:76` (كتابته وقت
إنشاء منشور جديد) — **لا استعلام قراءة واحد يستخدمه**. الموجود فعليًا:

- `PostRepository.get_global_feed(tenant_id, skip, limit)` — فيد عام
  للـtenant كله، **بلا فلتر مستخدم**.
- `SocialService.get_feed(tenant_id, skip, limit)` — نفس الشيء.
- `SocialService.get_post(post_id, tenant_id)` — منشور واحد بمعرفه.
- الراوتر يؤكد: `GET /social/feed` (عام) و`GET /social/posts/{post_id}`
  (فردي) بس — **صفر `/posts/mine` أو ما يعادله**.

**الخلاصة: مفيش أي دالة "منشورات مستخدم معيّن" في المشروع كله —
لازم تُبنى بالكامل من الصفر** (`list_user_posts(user_id, tenant_id,
skip, limit)` بفلتر `Post.author_id == user_id AND Post.is_deleted == False`).

**الملخَّص المقترح (أبسط وأأمن شكل، نظرًا لغياب أي فلتر خصوصية):**
عوض عرض محتوى المنشورات نفسه لولي الأمر (خطر خصوصية حقيقي بما إن مفيش
فلتر "خاص" أصلًا)، الأنسب ملخَّص **عددي بحت بلا محتوى نصي**:
```
{posts_count_last_30_days, comments_count_last_30_days, last_activity_at}
```
عرض `content` الفعلي للمنشورات **غير مستحسن** هنا تحديدًا لأن المشروع
مالوش آلية "خاص/عام" على مستوى المنشور أصلًا — عرض النص الكامل يعني
عرض كل حاجة كتبها الطالب بلا استثناء ممكن. **قرار منتجي نهائي خارج
نطاق هذه الجلسة.**

---

## 3. TRANSPORT — آخر رحلات/حجوزات كراكب

**موجود وقابل لإعادة الاستخدام مباشرة:**

```python
# transport/service.py:648-655
async def get_my_bookings(self, tenant_id: int, passenger_id: int) -> List[TripBooking]:
    await self._check_saas_limits(tenant_id, "transport")
    result = await self.repo.list_bookings(tenant_id, passenger_id=passenger_id)
    return list(result)
```

```python
# transport/repository.py:261-270
async def list_bookings(self, tenant_id, passenger_id=None, trip_id=None):
    query = select(TripBooking).options(selectinload(TripBooking.trip)).where(TripBooking.tenant_id == tenant_id)
    if passenger_id:
        query = query.where(TripBooking.passenger_id == passenger_id)
    ...
```

بالرغم من اسمها `get_my_bookings`، بتاخد `passenger_id` كمعامل صريح —
قابلة للاستخدام فورًا بـ`ward_id`. الـrepository **بيعمل eager-load
لـ`.trip` بالفعل** (`selectinload`)، يعني بيانات الرحلة (الجدول
الزمني، الحالة) متاحة بلا استعلام N+1 إضافي.

**النقص:** `TripBookingResponse` (`transport/schemas.py:134-139`) **ما
بتعرضش** العلاقة المحمَّلة `trip` أصلًا (لا `scheduled_start` ولا حالة
الرحلة ولا الطريق) رغم إنها محمَّلة فعليًا في الذاكرة — القصور في
الـschema بس، مش في الاستعلام. لعرض "رحلة يوم كذا الساعة كذا" لازم
**schema جديد** (أو تسطيح يدوي) يستخرج `booking.trip.scheduled_start`/
`booking.trip.status` بجانب حقول الحجز.

**الملخَّص المقترح:**
```
[{scheduled_start, trip_status, fare_paid_mrusdt, booking_status}, ...]  # آخر N رحلة
```
(بدون تفاصيل الموقع الدقيق/الطريق الكامل لو مطلوب تقليل الحساسية —
`route_id`/`waypoints` أدق من اللازم لملخَّص ولي أمر).

---

## 4. HEALTH — أقل قدر بيانات كافٍ (أكتر قطاع حساس)

### تصنيف الحساسية (فحص كامل لكل موديلات الدومين)

| الموديل | الحساسية | الحقول |
|---|---|---|
| `MedicalAppointment` | **إداري — آمن نسبيًا** | `appointment_time, appointment_type, status, facility_id, department_id` — **صفر تشخيص أو ملاحظات طبية** |
| `HealthConsultation` | **حساس سريريًا** | `doctor_notes (Text), diagnosis (Text), prescription_ref` |
| `Prescription` | **حساس سريريًا** | `medications (JSONB), doctor_notes (Text)` |
| `MedicalProfile` | **حساس جدًا** | `blood_type, chronic_diseases, allergies, current_medications, emergency_contact` |
| `AIHealthPrognosis` | **حساس** | `risk_level, predicted_condition, confidence_score` |
| `BiometricLog` | **حساس** | `aggregated_metrics (JSONB)` |

### دالة جاهزة للمواعيد (الإداري بس)

```python
# health/service.py:292-294
async def get_my_appointments(self, user_id: int, status_filter: Optional[str] = None) -> List[MedicalAppointment]:
    return list(await self.repo.list_appointments(user_id, status_filter))
```

```python
# health/repository.py:96-102
async def list_appointments(self, user_id: int, status: Optional[str] = None):
    query = select(MedicalAppointment).where(MedicalAppointment.patient_user_id == user_id)
    ...
```

**بترجع شكل إداري بحت بالفعل** (`MedicalAppointmentResponse`،
`health/schemas.py:100-106`): `doctor_id, facility_id, department_id,
appointment_time, appointment_type, status, payment_tx_hash` — **صفر
تشخيص، صفر ملاحظات طبية، صفر أدوية**. هذا **مرشَّح جاهز للعرض شبه كما
هو** — الحقل الوحيد اللي يستاهل الحذف هو `payment_tx_hash` (تفصيل
مالي/بلوكتشين زيادة عن اللزوم لولي الأمر).

**مفيش أي دالة "قايمة سجلات لمستخدم" لـ`HealthConsultation`/
`Prescription`/`MedicalProfile`** — بحث شامل: يوجد بس getters فردية
بالـid (`get_consultation(consultation_id)`)، **صفر `list_by_user`
لأي منهم**. هذا **إيجابي أمنيًا بالصدفة** — مفيش مسار موجود أصلًا
لتسريب بيانات سريرية حساسة، فمفيش خطر "إعادة استخدام دالة زيادة عن
اللزوم" هنا.

**⚠️ ملاحظة جانبية غير مرتبطة (موجودة بالفعل، غير مُصلَحة):**
`HealthService(db)` بتتبني **بلا `tenant_id`** (`health/service.py:44`)،
و`list_appointments` **بلا فلتر `tenant_id` إطلاقًا** — الفلترة الوحيدة
هي `patient_user_id`. بما إن `guardian_relationship` نفسها tenant-scoped
(هنتأكد من `ward_id` عبر علاقة موافَق عليها في نفس الـtenant قبل
استدعاء أي دومين)، الأثر العملي على ميزة ولي الأمر **محدود**، لكنها
فجوة معمارية مستقلة تستحق الإشارة — لم تُلمَس، خارج النطاق.

**الملخَّص المقترح (أقل قدر كافٍ):**
```
[{appointment_time, appointment_type, status, facility_id}, ...]  # بلا doctor_id ولا payment_tx_hash
```
**استبعاد كامل ومتعمَّد لـ**: `HealthConsultation`, `Prescription`,
`MedicalProfile`, `AIHealthPrognosis`, `BiometricLog` — أي منهم يحتوي
تشخيص/دواء/حالة مرضية فعلية، وده بالضبط "التفاصيل الطبية الدقيقة"
المطلوب تجنبها في صياغة السؤال.

---

## 5. جدول ملخَّص: إعادة استخدام مقابل بناء جديد

| القطاع | أفضل دالة موجودة | قابلة للاستخدام كما هي؟ | العمل الجديد المطلوب |
|---|---|---|---|
| ACADEMY | `AcademyService.get_user_enrollments(user_id, skip, limit)` | نعم لـ`course_id`/`progress`/`status` | `join` جديد لـ`Course.title` بس |
| ACHIEVEMENTS | `AchievementService.get_user_achievements(user_id)` | نعم للسجلات الخام | `join` جديد لـ`AchievementDefinition` (اسم/وصف/أيقونة) |
| SOCIAL | **لا يوجد** | لا | دالة جديدة بالكامل (`list_user_posts`) — ومفيش حقل خصوصية أصلًا على `Post` |
| TRANSPORT | `TransportService.get_my_bookings(tenant_id, passenger_id)` | نعم للحجوزات/الحالة/الأجرة | schema جديد بس لعرض جدول الرحلة (الاستعلام نفسه بيعمل eager-load بالفعل) |
| HEALTH | `HealthService.get_my_appointments(user_id, status_filter)` | نعم كما هي تقريبًا (إداري بحت) | لا شيء إجباري؛ حذف `payment_tx_hash` اختياري |

**الخلاصة العامة:** 3 من 4 قطاعات (academy, transport, health) عندها
دالة service جاهزة تاخد `user_id`/`passenger_id` كمعامل صريح (مش
مربوطة بـ`current_user` داخليًا) — إعادة استخدام مباشرة، مع تحسينات
عرض بسيطة (joins/schema) لكل من academy/achievements/transport. **قطاع
واحد بس (social) يحتاج دالة جديدة من الصفر بالكامل.**

**ملاحظة مشتركة مهمة:** **صفر دالة من الخمسة دول بتعمل فحص ownership
داخليًا** (`user_id == current_user.id` أو مكافئه) — الفحص كله (هل
`current_user` هو فعلًا ولي أمر مُوثَّق لـ`ward_id`، وهل `ward_id` مُتاح
له القطاع ده عبر `GuardianVisibilitySetting`) **لازم يتنفذ بالكامل جوّه
`GuardianService`/endpoint الجديد نفسه**، قبل استدعاء أي من الدوال دي.
بنيات `GuardianRelationship`/`GuardianVisibilitySetting` الموجودة
بالفعل من المرحلة السابقة (`GuardianRepository.get_relationship_by_guardian_and_ward`,
`list_visibility_settings`) كافية لبناء هذا الفحص.

---

## 6. تأكيد الأداء — `asyncio.gather` مقابل استدعاء تسلسلي

**التوصية: استدعاء تسلسلي، مش `asyncio.gather` — واكتشفنا سابقة فعلية
في المشروع بتوضح ليه.**

### السابقة الموجودة فعليًا (`projects/service.py:455-459`)

```python
async def get_project_analytics(self, project_id: int, tenant_id: int) -> dict:
    ...
    total_contributors, total_monetary, total_in_kind = await asyncio.gather(
        self.repo.count_contributors(project_id, tenant_id),
        self.repo.sum_monetary_contributions(project_id, tenant_id),
        self.repo.sum_in_kind_contributions(project_id, tenant_id)
    )
```

**المشكلة:** `self.repo` (`ProjectRepository(db)`، سطر 35-36 من نفس
الملف) بيستخدم **نفس `AsyncSession` (`self.db`) المُمرَّرة من الراوتر**
لكل الاستدعاءات الثلاثة داخل الـ`gather`. **`AsyncSession` في SQLAlchemy
غير آمنة للاستخدام المتزامن (concurrent) على الإطلاق** — التوثيق
الرسمي لـSQLAlchemy صريح في إن نفس الـsession/connection متسمحش
باستدعاءين `execute()` متزامنين. هذا النمط الموجود بالفعل في المشروع
**خطر حقيقي (قد ينتج `InterfaceError`/`IllegalStateChangeError` حسب
توقيت التداخل الفعلي بين الاستعلامات)** — لم يُفحص أو يُصلَح هنا (خارج
نطاق هذه الجلسة القرائية بالكامل)، لكنه **دليل مباشر وملموس** على خطر
تكرار نفس النمط في endpoint ولي الأمر الجديد.

### لماذا هذا ينطبق مباشرة على `/guardian/wards/{ward_id}/overview`

كل endpoints المشروع (بما فيها `guardian/router.py` المبني بالفعل)
تتبع نمط واحد: `db: AsyncSession = Depends(get_db)` — **جلسة واحدة
مُحقَنة لكل الطلب بالكامل**. الـendpoint الجديد هيستدعي 4 دومينات
(`AcademyService(db, ...)`, `AchievementService(db, ...)`,
`SocialService(db, ...)`, `TransportService(db, ...)`,
`HealthService(db)`) — **كلهم هيشاركوا نفس الـ`db` بالحقن الافتراضي
لأي endpoint في المشروع**. استخدام `asyncio.gather` على استدعاءات من
كل الدومينات دي هيكرر بالضبط نفس خطر `get_project_analytics` — بس
على نطاق أوسع (5 دومينات بدل 3 استعلامات في دومين واحد).

### حجم البيانات فعليًا يرجّح التسلسلي أصلًا

- كل استعلام من الخمسة (enrollments، achievements، posts-count،
  bookings، appointments) هو `SELECT` بسيط بفلتر `user_id`/`tenant_id`،
  بلا معالجة ثقيلة، وبأعداد صفوف صغيرة جدًا لكل مستخدم (طالب واحد،
  مش تجميع عبر آلاف المستخدمين).
- 5 استعلامات متسلسلة بسيطة كده = زمن استجابة إضافي مهمَل (كل واحدة
  ميلي ثانية قليلة) مقارنة بمخاطرة كسر الـsession.

**الخلاصة: استدعاء تسلسلي (`await` واحد تلو الآخر) كافٍ تمامًا، وهو
الخيار الآمن الوحيد فعليًا** طالما endpoint واحد بيستخدم `db` واحدة
مُحقَنة (وده النمط الوحيد المتَّبع في كل المشروع اليوم — تغييره لجلسات
منفصلة لكل دومين تعقيد غير مبرَّر لحجم البيانات ده). لو الأداء أصبح
مصدر قلق فعلي مستقبلًا (غير متوقَّع هنا)، البديل الصحيح هو **جلسات DB
منفصلة فعليًا لكل استدعاء متزامن** (مش نفس الـsession تحت `gather`) —
تعقيد إضافي غير مبرَّر الآن.

---

## خلاصة الأثر على تصميم `GET /guardian/wards/{ward_id}/overview`

هذه الجلسة تخطيط فقط، بدون قرار تصميم نهائي:

1. **الأمان أولًا، جوّه `GuardianService` نفسها**: فحص
   `GuardianRelationship` بين `current_user` و`ward_id` (لازم `VERIFIED`)
   + جلب `GuardianVisibilitySetting` لتحديد أي القطاعات الـ4 مسموح
   بيها فعلًا — **قبل** أي استدعاء لأي دومين تشغيلي.
2. **استدعاء تسلسلي لكل قطاع مسموح بيه بس** (مش الأربعة دايمًا) — كل
   استدعاء عبر الدالة الموجودة فعليًا (قسم 5)، مع تحسين عرض بسيط
   (join/schema) لـ3 من الـ4.
3. **social يحتاج دالة جديدة من الصفر** (`list_user_posts`) — وقرار
   منتجي منفصل: عرض المحتوى الفعلي (بلا أي حماية خصوصية موجودة أصلًا
   في الـschema) ولا ملخَّص عددي بس (المقترح الأأمن هنا).
4. **health الأكثر حساسية بالفعل مُقيَّد ببنية الكود نفسها** — صفر دالة
   "قايمة لمستخدم" لأي بيانات سريرية حقيقية، فالاستبعاد شبه تلقائي طالما
   الـendpoint الجديد بيستدعي بس `get_my_appointments`.
5. **`asyncio.gather` غير موصى به** — استدعاء تسلسلي هو الخيار الآمن
   والكافي، مدعومًا بمثال فعلي موجود بالكود (`projects/service.py:455`)
   يوضح الخطر لو اتكرر النمط.

**التنفيذ الفعلي (الـendpoint، الدوال الجديدة، الـjoins) يحتاج جلسة
تنفيذ منفصلة بموافقة صريحة**، نفس القاعدة المتبعة في كل الجلسات
السابقة.
