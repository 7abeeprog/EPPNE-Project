# جلسة إصلاح سوء استخدام PaginatedResponse — سجل تنفيذ

النطاق: إصلاح 3 حالات موثَّقة في `paginatedresponse-misuse-audit-session-log.md`،
واحدة في كل مرة، بموافقة صريحة بين كل حالة والتالية. الترتيب: invoicing →
academy → automation.

---

## الحالة 1: `invoicing/router.py:159`

### التعديل المُنفَّذ

`app/domains/invoicing/router.py:159` — قبل:
```python
items = [InvoiceResponse.model_validate(inv) for inv in invoices]
```
بعد:
```python
items = [InvoiceResponse.model_validate(inv) for inv in (invoices.data if hasattr(invoices, "data") else invoices)]
```

**سبب استخدام `hasattr` بدل `.data` المباشر (زي نمط invitations/ai_agents):**
هذا الـendpoint فيه فرعين مختلفين يُسندان لنفس المتغير `invoices` (سطر
138-157): الفرع الأول (`tenant_id is None`، أدمن عام) بيرجّع `list[Invoice]`
عادي من استعلام SQL خام. الفرع التاني (`tenant_id` محدَّد — **المسار
الافتراضي لكل مستخدم عادي**) بيرجّع `PaginatedResponse[InvoiceResponse]` من
`service.list_invoices`. تعديل سطر 159 فقط (بدون لمس أي سطر تاني في
الـendpoint، حسب المطلوب) يحتاج التعامل مع الحالتين معًا — فاستخدمت فحص
`hasattr` بدل `.data` مباشر لأن الفرع الأول لسه بيرجّع list عادي مالوش
`.data`.

### 🔴 اكتشاف جديد يوقف الاختبار الحي — خارج نطاق السطر المحدَّد لهذه الحالة

الاختبار الحي بمستخدم حقيقي (تفاصيل تحت) كشف إن endpoint `GET /invoices`
**لسه بيرجع 500 حتى بعد إصلاح سطر 159**، لكن **لسبب مختلف تمامًا** غير
موثَّق في التدقيق الأصلي:

- **المكان:** `app/domains/invoicing/repository.py:110-114`
  ```python
  return PaginatedResponse[InvoiceResponse](
      items=items,      # ❌ اسم الحقل غلط
      total=total,
      skip=skip,
      limit=limit
  )
  ```
- **العطل الفعلي (من الـtraceback الحي):**
  ```
  pydantic_core._pydantic_core.ValidationError: 1 validation error for PaginatedResponse[InvoiceResponse]
  data
    Field required [type=missing, input_value={'items': [InvoiceRespons... 'skip': 0, 'limit': 50}, input_type=dict]
  ```
  حقل `PaginatedResponse` (`app/core/pagination.py:12`) اسمه `data` مش
  `items`. يعني `list_invoices` في الـ**repository نفسه** بيفشل في بناء
  الكائن **قبل ما يوصل حتى لسطر 159 في الـrouter** — الـException بيتصاير
  جوه `service.py:141` ← `repository.py:110`، مش في الـrouter.
- **الأثر:** إصلاح سطر 159 (موضوع هذه الحالة) **صحيح ومطلوب**، لكنه وحده
  **مش كافي** لجعل `GET /invoices?tenant_id=<رقم>` يرجع نجاح فعلي — الـpath
  بيوقع في هذا العطل الأعمق قبل ما يوصل لسطر الـrouter المُصلَّح أصلًا.
- **ليه ده مش داخل نطاق هذه المهمة:** التعليمات صريحة — "ممنوع أي تعديل
  خارج السطر/السطور المحدَّدة في كل حالة" (`invoicing/router.py:159` فقط).
  هذا عطل في ملف وسطر مختلفين تمامًا (`repository.py:110`)، ولم يكن موثَّقًا
  في تدقيق `paginatedresponse-misuse-audit-session-log.md` الأصلي (التدقيق
  افترض إن `list_invoices` بترجع `PaginatedResponse` صالح، ولم يتحقق من نجاح
  بنائه فعليًا لأنه كان قراءة ثابتة بحتة بدون تشغيل).

