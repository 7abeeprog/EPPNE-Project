# جلسة: ai-governance-agents-signature-fix (المرحلة 1.3)

**تاريخ:** 2026-08-18
**النطاق المصرَّح به:** `AIGovernanceService.check_and_consume()` (#15) و`AIAgentsService.execute_agent_action()` (#16) فقط — ممنوع لمس أي method تانية.
**الحالة:** تشخيص مكتمل + قرارات §معتمدة (راجع القسم 9) — الجزء أ/المجموعة الآمنة (6 مواضع) معروضة للمراجعة في القسم 10، صفر Edit فعلي حتى الآن.

---

## 1) التعريف الفعلي الكامل للدالتين

### `check_and_consume` — `eppne-backend/app/domains/ai_governance/service.py:140-199`

```python
async def check_and_consume(
    self, agent_id: int, user_id: int, action_type: str, tokens: int, cost: Decimal,
    idempotency_key: Optional[str] = None, request_tokens: int = 0, completion_tokens: int = 0
) -> bool:
```

- الكلاس `AIGovernanceService.__init__(self, db, tenant_id)` — `self.tenant_id` مخزَّن وقت الإنشاء.
- **الجسم يستخدم `self.tenant_id` في كل موضع فعلي** (`get_active_quotas`, `create_or_update_quota`, `create_usage_log`) — **لا يوجد أي معامل `tenant_id` في التوقيع أصلًا**.
- **فحص حصة حقيقي مؤثِّر:** يلف على `active_quotas` (مفلترة بـ`self.tenant_id`)، يحسب `usage_to_add` حسب `limit_type` (REQUEST_COUNT/TOKEN_COUNT/COST_MRUSDT)، ولو `current_usage + usage_to_add > limit_value` → **`return False`** (رفض حقيقي، مش مجرد تسجيل).
- Idempotency حقيقي: لو `idempotency_key` موجود ومُسجَّل مسبقًا → `return True` فورًا بدون استهلاك.

### `execute_agent_action` — `eppne-backend/app/domains/ai_agents/service.py:147-264`

```python
async def execute_agent_action(
    self, agent_id: int, action_type: str, payload: Dict[str, Any],
    executor_user_id: int, idempotency_key: str
) -> Dict[str, Any]:
```

- الكلاس `AIAgentsService.__init__(self, db, tenant_id)` — نفس النمط، `self.tenant_id` مخزَّن.
- **الجسم يستخدم `self.tenant_id` حصريًا** في `get_agent`, `create_task_log`, `create_approval_request`, `_validate_idempotency`/`_store_idempotency` (مفتاح الكاش `idempotency:{self.tenant_id}:{idempotency_key}`) — **لا يوجد معامل `tenant_id` في التوقيع أصلًا**.
- تنفيذ فعلي حقيقي: يجلب الوكيل، يتحقق من حالته (`ACTIVE`)، ينفّذ `ai_engine.generate(...)` فعليًا، يسجّل `task_log`، ولو `agent.requires_human_approval` يُنشئ طلب موافقة بدل التنفيذ المباشر.
- `idempotency_key: str` **إجباري بلا default** — يُستخدم في cache key حقيقي لمنع التكرار.

---

## 2) القرار المحوري — هل نوسّع التوقيع (زي audit_log) أم نشيل الزيادة من الاستدعاءات؟

| البند | `audit_log` (#14، القرار المتخذ) | `check_and_consume`/`execute_agent_action` (هذه الجلسة) |
|---|---|---|
| طبيعة الدالة | دالة حرة (function)، لا يوجد "self" يحمل tenant_id | **method على كلاس يُبنى دائمًا بـ`tenant_id` في الـconstructor** |
| هل tenant_id مستخدَم فعليًا داخل الجسم؟ | لم يكن، فاحتجنا نضيفه للتوقيع عشان يُسجَّل في الـlog | **نعم — عبر `self.tenant_id`، في كل استعلام/تحديث فعلي (فلترة حصة، فلترة وكيل، مفتاح idempotency)** |
| مصدر tenant_id البديل | لا يوجد — لازم يُمرَّر صراحة كل مرة | **موجود بالفعل: `self.tenant_id`، مُهيَّأ وقت إنشاء الـservice في كل موضع استدعاء (`AIGovernanceService(self.db, tenant_id)` / `AIAgentsService(self.db, tenant_id)`)** |
| القرار | **توسيع التوقيع ليقبل `tenant_id`/`resource_id`** (نُفِّذ، commit `84e20f8`/سابقه) | **شيل `tenant_id=` الزائدة من كل استدعاء — عكس اتجاه audit_log** |
| السبب | الدالة لا تملك سياق tenant أصلًا؛ وسّعنا التوقيع ليصير هو مصدر الحقيقة | الـmethod **تملك بالفعل** سياق tenant صحيح عبر الـconstructor؛ إضافة معامل `tenant_id` مكرر للتوقيع تفتح باب لقيمة مختلفة تُمرَّر بالغلط لاحقًا (bug جديد صامت) بينما لا فائدة حقيقية منه |

**تأكيد إضافي مهم:** فحصت كل مواضع الاستدعاء (١٣+١٩) — **في كل موضع بدون استثناء، القيمة الممرَّرة كـ`tenant_id=` هي نفس المتغيّر المستخدَم لبناء الـservice نفسه** (مثال: `governance = AIGovernanceService(self.db, tenant_id); governance.check_and_consume(tenant_id=tenant_id, ...)`). يعني إزالة الـkwarg الزائد **لا تغيّر أي سلوك فعلي** — القيمة التي كانت "ستُستخدم" لو قُبلت هي بالضبط `self.tenant_id` الموجودة أصلًا.

### ✅ القرار الموصى به: **شيل `tenant_id=` من كل الـ32 موضع استدعاء (13+19)، بدون توسيع أي توقيع.** عكس اتجاه audit_log تمامًا، لكن بمنطق متسق: وسّعنا هناك لأن الدالة لم تكن تملك السياق؛ هنا نُزيل لأن الـmethod تملكه بالفعل وبشكل أدق (self.tenant_id ثابت طوال عمر الـservice، بينما kwarg منفصل قابل للتضارب بالخطأ مستقبلًا).

---

## 3) 🔴 اكتشاف حرج جديد (شرط إيقاف #2) — إنفاذ الحصة (quota enforcement) غير فعّال فعليًا في 11 من 13 موضع، حتى بعد الإصلاح

`check_and_consume` ترجع `bool` (`True`=مسموح، `False`=تجاوز الحصة). فحصت **كيف يُستخدَم الناتج الراجع في كل الـ13 موضع:**

| # | ملف:سطر | استخدام الناتج الراجع |
|---|---|---|
| 1 | zamakana:498 | ❌ **مُتجاهَل تمامًا** — `await governance.check_and_consume(...)` بلا `=` |
| 2 | transport:74 | ✅ `return await governance.check_and_consume(...)` — يُعاد للـcaller |
| 3 | insurance:338 | ❌ مُتجاهَل |
| 4 | tourism_sports:432 | ❌ مُتجاهَل |
| 5 | tenders_auctions:202 | ❌ مُتجاهَل |
| 6 | social:304 | ❌ مُتجاهَل |
| 7 | service_marketplace:159 | ✅ `allowed = await ...check_and_consume(...)` ثم `if not allowed: raise PermissionDeniedError(...)` — **الوحيد اللي فعليًا يطبّق القرار** |
| 8 | realestate:76 | ✅ `result = await ...`; `return result` — يُعاد للـcaller |
| 9 | arbitration_syndicates:95 | ❌ مُتجاهَل |
| 10 | manufacturing:300 | ❌ مُتجاهَل |
| 11 | manufacturing:662 | ❌ مُتجاهَل |
| 12 | logistics:546 | ❌ مُتجاهَل |
| 13 | invitations:383 | ❌ مُتجاهَل |

**الأثر:** حتى بعد إصلاح الـTypeError (شيل tenant_id + إضافة action_type)، **9 من 13 موضع (zamakana, insurance, tourism_sports, tenders_auctions, social, arbitration_syndicates, manufacturing×2, logistics, invitations = فعليًا 10) بتستدعي فحص الحصة، تحصل على `False` (تجاوز)، ولا تفعل أي شيء بالنتيجة — الكود يكمل تنفيذه وكأن الفحص نجح.** فحص الحصة "يعمل" بمعنى أنه لا يرمي استثناء، لكنه **لا يمنع أي شيء فعليًا** في أغلب الدومينات. هذا **غير موثَّق في التقرير الأصلي** ويغيّر معنى "نجاح الإصلاح" جوهريًا — إصلاح الـkwarg وحده **لا يعني أن إنفاذ الحصة أصبح فعّالًا**، فقط يعني أن الاستدعاء لم يعد يفشل بـ`TypeError`.

**قرار مطلوب منك:** هل نُصلح فقط الـTypeError (نطاق الجلسة المصرَّح به: check_and_consume/execute_agent_action أنفسهم)، أم نُبلّغ فقط عن هذا الاكتشاف كبند Backlog منفصل لاحق (لأن إصلاحه الحقيقي يتطلب لمس 9+ ملفات caller خارج نطاق الدالتين المصرَّح بهما — شرط الإيقاف #5)؟ **التوصية: توثيق فقط الآن، بند Backlog جديد `ai-governance-quota-result-ignored` لاحقًا — لمسه الآن يخالف شرط الإيقاف #5 (لمس methods/استدعاءات خارج الدالتين نفسهم بمنطق أعمق من مجرد تصحيح kwargs).**

---

## 4) 🟡 اكتشاف نمط إضافي غير موثَّق (شرط إيقاف #3) — `action_type="ANALYZE_SENSOR"` مُكرَّرة حرفيًا بلا معنى في 15 من 19 موضع `execute_agent_action`

فحص القيمة الفعلية الممرَّرة لـ`action_type` في كل الـ19 موضع:

| action_type الممرَّرة | عدد المواضع | المواضع | تقييم |
|---|---|---|
| `"ANALYZE_SENSOR"` (نصّ حرفي ثابت) | **15** | zamakana:521 (تحليل سيناريو!), employment:142 (تقييم توافق وظيفي!), command:348 (تحليل استراتيجي!), arbitration_syndicates:105 (تحليل نزاع!), transport:165 (تحسين مسار), tourism_sports:271 (فحص نقل VIP), tourism_sports:414 (تحليل طبي!), tenders_auctions:210 (تقييم عطاء), tenders_auctions:329 (تحليل مزاد), social:314 (اقتراحات توافق), manufacturing:311 (تحليل دفعة إنتاج), manufacturing:673 (صيانة تنبؤية — الوحيد القريب من المعنى الحرفي), logistics:558 (توقّع مخزون), invitations:84 (تحليل عميل مستهدَف), insurance:346+439 (تحليل/مراجعة مطالبة تأمين) | 🔴 **نسخ-لصق من قالب واحد** — القيمة لا تعكس العملية الفعلية في 14 من 15 (الاستثناء الوحيد المنطقي: agritech الحقيقية تحلل بيانات حساس فعلًا) |
| `action_type=action_type` (متغيّر ديناميكي فعلي) | 1 | automation:707 | 🟢 صحيح — القيمة الحقيقية تُمرَّر من الـcaller |
| `"ANALYZE_PROJECT"` | 1 | realestate:232 | 🟢 مخصَّص وصحيح |
| `"CHAT"` | 1 | invitations:415 | 🟢 مخصَّص وصحيح |
| `"ANALYZE_SENSOR"` (سياق حقيقي: بيانات حساس IoT فعلية) | 1 | tasks/agritech.py:168 | 🟢 القيمة صحيحة فعليًا هنا (التحليل حساسات فعلي) |

**الأثر العملي الحالي:** بما إن جسم `execute_agent_action` **لا يستخدم `action_type` إلا لمقارنة واحدة** (`if action_type == "TRANSLATE": task_type = TaskType.TRANSLATION`، وإلا `TaskType.ARABIC_CHAT` افتراضيًا)، القيمة الخاطئة **لا تُسبِّب كراش** — لكنها **تُخزَّن بشكل مضلِّل في `task_log`/`approval_request`** (بيانات تدقيق/تحليلات خاطئة دائمًا تقول "ANALYZE_SENSOR" لعمليات مطالبة تأمين، تحليل نزاع، تقييم توظيف... إلخ).

**هذا اكتشاف جديد كليًا لم يظهر في تقرير `technical-pattern-sweep-session-log.md`** (الذي غطّى فقط `tenant_id` الزائدة و`action_type`/`idempotency_key` المفقودة تمامًا — وليس "موجودة لكن قيمتها خاطئة"). بموجب شرط الإيقاف #3، أتوقف هنا لسؤالك: **هل يدخل هذا في نطاق الإصلاح الحالي (تصحيح القيم لتعكس العملية الفعلية) أم يُوثَّق كبند Backlog منفصل لاحق ("action-type-placeholder-copy-paste")؟** التوصية: توثيق فقط الآن — تصحيح كل قيمة يتطلب فهم السياق التجاري لكل موضع على حدة (14 موضع)، حجم عمل مستقل عن "شيل tenant_id الزائدة".

---

## 5) الجدول المُحدَّث النهائي — #15 `check_and_consume` (13 موضع، مؤكَّد بالقراءة المباشرة الكاملة لكل موضع)

| # | ملف:سطر | `tenant_id=` زيادة | `action_type` | try/except يحمي الاستدعاء؟ | الناتج الراجع (bool) يُستخدَم؟ |
|---|---|---|---|---|---|
| 1 | zamakana/service.py:498 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** | ❌ لا (خارج أي try، سطر 507 يبدأ try بعده) | ❌ لا |
| 2 | transport/service.py:74 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** | ✅ نعم (`except Exception`:81) | ✅ نعم (`return`) |
| 3 | insurance/service.py:338 | 🔴 إزالة | ✅ موجودة (`CLAIM_ANALYSIS`) | ✅ نعم (try كامل 335-359، مش جزئي كما ذُكر سابقًا — **تصحيح**) | ❌ لا |
| 4 | tourism_sports/service.py:432 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** | ❌ لا (بعد try/except سابق ينتهي سطر 428، هذا الاستدعاء خارجه) | ❌ لا |
| 5 | tenders_auctions/service.py:202 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** | ✅ نعم (try 199 / except 222 — **تصحيح عن "غير مؤكد"**) | ❌ لا |
| 6 | social/service.py:304 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** | ❌ لا (قبل try في 313) | ❌ لا |
| 7 | service_marketplace/service.py:159 | 🔴 إزالة | ✅ موجودة (`SERVICE_PURCHASE`) | ❌ لا | ✅ نعم (`if not allowed: raise`) |
| 8 | realestate/service.py:76 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** | ✅ نعم (`except Exception`:84) | ✅ نعم (`return result`) |
| 9 | arbitration_syndicates/service.py:95 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** | ❌ لا (قبل try في 104) | ❌ لا |
| 10 | manufacturing/service.py:300 | 🔴 إزالة | ✅ موجودة (`MANUFACTURING_ANALYSIS`) | ❌ لا (قبل try في 310) | ❌ لا |
| 11 | manufacturing/service.py:662 | 🔴 إزالة | ✅ موجودة (`MAINTENANCE_ANALYSIS`) | ❌ لا (قبل try في 672) | ❌ لا |
| 12 | logistics/service.py:546 | 🔴 إزالة | ✅ موجودة (`LOGISTICS_FORECAST`) | ❌ لا (قبل try في 557) | ❌ لا |
| 13 | invitations/service.py:383 | 🔴 إزالة | ✅ موجودة (`CRM_CHAT`) | ❌ لا | ❌ لا |

**آمنة تمامًا بلا تعديل:** `command/service.py:335` (بلا tenant_id، مع action_type)، `ai_governance/router.py:191` (الاستدعاء الصحيح).

**ملخص:** 13/13 تحتاج إزالة `tenant_id=`. **7/13 تحتاج أيضًا إضافة `action_type=`** (zamakana, transport, tourism_sports, tenders_auctions, social, realestate, arbitration_syndicates) — **مطابق تمامًا لما ورد في التقرير الأصلي، مؤكَّد الآن بالقراءة المباشرة لكل سطر وليس افتراضًا.**

---

## 6) الجدول المُحدَّث النهائي — #16 `execute_agent_action` (19 موضع، مؤكَّد بالقراءة المباشرة الكاملة لكل موضع)

| # | ملف:سطر | `tenant_id=` زيادة | `idempotency_key` | try/except يحمي؟ |
|---|---|---|---|---|
| 1 | tasks/agritech.py:168 | 🔴 إزالة | ✅ موجودة (**تصحيح عن "يحتاج تأكيد"**) | ✅ نعم (try:167) |
| 2 | zamakana/service.py:521 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** | ✅ نعم (try:507/except:536) |
| 3 | transport/service.py:165 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** | ✅ نعم (try:163/except:183) |
| 4 | tourism_sports/service.py:271 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** | ✅ نعم (try:270/except:278) |
| 5 | tourism_sports/service.py:414 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** | ✅ نعم (try:413/except:427) |
| 6 | tenders_auctions/service.py:210 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** | ✅ نعم (try:199/except:222 — **تصحيح عن "لا مباشرة"**) |
| 7 | tenders_auctions/service.py:329 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** | ✅ نعم (try:328/except:341) |
| 8 | social/service.py:314 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** | ✅ نعم (try:313) |
| 9 | realestate/service.py:232 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** | ❌ لا (جوّه `begin_nested()` فقط، لا try/except) |
| 10 | automation/service.py:707 | 🔴 إزالة | ✅ موجودة | ✅ نعم (try:706 / 3 except متخصصة) |
| 11 | arbitration_syndicates/service.py:105 | 🔴 إزالة | ✅ موجودة (**تصحيح عن "يحتاج تأكيد"**) | ✅ نعم (try:104/except:119) |
| 12 | manufacturing/service.py:311 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** | ✅ نعم (try:310) |
| 13 | manufacturing/service.py:673 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** | ✅ نعم (try:672/except:684) |
| 14 | logistics/service.py:558 | 🔴 إزالة | ✅ موجودة (**تصحيح عن "يحتاج تأكيد"**) | ✅ نعم (try:557) |
| 15 | invitations/service.py:84 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** | ✅ نعم (try:83) |
| 16 | invitations/service.py:415 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** | ❌ لا (جوّه `begin_nested()` فقط، لا try/except) |
| 17 | insurance/service.py:346 | 🔴 إزالة | ✅ موجودة (**تصحيح جوهري — التقرير الأصلي قال "مفقودة" بالغلط**) | ✅ نعم (try:335/except:359) |
| 18 | insurance/service.py:439 | 🔴 إزالة | 🔴 **مفقودة — لازم تُضاف** (**تصحيح — التقرير الأصلي قال "يحتاج تأكيد"**) | ✅ نعم (try:438) |
| 19 | employment/service.py:142 | 🔴 إزالة | ✅ موجودة | ✅ نعم (try:131/except:153) |

**آمنة تمامًا بلا تعديل:** `command/service.py:348` (بلا tenant_id، مع idempotency_key)، `ai_agents/router.py:95`.

**ملخص:** 19/19 تحتاج إزالة `tenant_id=`. **13/19 تحتاج إضافة `idempotency_key=`** (zamakana, transport, tourism_sports×2, tenders_auctions×2, social, realestate, manufacturing×2, invitations×2, insurance:439) — **تصحيح صافي +1 عن تقدير التقرير الأصلي (كان يفترض insurance:346 مفقودة و439 غير مؤكَّدة؛ الحقيقة العكس: 346 موجودة، 439 مفقودة)**.

**تصحيحات جوهرية عن التقرير الأصلي (5 مواضع كانت "يحتاج تأكيد" أو خاطئة، الآن مؤكَّدة 100%):**
- agritech tasks:168 → idempotency_key **موجودة** (ليست مفقودة)
- arbitration_syndicates:105 → idempotency_key **موجودة**
- logistics:558 → idempotency_key **موجودة**
- insurance:346 → idempotency_key **موجودة** (التقرير الأصلي قال "مفقودة" — خطأ)
- insurance:439 → idempotency_key **مفقودة فعليًا** (التقرير الأصلي قال "يحتاج تأكيد" لنفس الموضع بالخلط مع 346)
- tenders_auctions:210 و insurance:346/338 → **محمية فعليًا بـtry/except** (التقرير الأصلي صنّفها "لا مباشرة"/"يحتاج تأكيد"/"جزئي")

---

## 7) فحص: هل كود حالي يعتمد على فشل الدالتين حاليًا بشكل مقصود؟

- **صفر ملفات اختبار (`test*.py`) تشير لـ`check_and_consume` أو `execute_agent_action`** — لا يوجد pytest يعتمد على سلوك الفشل الحالي (`TypeError`) أو نجاح.
- **الاعتماد الوحيد المكتشَف هو التصميمي/الضمني:** كل المواضع المحمية بـ`try/except` (10 من 13 لـ#15 غير محمية فعليًا فقط 4 محمية؛ 16 من 19 لـ#16 محمية) **تتعامل حاليًا مع الفشل الدائم كـ"مسار طبيعي متوقَّع"** — تسجل تحذير وتكمل بمسار احتياطي (fallback). بعد الإصلاح، هذه المسارات **ستبدأ فعليًا في تنفيذ استدعاء AI حقيقي لأول مرة** (كانت تفشل دائمًا قبل كده) — هذا **تغيير سلوك وظيفي حقيقي، مش مجرد إسكات خطأ**، ويستاهل اختبار حي حذر بعد كل دفعة إصلاح، مش بس "صفر استثناء".
- المواضع غير المحمية (zamakana:498 check_and_consume، social:304، arbitration_syndicates:95، manufacturing×2، logistics:546، invitations:383 لـ#15؛ realestate:232، invitations:415 لـ#16) — **الـendpoint بالكامل يفشل بـ500 حاليًا عند الوصول لهذا السطر**. بعد الإصلاح، **الطلب سيكمل لأول مرة وينفّذ باقي منطق العملية** (مثال: `realestate.execute_agent_action:232` هو استدعاء **قبل** نقل الأموال الفعلي في نفس العملية — حاليًا العملية بالكامل تفشل هناك دائمًا؛ بعد الإصلاح ستكمل لمرحلة `finance.transfer` الفعلية). **هذا يستأهل انتباه خاص وقت التحقق الحي — مش فقط "التأكد من عدم وجود استثناء" بل التأكد من أن باقي تدفق العملية (نقل الأموال، إنشاء الفاتورة) يتصرف صح الآن بعد ما بقى قابلًا للوصول.**

---

## 8) هل نقسم الجلسة لجزئين؟

**التوصية: نعم، جزئين متتاليين — بموافقة منفصلة على كل جزء:**

1. **الجزء أ — `check_and_consume` (13 موضع):** إزالة `tenant_id=` من كل الـ13 + إضافة `action_type=` للـ7 الناقصة. حجم أصغر، الدالة أبسط (فحص حصة فقط).
2. **الجزء ب — `execute_agent_action` (19 موضع):** إزالة `tenant_id=` من كل الـ19 + إضافة `idempotency_key=` للـ13 الناقصة. حجم أكبر، ولكل موضع محتاج idempotency_key لازم نبني قيمة معقولة من سياق العملية (زي نمط `f"AI-{idempotency_key}"` في arbitration_syndicates، أو `f"agritech_high_{reading.id}_{uuid.uuid4().hex[:8]}"` في agritech) — عمل أكبر يستاهل مراجعة منفصلة لكل قيمة مقترحة.

كل ديف يُعرض بمجموعات صغيرة (2-3 مواضع لكل مجموعة، مفصولة حسب نوع الإصلاح: "شيل tenant_id فقط" مقابل "شيل tenant_id + أضف action_type/idempotency_key") — مش ديف ضخم واحد.

---

## القرارات المطلوبة منك قبل أي كود

1. ✅/❌ الاتجاه المحوري: إزالة `tenant_id=` من كل الاستدعاءات (بدل توسيع التوقيع) — موافق؟
2. كيف نتعامل مع اكتشاف §3 (إنفاذ الحصة غير فعّال في 10/13 موضع)؟ توثيق فقط الآن كبند Backlog منفصل، أم إصلاح فوري (يتطلب تجاوز شرط الإيقاف #5)؟
3. كيف نتعامل مع اكتشاف §4 (`action_type="ANALYZE_SENSOR"` خاطئة في 14/19 موضع)؟ توثيق فقط الآن، أم تصحيح القيم كجزء من هذه الجلسة؟
4. موافقة على التقسيم لجزئين (أ: check_and_consume، ب: execute_agent_action) بترتيب متتالٍ؟
5. لو موافق على الجزء أ: هل نبدأ بالمواضع "الآمنة" (شيل tenant_id فقط، 6 مواضع عندها action_type بالفعل) كمجموعة أولى صغيرة، قبل المواضع اللي محتاجة action_type جديد؟

---

## 9) قرارات معتمدة (بعد مراجعتك)

1. ✅ الاتجاه المحوري: إزالة `tenant_id=` من كل الـ32 موضع (بدل توسيع التوقيع).
2. ✅ اكتشاف §3 (quota enforcement غير فعّال): **توثيق فقط** كبند Backlog منفصل — `ai-governance-quota-result-ignored`، **أولوية مرتفعة** (قريبة من خطورة فقدان عمولة affiliate الصامت #10). لا يُلمس الآن.
3. ✅ اكتشاف §4 (`action_type="ANALYZE_SENSOR"` placeholder): **توثيق فقط** كبند Backlog منفصل — `action-type-placeholder-copy-paste`. **استثناء صريح:** المواضع السبعة في check_and_consume الناقصة `action_type` أصلًا (الجزء أ) تُضاف لها قيمة معبِّرة فعليًا عن العملية (نفس نمط `CRM_CHAT`/`MANUFACTURING_ANALYSIS` الصحيح)، **مش** نص عام مكرر — حتى لا يضيف الإصلاح لنفس المشكلة الموثَّقة.
4. ✅ تقسيم الجلسة: جزء أ (`check_and_consume`، 13 موضع) أولًا، ثم جزء ب (`execute_agent_action`، 19 موضع) بموافقة منفصلة.
5. ✅ الجزء أ يبدأ بالمجموعة الآمنة (6 مواضع: إزالة `tenant_id=` فقط، `action_type` موجودة وصحيحة بالفعل).

---

## 10) الجزء أ / المجموعة الآمنة — الديف الكامل (6 مواضع، للمراجعة فقط — صفر Edit فعلي بعد)

كل الستة: **حذف سطر `tenant_id=...,` فقط**. لا تغيير على أي معامل آخر. `action_type` في الستة كلها موجودة ومطابقة بالفعل لسياق العملية (لا تدخل في نطاق بند `action-type-placeholder-copy-paste` الموثَّق في §4 — لأنها ليست `"ANALYZE_SENSOR"` عامة، بل قيم مخصَّصة صحيحة: `CLAIM_ANALYSIS`, `SERVICE_PURCHASE`, `MANUFACTURING_ANALYSIS`, `MAINTENANCE_ANALYSIS`, `LOGISTICS_FORECAST`, `CRM_CHAT`).

### 1/6 — `eppne-backend/app/domains/insurance/service.py:338-345`

```diff
             await governance.check_and_consume(
-                tenant_id=tenant_id,
                 agent_id=10,
                 user_id=user_id,
                 action_type="CLAIM_ANALYSIS",
                 tokens=300,
                 cost=Decimal("0.03")
             )
```

### 2/6 — `eppne-backend/app/domains/service_marketplace/service.py:159-167`

```diff
             allowed = await governance_service.check_and_consume(
-                tenant_id=buyer_tenant_id,
                 agent_id=0,
                 user_id=buyer_user_id,
                 action_type="SERVICE_PURCHASE",
                 tokens=0,
                 cost=Decimal("0.01"),
                 idempotency_key=idempotency_key
             )
```

### 3/6 — `eppne-backend/app/domains/manufacturing/service.py:300-307` (الموضع الأول — `MANUFACTURING_ANALYSIS`)

```diff
         await governance.check_and_consume(
-            tenant_id=tenant_id,
             agent_id=4,
             user_id=user_id,
             action_type="MANUFACTURING_ANALYSIS",
             tokens=150,
             cost=Decimal("0.015")
         )
```

### 4/6 — `eppne-backend/app/domains/manufacturing/service.py:662-669` (الموضع الثاني — `MAINTENANCE_ANALYSIS`)

```diff
         await governance.check_and_consume(
-            tenant_id=tenant_id,
             agent_id=4,
             user_id=user_id,
             action_type="MAINTENANCE_ANALYSIS",
             tokens=200,
             cost=Decimal("0.02")
         )
```

### 5/6 — `eppne-backend/app/domains/logistics/service.py:546-553`

```diff
         await governance.check_and_consume(
-            tenant_id=tenant_id,  # type: ignore
             agent_id=13,
             user_id=user_id,
             action_type="LOGISTICS_FORECAST",
             tokens=200,
             cost=Decimal("0.02")
         )
```
**ملاحظة:** `# type: ignore` كانت مربوطة تحديدًا بتضارب `tenant_id` مع التوقيع الحقيقي — تُحذف معه لأن سببها زال. لا `# type: ignore` أخرى على نفس الاستدعاء.

### 6/6 — `eppne-backend/app/domains/invitations/service.py:383-390`

```diff
         await governance.check_and_consume(
-            tenant_id=tenant_id,  # type: ignore
             agent_id=invitation.assigned_ai_agent_id or 1,  # type: ignore
             user_id=user_id or 0,
             action_type="CRM_CHAT",
             tokens=100,
             cost=Decimal("0.01")
         )
```
**ملاحظة:** فيه `# type: ignore` تانية على سطر `agent_id=invitation.assigned_ai_agent_id or 1` — دي **غير مرتبطة** بـtenant_id (سببها `Optional[int] or 1`)، **تفضل زي ما هي، ما بتتحذفش**.

---

**بعد موافقتك على هذه الستة، هتُطبَّق بـEdit فعلي واحد لكل ملف، ثم `git diff`/`git status` خام يُعرض فورًا. بعدها ننتقل للـ7 مواضع المتبقية في الجزء أ (محتاجة إضافة `action_type` معبِّر + إزالة `tenant_id`).**

---

## 11) الجزء أ / المجموعة الآمنة — نتيجة التطبيق الفعلي (`git diff` خام)

**التطبيق تم على الستة مواضع.** `git status --short`:
```
 M eppne-backend/app/domains/insurance/service.py
 M eppne-backend/app/domains/invitations/service.py
 M eppne-backend/app/domains/logistics/service.py
 M eppne-backend/app/domains/manufacturing/service.py
 M eppne-backend/app/domains/service_marketplace/service.py
```

**5 من 6 ملفات (insurance, invitations, logistics, manufacturing×2) — ديف نظيف 100%، مطابق حرفيًا لما اتفقنا عليه في القسم 10.** سطر واحد محذوف (`tenant_id=`) لكل موضع، صفر تغيير إضافي.

**⚠️ استثناء موثَّق — `service_marketplace/service.py`:** الـ`git diff` لهذا الملف يحتوي تغييرات إضافية **كثيرة غير متعلقة بهذه الجلسة إطلاقًا** (إعادة هيكلة الـconstructor بالكامل: إزالة `self.finance`/`self.entity_service`/`self.saas_service`/`self.affiliate_service`/`self.invoice_service`/`self.governance_service` من `__init__`، واستبدالها بإنشاء instances محلية بـ`tenant_id` صحيح داخل كل method على حدة). **هذه التغييرات كانت موجودة كملف `M` (uncommitted) في `git status` من قبل بداية هذه الجلسة بالكامل** — على الأرجح بقايا جلسة سابقة (`#10 register_commission` أو `#9 SaaS get_active_subscription`، طبقًا لأنماط commits `9f37201`/`0071744` الأخيرة). **تعديلي الوحيد الفعلي والمقصود في هذا الملف: حذف سطر `tenant_id=buyer_tenant_id,` من استدعاء `check_and_consume` (كان سطر 159/160 الأصلي، الآن ظاهر في الديف كـ`- allowed = await self.governance_service.check_and_consume(\n-     tenant_id=buyer_tenant_id,` → `+ allowed = await governance_service.check_and_consume(`).** باقي الديف موروث ومُدرَج هنا بالكامل للشفافية فقط — **لم يُلمس أو يُراجَع من طرفي، ويحتاج قرارك: هل هو من عمل سابق مقصود ومُراجَع بالفعل، أم عالق ويحتاج تعامل منفصل خارج نطاق جلستنا؟**

---

## 12) الجزء أ / المجموعة الثانية — القيم المقترحة لـ`action_type` (7 مواضع، للمراجعة قبل أي Edit)

فُحصت الدالة المحيطة بكل موضع (السياق التجاري الفعلي، مش تخمين) قبل الاقتراح:

| # | الموضع | الدالة المحيطة (السياق الفعلي) | القيمة المقترحة | التبرير |
|---|---|---|---|---|
| 1 | `zamakana/service.py:498` | `generate_ai_analysis()` — تحليل سيناريو مستقبلي (اقتصادي/بيئي/اجتماعي)، `target_year`, `assumptions` | `"SCENARIO_ANALYSIS"` | يطابق طبيعة العملية فعليًا — الناتج نفسه يحتوي `economic_impact`/`environmental_impact`/`social_impact` |
| 2 | `transport/service.py:74` | `_check_ai_governance()` — **helper بمعامل `action: str` موجود أصلًا في التوقيع وغير مُستخدَم داخل الجسم**؛ المستدعي الوحيد (`service.py:324`) يمرر `"BOOK_TRIP"` | **`action_type=action`** (تمرير المعامل الموجود بدل نص جديد) | القيمة الحقيقية موجودة بالفعل في التوقيع؛ نفس نمط `automation/service.py:710` الصحيح (`action_type=action_type` ديناميكي) |
| 3 | `tourism_sports/service.py:432` | داخل دالة طلب/عرض انتقال لاعب (transfer bid) — يأتي بعد تحليل طبي بنفس `agent_id=6` (استدعاء `execute_agent_action` منفصل في نفس الدالة، سطر 414) | `"PLAYER_TRANSFER_ANALYSIS"` | يعكس أن هذا الفحص يغطي تكلفة تحليل عرض الانتقال ككل، متمايز عن الفحص الطبي المنفصل |
| 4 | `tenders_auctions/service.py:202` | دالة تقييم عطاء (`bid_id`, `technical_envelope`, `score`, `evaluator_id`) | `"BID_EVALUATION"` | يطابق العملية حرفيًا |
| 5 | `social/service.py:304` | `get_match_suggestions()` | `"MATCH_SUGGESTIONS"` | يطابق اسم الدالة والعملية |
| 6 | `realestate/service.py:76` | `_check_ai_governance()` — **نفس نمط transport بالضبط**: معامل `action: str` موجود وغير مُستخدَم؛ المستدعي الوحيد (`service.py:234`) يمرر `"FRACTIONAL_PURCHASE"` | **`action_type=action`** (تمرير المعامل الموجود) | نفس منطق transport — أفضل من نص جديد ثابت |
| 7 | `arbitration_syndicates/service.py:95` | `create_dispute()` — تحليل نزاع بواسطة "حكم AI" (`judging_mode`, `ai_judge_id` في نفس الدالة) | `"AI_JUDGE_ANALYSIS"` | يطابق التسمية المستخدَمة فعليًا في نفس الدالة |

**ملاحظة على #2 و#6:** `transport._check_ai_governance` و`realestate._check_ai_governance` لهما **نفس التوقيع بالضبط** (`action: str` كمعامل رابع غير مُستخدَم) **ولكل منهما مستدعٍ واحد فقط في كل المشروع**. الحل المقترح (`action_type=action`) **أدق من نص ثابت جديد** ولا يضيف نمط جديد لبند `action-type-placeholder-copy-paste` الموثَّق في §4 — بل يزيله من هذين الموضعين تحديدًا.

**بانتظار قرارك على القيم السبعة قبل عرض أي ديف فعلي عليها.**

---

## 13) الجزء أ / المجموعة الثانية — الديف الكامل (7 مواضع، القيم معتمدة، للمراجعة قبل أي Edit فعلي)

القيم السبعة اعتُمدت كاملة كما اقتُرحت (راجع القسم 12)، بما فيها حل `action_type=action` لـtransport وrealestate.

### 1/7 — `eppne-backend/app/domains/zamakana/service.py:498-504`

```diff
         await governance.check_and_consume(
-            tenant_id=tenant_id,
             agent_id=ai_agent_id,
             user_id=user_id,
+            action_type="SCENARIO_ANALYSIS",
             tokens=500,
             cost=Decimal("0.05")
         )
```

### 2/7 — `eppne-backend/app/domains/transport/service.py:73-80`

```diff
             governance = AIGovernanceService(self.db, tenant_id)
             return await governance.check_and_consume(
-                tenant_id=tenant_id,
                 agent_id=3,
                 user_id=user_id,
+                action_type=action,
                 tokens=50,
                 cost=cost
             )
```
(`action` هو المعامل الرابع الموجود أصلًا في توقيع `_check_ai_governance(self, tenant_id, user_id, action: str, cost)` — المستدعي الوحيد يمرر `"BOOK_TRIP"`.)

### 3/7 — `eppne-backend/app/domains/tourism_sports/service.py:432-438`

```diff
         await governance.check_and_consume(
-            tenant_id=tenant_id,
             agent_id=6,
             user_id=user_id,
+            action_type="PLAYER_TRANSFER_ANALYSIS",
             tokens=200,
             cost=Decimal("0.02")
         )
```

### 4/7 — `eppne-backend/app/domains/tenders_auctions/service.py:202-208`

```diff
             await governance.check_and_consume(
-                tenant_id=tenant_id,
                 agent_id=8,
                 user_id=evaluator_id,
+                action_type="BID_EVALUATION",
                 tokens=500,
                 cost=Decimal("0.05")
             )
```

### 5/7 — `eppne-backend/app/domains/social/service.py:304-310`

```diff
         await governance.check_and_consume(
-            tenant_id=tenant_id,
             agent_id=7,
             user_id=user_id,
+            action_type="MATCH_SUGGESTIONS",
             tokens=300,
             cost=Decimal("0.03")
         )
```

### 6/7 — `eppne-backend/app/domains/realestate/service.py:75-82`

```diff
             governance = AIGovernanceService(self.db, tenant_id)
             result = await governance.check_and_consume(
-                tenant_id=tenant_id,
                 agent_id=2,
                 user_id=user_id,
+                action_type=action,
                 tokens=100,
                 cost=cost
             )
```
(`action` هو المعامل الرابع الموجود أصلًا في توقيع `_check_ai_governance(self, tenant_id, user_id, action: str, cost)` — المستدعي الوحيد يمرر `"FRACTIONAL_PURCHASE"`.)

### 7/7 — `eppne-backend/app/domains/arbitration_syndicates/service.py:94-101`

```diff
             governance = AIGovernanceService(self.db, tenant_id)
-            await governance.check_and_consume(  # type: ignore
-                tenant_id=tenant_id,
+            await governance.check_and_consume(
                 agent_id=11,
                 user_id=claimant_id,
+                action_type="AI_JUDGE_ANALYSIS",
                 tokens=500,
                 cost=Decimal("0.05")
             )
```
(`# type: ignore` كانت مربوطة بتضارب التوقيع الناتج عن `tenant_id` الزائدة و`action_type` المفقودة معًا — تُحذف لأن السبب زال بالكامل بعد الإصلاح.)

---

**بانتظار موافقتك النهائية على السبعة قبل أي Edit فعلي. عند التطبيق: كل موضع Edit منفصل، ثم `git diff`/`git status` خام فورًا — ونفس ملاحظة الشفافية الخاصة بـservice_marketplace (لو ظهر أي ملف تاني فيه ديف موروث) هتُوثَّق بنفس الأسلوب.**

---

## 14) الجزء أ — نتيجة التطبيق الفعلي للسبعة (`git diff` خام) + ملاحظة شفافية إضافية

**التطبيق تم على السبعة مواضع.** `git status --short`:
```
 M eppne-backend/app/domains/arbitration_syndicates/service.py
 M eppne-backend/app/domains/realestate/service.py
 M eppne-backend/app/domains/social/service.py
 M eppne-backend/app/domains/tenders_auctions/service.py
 M eppne-backend/app/domains/tourism_sports/service.py
 M eppne-backend/app/domains/transport/service.py
 M eppne-backend/app/domains/zamakana/service.py
```

**4 من 7 ملفات (`arbitration_syndicates`, `realestate`, `tourism_sports`, `zamakana`) — ديف نظيف 100%**، مطابق حرفيًا لما اتفقنا عليه في القسم 13.

**⚠️ 3 ملفات فيها نفس نمط الديف الموروث من جلسة سابقة غير محفوظة (`social/service.py`, `tenders_auctions/service.py`, `transport/service.py`)** — كانوا أصلًا `M` في `git status` من **قبل بداية هذه المحادثة بالكامل** (تأكَّدت من ده بمراجعة الـstatus الأولي لأول رسالة في الجلسة). **بموافقتك الصريحة: هذا الديف الموروث يُترَك زي ما هو، ما يُلمَسش ولا يُراجَع في نطاق هذه الجلسة.** تعديلي الفعلي والوحيد المقصود في كل ملف من الثلاثة:

- `social/service.py` (`get_match_suggestions`): حذف `tenant_id=tenant_id,` + إضافة `action_type="MATCH_SUGGESTIONS",`
- `tenders_auctions/service.py` (تقييم عطاء): حذف `tenant_id=tenant_id,` + إضافة `action_type="BID_EVALUATION",`
- `transport/service.py` (`_check_ai_governance`): حذف `tenant_id=tenant_id,` + إضافة `action_type=action,`

**تنويه لازم يُذكَر صراحة في رسالة الـcommit لهذه الملفات الأربعة (service_marketplace, social, tenders_auctions, transport):** "يتضمن هذا الملف تعديلات موروثة من جلسة سابقة غير محفوظة (إعادة هيكلة constructors/instantiation لخدمات أخرى) — التعديل المقصود من جلسة `ai-governance-agents-signature-fix` هو حصريًا [السطر المحدد] في استدعاء `check_and_consume`."

**✅ الجزء أ (`check_and_consume`، 13 موضع) مكتمل بالكامل الآن — 6+7.**

---

## 15) التحقق الحي — Docker `eppne_db` (منهجية بيانات throwaway + SELECT مستقل)

**البيئة:** حاوية `eppne_db` (postgres، منفذ 5435، DATABASE_URL من `.env`) — نفس الحاوية الحقيقية المستخدمة في كل الجلسات السابقة. تم التشغيل عبر `AIGovernanceService` الحقيقية (الكود المُصلَح فعليًا)، مش mock ولا stub.

**السكربت:** `verify_check_and_consume.py` (مؤقت، في scratchpad الجلسة، لم يُدمَج بالمشروع) — أنشأ 3 وكلاء AI ثروواي (`THROWAWAY-verify-*`، IDs 10/11/99 مطابقة لـ`agent_id` الفعلي في insurance/arbitration_syndicates-zamakana) + 3 صفوف `agent_quotas` ثروواي، نفّذ 3 سيناريوهات عبر الكود الحقيقي، تحقَّق بـSELECT مستقل بعد كل سيناريو، ثم نظّف كل الصفوف وأكَّد الحذف بـSELECT مستقل نهائي.

### سيناريو 1 — عيّنة من المجموعة الأولى (شكل استدعاء `insurance/service.py:338`)
```
[call] check_and_consume(agent_id=10, action_type='CLAIM_ANALYSIS', tokens=300) -> True
[SELECT مستقل] quota.current_usage=300.00 / limit_value=1000.00
               usage_logs=[('CLAIM_ANALYSIS', 300, '0.03000000')]
```
✅ الاستدعاء الحقيقي بالتوقيع المُصلَح يعمل بدون `TypeError`، فحص الحصة يحسب الاستهلاك بشكل صحيح فعليًا (0→300)، ويسجّل `action_type` الصحيح في `agent_usage_logs`.

### سيناريو 2 — عيّنة من المجموعة الثانية (شكل استدعاء `arbitration_syndicates:95` + `zamakana:498`، نفس agent_id=11 بقيمتين مختلفتين لـ`action_type`)
```
[call] check_and_consume(agent_id=11, action_type='AI_JUDGE_ANALYSIS', tokens=500) -> True
[call] check_and_consume(agent_id=11, action_type='SCENARIO_ANALYSIS', tokens=500) -> True   (حد الحصة بالضبط: 500+500=1000)
[SELECT مستقل] quota.current_usage=1000.00 / limit_value=1000.00
               usage_logs=[('AI_JUDGE_ANALYSIS', 500, '0.05000000'), ('SCENARIO_ANALYSIS', 500, '0.05000000')]
```
✅ القيمتان الجديدتان لـ`action_type` (اللي اتضافوا في هذه الجلسة) بيتسجلوا **بدقة ومنفصلين** في `agent_usage_logs` — مش placeholder ولا قيمة مفقودة. الحصة تراكمت صح عبر استدعاءين متتاليين بنفس الوكيل.

### سيناريو 3 — رفض فعلي (تجاوز حصة، وكيل ثروواي مخصَّص بحصة منخفضة)
```
2026-08-18 13:39:44 [WARNING] eppne: Agent 99 exceeded TOKEN_COUNT quota.
[call] check_and_consume(agent_id=99, tokens=150, limit=100) -> False
[SELECT مستقل] quota.current_usage=0.00 / limit_value=100.00   (لم يتغيّر — لم يُستهلَك شيء)
               usage_logs=[]   (صفر سجل — لم يُنشأ usage_log للمحاولة المرفوضة)
```
✅ **إثبات حي إن `check_and_consume` بترفض فعليًا عند تجاوز الحصة** (مش بترجع `True` دايمًا) — الرفض حقيقي: لا استهلاك يُسجَّل، لا usage_log يُنشأ، `False` ترجع للـcaller.

### التنظيف
```
[cleanup] throwaway rows deleted
[SELECT مستقل بعد التنظيف] ai_agents=0 agent_quotas=0 agent_usage_logs=0  (الكل صفر، كما هو متوقَّع)
```

---

## 16) 🔴 اكتشاف حرج جديد إضافي (شرط إيقاف #2) — `AIGovernanceRepository.create_or_update_quota` تنهار لو الوكيل عنده أكثر من نوع حصة واحد فعّال

اكتُشِف بالصدفة أثناء التحقق الحي (تكرار غير مقصود لصفوف quota أثناء تصحيح السكربت، نفس الأثر الحقيقي لسيناريو مشروع حقيقي). **الكود الفعلي:** `ai_governance/repository.py:20-26`:

```python
async def create_or_update_quota(self, tenant_id: int, agent_id: int, **kwargs) -> AgentQuota:
    result = await self.db.execute(
        select(AgentQuota).where(
            and_(AgentQuota.agent_id == agent_id, AgentQuota.tenant_id == tenant_id)
        )
    )
    quota = result.scalar_one_or_none()   # ← يفترض صف واحد فقط لكل (agent_id, tenant_id)
```

الاستعلام **لا يفلتر بـ`limit_type`** — يفترض أن كل وكيل له صف `agent_quotas` واحد فقط لكل tenant. لكن `check_and_consume` نفسها (السطر 159-182) **مصمَّمة صراحة للتعامل مع أكثر من نوع حصة لنفس الوكيل** (`REQUEST_COUNT`/`TOKEN_COUNT`/`COST_MRUSDT` معًا)، وتستدعي `create_or_update_quota` **داخل حلقة `for quota in active_quotas`** لكل نوع على حدة. **النتيجة: أي وكيل حقيقي مُهيَّأ بأكثر من نوع حصة واحد فعّال في نفس الوقت (سيناريو طبيعي ومتوقَّع تمامًا حسب تصميم `set_quota`) سيتسبب في `sqlalchemy.exc.MultipleResultsFound` عند أول استدعاء ناجح لـ`check_and_consume` (مش عند الرفض — فقط عند النجاح، لأن الحلقة تصل لـ`create_or_update_quota` فقط لو لم يتجاوز أول نوع الحد).**

**هذا خارج نطاق `check_and_consume`/`execute_agent_action` أنفسهم — الخلل في `AIGovernanceRepository.create_or_update_quota`، method مختلفة تمامًا (شرط إيقاف #5: أي حل يمس method تانية غير الدالتين المصرَّح بهما).** **لا يُلمَس الآن.** يُوثَّق كبند Backlog جديد: `ai-governance-create-or-update-quota-multiple-results` — **أولوية عالية**، لأنه يعني أن ميزة "حصص متعددة الأنواع لنفس الوكيل" (موجودة في التصميم، مستخدَمة في `set_quota`) **مكسورة فعليًا بالكامل** لأي وكيل مُهيَّأ بأكثر من نوع حصة، بغض النظر عن إصلاح #15.

---

## 17) خلاصة الجزء أ

**الحالة: مكتمل ومُتحقَّق منه حيًا بنجاح.** 13/13 موضع `check_and_consume` — `tenant_id=` الزائدة أُزيلت، `action_type=` أُضيفت للسبعة الناقصة (بقيم معبِّرة عن السياق الفعلي، اتنين منهم بتمرير معامل موجود بدل نص جديد). التحقق الحي أثبت: (أ) الاستدعاءات الحقيقية تعمل بدون استثناء، (ب) فحص الحصة يحسب الاستهلاك صح، (ج) القيم الجديدة لـ`action_type` تُسجَّل بدقة، (د) **الرفض الفعلي عند تجاوز الحصة يعمل** لأي موضع يستخدم الناتج الراجع (زي `service_marketplace`/`realestate`/`transport` — راجع القسم 3 لملخص كل المواضع التي *لا* تستخدم الناتج). اكتشاف جانبي حرج جديد (§16) وُثِّق كبند منفصل، غير مُلمَس.

**بانتظار توجيهك: الانتقال للجزء ب (`execute_agent_action`، 19 موضع)، أم إغلاق رسمي للجزء أ أولًا (ختم + تحديث `PROGRESS_LOG.md` لبند #15 بالأرقام المصحَّحة) قبل البدء في الجزء ب؟**

---

## 18) ✅ ختم إغلاق رسمي — الجزء أ (`check_and_consume`، Backlog #15) [2026-08-18]

**الحالة النهائية: مُغلَق رسميًا.**

**الحل المطبَّق:** إزالة `tenant_id=` الزائدة من كل الـ13 موضع استدعاء `AIGovernanceService.check_and_consume()` عبر 13 دومين (التوقيع الحقيقي لا يقبل `tenant_id` — الـmethod تستخدم `self.tenant_id` من الـconstructor في كل منطق فعلي). **7 من الـ13 موضع كان عندهم بج ثانٍ متزامن** (`action_type` الإجباري مفقود بالكامل) — أُضيف بقيم معبِّرة عن السياق الفعلي (5 قيم نصية جديدة + موضعان بحل `action_type=action` أدق من نص ثابت).

**الأرقام النهائية المؤكَّدة (بالقراءة المباشرة لكل موضع، صفر افتراض):**
- 13/13 موضع: `tenant_id=` أُزيلت.
- 7/13 موضع: `action_type=` أُضيفت (`zamakana`→`SCENARIO_ANALYSIS`, `tourism_sports`→`PLAYER_TRANSFER_ANALYSIS`, `tenders_auctions`→`BID_EVALUATION`, `social`→`MATCH_SUGGESTIONS`, `arbitration_syndicates`→`AI_JUDGE_ANALYSIS`, `transport`+`realestate`→`action_type=action`).
- 6/13 موضع: كانت `action_type` موجودة وصحيحة بالفعل (`insurance`, `service_marketplace`, `manufacturing`×2, `logistics`, `invitations`) — لمسة `tenant_id` فقط.
- 4/13 ملف يحتوي ضوضاء ديف موروثة من جلسة سابقة غير محفوظة (`service_marketplace`, `social`, `tenders_auctions`, `transport`) — بموافقة صريحة: لم تُلمَس، موثَّقة في رسالة الـcommit.

**تحقق حي كامل** (docker `eppne_db`، بيانات throwaway + SELECT مستقل، راجع القسم 15) أثبت: الاستدعاءات الحقيقية تعمل بدون `TypeError`، فحص الحصة يحسب صح، `action_type` الجديدة تُسجَّل بدقة، **والرفض الفعلي عند تجاوز الحصة يعمل حقيقةً**.

**اكتشافان حرجان جانبيان، موثَّقان كبنود Backlog منفصلة، غير مُلمَسين في هذه الجلسة (خارج نطاق check_and_consume نفسها):**
1. `ai-governance-quota-result-ignored` — 10/13 موضع بتتجاهل الناتج الراجع (`bool`)، إنفاذ الحصة غير فعّال فعليًا في أغلب الدومينات.
2. `ai-governance-create-or-update-quota-multiple-results` — `AIGovernanceRepository.create_or_update_quota` تنهار بـ`MultipleResultsFound` لأي وكيل بأكثر من نوع حصة واحد فعّال.

كمان وُثِّق (توثيق فقط، بلا لمس): `action-type-placeholder-copy-paste` (15/19 موضع في `execute_agent_action` — نطاق الجزء ب القادم).

**`PROGRESS_LOG.md` مُحدَّث:** بند #15 → `✅ مُغلَق رسميًا`، + 3 بنود Backlog جديدة (`ai-governance-quota-result-ignored`, `ai-governance-create-or-update-quota-multiple-results`, `action-type-placeholder-copy-paste`).

**النطاق التالي:** الجزء ب (`execute_agent_action`، Backlog #16، 19 موضع) — جلسة/خطوة منفصلة تالية، نفس المنهجية بالكامل.
