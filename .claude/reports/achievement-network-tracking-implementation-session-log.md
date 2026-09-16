# تنفيذ: نشر حدث بوتكامب في academy + منطق walk-up وتحديث user_network_stats

**النوع:** تنفيذ فعلي (كتابة كود)، متحقَّق منه حيًا بالكامل.
**التاريخ:** 2026-09-15

**النطاق المطلوب صراحة:** (أ) نشر حدث `academy.bootcamp_enrollment.created`
عند تسجيل كورس مرتبط ببوتكامب، (ب) walk-up على `referred_by_user_id` +
تحديث `user_network_stats.bootcamp_network_size`.
**ممنوع صراحة:** أي منح `UserAchievement` تلقائي — لم يُلمَس، مفيش أي
كود بيقرأ `trigger_threshold` أو ينشئ صف إنجاز في هذه الجلسة.

يبني مباشرة على الأساس اللي اتبنى في الجلسة السابقة
(`.claude/reports/achievements-foundation-implementation-session-log.md`)
وعلى بنية Critical Event Dispatch الموجودة من قبل
(`.claude/reports/critical-event-dispatch-infrastructure-implementation-session-log.md`).

---

## 1. حدث جديد في `academy/service.py`

**تأكيد أولي (زي ما اتطلب بالحرف):** الملف مكانش فيه `EventBus` مستورد
أصلًا قبل هذه الجلسة — grep شامل قبل التعديل أكَّد صفر نتائج لـ
`event_bus|EventBus` في الملف.

### الإضافة (نفس نمط `health`/`logistics` بالحرف)

```python
# imports جديدة
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client

# __init__
class AcademyService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = AcademyRepository(db)
        self.finance = FinanceService(db, tenant_id)
        self.event_bus = EventBus(cast(Any, redis_client))   # ← جديد
```

### النشر — نهاية `enroll_in_course`، بعد `commit()` + invalidate cache

```python
await self.db.commit()

await self.repo._invalidate_cache(f"user_enrollments_{user_id}")
await self.repo._invalidate_cache("published_courses")

if course.bootcamp_id is not None:  # type: ignore
    await self.event_bus.publish("academy.bootcamp_enrollment.created", {
        "user_id": user_id,
        "tenant_id": self.tenant_id,
        "course_id": course_id,
        "bootcamp_id": course.bootcamp_id,
    })

return enrollment
```

`course` هو نفس الكائن اللي اتجاب في بداية الدالة (`course =
await self.repo.get_course(course_id, self.tenant_id)`) — لسه في
النطاق، `bootcamp_id` بتاعه اتقرا من كورس منشور فعليًا مش placeholder.
`tenant_id` في الـpayload هو `self.tenant_id` (بارامتر الـconstructor)
— الدالة مالهاش بارامتر `tenant_id` منفصل، نفس النمط المستخدَم في باقي
الدالة (`self.repo.get_enrollment(user_id, course_id, self.tenant_id)`).

**تحقُّق حي (اختبار 1، قسم 6):** النشر بيحصل **بس** لما
`bootcamp_id is not None` — كورس عادي (`bootcamp_id=None`) صفر نشر،
مؤكَّد بالاتجاهين مش افتراض.

---

## 2. `app/core/critical_events.py` — أول قيمة حقيقية

```python
CRITICAL_EVENT_HANDLERS: dict[str, str] = {
    "academy.bootcamp_enrollment.created": "achievements.update_bootcamp_network_stats",
}
```

كان فاضيًا عمدًا من الجلسة السابقة (`critical-event-dispatch-infrastructure`).
القيمة نصية (dotted identifier)، مش import فعلي — نفس النية الأصلية
للملف (تجنّب circular import، `core/critical_events.py` مستورد من
`event_bus.py` اللي 22+ دومين بيستورده).

---

## 3. Walk-up — `app/domains/achievements/service.py` + `repository.py`

### الدالة المطلوبة (نفس التوقيع بالحرف)