**قرار المستخدم:** توسيع ضيّق لنطاق الحالة 1 فقط — تصحيح اسم الحقل في
`repository.py:110` من `items=items` إلى `data=items`، بلا أي تغيير آخر في
نفس الدالة أو أي دالة حواليها، ثم إعادة نفس الاختبار الحي بالضبط.

### التصحيح الإضافي المُنفَّذ (بموافقة صريحة)

`app/domains/invoicing/repository.py:110-114` — قبل:
```python
return PaginatedResponse[InvoiceResponse](
    items=items,
    total=total,
    skip=skip,
    limit=limit
```
بعد (تصحيح اسم الحقل فقط):
```python
return PaginatedResponse[InvoiceResponse](
    data=items,
    total=total,
    skip=skip,
    limit=limit
```
لا تغيير آخر في الدالة (`list_invoices`) ولا في أي دالة أخرى في نفس الملف.

### الاختبار الحي — الجولة الأولى (نتيجتها: 500، عطل مختلف عن سطر 159)

- **بيئة:** `eppne-backend` محليًا، `uvicorn` على `127.0.0.1:8000`،
  DB الحقيقي (`eppne_v2`, `localhost:5435`, حاوية `eppne_db`).
- **المستخدم:** `TEST_super_a` (id=772, tenant_id=1, `SUPER_ADMIN`) —
  حساب throwaway موثَّق في `throwaway-test-users.md`، كلمة السر
  `TEST_pass_batch3_2026` (لسه صالحة، تم التحقق بـ`GET /identity/login`
  → 200).
- **بيانات حقيقية مستهدفة:** فواتير حقيقية موجودة فعليًا في `tenant_id=1`
  (تحقَّق عبر `psql` مباشرة: `id=4,5,6,7,8...`، حالات `PENDING`، مستخدمين
  فعليين مثل `p_ctor_re_buyer@example.com`).
- **الاستدعاء:** `GET /api/invoicing/invoices?tenant_id=1` (بتوكن
  `Bearer` من `POST /api/identity/login`) — هذا يُفعِّل عمدًا **الفرع
  الثاني** (`tenant_id` محدَّد) وهو المسار الذي كان معطوبًا في سطر 159.
- **النتيجة:** `HTTP 500` — لكن الـtraceback في `paginatedresponse_fix_uvicorn.log`
  يثبت إن الفشل صار في `repository.py:110` (`ValidationError` على حقل
  `data` المفقود)، **قبل تنفيذ سطر 159 المُصلَّح أصلًا**. يعني إصلاح سطر 159
  لم يُختبر فعليًا حيًا بنجاح كامل — تم التحقق إنه **منطقيًا صحيح** (قراءة
  كود) لكن لم يُشاهَد ينفَّذ بنجاح على بيانات حقيقية بسبب العطل الأعمق.

### Regression

لا يوجد أي ملف اختبار مخصص لدومين `invoicing` في `eppne-backend/tests/`
(تأكيد عبر `grep -rl invoicing tests/` — 8 نتائج، كلها ملفات دومينات تانية
(saas, realestate, ai_governance...) بتشير لـ invoicing بشكل عرضي فقط، مفيش
حتى ملف واحد اسمه `test_invoicing*`). لا يوجد regression suite لتشغيله لهذا
الدومين تحديدًا.

### الاختبار الحي — الجولة الثانية (بعد تصحيح `repository.py:110`)

- **نفس البيئة/المستخدم/التوكن بالضبط:** إعادة تشغيل `uvicorn` فقط (كان
  بدون `--reload`، فاحتاج إعادة تشغيل يدوية ليلتقط تعديل `repository.py`)،
  ثم نفس تسلسل `POST /api/identity/login` (`TEST_super_a` /
  `TEST_pass_batch3_2026`) ← `GET /api/invoicing/invoices?tenant_id=1`
  بنفس الـ`Bearer` token.
