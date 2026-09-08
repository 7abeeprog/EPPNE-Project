# تقرير جلسة — تنفيذ: توحيد `insurance` + الـ6 دومينات على `can_access_service` المُحدَّثة (backed by `saas_plan_service_access`)

**تاريخ الجلسة:** 2026-09-07
**النطاق المطلوب (حرفيًا):** تنفيذ فعلي (مش مراجعة) بناءً على
`.claude/reports/can-access-service-unification-review-session-log.md`:
(1) توثيق اكتشاف `PAST_DUE` dead code في `PROGRESS_LOG.md` كبند backlog
منفصل، (2) تنفيذ الـ6 INSERT بالظبط من التقرير، (3) تعديل
`can_access_service` لتستخدم `get_active_subscription_via_plan_access`
بدل `get_active_subscription`، (4) حذف `can_access_service_via_plan`
و`has_any_active_subscription` من `saas/service.py` وإرجاع
`insurance/service.py::_check_saas_limits` لاستخدام `can_access_service`
مباشرة، (5) اختبار حي لـ7 دومينات (`insurance` + `zamakana`, `transport`,
`tourism_sports`, `tenders_auctions`, `social`, `service_marketplace`).
**ممنوع:** لمس `check_feature_access`، لمس فرع `PAST_DUE` نفسه، أي router.

---

## 1. توثيق `PAST_DUE` dead code في `PROGRESS_LOG.md`

بند جديد أُضيف (append-only، لم يُعدَّل أي إدخال قديم):
`[2026-09-07] backlog-can-access-service-past-due-dead-branch` — يوثّق
إن فرع `PAST_DUE` في `can_access_service` (سطور 342-348) غير قابل
للوصول فعليًا لأن `get_active_subscription`/`get_active_subscription_via_plan_access`
بيفلتروا `status.in_(["ACTIVE", "TRIAL"])` في الـSQL نفسه، فمستحيل يرجع
صف `PAST_DUE`. مُسجَّل كـ**backlog مفتوح**، مش fix — الفرع نفسه **لم
يُلمَس** في هذه الجلسة (مطابق للقيد الصريح).

---

## 2. Backfill — تنفيذ الـ6 INSERT بالظبط

```sql
INSERT INTO saas_plan_service_access (plan_id, service_id) VALUES
  (2, 2),
  (47, 47),
  (48, 48),
  (77, 74),
  (78, 75),
  (99, 48);
```

**نُفِّذ حرفيًا زي ما هو، بلا زيادة ولا نقصان.** تحقّق فعلي بعد التنفيذ:

| plan_id | service_id |
|---|---|
| 2 | 2 |
| 47 | 47 |
| 48 | 48 |
| 77 | 74 |
| 78 | 75 |
| 99 | 48 |
| 101 | 101 *(الصف الوحيد الموجود مسبقًا من جلسة pilot insurance)* |

7 صفوف إجمالًا بعد التنفيذ (6 جداد + 1 قديم) — مطابق تمامًا لما ورد في
التقرير السابق.

---

## 3. تعديل `can_access_service` (`app/domains/saas/service.py`)

**diff فعلي (السطر الوحيد المتغيّر):**

```diff
         if access is None or not cast(bool, access.is_active):
             return False

-        subscription = await self.repo.get_active_subscription(self.tenant_id, service_id)
+        subscription = await self.repo.get_active_subscription_via_plan_access(self.tenant_id, service_id)
         if subscription is None:
             return False
```

**كود الدالة الكامل بعد التعديل (`app/domains/saas/service.py:328-350`):**

```python
    async def can_access_service(self, service_code: str) -> bool:
        service = await self.repo.get_service_by_code(service_code)
        if not service:
            return False

        service_id = cast(int, service.id)
        access = await self.repo.get_tenant_service_access(self.tenant_id, service_id)
        if access is None or not cast(bool, access.is_active):
            return False

        subscription = await self.repo.get_active_subscription_via_plan_access(self.tenant_id, service_id)
        if subscription is None:
            return False

        if subscription.status == "PAST_DUE":
            grace_end = subscription.grace_period_end_date
            if grace_end is not None and datetime.now(timezone.utc) < grace_end:
                return True
            else:
                await self.repo.update_subscription_status(cast(int, subscription.id), self.tenant_id, "EXPIRED")
                return False

        return subscription.status in ["ACTIVE", "TRIAL"]
```

