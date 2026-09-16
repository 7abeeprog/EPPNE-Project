# جرد أحداث EventBus.publish المتاحة كـ triggers لنظام الإنجازات — academy / tourism_sports / projects

**النوع:** فحص read-only بحت — ممنوع أي تعديل كود، ولم يتم تعديل أي ملف.
**التاريخ:** 2026-09-15

---

## الخلاصة المباشرة

| الدومين | عدد أحداث `event_bus.publish(...)` فعليًا | حدث "إكمال تدريب" أو "بناء فريق"؟ |
|---|---|---|
| `academy` | **0** — الملف مالوش `EventBus` مستورد أصلًا | ❌ لا يوجد — ولا حتى مفهوم "إكمال كورس" كحالة صريحة في الكود (تفصيل تحت) |
| `tourism_sports` | **0** — `EventBus` متسمّى (`self.event_bus`) في `__init__` لكن **مالهوش أي استدعاء `.publish()` في الملف كله** — كود ميت | ❌ لا يوجد |
| `projects` | **4** أحداث حقيقية فعليًا منشورة | ✅ `project.contribution.received` هو حدث "مساهمة/استثمار" حقيقي |

**النتيجة الأهم:** من التلات دومينز المطلوب فحصها، **دومين واحد بس (`projects`) بينشر أحداث فعلية فعلاً**. `academy` و`tourism_sports` مفيهمش ولا حدث واحد شغّال حاليًا — أي ربط بنظام الإنجازات بحدث "إكمال كورس" أو "بناء فريق" **محتاج إضافة `event_bus.publish(...)` جديدة بالكامل**، مش مجرد ربط على حدث موجود.

---

## 1. `academy/service.py` — صفر أحداث

grep عن `event_bus|EventBus|publish` في الملف بالكامل: **لا نتائج إطلاقًا**. الملف مالوش `from app.core.event_bus import EventBus` أصلًا، ولا أي إشارة لـ `.publish(`.

### أقرب مفهوم لـ"إكمال تدريب/كورس" موجود في الكود (بدون أي نشر حدث)

من قائمة الدوال الكاملة في `AcademyService`:
```
async def enroll_in_course(...)              # سطر 330 — تسجيل في كورس، مش إكمال
async def get_user_enrollments(...)           # سطر 425
async def update_progress(self, user_id: int, course_id: int, progress: float)  # سطر 428
async def cancel_enrollment(...)               # سطر 436
```

`update_progress` هو أقرب دالة لمفهوم "تقدّم/إكمال" — بتاخد `progress: float` لكن:
- **مفيش أي شرط بيفحص `if progress >= 100`** أو أي منطق "اكتمال" صريح داخلها.
- **مفيش أي `event_bus.publish(...)` بعدها** — مجرد تحديث قيمة، من غير أي حدث يتنشر.

بالإضافة لكده، فيه `submit_quiz` (سطر 283) و`submit_task`/`grade_submission` (سطور 500، 529) — دول أقرب لتقييمات جزئية، برضه من غير أي نشر حدث.

**الخلاصة: لا يوجد أي حدث حاليًا يمثل "إكمال كورس" في `academy`. ولا حتى الحالة نفسها (Course Completed) موجودة كـ state صريح في السيرفس — بس فيه `progress: float` مجرد رقم بيتحدّث من غير trigger.**

---

## 2. `tourism_sports/service.py` — صفر أحداث (كود event_bus ميت)

```python
# سطر 24
from app.core.event_bus import EventBus
...
# سطر 42 (داخل __init__)
self.event_bus = EventBus(cast(Any, redis_client))
```

`EventBus` بيتستورد ويتعمله instantiate في `__init__`، لكن grep شامل عن `\.publish\(` في الملف بالكامل **رجّع صفر نتائج**. يعني `self.event_bus` **موجود كمتغيّر لكن مش مستخدم في أي مكان في الملف** — كود ميت (dead wiring)، مش حتى حدث واحد بيتنشر فعليًا.

### أقرب مفهوم لـ"بناء فريق" (انضمام لاعب لمنظمة رياضية) موجود في الكود

من قائمة الدوال الكاملة في السيرفس:
```
async def create_sports_org(...)        # سطر 371 — إنشاء منظمة رياضية (نادي/فريق)
async def create_player_profile(...)    # سطر 408 — إنشاء بروفايل لاعب (أقرب حاجة لـ"لاعب ينضم")
async def place_transfer_bid(...)       # سطر 443 — عرض انتقال لاعب (transfer) بين أندية
```

الفحص المباشر بيأكد: **ولا واحدة من التلاتة دي بتنشر أي حدث**. `create_player_profile` هو أقرب دالة منطقيًا لـ"لاعب انضم لمنظمة"، و`place_transfer_bid` أقرب لـ"انتقال/بناء فريق"، لكن كلاهما من غير أي `event_bus.publish(...)` بعدهم.

**الخلاصة: لا يوجد أي حدث حاليًا يمثل "بناء فريق" أو "انضمام لاعب" في `tourism_sports` — رغم إن `EventBus` متسمّى في الكلاس، مفيش استخدام فعلي له إطلاقًا.**

---

## 3. `projects/service.py` — 4 أحداث حقيقية (القائمة الكاملة)

grep عن `event_bus\.publish\(` في الملف بالكامل: **4 نتائج مؤكدة**، دي كل الأحداث الموجودة في الدومين، مفيش غيرهم.

### 3.1 `project.published`