- **النتيجة:** `HTTP 200` ✅ — رد فعلي يحتوي فواتير حقيقية موجودة في
  `tenant_id=1` (مش بيانات وهمية): مثال من الرد الفعلي —
  `id=17, invoice_number="INV-1-000015", amount="20.00000000", user_id=117,
  description="Insurance premium: P-SAAS9-VERIFY-POLICY-8fa402", status="PENDING"`
  وكذلك `id=16` (rent invoice)، `id=15` (time pledge)، `id=14`
  (insurance premium)، `id=13` (rent)، `id=11` (event ticket)، `id=10`
  ("B3 invoicing router test invoice") وغيرها — كلها سجلات حقيقية من
  الجدول، مش mock. الاستجابة كانت قائمة JSON صالحة (`items` — مفتاح
  الاستجابة النهائية عبر `InvoiceListResponse`، غير مرتبط بحقل `data`
  الداخلي في `PaginatedResponse` المُصحَّح) بدون أي `ValidationError` أو
  `500`.
- **لا عطل ثالث ظهر.** المسار الافتراضي لكل مستخدم عادي (`tenant_id`
  محدَّد) بقى شغّال فعليًا من طرف لطرف: `router.py:151` (استدعاء الخدمة) →
  `service.py:141` → `repository.py:110` (بناء `PaginatedResponse` صحيح
  الآن) → `router.py:159` (استخراج `.data` صحيح الآن) → استجابة `200`
  فعلية.

### Regression

لا يوجد أي ملف اختبار مخصص لدومين `invoicing` في `eppne-backend/tests/`
(تأكيد عبر `grep -rl invoicing tests/` — 8 نتائج، كلها ملفات دومينات تانية
(saas, realestate, ai_governance...) بتشير لـ invoicing بشكل عرضي فقط، مفيش
حتى ملف واحد اسمه `test_invoicing*`). لا يوجد regression suite لتشغيله لهذا
الدومين تحديدًا — لا شيء تغيّر في هذا التقييم بعد التصحيح الإضافي.

### ملخّص التعديلات النهائية لهذه الحالة (سطرين فقط، في ملفين)

1. `app/domains/invoicing/router.py:159` — استخدام `.data`/list مباشر حسب
   الفرع بدل تكرار كائن `PaginatedResponse` كأنه list.
2. `app/domains/invoicing/repository.py:110` — تصحيح اسم الحقل
   `items=` → `data=` عند بناء `PaginatedResponse[InvoiceResponse]`.

### الحالة: ✅ مكتملة ومُختبرة حيًا بنجاح فعلي (200 + فواتير حقيقية في الرد)

**موافقة المستخدم على الحالة 1 بالكامل — تم الانتقال للحالة 2.**

---

## الحالة 2: `academy/router.py:248`

### التعديل المُنفَّذ

`app/domains/academy/router.py:248` (endpoint `GET /store/courses`) — قبل:
```python
tenant_id = cast(int, current_user.tenant_id)
service = AcademyService(db, tenant_id)
return await service.get_store_courses(cast(int, current_user.id), skip=skip, limit=limit)
```
بعد:
```python
tenant_id = cast(int, current_user.tenant_id)
service = AcademyService(db, tenant_id)
result = await service.get_store_courses(cast(int, current_user.id), skip=skip, limit=limit)
return result.data
```
نفس النمط بالضبط المستخدم في باقي endpoints في نفس الملف (مثال:
`get_course_units`، `router.py:352-353` — `result = await service...` ثم
`return result.data`). لا تغيير في `service.py` ولا `repository.py` — تم
التحقق مسبقًا (في جلسة التدقيق) إن `repository.py:308`
(`list_published_courses`) بيبني `PaginatedResponse(data=items, ...)` **صح**
من الأساس (خلافًا لعطل invoicing) — يعني العطل هنا كان في الـrouter فقط.

### الاختبار الحي

- **نفس الخادم/البيئة:** إعادة تشغيل `uvicorn` (بدون `--reload`) بعد
  التعديل، انتظار اكتمال `create_indexes` عند الإقلاع، ثم نفس تسلسل تسجيل
  الدخول.
- **المستخدم:** نفس `TEST_super_a` (id=772, tenant_id=1, `SUPER_ADMIN`) —
  `POST /api/identity/login` → `200`.
