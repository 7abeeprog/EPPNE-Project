# تنفيذ: ربط فئة PROJECT_FUNDING بالمنح التلقائي — حدث موجود بالفعل

**النوع:** تنفيذ فعلي (كتابة كود)، متحقَّق منه حيًا بالكامل.
**التاريخ:** 2026-09-15

**النطاق المطلوب صراحة:** ربط `project.contribution.received` (حدث
موجود بالفعل من قبل في دومين `projects`) بمنح تلقائي لفئة
PROJECT_FUNDING — **بلا أي تعديل على `projects` نفسها**.

يبني مباشرة على `.claude/reports/achievement-project-funding-category-planning-session-log.md`
(الفحص read-only اللي أكَّد شكل الـpayload بالضبط، وحذَّر من فرق
تسمية `contributor_id`/`user_id`، وأكَّد إن الحدث مش مُسجَّل كحرج
لسه).

**🎉 هذه الجلسة الأخيرة تُقفل نظام الإنجازات بالكامل — 3/3 فئات
مكتملة end-to-end (تفصيل كامل في القسم 7).**

---

## 1. `app/core/critical_events.py`

```python
CRITICAL_EVENT_HANDLERS: dict[str, str] = {
    "academy.bootcamp_enrollment.created": "achievements.update_bootcamp_network_stats",
    "academy.course.completed": "achievements.grant_training_achievements_for_course_completion",
    "project.contribution.received": "achievements.grant_project_funding_achievements_for_contribution",
}
```

سطر واحد إضافة فقط. **صفر تعديل على `projects/service.py` أو
`projects/router.py`** — الآلية عامة بالفعل (نفس تأكيد التخطيط): الفحص
`if event_name in CRITICAL_EVENT_HANDLERS` جوّه `EventBus.publish()`
نفسها (`app/core/event_bus.py:38`) بيتفعّل تلقائيًا لأي حدث اسمه
موجود في القاموس، بغض النظر عن الدومين اللي نشره. `ProjectService`
بتستخدم نفس كلاس `EventBus` بالفعل.

---

## 2. `app/domains/achievements/service.py` — منح مباشر بلا عتبة

```python
CONTRIBUTION_RECEIVED_EVENT_NAME = "project.contribution.received"

async def grant_project_funding_achievements_for_contribution(
    self, user_id: int, tenant_id: int, contribution_id: int, project_id: int,
) -> List[int]:
    definitions = await self.repo.get_auto_grant_definitions(
        tenant_id=tenant_id,
        category=AchievementCategory.PROJECT_FUNDING,
        trigger_event_name=CONTRIBUTION_RECEIVED_EVENT_NAME,
    )
    granted_definition_ids: List[int] = []
    for definition in definitions:
        granted = await self.repo.grant_achievement_if_not_exists(
            tenant_id=tenant_id, user_id=user_id,
            achievement_definition_id=definition.id, granted_by=None,
            source_event_name=CONTRIBUTION_RECEIVED_EVENT_NAME,
            source_payload={"project_id": project_id, "contribution_id": contribution_id},
        )
        if granted:
            granted_definition_ids.append(definition.id)

    if granted_definition_ids:
        await self.db.commit()

    return granted_definition_ids
```

**إعادة استخدام كاملة للبنية التحتية من TEAM_BUILDING/TRAINING — صفر
كود جديد على مستوى الـrepository:**
- `get_auto_grant_definitions` (نفسها بالحرف — `category=PROJECT_FUNDING`
  بس بيتغيّر، وبرضه بتفلتر `trigger_type=AUTO_EVENT` و`is_active=True`
  تلقائيًا).
- `grant_achievement_if_not_exists` (نفسها بالحرف — نفس `INSERT...ON
  CONFLICT DO NOTHING` + `RETURNING id`).

نفس نمط `grant_training_achievements_for_course_completion` بالحرف —
مفيش أي فحص `trigger_threshold`، منح فوري لأول مرة.

---

## 3. `app/tasks/events.py` — الـhandler (تطبيق مباشر لتحذير التخطيط)

```python
def _handle_contribution_received(payload: dict) -> None:
    from app.core.database import SessionLocal
    from app.domains.achievements.service import AchievementService

    async def _run():
        async with SessionLocal() as db:
            service = AchievementService(db, payload["tenant_id"])
            granted = await service.grant_project_funding_achievements_for_contribution(
                # ⚠️ الـpayload المصدر (projects/service.py) بيستخدم
                # "contributor_id" مش "user_id" — راجع تقرير التخطيط.
                user_id=payload["contributor_id"],
                tenant_id=payload["tenant_id"],
                contribution_id=payload["contribution_id"],
                project_id=payload["project_id"],
            )
            logger.info(f"✅ PROJECT_FUNDING achievements granted: {granted} ...")

    _run_async(_run())


CRITICAL_EVENT_DISPATCH_HANDLERS = {
    "academy.bootcamp_enrollment.created": _handle_bootcamp_enrollment_created,
    "academy.course.completed": _handle_course_completed,
    "project.contribution.received": _handle_contribution_received,
}
```

