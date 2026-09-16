# تنفيذ: منح UserAchievement تلقائي عند تجاوز عتبة — فئة TEAM_BUILDING

**النوع:** تنفيذ فعلي (كتابة كود)، متحقَّق منه حيًا بالكامل.
**التاريخ:** 2026-09-15

**النطاق المطلوب صراحة:** ربط `update_bootcamp_network_stats` بمنح
`UserAchievement` تلقائيًا عند تجاوز `trigger_threshold` — فئة
`TEAM_BUILDING` تحديدًا.

هذه الجلسة هي **الخطوة الثالثة والأخيرة** لإغلاق دورة الإنجازات
end-to-end لفئة واحدة (`TEAM_BUILDING`)، بعد:
1. `.claude/reports/achievements-foundation-implementation-session-log.md`
   (Migration + الدومين + endpoints إدارية)
2. `.claude/reports/achievement-network-tracking-implementation-session-log.md`
   (حدث academy + walk-up + عداد `user_network_stats`)

---

## ملخص الحالة النهائية لنظام الإنجازات (3 فئات)

| الفئة | الحدث المُشغِّل | الحالة |
|---|---|---|
| **TEAM_BUILDING** | `academy.bootcamp_enrollment.created` | ✅ **مكتمل end-to-end** — حدث ← walk-up ← عداد ← منح تلقائي، كل ده متحقَّق منه حيًا |
| `TRAINING` | لا يوجد | ❌ مفيش حدث "إكمال كورس" حقيقي في `academy` أصلًا (راجع `achievement-trigger-events-inventory-session-log.md` — `update_progress` مجرد رقم، بلا منطق اكتمال ولا نشر حدث) |
| `PROJECT_FUNDING` | `project.contribution.received` (موجود بالفعل) | ❌ الحدث موجود وجاهز، لكن مفيش أي دالة فحص/منح مربوطة بيه لسه |

**الخلاصة:** البنية التحتية (migration، models، `AchievementRepository`/`AchievementService`
العامة، `CRITICAL_EVENT_HANDLERS`/`dispatch_critical_event_task`) عامة
بالكامل وجاهزة للفئتين التانيتين — لكن **صفر ربط فعلي ليهم لسه**. كل
فئة محتاجة نفس النمط المُطبَّق هنا بالحرف: (أ) حدث حقيقي يتنشر من
الدومين المناسب، (ب) تسجيله في `CRITICAL_EVENT_HANDLERS`، (ج) دالة
فحص/منح مشابهة لـ`_check_and_grant_team_building_achievements`.

---

## 1. `app/domains/achievements/repository.py` — 3 تعديلات

### 1.1 `increment_bootcamp_network_size` — بترجّع القيمة الجديدة دلوقتي

```python
async def increment_bootcamp_network_size(self, user_id: int, tenant_id: int) -> int:
    stmt = pg_insert(UserNetworkStats).values(
        user_id=user_id, tenant_id=tenant_id, bootcamp_network_size=1,
    ).on_conflict_do_update(
        index_elements=[UserNetworkStats.user_id],
        set_={
            "bootcamp_network_size": UserNetworkStats.bootcamp_network_size + 1,
            "updated_at": func.now(),
        },
    ).returning(UserNetworkStats.bootcamp_network_size)
    result = await self.db.execute(stmt)
    return result.scalar_one()
```

كانت بترجّع `None` في الجلسة السابقة (مفيش محتاج للقيمة وقتها). دلوقتي
لازم القيمة الجديدة فورًا (لفحص العتبة)، فـ`RETURNING` على نفس الـ
`INSERT...ON CONFLICT` — **مش** استعلام `SELECT` منفصل بعده، لأن ده
كان هيقع بالظبط في نفس مشكلة identity map القديمة اللي اتصلحت الجلسة
اللي فاتت (`get_network_stats.populate_existing`) — الفرق إن
`RETURNING` بيجيب القيمة الحقيقية مباشرة من الـstatement نفسه، بلا أي
مشكلة cache من الأساس.

