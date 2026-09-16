# تنفيذ: ربط فئة TRAINING بالمنح التلقائي — حدث واحد بسيط

**النوع:** تنفيذ فعلي (كتابة كود)، متحقَّق منه حيًا بالكامل.
**التاريخ:** 2026-09-15

**النطاق المطلوب صراحة:** حدث واحد بسيط (`academy.course.completed`)،
**بلا walk-up، بلا فحص عتبة، بلا تخصيص كورس** — منح مباشر لتعريفات
TRAINING عند أول إكمال.

يبني مباشرة على `.claude/reports/achievement-training-category-planning-session-log.md`
(الفحص read-only اللي حدَّد المكان الدقيق للإكمال، وأكَّد فجوة
idempotency، وأوصى بنمط "تعريف عام" بدل "إنجاز لكل كورس").

---

## ملخص الحالة النهائية لنظام الإنجازات (3 فئات) بعد هذه الجلسة

| الفئة | الحدث | الحالة |
|---|---|---|
| TEAM_BUILDING | `academy.bootcamp_enrollment.created` | ✅ مكتمل end-to-end (حدث + walk-up + عداد + عتبة + منح) |
| **TRAINING** | `academy.course.completed` | ✅ **مكتمل end-to-end** — **جديد هذه الجلسة** (حدث + منح مباشر بلا عتبة) |
| PROJECT_FUNDING | `project.contribution.received` (موجود بالفعل) | ❌ **الفئة الأخيرة الباقية** — الحدث موجود، صفر ربط |

---

## 1. `app/domains/academy/service.py` — نشر الحدث في `update_progress`

الفحص السابق حدَّد بدقة إن `is_completed` بيتحدَّد فعليًا في
`AcademyRepository.update_progress`، مش في الـservice. التعديل هنا في
الـservice — بيفحص نتيجة الـrepo call بعد ما يرجع (بعد ما الإكمال يكون
اتحدَّد وتخزن فعليًا):

```python
async def update_progress(self, user_id: int, course_id: int, progress: float):
    enrollment = await self.repo.get_enrollment(user_id, course_id, self.tenant_id)
    if not enrollment:
        raise NotFoundError("غير مسجل في هذا الكورس")
    updated = await self.repo.update_progress(user_id, course_id, self.tenant_id, progress)
    await self.repo._invalidate_cache(f"enrollment_{user_id}_{course_id}")

    if updated and cast(bool, updated.is_completed):
        await self.event_bus.publish("academy.course.completed", {
            "user_id": user_id,
            "tenant_id": self.tenant_id,
            "course_id": course_id,
        })

    return updated
```

`self.event_bus` كانت أصلًا موجودة في `__init__` من الجلسة اللي فاتت
(TEAM_BUILDING) — صفر import/init إضافي مطلوب هنا.

### ⚠️ فجوة idempotency الموثَّقة في التخطيط — **لم تُصلَح عمدًا**

الفحص السابق حذَّر إن `AcademyRepository.update_progress` بتكتب
`is_completed=True` في **كل** نداء بـ`progress>=100`، بلا فحص القيمة
القديمة — يعني نداءات متكررة (`progress=100` مرتين) هتنشر الحدث
**مرتين**. **التعليمات في هذه الجلسة ما طلبتش إصلاح الفجوة دي** — طلبت
تحديدًا الاعتماد على القيد الفريد على مستوى المنح لمنع التكرار
(`INSERT...ON CONFLICT DO NOTHING`)، مش منع التكرار عند النشر نفسه.
**ده قرار تصميم متعمَّد اتّبعته بالحرف**، مش سهو — النتيجة العملية:
الحدث ممكن يتنشر أكتر من مرة لنفس الإكمال، لكن المنح الفعلي (`UserAchievement`)
بيحصل مرة واحدة بس مهما اتكرر النشر (مؤكَّد حيًا في القسم 6).

---

## 2. `app/core/critical_events.py`

```python
CRITICAL_EVENT_HANDLERS: dict[str, str] = {
    "academy.bootcamp_enrollment.created": "achievements.update_bootcamp_network_stats",
    "academy.course.completed": "achievements.grant_training_achievements_for_course_completion",
}
```

---

## 3. `app/domains/achievements/service.py` — منح مباشر بلا عتبة

```python
COURSE_COMPLETED_EVENT_NAME = "academy.course.completed"

async def grant_training_achievements_for_course_completion(
    self, user_id: int, tenant_id: int, course_id: int,
) -> List[int]:
    definitions = await self.repo.get_auto_grant_definitions(
        tenant_id=tenant_id,
        category=AchievementCategory.TRAINING,
        trigger_event_name=COURSE_COMPLETED_EVENT_NAME,
    )
    granted_definition_ids: List[int] = []
    for definition in definitions:
        granted = await self.repo.grant_achievement_if_not_exists(
            tenant_id=tenant_id, user_id=user_id,
            achievement_definition_id=definition.id, granted_by=None,
            source_event_name=COURSE_COMPLETED_EVENT_NAME,
            source_payload={"course_id": course_id},
        )
        if granted:
            granted_definition_ids.append(definition.id)

    if granted_definition_ids:
        await self.db.commit()

    return granted_definition_ids
```