**التفصيل الحرج اللي التخطيط حذَّر منه:** payload المساهمة بيستخدم
`contributor_id`، **مش** `user_id` (على عكس حدثي `academy` الاتنين).
`_handle_contribution_received` بتقرا `payload["contributor_id"]`
صراحة وتمررها كـ`user_id` للدالة العامة — لو اتقرا `payload["user_id"]`
بالغلط، كانت هتطلع `KeyError` فورًا (مفيش أي مفتاح بهذا الاسم في
الـpayload الحقيقي)، والحدث كله كان هيفشل بصمت (بعد retry×3 من
`dispatch_critical_event_task`). اتفادي الباج ده مباشرة بفضل تقرير
التخطيط.

---

## 4. Seed اختباري

```python
AchievementDefinitionCreate(
    name="أول مساهمة",
    description="...",
    category=AchievementCategory.PROJECT_FUNDING,
    trigger_type=AchievementTriggerType.AUTO_EVENT,
    trigger_event_name="project.contribution.received",
    # trigger_threshold غير مُمرَّر — يفضل None، غير مستخدَم
)
```

---

## 5. اختبار حي — `tests/test_achievement_auto_grant_project_funding_implementation.py`

DB حقيقية، صفر mock على منطق الأعمال (`celery_app.send_task` بس
اللي اتـpatch). المساهمات استخدمت `ContributionType.LABOR_HOURS`
عمدًا (مش `MONETARY`) — بيتفادى تمامًا مسار `FinanceService.transfer`،
فمش محتاجين رصيد محفظة حقيقي للاختبار.

**4 اختبارات:**
1. `test_event_registered_as_critical` — تأكيد تسجيل الحدث + تأكيد
   القيمة الحرفية `"project.contribution.received"`.
2. `test_add_contribution_publishes_event_with_contributor_id_key` —
   تأكيد مباشر إن الـpayload المنشور فيه `contributor_id` **ومفيهوش**
   `user_id` إطلاقًا (`assert "user_id" not in payload`)، ومطابقة
   الـpayload بالكامل بالحرف + تأكيد شكل استدعاء `celery_app.send_task`.
3. `test_first_contribution_grants_achievement_second_project_does_not`
   — مساهمة أولى في مشروع 1 → `grant_project_funding_achievements_for_contribution`
   بترجّع `[definition_id]`، صف `UserAchievement` واحد
   (`granted_by=None`, `source_payload={"project_id": ..., "contribution_id": ...}`).
   مساهمة **في مشروع 2 مختلف تمامًا** بنفس المستخدم → الدالة بترجّع
   `[]`، وعدد صفوف `UserAchievement` **يفضل 1 بالظبط** — **نفس نتيجة
   TRAINING بالحرف، ومؤكَّد بالتنفيذ الفعلي مش افتراض**: نفس المستخدم
   يقدر يساهم في عدد غير محدود من المشاريع (مفيش أي قيد يمنعه، على
   عكس `Enrollment`)، لكن الإنجاز العام بيتمنح مرة واحدة بس.
4. `test_full_dispatch_path_grants_achievement` — مسار كامل end-to-end:
   `add_contribution` حقيقي → الحدث المُلتقَط (spy) يتمرر لـ
   `dispatch_critical_event_task.run(...)` (محاكاة worker، عبر
   `asyncio.to_thread` + `engine.dispose()` bracketing — نفس الإصلاحين
   الموثَّقين من جلسة `achievement-network-tracking-implementation`) →
   الإنجاز اتمنح فعليًا.

```
tests/test_achievement_auto_grant_project_funding_implementation.py::test_event_registered_as_critical PASSED
tests/test_achievement_auto_grant_project_funding_implementation.py::test_add_contribution_publishes_event_with_contributor_id_key PASSED
tests/test_achievement_auto_grant_project_funding_implementation.py::test_first_contribution_grants_achievement_second_project_does_not PASSED
tests/test_achievement_auto_grant_project_funding_implementation.py::test_full_dispatch_path_grants_achievement PASSED
4 passed in 89.79s
```

**تأكيد إضافي (صفر تأثير جانبي):** أعِيد تشغيل 17 اختبار من الجلسات
الأربع السابقة (`achievements_foundation`، `network_tracking`،
`auto_grant_team_building`، `auto_grant_training`،
`critical_event_dispatch_infrastructure`) — **17/17 لسه PASSED**.

---

## 6. Regression — تشغيلة كاملة، صفر تأثير جانبي

```
15 failed, 199 passed, 2 xfailed, 260 warnings in 1175.88s (0:19:35)
```