- **بيانات حقيقية مستهدفة:** كورسات حقيقية منشورة (`is_published=true`,
  `is_active=true`) في `tenant_id=1`، تحقَّق منها عبر `psql` مباشرة على جدول
  `academy_courses` (اسم الجدول الفعلي، مختلف عن `courses` — تم تصحيح
  الاستعلام بعد فشل أول محاولة بـ`relation "courses" does not exist`):
  مثال `id=2 TEST_COURSE_A_PAID`, `id=3 TEST_COURSE_A_FREE`,
  `id=7 TEST_COURSE_C2_FULL`, إلخ.
- **الاستدعاء:** `GET /api/academy/store/courses` (بتوكن `Bearer` من نفس
  الـlogin).
- **النتيجة:** `HTTP 200` ✅ — رد فعلي (JSON list) يحتوي 9 كورسات حقيقية من
  `tenant_id=1`، من ضمنها `id=2 "TEST_COURSE_A_PAID"` (`price_mrusdt=
  "100.00000000"`, `is_published=true`), `id=3 "TEST_COURSE_A_FREE"`
  (`is_free=true`, `price_mrusdt="0E-8"`), `id=7 "TEST_COURSE_C2_FULL"`،
  وغيرها — كلها سجلات فعلية من الجدول، مش mock. لا `ResponseValidationError`
  ولا `500`.
- **لا عطل ثالث ظهر** (لا تسمية حقل غلط ولا أي شيء غير متوقَّع) — المسار
  كامل من طرف لطرف اشتغل من أول محاولة بعد التعديل الوحيد في الراوتر.

### Regression

لا يوجد ملف اختبار مخصص لدومين `academy` في `eppne-backend/tests/`
(تأكيد عبر `grep -rl academy tests/` — 5 نتائج فقط، كلها ملفات دومينات تانية
(`referral_affiliate`, `security_deps_unification`, `tourism_sports`,
`transport_vehicles_fleets_drivers`, وملف `.md` واحد) بتشير لـ academy
بشكل عرضي فقط). تأكيد إضافي: `grep -rl "store/courses\|get_store_courses"
tests/` — صفر نتائج. لا يوجد regression suite لتشغيله لهذا الدومين أو لهذا
الـendpoint تحديدًا.

### ملخّص التعديل النهائي لهذه الحالة (سطر واحد أصبح سطرين، في ملف واحد)

`app/domains/academy/router.py:248` — استخراج `.data` من نتيجة الخدمة قبل
الإرجاع، بدل إرجاع كائن `PaginatedResponse` كامل تحت
`response_model=list[CourseResponse]`.

### الحالة: ✅ مكتملة ومُختبرة حيًا بنجاح فعلي (200 + كورسات حقيقية في الرد) — نجحت من أول محاولة، بلا أي عطل إضافي مكتشف

**موافقة المستخدم على الحالة 2 بالكامل — تم الانتقال للحالة 3.**

---

## الحالة 3: `automation/service.py:1045`

### التعديل المُنفَّذ

`app/domains/automation/service.py:1045` (داخل `list_available_agents`) — قبل:
```python
        return [
            {
                "id": agent.id,
                "name": agent.name,
                "role": agent.role.value if hasattr(agent.role, 'value') else str(agent.role),
                "can_execute_payments": agent.can_execute_payments,
                "can_sign_contracts": agent.can_sign_contracts,
            }
            for agent in agents
        ]
```
بعد:
```python
            for agent in agents.data
```
(السطر الوحيد المُعدَّل: `for agent in agents` → `for agent in agents.data`.)
تحقَّقت أولًا من `AIAgentsRepository.list_agents`
(`ai_agents/repository.py:89-94`) إن بنائها لـ`PaginatedResponse` **صحيح
من الأساس** (`data=items`، خلافًا لعطل invoicing) — يعني العطل هنا مقصور
على سطر `automation/service.py` فقط، زي ما كان موثَّق في التدقيق.

### 🔴 توقف قبل تنفيذ الاختبار الحي — بيانات حقيقية غير موجودة أصلًا

