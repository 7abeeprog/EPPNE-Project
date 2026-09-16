# آلية التنبيهات الموجَّهة (طالب/ولي أمر/إدارة/مدرّس) — جلسة تخطيط (read-only)

**تاريخ:** 2026-09-16
**النطاق:** فحص read-only بحت لتجهيز خطة تصميم آلية تنبيهات موجَّهة لأكثر من
مستلم لنفس الحدث، عبر `academy` + `identity` + `communications`.
**ممنوع أي تعديل كود — تم الالتزام، صفر Edit/Write على كود المشروع.**

---

## 1. هل يوجد مفهوم "ولي أمر" (Parent/Guardian) فعليًا؟

**لا يوجد أي مفهوم Guardian/Parent-of-student قابل للاستخدام، لا في
`academy` ولا في `identity`.**

- بحث شامل عن `parent|guardian|ولي` في `academy/models.py`,
  `academy/service.py`, `academy/schemas.py`: كل المطابقات (3 ملفات) هي
  `parent_id` الخاص بـ`OrganizationEntity` — شجرة **تنظيمية** (فرع/قسم داخل
  الكيان)، غير متعلقة بعلاقة طالب↔ولي أمر إطلاقًا
  (`academy/models.py:37-58`).
- بحث `parent|guardian` في كامل `identity/`: **صفر مطابقة**.
- الأقرب لمفهوم "قرابة" هو عمودان في `User` نفسه
  (`identity/models.py:45-46`):
  ```python
  father_id = Column(BigInteger, nullable=True)
  mother_id = Column(BigInteger, nullable=True)
  ```
  لكن هذان العمودان **بلا `ForeignKey`، بلا `relationship()`، وغير
  مُستخدَمين في أي منطق عمل** — تم التحقق بـ grep على كامل `eppne-backend`:
  المطابقات الوحيدة لـ`father_id`/`mother_id` في كل المشروع هي تعريف العمود
  نفسه في `models.py` وتعريفه في migration الأولية
  (`71820e4fe1f3_initial_migration_all_34_sectors_final.py:105-106`). صفر
  قراءة أو كتابة في أي `service.py`/`router.py`/`schemas.py` عبر كل
  الدومينات. أعمدة ميتة (vestigial) بالكامل.

**الأثر:** لا يوجد أي رابط بيانات (FK مباشر، `EntityMembership`، أو جدول
ربط منفصل) يمكن الاعتماد عليه اليوم لتحديد "من هو ولي أمر الطالب X".
أي تصميم لآلية التنبيهات **لازم يفترض أن هذا الرابط غير موجود بعد** — إما
يُبنى جدول ربط جديد (migration جديدة)، أو تُفعَّل `father_id`/`mother_id`
فعليًا (FK + منطق قراءة)، أو يُطلب تأجيل جمهور "ولي الأمر" لمرحلة تالية.

---

## 2. هل يوجد مفهوم "مدرّس" مربوط بكورس/فصل معيّن؟

**نعم، موجود وقابل للاستنتاج بوضوح — بعكس ولي الأمر.**

- `Instructor` (`academy/models.py:63-81`): سجل منفصل، `user_id` (فريد،
  FK → `users.id`) + `org_entity_id` + `tenant_id`. المدرّب نفسه مستخدم
  عادي بسجل إضافي.
- `Course.instructor_id` (`academy/models.py:157`): FK اختياري →
  `academy_instructors.id` (`ondelete="SET NULL"`) — **كل كورس مربوط
  بمدرّس واحد كحد أقصى** (nullable، يعني ممكن كورس بلا مدرّس مُسنَد).
- `LiveSession.instructor_id` (`academy/models.py:317`): FK **إجباري**
  (`nullable=False`) → `academy_instructors.id` — كل جلسة مباشرة (فصل
  فعلي) لها مدرّس محدد ومُلزَم.
- سلسلة الاستنتاج "مين المدرّس المسؤول عن الطالب ده تحديدًا" فعليًا
  ممكنة عبر جدولين فقط:
  `Enrollment(user_id=<student>, course_id) → Course.instructor_id →
  Instructor.user_id`
  والدوال الجاهزة بالفعل في `repository.py` (`count_instructor_courses`,
  `count_distinct_students_in_instructor_courses`, أسطر 820-862) تؤكد إن
  هذا الـjoin (`Course.instructor_id` + `tenant_id`) نمط مُستخدَم ومختبَر
  بالفعل في الكود، مش افتراض نظري.