### 1.2 `get_auto_grant_definitions` — تعريفات مؤهَّلة للمنح التلقائي

```python
async def get_auto_grant_definitions(
    self, tenant_id: int, category: AchievementCategory, trigger_event_name: str,
) -> List[AchievementDefinition]:
    result = await self.db.execute(
        select(AchievementDefinition).where(
            and_(
                AchievementDefinition.tenant_id == tenant_id,
                AchievementDefinition.category == category,
                AchievementDefinition.trigger_event_name == trigger_event_name,
                AchievementDefinition.trigger_type == AchievementTriggerType.AUTO_EVENT,
                AchievementDefinition.is_active == True,
            )
        )
    )
    return list(result.scalars().all())
```

**⚠️ إضافة عن المواصفة الأصلية:** المواصفة ذكرت 3 شروط فقط
(`category=TEAM_BUILDING`, `trigger_event_name=...`, `is_active=True`).
أضفت شرط رابع: **`trigger_type=AUTO_EVENT`**. السبب: الحقل ده موجود في
الموديل بالظبط عشان يميّز بين تعريف "يُمنح يدويًا فقط" (`MANUAL`،
الافتراضي من الجلسة الأولى) و"يُمنح تلقائيًا عند حدث" (`AUTO_EVENT`).
من غير الشرط ده، لو مشرف عمل تعريف `MANUAL` وملأ `trigger_event_name`
عليه بالغلط (أو لأي سبب تاني)، هيتمنح تلقائيًا رغم إن نيته كانت منح
يدوي بس. الـseed الاختباري في هذه الجلسة بيحدّد `trigger_type=AUTO_EVENT`
صراحةً — لو الشرط ده اتشال، الاختبار كان برضه هيعدّي (لأن الـseed
مضبوط صح من الأساس)، لكن السلوك العام للنظام كان هيبقى أضعف.

### 1.3 `grant_achievement_if_not_exists` — منح ذرّي بلا SELECT أول

```python
async def grant_achievement_if_not_exists(
    self, tenant_id: int, user_id: int, achievement_definition_id: int,
    granted_by: Optional[int], source_event_name: Optional[str], source_payload: Optional[dict],
) -> bool:
    stmt = pg_insert(UserAchievement).values(
        tenant_id=tenant_id, user_id=user_id,
        achievement_definition_id=achievement_definition_id,
        granted_by=granted_by, source_event_name=source_event_name,
        source_payload=source_payload,
    ).on_conflict_do_nothing(
        index_elements=[UserAchievement.user_id, UserAchievement.achievement_definition_id],
    ).returning(UserAchievement.id)
    result = await self.db.execute(stmt)
    return result.scalar_one_or_none() is not None
```

بالضبط زي ما اتطلب: `INSERT...ON CONFLICT DO NOTHING`، بلا `SELECT`
أول. `index_elements` بتشاور على نفس عمودي القيد الفريد
`ix_user_achievements_unique_user_definition` (`user_id`,
`achievement_definition_id`) — Postgres بيتعرف عليه كـunique index
موجود بالفعل، مش محتاج اسم constraint صريح. `RETURNING id` بيرجّع
صف واحد لو المنح حصل فعليًا، وصفر صفوف لو كان موجود بالفعل (conflict) —
`scalar_one_or_none()` بيترجم الحالتين لـ`bool` واضح، بلا أي استثناء
في الحالة العادية للتكرار (التكرار متوقَّع تمامًا، مش خطأ).

---

## 2. `app/domains/achievements/service.py`

### `update_bootcamp_network_stats` — إضافة الفحص بعد كل UPDATE ناجح

```python
async def update_bootcamp_network_stats(
    self, user_id: int, tenant_id: int, max_depth: int = 8,
) -> List[int]:
    updated_user_ids: List[int] = []
    current_id = user_id
    ancestor_level = 0
    for _ in range(max_depth):
        referrer_id = await self.repo.get_referred_by_user_id(current_id)
        if referrer_id is None:
            break
        ancestor_level += 1

        new_network_size = await self.repo.increment_bootcamp_network_size(referrer_id, tenant_id)
        updated_user_ids.append(referrer_id)

        await self._check_and_grant_team_building_achievements(
            tenant_id=tenant_id, ancestor_id=referrer_id,
            new_network_size=new_network_size, ancestor_level=ancestor_level,
        )

        current_id = referrer_id

    if updated_user_ids:
        await self.db.commit()

    return updated_user_ids
```

