# تخطيط: تأكيد أخير قبل ربط PROJECT_FUNDING بالمنح التلقائي

**النوع:** فحص read-only بحت — ممنوع أي تعديل كود، ولم يتم تعديل أي ملف.
**التاريخ:** 2026-09-15

---

## الخلاصة المباشرة

1. **الحدث `project.contribution.received` موجود وجاهز بالكامل** —
   `projects/service.py:224-230`. الـpayload: `project_id`, `tenant_id`,
   `contributor_id` (مش `user_id` — الاسم مختلف، لازم يُستخدَم بالحرف
   ده)، `amount`, `contribution_id`. `contributor_id` مؤكَّد = المستخدم
   الحقيقي من JWT (`current_user.id`)، مش placeholder.
2. **مش مُسجَّل كحدث حرج حاليًا** — `project.contribution.received`
   **غايب تمامًا** من `CRITICAL_EVENT_HANDLERS` (اللي فيه بس حدثين
   `academy`). بيتنشر عبر Redis Pub/Sub العادي بس، **بلا** أي مسار
   Celery موثوق. الربط محتاج: (أ) إضافة سطر واحد في
   `CRITICAL_EVENT_HANDLERS`، (ب) handler جديد في `tasks/events.py`،
   (ج) دالة منح في `achievements/service.py` — **صفر تعديل مطلوب على
   `projects/service.py` نفسها** (نفس ميكانيكية `EventBus.publish` اللي
   TRAINING استخدمتها بالضبط، بلا أي فرق).
3. **التكرار وارد فعلًا — وبشكل أوسع بكتير من TRAINING.** مفيش أي قيد
   فريد على مستوى `Contribution` بيمنع نفس المستخدم من المساهمة أكتر
   من مرة في نفس المشروع أو مشاريع مختلفة — القيد الفريد الوحيد
   (`idempotency_key`) قابل للـNull وبيمنع بس تكرار **نفس مفتاح الطلب
   الحرفي**، مش تكرار المساهمة نفسها. **نفس نمط TRAINING بالحرف:**
   إنجاز واحد لأول مساهمة، والقيد الفريد `(user_id, achievement_definition_id)`
   كافي 100%.
4. **⚠️ اكتشاف إضافي مهم (خارج الأسئلة التلاتة، لكن مرتبط مباشرة
   بجاهزية الربط):** الحدث بيتنشر وقت **إنشاء** المساهمة (`status="PENDING"`)،
   **مش** وقت موافقة صاحب المشروع عليها. فيه تدفق منفصل تمامًا
   (`approve_contribution`) بيغيّر الحالة لـ`APPROVED`/`REJECTED`
   — **وده مفيهوش أي `event_bus.publish` إطلاقًا**. يعني لو ربطنا
   PROJECT_FUNDING بالحدث الحالي، الإنجاز هيتمنح لمجرد **تقديم** مساهمة،
   حتى لو صاحب المشروع رفضها بعدين — مفيش أي مسار حاليًا لسحب الإنجاز
   أو حتى معرفة إن المساهمة اتردّت.

---

## 1. نقطة النشر كاملة — `projects/service.py:224-230`

```python
async def add_contribution(
    self,
    contributor_id: int,
    tenant_id: int,
    data,
    idempotency_key: Optional[str] = None
) -> dict:
    ...
    try:
        project = await self.repo.get_project(data.project_id, tenant_id)
        if not project:
            raise NotFoundError("Project not found")
        if project.status != ProjectStatus.FUNDRAISING:
            raise PermissionDeniedError("Project is not accepting contributions")

        eq_val = data.amount_mrusdt or (...)  # حساب القيمة المعادلة حسب نوع المساهمة

        if data.contribution_type == ContributionType.MONETARY:
            finance = FinanceService(self.db, tenant_id)
            ...
            await finance.transfer(sender_id=contributor_id, ...)  # خصم فعلي لو نقدي

        contribution_data = {
            'tenant_id': tenant_id,
            'project_id': project.id,
            'contributor_id': contributor_id,
            'contribution_type': data.contribution_type,
            'equivalent_value_mrusdt': eq_val,
            'status': "PENDING",          # ⚠️ دايمًا PENDING وقت الإنشاء
        }
        ...
        contribution = await self.repo.create_contribution(**contribution_data)

        result = {"id": contribution.id, "status": "PENDING", "equivalent_value_mrusdt": float(eq_val)}
        if redis_key:
            await self.redis.setex(redis_key, 3600, json.dumps(result))

        await self.event_bus.publish("project.contribution.received", {
            "project_id": project.id,
            "tenant_id": tenant_id,
            "contributor_id": contributor_id,
            "amount": float(eq_val),
            "contribution_id": contribution.id
        })

        await invalidate_cache(f"project_analytics_{project.id}")
        return result
```

### تأكيد شكل الـpayload بالضبط

```python
{
    "project_id": project.id,           # int
    "tenant_id": tenant_id,             # int — موجود مباشرة، صريح
    "contributor_id": contributor_id,   # int — ⚠️ اسمه "contributor_id" مش "user_id"
    "amount": float(eq_val),            # float — القيمة المعادلة (نقدي أو محسوبة لعيني)
    "contribution_id": contribution.id, # int
}
```