- **مؤهَّل أكثر** من مستوى الكورس: لو الحدث خاص بجلسة مباشرة محددة
  (مثلاً غياب عن جلسة)، `LiveSession.instructor_id` بيدّي المدرّس **الفعلي**
  لتلك الجلسة تحديدًا (ممكن يختلف عن `Course.instructor_id` لو تم تفويض
  الجلسة)، وده أدق من الاعتماد على مستوى الكورس فقط.

**ملاحظة جانبية غير مطلوب حلها الآن (side-finding، لا علاقة مباشرة بسؤال
التنبيهات):** `AcademyRepository.create_live_session`
(`academy/repository.py:684-689`) فيه:
```python
if "instructor_id" not in session_data:
    session_data["instructor_id"] = 1
```
قيمة افتراضية hardcoded لمستخدم `instructor_id=1` غير مضمون وجوده — نفس
نمط باج `fleet entity_id=1 hardcoded default` الذي أُصلح سابقًا في
`transport` ([[project_transport_fleet_entity_id_hardcoded_default_fix]]).
لو أي جلسة أُنشئت فعليًا بدون `instructor_id` صريح، أي منطق تنبيه مستقبلي
يعتمد على `LiveSession.instructor_id` سيبعت لمستخدم عشوائي (أو غير
موجود). يُوصى بفتح مهمة منفصلة لهذا الباج قبل الاعتماد على
`LiveSession.instructor_id` كمصدر حقيقة في آلية التنبيهات، تماشيًا مع
[[feedback_split_urgent_side_findings_from_broader_investigation]] — لم
يُلمَس هنا.

---

## 3. `CommunicationsService.send_notification` — مستلم واحد ولا متعدد؟

**مصممة لمستلم واحد فقط، على طول السلسلة الكاملة (Schema → Router →
Service → Celery Task) — بلا أي دعم لقائمة مستلمين.**

- التوقيع (`communications/service.py:42-51`):
  ```python
  async def send_notification(
      self,
      user_id: int,          # ← عدد صحيح واحد، ليس list[int]
      title: str,
      body: str,
      data: Optional[Dict[str, Any]] = None,
      priority: str = NotificationPriority.NORMAL,
      channel: str = NotificationChannel.IN_APP,
      idempotency_key: Optional[str] = None
  ) -> Notification:
  ```
  الدالة بتجيب `tenant_id` **مستخدم واحد** (`_get_user_tenant(user_id)`
  سطر 60)، وبتنشئ **سجل `Notification` واحد** (سطر 66-76)، وبتجدول
  **مهمة Celery واحدة** بمستلم واحد (سطر 81-89). لا يوجد loop داخلي على
  عدة مستخدمين.
- `NotificationCreate` schema (`communications/schemas.py:12-18`): حقل
  `user_id: int` وحيد، **لا يوجد** `user_ids: list[int]` ولا أي بديل جمعي.
- Router (`communications/router.py:89-113`): يمرر `data.user_id` مباشرة
  (مفرد) لـ`service.send_notification`.
- **تأكيد إضافي من كل المستدعين الفعليين الحاليين** (بحث شامل عن
  `send_notification(` في كامل الباك إند): كل استدعاء — `transport/
  service.py:903`, `realestate/service.py:729`, `automation/service.py:
  553`, `saas/service.py:448,536` — يمرر `user_id` مفرد واحد فقط. **صفر
  مكان في المشروع بالكامل حاليًا يبعت نفس الحدث لأكثر من مستخدم دفعة
  واحدة.** أي بث لجمهور متعدد اليوم لازم يتم بـ**استدعاءات متكررة يدوية**
  لنفس الدالة، وحدة بكل `user_id` — الدالة نفسها لا "تدعم" التعدد، هي فقط
  لا تمنع استدعاءها في loop خارجي.

---

## 4. أحداث حرجة موجودة — هل فيه أي حدث متفَق عليه يحتاج بث لجمهور متعدد؟