`ancestor_level` بيتتبَّع جوّه نفس حلقة الـwalk-up (1 = الراعي المباشر
للمستخدم اللي عمل الحدث، يزيد بمستوى كل صعدة) — مطلوب لـ`source_payload`.

### `_check_and_grant_team_building_achievements` — الفحص والمنح

```python
async def _check_and_grant_team_building_achievements(
    self, tenant_id: int, ancestor_id: int, new_network_size: int, ancestor_level: int,
) -> None:
    definitions = await self.repo.get_auto_grant_definitions(
        tenant_id=tenant_id,
        category=AchievementCategory.TEAM_BUILDING,
        trigger_event_name=BOOTCAMP_ENROLLMENT_EVENT_NAME,
    )
    for definition in definitions:
        if definition.trigger_threshold is None:
            continue
        if new_network_size < definition.trigger_threshold:
            continue
        await self.repo.grant_achievement_if_not_exists(
            tenant_id=tenant_id, user_id=ancestor_id,
            achievement_definition_id=definition.id, granted_by=None,
            source_event_name=BOOTCAMP_ENROLLMENT_EVENT_NAME,
            source_payload={"network_size": new_network_size, "ancestor_level": ancestor_level},
        )
```

`granted_by=None` دايمًا (منح تلقائي، مفيش مشرف بشري وراه) —
`source_event_name`/`source_payload` مملوءان دلوقتي (عكس المنح اليدوي
من الجلسة الأولى، اللي بيسيبهم `None` دايمًا). `BOOTCAMP_ENROLLMENT_EVENT_NAME`
ثابت محلي جديد في أول الملف (`"academy.bootcamp_enrollment.created"`) —
لتفادي تكرار الـstring literal داخل نفس الملف بس (مش pattern عام في
المشروع، الأحداث التانية كلها strings حرة).

---

## 3. Seed اختباري

```python
await achievement_service.create_definition(
    AchievementDefinitionCreate(
        name="...", description="...",
        category=AchievementCategory.TEAM_BUILDING,
        trigger_type=AchievementTriggerType.AUTO_EVENT,
        trigger_event_name="academy.bootcamp_enrollment.created",
        trigger_threshold=3,   # ← 3 بدل 10، للسرعة والعملية
    ),
    created_by=admin_id,
)
```

---

## 4. اختبار حي — `tests/test_achievement_auto_grant_team_building_implementation.py`

DB حقيقية، صفر mock. سلسلة `referred_by_user_id`: أ→ب→ج→د (أ الجذر،
مالوش راعٍ).

### السيناريو الأساسي

| الحدث | عداد ج | عداد ب | عداد أ | منح أ؟ |
|---|---|---|---|---|
| ب يسجّل في بوتكامب | — | — | 1 | لا |
| ج يسجّل في بوتكامب | — | 1 | 2 | لا |
| **د يسجّل (3⃣)** | 1 | 2 | **3** | **✅ نعم — تلقائيًا** |

بعد التسجيل التالت (د — أ نفسه ملوش داعي يسجّل، تسجيله مش هيزوّد عداد
حد لأنه الجذر): عداد أ يوصل بالظبط 3 = العتبة → أ يتمنح فورًا،
`granted_by=None`, `source_payload={"network_size": 3, "ancestor_level":
3}`. ب (عداده 2) وج (عداده 1) اتفحصوا صراحة — **صفر** إنجاز لأي
منهم (لسه تحت العتبة).

### Idempotency + newly-crossing في نفس الوقت

د يسجّل **تاني** في بوتكامب مختلف (throwaway ثاني):