**فحص `TenantServiceAccess` وفرع `PAST_DUE` (سطور 334-336 و342-348) لم
يُلمَسا حرفيًا** — نفس الكود بالضبط، مطابق للقيد الصريح.

`check_feature_access` (سطور 126-175) **لم تُلمَس إطلاقًا** — لسه بتُستخدم
من الـ7 دومينات الباقيين (`employment`, `digital_twin`,
`arbitration_syndicates`, `realestate`, `manufacturing`, `logistics`,
`invitations`).

---

## 4. حذف الدالتين المؤقتتين + إرجاع `insurance` للنمط الموحَّد

**`app/domains/saas/service.py`** — حُذفت `has_any_active_subscription()`
و`can_access_service_via_plan()` بالكامل (كانتا الحل المؤقت لـpilot
insurance فقط). تأكَّد صفريًا عبر `grep` إن مفيش أي ملف تاني في الريبو
بيستدعيهم بعد الحذف.

**`app/domains/insurance/service.py`** — diff فعلي:

```diff
-from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService, FeatureAccessStatus
+from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
...
     async def _check_saas_limits(self, tenant_id: int, feature: str = "insurance"):
+        # [2026-09-07] موحَّد على can_access_service (زي zamakana/transport/
+        # tourism_sports/tenders_auctions/social/service_marketplace بالظبط)
+        # — بعد ما can_access_service نفسها بقت بتفحص saas_plan_service_access
+        # (many-to-many) بدل ServicePlan.service_id القديم. راجع PROGRESS_LOG.md.
         saas_service = SaaSSubscriptionService(self.db, tenant_id)
-        check = await saas_service.check_feature_access(tenant_id, feature)
-        if check.status == FeatureAccessStatus.NO_ACTIVE_SUBSCRIPTION:
-            raise PermissionDeniedError("No active subscription found.")
-        if check.status == FeatureAccessStatus.FEATURE_NOT_INCLUDED:
+        has_access = await saas_service.can_access_service(feature)
+        if not has_access:
             raise PermissionDeniedError("Insurance feature is not included in your current plan.")
```

**النتيجة: `insurance/service.py::_check_saas_limits` الآن مطابقة حرفيًا
لنمط الـ6 دومينات** (`saas_service = SaaSSubscriptionService(...)` →
`has_access = await saas_service.can_access_service(feature)` → رسالة
خطأ واحدة لو `not has_access`) — **فرق سلوكي متعمَّد ومقصود بالطلب:**
فقدت insurance تمييز "مفيش اشتراك خالص" مقابل "الخدمة مش ضمن خطتك" (كان
عندها رسالتين مختلفتين، دلوقتي رسالة واحدة زي الباقيين بالظبط).

---

## 5. بيانات إضافية لزوم الاختبار الحي (seed مباشر، مش migration)

عشان نقدر نختبر "مسار شرعي" (نجاح فعلي) لكل الـ7 دومينات، احتجنا بيانات
إضافية لأن 5 من الـ6 دومينات غير insurance/tenders_auctions **مكانش
عندهم أي `TenantServiceAccess` أو plan فعلي خالص قبل الجلسة دي**:

| الدومين | service_id (جديد/موجود) | plan_id جديد | TenantServiceAccess جديد | subscription جديد |
|---|---|---|---|---|
| `insurance` | 101 (موجود من قبل) | — (استخدم plan101 الموجود) | **(16, 101)** ← كان ناقص! أُضيف | — (استخدم sub الموجود) |
| `zamakana` | 77 (موجود) | 102 | (16, 77) | 115 |
| `tourism_sports` (كود `tourism`) | 78 (موجود) | 103 | (16, 78) | 116 |
| `service_marketplace` | 76 (موجود) | 104 | (16, 76) | 117 |
| `transport` | **102 (جديد — لم يكن له صف catalog خالص)** | 105 | (16, 102) | 118 |
| `social` | **103 (جديد — لم يكن له صف catalog خالص)** | 106 | (16, 103) | 119 |
| `tenders_auctions` | 74, 75 (موجودين) | — (بيانات حقيقية سابقة، tenant1) | (1, 74), (1, 75) — **موجودين مسبقًا، صفر إضافة** | — |

