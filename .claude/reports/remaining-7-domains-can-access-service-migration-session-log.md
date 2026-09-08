# تقرير جلسة — تحويل الـ7 دومينات الباقيين من `check_feature_access` إلى `can_access_service`

**تاريخ الجلسة:** 2026-09-07
**النطاق المطلوب (حرفيًا):** تحويل 7 دومينات (`employment`, `digital_twin`,
`arbitration_syndicates`, `realestate`, `manufacturing`, `logistics`,
`invitations`) من `check_feature_access` إلى `can_access_service` — نفس
نمط pilot `insurance` بالظبط (راجع
`.claude/reports/insurance-can-access-service-pilot-session-log.md`
والحالة الحالية الفعلية لـ`insurance/service.py` بعد تطوّرها اللاحق —
انظر §0 تحت). **دومين واحد في كل مرة**، بموافقة صريحة قبل الانتقال للتالي.
**ممنوع:** لمس `check_feature_access` نفسها، لمس أي دومين غير المذكور
حاليًا، لمس فرع `PAST_DUE`، أي `router`.

**قاعدة إلزامية جديدة (من دومين `arbitration_syndicates` فصاعدًا، بعد
اكتشاف §2.5):** أي `INSERT` مباشر بـ`id=` صريح على جدول `SERIAL`/`IDENTITY`
لازم يتبعه `setval()` **فورًا** على نفس الجدول، قبل أي اختبار حي أو
regression — مش بعده.

---

## 0. ملاحظة مهمة — النمط الفعلي المُستخدَم (أحدث من توثيق الـpilot الأصلي)

تقرير الـpilot الأصلي (`insurance-can-access-service-pilot-session-log.md`)
وثّق استخدام دالتين منفصلتين جداد (`has_any_active_subscription()` +
`can_access_service_via_plan()`). لكن **الحالة الفعلية الحالية** لكود
`insurance/service.py` (غير committed، فحصت بـ`git diff` مباشرة قبل بدء
هذه الجلسة) تستخدم نمط أبسط: استدعاء واحد لـ`can_access_service()`
الموجودة أصلًا في `SaaSControlService` — والتي بقت هي نفسها (بعد تطوّر
لاحق غير موثَّق بجلسة منفصلة بعد) تفحص `saas_plan_service_access`
(many-to-many) عبر `get_active_subscription_via_plan_access()`. نفس النمط
مُستخدَم فعليًا في `zamakana`/`transport`/`tourism_sports`/
`tenders_auctions`/`social`/`service_marketplace` (تأكَّد بـ
`grep -rl can_access_service app/domains`). **هذا هو النمط المتبَع في
هذه الجلسة لكل الدومينات الـ7** — أبسط من توثيق الـpilot الأصلي، لكنه
الكود الحي الفعلي المُطابق لباقي الدومينات المُحوَّلة.

---

## 1. دومين `employment` — ✅ تم

### 1.1 الملف المتأثر

| الملف | التغيير |
|---|---|
| `eppne-backend/app/domains/employment/service.py` | `_check_saas_limits()` (كانت سطر 67-78) بقت تستخدم `can_access_service` بدل `check_feature_access` |

لم يُلمَس أي ملف تاني في `app/` — تأكَّد بـ`git status`/`git diff` (باقي
التعديلات المعروضة في `git status` العام كانت موجودة قبل بدء الجلسة من
جلسات سابقة غير متعلقة).

### 1.2 الـdiff الفعلي

```diff
-from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService, FeatureAccessStatus
+from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService


     async def _check_saas_limits(self, tenant_id: int, feature: str = "hr_management") -> None:
         """
         التحقق من أن المستأجر لديه اشتراك فعال يتضمن الميزة المطلوبة.
         """
+        # [2026-09-07] موحَّد على can_access_service (زي insurance/zamakana/
+        # transport/tourism_sports/tenders_auctions/social/service_marketplace
+        # بالظبط) — بعد ما can_access_service نفسها بقت بتفحص
+        # saas_plan_service_access (many-to-many) بدل ServicePlan.service_id
+        # القديم. راجع PROGRESS_LOG.md.
         saas_service = SaaSSubscriptionService(self.db, tenant_id)
-        check = await saas_service.check_feature_access(tenant_id, feature)
-        if check.status == FeatureAccessStatus.NO_ACTIVE_SUBSCRIPTION:
-            raise PermissionDeniedError("No active subscription found for this entity.")
-        if check.status == FeatureAccessStatus.FEATURE_NOT_INCLUDED:
+        has_access = await saas_service.can_access_service(feature)
+        if not has_access:
             raise PermissionDeniedError(
                 f"Feature '{feature}' is not included in your current plan."
             )
```

