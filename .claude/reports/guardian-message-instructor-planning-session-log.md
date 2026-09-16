# POST /guardian/wards/{ward_id}/message-instructor — جلسة تخطيط (read-only)

**تاريخ:** 2026-09-16
**النطاق:** فحص read-only بحت لتجهيز تصميم endpoint يسمح لولي الأمر
يبعت رسالة لمدرّس مسؤول عن ابنه. امتدادًا لـ
[[project_guardian_overview_endpoint_implementation]] و
[[project_targeted_notifications_planning]] (اكتشاف hardcoded
`instructor_id=1` القديم).
**ممنوع أي تعديل كود — تم الالتزام، صفر Edit/Write على كود المشروع.**

---

## 1. "المدرّس المسؤول" — إزاي بيتحدد فعليًا؟

### السلسلة الحقيقية (مُتحقَّق منها مرة تانية بالكود الحالي)

```
Enrollment(user_id=ward_id, course_id)  →  Course.instructor_id (nullable, FK → academy_instructors.id, ondelete SET NULL)  →  Instructor.user_id (FK → users.id, unique)
```

- `Enrollment` (`academy/models.py:262-300`): `user_id`, `course_id`
  (قيد فريد `(user_id, course_id)` — طالب واحد بس لكل كورس، يعني
  **عدد صفوف enrollment = عدد الكورسات المسجَّل فيها الطالب، كل واحد
  بمدرّس محتمل مختلف**).
- `Course.instructor_id` (`academy/models.py:140-158`): **nullable** —
  بعض الكورسات ممكن تكون بلا مدرّس مُسنَد إطلاقًا (لازم يتعامل معاها
  الـendpoint بوضوح، مش يفترض وجوده دايمًا).
- `Instructor.user_id` (`academy/models.py:63-72`): `unique=True،
  nullable=False` — كل مدرّب مرتبط بمستخدم واحد بس، وهو الشخص الفعلي
  اللي هيستقبل الرسالة.

### دوال جاهزة لإعادة الاستخدام (صفر كود جديد مطلوب لهذا الجزء)

```python
# academy/repository.py:501-511
async def get_enrollment(self, user_id: int, course_id: int, tenant_id: int) -> Optional[Enrollment]:
    ...  # للتحقق إن الطالب فعلًا مسجَّل في الكورس ده

# academy/repository.py:247-257
async def get_course(self, course_id: int, tenant_id: int) -> Optional[Course]:
    ...  # لجلب instructor_id بتاع الكورس

# academy/repository.py:149-153
async def get_instructor(self, instructor_id: int, tenant_id: int) -> Optional[Instructor]:
    ...  # لتحويل instructor_id → user_id الفعلي (المستلم)
```

كل الثلاثة موجودة فعليًا وقابلة للاستدعاء المباشر من `GuardianService`،
نفس نمط `guardian_overview` (استهلاك دوال قائمة بلا تعديل عليها).

### السؤال المطروح: رسالة لمدرّس كورس معيّن، ولا لكل مدرّسي الطالب؟

**التوصية: رسالة لمدرّس كورس معيّن، محدَّد صراحةً بـ`course_id` في
جسم الطلب — مش بث لكل المدرّسين.** الأسباب:
1. اسم الـendpoint نفسه مفرد (`message-instructor`، مش
   `message-instructors`) — يفترض ضمنيًا مستلم واحد محدَّد.
2. طالب مسجَّل في N كورس = N مدرّس محتمل مختلف (القيد الفريد
   `(user_id, course_id)` يثبت هذا فعليًا) — "كل مدرّسي الطالب" بث
   جماعي بلا سياق واضح (رسالة عن أنهي كورس بالظبط؟).
3. يطابق نمط `send_notification` نفسه (مستلم واحد فقط، راجع قسم 3) —
   بث لعدة مدرّسين كان هيحتاج loop زي `_notify_admins_pending_review`
   في المرحلة السابقة، وهو تعقيد إضافي بلا داعٍ واضح هنا (الرسالة
   موجَّهة لسياق كورس محدَّد، مش تنبيه عام).
4. **فحص إلزامي مطلوب قبل الإرسال**: `course_id` المُرسَل لازم يتحقق
   منه عبر `get_enrollment(ward_id, course_id, tenant_id)` — **ليس أي
   `course_id` عشوائي**، لازم يكون الطالب فعليًا مسجَّل فيه (يمنع ولي
   الأمر من "اختراع" `course_id` لمراسلة مدرّس مش له علاقة بابنه
   إطلاقًا).