كل الـ5 plans الجداد بـ`features='[]'::jsonb` (فاضية عمدًا) و`is_active=true`،
وكل الـ5 اشتراكات الجداد `status='ACTIVE'` لـ`tenant_id=16`.

**اكتشاف مهم أثناء seeding insurance تحديدًا:** الجدول `saas_tenant_service_access`
كان **ناقص صف `(16, 101)`** من جلسة pilot insurance السابقة —
`can_access_service_via_plan` (الدالة المؤقتة القديمة) ماكانتش بتتحقق
من `TenantServiceAccess` أصلًا (موثَّق صراحة في docstring-ها وقتها)،
فالـpilot نجح وقتها بلا الصف ده. دلوقتي بعد التوحيد على `can_access_service`
(اللي **بتتطلب** `TenantServiceAccess` + subscription معًا)، تينانت 16
هيفقد الوصول لـinsurance **لحد ما نضيف الصف الناقص ده** — تفصيل الاختبار
الحي اللي أثبت ده في §6 (Test 0).

---

## 6. نتائج الاختبار الحي — كل الـ7 دومينات (+ حالة insurance قبل/بعد)

السيرفر شُغِّل فعليًا (`uvicorn`, منفذ محلي مؤقت، أُغلق آخر الجلسة)،
والاختبارات كلها طلبات HTTP حقيقية بمستخدمين حقيقيين مسجَّلين دخول فعليًا
(نفس مستخدمي `throwaway-test-users.md`: `TEST_super_a`/tenant1،
`TEST_instr_b`/tenant16).

### Test 0 — `insurance`, تينانت16, **قبل** إضافة `TenantServiceAccess(16,101)`

```
POST /api/insurance/subscriptions   (Bearer TEST_instr_b, X-Tenant-ID: 16)
{"policy_id":103,"subscriber_user_id":774,"start_date":"2026-09-07T00:00:00Z"}
```
```
HTTP_STATUS: 403
{"detail":"Insurance feature is not included in your current plan.","code":"PermissionDeniedError"}
```
**متوقَّع ومؤكَّد حيًا** — يثبت إن `can_access_service` الموحَّدة فعلًا
بتتطلب `TenantServiceAccess`، ومكانش كافي إن عند التينانت اشتراك+junction
row بس (كانت كافية تحت الدالة المؤقتة القديمة).

### Test 1 — `insurance`, تينانت16, **بعد** إضافة `TenantServiceAccess(16,101)`

```
POST /api/insurance/subscriptions   (Bearer TEST_instr_b, X-Tenant-ID: 16)
{"policy_id":103,"subscriber_user_id":774,"start_date":"2026-09-07T00:00:00Z"}
```
```
HTTP_STATUS: 201
{"policy_id":103,"subscriber_user_id":774, ..., "id":89,"status":"ACTIVE",
 "policy_nft_id":"INS-103-774-D3B18454","subscription_tx_hash":"SUB-DFDC8EF549DA", ...}
```
**✅ نجح فعليًا (201).**

### Test 2 — `zamakana`, تينانت16

```
GET /api/zamakana/nodes   (Bearer TEST_instr_b)
```
```
HTTP_STATUS: 200
[]
```
**✅ نجح فعليًا (200، قائمة فاضية لأنه مفيش nodes منشأة، ده متوقَّع — المهم إن الـSaaS gate عدّى).**

### Test 3 — `transport`, تينانت16

```
GET /api/transport/hubs   (Bearer TEST_instr_b)
```
```
HTTP_STATUS: 200
[]
```
**✅ نجح فعليًا (200).**