```python
async def update_bootcamp_network_stats(
    self, user_id: int, tenant_id: int, max_depth: int = 8,
) -> List[int]:
    updated_user_ids: List[int] = []
    current_id = user_id
    for _ in range(max_depth):
        referrer_id = await self.repo.get_referred_by_user_id(current_id)
        if referrer_id is None:
            break
        await self.repo.increment_bootcamp_network_size(referrer_id, tenant_id)
        updated_user_ids.append(referrer_id)
        current_id = referrer_id

    if updated_user_ids:
        await self.db.commit()

    return updated_user_ids
```

حلقة Python بسيطة (8 تكرارات كحد أقصى، مش CTE — بالضبط زي المطلوب).
استعلام واحد بس لكل مستوى (`get_referred_by_user_id` — `SELECT
referred_by_user_id FROM users WHERE id = ...`، عمود مفهرس)، `tenant_id`
المُمرَّر (مش tenant_id الخاص بكل سلف) هو اللي بيتكتب في صف الإحصاء —
نفس اتفاقية `ReferralTree.tenant_id` الموجودة بالفعل (`= self.tenant_id`
السياقي، مش `referrer.tenant_id`/`referred.tenant_id` الفردي).

### `increment_bootcamp_network_size` — **انحراف مقصود عن الاقتراح الأولي**

الاقتراح الأولي كان `UPDATE ... SET bootcamp_network_size =
bootcamp_network_size + 1` مباشر. **ده كان هيفشل بصمت** — كل صفوف
`user_network_stats` حاليًا صفر (الجدول اتبنى فاضي في الجلسة السابقة،
وده أول كود بيكتب فيه إطلاقًا)، و`UPDATE` وحده بيرجع 0 صفوف متأثرة لو
الصف مش موجود أصلًا، بلا أي خطأ ولا أي تأثير. الحل الفعلي:

```python
async def increment_bootcamp_network_size(self, user_id: int, tenant_id: int) -> None:
    stmt = pg_insert(UserNetworkStats).values(
        user_id=user_id, tenant_id=tenant_id, bootcamp_network_size=1,
    ).on_conflict_do_update(
        index_elements=[UserNetworkStats.user_id],
        set_={
            "bootcamp_network_size": UserNetworkStats.bootcamp_network_size + 1,
            "updated_at": func.now(),
        },
    )
    await self.db.execute(stmt)
```

`INSERT ... ON CONFLICT DO UPDATE` ذرّي — **statement واحد**، مش
`SELECT` ثم `UPDATE` (نفس الروح المطلوبة: صفر race condition)، وبيغطي
الحالتين معًا: إنشاء أول صف لسلف جديد، والتراكم على صف موجود.

---

## 4. ربط الـhandler — `app/tasks/events.py`

```python
def _handle_bootcamp_enrollment_created(payload: dict) -> None:
    from app.core.database import SessionLocal
    from app.domains.achievements.service import AchievementService

    async def _run():
        async with SessionLocal() as db:
            service = AchievementService(db, payload["tenant_id"])
            updated = await service.update_bootcamp_network_stats(
                user_id=payload["user_id"],
                tenant_id=payload["tenant_id"],
            )
            logger.info(f"✅ bootcamp_network_size updated for ancestors: {updated} ...")

    _run_async(_run())


CRITICAL_EVENT_DISPATCH_HANDLERS = {
    "academy.bootcamp_enrollment.created": _handle_bootcamp_enrollment_created,
}


@celery_app.task(name="events.dispatch_critical_event", bind=True, ...)
def dispatch_critical_event_task(self, event_name: str, payload: dict):
    try:
        if event_name in CRITICAL_EVENT_HANDLERS:
            logger.info(f"🔥 Critical event dispatched: {event_name} | payload={payload}")
            handler = CRITICAL_EVENT_DISPATCH_HANDLERS.get(event_name)
            if handler is not None:
                handler(payload)
        else:
            logger.info(f"Critical event dispatch skipped (not registered): {event_name}")
    except Exception as e:
        logger.error(f"❌ Critical event dispatch failed for {event_name}: {str(e)}")
        raise self.retry(exc=e, countdown=60)
```

