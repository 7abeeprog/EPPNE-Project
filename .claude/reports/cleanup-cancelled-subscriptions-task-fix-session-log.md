# جلسة إصلاح — `cleanup_cancelled_subscriptions_task` (المرحلة أ فقط، بموافقة تصميم صريحة)

**التاريخ:** 2026-09-09

**النطاق:** بناء + إصلاح `cleanup_cancelled_subscriptions_task` فقط —
نطاق ضيق متعمَّد، مش المدى الكامل المذكور في الـdocstring الأصلي.
هذا آخر الأربعة المذكورين في
`.claude/reports/saas-nonexistent-methods-investigation-session-log.md`
(الثلاثة الباقيين — `check_expired_trials_task`,
`generate_monthly_invoices_task`, `send_trial_expiry_reminders_task`
— اتحلوا في جلسات سابقة، راجع `PROGRESS_LOG.md`).

**التصميم المتفق عليه (بموافقة صريحة قبل التنفيذ):** المرحلة الوحيدة
المُنفَّذة الآن: تعطيل `TenantServiceAccess.is_active=False`
للاشتراكات `CANCELLED` بعد 30 يوم من الإلغاء. **بلا أي حذف أو تعمية
لبيانات شخصية** — ده مؤجَّل صراحة لجلسة منفصلة تراجع دومين `privacy`
الموجود.

---

## 1) المشكلة (بَجان متراكبان، بالإضافة لدالة مفقودة بالكامل)

### أ) `TypeError` في الـconstructor

`app/tasks/saas_tasks.py` — `cleanup_cancelled_subscriptions_task`
كانت بتستدعي `SaaSControlService(db)`، بينما الـconstructor الفعلي
(`app/domains/saas/service.py:59`) عندها `tenant_id: int` إجباري بلا
`default` → `TypeError`. نفس نمط الثلاثة المُصلَحين سابقًا.

### ب) دالة `cleanup_cancelled_subscriptions` غير موجودة أصلًا

الكود كان بيستدعي `service.cleanup_cancelled_subscriptions()` معلَّمة
بـ`# type: ignore[attr-defined]` — بحث `grep` شامل قبل البدء أكَّد
غيابها الكامل.

### ج) لا يوجد أي عمود `cancelled_at`

`TenantSubscription` كانت بلا أي عمود يسجّل تاريخ الإلغاء الفعلي —
الحقل الوحيد المتاح كان `updated_at` (يتغيّر لأي تعديل، مش بالضرورة
وقت الإلغاء تحديدًا). هذا وحده كان يمنع أي منطق عتبة زمنية موثوق
("بعد 30 يوم من الإلغاء") بلا بناء عمود جديد أولًا.

---

## 2) الإصلاح

### أ) `app/tasks/saas_tasks.py` — `cleanup_cancelled_subscriptions_task`