---

## 2. `LiveSession.instructor_id` مقابل `Course.instructor_id` — أيهما أوثق؟

### تأكيد الباج القديم (لسه موجود، صفر تغيير منذ الجلسة السابقة)

```python
# academy/repository.py:707-716
async def create_live_session(self, node_id: int, data: dict) -> LiveSession:
    session_data = data.copy()
    session_data["node_id"] = node_id
    if "instructor_id" not in session_data:
        session_data["instructor_id"] = 1
    ...
```

**تفصيل إضافي اتأكَّد في هذه الجلسة (أدق من التوثيق السابق):** الفallback
ده **غير قابل للتفعيل عمليًا اليوم** — المسار الوحيد اللي بينادي هذه
الدالة هو `POST /academy/nodes/{node_id}/live`
(`academy/router.py:433-442`)، وجسم الطلب `LiveSessionCreate`
(`academy/schemas.py:317-319`) بيحدد `instructor_id: int` **إجباري
بلا قيمة افتراضية** — يعني `data.model_dump()` هيحتوي المفتاح دايمًا،
فالـfallback مش بيتفعل فعليًا من هذا المسار (تأكَّد بـgrep شامل: صفر
مستدعٍ تاني لـ`create_live_session` في كامل المشروع).

**لكن ده مايخليش `LiveSession.instructor_id` موثوقة** — المشكلة
الحقيقية أعمق من الـfallback: `instructor_id` في `LiveSessionCreate`
**قيمة يدخلها العميل بنفسه بالكامل، بلا أي تحقق من السيرفر** إنها
فعلًا نفس `Course.instructor_id` بتاع الكورس اللي الـlive session
تابعة له، ولا حتى إنها تطابق `current_user.id` (المُدخِل نفسه — الفحص
الوحيد هو `get_current_instructor_or_admin`، دور عام بس، مش تطابق
هوية). يعني أي مدرّس أو أدمن يقدر يدخل `instructor_id` لمدرّس تاني
تمامًا عن طريق الخطأ أو عمدًا، وهيتقبل بلا اعتراض.

**تحقق مباشر على DB الديف:** صفر صف في `live_sessions` حاليًا (الجدول
فاضي تمامًا) — يعني مفيش أي بيانات حقيقية نقارن بيها `LiveSession.instructor_id`
مقابل `Course.instructor_id` أصلًا، الخطر نظري بالكامل حتى الآن لكنه
حقيقي بنيويًا.

### التوصية: `Course.instructor_id` أوثق حاليًا — بوضوح

- **`Course.instructor_id`**: قيمة مُدارة إداريًا وقت إنشاء/تعديل
  الكورس (عبر endpoints إدارة الكورسات، خارج تحكم المستخدم العادي)،
  **علاقة واحدة ثابتة لكل كورس**، صفر مشكلة hardcoded/إدخال حر
  مكتشَفة.
- **`LiveSession.instructor_id`**: مُدخَل حر من العميل لكل جلسة على
  حدة، بلا أي تحقق مقابل `Course.instructor_id`، بلا بيانات حقيقية
  للمقارنة أصلًا (الجدول فاضي).

**القرار: استخدام `Course.instructor_id` حصريًا لتحديد "المدرّس
المسؤول" — تجاهل `LiveSession.instructor_id` بالكامل** في تصميم هذا
الـendpoint، بالحرف حسب توصية السؤال.

---

## 3. قناة الإرسال — `send_notification`: تأكيد نهائي + اكتشاف إضافي مهم

### التأكيد المطلوب (IN_APP فقط فعليًا)

```python
# app/core/celery_app.py:71-78
@shared_task(name="send_notification_task")
def send_notification_task(*args, **kwargs):
    """مهمة إرسال إشعار (مؤقتة - سيتم استبدالها بمهمة حقيقية لاحقاً)"""
    pass

@shared_task(name="send_email_task")
def send_email_task(*args, **kwargs):
    """مهمة إرسال بريد إلكتروني (مؤقتة - سيتم استبدالها بمهمة حقيقية لاحقاً)"""
    pass
```

