# تقرير جلسة — إصلاح `create_invitation`/`_assign_ai_agent` (4 أعطال)

**نوع الجلسة:** إصلاح كود محدود النطاق — **الأربعة أعطال فقط، مفيش أي
تعديل تاني**.

**البند في `PROGRESS_LOG.md`:** `backlog-invitations-create-invitation-broken`.

**مرجع التحقيق الكامل قبل هذا الإصلاح:**
`.claude/reports/invitations-create-invitation-investigation-session-log.md`
(جلسة read-only سابقة، صفر تعديل كود، وثّقت الأربعة أعطال بترتيب
التنفيذ الفعلي مع traceback كامل لكل واحد).

---

## 1) التعديلات المُطبَّقة (`eppne-backend/app/domains/invitations/service.py`)

### 1.1 السطور 172–174 — `bleach.clean(None)` على 3 حقول

**قبل:**
```python
sanitized_title = bleach.clean(data.get("title", ""), tags=[], strip=True)
sanitized_message = bleach.clean(data.get("custom_message", ""), tags=[], strip=True)
sanitized_identifier = bleach.clean(data.get("target_entity_identifier", ""), tags=[], strip=True)
```

**بعد:**
```python
sanitized_title = bleach.clean(data.get("title") or "", tags=[], strip=True)
sanitized_message = bleach.clean(data.get("custom_message") or "", tags=[], strip=True)
sanitized_identifier = bleach.clean(data.get("target_entity_identifier") or "", tags=[], strip=True)
```

**السبب:** `.get(key, "")` بيرجّع الـdefault (`""`) بس لو المفتاح
**غايب تمامًا** من الـdict — لكن `data.model_dump()` (من الراوتر) بيرجّع
كل المفاتيح دايمًا، حتى لو `None` (لأن `title`/`custom_message`/
`target_entity_identifier` كلهم `Optional[... ] = None` في
`InvitationCreate`). يعني `.get(key, "")` كانت بترجع `None` صراحة مش
`""`، و`bleach.clean(None)` بيرمي `TypeError`. `x or ""` بيحوّل
`None` (وكمان `""` الفاضية أصلًا) لـ`""` بأمان قبل ما توصل لـ`bleach`.

### 1.2 السطر 115 (`_assign_ai_agent`) — `PaginatedResponse` غير قابلة للفهرسة

**قبل:**
```python
return agents[0] if agents else None
```

**بعد:**
```python
return agents.data[0] if agents.data else None
```

**السبب:** `AIAgentsRepository.list_agents()` بترجّع
`PaginatedResponse[AIAgentResponse]` (`pydantic.BaseModel` عادي بدون
`__getitem__`) — العناصر الفعلية في `.data` (نفس النمط المستخدم فعلًا
وبشكل صحيح في `ai_agents/router.py:60`: `return result.data`). الشرط
`agents.data` (مش `agents`) صح كمان من ناحية الـtruthiness — قايمة
فاضية `[]` بترجع `False` بشكل طبيعي، بعكس كائن `PaginatedResponse`
نفسه اللي كان دايمًا truthy بغض النظر عن محتواه.

### 1.3 تأكيد النطاق — `git diff` كامل للملف

```diff
-        return agents[0] if agents else None
+        return agents.data[0] if agents.data else None
...
-        sanitized_title = bleach.clean(data.get("title", ""), tags=[], strip=True)
-        sanitized_message = bleach.clean(data.get("custom_message", ""), tags=[], strip=True)
-        sanitized_identifier = bleach.clean(data.get("target_entity_identifier", ""), tags=[], strip=True)
+        sanitized_title = bleach.clean(data.get("title") or "", tags=[], strip=True)
+        sanitized_message = bleach.clean(data.get("custom_message") or "", tags=[], strip=True)
+        sanitized_identifier = bleach.clean(data.get("target_entity_identifier") or "", tags=[], strip=True)
```

**ملاحظة:** الملف كان فيه بالفعل تعديل غير مرتبط من قبل بدء هذه
الجلسة (توحيد `_check_saas_limits` على `can_access_service` — جلسة
`remaining-7-domains-can-access-service-migration`، موثَّق مسبقًا).
هذا التعديل **لم يُلمَس ولم يُضاف له أي شيء** في هذه الجلسة — أُكِّد
بفحص الـ`diff` بالكامل، وبمقارنة قبل/بعد الإصلاح (§4 تحت).

---

## 2) الاختبار الحي رقم 1 — نفس سيناريو التحقيق بالضبط (كل الحقول الاختيارية `None` صراحة)

**الطريقة:** نفس منهجية جلسة التحقيق — استدعاء
`InvitationsService(db).create_invitation()` مباشرة (بلا HTTP/JWT)،
ضد قاعدة بيانات حقيقية، `tenant_id=16` (اشتراك `crm` فعلي `ACTIVE`)،
`sender_id=774` (`TEST_instr_b`).