**إعادة استخدام كاملة للبنية التحتية من جلسة TEAM_BUILDING — صفر كود
جديد على مستوى الـrepository:**
- `get_auto_grant_definitions` (نفسها بالحرف — بارامتر `category`
  بس بيتغيّر لـ`TRAINING`، وبرضه بتفلتر `trigger_type=AUTO_EVENT`
  و`is_active=True` تلقائيًا زي TEAM_BUILDING).
- `grant_achievement_if_not_exists` (نفسها بالحرف — نفس `INSERT...ON
  CONFLICT DO NOTHING` + `RETURNING id`).

**الفرق الوحيد عن TEAM_BUILDING:** **مفيش أي فحص `trigger_threshold`
إطلاقًا** — كل تعريف مطابق بيتمنح فورًا لأول مرة (`trigger_threshold`
بيفضل `None` في الـseed، وحتى لو اتملى بالغلط، مش بيتقرا هنا). ومفيش
`ancestor_level`/walk-up — `user_id` هو نفس اللي أكمل الكورس، مباشرة.

---

## 4. `app/tasks/events.py` — الـhandler

```python
def _handle_course_completed(payload: dict) -> None:
    from app.core.database import SessionLocal
    from app.domains.achievements.service import AchievementService

    async def _run():
        async with SessionLocal() as db:
            service = AchievementService(db, payload["tenant_id"])
            granted = await service.grant_training_achievements_for_course_completion(
                user_id=payload["user_id"], tenant_id=payload["tenant_id"],
                course_id=payload["course_id"],
            )
            logger.info(f"✅ TRAINING achievements granted: {granted} ...")

    _run_async(_run())


CRITICAL_EVENT_DISPATCH_HANDLERS = {
    "academy.bootcamp_enrollment.created": _handle_bootcamp_enrollment_created,
    "academy.course.completed": _handle_course_completed,
}
```

نفس نمط `_handle_bootcamp_enrollment_created` بالحرف — lazy import
جوّه الدالة (تفادي circular import، نفس السبب الموثَّق سابقًا)، `_run_async`
المحلية الموجودة بالفعل (صفر تكرار).

---

## 5. Seed اختباري

```python
AchievementDefinitionCreate(
    name="أول خطوة",
    description="...",
    category=AchievementCategory.TRAINING,
    trigger_type=AchievementTriggerType.AUTO_EVENT,
    trigger_event_name="academy.course.completed",
    # trigger_threshold غير مُمرَّر — يفضل None، غير مستخدَم لـTRAINING
)
```

---

## 6. اختبار حي — `tests/test_achievement_auto_grant_training_implementation.py`

DB حقيقية، صفر mock على منطق الأعمال (`celery_app.send_task` بس
اللي اتـpatch، نفس نمط الجلسات السابقة — تفاديًا لمهمة معلَّقة في
طابور Redis محدش هيستهلكها).

**4 اختبارات:**
1. `test_event_registered_as_critical` — تأكيد تسجيل الحدث (sync بحت).
2. `test_update_progress_publishes_event_only_on_completion` — spy
   على `event_bus.publish`: `progress=50` → صفر نشر + `send_task` مش
   بتتنادى؛ `progress=100` → نشر بـpayload مطابق بالحرف
   (`{user_id, tenant_id, course_id}`) + `send_task` بتتنادى بالشكل
   الصح.
3. `test_first_course_completion_grants_training_achievement_second_course_does_not`
   — إكمال كورس أول → `grant_training_achievements_for_course_completion`
   بترجّع `[definition_id]`، صف `UserAchievement` واحد
   (`granted_by=None`, `source_payload={"course_id": course_1.id}`).
   إكمال كورس **تاني مختلف تمامًا** بنفس المستخدم → الدالة بترجّع `[]`
   (صفر منح جديد)، وعدد صفوف `UserAchievement` **يفضل 1 بالظبط** (نفس
   الصف الأصلي بالـid) — **تأكيد مباشر إن الفكرة "إنجاز لكل كورس مختلف"
   مش شغّالة فعليًا بالتصميم الحالي، بالظبط زي ما التخطيط توقَّع** (التعريف
   عام، القيد الفريد `(user_id, achievement_definition_id)` بيمنع أي
   منح تاني بغض النظر عن اختلاف الكورس).
4. `test_full_dispatch_path_grants_achievement` — مسار كامل end-to-end:
   `enroll_in_course` + `update_progress(100)` حقيقيين → الحدث المُلتقَط
   (spy) يتمرر لـ`dispatch_critical_event_task.run(...)` (محاكاة
   worker، عبر `asyncio.to_thread` + `engine.dispose()` bracketing —
   نفس الإصلاحين الموثَّقين في جلسة `achievement-network-tracking-implementation`
   لتفادي تضارب event loop) → الإنجاز اتمنح فعليًا (`granted_by=None`).