**مؤكَّد: `send_notification_task` نفسها — المسؤولة نظريًا عن أي قناة
(بما فيها IN_APP) — دالة فارغة تمامًا (`pass`)، بلا أي فرق فعلي بين
EMAIL/SMS/IN_APP على مستوى الـCelery task.** القناة `channel` كباراميتر
بتتخزن في عمود `Notification.channel` بس (بيانات وصفية)، **بلا أي
منطق توجيه فعلي مختلف باختلاف القيمة**.

### ⚠️ اكتشاف إضافي (أدق من "IN_APP هي القناة الفعلية" — تفصيل مهم لتصميم الـUX)

`CommunicationsService.send_notification()` (المُستخدَمة من أي دومين،
بما فيها guardian) بترجع بعد إنشاء صف `Notification` حقيقي في DB —
هذا **الأثر الوحيد المضمون فعليًا**. لكن **البث اللحظي عبر WebSocket
(Redis Pub/Sub، `broadcast_to_user_redis`) مش جزء من
`CommunicationsService.send_notification()` نفسها إطلاقًا** —
تم التحقق بالكود:

```python
# communications/router.py:89-128 — POST /communications/notifications/send (أدمن فقط)
service = CommunicationsService(db)
notification = await service.send_notification(...)
...
await broadcast_to_user_redis(data.user_id, {...})  # ← هنا بس، جوّه الـrouter، مش جوّه الـservice
```

**البث اللحظي مكتوب جوّه الـrouter handler الخاص بـ`POST
/communications/notifications/send` بس (endpoint إداري محمي
بـ`get_current_superuser`)** — مش جوّه `CommunicationsService.send_notification()`
نفسها. **أي دومين تاني بينادي `send_notification()` مباشرة (زي
`_notify_admins_pending_review` في guardian من قبل، أو transport/
realestate/saas الحاليين) لا يحصل على أي بث WebSocket لحظي إطلاقًا.**

**الأثر العملي على ميزة "رسالة لمدرّس":** لو الـendpoint الجديد استدعى
`CommunicationsService.send_notification()` مباشرة من `GuardianService`
(نفس النمط المُستخدَم في كل الـendpoints السابقة)، المدرّس:
- ✅ هيلاقي صف `Notification` حقيقي محفوظ، متاح عبر `GET
  /communications/notifications/me` (endpoint موجود ومؤكَّد،
  `communications/router.py:134`).
- ❌ **مش هيتبلّغ لحظيًا (لا WebSocket، لا Celery فعلي)** — لازم
  يفتح تطبيقه ويشوف قائمة إشعاراته بنفسه ليكتشف الرسالة.

هذا سلوك **مطابق تمامًا** لكل استدعاءات `send_notification` الحالية
في المشروع (بما فيها تنبيه الأدمنز في guardian نفسها من قبل) — **مش
قصور خاص بهذه الميزة**، لكن يستاهل التوثيق الصريح هنا عشان مايتفاجئش
حد بغياب "push حقيقي".

### بديل موجود لم يُطلَب لكن يستاهل الذكر

`CommunicationsService.send_mail(sender_id, recipient_id, subject,
body_text, ...)` (`communications/service.py:122+`) — نظام بريد داخلي
كامل (threads، mailbox، رد) أقرب مفاهيميًا لـ"رسالة محادثة حقيقية"
من `send_notification` (المصمَّمة أصلًا لتنبيهات نظام أحادية الاتجاه).
**السؤال افترض `send_notification` كخيار محسوم مسبقًا، فالتحقيق ركّز
عليها** — لكن لو المرحلة القادمة (تنفيذ فعلي) تحتاج "محادثة" حقيقية
(رد المدرّس على ولي الأمر مثلًا)، `send_mail` قد يكون أنسب معماريًا.
**قرار خارج نطاق هذه الجلسة القرائية بالكامل.**

---

## 4. صلاحية الوصول — هل VERIFIED كافية، ولا نحتاج فحص إضافي؟

### الفحص الأساسي (نفس نمط `guardian_overview` بالحرف)

نفس الحد الأدنى المطلوب دايمًا: `GuardianRelationship` موجودة، `tenant_id`
مطابق، `status == VERIFIED`. **هذا الفحص إجباري وكافٍ كحد أدنى** —
بلا علاقة موثَّقة، مفيش أي أساس شرعي لولي الأمر يتواصل مع أي حد بخصوص
الطالب.

### فحص إضافي مقترح (مش موجود في `guardian_overview`، خاص بهذه الميزة تحديدًا)