**الأحداث الحرجة الثلاثة الموثقة رسميًا (`app/core/critical_events.py`)
كلهم أحادي المستلم فعليًا، تم التحقق من كودها مباشرة:**

| الحدث | الـhandler | المستلم |
|---|---|---|
| `academy.bootcamp_enrollment.created` | `update_bootcamp_network_stats` → `_check_and_grant_team_building_achievements` (`achievements/service.py:130-200`) | `ancestor_id` واحد بكل مستوى في سلسلة الإحالة (walk-up)، منح واحد تلو الآخر — ليس بثًا جماعيًا لنفس اللحظة |
| `academy.course.completed` | `grant_training_achievements_for_course_completion` (`achievements/service.py:206-240`) | `user_id` واحد (صاحب الإنجاز) |
| `project.contribution.received` | `grant_project_funding_achievements_for_contribution` (`achievements/service.py:246-...`) | `user_id` واحد (المساهم) |

هذه الأحداث الثلاثة أصلًا **منح إنجازات (Achievements)**، ليست تنبيهات
(`Notification`) بالمعنى الدقيق — لا يوجد استدعاء `send_notification` داخل
أي من الثلاثة handlers (تم التحقق بالقراءة الكاملة). آلية النشر نفسها
(`EventBus.publish`, `app/core/event_bus.py:25-40`) توجّه كل حدث حرج
لـ**مهمة Celery واحدة** (`dispatch_critical_event`) مربوطة بـ**handler واحد**
في `CRITICAL_EVENT_HANDLERS` — البنية التحتية للـEvent Bus نفسها لا تفرّق
بين "مستلم واحد" و"عدة مستلمين"؛ التفريق يحصل داخل الـhandler فقط (هل
بيستدعي منطق مستلم واحد ولا loop).

**لا يوجد أي حدث حرج متفَق عليه رسميًا اليوم في `critical_events.py`
يحتاج بثًا لجمهور متعدد.** "غياب طالب → طالب + ولي أمر + مدرّس" **غير
موجود كحدث في الكود حاليًا** — تم البحث عن `absence|absent|غياب|attendance`
في `academy/service.py`: **صفر مطابقة**. الموديل `LiveAttendance`
(`academy/models.py:333-347`) يسجّل الحضور (join/leave) لكن لا يوجد أي
منطق "غياب" (عدم حضور) مكتوب أو حدث مرتبط به بعد — هذا مثال افتراضي طرحه
السؤال، ليس حدثًا قائمًا فعليًا في الكود.

---

## خلاصة الأثر على تصميم آلية التنبيهات الموجَّهة

هذه الجلسة تخطيط فقط، بدون قرار تصميم — فقط توثيق الفجوات الفعلية التي
لازم أي تصميم يتعامل معها:

1. **جمهور "ولي أمر" غير قابل للتحقيق تقنيًا اليوم** بدون عمل بيانات إضافي
   (لا رابط FK ولا `EntityMembership` ولا جدول ربط) — هذا أكبر blocker.
2. **جمهور "مدرّس" قابل للتحقيق فعليًا** عبر `Course.instructor_id`
   (مستوى الكورس) أو `LiveSession.instructor_id` (مستوى الجلسة، أدق، لكن
   معرَّض لباج hardcoded default غير مُصلَح — راجع قسم 2).
3. **`CommunicationsService.send_notification` تحتاج تعديل توقيع** (أو
   دالة جديدة موازية) لدعم مستلمين متعددين — لا يوجد أي مسار حالي في
   المشروع يفعل ذلك اليوم، سواء على مستوى الـschema أو الـservice أو
   الـCelery task.
4. **لا يوجد سابقة كود فعلية للبث الجماعي** يمكن البناء عليها أو تعميمها
   — أي تصميم جديد سيكون أول تطبيق من نوعه في المشروع، وليس امتدادًا لنمط
   قائم.

**التنفيذ الفعلي (تعديل schema/service لدعم تعدد المستلمين، أو بناء رابط
ولي الأمر) يحتاج جلسة تصميم/موافقة صريحة منفصلة**، نفس القاعدة المتبعة في
كل قرارات معمارية سابقة بالمشروع.