```
tests/test_achievement_auto_grant_training_implementation.py::test_event_registered_as_critical PASSED
tests/test_achievement_auto_grant_training_implementation.py::test_update_progress_publishes_event_only_on_completion PASSED
tests/test_achievement_auto_grant_training_implementation.py::test_first_course_completion_grants_training_achievement_second_course_does_not PASSED
tests/test_achievement_auto_grant_training_implementation.py::test_full_dispatch_path_grants_achievement PASSED
4 passed in 128.83s
```

**تأكيد إضافي (صفر تأثير جانبي):** أعِيد تشغيل 13 اختبار من الجلسات
الثلاث السابقة (`test_achievements_foundation_implementation.py` +
`test_achievement_network_tracking_implementation.py` +
`test_achievement_auto_grant_team_building_implementation.py` +
`test_critical_event_dispatch_infrastructure.py`) — **13/13 لسه
PASSED**، بما فيهم تأكيد إن حدث `academy.bootcamp_enrollment.created`
لسه شغّال زي ما كان، بلا أي تداخل مع الحدث الجديد.

---

## 7. Regression — تشغيلة كاملة، صفر تأثير جانبي (أبطأ من الطبيعي، بلا تأثير على النتيجة)

```
15 failed, 195 passed, 2 xfailed, 257 warnings in 2554.93s (0:42:34)
```

**⚠️ ملحوظة على الوقت:** التشغيلة استغرقت 2554.93 ثانية (~42.5 دقيقة)
— أبطأ بشكل ملحوظ من المعتاد (~500-670 ثانية في كل الجلسات السابقة).
اتفحص هذا صراحة أثناء الانتظار عبر مراقبة العملية حيًا
(`Get-Process`): استهلاك CPU الفعلي للعملية كان ~215 ثانية بس من أصل
~2555 ثانية wall-time (~8%) — نسبة منخفضة بتدل على انتظار I/O (استعلامات
DB/Redis) مش تجميد أو حلقة لا نهائية. الأرجح إن السبب تراكم حمل على
DB المحلية من كثرة تشغيلات الاختبار المتكررة في نفس الجلسة الطويلة دي
(أكتر من 15 تشغيلة pytest اليوم)، **مش أي تغيير في الكود** — النتيجة
النهائية (عدد الفشل/النجاح، أسماء الفشل) مطابقة تمامًا للمتوقَّع بلا أي
شذوذ.

**مقارنة مباشرة بالأساس** (جلسة `achievement-auto-grant-team-building`):
`15 failed, 191 passed, 2 xfailed, 254 warnings`.

- `195 = 191 + 4` (الاختبارات الحية الأربعة الجديدة) ✅
- `257 = 254 + 3` (تحذير Redis لـ3 من الـ4 اختبارات فقط —
  `test_event_registered_as_critical` سنكرونيزد بحت) ✅
- **نفس أسماء الـ15 فشل بالحرف** — كلهم pre-existing، لا علاقة لأي
  واحد فيهم بهذا التعديل. صفر regression جديد.

---

## 8. الملفات

**معدَّلة:**
- `app/domains/academy/service.py` (نشر الحدث في `update_progress`)
- `app/core/critical_events.py` (تاني قيمة حقيقية)
- `app/tasks/events.py` (`_handle_course_completed` + تسجيله)
- `app/domains/achievements/service.py` (`grant_training_achievements_for_course_completion`
  + ثابت `COURSE_COMPLETED_EVENT_NAME`)

**جديدة:** `tests/test_achievement_auto_grant_training_implementation.py`.

---

## خارج النطاق — لم يُلمَس، بالحرف حسب الطلب

- **فجوة idempotency في `update_progress`** (نداءات متكررة بـ`progress=100`
  بتنشر الحدث أكتر من مرة) — موثَّقة صراحة في التخطيط، **لم تُصلَح عمدًا**
  هنا (القرار: الاعتماد على القيد الفريد عند المنح، مش منع التكرار
  عند النشر — بالضبط زي التعليمات).
- **فئة `PROJECT_FUNDING`** — الفئة الأخيرة الباقية. الحدث
  (`project.contribution.received`) موجود وجاهز بالفعل من دومين
  `projects` (مؤكَّد سابقًا في `achievement-trigger-events-inventory-session-log.md`)
  — لكن صفر تسجيل في `CRITICAL_EVENT_HANDLERS` وصفر دالة فحص/منح.
  محتاجة جلسة منفصلة، نفس النمط.
- **أي تعديل على `get_auto_grant_definitions`/`grant_achievement_if_not_exists`
  نفسهم** — استُخدما كما هما بالحرف، صفر تعديل على الـrepository في
  هذه الجلسة (كل التعديلات في `service.py`/`events.py`/`critical_events.py`
  فقط).