**قرار تصميمي:** `CRITICAL_EVENT_DISPATCH_HANDLERS` (قاموس جديد
event_name→callable حقيقي) **منفصل عمدًا** عن `CRITICAL_EVENT_HANDLERS`
(القاموس التصريحي event_name→string في `core/critical_events.py`).
السبب: `core/critical_events.py` مستورد من `event_bus.py` اللي 22+
دومين بيستورده مباشرة — أي import فعلي لكود دومين `achievements` هناك
= خطر circular import حقيقي (نفس المشكلة اللي الجلسة السابقة وثّقتها
صراحة وتجنَّبتها بنفس الطريقة). `import AchievementService` الفعلي
موجود **جوّه** `_handle_bootcamp_enrollment_created` (lazy import، مش
على مستوى الملف) — بلا أي خطر استيراد دائري وقت تحميل `app/tasks/events.py`
نفسه (اللي بيتحمَّل مبكرًا عبر `celery_app.autodiscover_tasks(['app.tasks', ...])`).

`_run_async` نسخة محلية جديدة في `events.py` (مش helper مشترك) — نفس
اتفاقية باقي `app/tasks/*.py` (كل ملف بينسخ نسخته، مؤكَّد بـgrep: 9
ملفات تاسكس كل واحد له نسخته الخاصة).

---

## 5. اكتشافان أثناء التنفيذ — إصلاحان فعليان، مش مجرد باجات اختبار

### 5.1 Identity map قديمة بعد Core statement خام

أول تشغيلة لاختبار "التراكم" (تحديث تاني لنفس السلف، توقُّع العداد
يوصل لـ2) فشلت — العداد فضل واقف على 1 رغم إن الـ`INSERT...ON CONFLICT`
اتنفَّذ فعليًا (اتأكَّد بالتنفيذ الفعلي إن الصف اتحدَّث في DB). السبب:
`get_network_stats` كانت بتعمل `select(UserNetworkStats).where(...)`
عادي — لكن الـ`INSERT...ON CONFLICT DO UPDATE` هو **Core statement**
بيتخطّى الـidentity map بالكامل، فأي كائن `UserNetworkStats` كان
اتحمَّل قبل كده لنفس الـsession (من `get_network_stats` الأول) بيفضل في
الـidentity map بقيمته القديمة، والـselect التاني بيرجَّع **نفس الكائن
الكاش القديم**، مش صف جديد بالقيمة المحدَّثة. الإصلاح:

```python
async def get_network_stats(self, user_id: int) -> Optional[UserNetworkStats]:
    result = await self.db.execute(
        select(UserNetworkStats)
        .where(UserNetworkStats.user_id == user_id)
        .execution_options(populate_existing=True)   # ← الإصلاح
    )
    return result.scalar_one_or_none()
```

**ده مش مجرد باج اختبار** — أي كود مستقبلي (مثلًا مرحلة المنح التلقائي
القادمة، لما هتفحص `trigger_threshold` مقابل `bootcamp_network_size`)
لو استخدم `get_network_stats` على نفس الـsession اللي عملت التحديث،
كان هيقرأ قيمة غلط بصمت بلا أي خطأ.

### 5.2 تضارب event loop بين اختبار المسار الكامل والـworker المحاكى

اختبار "المسار الكامل" (`dispatch_critical_event_task.run(event_name,
payload)` من جوّه test نفسه `async def`) فشل **مرتين متتاليتين**:

1. **"Cannot run the event loop while another loop is running"** —
   `_run_async` بتعمل `asyncio.new_event_loop()` + `run_until_complete()`،
   لكن استدعاءها المباشر من جوّه test أصلًا شغّال جوّه loop
   pytest-asyncio بيتعارض. الإصلاح: `await asyncio.to_thread(dispatch_critical_event_task.run,
   event_name, payload)` — تنفيذ في thread منفصل بلا loop مسبق.

2. **"attached to a different loop"** (من `asyncpg`، بعد إصلاح رقم 1) —
   `engine` (في `app/core/database.py`) singleton عام، مشترك بين كل
   الـloops في نفس العملية. الـthread الجديد بـloop جديد طلب اتصال من
   نفس الـpool، والـpool رجَّع اتصال `asyncpg` كان اتعمل أصلًا في loop
   التست الرئيسي — و`asyncpg` connections مرتبطة بـloop بعينه داخليًا،
   فاستخدامها من loop تاني بيفشل. الإصلاح: `await engine.dispose()`
   **قبل** استدعاء الـthread (يضمن اتصالات جديدة تتبني في loop
   الـthread) **وبعده** (يضمن استمرار استخدام `db`/`AsyncSessionLocal`
   في loop التست الرئيسي بأمان). نفس السبب بالحرف الموثَّق في تعليق
   `conftest.py` نفسه (`engine.dispose()` بين كل test لتفادي بالضبط
   المشكلة دي على Windows/`ProactorEventLoop`) — هنا اتطبَّق **داخل**
   نفس الاختبار، مش بين اختبارين.

**⚠️ ملحوظة نطاق:** المشكلة دي محدودة ببيئة الاختبار تحديدًا (استدعاء
`.run()` من جوّه loop تاني شغّال بالفعل في نفس الـthread). **worker
Celery حقيقي في الإنتاج مالوش loop سابق شغّال في الـthread اللي بيعالج
فيه المهمة من الأساس** — فمفيش أي تضارب مماثل متوقَّع هناك. لم يُعدَّل
أي كود إنتاجي عشان الإصلاح ده — الإصلاحين (1) و(2) كلاهما في ملف
الاختبار بس.

---

## 6. اختبار حي — `tests/test_achievement_network_tracking_implementation.py`

DB حقيقية، صفر mock على أي منطق أعمال (الـmock الوحيد: `celery_app.send_task`
نفسها، عشان منسيبش مهمة فعلية معلَّقة في طابور Redis محدش هيستهلكها —
نفس نمط `test_critical_event_dispatch_infrastructure.py`).

**4 اختبارات:**
1. `test_event_registered_as_critical` — تأكيد تسجيل الحدث في
   `CRITICAL_EVENT_HANDLERS` (sync بحت، صفر DB/async).
2. `test_enroll_publishes_event_only_for_bootcamp_course` — spy على
   `event_bus.publish`: كورس عادي → صفر نشر + `send_task` مش بتتنادى؛
   كورس بوتكامب → نشر بـpayload مطابق بالحرف + `send_task` بتتنادى
   بالشكل الصح (`"events.dispatch_critical_event", args=[event_name,
   payload], queue="events"`).
3. `test_update_bootcamp_network_stats_walks_up_referral_chain` —
   سلسلة أ→ب→ج (`referred_by_user_id` مباشر، نفس نمط
   `test_referral_affiliate_unified_system.py`)، تحديث من ج → `[b_id,
   a_id]` مُرجَّعة (الأقرب أولًا)، عداد ب=1 وأ=1، عداد ج=`None` (مش
   سلف لحد)، تحديث تاني → عداد أ يتراكم لـ2.
4. `test_full_dispatch_path_updates_ancestors_network_stats` — المسار
   الكامل end-to-end: سلسلة أ→ب→ج + بوتكامب throwaway + `enroll_in_course`
   حقيقي من ج → الحدث المُلتقَط يتمرر لـ`dispatch_critical_event_task.run(...)`
   (محاكاة worker) → عداد ب وأ اتحدّث فعليًا، ج يفضل `None`.