```python
service = SaaSControlService(db, 0)
cleaned_count = await service.cleanup_cancelled_subscriptions()
```
(`# type: ignore[attr-defined]` اتشال — الدالة بقت موجودة فعليًا.)
الـdocstring اتعدّل ليوضّح النطاق الحقيقي الضيق (تعطيل وصول فقط، بلا
حذف/تعمية بيانات) بدل الادّعاء الأصلي المضلِّل ("حذف بيانات المستخدمين
وفقاً لسياسة الخصوصية GDPR/PDPL").

### ب) `migrations/versions/048_add_cancelled_at_to_saas_tenant_subscriptions.py`

Migration جديدة، بنفس نمط `046`/`047` (Expand فقط):
```python
def upgrade() -> None:
    op.add_column(
        'saas_tenant_subscriptions',
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        'ix_saas_tenant_subscriptions_cancelled_at',
        'saas_tenant_subscriptions', ['cancelled_at'], unique=False,
    )
```
مُطبَّقة فعليًا على القاعدة الحية (`alembic upgrade head` — نجحت،
`alembic heads` يؤكد `048` هو الـhead الوحيد). **صفر backfill** لأي
صف قديم — اشتراكات `CANCELLED` قبل هذه الـmigration (زي `id=50`،
`tenant_id=1`، الموثَّق مسبقًا في تقرير التحقيق) تفضل `cancelled_at`
NULL. تأكيد حي بعد التطبيق:
```
SELECT id, tenant_id, status, cancelled_at, updated_at
FROM saas_tenant_subscriptions WHERE status='CANCELLED';

 id | tenant_id |  status   | cancelled_at |          updated_at
----+-----------+-----------+--------------+-------------------------------
 50 |         1 | CANCELLED |              | 2026-08-21 01:07:06.813647+00
```

### ج) `app/domains/saas/models.py` — عمود `cancelled_at`

```python
cancelled_at = Column(DateTime(timezone=True), nullable=True)
```
+ `Index("ix_saas_tenant_subscriptions_cancelled_at", "cancelled_at")`
في `__table_args__`.

### د) `app/domains/saas/service.py` — `cancel_subscription` يملأ `cancelled_at`

```python
result = await self.repo.update_subscription(
    subscription_id,
    self.tenant_id,
    status="CANCELLED",
    auto_renew=False,
    cancelled_at=datetime.now(timezone.utc),
)
```
هذا أهم تعديل بنيوي: بدون هذا السطر، أي اشتراك جديد يتلغى من الآن
فصاعدًا كان هيفضل `cancelled_at` NULL برضو، وأي منطق تنظيف مبني على
العمود يفضل ميتًا للأبد. بحث `grep` شامل عن `CANCELLED` في كل
`app/domains/saas/` أكَّد `cancel_subscription` هي **المكان الوحيد**
اللي بيحوّل `TenantSubscription.status` لـ`CANCELLED` (مكان تاني
مشابه — `insurance/service.py:320` — بيلمس `InsuranceSubscription`
موديل مختلف تمامًا، غير مرتبط).

### هـ) `app/domains/saas/repository.py` — `get_cancelled_subscriptions_for_cleanup` الجديدة

```python
async def get_cancelled_subscriptions_for_cleanup(
    self,
    tenant_id: Optional[int] = None,
) -> List[TenantSubscription]:
    threshold = datetime.now(timezone.utc) - timedelta(days=30)
    conditions = [
        TenantSubscription.status == "CANCELLED",
        TenantSubscription.cancelled_at.isnot(None),
        TenantSubscription.cancelled_at <= threshold,
    ]
    if tenant_id is not None:
        conditions.append(TenantSubscription.tenant_id == tenant_id)
    result = await self.db.execute(select(TenantSubscription).where(and_(*conditions)))
    return list(result.scalars().all())
```
بنفس نمط `get_past_due_subscriptions` بالضبط — بلا فلتر `tenant_id`
افتراضيًا (عبر كل المستأجرين)، و`cancelled_at.isnot(None)` يستبعد
الاشتراكات القديمة قبل الـmigration صراحةً (بلا أي fallback على
`updated_at` — القرار موضَّح في §3 أدناه).

### و) `app/domains/saas/service.py` — دالة `cleanup_cancelled_subscriptions` الجديدة

اتضافت بعد `send_trial_expiry_reminders` مباشرة:

```python
async def cleanup_cancelled_subscriptions(self, tenant_id: Optional[int] = None) -> int:
    subscriptions = await self.repo.get_cancelled_subscriptions_for_cleanup(tenant_id)
    disabled_count = 0

    for sub in subscriptions:
        sub_id = cast(int, sub.id)
        sub_tenant_id = cast(int, sub.tenant_id)
        try:
            plan = await self.repo.get_plan_by_id_admin(cast(int, sub.plan_id))
            if not plan or plan.service_id is None:
                continue

            access = await self.repo.get_tenant_service_access(sub_tenant_id, cast(int, plan.service_id))
            if not access or not cast(bool, access.is_active):
                continue

            await self.repo.update_service_access(cast(int, access.id), is_active=False)
            await self.db.commit()
            disabled_count += 1
            logger.info(f"Service access disabled for cancelled subscription {sub_id}")

        except Exception as e:
            logger.error(f"Cleanup cancelled subscription failed: subscription {sub_id} - {str(e)}")

    return disabled_count
```

ملاحظات تصميم:
- **حل الخدمة عبر `plan.service_id`** (الـFK المباشر على
  `ServicePlan`، نفس المستخدَم في `get_active_subscription`) **مش**
  `PlanServiceAccess` many-to-many — الأخيرة pilot دومين `insurance`
  فقط حاليًا (موثَّق في تعليق `get_active_subscription_via_plan_access`
  بالـrepository)، ومعظم الأكواد الموجودة بتعتمد على `service_id`
  المباشر. لو الخطة بلا `service_id` (أصبح nullable من migration
  `046`)، الاشتراك بيتخطى بصمت.
- **صفوف `is_active=False` بالفعل بتتخطى بصمت** ومش بتتعدّ — بيضمن
  `cleaned_count` يعكس "عدد المُعطَّل فعليًا في هذه التشغيلة" مش
  "عدد المرشَّحين"، ويضمن idempotency طبيعية بلا أي حاجة لعمود
  إضافي.
- `try/except` حول كل اشتراك على حدة + `commit()` بعد كل تعطيل ناجح
  على حدة — نفس فلسفة `check_and_expire_trials`.

---

## 3) قرار تصميم مهم — رفض `updated_at` كـfallback لـ`cancelled_at`

التحقيق السابق (`saas-nonexistent-methods-investigation-session-
log.md` §4) كان طرح احتمال استخدام `updated_at` كبديل مؤقت لعمود
`cancelled_at` غير الموجود وقتها. **رُفض هذا صراحةً في هذه الجلسة**:
`updated_at` معرَّف بـ`onupdate=func.now()` — أي تعديل لاحق على
الصف (لأي سبب، مش بالضرورة إلغاء) بيحرّكه. استخدامه كمعيار "30 يوم
من الإلغاء" كان هيفتح احتمال تعطيل وصول تينانت بناءً على تاريخ غير
دقيق. الحل: عمود `cancelled_at` مخصص، يتملى فقط من `cancel_subscription`
نفسها، واشتراكات قديمة بلا قيمة واضحة (`id=50`) **مُستبعدة بالكامل**
من أي معالجة لحد ما يبقى عندهم قيمة حقيقية (يعني: لو حد ألغاها تاني
من خلال مسار موحَّد، أو migration منفصلة بقرار واعٍ لاحقًا).

---

## 4) اختبار حي فعلي — بيانات مزروعة + تشغيلتان (idempotency) + تحقق مستقل

### أ) الزرع

```sql
-- صف TenantServiceAccess جديد (تينانت1/service_id=48، كان غير موجود أصلًا)
INSERT INTO saas_tenant_service_access (tenant_id, service_id, access_level, is_active, created_at, updated_at)
VALUES (1, 48, 'BASIC', true, now(), now())
RETURNING id;  -- → 65

-- اشتراكان CANCELLED (plan_id=48، نفس الخطة المرجعية لكل جلسات saas السابقة)
INSERT INTO saas_tenant_subscriptions (tenant_id, plan_id, status, auto_renew, cancelled_at, start_date, created_at, updated_at)
VALUES
  (1, 48, 'CANCELLED', false, now() - interval '35 days', now(), now(), now()),  -- id=184، لازم يتعطّل
  (16, 48, 'CANCELLED', false, now() - interval '5 days', now(), now(), now())   -- id=185، لازم يفضل زي ما هو
RETURNING id;
```
صف `TenantServiceAccess` لتينانت16/`service_id=48` (`id=2`) كان
**موجود بالفعل مسبقًا** (بيانات حقيقية سابقة من جلسة تانية غير
معروفة) — لم يُلمَس زرعًا، استُخدم كما هو لاختبار "لازم يفضل نشط
لأن اشتراكه لسه حديث (5 أيام)".

### ب) التشغيل الفعلي (تشغيلة 1)

```python
import app.main
from app.tasks.saas_tasks import cleanup_cancelled_subscriptions_task
result = cleanup_cancelled_subscriptions_task.run()
```
**النتيجة الفعلية:**
```
2026-09-08 21:59:06 [INFO] Service access disabled for cancelled subscription 184
2026-09-08 21:59:06 [INFO] ✅ Cancelled subscriptions cleaned: 1 subscriptions.
TASK RESULT: {'status': 'success', 'result': {'status': 'success', 'cleaned_count': 1, 'cleaned_at': '2026-09-08T21:59:06...'}}
```

### ج) التحقق المستقل على القرص (بعد التشغيلة مباشرة)

```sql
SELECT id, tenant_id, service_id, is_active, updated_at
FROM saas_tenant_service_access WHERE id IN (65, 2);

 id | tenant_id | service_id | is_active |          updated_at
----+-----------+------------+-----------+-------------------------------
  2 |        16 |         48 | t         | 2026-08-20 12:32:37.792123+00
 65 |         1 |         48 | f         | 2026-09-08 21:59:05.348402+00
```
**النتيجتان المتوقَّعتان تمامًا:** `id=65` (اشتراك عمره 35 يوم) اتعطّل
فعليًا (`is_active=f`, `updated_at` اتغيّر). `id=2` (اشتراك عمره 5
أيام، بيانات حقيقية سابقة) **لم يُلمَس إطلاقًا** (`is_active=t`,
`updated_at` بلا تغيير — نفس القيمة القديمة تمامًا).

### د) تشغيلة 2 — idempotency

```
TASK RESULT: {'status': 'success', 'result': {'status': 'success', 'cleaned_count': 0, ...}}
```
صفر تعديل إضافي — الدالة بتتخطى `id=65` (بقى `is_active=False`
بالفعل) بصمت.

### هـ) التنظيف

```sql
DELETE FROM saas_tenant_subscriptions WHERE id IN (184,185);
DELETE FROM saas_tenant_service_access WHERE id = 65;
```
تحقُّق بعدي:
```sql
SELECT id, tenant_id, plan_id, status, cancelled_at FROM saas_tenant_subscriptions WHERE status='CANCELLED';
-- → صف واحد فقط: id=50, cancelled_at NULL (بلا تغيير)

SELECT id, tenant_id, service_id, is_active, updated_at FROM saas_tenant_service_access WHERE tenant_id=16 AND service_id=48;
-- → id=2, is_active=t, updated_at=2026-08-20 12:32:37 (تمامًا زي قبل الجلسة)
```
صفر أثر متبقٍّ في القاعدة الحية من هذا الاختبار.

---

## 5) Regression — كل اختبار موجود يلمس `SaaSControlService`/`TenantSubscription`

```
tests/test_financeservice_tenant_binding_fix.py
tests/test_insurance_getter_endpoints_wiring.py
tests/test_referral_affiliate_unified_system.py
tests/test_saas_active_subscription.py
tests/test_saas_cancel_subscription_silent_write.py
tests/test_transport_vehicles_fleets_drivers.py
tests/test_trigger_renewals_endpoint_missing_commit.py
```
تشغيل السبعة معًا: **21 نجحوا، 7 فشلوا.**

**فشلان معروفان مسبقًا** (`test_saas_active_subscription.py`):
`test_realestate_rent_unit_saas_check_passes`,
`test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug`
— بَج fixture/`realestate` موثَّق مسبقًا في `PROGRESS_LOG.md`، لا
علاقة له بهذه الجلسة.

**خمسة فشول جديدة مكتشَفة** (`test_transport_vehicles_fleets_drivers.py`):
`test_list_vehicles_tenant_isolation_and_fleet_filter`,
`test_update_vehicle_sanitizes_and_isolates_tenant`,
`test_list_fleets_tenant_isolation`,
`test_update_and_soft_delete_fleet`,
`test_list_drivers_active_only_and_tenant_isolation` — كلهم بنفس
السبب: `IntegrityError` في `teardown` الـfixture:
```
sqlalchemy.exc.IntegrityError: ForeignKeyViolationError:
update or delete on table "saas_service_plans" violates foreign key
constraint "saas_plan_service_access_plan_id_fkey"
DETAIL: Key (id)=(105) is still referenced from table "saas_plan_service_access".
[SQL: DELETE FROM saas_service_plans WHERE saas_service_plans.service_id = $1]
```
**مؤكَّد غير ناتج عن تعديلات هذه الجلسة:**
- `git status` (قبل وبعد كل التعديلات) يُظهر صفر لمس لأي ملف تحت
  `app/domains/transport/` أو `tests/test_transport_*`.
- القيد المخالَف (`saas_plan_service_access_plan_id_fkey`
  `ondelete='RESTRICT'`) جاي من migration `047` — موجودة أصلًا على
  `main` **قبل بدء هذه الجلسة**، غير مرتبطة بـ`cancelled_at` أو
  `cleanup_cancelled_subscriptions` إطلاقًا.
- الكود المتغيّر فعليًا في هذه الجلسة (4 ملفات فقط):
  `app/tasks/saas_tasks.py`, `app/domains/saas/service.py`,
  `app/domains/saas/repository.py`, `app/domains/saas/models.py`
  + migration `048` الجديدة.

**صفر regression ناتج عن التعديلات هنا.** الفشول الخمسة الجديدة
موثَّقة كـbacklog منفصل تحت (على الأرجح fixture الخاص بـ`transport`
بيحاول يمسح `saas_service_plans` بترتيب غلط بالنسبة لقيد `RESTRICT`
المُضاف في `047` — احتمال إن `transport` fixture اتبنى/اتعدَّل بعد
`047` بلا مراعاة القيد الجديد).

---

## 6) الملفات المعدَّلة

- `app/tasks/saas_tasks.py` — `cleanup_cancelled_subscriptions_task`:
  تصحيح الـconstructor، إزالة `# type: ignore[attr-defined]`، تعديل
  الـdocstring ليعكس النطاق الضيق الفعلي.
- `app/domains/saas/models.py` — عمود `cancelled_at` جديد على
  `TenantSubscription` + index.
- `app/domains/saas/service.py` — `cancel_subscription` يملأ
  `cancelled_at` وقت الإلغاء + دالة `cleanup_cancelled_subscriptions`
  الجديدة بالكامل.
- `app/domains/saas/repository.py` — دالة
  `get_cancelled_subscriptions_for_cleanup` الجديدة.
- `migrations/versions/048_add_cancelled_at_to_saas_tenant_subscriptions.py`
  — migration جديدة (مُطبَّقة فعليًا على القاعدة الحية).
- `PROGRESS_LOG.md` — إدخال جديد يوثِّق الإصلاح (الإدخال القديم لم
  يُعدَّل — سياسة المشروع append-only).

**صفر تعديل** على أي ملف `transport` أو `realestate` — الفشول
الموجودة في تلك الدومينات غير مرتبطة وموثَّقة كـbacklog منفصل فوق.

---

## 7) الحالة النهائية

| البند | الحالة |
|---|---|
| `cleanup_cancelled_subscriptions_task` — المرحلة أ (تعطيل service access) | ✅ **اتحلت بالكامل واتأكدت حيًا** |
| المرحلة ب (تعمية بيانات شخصية، PDPL/GDPR) | 🔴 **مؤجَّلة عمدًا** — تحتاج جلسة تصميم منفصلة تراجع دومين `privacy` |
| `test_transport_vehicles_fleets_drivers.py` fixture teardown FK violation (5 اختبارات) | 🔴 **backlog جديد مكتشَف في هذه الجلسة** — غير مرتبط، يحتاج فحص مستقل |

**الأربعة الأصليون من تقرير الفحص (`saas-nonexistent-methods-
investigation-session-log.md`) اتحلوا جميعًا الآن** (كلٌّ في جلسة
منفصلة، آخرهم هذه الجلسة).