الـendpoint المتأثر هو `GET /automation/ai-agents`
(`automation/router.py:219-233`) — بيستدعي
`service.list_available_agents(tenant_id=tenant.id, user_id=current_user.id)`
اللي بدورها بتفلتر `AIAgentsRepository.list_agents(tenant_id=...,
owner_id=user_id, status="ACTIVE")`.

تحقَّقت من وجود بيانات حقيقية قبل الاستدعاء (نفس المنهجية المتبعة في
الحالتين السابقتين) عبر `psql` مباشرة على جدول `ai_agents`:
```sql
SELECT id, tenant_id, owner_id, name, status, is_deleted FROM ai_agents;
```
**النتيجة: 0 صفوف — الجدول فاضي تمامًا في هذه القاعدة، بغض النظر عن
الحالة (`ACTIVE` أو غيرها).** هذا مختلف عن الحالتين السابقتين (invoicing/
academy) اللي كان فيهم بيانات throwaway حقيقية جاهزة من جلسات سابقة.

**لماذا توقفت بدل ما أوسّع من نفسي:** المطلوب صراحة هو اختبار حي بـ"وكيل
AI حقيقي" ينتج "نتيجة ناجحة فعلية موثّقة" بمحتوى حقيقي في الرد — نفس معيار
invoicing/academy. بما إن الجدول فاضي، مفيش طريقة أعمل هذا الاختبار بدون
أحد الخيارين التاليين، وكلاهما يغيّر نطاق العمل عن مجرد "تعديل السطر
واختبار حي":

1. **إنشاء وكيل حقيقي عبر الـAPI الرسمي** (`POST /api/ai-agents/agents`،
   endpoint موجود فعلاً في `ai_agents/router.py:28`) — مملوك لنفس مستخدم
   الاختبار، `status=ACTIVE`، ثم استدعاء `GET /automation/ai-agents` عليه.
   هذا وكيل "حقيقي" بمعنى إنه بيتولد من نفس منطق التطبيق الفعلي (مش SQL
   مباشر)، لكنه بيانات جديدة اتخلقت خصيصًا للاختبار، مش بيانات موجودة
   مسبقًا.
2. اعتبار عدم وجود بيانات = تعذّر إجراء اختبار حي بمحتوى فعلي لهذه الحالة
   تحديدًا، وتوثيق الاعتماد فقط على قراءة الكود (زي حالات "✅ صح" الأخرى في
   التدقيق الأصلي التي اعتمدت على استنتاج القراءة الثابتة) + تشغيل ناجح بلا
   استثناء (200 وقائمة فاضية `[]`، من غير محتوى فعلي يُثبت صحة تحويل
   `.data` على بيانات حقيقية).

**قرار المستخدم:** الخيار الأول — إنشاء وكيل حقيقي عبر الـAPI الرسمي
(`role="SUPPORT"`)، مملوك لـ`TEST_super_a`، `status=ACTIVE`، ويُترك موجودًا
بعد الاختبار (مش throwaway يُحذف فورًا) ويُوثَّق في
`throwaway-test-users.md`.

### إنشاء بيانات الاختبار الحقيقية (بموافقة صريحة)

1. **إنشاء الوكيل** — `POST /api/ai/agents` (بتوكن `TEST_super_a`،
   `SUPER_ADMIN`، مؤهَّل لـ`get_current_superuser`):
   ```json
   {"name": "TEST_automation_support_agent", "role": "SUPPORT",
    "system_prompt": "Throwaway test agent for automation PaginatedResponse live-test verification.",
    "base_model": "gemini-1.5-pro", "can_execute_payments": false,
    "can_sign_contracts": false, "requires_human_approval": true,
    "interaction_cost_mrusdt": 0}
   ```
   → `201`، `id=216`, `status="IDLE"` (الافتراضي عند الإنشاء —
   `models.py:52`، `default=AgentStatus.IDLE`)، `owner_id=772`,
   `tenant_id=1`.
2. **تفعيله** — `PATCH /api/ai/agents/216/status` مع `{"status": "ACTIVE"}`
   → `200`، `"status":"ACTIVE"` مؤكَّد في الرد.