| بعده | عداد ج | عداد ب | عداد أ |
|---|---|---|---|
| قبل | 1 | 2 | 3 (ممنوح) |
| بعد | 2 | **3** | **4** |

- **أ:** عداده اتزوّد لـ4 (لسه فوق العتبة) — الفحص بيحاول منح تاني،
  لكن `ON CONFLICT DO NOTHING` بيرفضه بصمت. **مؤكَّد صراحة:** نفس
  `UserAchievement.id` الأصلي بالظبط (`a_achievements_after[0].id ==
  granted.id`) — صف واحد، مش اتنين، بلا أي استثناء.
- **ب:** عداده وصل 3 لأول مرة في الجولة دي → **بيتمنح صح** (سلوك
  متوقَّع ومقصود، مش خطأ ولا تكرار) — `granted_by=None`,
  `source_payload={"network_size": 3, "ancestor_level": 2}`.
- **ج:** عداده 2، لسه تحت العتبة — صفر إنجاز.

الاختبار بيفرِّق بوضوح بين الحالتين (منع تكرار لأ، ومنح جديد لسلف
تاني عدّى العتبة لأول مرة) في نفس التشغيلة — تغطية أعمق من مجرد
"idempotency بسيطة".

```
tests/test_achievement_auto_grant_team_building_implementation.py::test_auto_grant_fires_exactly_when_threshold_crossed_and_is_idempotent PASSED
1 passed in 42.98s
```

**تأكيد إضافي (صفر تأثير جانبي من تعديل توقيع `increment_bootcamp_network_size`):**
أعِيد تشغيل 12 اختبار من الجلستين السابقتين (`test_achievements_foundation_implementation.py`
+ `test_achievement_network_tracking_implementation.py` +
`test_critical_event_dispatch_infrastructure.py`) — **12/12 لسه PASSED**.

---

## 5. Regression — تشغيلة كاملة، صفر تأثير جانبي

```
15 failed, 191 passed, 2 xfailed, 254 warnings in 513.33s (0:08:33)
```

**مقارنة مباشرة بالأساس** (جلسة `achievement-network-tracking-implementation`):
`15 failed, 190 passed, 2 xfailed, 253 warnings`.

- `191 = 190 + 1` (الاختبار الحي الجديد) ✅
- `254 = 253 + 1` (تحذير Redis واحد إضافي، الاختبار الجديد بيستخدم
  fixture async/redis) ✅
- **نفس أسماء الـ15 فشل بالحرف** — كلهم pre-existing، لا علاقة لأي
  واحد فيهم بهذا التعديل. صفر regression جديد.

---

## 6. الملفات

**معدَّلة:** `app/domains/achievements/service.py`،
`app/domains/achievements/repository.py`.

**جديدة:** `tests/test_achievement_auto_grant_team_building_implementation.py`.

---

## خارج النطاق — لم يُلمَس، بالحرف حسب الطلب

- **فئة `TRAINING`:** مفيش حدث "إكمال كورس" حقيقي في `academy` أصلًا
  (مؤكَّد مسبقًا في `achievement-trigger-events-inventory-session-log.md`)
  — محتاج إضافة منطق اكتمال (`progress >= 100`) + نشر حدث جديد، قبل
  حتى التفكير في دالة فحص/منح مشابهة.
- **فئة `PROJECT_FUNDING`:** الحدث (`project.contribution.received`)
  موجود وجاهز بالفعل من دومين `projects` — لكن **صفر تسجيل في
  `CRITICAL_EVENT_HANDLERS`** وصفر دالة فحص/منح مربوطة بيه. أقرب فئة
  للتفعيل من الاتنين، لأن الحدث موجود فعلًا.
- **أي تعديل على `dispatch_critical_event_task`/`CRITICAL_EVENT_DISPATCH_HANDLERS`
  نفسها** — نفس البنية الموجودة من الجلسة السابقة استُخدمت كما هي،
  بلا أي تعديل عليها في هذه الجلسة (الفحص/المنح بيحصل **جوّه**
  `update_bootcamp_network_stats` نفسها، اللي أصلًا متسجّلة كـhandler).