**⚠️ ملحوظة على الوقت:** أبطأ من الأساس التاريخي (~500-670 ثانية)
لكن أسرع من الجلسة السابقة مباشرة (2554.93 ثانية) — نفس التفسير
(حمل نظام تراكمي من كتر تشغيلات pytest المتتالية في نفس الجلسة
الطويلة دي، مش أي تغيير في الكود). النتيجة نفسها مطابقة تمامًا للمتوقَّع.

**مقارنة مباشرة بالأساس** (جلسة `achievement-auto-grant-training`):
`15 failed, 195 passed, 2 xfailed, 257 warnings`.

- `199 = 195 + 4` (الاختبارات الحية الأربعة الجديدة) ✅
- `260 = 257 + 3` (تحذير Redis لـ3 من الـ4 اختبارات فقط) ✅
- **نفس أسماء الـ15 فشل بالحرف** — كلهم pre-existing، لا علاقة لأي
  واحد فيهم بهذا التعديل. صفر regression جديد.

---

## 7. 🎉 نظام الإنجازات بالكامل — 3/3 فئات مكتملة end-to-end

| الفئة | الحدث | Handler | الحالة |
|---|---|---|---|
| TEAM_BUILDING | `academy.bootcamp_enrollment.created` | `update_bootcamp_network_stats` (walk-up + عداد + عتبة) | ✅ مكتمل |
| TRAINING | `academy.course.completed` | `grant_training_achievements_for_course_completion` (مباشر بلا عتبة) | ✅ مكتمل |
| **PROJECT_FUNDING** | `project.contribution.received` | `grant_project_funding_achievements_for_contribution` (مباشر بلا عتبة) | ✅ **مكتمل — جديد هذه الجلسة** |

### الرحلة الكاملة (6 جلسات تنفيذية + 3 جلسات تخطيط read-only، كلها بتاريخ 2026-09-15)

1. `achievements-foundation-implementation` — Migration 054 + الدومين
   الكامل + 4 endpoints إدارية يدوية.
2. `achievement-network-tracking-implementation` — أول حدث حقيقي
   (`academy.bootcamp_enrollment.created`) + walk-up + عداد
   `user_network_stats`.
3. `achievement-auto-grant-team-building` — ربط العداد بالمنح التلقائي
   (أول فئة عتبة-محورة).
4. (تخطيط) `achievement-training-category-planning` — تحديد دقيق
   لمكان "إكمال الكورس" + تحذير idempotency.
5. `achievement-auto-grant-training` — أول فئة منح مباشر بلا عتبة.
6. (تخطيط) `achievement-project-funding-category-planning` — تأكيد
   شكل payload + تحذير `contributor_id`/`user_id`.
7. `achievement-auto-grant-project-funding` — **هذه الجلسة**، الفئة
   الأخيرة.

**صفر regression عبر كل الجلسات الست التنفيذية.** إجمالي 21 اختبار حي
جديد (3+4+1+4+4 عبر الجلسات + هذه الـ4) كلهم PASSED باستمرار عبر كل
إعادة تشغيل لاحقة.

### نطاق مستقبلي معروف (مش التزام حالي — مجرد توثيق لما هو مفتوح)

- **فجوة idempotency في `AcademyRepository.update_progress`** (موثَّقة
  صراحة في تخطيط TRAINING) — نداءات متكررة بـ`progress=100` بتنشر
  `academy.course.completed` أكتر من مرة. اتقرر صراحة عدم إصلاحها
  (الحماية عند المنح كافية).
- **ملحوظة "الحدث بيتنشر قبل الموافقة" لـPROJECT_FUNDING** (موثَّقة في
  تخطيط الجلسة دي) — `project.contribution.received` بيتنشر وقت
  التقديم (`PENDING`)، مش وقت موافقة صاحب المشروع. اتقرر صراحة
  الاعتماد على الحدث الحالي كما هو.
- **صفر واجهة مستخدم** — لا لوحة عرض إنجازات، لا إشعارات عند المنح،
  لا استخدام فعلي لـ`icon_url` (مُعرَّف في الـschema من الجلسة الأولى،
  بس مفيش أي عرض بصري له بعد).
- **صفر تسلسل/مستويات للإنجازات** (Bronze/Silver/Gold وغيره) — كل
  تعريف مستقل بعتبته الخاصة لو وُجدت.

---

## 8. الملفات

**معدَّلة:**
- `app/core/critical_events.py` (تالت قيمة حقيقية)
- `app/tasks/events.py` (`_handle_contribution_received` + تسجيله)
- `app/domains/achievements/service.py`
  (`grant_project_funding_achievements_for_contribution` + ثابت
  `CONTRIBUTION_RECEIVED_EVENT_NAME`)

**لم تُلمَس إطلاقًا:** `app/domains/projects/*.py` (بالحرف زي ما
اتطلب — "بلا أي تعديل على projects").

**جديدة:** `tests/test_achievement_auto_grant_project_funding_implementation.py`.