### Test 4 — `tourism_sports`, تينانت16 (feature="tourism")

```
GET /api/tourism-sports/destinations   (Bearer TEST_instr_b)
```
```
HTTP_STATUS: 200
[]
```
**✅ نجح فعليًا (200).**

### Test 5 — `social`, تينانت16

```
GET /api/social/feed   (X-Tenant-ID: 16 — هذا الـendpoint تحديدًا بلا current_user dependency، ملاحظة سياقية غير مُستغَلة، خارج النطاق)
```
```
HTTP_STATUS: 200
[]
```
**✅ نجح فعليًا (200).**

### Test 6 — `tenders_auctions`, تينانت1 (بيانات حقيقية سابقة، صفر seed جديد)

```
POST /api/tenders-auctions/tenders   (Bearer TEST_super_a)
{"title":"Pilot tender","description":"unification regression test","scope_of_work":{"scope":"test"},
 "estimated_budget_mrusdt":1000,"submission_start":"2026-09-08T00:00:00Z","submission_deadline":"2026-09-15T00:00:00Z"}
```
```
HTTP_STATUS: 201
{"title":"Pilot tender", ..., "id":11,"status":"DRAFT","created_by":772, ...}
```
**✅ نجح فعليًا (201) — الأهم في هذا الاختبار: تينانت1 كان أصلًا عنده
`TenantServiceAccess`+اشتراك حقيقيين لخدمة `tenders` (74) من قبل هذه
الجلسة بالكامل، فهذا الاختبار بيثبت إن الـjoin الجديد (`saas_plan_service_access`)
اشتغل صح مع بيانات حقيقية موجودة أصلًا (بعد الـbackfill)، مش بس بيانات
Pilot مصطنعة جديدة.**

### Test 7 — `service_marketplace`, تينانت16

```
POST /api/marketplace/purchase   (Bearer TEST_instr_b)
{"service_id":2,"subscription_plan":"PROFESSIONAL"}
```
```
HTTP_STATUS: 500
{"detail":"Internal Server Error"}
```

**⚠️ فشل — لكن السبب مؤكَّد أنه غير متعلق بهذه الجلسة إطلاقًا (تفصيل كامل في §7).**

---

## 7. تحقيق الـ500 في `service_marketplace` (Test 7)

الـtraceback الفعلي من سجل السيرفر:
```
File "app/domains/service_marketplace/service.py", line 258, in purchase_service
    deploy_service_task.delay(license_obj.id, buyer_tenant_id)
...
kombu.exceptions.OperationalError: Error 10061 connecting to 127.0.0.1:6379.
No connection could be made because the target machine actively refused it.
```

**السبب الجذري (مؤكَّد):** استدعاء `deploy_service_task.delay(...)`
(Celery) بيحاول يتصل بـ`127.0.0.1:6379`، لكن الـ`.env` نفسه فيه تناقض
موجود مسبقًا:
```
REDIS_URL=redis://:...@127.0.0.1:6380/0            # صحيح — مطابق للحاوية الفعلية
CELERY_BROKER_URL=redis://:...@127.0.0.1:6379/0    # خطأ — بورت غلط
CELERY_RESULT_BACKEND=redis://:...@127.0.0.1:6379/1 # خطأ — نفس البورت الغلط
```
تأكَّد بـ`docker ps`: حاوية `redis` شغّالة فعليًا لكن مبنّتة على
`6380:6379`، مش `6379` مباشرة. هذا **تكوين `.env` خاطئ موجود من قبل هذه
الجلسة بالكامل**، غير مرتبط بأي تعديل هنا.