**ملاحظة سلوكية:** رسالة `"No active subscription found for this entity."`
اختفت (نفس ما حصل بالظبط في insurance — `can_access_service` بترجع
`bool` واحد بلا تمييز بين "مفيش اشتراك خالص" و"مفيش صلاحية للخدمة دي
تحديدًا"). رسالة الرفض المتبقية (`"Feature '{feature}' is not included
in your current plan."`) **لم تتغيّر حرفيًا**.

`_check_saas_limits` بيتنادى بقيمتين مختلفتين لـ`feature` في هذا
الدومين: `"hr_management"` (سطر 160 `create_job`, سطر 299) و`"payroll"`
(سطر 538, 612). الاختبار الحي (§1.4) استخدم `"hr_management"` فقط —
`"payroll"` نفس المنطق بالضبط، غير مُختبَر منفصلًا (خارج ما طلبه المستخدم).

### 1.3 بيانات اختبار حقيقية (Seed مباشر عبر `docker exec psql` على `eppne_v2`)

خدمة `hr_management` لم تكن موجودة أصلًا في `saas_service_catalog` —
أُنشئت صفوف جديدة بنفس نمط pilot insurance (`id=101`) بالظبط:

| الجدول | الصف الجديد | القيمة |
|---|---|---|
| `saas_service_catalog` | خدمة `hr_management` حقيقية | `id=104`, `code='hr_management'`, `name='الموارد البشرية والتوظيف (Pilot)'` |
| `saas_service_plans` | خطة تابعة لها | `id=107`, `service_id=104`, `code='employment-pilot-plan'`, `features='[]'::jsonb` (فاضية عمدًا) |
| `saas_plan_service_access` | الربط عبر الجدول many-to-many | `(plan_id=107, service_id=104)` |
| `saas_tenant_subscriptions` | اشتراك `ACTIVE` حقيقي لتينانت 16 | `id=120`, `tenant_id=16`, `plan_id=107`, `status='ACTIVE'` |
| `saas_tenant_service_access` | تفعيل الخدمة لتينانت 16 | `id=52`, `tenant_id=16`, `service_id=104`, `is_active=true` |

تينانت 1 (`Local Test Tenant`) **لم يُمس بأي seed** — مفيش أي صف
`saas_tenant_service_access`/`saas_plan_service_access` بيربطه بخدمة
`hr_management` (`id=104`)، فهو سيناريو "من غير صلاحية" طبيعي بلا أي
seed سلبي إضافي.

### 1.4 اختبار E2E حي — الطريقة والنتائج

تشغيل السيرفر فعليًا (`uvicorn app.main:fastapi_app`, منفذ `8123` محلي
مؤقت لهذه الجلسة فقط) + طلبات HTTP فعلية بـ`curl` ضد endpoint حقيقي
(`POST /api/employment/jobs`)، بمستخدمين حقيقيين مسجَّلين دخول فعليًا
(JWT حقيقي من `/api/identity/login`)، لا mocks.

**المستخدمون** (من `.claude/reports/throwaway-test-users.md`، كلمة السر
اشتغلت من أول محاولة، لم تُحدَّث):

| المستخدم | tenant_id | الدور في الاختبار |
|---|---|---|
| `TEST_instr_b` (id=774) | 16 | **معه** صلاحية `hr_management` |
| `TEST_super_a` (id=772) | 1 | **من غيرها** |

`create_job` بياخد `tenant_id` من `current_user.tenant_id` (الـJWT
نفسه) — مش من هيدر `X-Tenant-ID` زي endpoint insurance، فمفيش أي
تعقيد/ثغرة هيدر ذات صلة هنا.

**اختبار 1 — تينانت 16 (معه صلاحية) → متوقَّع نجاح:**

```
POST /api/employment/jobs
Authorization: Bearer <JWT لـTEST_instr_b>
{"title":"EMPLOYMENT-CANACCESS-PILOT-TENANT16","employment_type":"FULL_TIME"}
```

```
HTTP_STATUS: 201
{"title":"EMPLOYMENT-CANACCESS-PILOT-TENANT16","description":null,"required_skills":[],"required_certificate_ids":[],"required_rank":null,"salary_min":null,"salary_max":null,"currency":"MR_USDT","location":null,"employment_type":"FULL_TIME","id":10,"employer_id":774,"is_active":true,"created_at":"2026-09-07T13:39:44.450478Z"}
```

**✅ نجح فعليًا (201 Created، وظيفة حقيقية اتسجَّلت بـ`id=10`)** —
`can_access_service("hr_management")` رجعت `True` لتينانت 16، من أول
محاولة (بلا أي مشكلة `is_deleted`/`server_default` زي insurance).

**اختبار 2 — تينانت 1 (من غير صلاحية) → متوقَّع رفض:**

```
POST /api/employment/jobs
Authorization: Bearer <JWT لـTEST_super_a>
{"title":"EMPLOYMENT-CANACCESS-PILOT-TENANT1-SHOULD-FAIL","employment_type":"FULL_TIME"}
```

```
HTTP_STATUS: 403
{"detail":"Feature 'hr_management' is not included in your current plan.","code":"PermissionDeniedError"}
```

**✅ رُفض فعليًا (403، رسالة مطابقة حرفيًا للرسالة الجديدة في الكود)**.

### 1.5 فحص ارتداد (regression)

```
pytest tests/test_employment_get_job_wiring.py -q
```

**النتيجة:** `1 passed, 2 warnings` (تحذيرات غير متعلقة —
`asyncio_default_fixture_loop_scope` وdeprecation قديم في `router.py`
سطر 378، موجودين قبل هذه الجلسة).

### 1.6 ملاحظة تقنية (بيئة، غير كودية)

أول محاولتين لتشغيل uvicorn محليًا فشلتا: الأولى لأن `uvicorn` مش على
PATH مباشرة (لازم `venv/Scripts/python.exe -m uvicorn`)، والثانية لأن
عملية `python.exe` (PID 12664) من محاولة سابقة فاشلة ظلت شغّالة في
الخلفية وماسكة المنفذ `8123` (`WinError 10048`) — اتقتلت بـ
`Stop-Process -Force` قبل إعادة المحاولة بنجاح. كمان استخدام
`PYTHONUTF8=1` كان ضروري لتفادي فيضان `UnicodeEncodeError` (طابور
logging بيحاول يطبع إيموجي على console بترميز `cp1256` الافتراضي على
Windows) — مشكلة بيئة معروفة، مش خطأ في كود هذه الجلسة.

### 1.7 ملخص الالتزام بالقيود

| القيد | الحالة |
|---|---|
| دومين `employment` فقط في هذه الخطوة | ✅ الملف الوحيد المتأثر: `employment/service.py` |
| ممنوع لمس `check_feature_access` نفسها | ✅ لم تُعدَّل، لسه موجودة ومُستخدَمة من الدومينات الـ6 الباقية |
| ممنوع لمس فرع `PAST_DUE` | ✅ لم يُلمَس (الفرع موجود داخل `can_access_service` نفسها، لم تُلمَس) |
| ممنوع أي `router` | ✅ صفر تعديل على `employment/router.py` |
| بيانات اختبار حقيقية (seed مباشر) | ✅ 5 صفوف عبر `docker exec psql`، بلا migration جديدة |
| اختبار حي E2E حقيقي (status code موثَّق) | ✅ 201 (نجاح) + 403 (رفض)، §1.4 |

**الحالة النهائية لهذا الدومين:** ✅ نجح. **الدومينات المتبقية:**
`digital_twin`, `arbitration_syndicates`, `realestate`, `manufacturing`,
`logistics`, `invitations` — لسه بتستخدم `check_feature_access` القديمة.

---

## 2. دومين `digital_twin` — ✅ تم

### 2.1 الملف المتأثر

| الملف | التغيير |
|---|---|
| `eppne-backend/app/domains/digital_twin/service.py` | `_check_saas_limits()` (كانت سطر 36-43) بقت تستخدم `can_access_service` بدل `check_feature_access` |

لم يُلمَس أي ملف تاني — تأكَّد بـ`git status`/`git diff` (الملف الوحيد
المتأثر من هذه الجلسة `digital_twin/service.py`).

### 2.2 الـdiff الفعلي

```diff
-from app.domains.saas.service import SaaSControlService, FeatureAccessStatus
+from app.domains.saas.service import SaaSControlService
 ...
     async def _check_saas_limits(self, tenant_id: int):
         """التحقق من صلاحية التوأم الرقمي في خطة الاشتراك."""
+        # [2026-09-07] موحَّد على can_access_service (زي insurance/employment/
+        # zamakana/transport/tourism_sports/tenders_auctions/social/
+        # service_marketplace بالظبط) — بعد ما can_access_service نفسها بقت
+        # بتفحص saas_plan_service_access (many-to-many) بدل
+        # ServicePlan.service_id القديم. راجع PROGRESS_LOG.md.
         saas_service = SaaSControlService(self.db, tenant_id)
-        check = await saas_service.check_feature_access(tenant_id, "digital_twin")
-        if check.status == FeatureAccessStatus.NO_ACTIVE_SUBSCRIPTION:
-            raise PermissionDeniedError("No active subscription found for this entity.")
-        if check.status == FeatureAccessStatus.FEATURE_NOT_INCLUDED:
+        has_access = await saas_service.can_access_service("digital_twin")
+        if not has_access:
             raise PermissionDeniedError("Digital Twin feature is not included in your current plan.")
```

نفس ملاحظة `employment`: رسالة `"No active subscription found for this
entity."` اختفت، رسالة الرفض المتبقية (`"Digital Twin feature is not
included in your current plan."`) **لم تتغيّر حرفيًا**. `_check_saas_limits`
بيتنادى من 4 نقاط (`get_or_create_twin` سطر 109, `update_twin_config`
سطر 124, `interact_with_twin` سطر 154, ونقطة رابعة سطر 235) — كلهم بنفس
الفيتشر الثابت `"digital_twin"` (بلا باراميتر متغيّر زي `employment`).

### 2.3 بيانات اختبار حقيقية (Seed مباشر عبر `docker exec psql` على `eppne_v2`)

خدمة `digital_twin` لم تكن موجودة أصلًا في `saas_service_catalog` —
نفس نمط `employment` (id تالي بالترتيب):

| الجدول | الصف الجديد | القيمة |
|---|---|---|
| `saas_service_catalog` | خدمة `digital_twin` حقيقية | `id=105`, `code='digital_twin'`, `name='التوأم الرقمي (Pilot)'` |
| `saas_service_plans` | خطة تابعة لها | `id=108`, `service_id=105`, `code='digital-twin-pilot-plan'`, `features='[]'::jsonb` |
| `saas_plan_service_access` | الربط عبر الجدول many-to-many | `(plan_id=108, service_id=105)` |
| `saas_tenant_subscriptions` | اشتراك `ACTIVE` حقيقي لتينانت 16 | `id=121`, `tenant_id=16`, `plan_id=108`, `status='ACTIVE'` |
| `saas_tenant_service_access` | تفعيل الخدمة لتينانت 16 | `id=53`, `tenant_id=16`, `service_id=105`, `is_active=true` |

تينانت 1 لم يُمس بأي seed (نفس منطق `employment` — غياب الصفوف كافٍ
لسيناريو "من غير صلاحية").

### 2.4 اختبار E2E حي — الطريقة والنتائج

نفس آلية دومين `employment` بالضبط (uvicorn حي على منفذ `8123` + `curl`
+ JWT حقيقي من `TEST_instr_b`/`TEST_super_a`). الـendpoint هذه المرة
`GET /api/digital-twin/config` (`get_or_create_twin` — `tenant_id` من
`current_user.tenant_id`، مفيش هيدر `X-Tenant-ID` متداخل).

**اختبار 1 — تينانت 16 (معه صلاحية) → متوقَّع نجاح:**

```
GET /api/digital-twin/config
Authorization: Bearer <JWT لـTEST_instr_b>
```

```
HTTP_STATUS: 200
{"global_access_level":"PRIVATE","interaction_fee_mrusdt":"0E-8","subscription_monthly_mrusdt":"0E-8","capabilities":[],"knowledge_boundaries":{},"max_spending_limit":"0E-8","settlement_type":"WEB2_FIAT","id":5,"user_id":774,"agent_id":null,"is_active":true,"physical_embodiment_status":"DIGITAL_ONLY","created_at":"2026-09-07T13:49:13.943879Z"}
```

**✅ نجح فعليًا (200، توأم رقمي حقيقي اتنشأ/اترجع بـ`id=5`)** —
`can_access_service("digital_twin")` رجعت `True` لتينانت 16 من أول محاولة.

**اختبار 2 — تينانت 1 (من غير صلاحية) → متوقَّع رفض:**

```
GET /api/digital-twin/config
Authorization: Bearer <JWT لـTEST_super_a>
```

```
HTTP_STATUS: 403
{"detail":"Digital Twin feature is not included in your current plan.","code":"PermissionDeniedError"}
```

**✅ رُفض فعليًا (403، رسالة مطابقة حرفيًا للكود)**.

### 2.5 فحص ارتداد (regression) — واكتشاف جانبي مهم (بيانات، مش كود)

`grep` عن `digital_twin`/`DigitalTwin` في `tests/` رجع ملفين ذوي صلة:
`test_affiliate_service_missing_methods.py` (فشل تجميع — `ImportError:
cannot import name 'ActionCommission'` — **موجود مسبقًا قبل هذه الجلسة**،
ناتج عن commit `2960d9d` "Unify 3 conflicting referral/affiliate
systems..." اللي غيّر موديلات `affiliate`، غير مرتبط بتاتًا بتعديل
`digital_twin/service.py` في هذه الجلسة — تأكَّد بـ`git log --oneline --
app/domains/affiliate/models.py`) و`test_referral_affiliate_unified_system.py`
(6 اختبارات، منها اختبار ينادي `DigitalTwinService` مباشرة).

**أول تشغيلة** لـ`test_referral_affiliate_unified_system.py` رجعت
`1 failed, 5 passed`: الفشل الوحيد
(`test_saas_subscription_activates_default_affiliate_scope`) كان
`sqlalchemy.exc.PendingRollbackError` بسبب `UniqueViolationError` على
`saas_tenant_subscriptions_pkey` (`id=120` مكرر). **السبب الجذري
(اتأكد بالتحقيق):** الـseed المباشر في هذه الجلسة (§2.3) وجلسة
`employment` قبلها استخدما `id=` صريح (120, 121) بدون `setval()` على
الـsequence بعدها — فالـsequence `saas_tenant_subscriptions_id_seq`
فضل واقف على `last_value=120` (القيمة الأخيرة قبل أي INSERT صريح)، وأول
`INSERT` عبر الـORM (بيستخدم `nextval()`) في التست جرّب يستخدم `id=120`
نفسها فاصطدم. **هذا خلل بيانات ناتج عن منهجية الـseed المباشر
(بدأ من جلسة insurance pilot الأصلية واستمر في `employment`)، مش خلل في
تعديل الكود نفسه.**

**الإصلاح (بيانات فقط):**
```sql
SELECT setval('saas_service_catalog_id_seq', (SELECT max(id) FROM saas_service_catalog));        -- → 105
SELECT setval('saas_service_plans_id_seq', (SELECT max(id) FROM saas_service_plans));             -- → 108
SELECT setval('saas_tenant_subscriptions_id_seq', (SELECT max(id) FROM saas_tenant_subscriptions)); -- → 121
SELECT setval('saas_tenant_service_access_id_seq', (SELECT max(id) FROM saas_tenant_service_access)); -- → 53
```

**بعد الإصلاح:** إعادة تشغيل `test_saas_subscription_activates_default_affiliate_scope`
منفردًا → `1 passed`. إعادة تشغيل الملف كامل →
`tests/test_referral_affiliate_unified_system.py`: **`6 passed`**.

**تحذير لأي جلسة قادمة من الـ5 الباقيين:** استخدام `id=` صريح في أي
`INSERT` مباشر عبر `psql`/`asyncpg` على أي جدول بـ`SERIAL`/`IDENTITY`
لازم يتبعه `setval()` فورًا على نفس الجلسة، وإلا نفس الاصطدام هيتكرر مع
أي اختبار ORM لاحق يلمس نفس الجدول.

### 2.6 ملخص الالتزام بالقيود

| القيد | الحالة |
|---|---|
| دومين `digital_twin` فقط في هذه الخطوة | ✅ الملف الوحيد المتأثر: `digital_twin/service.py` |
| ممنوع لمس `check_feature_access` نفسها | ✅ لم تُعدَّل |
| ممنوع لمس فرع `PAST_DUE` | ✅ لم يُلمَس |
| ممنوع أي `router` | ✅ صفر تعديل على `digital_twin/router.py` |
| بيانات اختبار حقيقية (seed مباشر) | ✅ 5 صفوف + إصلاح 4 sequences (بيانات، مش migration/كود) |
| اختبار حي E2E حقيقي (status code موثَّق) | ✅ 200 (نجاح) + 403 (رفض)، §2.4 |

**الحالة النهائية لهذا الدومين:** ✅ نجح. **الدومينات المتبقية:**
`arbitration_syndicates`, `realestate`, `manufacturing`, `logistics`,
`invitations` — لسه بتستخدم `check_feature_access` القديمة.

---

## 3. دومين `arbitration_syndicates` — ✅ تم

### 3.1 الملف المتأثر

| الملف | التغيير |
|---|---|
| `eppne-backend/app/domains/arbitration_syndicates/service.py` | `_check_saas_limits()` (كانت سطر 38-44) بقت تستخدم `can_access_service` بدل `check_feature_access` |

لم يُلمَس أي ملف تاني — تأكَّد بـ`git status`/`git diff` (الملف الوحيد
المتأثر من هذه الجلسة `arbitration_syndicates/service.py`).

### 3.2 الـdiff الفعلي

```diff
-from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService, FeatureAccessStatus
+from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
 ...
     async def _check_saas_limits(self, tenant_id: int, feature: str = "arbitration_syndicates"):
+        # [2026-09-07] موحَّد على can_access_service (زي insurance/employment/
+        # digital_twin/zamakana/transport/tourism_sports/tenders_auctions/
+        # social/service_marketplace بالظبط) — بعد ما can_access_service
+        # نفسها بقت بتفحص saas_plan_service_access (many-to-many) بدل
+        # ServicePlan.service_id القديم. راجع PROGRESS_LOG.md.
         saas_service = SaaSSubscriptionService(self.db, tenant_id)
-        check = await saas_service.check_feature_access(tenant_id, feature)
-        if check.status == FeatureAccessStatus.NO_ACTIVE_SUBSCRIPTION:
-            raise PermissionDeniedError("No active subscription found.")
-        if check.status == FeatureAccessStatus.FEATURE_NOT_INCLUDED:
+        has_access = await saas_service.can_access_service(feature)
+        if not has_access:
             raise PermissionDeniedError("Arbitration & Syndicates feature is not included in your current plan.")
```

نفس ملاحظة الدومينين السابقين: رسالة `"No active subscription found."`
اختفت، رسالة الرفض المتبقية (`"Arbitration & Syndicates feature is not
included in your current plan."`) **لم تتغيّر حرفيًا**. هذا الدومين
مميَّز عن `employment`/`digital_twin`: `_check_saas_limits` بيتنادى
بـ**قيمتين مختلفتين فعليًا** لـ`feature` — `"arbitration"` (3 نقاط: سطر
72, 176, 236 — قضايا التحكيم) و`"syndicates"` (6 نقاط: سطر 285, 306,
397, 461, 474, 493 — النقابات). الاختبار الحي (§3.4) استخدم `"syndicates"`
فقط (عبر `create_syndicate`) — `"arbitration"` نفس المنطق بالضبط، غير
مُختبَر منفصلًا (خارج ما طلبه المستخدم).

### 3.3 بيانات اختبار حقيقية (Seed مباشر عبر `docker exec psql` على `eppne_v2`)

خدمة `syndicates` لم تكن موجودة أصلًا في `saas_service_catalog`:

| الجدول | الصف الجديد | القيمة |
|---|---|---|
| `saas_service_catalog` | خدمة `syndicates` حقيقية | `id=106`, `code='syndicates'`, `name='النقابات السيادية (Pilot)'` |
| `saas_service_plans` | خطة تابعة لها | `id=109`, `service_id=106`, `code='syndicates-pilot-plan'`, `features='[]'::jsonb` |
| `saas_plan_service_access` | الربط عبر الجدول many-to-many | `(plan_id=109, service_id=106)` |
| `saas_tenant_subscriptions` | اشتراك `ACTIVE` حقيقي لتينانت 16 | `id=122`, `tenant_id=16`, `plan_id=109`, `status='ACTIVE'` |
| `saas_tenant_service_access` | تفعيل الخدمة لتينانت 16 | `id=54`, `tenant_id=16`, `service_id=106`, `is_active=true` |

تينانت 1 لم يُمس بأي seed (نفس منطق الدومينين السابقين).

**تنفيذ القاعدة الإلزامية الجديدة (§0):** فور الـ`COMMIT` بتاع الـINSERTs
فوق، نُفِّذ `setval()` على الأربع sequences المعنية **قبل** أي اختبار حي
أو regression:

```sql
SELECT setval('saas_service_catalog_id_seq', (SELECT max(id) FROM saas_service_catalog));         -- → 106
SELECT setval('saas_service_plans_id_seq', (SELECT max(id) FROM saas_service_plans));              -- → 109
SELECT setval('saas_tenant_subscriptions_id_seq', (SELECT max(id) FROM saas_tenant_subscriptions)); -- → 122
SELECT setval('saas_tenant_service_access_id_seq', (SELECT max(id) FROM saas_tenant_service_access)); -- → 54
```

كل الـ4 قيم رجعت مطابقة تمامًا للـid الأقصى الجديد في كل جدول — صفر
احتمال اصطدام لاحق زي اللي حصل في §2.5.

### 3.4 اختبار E2E حي — الطريقة والنتائج

نفس آلية الدومينين السابقين (uvicorn حي على منفذ `8123` + `curl` + JWT
حقيقي من `TEST_instr_b`/`TEST_super_a`، الاثنين `SUPER_ADMIN` فمرّوا من
`get_current_superuser`). الـendpoint: `POST /api/arbitration-syndicates/syndicates`
(`create_syndicate` — `tenant_id` من `current_user.tenant_id`).

**اختبار 1 — تينانت 16 (معه صلاحية) → متوقَّع نجاح:**

```
POST /api/arbitration-syndicates/syndicates
Authorization: Bearer <JWT لـTEST_instr_b>
{"name":"ARBITRATION-SYND-CANACCESS-PILOT-TENANT16","syndicate_type":"PROFESSIONAL"}
```

```
HTTP_STATUS: 201
{"name":"ARBITRATION-SYND-CANACCESS-PILOT-TENANT16","syndicate_type":"PROFESSIONAL","description":null,"annual_fee_mrusdt":"0E-8","dao_contract_address":null,"treasury_wallet_address":null,"governance_token":null,"id":4,"is_active":true,"created_at":"2026-09-07T14:47:02.974645Z"}
```

**✅ نجح فعليًا (201، نقابة حقيقية اتسجَّلت بـ`id=4`)** —
`can_access_service("syndicates")` رجعت `True` لتينانت 16 من أول محاولة.

**اختبار 2 — تينانت 1 (من غير صلاحية) → متوقَّع رفض:**

```
POST /api/arbitration-syndicates/syndicates
Authorization: Bearer <JWT لـTEST_super_a>
{"name":"ARBITRATION-SYND-CANACCESS-PILOT-TENANT1-SHOULD-FAIL","syndicate_type":"PROFESSIONAL"}
```

```
HTTP_STATUS: 403
{"detail":"Arbitration & Syndicates feature is not included in your current plan.","code":"PermissionDeniedError"}
```

**✅ رُفض فعليًا (403، رسالة مطابقة حرفيًا للكود)**.

### 3.5 فحص ارتداد (regression) — فشل موجود مسبقًا غير متعلق (موثَّق للشفافية)

`grep` عن `arbitration_syndicates`/`ArbitrationSyndicates`/`SovereignSyndicate`
في `tests/` رجع 3 ملفات ذات صلة:
`tests/test_ai_governance_begin_nested.py` (ذِكر نصي فقط، لا استدعاء
فعلي)، `tests/test_eventbus_publish_fix.py`، و
`tests/test_user_repository_get_by_id_audit.py`.

```
pytest tests/test_eventbus_publish_fix.py tests/test_user_repository_get_by_id_audit.py -q
```

**النتيجة:** `11 failed, 8 passed`. **كل الـ11 فشل في نفس الملف**
(`test_user_repository_get_by_id_audit.py`)، وموزَّعين على **11 دومين
مختلف** — `zamakana`, `transport`, `tourism_sports`, `tenders_auctions`,
`social`, `service_marketplace`, `realestate`, `arbitration_syndicates`,
`manufacturing`, `invitations`, `insurance` — **10 منهم لم تُلمَس هذه
الجلسة إطلاقًا** (ولا حتى `arbitration_syndicates` بنفس نقطة الفشل).

**تحقيق فعلي لسبب الفشل** (تشغيل الاختبار الخاص بـ`arbitration_syndicates`
منفردًا مع traceback كامل):

```
await svc._register_affiliate_commission(user.id, TENANT_ID, "ARBITRATION_CASE_CREATED")
_assert_no_typeerror_leak(cap.records)
assert any("referred_by" in r for r in cap.records)
AssertionError: assert False
```

الاختبار بيفحص `_register_affiliate_commission` (سطر 564 تقريبًا) —
**دالة منفصلة تمامًا عن `_check_saas_limits`** (اللي هي الوحيدة اللي
اتعدَّلت هذه الجلسة، تأكَّد بـ`git diff` §3.2 — صفر لمس لـ
`_register_affiliate_commission`). كون نفس نمط الفشل بالحرف
(`referred_by` مفقودة من الـlog) بيتكرر في 10 دومينات تانية لم تُلمَس
هذه الجلسة إطلاقًا **دليل حاسم** إنه خلل بنيوي عام في طبقة `affiliate`
المشتركة — على الأرجح ناتج عن نفس commit `2960d9d` ("Unify 3 conflicting
referral/affiliate systems into one scope-based model") المذكور بالفعل
في §2.5 كسبب `ImportError: ActionCommission`. **لم يُصلَح هنا** — خارج
النطاق الصريح لهذه الجلسة (`affiliate` مش من الـ7 دومينات المطلوبين، ولا
مذكور كاستثناء مسموح).

### 3.6 ملخص الالتزام بالقيود

| القيد | الحالة |
|---|---|
| دومين `arbitration_syndicates` فقط في هذه الخطوة | ✅ الملف الوحيد المتأثر: `arbitration_syndicates/service.py` |
| ممنوع لمس `check_feature_access` نفسها | ✅ لم تُعدَّل |
| ممنوع لمس فرع `PAST_DUE` | ✅ لم يُلمَس |
| ممنوع أي `router` | ✅ صفر تعديل على `arbitration_syndicates/router.py` |
| بيانات اختبار حقيقية (seed مباشر) | ✅ 5 صفوف + `setval()` فوري على 4 sequences (القاعدة الجديدة §0) |
| اختبار حي E2E حقيقي (status code موثَّق) | ✅ 201 (نجاح) + 403 (رفض)، §3.4 |

**الحالة النهائية لهذا الدومين:** ✅ نجح. **الدومينات المتبقية:**
`realestate`, `manufacturing`, `logistics`, `invitations` — لسه بتستخدم
`check_feature_access` القديمة.

---

## 4. دومين `realestate` — ✅ تم

### 4.1 الملف المتأثر

| الملف | التغيير |
|---|---|
| `eppne-backend/app/domains/realestate/service.py` | `_check_saas_limits()` (كانت سطر 60-66) بقت تستخدم `can_access_service` بدل `check_feature_access` |

لم يُلمَس أي ملف تاني — تأكَّد بـ`git status`/`git diff` (الملف الوحيد
المتأثر من هذه الجلسة `realestate/service.py`).

### 4.2 الـdiff الفعلي

```diff
-from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService, FeatureAccessStatus
+from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
 ...
     async def _check_saas_limits(self, tenant_id: int, feature: str = "real_estate"):
+        # [2026-09-07] موحَّد على can_access_service (زي insurance/employment/
+        # digital_twin/arbitration_syndicates/zamakana/transport/
+        # tourism_sports/tenders_auctions/social/service_marketplace بالظبط)
+        # — بعد ما can_access_service نفسها بقت بتفحص saas_plan_service_access
+        # (many-to-many) بدل ServicePlan.service_id القديم. راجع PROGRESS_LOG.md.
         saas = SaaSSubscriptionService(self.db, tenant_id)
-        check = await saas.check_feature_access(tenant_id, feature)
-        if check.status == FeatureAccessStatus.NO_ACTIVE_SUBSCRIPTION:
-            raise PermissionDeniedError("No active subscription found.")
-        if check.status == FeatureAccessStatus.FEATURE_NOT_INCLUDED:
+        has_access = await saas.can_access_service(feature)
+        if not has_access:
             raise PermissionDeniedError("Real Estate feature is not included in your current plan.")
```

نفس ملاحظة الدومينات السابقة: رسالة `"No active subscription found."`
اختفت، رسالة الرفض المتبقية (`"Real Estate feature is not included in
your current plan."`) **لم تتغيّر حرفيًا**. هذا الدومين عنده **4 قيم
مختلفة فعليًا** لـ`feature`: `"real_estate"` (5 نقاط: سطر 93, 156, 259,
423، والاختبار الحي هنا)، `"real_estate_development"` (سطرين: 135, 523)،
`"real_estate_tokenization"` (سطر 553)، `"real_estate_smart_contracts"`
(سطر 602). الاختبار الحي (§4.4) استخدم `"real_estate"` فقط (عبر
`create_land_asset`) — الباقي نفس المنطق بالظبط، غير مُختبَر منفصلًا
(خارج ما طلبه المستخدم).

### 4.3 بيانات اختبار حقيقية (Seed مباشر عبر `docker exec psql` على `eppne_v2`)

خدمة `real_estate` لم تكن موجودة أصلًا في `saas_service_catalog`:

| الجدول | الصف الجديد | القيمة |
|---|---|---|
| `saas_service_catalog` | خدمة `real_estate` حقيقية | `id=107`, `code='real_estate'`, `name='العقارات السيادية (Pilot)'` |
| `saas_service_plans` | خطة تابعة لها | `id=110`, `service_id=107`, `code='real-estate-pilot-plan'`, `features='[]'::jsonb` |
| `saas_plan_service_access` | الربط عبر الجدول many-to-many | `(plan_id=110, service_id=107)` |
| `saas_tenant_subscriptions` | اشتراك `ACTIVE` حقيقي لتينانت 16 | `id=123`, `tenant_id=16`, `plan_id=110`, `status='ACTIVE'` |
| `saas_tenant_service_access` | تفعيل الخدمة لتينانت 16 | `id=55`, `tenant_id=16`, `service_id=107`, `is_active=true` |

تينانت 1 لم يُمس بأي seed (نفس منطق الدومينات السابقة).

**تنفيذ القاعدة الإلزامية (§0):** فور الـ`COMMIT`، نُفِّذ `setval()` على
الأربع sequences **قبل** أي اختبار حي أو regression:

```sql
SELECT setval('saas_service_catalog_id_seq', (SELECT max(id) FROM saas_service_catalog));         -- → 107
SELECT setval('saas_service_plans_id_seq', (SELECT max(id) FROM saas_service_plans));              -- → 110
SELECT setval('saas_tenant_subscriptions_id_seq', (SELECT max(id) FROM saas_tenant_subscriptions)); -- → 123
SELECT setval('saas_tenant_service_access_id_seq', (SELECT max(id) FROM saas_tenant_service_access)); -- → 55
```

### 4.4 اختبار E2E حي — الطريقة والنتائج

نفس آلية الدومينات السابقة (uvicorn حي على منفذ `8123` + `curl` + JWT
حقيقي من `TEST_instr_b`/`TEST_super_a`). الـendpoint: `POST /api/realestate/lands`
(`create_land_asset` — `tenant_id` من `get_current_tenant` عبر هيدر
`X-Tenant-ID`، نفس نمط `insurance` — أُرسل الهيدر مطابقًا لتينانت كل
مستخدم فعليًا، بلا أي استغلال).

**اختبار 1 — تينانت 16 (معه صلاحية) → متوقَّع نجاح:**

```
POST /api/realestate/lands
Authorization: Bearer <JWT لـTEST_instr_b>
X-Tenant-ID: 16
{"plot_number":"REALESTATE-CANACCESS-PILOT-TENANT16","area_sqm":1000,"gps_polygon":{"type":"Polygon","coordinates":[]},"zoning":"RESIDENTIAL","legal_status":"REGISTERED"}
```

```
HTTP_STATUS: 201
{"plot_number":"REALESTATE-CANACCESS-PILOT-TENANT16","area_sqm":"1000.00","gps_polygon":{"type":"Polygon","coordinates":[]},"zoning":"RESIDENTIAL","legal_status":"REGISTERED","current_value_mrusdt":"0E-8","has_insurance":false,"id":68,"parent_id":null,"owner_id":774,"created_at":"2026-09-07T15:18:47.499637Z"}
```

**✅ نجح فعليًا (201، أرض حقيقية اتسجَّلت بـ`id=68`)** —
`can_access_service("real_estate")` رجعت `True` لتينانت 16 من أول محاولة.

**اختبار 2 — تينانت 1 (من غير صلاحية) → متوقَّع رفض:**

```
POST /api/realestate/lands
Authorization: Bearer <JWT لـTEST_super_a>
X-Tenant-ID: 1
{"plot_number":"REALESTATE-CANACCESS-PILOT-TENANT1-SHOULD-FAIL","area_sqm":1000,"gps_polygon":{"type":"Polygon","coordinates":[]},"zoning":"RESIDENTIAL","legal_status":"REGISTERED"}
```

```
HTTP_STATUS: 403
{"detail":"Real Estate feature is not included in your current plan.","code":"PermissionDeniedError"}
```

**✅ رُفض فعليًا (403، رسالة مطابقة حرفيًا للكود)**.

### 4.5 فحص ارتداد (regression) — 6 فشل، كلهم موجودين مسبقًا/متوقَّعين (موثَّق للشفافية)

`grep` عن `realestate`/`RealEstate` في `tests/` رجع 13 ملف؛ اتشغَّلت الـ7
ذوي الصلة المباشرة بمسار `_check_saas_limits`/CRUD الأساسي:

```
pytest tests/test_realestate_getter_endpoints_wiring.py tests/test_realestate_insurance_savepoint.py tests/test_realestate_property_crud_endpoints.py tests/test_realestate_rent_unit_ownership_check.py tests/test_realestate_tokenize_asset_ownership_check.py tests/test_realestate_update_delete_property_unit_ownership_check.py tests/test_saas_active_subscription.py -q
```

**النتيجة:** `6 failed, 20 passed, 1 xfailed`. تحقيق كل الـ6:

| الاختبار الفاشل | السبب المؤكَّد | متعلق بهذه الجلسة؟ |
|---|---|---|
| `test_realestate_insurance_savepoint.py::test_realestate_buy_fractional_ownership_invoice_ordering` | حارس بنيوي (source-order) على `buy_fractional_ownership` — **موثَّق مسبقًا كفشل موجود من قبل** في §8 من `insurance-can-access-service-pilot-session-log.md` (نفس الاختبار بالحرف)، `realestate/service.py` لم يُلمَس في هذه النقطة | ❌ لا — موجود قبل أي جلسة من الـ4 |
| `test_realestate_rent_unit_ownership_check.py::test_rent_unit_succeeds_for_real_owner` | **تحقيق فعلي (traceback كامل):** `rent_unit(tenant_id=1, ...)` → `_check_saas_limits(1, "real_estate")` → `can_access_service("real_estate")` رجعت `False` لتينانت `1` (`TENANT_ID` ثابتة في ملف الاختبار) | 🟡 **نعم، أثر متوقَّع** |
| `test_saas_active_subscription.py::test_realestate_rent_unit_saas_check_passes` | نفس السبب بالحرف — تينانت `1` | 🟡 **نعم، أثر متوقَّع** |
| `test_saas_active_subscription.py::test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug` | نفس السبب بالحرف — تينانت `1` | 🟡 **نعم، أثر متوقَّع** |
| `test_saas_active_subscription.py::test_insurance_subscribe_saas_check_passes` | خاص بـ`insurance` مش `realestate` — **موثَّق مسبقًا كبند backlog مفتوح #2 في `PROGRESS_LOG.md`** (من جلسة توحيد `insurance` السابقة، قبل أي جلسة من الـ4) | ❌ لا — pre-existing، `insurance` |
| `test_saas_active_subscription.py::test_insurance_review_claim_saas_check_passes_then_hits_known_bug` | نفس السابق — `insurance`، pre-existing | ❌ لا — pre-existing، `insurance` |

**تحليل الـ3 فشل المتعلقة فعليًا (`rent_unit`/`buy_fractional_ownership`
لتينانت 1):** هذه **نفس فئة العيب الموثَّقة بالفعل كبند backlog مفتوح
#2 في `PROGRESS_LOG.md`** (قبل بدء أي جلسة من الـ4 دومينات) — الاختبارات
دي بتعتمد على تينانت `1` اللي كان بيحصل على وصول `real_estate` **وهميًا**
عبر تطابق نصي عرضي في `plan.features` (خطة `id=2`، `features:
["real_estate", "insurance"]`، **مش** لها أي علاقة فعلية بخدمة عقارات
حقيقية) تحت منطق `check_feature_access` القديم. `can_access_service`
الجديدة **بتصحيح متعمَّد** بترفض هذا التطابق النصي الوهمي — تمامًا زي ما
اتوثَّق ونُجرِّب حيًا لـ`insurance` نفسها في §5 من
`insurance-can-access-service-pilot-session-log.md`. **الاختبارات نفسها
لسه لم تُعدَّل** (بحاجة seed حقيقي لخدمة `real_estate` لتينانت 1، أو
تحديث لتستخدم تينانت 16) — **خارج نطاق هذه الجلسة صراحة** (بند backlog
#2 موجود بالفعل، ينتظر جلسة منفصلة).

### 4.6 ملخص الالتزام بالقيود

| القيد | الحالة |
|---|---|
| دومين `realestate` فقط في هذه الخطوة | ✅ الملف الوحيد المتأثر: `realestate/service.py` |
| ممنوع لمس `check_feature_access` نفسها | ✅ لم تُعدَّل |
| ممنوع لمس فرع `PAST_DUE` | ✅ لم يُلمَس |
| ممنوع أي `router` | ✅ صفر تعديل على `realestate/router.py` |
| بيانات اختبار حقيقية (seed مباشر) | ✅ 5 صفوف + `setval()` فوري على 4 sequences (القاعدة الإلزامية) |
| اختبار حي E2E حقيقي (status code موثَّق) | ✅ 201 (نجاح) + 403 (رفض)، §4.4 |

**الحالة النهائية لهذا الدومين:** ✅ نجح. 6 فشل regression موثَّقين
ومُحقَّقين بالكامل — صفر منهم ناتج عن خلل في تعديل الكود نفسه؛ 3 pre-existing
(اتنين `insurance`، واحد حارس `realestate` بنيوي)، و3 أثر متوقَّع لنفس
عيب backlog #2 المفتوح بالفعل قبل هذه الجلسة. **الدومينات المتبقية:**
`manufacturing`, `logistics`, `invitations` — لسه بتستخدم
`check_feature_access` القديمة.

---

## 5. دومين `manufacturing` — ✅ تم

### 5.1 الملف المتأثر

| الملف | التغيير |
|---|---|
| `eppne-backend/app/domains/manufacturing/service.py` | `_check_saas_limits()` (كانت سطر 42-48) بقت تستخدم `can_access_service` بدل `check_feature_access` |

لم يُلمَس أي ملف تاني — تأكَّد بـ`git status`/`git diff` (الملف الوحيد
المتأثر من هذه الجلسة `manufacturing/service.py`).

### 5.2 الـdiff الفعلي

```diff
-from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService, FeatureAccessStatus
+from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
 ...
     async def _check_saas_limits(self, tenant_id: int, feature: str = "manufacturing"):
+        # [2026-09-07] موحَّد على can_access_service (زي insurance/employment/
+        # digital_twin/arbitration_syndicates/realestate/zamakana/transport/
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
             raise PermissionDeniedError("Manufacturing feature is not included in your current plan.")
```

نفس ملاحظة الدومينات السابقة: رسالة `"No active subscription found."`
اختفت، رسالة الرفض المتبقية (`"Manufacturing feature is not included in
your current plan."`) **لم تتغيّر حرفيًا**. هذا الدومين بسيط نسبيًا —
`_check_saas_limits` بيتنادى من **12 نقطة** (سطر 99, 154, 188, 238, 280,
400, 466, 552, 605, 654, 754, 792) لكن **كلهم بنفس الفيتشر الثابت
`"manufacturing"`** (بلا باراميتر متغيّر زي `arbitration_syndicates`/
`realestate`).

### 5.3 بيانات اختبار حقيقية (Seed مباشر عبر `docker exec psql` على `eppne_v2`)

خدمة `manufacturing` لم تكن موجودة أصلًا في `saas_service_catalog`:

| الجدول | الصف الجديد | القيمة |
|---|---|---|
| `saas_service_catalog` | خدمة `manufacturing` حقيقية | `id=108`, `code='manufacturing'`, `name='التصنيع السيادي (Pilot)'` |
| `saas_service_plans` | خطة تابعة لها | `id=111`, `service_id=108`, `code='manufacturing-pilot-plan'`, `features='[]'::jsonb` |
| `saas_plan_service_access` | الربط عبر الجدول many-to-many | `(plan_id=111, service_id=108)` |
| `saas_tenant_subscriptions` | اشتراك `ACTIVE` حقيقي لتينانت 16 | `id=124`, `tenant_id=16`, `plan_id=111`, `status='ACTIVE'` |
| `saas_tenant_service_access` | تفعيل الخدمة لتينانت 16 | `id=56`, `tenant_id=16`, `service_id=108`, `is_active=true` |

تينانت 1 لم يُمس بأي seed. الاختبار الحي (§5.4) احتاج كيان سيادي حقيقي
(`entity_id`) — أُعيد استخدام الكيان الموجود بالفعل لتينانت 16 من جلسة
`insurance` pilot السابقة (`sovereign_entities_v2.id=30`,
`PILOT-INSURANCE-ENTITY-TENANT16`)، بدون أي seed جديد لهذا الجدول.

**تنفيذ القاعدة الإلزامية (§0):** فور الـ`COMMIT`، نُفِّذ `setval()` على
الأربع sequences **قبل** أي اختبار حي أو regression:

```sql
SELECT setval('saas_service_catalog_id_seq', (SELECT max(id) FROM saas_service_catalog));         -- → 108
SELECT setval('saas_service_plans_id_seq', (SELECT max(id) FROM saas_service_plans));              -- → 111
SELECT setval('saas_tenant_subscriptions_id_seq', (SELECT max(id) FROM saas_tenant_subscriptions)); -- → 124
SELECT setval('saas_tenant_service_access_id_seq', (SELECT max(id) FROM saas_tenant_service_access)); -- → 56
```

كل الـ4 قيم رجعت مطابقة تمامًا للـid الأقصى الجديد في كل جدول.

### 5.4 اختبار E2E حي — الطريقة والنتائج

نفس آلية الدومينات السابقة (uvicorn حي على منفذ `8123` + `curl` + JWT
حقيقي من `TEST_instr_b`/`TEST_super_a`). الـendpoint: `POST /api/manufacturing/facilities`
(`create_facility` — `tenant_id` من `current_user.tenant_id`، مفيش هيدر
متداخل).

**اختبار 1 — تينانت 16 (معه صلاحية) → متوقَّع نجاح:**

```
POST /api/manufacturing/facilities
Authorization: Bearer <JWT لـTEST_instr_b>
{"entity_id":30,"name":"MANUFACTURING-CANACCESS-PILOT-TENANT16","facility_type":"ASSEMBLY_LINE"}
```

```
HTTP_STATUS: 201
{"entity_id":30,"name":"MANUFACTURING-CANACCESS-PILOT-TENANT16","facility_type":"ASSEMBLY_LINE","location_gps":null,"real_estate_unit_id":null,"id":5,"manager_id":774,"safety_compliance_score":100.0,"is_active":true,"created_at":"2026-09-07T15:38:50.317519Z"}
```

**✅ نجح فعليًا (201، منشأة تصنيع حقيقية اتسجَّلت بـ`id=5`)** —
`can_access_service("manufacturing")` رجعت `True` لتينانت 16 من أول محاولة.

**اختبار 2 — تينانت 1 (من غير صلاحية) → متوقَّع رفض:**

```
POST /api/manufacturing/facilities
Authorization: Bearer <JWT لـTEST_super_a>
{"entity_id":1,"name":"MANUFACTURING-CANACCESS-PILOT-TENANT1-SHOULD-FAIL","facility_type":"ASSEMBLY_LINE"}
```

```
HTTP_STATUS: 403
{"detail":"Manufacturing feature is not included in your current plan.","code":"PermissionDeniedError"}
```

**✅ رُفض فعليًا (403، رسالة مطابقة حرفيًا للكود)** — الرفض حصل عند بوابة
الـSaaS قبل ما الكود يوصل لأي تحقق تاني (زي `entity_id` غير الحقيقي
`1` المُرسَل في هذا الطلب).

### 5.5 فحص ارتداد (regression) — فشل موجود مسبقًا، موثَّق بالفعل في backlog اليوم (موثَّق للشفافية)

`grep` عن `manufacturing`/`Manufacturing` في `tests/` رجع 3 ملفات؛ اثنين
منهم (`test_ai_agents_execute_action.py`, `test_ai_governance_begin_nested.py`)
ذِكر نصي فقط بلا استدعاء فعلي لـ`ManufacturingService`. الملف الوحيد ذو
الصلة الفعلية:

```
pytest tests/test_user_repository_get_by_id_audit.py::test_manufacturing_get_user_correct_and_wrong_tenant -q
```

**النتيجة:** `1 failed`. **تحقيق مباشر (traceback كامل):** الفشل في
`_register_affiliate_commission` (`assert any("referred_by" in r for r
in cap.records)` → `AssertionError`) — **دالة منفصلة تمامًا عن
`_check_saas_limits`** (اللي هي الوحيدة اللي اتعدَّلت هذه الجلسة، تأكَّد
بـ`git diff` §5.2). `manufacturing` هو **بالضبط أحد الـ11 دومين** المذكورين
في بند backlog `backlog-affiliate-commission-registration-systemwide-broken`
(المُضاف في `PROGRESS_LOG.md` بعد جلسة `arbitration_syndicates` مباشرة)
— **مش اكتشاف جديد**، تأكيد إضافي لنفس الخلل البنيوي الموثَّق بالفعل في
طبقة `affiliate` المشتركة (على الأرجح تبعة commit `2960d9d`). **لم
يُصلَح هنا** — خارج النطاق الصريح، وله backlog مفتوح بالفعل.

### 5.6 ملخص الالتزام بالقيود

| القيد | الحالة |
|---|---|
| دومين `manufacturing` فقط في هذه الخطوة | ✅ الملف الوحيد المتأثر: `manufacturing/service.py` |
| ممنوع لمس `check_feature_access` نفسها | ✅ لم تُعدَّل |
| ممنوع لمس فرع `PAST_DUE` | ✅ لم يُلمَس |
| ممنوع أي `router` | ✅ صفر تعديل على `manufacturing/router.py` |
| بيانات اختبار حقيقية (seed مباشر) | ✅ 5 صفوف + `setval()` فوري على 4 sequences (القاعدة الإلزامية) |
| اختبار حي E2E حقيقي (status code موثَّق) | ✅ 201 (نجاح) + 403 (رفض)، §5.4 |

**الحالة النهائية لهذا الدومين:** ✅ نجح. فشل regression واحد فقط —
مؤكَّد pre-existing وموثَّق بالفعل ضمن backlog اليوم، صفر علاقة بتعديل
الكود. **الدومينات المتبقية:** `logistics`, `invitations` — لسه بتستخدم
`check_feature_access` القديمة.

---

## 6. دومين `logistics` — ✅ تم

### 6.1 الملف المتأثر

| الملف | التغيير |
|---|---|
| `eppne-backend/app/domains/logistics/service.py` | `_check_saas_limits()` (كانت سطر 47-53) بقت تستخدم `can_access_service` بدل `check_feature_access` |

لم يُلمَس أي ملف تاني — تأكَّد بـ`git status`/`git diff` (الملف الوحيد
المتأثر من هذه الجلسة `logistics/service.py`).

### 6.2 الـdiff الفعلي

```diff
-from app.domains.saas.service import SaaSControlService, FeatureAccessStatus
+from app.domains.saas.service import SaaSControlService
 ...
     async def _check_saas_limits(self, tenant_id: int, feature: str = "logistics"):
+        # [2026-09-07] موحَّد على can_access_service (زي insurance/employment/
+        # digital_twin/arbitration_syndicates/realestate/manufacturing/
+        # zamakana/transport/tourism_sports/tenders_auctions/social/
+        # service_marketplace بالظبط) — بعد ما can_access_service نفسها بقت
+        # بتفحص saas_plan_service_access (many-to-many) بدل
+        # ServicePlan.service_id القديم. راجع PROGRESS_LOG.md.
         saas_service = SaaSControlService(self.db, tenant_id)
-        check = await saas_service.check_feature_access(tenant_id, feature)
-        if check.status == FeatureAccessStatus.NO_ACTIVE_SUBSCRIPTION:
-            raise PermissionDeniedError("No active subscription found.")
-        if check.status == FeatureAccessStatus.FEATURE_NOT_INCLUDED:
+        has_access = await saas_service.can_access_service(feature)
+        if not has_access:
             raise PermissionDeniedError("Logistics feature is not included in your current plan.")
```

نفس ملاحظة الدومينات السابقة: رسالة `"No active subscription found."`
اختفت، رسالة الرفض المتبقية (`"Logistics feature is not included in
your current plan."`) **لم تتغيّر حرفيًا**. `_check_saas_limits` بيتنادى
من **6 نقاط** (سطر 86, 177, 267, 344, 438, 525) كلهم بنفس الفيتشر الثابت
`"logistics"` (بلا باراميتر متغيّر).

### 6.3 بيانات اختبار حقيقية (Seed مباشر عبر `docker exec psql` على `eppne_v2`)

خدمة `logistics` لم تكن موجودة أصلًا في `saas_service_catalog`:

| الجدول | الصف الجديد | القيمة |
|---|---|---|
| `saas_service_catalog` | خدمة `logistics` حقيقية | `id=109`, `code='logistics'`, `name='اللوجيستيات السيادية (Pilot)'` |
| `saas_service_plans` | خطة تابعة لها | `id=112`, `service_id=109`, `code='logistics-pilot-plan'`, `features='[]'::jsonb` |
| `saas_plan_service_access` | الربط عبر الجدول many-to-many | `(plan_id=112, service_id=109)` |
| `saas_tenant_subscriptions` | اشتراك `ACTIVE` حقيقي لتينانت 16 | `id=125`, `tenant_id=16`, `plan_id=112`, `status='ACTIVE'` |
| `saas_tenant_service_access` | تفعيل الخدمة لتينانت 16 | `id=57`, `tenant_id=16`, `service_id=109`, `is_active=true` |

تينانت 1 لم يُمس بأي seed.

**تنفيذ القاعدة الإلزامية (§0):** فور الـ`COMMIT`، نُفِّذ `setval()` على
الأربع sequences **قبل** أي اختبار حي أو regression:

```sql
SELECT setval('saas_service_catalog_id_seq', (SELECT max(id) FROM saas_service_catalog));         -- → 109
SELECT setval('saas_service_plans_id_seq', (SELECT max(id) FROM saas_service_plans));              -- → 112
SELECT setval('saas_tenant_subscriptions_id_seq', (SELECT max(id) FROM saas_tenant_subscriptions)); -- → 125
SELECT setval('saas_tenant_service_access_id_seq', (SELECT max(id) FROM saas_tenant_service_access)); -- → 57
```

كل الـ4 قيم رجعت مطابقة تمامًا للـid الأقصى الجديد في كل جدول.

### 6.4 اختبار E2E حي — الطريقة والنتائج

نفس آلية الدومينات السابقة (uvicorn حي على منفذ `8123` + `curl` + JWT
حقيقي من `TEST_instr_b`/`TEST_super_a`). الـendpoint: `POST /api/logistics/warehouses`
(`create_warehouse` — `tenant_id` من `current_user.tenant_id`).

**اختبار 1 — تينانت 16 (معه صلاحية) → متوقَّع نجاح:**

```
POST /api/logistics/warehouses
Authorization: Bearer <JWT لـTEST_instr_b>
{"name":"LOGISTICS-CANACCESS-PILOT-TENANT16","warehouse_type":"CENTRAL","location":"Cairo","total_capacity_sqm":1000,"total_capacity_units":500}
```

```
HTTP_STATUS: 201
{"name":"LOGISTICS-CANACCESS-PILOT-TENANT16","warehouse_type":"CENTRAL","location":"Cairo","gps_location":null,"total_capacity_sqm":"1000.00","total_capacity_units":500,"manager_id":null,"id":5,"tenant_id":16,"used_capacity_sqm":"0.00","used_capacity_units":0,"is_active":true,"created_by":774,"created_at":"2026-09-07T15:56:02.732519Z","updated_at":"2026-09-07T15:56:02.732519Z"}
```

**✅ نجح فعليًا (201، مخزن حقيقي اتسجَّل بـ`id=5`)** —
`can_access_service("logistics")` رجعت `True` لتينانت 16 من أول محاولة.

**اختبار 2 — تينانت 1 (من غير صلاحية) → متوقَّع رفض:**

```
POST /api/logistics/warehouses
Authorization: Bearer <JWT لـTEST_super_a>
{"name":"LOGISTICS-CANACCESS-PILOT-TENANT1-SHOULD-FAIL","warehouse_type":"CENTRAL","location":"Cairo","total_capacity_sqm":1000,"total_capacity_units":500}
```

```
HTTP_STATUS: 403
{"detail":"Logistics feature is not included in your current plan.","code":"PermissionDeniedError"}
```

**✅ رُفض فعليًا (403، رسالة مطابقة حرفيًا للكود)**. **ملاحظة تشغيلية
(بلا أثر على النتيجة النهائية):** أول محاولة لهذا الاختبار استخدمت JWT
قديم/خطأ بالغلط (نُسخ من جلسة سابقة في نفس المحادثة) فرجعت `401 Invalid
token` بدل `403` — اتصلح فورًا بإعادة استخدام الـJWT الصحيح الفعلي
لـ`TEST_super_a` من تسجيل الدخول الحي بنفس هذه الجلسة (§6.4)، والنتيجة
`403` المذكورة فوق هي نتيجة المحاولة المُصححة.

### 6.5 فحص ارتداد (regression)

```
pytest tests/test_user_repository_get_by_id_audit.py::test_logistics_get_user_left_untouched_as_documented_dead_code -q
```

**النتيجة:** `1 passed`. الاختبار الوحيد ذو الصلة الفعلية بـ`logistics`
(بين 4 ملفات رجعها الـ`grep`، الباقي ذِكر نصي فقط) — نجح بلا أي فشل، لا
علاقة بمشكلة `_register_affiliate_commission`/`referred_by` الموثَّقة في
backlog اليوم (هذا الاختبار بيفحص `_get_user` بس، مش
`_register_affiliate_commission`).

### 6.6 ملخص الالتزام بالقيود

| القيد | الحالة |
|---|---|
| دومين `logistics` فقط في هذه الخطوة | ✅ الملف الوحيد المتأثر: `logistics/service.py` |
| ممنوع لمس `check_feature_access` نفسها | ✅ لم تُعدَّل |
| ممنوع لمس فرع `PAST_DUE` | ✅ لم يُلمَس |
| ممنوع أي `router` | ✅ صفر تعديل على `logistics/router.py` |
| بيانات اختبار حقيقية (seed مباشر) | ✅ 5 صفوف + `setval()` فوري على 4 sequences (القاعدة الإلزامية) |
| اختبار حي E2E حقيقي (status code موثَّق) | ✅ 201 (نجاح) + 403 (رفض)، §6.4 |

**الحالة النهائية لهذا الدومين:** ✅ نجح. صفر فشل regression. **الدومين
المتبقي الوحيد:** `invitations` — لسه بيستخدم `check_feature_access`
القديمة.

---

## 7. دومين `invitations` — ✅ تم (آخر دومين من الـ7)

### 7.1 الملف المتأثر

| الملف | التغيير |
|---|---|
| `eppne-backend/app/domains/invitations/service.py` | `_check_saas_limits()` (كانت سطر 41-47) بقت تستخدم `can_access_service` بدل `check_feature_access` |

لم يُلمَس أي ملف تاني — تأكَّد بـ`git status`/`git diff` (الملف الوحيد
المتأثر من هذه الجلسة `invitations/service.py`).

### 7.2 الـdiff الفعلي

```diff
-from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService, FeatureAccessStatus
+from app.domains.saas.service import SaaSControlService as SaaSSubscriptionService
 ...
     async def _check_saas_limits(self, tenant_id: int, feature: str = "crm"):
+        # [2026-09-07] موحَّد على can_access_service (زي insurance/employment/
+        # digital_twin/arbitration_syndicates/realestate/manufacturing/
+        # logistics/zamakana/transport/tourism_sports/tenders_auctions/
+        # social/service_marketplace بالظبط) — بعد ما can_access_service
+        # نفسها بقت بتفحص saas_plan_service_access (many-to-many) بدل
+        # ServicePlan.service_id القديم. راجع PROGRESS_LOG.md.
         saas_service = SaaSSubscriptionService(self.db, tenant_id)
-        check = await saas_service.check_feature_access(tenant_id, feature)
-        if check.status == FeatureAccessStatus.NO_ACTIVE_SUBSCRIPTION:
-            raise PermissionDeniedError("No active subscription found.")
-        if check.status == FeatureAccessStatus.FEATURE_NOT_INCLUDED:
+        has_access = await saas_service.can_access_service(feature)
+        if not has_access:
             raise PermissionDeniedError("CRM feature is not included in your current plan.")
```

نفس ملاحظة الدومينات السابقة: رسالة `"No active subscription found."`
اختفت، رسالة الرفض المتبقية (`"CRM feature is not included in your
current plan."`) **لم تتغيّر حرفيًا**. ملاحظة تسمية: اسم الدومين
`invitations` لكن الفيتشر الافتراضي المُستخدَم في كل الـ9 نقاط
(سطر 156, 275, 368, 485, 555, 634, 758, 843, 924) هو `"crm"` — الدومين
بيغطي الدعوات + CRM + العملاء المحتملين + الحملات + تذاكر الدعم تحت نفس
فيتشر SaaS واحد.

### 7.3 بيانات اختبار حقيقية (Seed مباشر عبر `docker exec psql` على `eppne_v2`)

خدمة `crm` لم تكن موجودة أصلًا في `saas_service_catalog`:

| الجدول | الصف الجديد | القيمة |
|---|---|---|
| `saas_service_catalog` | خدمة `crm` حقيقية | `id=110`, `code='crm'`, `name='الدعوات وخدمة العملاء (Pilot)'` |
| `saas_service_plans` | خطة تابعة لها | `id=113`, `service_id=110`, `code='crm-pilot-plan'`, `features='[]'::jsonb` |
| `saas_plan_service_access` | الربط عبر الجدول many-to-many | `(plan_id=113, service_id=110)` |
| `saas_tenant_subscriptions` | اشتراك `ACTIVE` حقيقي لتينانت 16 | `id=126`, `tenant_id=16`, `plan_id=113`, `status='ACTIVE'` |
| `saas_tenant_service_access` | تفعيل الخدمة لتينانت 16 | `id=58`, `tenant_id=16`, `service_id=110`, `is_active=true` |

تينانت 1 لم يُمس بأي seed.

**تنفيذ القاعدة الإلزامية (§0):** فور الـ`COMMIT`، نُفِّذ `setval()` على
الأربع sequences **قبل** أي اختبار حي أو regression:

```sql
SELECT setval('saas_service_catalog_id_seq', (SELECT max(id) FROM saas_service_catalog));         -- → 110
SELECT setval('saas_service_plans_id_seq', (SELECT max(id) FROM saas_service_plans));              -- → 113
SELECT setval('saas_tenant_subscriptions_id_seq', (SELECT max(id) FROM saas_tenant_subscriptions)); -- → 126
SELECT setval('saas_tenant_service_access_id_seq', (SELECT max(id) FROM saas_tenant_service_access)); -- → 58
```

كل الـ4 قيم رجعت مطابقة تمامًا للـid الأقصى الجديد في كل جدول.

### 7.4 اختبار E2E حي — الطريقة والنتائج (بما فيها اكتشاف عيب جديد غير متعلق)

**أول محاولة** استخدمت `POST /api/invitations/` (`create_invitation`، أول
نقطة استدعاء لـ`_check_saas_limits` في الملف) — **رجعت `500 Internal
Server Error`** بدل `201` رغم إن `_check_saas_limits` كانت نجحت (تأكَّد
بالـtraceback الفعلي، §7.4.1 تحت). بعد التحقيق والالتفاف عليه (بلا لمس
أي كود)، اتحوَّل الاختبار الحي لـ`POST /api/invitations/campaigns`
(`create_campaign` — نفس `_check_saas_limits(tenant_id, "crm")` بالظبط،
سطر 638) واللي نجح بشكل نظيف كامل.

#### 7.4.1 اكتشاف عيب جديد (pre-existing، غير متعلق، موثَّق للشفافية) — `create_invitation` مكسورة بالكامل لأي تينانت عنده صلاحية

**السلسلة الفعلية (3 محاولات متتالية، كل واحدة كشفت الخطوة التالية):**

1. `{"invitation_type":"GENERAL","target_type":"PERSON","title":"...","campaign_type":"SERVICE","campaign_id":1}`
   (بدون `custom_message`) → `500`. **traceback:**
   `bleach.clean(data.get("custom_message", ""), ...)` → `TypeError:
   argument cannot be of 'NoneType' type` — لأن `InvitationCreate.custom_message`
   مُعرَّف `Optional[str] = None`، و`data.model_dump()` بيرجع المفتاح
   موجود بقيمة `None` صراحة (مش غايب) فـ`.get(key, "")` **بترجع `None`
   مش `""`** (القيمة الافتراضية بتتفعل بس لو المفتاح غايب تمامًا).
2. أُضيف `custom_message` → نفس الخطأ بالحرف على `target_entity_identifier`
   (سطر 174، نفس السبب بالضبط).
3. أُضيف `target_entity_identifier` → عيار مختلف تمامًا: `500` في
   `_assign_ai_agent` (سطر 108-115):
   ```python
   agents = await agents_repo.list_agents(tenant_id=..., role="SUPPORT")
   return agents[0] if agents else None
   ```
   `AIAgentsRepository.list_agents()` بترجع `PaginatedResponse[AIAgentResponse]`
   (تأكَّد من التوقيع في `app/domains/ai_agents/repository.py:59-67`) —
   **مش** قابلة للفهرسة (`agents[0]`) مباشرة، فترفع
   `TypeError: 'PaginatedResponse[AIAgentResponse]' object is not
   subscriptable`. هذا الاستدعاء **غير مشروط** (مفيش `if` قبله في
   `create_invitation`، سطر 207) — يعني **أي** طلب `POST
   /api/invitations/` لأي تينانت عنده صلاحية CRM فعلية هيفشل بـ`500`
   دايمًا، بغض النظر تمامًا عن `check_feature_access` القديمة أو
   `can_access_service` الجديدة (العيب في كود **بعد** بوابة الـSaaS
   بمراحل).

**التأكيد إن السبب مش `_check_saas_limits`:** كل الـ3 أخطاء فوق حصلت
**بعد** ما `_check_saas_limits` نجحت (لو كانت فشلت كانت هترفع
`PermissionDeniedError`/`403` قبل أي سطر من دول — وده بالظبط اللي حصل
فعليًا في اختبار الرفض لتينانت 1، §7.4.2). صفر لمس لـ`create_invitation`
أو `_assign_ai_agent` في هذه الجلسة (تأكَّد بـ`git diff` §7.2 — التعديل
الوحيد في الملف كله هو `_check_saas_limits`). **لم يُصلَح** — خارج
النطاق الصريح تمامًا، ومكتشَف بالصدفة أثناء محاولة اختبار حي.

#### 7.4.2 النتائج الفعلية (عبر `create_campaign` بعد الالتفاف)

**اختبار 1 — تينانت 16 (معه صلاحية) → متوقَّع نجاح:**

```
POST /api/invitations/campaigns
Authorization: Bearer <JWT لـTEST_instr_b>
{"name":"CRM-CANACCESS-PILOT-TENANT16","description":"pilot test campaign","campaign_type":"SERVICE","start_date":"2026-09-08T00:00:00Z"}
```

```
HTTP_STATUS: 201
{"name":"CRM-CANACCESS-PILOT-TENANT16","description":"pilot test campaign","campaign_type":"SERVICE","target_audience":{},"budget_mrusdt":"0E-8","start_date":"2026-09-08T00:00:00Z","end_date":null,"channels":[],"id":5,"tenant_id":16,"status":"DRAFT","spent_mrusdt":"0E-8","total_leads":0,"converted_leads":0,"created_by":774,"created_at":"2026-09-07T16:08:41.216756Z","updated_at":"2026-09-07T16:08:41.216756Z"}
```

**✅ نجح فعليًا (201، حملة تسويقية حقيقية اتسجَّلت بـ`id=5`)** —
`can_access_service("crm")` رجعت `True` لتينانت 16 من أول محاولة.

**اختبار 2 — تينانت 1 (من غير صلاحية) → متوقَّع رفض (اختُبر مرتين، على
مسارين مختلفين، بنفس النتيجة):**

```
POST /api/invitations/  (create_invitation)          → 403 "CRM feature is not included in your current plan."
POST /api/invitations/campaigns  (create_campaign)    → 403 "CRM feature is not included in your current plan."
```

**✅ رُفض فعليًا في الحالتين** — يثبت إن بوابة `_check_saas_limits`
بترفض بشكل صحيح ومتّسق عبر أكتر من نقطة استدعاء في نفس الدومين، وإن عيب
§7.4.1 معزول تمامًا في `create_invitation` (تحديدًا `_assign_ai_agent`)
ومش له أي تأثير على منطق الصلاحيات نفسه.

### 7.5 فحص ارتداد (regression)

```
pytest tests/test_ai_agents_execute_action.py tests/test_invitations_response_schema_fields_wiring.py tests/test_invitations_savepoint_leak.py tests/test_saas_active_subscription.py -q
```

**النتيجة:** `4 failed, 12 passed`. كل الـ4 فشل في
`test_saas_active_subscription.py` وكلهم **نفس الأربعة الموثَّقين بالضبط
بالفعل في §4.5** (`realestate`/`insurance`، بند backlog #2 المفتوح من
قبل هذه الجلسة) — صفر فشل جديد، صفر فشل خاص بـ`invitations` نفسها.
ملحوظة: `test_ai_agents_execute_action.py` بيعمل `monkeypatch.setattr(
InvitationsService, "_check_saas_limits", ...)` مباشرة (noop) في
اختباراته الخاصة بـ`invitations` — **غير متأثر إطلاقًا** بأي تعديل هنا
بالتصميم.

اختبار إضافي من `test_user_repository_get_by_id_audit.py`:

```
pytest tests/test_user_repository_get_by_id_audit.py::test_invitations_get_user_correct_and_wrong_tenant -q
```

**النتيجة:** `1 failed` — **نفس خلل `_register_affiliate_commission`/
`referred_by` الموثَّق بالفعل في backlog اليوم** (`invitations` كان من
الـ11 دومين المذكورين في `backlog-affiliate-commission-registration-systemwide-broken`).
مش اكتشاف جديد.

### 7.6 ملخص الالتزام بالقيود

| القيد | الحالة |
|---|---|
| دومين `invitations` فقط في هذه الخطوة | ✅ الملف الوحيد المتأثر: `invitations/service.py` |
| ممنوع لمس `check_feature_access` نفسها | ✅ لم تُعدَّل |
| ممنوع لمس فرع `PAST_DUE` | ✅ لم يُلمَس |
| ممنوع أي `router` | ✅ صفر تعديل على `invitations/router.py` |
| بيانات اختبار حقيقية (seed مباشر) | ✅ 5 صفوف + `setval()` فوري على 4 sequences (القاعدة الإلزامية) |
| اختبار حي E2E حقيقي (status code موثَّق) | ✅ 201 (نجاح عبر `create_campaign`) + 403 (رفض، على مسارين) |

**الحالة النهائية لهذا الدومين:** ✅ نجح. صفر فشل regression جديد؛
اكتشاف عيب pre-existing جديد غير متعلق (`create_invitation`/
`_assign_ai_agent`) موثَّق بالكامل في §7.4.1، لم يُصلَح، خارج النطاق. **هذا
كان آخر دومين من الـ7 — راجع §8 للملخص الختامي الشامل لمسار
`check_feature_access`→`can_access_service` بالكامل.**

---

## 8. ملخص ختامي شامل — إغلاق مسار `check_feature_access`→`can_access_service` بالكامل

### 8.1 الحالة النهائية: المسار مُغلَق بالكامل

**كل الـ8 دومينات** اللي كانت بتستخدم `check_feature_access` (`insurance`
في جلسة pilot سابقة + الـ7 المذكورين في هذه الجلسة) بقوا يستخدموا
`can_access_service` دلوقتي. تحقُّق نهائي فعلي (`grep` مباشر، مش من
الذاكرة):

```
$ grep -rl "check_feature_access" app/domains --include=service.py
app/domains/saas/service.py          # التعريف نفسه بس — صفر استدعاء من أي دومين

$ grep -rn "\.check_feature_access(" app --include=*.py | grep -v "app/domains/saas/service.py"
(صفر نتائج)

$ grep -rl "can_access_service\b" app/domains --include=service.py | grep -v "/saas/"
arbitration_syndicates, digital_twin, employment, insurance, invitations,
logistics, manufacturing, realestate, service_marketplace, social,
tenders_auctions, tourism_sports, transport, zamakana   ← 14 دومين
```

**النتيجة:** `check_feature_access` بقت **dead code فعليًا** (لسه موجودة
في `app/domains/saas/service.py` بالضبط زي ما طُلب — "ممنوع لمسها" —
لكن **صفر مُستدعٍ** لها في كل الـ`app/` بعد إغلاق هذا المسار). القرار
بشأن حذفها أو تركها نهائيًا **قرار منفصل خارج نطاق هذه السلسلة من
الجلسات** (لم يُطلب، ولم يُنفَّذ).

### 8.2 جدول ملخص الدومينات السبعة (هذه الجلسة)

| # | الدومين | الفيتشر(ات) المُختبَرة حيًا | Endpoint المُختبَر | نجاح (tenant 16) | رفض (tenant 1) | Regression |
|---|---|---|---|---|---|---|
| 1 | `employment` | `hr_management` | `POST /api/employment/jobs` | 201 | 403 | 1 passed |
| 2 | `digital_twin` | `digital_twin` | `GET /api/digital-twin/config` | 200 | 403 | 6 passed (بعد إصلاح sequence، راجع §2.5) |
| 3 | `arbitration_syndicates` | `syndicates` | `POST /api/arbitration-syndicates/syndicates` | 201 | 403 | 11 failed (كلهم pre-existing، اكتشاف backlog جديد §3.5) |
| 4 | `realestate` | `real_estate` | `POST /api/realestate/lands` | 201 | 403 | 6 failed (3 pre-existing + 3 أثر backlog #2 معروف) |
| 5 | `manufacturing` | `manufacturing` | `POST /api/manufacturing/facilities` | 201 | 403 | 1 failed (pre-existing، نفس backlog #4 — `affiliate`) |
| 6 | `logistics` | `logistics` | `POST /api/logistics/warehouses` | 201 | 403 | 1 passed |
| 7 | `invitations` | `crm` | `POST /api/invitations/campaigns` (بعد اكتشاف عيب في `create_invitation`) | 201 | 403 (×2 مسار) | 4 failed + 1 failed (تشغيلتين منفصلتين، §7.5) — كلهم pre-existing موثَّقين |

**صفر فشل regression جديد ناتج فعليًا عن أي تعديل في `_check_saas_limits`
عبر الـ7 دومينات** — كل فشل تم تحقيقه بالـtraceback الفعلي وتأكيد إنه إما
(أ) pre-existing قبل بدء هذه السلسلة، أو (ب) أثر متوقَّع ومُوثَّق مسبقًا
لعيب `plan.features` النصي القديم (backlog #2)، أو (ج) خلل بنيوي منفصل
في طبقة `affiliate` (backlog جديد اتفتح في جلسة `arbitration_syndicates`).

### 8.3 بيانات الاختبار المُنشأة (كل الـ7 دومينات، بالنمط الموحَّد)

كل دومين حصل على 5 صفوف seed حقيقية بنفس البنية:
`saas_service_catalog` (خدمة جديدة) → `saas_service_plans` (خطة تابعة)
→ `saas_plan_service_access` (الربط many-to-many) →
`saas_tenant_subscriptions` (اشتراك `ACTIVE` لتينانت 16) →
`saas_tenant_service_access` (تفعيل الخدمة لتينانت 16). تينانت 1 لم
يُمس بأي seed في أي دومين — دايمًا سيناريو "من غير صلاحية" الطبيعي.

| الدومين | service_catalog.id | code | service_plans.id | subscriptions.id | tenant_service_access.id |
|---|---|---|---|---|---|
| `employment` | 104 | `hr_management` | 107 | 120 | 52 |
| `digital_twin` | 105 | `digital_twin` | 108 | 121 | 53 |
| `arbitration_syndicates` | 106 | `syndicates` | 109 | 122 | 54 |
| `realestate` | 107 | `real_estate` | 110 | 123 | 55 |
| `manufacturing` | 108 | `manufacturing` | 111 | 124 | 56 |
| `logistics` | 109 | `logistics` | 112 | 125 | 57 |
| `invitations` | 110 | `crm` | 113 | 126 | 58 |

**إجمالي `saas_plan_service_access` الآن: 19 صف** (12 كانوا موجودين من
جلسات سابقة اليوم + 7 من هذه الجلسة) — **كلهم بيانات اختبار/backfill،
صفر بيانات إنتاج حقيقية** (نفس التحذير الموثَّق بالفعل في
`PROGRESS_LOG.md` قبل بدء هذه الجلسة، ينطبق بنفس القوة الآن بعد الزيادة
من 12 لـ19).

### 8.4 القاعدة الإلزامية الجديدة (`setval` فوري) — الأثر والتحقق

اتفعّلت من دومين `arbitration_syndicates` فصاعدًا (3 دومينات:
`arbitration_syndicates`, `realestate`, `manufacturing`, `logistics`,
`invitations` — 5 مرات تنفيذ، **صفر تصادم `UniqueViolationError` بعدها
نهائيًا**). قبل تفعيلها، حادثة واحدة فعلية حصلت في §2.5
(`digital_twin`): seed مباشر بـ`id=` صريح في جلستي `employment`+
`digital_twin` بدون `setval()` فوري خلّى `saas_tenant_subscriptions_id_seq`
متأخرة، فسبّبت `UniqueViolationError` حقيقي لاختبار regression غير
متعلق (`test_saas_subscription_activates_default_affiliate_scope`) —
اتصلحت وقتها ووثِّقت، وبقت قاعدة إلزامية دايمة بعدها. **صفر تكرار لنفس
المشكلة في الدومينات الخمسة اللي طُبِّقت عليهم القاعدة.**

### 8.5 كل بنود الـbacklog المفتوحة الآن (مُجمَّعة، من `PROGRESS_LOG.md` وهذه الجلسة)

| # | البند | نشأ في | الحالة |
|---|---|---|---|
| 1 | فرع `PAST_DUE` في `can_access_service` غير قابل للوصول فعليًا (dead code) | جلسة توحيد `insurance` (قبل هذه السلسلة) | مفتوح، يحتاج قرار تصميمي |
| 2 | `tests/test_saas_active_subscription.py` بيفترض سلوك `plan.features` النصي القديم كـ"نجاح متوقَّع" — ضرب `insurance` أصلًا، وبعدين `realestate`/`invitations` في هذه الجلسة (§4.5, §7.5) | جلسة توحيد `insurance` | مفتوح، يحتاج seed حقيقي جديد للاختبارات المتأثرة |
| 3 | تناقض بورت Redis/Celery في `.env` (`6380` صح لـ`REDIS_URL`، `6379` غلط لـ`CELERY_*`) | جلسة توحيد `insurance` | مفتوح، غير مرتبط بمسار الـSaaS |
| 4 | `backlog-affiliate-commission-registration-systemwide-broken` — `_register_affiliate_commission` بتفشل عبر 11 دومين (`referred_by` مفقود) | جلسة `arbitration_syndicates` (هذه السلسلة) | مفتوح، أولوية عالية، مُضاف لـ`PROGRESS_LOG.md` بطلب المستخدم |
| 5 | **جديد [2026-09-07]** — `InvitationsService.create_invitation` مكسورة بالكامل (`500`) لأي تينانت عنده صلاحية CRM فعلية، بسبب `_assign_ai_agent` بتحاول `agents[0]` على `PaginatedResponse` غير قابلة للفهرسة (§7.4.1) | جلسة `invitations` (هذه الجلسة، اكتشاف عرضي أثناء الاختبار الحي) | **غير مُضاف لـ`PROGRESS_LOG.md` بعد** — موثَّق في هذا التقرير فقط، ينتظر توجيه المستخدم |

**ملاحظة:** بند #5 جديد ولم يُطلب إضافته لـ`PROGRESS_LOG.md` صراحة —
موثَّق هنا بالتفصيل الكامل (§7.4.1) تحسّبًا، وجاهز للإضافة لو المستخدم
طلب ذلك.

### 8.6 التزام القيود الثابتة عبر كل الـ7 جلسات (بدون استثناء واحد)

| القيد | الحالة عبر كل الدومينات السبعة |
|---|---|
| دومين واحد في كل مرة، بموافقة صريحة قبل التالي | ✅ 7/7 — توقف فعلي بعد كل دومين، انتظار رد المستخدم |
| ممنوع لمس `check_feature_access` نفسها | ✅ 7/7 — صفر سطر تعديل عليها (تأكَّد نهائيًا §8.1) |
| ممنوع لمس فرع `PAST_DUE` | ✅ 7/7 — لم يُلمَس، لسه backlog #1 مفتوح |
| ممنوع أي `router` | ✅ 7/7 — صفر تعديل على أي ملف `router.py` |
| بيانات اختبار حقيقية (seed مباشر، لا mocks) | ✅ 7/7 — 35 صف seed إجمالًا (5 × 7)، كلها عبر `docker exec psql` مباشر |
| اختبار حي E2E حقيقي (status code فعلي موثَّق) | ✅ 7/7 — نجاح (200/201) + رفض (403) موثَّقين حرفيًا لكل دومين |
| `setval()` فوري بعد أي `id=` صريح (من `arbitration_syndicates` فصاعدًا) | ✅ 5/5 (الدومينات اللي طُبِّقت عليهم القاعدة) — صفر تصادم لاحق |

**الحالة النهائية لكامل السلسلة:** ✅ **مُغلَقة بالكامل** — 8/8 دومين
(`insurance` + 7) بقوا يستخدموا `can_access_service`، `check_feature_access`
بقت dead code مُتحقَّق منه، صفر انتهاك لأي قيد عبر كل الجلسات السبع، وكل
فشل regression ظهر أثناء الطريق تم تحقيقه وربطه بسبب جذري مؤكَّد (إما
pre-existing أو backlog مفتوح بالفعل).