**لا يوجد مفتاح `user_id` في الـpayload** — الاسم المستخدَم هو
`contributor_id` حصريًا. أي دالة منح مستقبلية (زي `_handle_bootcamp_enrollment_created`/
`_handle_course_completed`) لازم تقرا `payload["contributor_id"]`،
مش `payload["user_id"]` — فرق تسمية بسيط لكن لازم الانتباه له عمليًا
وقت التنفيذ.

### تأكيد مصدر `contributor_id` (تتبّع للخلف حتى الراوتر — إعادة تأكيد)

```python
# projects/router.py:135-147
@router.post("/contributions", response_model=dict, status_code=status.HTTP_201_CREATED)
async def add_contribution(
    request: Request, data: ContributionCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = ProjectService(db)
    user_id = cast(int, current_user.id)
    tenant_id = cast(int, current_user.tenant_id)
    return await service.add_contribution(user_id, tenant_id, data, idempotency_key)
```

**مؤكَّد (تكرار للتأكيد النهائي قبل الربط):** `contributor_id` = `current_user.id`
الحقيقي من الجلسة المصادَق عليها، `tenant_id` = `current_user.tenant_id`
الحقيقي. **صفر تغيير عن الفحص الأصلي** (`achievement-trigger-events-inventory-session-log.md`)
— نفس الكود بالحرف، لسه صحيح 100%.

---

## 2. هل الحدث مُسجَّل كـ"حرج"؟ — لأ، ومحتاج تسجيل صريح

### حالة `CRITICAL_EVENT_HANDLERS` الحالية

```python
# app/core/critical_events.py (بعد جلستي TEAM_BUILDING وTRAINING)
CRITICAL_EVENT_HANDLERS: dict[str, str] = {
    "academy.bootcamp_enrollment.created": "achievements.update_bootcamp_network_stats",
    "academy.course.completed": "achievements.grant_training_achievements_for_course_completion",
}
```

**`project.contribution.received` غايب تمامًا.** يعني حاليًا بيتنشر
عبر `EventBus.publish()` بمسار Redis Pub/Sub العادي بس (أي subscriber
حي وقت النشر بيستقبله، أي حد مش مستمع وقتها بيفوّته نهائيًا) — **بلا**
أي مسار Celery موثوق بـretry.

### هل محتاج أي تعديل في `projects` نفسها؟ — لأ، صفر تعديل

الآلية عامة تمامًا (`app/core/event_bus.py:38-40`):
```python
if event_name in CRITICAL_EVENT_HANDLERS:
    celery_app.send_task("events.dispatch_critical_event",
                          args=[event_name, payload], queue="events")
```

هذا الفحص جوّه `EventBus.publish()` نفسها — بيتفعّل تلقائيًا لأي حدث
اسمه موجود في القاموس، **بغض النظر عن الدومين اللي نشره.** `ProjectService`
بتستخدم بالفعل نفس كلاس `EventBus` (`from app.core.event_bus import
EventBus`) ونفس نمط الاستدعاء (`self.event_bus.publish(...)`) المستخدَم
في `academy`. **يعني الربط الكامل محتاج بس:**
1. سطر واحد جديد في `CRITICAL_EVENT_HANDLERS` (`app/core/critical_events.py`).
2. handler جديد في `app/tasks/events.py` (نفس نمط `_handle_course_completed`
   بالحرف) + تسجيله في `CRITICAL_EVENT_DISPATCH_HANDLERS`.
3. دالة منح جديدة في `achievements/service.py` (نفس نمط
   `grant_training_achievements_for_course_completion` بالحرف —
   `get_auto_grant_definitions(category=PROJECT_FUNDING, trigger_event_name="project.contribution.received")`
   + `grant_achievement_if_not_exists`).

**صفر سطر واحد محتاج يتغيّر في `projects/service.py` أو `projects/router.py`.**

---

## 3. التكرار — وارد فعلًا، وبشكل أوسع بكتير من TRAINING

### هل نفس المستخدم يقدر يساهم أكتر من مرة؟ — أيوه، بلا أي قيد

على عكس `Enrollment` (اللي عليها `UniqueConstraint(user_id, course_id)`
تمنع التسجيل مرتين في نفس الكورس)، **جدول `contributions` مفيهوش أي
قيد مشابه إطلاقًا.** الفحص المباشر لـ`add_contribution` (قسم 1 فوق)
بيأكد: **مفيش أي فحص "هل ساهم قبل كده في المشروع ده؟"** قبل إنشاء
صف `Contribution` جديد. القيد الفريد الوحيد الموجود:

```python
idempotency_key = Column(String(255), unique=True, nullable=True, index=True)
```

ده بيمنع بس **نفس مفتاح الطلب الحرفي** يتكرر (حماية من double-submit
عرضي لنفس الطلب) — **مش** حماية من "نفس المستخدم يساهم تاني بمفتاح
جديد في نفس المشروع أو مشروع مختلف". من ناحية تصميم النظام، ده
**متوقَّع ومطلوب فعليًا** — التمويل الجماعي بطبيعته مبني على إمكانية
المساهمة أكتر من مرة (زيادة المساهمة، أو دعم مشاريع متعددة).