الموقع: `add_contribution`... لأ، ده في دالة نشر المشروع (بعد `update_project(..., status=ProjectStatus.FUNDRAISING)`، سطر ~132.

```python
await self.event_bus.publish("project.published", {
    "project_id": project.id,
    "tenant_id": tenant_id,
    "owner_id": owner_id,
    "title": project.title,
    "funding_goal": float(project.funding_goal_mrusdt)
})
```
**user_id مباشر؟** ✅ نعم — `owner_id` (صاحب المشروع). **tenant_id؟** ✅ نعم مباشر.

---

### 3.2 `project.contribution.received` — الحدث المطلوب تأكيده بدقة (المساهمة/الاستثمار)

**اسم الحدث بالظبط:** `"project.contribution.received"` (سطر 224 من `add_contribution`)

```python
await self.event_bus.publish("project.contribution.received", {
    "project_id": project.id,
    "tenant_id": tenant_id,
    "contributor_id": contributor_id,
    "amount": float(eq_val),
    "contribution_id": contribution.id
})
```

**تأكيد مصدر `contributor_id` (تتبّع للخلف حتى الراوتر):**

توقيع الدالة في `service.py`:
```python
async def add_contribution(
    self,
    contributor_id: int,
    tenant_id: int,
    data,
    idempotency_key: Optional[str] = None
) -> dict:
```

استدعاؤها من `router.py` (سطر 135-147):
```python
@router.post("/contributions", response_model=dict, status_code=status.HTTP_201_CREATED)
async def add_contribution(
    request: Request,
    data: ContributionCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    user_id = cast(int, current_user.id)
    tenant_id = cast(int, current_user.tenant_id)
    return await service.add_contribution(user_id, tenant_id, data, idempotency_key)
```

**مؤكد: `contributor_id` = `current_user.id` الفعلي القادم من JWT/session، مش placeholder ولا قيمة افتراضية.**

**user_id مباشر؟** ✅ نعم — `contributor_id` واضح وصريح في الـ payload، وقيمته مأخوذة مباشرة من المستخدم المُصادَق عليه. **tenant_id؟** ✅ نعم مباشر. **مبلغ المساهمة؟** ✅ `amount` (قيمة معادلة نقدية `eq_val`، تشمل مساهمات عينية زي أرض/ساعات عمل بعد تحويلها لقيمة نقدية تقديرية — مش بالضرورة قيمة نقدية حقيقية محوّلة فعليًا لكل الأنواع).

---

### 3.3 `project.milestone.completed`

الموقع: بعد `update_milestone(..., is_completed=True)`، سطر ~337 — **بس بشرط `milestone.funds_to_release > 0`** (لو الـ milestone مالوش أموال مرتبطة، الحدث مبينشرش خالص).

```python
if milestone.funds_to_release > 0:
    await self.event_bus.publish("project.milestone.completed", {
        "project_id": project.id,
        "tenant_id": tenant_id,
        "milestone_id": milestone.id,
        "funds_to_release": float(milestone.funds_to_release)
    })
```

**user_id مباشر؟** ❌ **لا** — الـ payload مفيهوش أي `user_id`/`owner_id`/`completed_by`. لو الهدف منح إنجاز لصاحب المشروع عند إكمال milestone، محتاج تُجاب من `project.owner_id` بشكل منفصل (مش موجودة جاهزة في الـ payload نفسه). **tenant_id؟** ✅ نعم مباشر.

⚠️ **ملحوظة مهمة إضافية:** الحدث ده **مشروط** (`if funds_to_release > 0`) — مش كل milestone بيكتمل بينشر حدث، فمينفعش الاعتماد عليه كـ trigger شامل لكل "إكمال معلم في المشروع".

---

### 3.4 `project.update.added`

الموقع: بعد `create_project_update(...)`، سطر ~415.

```python
await self.event_bus.publish("project.update.added", {
    "project_id": project_id,
    "tenant_id": tenant_id,
    "update_id": update_obj.id,
    "author_id": author_id
})
```

**user_id مباشر؟** ✅ نعم — `author_id`. **tenant_id؟** ✅ نعم مباشر.

---

## جدول التأكيد النهائي — user_id/tenant_id في كل حدث بـ `projects`

| الحدث | user_id مباشر؟ | tenant_id مباشر؟ | ملاحظات |
|---|---|---|---|
| `project.published` | ✅ `owner_id` | ✅ | — |
| `project.contribution.received` | ✅ `contributor_id` (مؤكد = current_user.id من الراوتر) | ✅ | أنسب حدث فعليًا لـ"مساهمة/استثمار" لمنح إنجاز |
| `project.milestone.completed` | ❌ مفيش user_id في الـ payload، وكمان الحدث **مشروط** (`funds_to_release > 0`) | ✅ | يحتاج جلب `owner_id` بشكل منفصل لو هيُستخدم |
| `project.update.added` | ✅ `author_id` | ✅ | — |

---

## توصية للمرحلة التالية (بدون تنفيذ — للنقاش فقط)

- **`projects`** هو الدومين الوحيد الجاهز فعليًا حاليًا لربطه بنظام الإنجازات من غير أي تعديل كود إضافي — وتحديدًا `project.contribution.received` (payload كامل وواضح: `contributor_id` + `tenant_id` + `amount`).
- **`academy`** و**`tourism_sports`**: أي ربط بنظام الإنجازات بحدث "إكمال كورس" أو "بناء فريق" **مش ممكن حاليًا بدون تعديل كود** — لازم إضافة `event_bus.publish(...)` جديدة في نقاط مناسبة (مثلاً داخل `update_progress` بشرط `progress >= 100` في academy، أو داخل `create_player_profile`/`place_transfer_bid` في tourism_sports). ده خارج نطاق الفحص الحالي (read-only) ومحتاج قرار/موافقة منفصلة قبل أي تنفيذ.

هذا القسم توصية فقط — لم يُطلب مني تنفيذ أي تغيير، والنطاق المحدد كان فحص read-only.