**البيانات المُرسَلة (`InvitationCreate(...).model_dump()`):**
```
invitation_type = InvitationType.GENERAL
target_type = InvitationTargetType.PERSON
target_user_id = None
target_entity_identifier = None
custom_message = None
title = None
campaign_type = CampaignType.SERVICE
campaign_id = 1
discount_percentage = Decimal('0.0')
gift_coins_amount = Decimal('0.0')
gift_currency = None
max_uses = 1
expires_at = None
```

**النتيجة الفعلية:**
```
2026-09-07 23:36:18 [INFO] eppne.audit: {"action": "INVITATION_CREATED", "user_id": 774,
  "tenant_id": 16, "resource_id": 71, "details": {"title": ""}}

✅ SUCCESS — invitation created:
  id=71
  tenant_id=16
  title=''
  custom_message=''
  target_entity_identifier=''
  assigned_ai_agent_id=None
  status=InvitationStatus.DRAFT
```

**نجحت بالكامل — 201 معادِل (إنشاء ناجح، دعوة حقيقية اتسجَّلت
بـ`id=71`).** الحقول الفاضية اتحوَّلت لـ`""` بأمان بدل ما تكسر
`bleach.clean`. `assigned_ai_agent_id=None` لأن `tenant_id=16` **مفيش
عنده أصلًا أي `AIAgent` بـ`role="SUPPORT"`** (اتأكَّد بالاستعلام
المباشر: 0 صفوف — تفاصيل §5) — يعني فرع "لقى وكيل" في
`_assign_ai_agent` (`agents.data[0]`) **لم يُختبَر حيًا** في هذه
الجلسة لعدم توفر بيانات حقيقية له، لكن فرع "مفيش وكلاء"
(`agents.data` فاضية → `None`) اتأكَّد إنه بيشتغل بأمان بدل ما يفشل
زي قبل الإصلاح.

---

## 3) الاختبار الحي رقم 2 — كل الحقول بقيم حقيقية (تأكيد عدم كسر المسار العادي)

**البيانات المُرسَلة:**
```
invitation_type = InvitationType.GENERAL
target_type = InvitationTargetType.PERSON
target_user_id = None
target_entity_identifier = 'FIXVERIFY-ENTITY-7bcfcdc0'
custom_message = 'مرحباً، هذه رسالة دعوة حقيقية للاختبار'
title = 'FIXVERIFY-TITLE-7bcfcdc0'
campaign_type = CampaignType.SERVICE
campaign_id = 1
discount_percentage = Decimal('15.0')
gift_coins_amount = Decimal('5.0')
gift_currency = 'MR_USDT'
max_uses = 3
expires_at = None
```

**النتيجة الفعلية:**
```
2026-09-07 23:36:19 [INFO] eppne.audit: {"action": "INVITATION_CREATED", "user_id": 774,
  "tenant_id": 16, "resource_id": 72, "details": {"title": "FIXVERIFY-TITLE-7bcfcdc0"}}

✅ SUCCESS — invitation created:
  id=72
  tenant_id=16
  title='FIXVERIFY-TITLE-7bcfcdc0'
  custom_message='مرحباً، هذه رسالة دعوة حقيقية للاختبار'
  target_entity_identifier='FIXVERIFY-ENTITY-7bcfcdc0'
  assigned_ai_agent_id=None
  status=InvitationStatus.DRAFT
```

**نجحت بالكامل — الحقول النصية الحقيقية اتحفظت زي ما هي (بعد تنظيف
`bleach` العادي، بلا أي تغيير في المحتوى لأنه أصلًا نص نظيف بلا HTML)،
والحقول الرقمية (`discount_percentage`, `gift_coins_amount`,
`max_uses`) اتحفظت بقيمها المُرسَلة.** يثبت إن `x or ""` ماأثَّرش على
أي قيمة نصية حقيقية غير فاضية (المسار العادي سليم 100%).

---

## 4) تأكيد صفر تلوث DB بعد الاختبارين

```python
DELETE FROM sovereign_invitations_v2 WHERE id IN (71, 72);
```
نُفِّذ فورًا بعد كل اختبار (`cleanup()` في سكريبت الاختبار)، واتأكَّد
بـ`SELECT` مباشر بعده:
```
remaining rows for ids [71,72]: 0
```

---

## 5) فحص جانبي (اكتشاف موثَّق، **لم يُلمَس** — خارج النطاق الصريح)

أثناء التحقق من الشكل الصحيح للتعامل مع `PaginatedResponse`، وُجد
استخدام صحيح مماثل فعلًا في `ai_agents/router.py:60`
(`return result.data  # ✅ تم التعديل: items -> data`) — يؤكد إن
`.data` هو النمط المعتمد في المشروع.

**لكن** وُجد أيضًا استخدام **بنفس نمط العطل** (تكرار مباشر بلا
`.data`) في مكان تالت غير `_assign_ai_agent`:

```python
# app/domains/automation/service.py:1032 — list_available_agents()
agents = await repo.list_agents(tenant_id=tenant_id, owner_id=user_id, status="ACTIVE")
return [
    {"id": agent.id, "name": agent.name, ...}
    for agent in agents   # ⚠️ نفس فئة العطل — بس بشكل مختلف
]
```