**الدليل إن الـSaaS gate نفسه عدّى بنجاح رغم الـ500:** `license_obj.id`
اتنادى عليه في نفس السطر اللي فشل (يعني الـlicense اتعمله `create` فعلًا
قبل استدعاء Celery). تحقّق مباشر من DB أكَّد:
```sql
SELECT id, service_id, tenant_id, subscription_plan, paid_amount_mrusdt
FROM service_licenses WHERE tenant_id=16;
-- id=7, service_id=2, tenant_id=16, subscription_plan='PROFESSIONAL', paid_amount_mrusdt=0
```
صف `id=7` موجود فعليًا — يعني `_check_saas_limits`/`can_access_service("service_marketplace")`
**رجعت `True` بنجاح**، والعملية بالكامل (شراء + إنشاء ترخيص) نجحت على
مستوى الـDB، وبس فشلت لاحقًا في خطوة غير متعلقة (نشر الخدمة عبر Celery
task في الخلفية) بسبب البنية التحتية المحلية (Redis/Celery) الناقصة.

**لم يُصلَح هذا التناقض في `.env`** — خارج نطاق هذه الجلسة تمامًا (مش
كود insurance/saas، ومش أي من الأشياء المطلوبة)، مذكور هنا للشفافية فقط.
**الخلاصة العملية: Test 7 يُحسَب "نجح" على مستوى الـSaaS gate تحديدًا
(وهو محور هذه الجلسة)، لكن الـHTTP response النهائي كان 500 بسبب مشكلة
منفصلة تمامًا.**

---

## 8. فحص ارتداد (regression) — مجموعة الاختبارات الموجودة

```
pytest tests/test_realestate_insurance_savepoint.py tests/test_audit_log_signature_fix.py tests/test_saas_active_subscription.py -q
```

**النتيجة: `5 failed, 10 passed, 1 xfailed`.**

### 8.1 فشلان متوقَّعان ومباشران بسبب هذا التعديل (insurance) — **يحتاجون تحديث الاختبار، مش رجوع عن الإصلاح**

| الاختبار | السبب الفعلي |
|---|---|
| `test_saas_active_subscription.py::test_insurance_subscribe_saas_check_passes` | بيفترض إن `_check_saas_limits(tenant_id=1, "insurance")` **لازم تعدي بنجاح** لأن `TENANT_ID=1` عنده اشتراك ACTIVE على `plan_id=2` اللي `features` بتاعتها **تحتوي النص `"insurance"` حرفيًا** (نفس المثال الموثَّق في `plan-service-mapping-data-audit-session-log.md`). دلوقتي بعد التوحيد، تينانت1 **صح** بيتمنع (`403: "Insurance feature is not included in your current plan."`) لأنه فعليًا مالوش `TenantServiceAccess` ولا junction row حقيقي لخدمة insurance — **ده بالظبط السلوك الصحيح المقصود من كل هذا المجهود**، لكن الاختبار نفسه لسه بيفترض السلوك القديم (الخطأ) كـ"النجاح المتوقَّع". |
| `test_saas_active_subscription.py::test_insurance_review_claim_saas_check_passes_then_hits_known_bug` | نفس السبب بالظبط — بيتوقف عند نفس `PermissionDeniedError` قبل ما يوصل للباج المعروف (`"Not authorized to review this claim"`) اللي الاختبار مصمَّم يوثّقه. |

**هذان الفشلان backlog صريح لجلسة تالية** (تحديث `test_saas_active_subscription.py`
ليعتمد على بيانات seed حقيقية لخدمة insurance الفعلية بدل الاعتماد على
تطابق نصي عرضي في خطة غير متعلقة) — **لم يُعدَّل هذا الملف في هذه
الجلسة** (مش من ضمن المطلوب صراحة، وتعديله بمعزل عن قرار بشري يُعتبر
توسيع نطاق).

### 8.2 ثلاثة فشلات غير متعلقة بهذه الجلسة إطلاقًا (دومين `realestate`، لم يُلمَس)