**نعم، فحصان إضافيان محدَّدان لهذه الميزة بالذات — مش "تعقيد إضافي"،
بل **نفس مستوى التحقق المُستخدَم بالفعل** لمنع طلب "اخترع بيانات غير
موجودة":

1. **`GuardianVisibilitySetting` لقطاع `ACADEMY` لازم يكون مرئي**
   (مش محجوب) — قرار تصميمي متّسق مع فلسفة `guardian_overview`
   بالكامل: لو الطالب حجب قطاع الأكاديميا عن وليّ أمره، منطقيًا **ميصحش**
   وليّ الأمر يقدر يتواصل مع مدرّس عن كورس هو أصلًا ممنوع يشوف بياناته.
   هذا **قرار منتجي يحتاج تأكيد صريح من المستخدم**، لكنه الأكثر اتساقًا
   مع القرار السابق في `guardian_overview` (استبعاد القسم كامل لو
   محجوب) — نفس المنطق ينطبق هنا: لو مينفعش تشوف enrollments الطالب،
   منطقيًا ميصحش تعرف مين مدرّس أنهي كورس أصلًا.
2. **`get_enrollment(ward_id, course_id, tenant_id)` لازم يرجّع صف
   حقيقي** — مش فحص "صلاحية" بالمعنى الأمني، لكنه **إلزامي لمنع طلب
   غير منطقي**: لو الطالب مش مسجَّل في الكورس المُرسَل، مفيش "مدرّس
   مسؤول" أصلًا يُرسَل له. هذا يمنع ولي الأمر من تمرير `course_id`
   عشوائي لمراسلة أي مدرّس في المنصة بحجة كاذبة إن ابنه طالب عنده.
3. **`Course.instructor_id` لازم يكون غير `NULL`** — لو الكورس بلا
   مدرّس مُسنَد، الطلب لازم يترفض بوضوح (`NotFoundError` مثلًا)، مش
   إرسال لمستخدم وهمي أو استثناء غامض.

**الخلاصة: `VERIFIED` وحدها كافية أمنيًا كحد أدنى للتفويض العام (نفس
overview)، لكن هذه الميزة بالذات محتاجة تحققين إضافيين محدَّدين
(تسجيل فعلي في الكورس + مدرّس موجود فعليًا) لأسباب منطق العمل، مش
لأسباب صلاحية إضافية — الفحص الأمني الجوهري لسه نفسه بالحرف.** فحص
رؤية `ACADEMY` قرار منتجي مفتوح يحتاج تأكيد المستخدم قبل التنفيذ.

---

## خلاصة الأثر على تصميم `POST /guardian/wards/{ward_id}/message-instructor`

هذه الجلسة تخطيط فقط، بدون قرار تصميم نهائي:

1. **جسم الطلب لازم يشمل `course_id`** (بالإضافة لنص الرسالة) — لا
   يوجد بديل لتحديد "أنهي مدرّس بالظبط" غير كده.
2. **سلسلة الحل**: `get_enrollment(ward_id, course_id, tenant_id)` →
   `get_course(course_id, tenant_id)` → `get_instructor(course.instructor_id,
   tenant_id)` → `instructor.user_id` (المستلم النهائي) — 3 دوال
   موجودة بالفعل، صفر كود جديد مطلوب في `academy/`.
3. **`LiveSession.instructor_id` مُستبعَدة تمامًا** من هذا التصميم —
   `Course.instructor_id` هي مصدر الحقيقة الوحيد.
4. **القناة `IN_APP` = صف `Notification` محفوظ بس، بلا بث لحظي** —
   المدرّس هيحتاج يفتح قائمة إشعاراته بنفسه (`GET
   /communications/notifications/me`). هذا سلوك المشروع الحالي كله،
   مش قصور خاص بالميزة الجديدة.
5. **فحوصات الوصول**: `VERIFIED` (إجباري، أساسي) + تسجيل فعلي في
   الكورس + مدرّس موجود فعليًا (إلزاميان لمنطق العمل) + رؤية `ACADEMY`
   غير محجوبة (**قرار منتجي مفتوح**، يحتاج تأكيد قبل أي تنفيذ).

**التنفيذ الفعلي (service.py/router.py الحقيقيين) يحتاج جلسة تنفيذ
منفصلة بموافقة صريحة**، نفس القاعدة المتَّبعة في كل الجلسات السابقة.