**تأكَّد حيًا (بمعزل عن أي DB):** التكرار المباشر على كائن
`PaginatedResponse` (`pydantic.BaseModel`) عبر `for x in agents`
بيرجّع **tuples** بصيغة `(field_name, value)` (`("data", [...])`,
`("total", ...)`, إلخ) — مش عناصر `AIAgentResponse` — يعني
`agent.id`/`agent.name` جوه الـcomprehension هيفشل بـ
`AttributeError: 'tuple' object has no attribute 'id'` لأول عنصر
(`"data"`). **هذا عطل مختلف تمامًا (pre-existing)، في دومين
`automation` مش `invitations`، وخارج النطاق الصريح المطلوب في هذه
الجلسة ("مفيش أي تعديل تاني") — لم يُصلَح، موثَّق هنا للشفافية فقط
كمتابعة محتملة مستقبلية.**

---

## 6) Regression — كل ملفات الاختبار المرتبطة بـ`invitations`

### 6.1 اختبارات `invitations` المباشرة

```
pytest tests/test_invitations_savepoint_leak.py tests/test_invitations_response_schema_fields_wiring.py -q
```
**النتيجة:** `5 passed` — صفر فشل.

### 6.2 باقي الملفات اللي بتشير لـ`invitations` (فحص شامل عبر grep)

```
pytest tests/test_ai_governance_begin_nested.py tests/test_ai_agents_execute_action.py \
       tests/test_identity_router_protection.py tests/test_user_repository_get_by_id_audit.py \
       tests/test_saas_active_subscription.py -q
```
**النتيجة بعد الإصلاح:** `16 failed, 23 passed`.

**التأكد الصارم إن الـ16 فشل pre-existing 100% ومش ناتجين عن هذا
الإصلاح:** اتعمل `git stash push -- invitations/service.py` (إرجاع
الملف بالكامل لحالة `HEAD`، شامل التعديل غير المرتبط `_check_saas_limits`)،
واتشغَّلت نفس الـ5 ملفات **بالظبط** قبل أي إصلاح:

**النتيجة قبل الإصلاح (baseline):** `16 failed, 23 passed` — **نفس
القائمة بالحرف الواحد** (نفس الـ16 اسم اختبار، بلا زيادة ولا نقصان):
- `test_ai_governance_begin_nested.py::test_buy_fractional_ownership_full_flow_succeeds_with_real_ai_governance`
- 11× `test_user_repository_get_by_id_audit.py::*` (شامل
  `test_invitations_get_user_correct_and_wrong_tenant`) — كلها مرتبطة
  بـ`backlog-affiliate-commission-registration-systemwide-broken`
  المفتوح مسبقًا (11 دومين شامل `invitations`، غير مرتبط بـ
  `create_invitation`/`_assign_ai_agent` إطلاقًا)
- 4× `test_saas_active_subscription.py::*` (realestate/insurance) —
  backlog مفتوح مسبقًا، غير مرتبط بـ`invitations`

بعد التأكيد، اتعمل `git stash pop` فورًا لاسترجاع الإصلاح — اتأكَّد
بـ`git diff` إن الأربعة أسطر المطلوبة رجعت بالظبط زي ما اتعملت، وإن
التعديل غير المرتبط (`_check_saas_limits`) رجع زي ما كان بالظبط بلا
أي فقدان.

**الخلاصة:** صفر regression جديد. الـ16 فشل موجودين بالحرف الواحد
قبل وبعد الإصلاح — معزولين تمامًا عن `create_invitation`/
`_assign_ai_agent`.

---

## 7) ملخص الالتزام بالنطاق

| القيد | الحالة |
|---|---|
| الأربعة أعطال المذكورة فقط (`service.py:172-174`, `115`) | ✅ 4 أسطر فقط اتغيَّرت، لا أكتر |
| مفيش أي تعديل تاني (schemas/router/models/إلخ) | ✅ صفر لمس لأي ملف تاني |
| اختبار حي: كل الحقول الاختيارية `None` → لازم ينجح | ✅ نجح فعليًا، `id=71` |
| اختبار حي إضافي: قيم حقيقية → المسار العادي سليم | ✅ نجح فعليًا، `id=72` |
| Regression لاختبارات `invitations` الموجودة | ✅ `5 passed` مباشرة + `16 failed, 23 passed` في الملفات الأوسع، مؤكَّد بـbaseline إنهم pre-existing 100% |
| صفر تلوث DB من الاختبارات الحية | ✅ `id=71`/`72` اتحذفوا فورًا، اتأكَّد بـSELECT |

**الحالة النهائية:** ✅ الأربعة أعطال اتصلحوا بنجاح، بأقل تغيير ممكن
(4 أسطر)، مع تحقق حي كامل ومقارنة baseline صارمة تثبت صفر أثر جانبي.
البند `backlog-invitations-create-invitation-broken` جاهز للإغلاق في
`PROGRESS_LOG.md` (لم يُغلَق في هذا التقرير — بانتظار توجيه المستخدم).