المسارين الحقيقيين المُستخدَمين هما `/api/ai/agents` و
`/api/ai/agents/{id}/status` (تم التأكد من المسار الفعلي عبر `openapi.json`
حيًا — مسار الـrouter الداخلي `/ai` مع mount `/ai-agents` في `main.py`
بينتج `/api/ai/agents`، مش `/api/ai-agents/agents` كما قد يُفترض من اسم
الـmount).

### الاختبار الحي النهائي

- **الاستدعاء:** `GET /api/automation/ai-agents` (بنفس توكن
  `TEST_super_a`، بعد إعادة تشغيل `uvicorn` لالتقاط تعديل
  `automation/service.py`).
- **النتيجة:** `HTTP 200` ✅ — الرد:
  ```json
  [{"id":216,"name":"TEST_automation_support_agent","role":"SUPPORT","can_execute_payments":false,"can_sign_contracts":false}]
  ```
  الوكيل الحقيقي اللي اتعمل بالـAPI الرسمي (`id=216`, `role=SUPPORT`)
  ظهر فعليًا في الرد — **مش قائمة فاضية** — وده الدليل الحقيقي المطلوب على
  نجاح `agents.data` في استخراج العناصر الصحيحة من `PaginatedResponse`
  بدل الفشل بـ`AttributeError` على tuples (العطل الأصلي الموثَّق في
  التدقيق). لا `AttributeError` ولا `500` ولا أي عطل ثالث ظهر.

### البيانات المتروكة بعد الاختبار (بقرار المستخدم)

الوكيل `id=216` (`TEST_automation_support_agent`, `SUPPORT`, `ACTIVE`,
`owner_id=772`, `tenant_id=1`) **تُرك موجودًا عمدًا** — موثَّق بالتفصيل في
`throwaway-test-users.md` (قسم جديد "بيانات throwaway إضافية غير-مستخدمين
(AI Agents)") لأي جلسة قادمة تحتاج وكيل AI حقيقي `ACTIVE` جاهز.

### Regression

لا يوجد ملف اختبار مخصص لدومين `automation` أو لـ`list_available_agents`/
`GET /automation/ai-agents` تحديدًا في `eppne-backend/tests/` (تأكيد عبر
`grep -rl "list_available_agents\|automation/ai-agents" tests/` — صفر
نتائج). لا يوجد regression suite لتشغيله.

### ملخّص التعديل النهائي لهذه الحالة (سطر واحد، في ملف واحد)

`app/domains/automation/service.py:1045` — `for agent in agents` →
`for agent in agents.data`.

### الحالة: ✅ مكتملة ومُختبرة حيًا بنجاح فعلي (200 + وكيل AI حقيقي فعلي
في الرد، مش قائمة فاضية)

---

## الخلاصة النهائية — الحالات الثلاث

| الحالة | الملف/السطر المُعدَّل | نتيجة الاختبار الحي | ملاحظة |
|---|---|---|---|
| 1. `invoicing` | `router.py:159` + `repository.py:110` (عطل إضافي مكتشف بموافقة) | ✅ 200 + فواتير حقيقية | أخطر حالة — يصيب أغلبية المستخدمين |
| 2. `academy` | `router.py:248` (سطر واحد) | ✅ 200 + كورسات حقيقية | نجحت من أول محاولة، بلا عطل إضافي |
| 3. `automation` | `service.py:1045` (سطر واحد) | ✅ 200 + وكيل AI حقيقي فعلي | احتاج إنشاء بيانات اختبار حقيقية عبر الـAPI الرسمي (لم تكن موجودة أصلًا) |

**الثلاث حالات المؤكَّدة في تدقيق `paginatedresponse-misuse-audit-session-log.md`
تم إصلاحها واختبارها حيًا بنجاح فعلي، كل واحدة بموافقة صريحة منفصلة قبل
الانتقال للتالية.** لم يُلمَس أي كود خارج الأسطر المحدَّدة لكل حالة (عدا
التوسيع الضيّق المُوافَق عليه صراحةً في حالة invoicing). لم تُلمَس أي حالة
مصنَّفة "✅ صح" في التدقيق الأصلي، ولا أي "كود ميت" (`commerce.get_user_addresses`
وغيرها).