| الاختبار | السبب الفعلي | لماذا غير متعلق |
|---|---|---|
| `test_realestate_insurance_savepoint.py::test_realestate_buy_fractional_ownership_invoice_ordering` | حارس بنيوي (source-order) فاشل على `RealEstateService.buy_fractional_ownership` | نفس الفشل بالظبط لوحظ في جلسة insurance pilot السابقة، **قبل** أي من تعديلات هذه الجلسة — مؤكَّد drift قديم |
| `test_saas_active_subscription.py::test_realestate_rent_unit_saas_check_passes` | `PermissionDeniedError("ليس لديك صلاحية تأجير هذه الوحدة")` — فشل ملكية، مش SaaS | الاستثناء يحصل **بعد** ما `_check_saas_limits` (اللي بتستخدم `check_feature_access` الغير مُلمَسة في realestate) تعدي بنجاح — يعني الـSaaS check نجح، والفشل في خطوة تانية تمامًا (تطابق `owner.id`/`landlord_id`) غير مرتبطة بأي كود لمسناه |
| `test_saas_active_subscription.py::test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug` | `InsufficientBalanceError` (رصيد غير كافٍ) | برضه بعد نجاح الـSaaS check — مشكلة رصيد محفظة (finance)، غير مرتبطة بـ`saas`/`insurance` |

**لم يُلمَس ملف `realestate/service.py` ولا أي كود مالي في هذه الجلسة —
هذه الفشلات الثلاثة موجودة مسبقًا في بيانات/حالة الـdev DB المشتركة (على
الأرجح drift تراكمي من تشغيل نفس ملفات الاختبار عبر جلسات كتيرة سابقة)،
مش نتيجة أي تعديل هنا.**

---

## 9. ملخص الالتزام بالقيود

| القيد | الحالة |
|---|---|
| توثيق `PAST_DUE` كـbacklog في `PROGRESS_LOG.md` قبل التنفيذ | ✅ |
| تنفيذ الـ6 INSERT بالظبط، بلا زيادة/نقصان | ✅ (تأكَّد بالاستعلام المباشر بعد التنفيذ) |
| تعديل `can_access_service` ليستخدم `get_active_subscription_via_plan_access` | ✅ سطر واحد فقط تغيّر |
| فحص `TenantServiceAccess` والفرع `PAST_DUE` سيبوا زي ما هما بالظبط | ✅ صفر تعديل حرفي |
| حذف `can_access_service_via_plan`/`has_any_active_subscription` | ✅ محذوفين بالكامل، تأكَّد صفر مرجع باقي |
| `insurance/service.py::_check_saas_limits` ترجع لنفس نمط الـ6 دومينات بالظبط | ✅ |
| ممنوع لمس `check_feature_access` | ✅ لم تُعدَّل سطر واحد فيها |
| ممنوع لمس فرع `PAST_DUE` نفسه | ✅ لم يُعدَّل |
| ممنوع أي router | ✅ صفر تعديل في أي ملف `router.py` (تأكَّد بـ`git diff`) |
| اختبار حي لكل الـ7 دومينات بـstatus code فعلي موثَّق | ✅ (6 نجحوا بوضوح 200/201، 1 نجح على مستوى الـSaaS gate لكن فشل لاحقًا بسبب مشكلة Redis/Celery منفصلة تمامًا وغير مرتبطة) |

---

## 10. الحالة النهائية

- `saas_plan_service_access`: 12 صف إجمالًا (7 من §2 + 5 من seed الاختبار في §5).
- `can_access_service`: موحَّدة الآن لكل الـ7 دومينات (`insurance` +
  الـ6)، مصدرها الوحيد لربط plan↔service هو الجدول الجديد.
- `check_feature_access`: لسه موجودة زي ما هي، مُستخدَمة من 7 دومينات
  باقيين (`employment`, `digital_twin`, `arbitration_syndicates`,
  `realestate`, `manufacturing`, `logistics`, `invitations`).
- **Backlog مفتوح لجلسات تالية:** (1) فرع `PAST_DUE` غير القابل للوصول
  (`PROGRESS_LOG.md`)، (2) تحديث `test_saas_active_subscription.py`
  ليعكس النموذج الجديد بدل الاعتماد على التطابق النصي القديم، (3) تصحيح
  بورت `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` في `.env` (6379 →
  6380)، (4) تحويل الـ7 دومينات الباقيين من `check_feature_access` إلى
  `can_access_service` (كل واحد بجلسة منفصلة بموافقة صريحة).