```
tests/test_achievement_network_tracking_implementation.py::test_event_registered_as_critical PASSED
tests/test_achievement_network_tracking_implementation.py::test_enroll_publishes_event_only_for_bootcamp_course PASSED
tests/test_achievement_network_tracking_implementation.py::test_update_bootcamp_network_stats_walks_up_referral_chain PASSED
tests/test_achievement_network_tracking_implementation.py::test_full_dispatch_path_updates_ancestors_network_stats PASSED
4 passed in 41.40s
```

**تأكيد إضافي (صفر تأثير جانبي على المسارات القديمة):** أعِيد تشغيل
`tests/test_achievements_foundation_implementation.py` (3 اختبارات) +
`tests/test_critical_event_dispatch_infrastructure.py` (5 اختبارات)
منفصلة بعد كل التعديلات — **8/8 لسه PASSED**، بما فيهم الاختبار اللي
بيتأكد إن حدث إنتاجي قديم (`insurance.subscription.created`، مش في
`CRITICAL_EVENT_HANDLERS`) لسه بينشر عادي بلا أي `send_task`.

---

## 7. Regression — تشغيلة كاملة، صفر تأثير جانبي

```
15 failed, 190 passed, 2 xfailed, 253 warnings in 508.36s (0:08:28)
```

**مقارنة مباشرة بالأساس** (جلسة `achievements-foundation-implementation`،
آخر جلسة قبل هذه): `15 failed, 186 passed, 2 xfailed, 250 warnings`.

- `190 = 186 + 4` (الاختبارات الحية الأربعة الجديدة) ✅
- `253 = 250 + 3` (تحذير `DeprecationWarning` من إغلاق Redis لـ3 من
  الـ4 اختبارات الجديدة فقط — `test_event_registered_as_critical`
  سنكرونيزد بحت، مالوش fixture async أو استخدام Redis إطلاقًا) ✅
- **نفس أسماء الـ15 فشل بالحرف** — كلهم pre-existing، موثَّقين مسبقًا،
  لا علاقة لأي واحد فيهم بهذا التعديل. صفر regression جديد.

---

## 8. الملفات

**معدَّلة:**
- `app/domains/academy/service.py` (import `EventBus`/`redis_client` +
  `self.event_bus` في `__init__` + نشر الحدث في `enroll_in_course`)
- `app/core/critical_events.py` (أول قيمة حقيقية في القاموس)
- `app/tasks/events.py` (`CRITICAL_EVENT_DISPATCH_HANDLERS` + `_handle_bootcamp_enrollment_created`
  + `_run_async` محلية + التوجيه داخل `dispatch_critical_event_task`)
- `app/domains/achievements/service.py` (`update_bootcamp_network_stats`)
- `app/domains/achievements/repository.py` (`get_referred_by_user_id`،
  `increment_bootcamp_network_size`، `get_network_stats` — + إصلاح
  `populate_existing`)

**جديدة:** `tests/test_achievement_network_tracking_implementation.py`.

---

## خارج النطاق — لم يُلمَس، بالحرف حسب الطلب

- **أي منح `UserAchievement` تلقائي** — مفيش أي كود بيفحص
  `AchievementDefinition.trigger_threshold` مقابل `bootcamp_network_size`
  بعد كل تحديث، ولا أي استدعاء لـ`grant_achievement` من أي مسار تلقائي.
  `update_bootcamp_network_stats` بترجَّع `updated_user_ids` **معدَّة**
  للاستخدام في فحص العتبات لاحقًا (زي ما اتطلب بالحرف: "يرجع قايمة
  user_ids اللي اتحدّثوا عشان نفحص عتباتهم بعدين") — لكن مفيش أي كود
  فعليًا بيستهلك القيمة المرجَّعة دي في هذه الجلسة.
- أي دومين تاني غير `academy` — مفيش أي حدث `*.bootcamp_enrollment.created`
  تاني ولا أي تعديل على `tourism_sports`/`projects`/غيرهم.