### هل القيد الفريد الموجود كافي؟ — أيوه، بالضبط زي TRAINING

`UserAchievement`'s القيد الفريد (`user_id`, `achievement_definition_id`)
**كافي 100%** لضمان "إنجاز واحد بس لأول مساهمة" — بغض النظر عن كام
مساهمة المستخدم عملها بعد كده (لنفس المشروع أو مشاريع مختلفة)، كل
محاولة منح تانية بعد الأولى هتترفض بصمت عبر نفس آلية
`grant_achievement_if_not_exists` (`INSERT...ON CONFLICT DO NOTHING`)
المستخدَمة بالفعل لـTEAM_BUILDING وTRAINING. **صفر تعديل إضافي على
الـschema أو القيد مطلوب** — نفس الاستنتاج بالحرف اللي وصل له تخطيط
TRAINING، وبنفس المنطق: التعريف عام (مش خاص بمشروع معيّن)، فـ"مساهمة
في مشروع تاني" بترجع لنفس (`user_id`, `achievement_definition_id`)
وتترفض تلقائيًا.

---

## 4. ملحوظة إضافية مهمة — الحدث بيتنشر قبل الموافقة، مش بعدها

اكتشاف مش من ضمن الأسئلة التلاتة المطلوبة صراحة، لكن مباشرة ومهم
لقرار الربط نفسه:

### فيه تدفق موافقة منفصل — بلا أي حدث مقابل

```python
# projects/service.py:247-281
async def approve_contribution(
    self, contribution_id: int, owner_id: int, tenant_id: int,
    approved: bool, notes: Optional[str] = None,
) -> Contribution:
    ...
    status = "APPROVED" if approved else "REJECTED"
    if approved:
        new_funding = project.current_funding_mrusdt + contribution.equivalent_value_mrusdt
        await self.repo.update_project(cast(int, project.id), tenant_id, current_funding_mrusdt=new_funding)

    updated = await self.repo.update_contribution(contribution_id, tenant_id, status=status)
    ...
    await self.db.commit()
    return updated
```

**صفر `event_bus.publish` في `approve_contribution` بالكامل** (grep
مباشر على الدالة — لا يوجد). يعني:

- `project.contribution.received` بيتنشر **فورًا وقت الإنشاء**
  (`status="PENDING"`)، قبل ما صاحب المشروع يشوفها أو يوافق عليها.
- مفيش أي حدث تاني بيتنشر وقت الموافقة الفعلية (`APPROVED`) أو
  الرفض (`REJECTED`).
- **يعني: لو ربطنا PROJECT_FUNDING بالحدث الحالي، الإنجاز هيتمنح لمجرد
  محاولة المساهمة (submit)، مش لمساهمة اتقبلت وعُدّت فعليًا في تمويل
  المشروع.** مساهمة اتقدّمت وبعدين اترفضت من صاحب المشروع هتكون خلاص
  منحت الإنجاز، وصفر مسار حاليًا لسحبه أو حتى لمعرفة إن الرفض حصل.

**ده قرار منتج/معماري محتاج توضيح صريح قبل التنفيذ** (خارج نطاق هذا
الفحص): هل المطلوب فعلًا "أول محاولة مساهمة" (الحدث الحالي مناسب
تمامًا كما هو)، ولا "أول مساهمة **معتمدة فعليًا**" (لازم حدث جديد
يُضاف داخل `approve_contribution` نفسها، مشابه تمامًا للفجوة اللي
كانت موجودة في `academy` قبل الجلسات السابقة)؟

---

## ملخص نهائي للأسئلة الثلاثة

| السؤال | الإجابة المختصرة |
|---|---|
| شكل الـpayload بالضبط؟ | `{project_id, tenant_id, contributor_id, amount, contribution_id}` — **`contributor_id` مش `user_id`**، `tenant_id` موجود مباشرة وصريح. مؤكَّد = `current_user.id`/`current_user.tenant_id` الحقيقيين من الراوتر |
| مُسجَّل كحدث حرج بالفعل؟ | **لأ** — غايب تمامًا من `CRITICAL_EVENT_HANDLERS`. الربط محتاج تسجيل صريح (سطر واحد) + handler جديد + دالة منح — **صفر تعديل على `projects` نفسها**، الآلية عامة بالفعل عبر نفس `EventBus` |
| التكرار والقيد الفريد؟ | التكرار وارد فعلًا وبلا أي قيد يمنعه أصلًا (على عكس `Enrollment`) — متوقَّع بطبيعة التمويل الجماعي. القيد الفريد `(user_id, achievement_definition_id)` كافي 100%، بنفس نمط TRAINING بالحرف: إنجاز واحد لأول مساهمة بس |

**ملحوظة إضافية للنقاش:** الحدث بيتنشر وقت تقديم المساهمة، مش وقت
موافقة صاحب المشروع عليها — قرار محتاج توضيح قبل أي تنفيذ.

هذا التقرير فحص read-only بالكامل — لم يُنفَّذ أي تعديل كود.
