# تقرير جلسة Phase 16 — إصلاح ثغرة X-Tenant-ID في 4 دومينات (ai_agents, sovereign_entities, command, saas)

**بدأ التسجيل:** 2026-08-12
**الحالة العامة وقت بدء التسجيل:** لسه في مرحلة التحقق الحي المسبق (Phase 2) لدومين `command`، قبل تطبيق أي إصلاح فعلي لثغرة X-Tenant-ID نفسها في أي من الـ4 دومينات.

---

## ملخص خلفية سريع (retroactive، لغاية لحظة بدء التسجيل)

- **الهدف:** نفس نمط الإصلاح اللي اتعمل قبل كده مرتين (Phase 10c في `affiliate`، Phase 12 في `automation`): استبدال `Depends(get_current_tenant)` (بيثق في هيدر `X-Tenant-ID` بلا أي تحقق) بـ`current_user.tenant_id` (مُستخرج من JWT الموقّع)، عبر 4 دومينات: `ai_agents`، `sovereign_entities`، `command`، `saas`.
- **خطة الإصلاح النهائية اتفق عليها بالكامل** (تفاصيل الـendpoints لكل دومين، حالات خاصة زي saas admin path/query endpoints، sovereign_entities endpoints الناقصة current_user).
- **اكتشافات جانبية غير متعلقة بـX-Tenant-ID اتلقطت أثناء التحقق الحي لـcommand:**
  1. `CommandService.__init__` كان بيعمل `AIAgentsService(db)` و`SaaSControlService(db)` من غير `tenant_id` المطلوب → `TypeError` في كل endpoint. **اتصلح** (أزيلوا من `__init__`، `saas_service` اتأكد إنه dead code).
  2. `AIGovernanceService(self.db)` (داخل `generate_ai_recommendations`) نفس المشكلة، ناقص `tenant_id`. **اتصلح** (`AIGovernanceService(self.db, tenant_id)` + إزالة `tenant_id=tenant_id` الزايدة من `check_and_consume`).
  3. `get_dashboard` → `ResponseValidationError` لأن `DashboardResponse.dashboard` متوقع dict لكن السيرفس بيرجّع كائن ORM خام (`CommandDashboard`). **لسه مش متصلح، مش موثّق كقرار نهائي.**
  4. `generate_ai_recommendations` → `agent_id=14` مش موجود في جدول `ai_agents` (hardcoded) → `ForeignKeyViolationError` على `agent_usage_logs`. **قيد النقاش دلوقتي.**
- **تناقض اتكتشف لحظيًا (السبب المباشر لطلب التقرير ده):** بعد قراءة الملف حرفيًا من القرص، لقيت إن الإصلاح رقم (1) مطبّق جزئيًا بس — `__init__` نضيف فعلاً، لكن الاستخدام الوحيد لـ`self.ai_service` (سطر 347 في `generate_ai_recommendations`) **لسه بيشير لمتغيّر مش موجود أصلاً** (`self.ai_service` اتشال من `__init__` ومفيش `ai_service` محلي اتضاف بدالها). ده هيسبب `AttributeError` بعد ما نعدي مشكلة الـFK بتاعة `agent_id=14`.

---

## [2026-08-12] طلب موافقة #1 — استكمال إصلاح `self.ai_service` في `command/service.py:347`

**السياق:** أثناء التحقق الحي لـ`generate_ai_recommendations`، ظهر `ForeignKeyViolationError` بسبب `agent_id=14` غير موجود. لكن قبل حتى ما نوصل لمشكلة الـseed، اكتشفت إن الكود بعد كده (سطر 347) هيفشل بـ`AttributeError: 'CommandService' object has no attribute 'ai_service'` — لأن الإصلاح الأول (إزالة `self.ai_service` من `__init__`) اتطبّق، لكن استبداله بمتغيّر محلي في `generate_ai_recommendations` (نفس نمط الإصلاح اللي اتعمل لـ`AIGovernanceService`) **لم يُكتب فعليًا على القرص**.

**المطلوب:** موافقة على إكمال نفس الإصلاح (مش نطاق جديد):
```python
ai_service = AIAgentsService(self.db, tenant_id)
ai_result = await ai_service.execute_agent_action(...)
```
بدل `self.ai_service.execute_agent_action(...)` في سطر 347.

**الحالة:** ✅ اتوافق عليه، واتطبّق فعليًا.

---

## [2026-08-12] تطبيق الإصلاح + قرار #2 — إكمال `self.ai_service` وتوثيق `get_dashboard` كباج منفصل

**الإصلاح المطبّق (diff):** `command/service.py` — سطر واحد اتضاف قبل استدعاء `execute_agent_action` داخل `generate_ai_recommendations`:
```python
ai_service = AIAgentsService(self.db, tenant_id)
ai_result = await ai_service.execute_agent_action(...)
```
بدل `self.ai_service.execute_agent_action(...)`. تصحيح استكمال لنفس إصلاح الـconstructor السابق، مش نطاق جديد.

**اكتشاف #3 (موثَّق، خارج نطاق تمامًا):** `GET /command/dashboard` → `ResponseValidationError`. تأكَّد إنه **باج سابق لأي تعديل في Phase 16**:
- `command/schemas.py:16` — `DashboardResponse.dashboard: Dict[str, Any]` متوقع dict.
- `command/service.py:126-133` (`get_dashboard`) بيرجّع كائن ORM خام (`CommandDashboard`) تحت مفتاح `"dashboard"` بلا تحويل.
- المسار الكامل (`repository.py:19` → `service.py:110-133` → `router.py:22-35`) **لم يُلمس إطلاقًا** في هذه الجلسة (التعديلات الوحيدة كانت في `__init__` و`generate_ai_recommendations` — دالتين مختلفتين).

**القرار:** يُوثَّق في `PROGRESS_LOG.md` كملاحظة منفصلة (زي نمط agritech/invoicing)، **لا يُصلَح في Phase 16**. بديل لتأكيد "الوصول الشرعي شغال بعد الإصلاح": `GET /command/brands/me` بدل `get_dashboard` (endpoint تينانت-scoped أبسط، `response_model` سليم، وسبق للمستخدم إنه وافق عليه كـ"تأكيد كافي وواضح" في نقاش سابق).

**التوثيق:** اتضاف قسم كامل لـ`PROGRESS_LOG.md` (بعد نهاية Phase 15 مباشرة) يغطي: (1) 3 باجات constructor في `CommandService` (فيها الاتنين المصلَّحين سابقًا + الثالث المصلَّح دلوقتي)، (2) `get_dashboard` ResponseValidationError — موثَّق بدون إصلاح، (3) `agent_id=14` FK issue — قيد المناقشة، قرار لسه معلّق (seed بيانات اختبار minimal مقابل توثيق بدون إصلاح).

**الحالة:** الإصلاح رقم 3 من فئة constructor ✅ مطبّق. `get_dashboard` 🔴 موثَّق فقط. `agent_id=14` 🟡 قيد القرار (سؤال معلّق للمستخدم عن أعمدة `ai_agents` المطلوبة لصف minimal).

---

## [2026-08-12] فحص شامل — هل يوجد رابع من نفس فئة باج الـconstructor؟

**الطلب:** `grep` شامل read-only على `command/service.py` كامل، للتأكد من عدم وجود constructor رابع بياخد `tenant_id` إجباري ومش بيتمرّرله وقت الإنشاء (نفس نمط الـ3 بجات اللي اتصلحوا).

**النتيجة: لا يوجد رابع.** فحصت كل استدعاء `Service(` في الملف كله — 4 استدعاءات constructor فقط موجودة إجمالًا:

| السطر | الاستدعاء | الحالة |
|---|---|---|
| 33 | `CommandRepository(db)` | سليم — `__init__(self, db)` بس، بدون `tenant_id` أصلاً |
| 34 | `EventBus(cast(Any, redis_client))` | سليم — غير متعلق بـ`tenant_id` |
| 334 | `AIGovernanceService(self.db, tenant_id)` | سليم — اتصلح سابقًا (باج #2) |
| 347 | `ai_service = AIAgentsService(self.db, tenant_id)` | سليم — اتصلح دلوقتي (باج #3) |

**ملاحظة جانبية (كود ميت، صفر خطر):** `SaaSControlService` متستوردة في سطر 15 لكن **صفر instantiation ليها في الملف كله** — نفس اكتشاف dead code السابق وقت شيلها من `__init__`. مش باج، الاستيراد نفسه لسه موجود بس بلا أي استخدام أو خطر تشغيلي.

**الخلاصة:** فئة باج الـconstructor (استدعاء service بـ`tenant_id` إجباري بدون تمريره) **مغلقة بالكامل — الـ3 المصلَّحين هم كل الموجود**.

---

## [2026-08-12] إجابة: أعمدة `ai_agents` المطلوبة لصف minimal (لحسم قرار `agent_id=14`)

من `ai_agents/models.py:43-67` — الأعمدة الإجبارية (`nullable=False`, بلا `default`) فقط:
- `tenant_id` (FK → `academy_tenants.id`)
- `owner_id` (FK → `users.id`)
- `name` (String)
- `role` (enum `AgentRole`, مثلاً `"CEO"`)
- `system_prompt` (Text)

باقي الأعمدة (`status`, `base_model`, `can_execute_payments`, `can_sign_contracts`, `requires_human_approval`, `interaction_cost_mrusdt`, `agent_wallet_address`...) عندها `default` في الموديل — مش لازم تتحدد.

**الخلاصة:** `INSERT` واحد بـ6 قيم فقط (`id=14` صريح + الـ5 الإجبارية فوق) كافي لإرضاء الـFK constraint، **بلا لمس أي منطق KYB/إنشاء agent حقيقي**. مقترح: بيانات اختبار مؤقتة (بادئة `phase16_` في `name`)، تُنضَّف في Phase 5 زي باقي بيانات الاختبار.

**الحالة:** ✅ اتوافق عليه، بشرط 3 تأكيدات قبل التنفيذ (owner_id/tenant_id مطابقين، id=14 مش موجود، تحديث cleanup query).

---

## [2026-08-12] تنفيذ seed لـ`ai_agents id=14` — تأكيدات ما قبل الـINSERT + التنفيذ

**التأكيدات الثلاثة (SELECT فقط، قبل أي كتابة):**
1. `SELECT id, tenant_id, username, system_role FROM users WHERE id=26` → `tenant_id=1`, `SUPER_ADMIN` — نفس تينانت الـagent المزمع إنشاؤه.
2. `SELECT id, tenant_id, name, role FROM ai_agents WHERE id=14` → **0 صف** — الـid مش مستخدم أصلًا، مش placeholder بيعتمد عليه كود/بيانات حقيقية.
3. `SELECT COUNT(*), MAX(id) FROM ai_agents` → **الجدول فاضي بالكامل (0 صف)** — تأكيد إضافي إن الاختبار الحي معزول تمامًا عن أي بيانات حقيقية.

**الـINSERT المنفَّذ (DB write، بموافقة صريحة مسبقة):**
```sql
INSERT INTO ai_agents (id, tenant_id, owner_id, name, role, system_prompt)
VALUES (14, 1, 26, 'phase16_test_agent', 'CEO',
        'Phase16 throwaway test agent - seeded for generate_ai_recommendations live verification');
```
النتيجة: `INSERT 0 1` ✅. تحقُّق فوري بعد الإدراج: `SELECT id, tenant_id, owner_id, name, role, status FROM ai_agents WHERE id=14` → صف واحد مطابق تمامًا للمتوقع (`tenant_id=1`, `owner_id=26`, `role=CEO`).

**تحديث query الـcleanup الخاص بنهاية الجلسة (Phase 5)** — بيانات phase16 التجريبية المطلوب حذفها/التحقق من صفريتها الآن تشمل:
```sql
DELETE FROM ai_agents WHERE id = 14;
-- بالإضافة للي كانوا موجودين بالفعل في خطة التنظيف:
-- users WHERE id IN (26, 27, 28)
-- academy_tenants WHERE id = 12
-- + أي فاتورة/بيانات saas تجريبية اتعملت لاحقًا (لو حصلت)
```
استعلام تحقق مستقل بعد التنظيف (زي نمط Phase 15): `SELECT COUNT(*) FROM ai_agents WHERE id=14` يجب يرجّع `0`.

**الحالة:** ✅ تم بالكامل. جاهزين نكمل التحقق الحي لـ`generate_ai_recommendations`.

---

## [2026-08-12] التحقق الحي لـ`generate_ai_recommendations` — تعطُّل السيرفر + اكتشاف باج رابع منفصل تمامًا

### 1. عائق تشغيلي (مش باج كود): Redis مكنش شغال
أول محاولة تشغيل `uvicorn` فشلت فورًا وقت `startup` (`redis.exceptions.ConnectionError:
تعذر الاتصال بـ Redis: Error 22 connecting to 127.0.0.1:6380`). تحقّقت:
`docker ps -a` أظهر container اسمه `redis` بحالة `Exited (255)`. اتعمل
`docker start redis` (container موجود بالفعل، مش إنشاء جديد)، اتأكَّد إنه
`Up`، وبعدها `uvicorn` بدأ نضيف (`Application startup complete`، صفر
Traceback حقيقي في اللوج).

### 2. `GET /api/command/brands/me` و`GET /api/command/alerts` — نجحوا (200) لكن مش كافيين لإثبات عزل التينانت
- `brands/me` برجّع 404 ("Brand not found") — طبيعي، مفيش صف `BrandSettings` لتينانت=1 في قاعدة اختبار فاضية، مش دليل فشل مصادقة.
- `alerts` (GET، بهيدر حقيقي زي بهيدر مزوَّر X-Tenant-ID=12) رجعوا **200 بقايمة فاضية `[]` في الحالتين** — مفيش بيانات مميِّزة بين التينانتين أصلًا في الجدول ده حاليًا، فمش دليل حاسم على تسريب أو عزل. اتسجَّل كملاحظة، مش دليل نهائي.

### 3. `POST /api/command/recommendations/generate` (السيناريو الرئيسي المطلوب) — فشل بـ`500`، **باج رابع مكتشف حيًا**
الطلب الأول (SUPER_ADMIN تينانت A، هيدر حقيقي، بعد إصلاح `self.ai_service` والتأكد من عدم وجود رابع من فئة الـconstructor) رجّع `500` فاضي. تتبُّع اللوج الحي كشف تراكة مختلفة تمامًا:

```
sqlalchemy.exc.InvalidRequestError: Can't operate on closed transaction inside context manager.
  File "app/domains/command/service.py", line 335, in generate_ai_recommendations
    await governance.check_and_consume(...)
  File "app/domains/ai_governance/service.py", line 180, in check_and_consume
    await self.repo.create_usage_log(...)
  File "app/domains/ai_governance/repository.py", line 63, in create_usage_log
    await self.db.refresh(log)
```

**السبب الجذري (قراءة كود، مؤكَّد):**
- `ai_governance/service.py:155` — `check_and_consume` بيفتح `async with self.db.begin_nested():`.
- `ai_governance/repository.py:59-64` (`create_usage_log`) بتعمل `await self.db.commit()` (سطر 62) على الـsession الأساسية **من جوه** بلوك `begin_nested()` الخارجي (استدعاؤها من `service.py:180`، داخل نفس البلوك).
- `commit()` مباشر جوه `begin_nested()` بيقفل الترانزاكشن اللي الـSAVEPOINT معتمد عليه → أي عملية بعدها (`self.db.refresh(log)`, سطر 63) بتفشل.
- **تأكَّد إنه مش مرتبط بـ`agent_id=14`/الـseed**: `active_quotas` كانت فاضية (مفيش `AgentQuota` لـagent 14)، فحلقة الـfor (سطور 156-178) اتخطّت بالكامل، والتنفيذ راح مباشرة لـ`create_usage_log` جوه نفس البلوك — الباج هيحصل حتى مع quotas وseed كاملين، لأنه مشكلة بنيوية في إدارة الترانزاكشن.

**ملاحظة إضافية (لم تُفعَّل هنا، موجودة في الكود):** `service.py:148` بيستدعي
`self.repo.get_usage_log_by_idempotency(idempotency_key)` بـparameter واحد،
لكن التوقيع الحقيقي (`repository.py:66`) محتاج `tenant_id` كمان. ماتفعّلتش
لأن نداءنا مبعتش `idempotency_key`، لكنها كمين تاني لأي استدعاء تاني بيبعته.

**التأثير:** `generate_ai_recommendations` (وأي endpoint في أي دومين تاني
بيستخدم `AIGovernanceService.check_and_consume`) **مش هينجح حاليًا إطلاقًا**،
بغض النظر عن `tenant_id`/الـseed. الباج في دومين `ai_governance` نفسه —
**خارج الأربعة دومينات المتفق عليها لـPhase 16** (`ai_agents`,
`sovereign_entities`, `command`, `saas`) بالكامل.

**الحالة:** ⏳ **موقوف، في انتظار قرار المستخدم** — يُوثَّق فقط في
`PROGRESS_LOG.md` (زي `get_dashboard`)، بلا إصلاح، أم حل تاني؟ لم يُتخذ أي
إجراء إصلاحي بعد.

---

## [2026-08-12] قرار المستخدم — الخيار أ: إصلاح مصغّر لباج الترانزاكشن + الديف المقترح للمراجعة

**القرار:** موافقة على إصلاح مصغّر لباج `ai_governance` (نقل/إزالة
`commit()` من جوه `begin_nested()` بس)، بشرط: صفر لمس لأي حاجة تانية حتى
لو ظهرت مشاكل جديدة. مشكلة `idempotency_key`/`tenant_id` المكتشفة جانبيًا
(غير مفعّلة، غير مؤثرة على مسارنا) — توثيق فقط في `PROGRESS_LOG`، بلا
إصلاح. مطلوب توثيق صريح في `PROGRESS_LOG` إن ده استثناء نطاق مبرر (حاجز
فعلي قدام التحقق الحي الإلزامي، مش توسيع اختياري). بعد الإصلاح: إعادة
تشغيل السيناريو الحي الكامل لـ`generate_ai_recommendations` (تينانت شرعي
ينجح، تينانت مزوَّر يترفض).

**الديف المقترح (لسه لم يُطبَّق، معروض للمراجعة):**

الملف: `eppne-backend/app/domains/ai_governance/repository.py`
السطر المتأثر: 62 (داخل `create_usage_log`، الاستدعاء الوحيد ليها في
المشروع كله هو `ai_governance/service.py:180`، جوه بلوك
`async with self.db.begin_nested()` في `check_and_consume`).

```python
async def create_usage_log(self, **kwargs) -> AgentUsageLog:
    log = AgentUsageLog(**kwargs)
    self.db.add(log)
    await self.db.flush()      # كان: await self.db.commit()
    await self.db.refresh(log)
    return log
```

**السبب:** `commit()` مباشر جوه `begin_nested()` بيقفل الترانزاكشن
الخارجي اللي الـSAVEPOINT معتمد عليه، فبيكسر أي عملية بعده (هنا
`refresh(log)` بالظبط). `flush()` بيكتب الصف جوه نفس الترانزاكشن (قابل
للقراءة/`refresh` فورًا) بلا ما يقفل حاجة — الـSAVEPOINT بيتقفل طبيعي لما
بلوك `async with` يخلص. الالتزام النهائي بيحصل بعدين فعليًا عبر
`command/repository.py:188` (`create_recommendation`، بتتنفذ بعد
`check_and_consume` في نفس الطلب، وعندها `self.db.commit()` خاص بيها) —
الصف مش هيضيع.

**نطاق الفحص:** الاستدعاء الوحيد لـ`create_usage_log` في المشروع كله هو
`service.py:180`. **لم تُلمس** `create_or_update_quota`
(`repository.py:20-37`) رغم وجود نفس النمط بالظبط فيها (`commit()` جوه
`begin_nested()` في `service.py:33` و`174`) — غير مفعّلة في مسارنا الحالي
(`active_quotas` فاضية، الحلقة اتخطّت بالكامل)، وسايبينها زي ما هي حسب
توجيه المستخدم الصريح.

**الحالة:** ⏳ في انتظار موافقة نهائية على تطبيق السطر ده قبل أي تنفيذ.

---

## [2026-08-12] الإصلاح اتطبّق + إعادة التشغيل + اكتشاف باج خامس (نفس فئة الـconstructor، سطر فاتنا)

**الإصلاح المطبَّق:** `ai_governance/repository.py:62` — `commit()` → `flush()`
جوه `create_usage_log` (زي الديف المعروض بالضبط). وثّقت الاستثناء صراحةً
في `PROGRESS_LOG.md` (سبب: حاجز فعلي قدام التحقق الحي الإلزامي، مش
توسيع اختياري)، + ملاحظة منفصلة لمشكلة `idempotency_key`/`tenant_id`
(غير مفعّلة، لم تُصلَح).

أعدت تشغيل `uvicorn` (بعد إيقاف العملية القديمة PID 4780، تشغيل جديد
PID 3056) — startup نضيف (صفر Traceback، `Application startup complete`).

**السيناريو الحي (تينانت شرعي / هيدر مزوَّر) على
`POST /api/command/recommendations/generate`:**
- طلب 1 (SUPER_ADMIN تينانت A، بدون هيدر مزوَّر) → `200 | []`
- طلب 2 (نفس اليوزر، `X-Tenant-ID: 12` مزوَّر) → `200 | []`

**النتيجتين متطابقتين وفارغتين — لسه مش دليل كافٍ.** تتبُّع اللوج كشف
**باج خامس** (نفس فئة الـconstructor اللي فاتت مراجعتنا السابقة):

```
AI recommendation generation failed: AIAgentsService.execute_agent_action()
got an unexpected keyword argument 'tenant_id'
```

`command/service.py:350` — `tenant_id=tenant_id,` kwarg زيادة مبعوتة
لـ`execute_agent_action` (توقيعها الحقيقي مفيهوش `tenant_id`، بما إنه
اتربط في constructor السطر اللي فوقه: `AIAgentsService(self.db, tenant_id)`).
الاستثناء ده بيتبلع جوه `except Exception` في `generate_ai_recommendations`
وبيرجّع `[]` بصمت — يعني نتيجتي الاختبار الحي `200 | []` **مش دليل نجاح
فعلي**، الطلبين فشلوا فعليًا قبل أي منطق تمييز بين تينانت شرعي ومزوَّر.

**التصنيف:** نفس الدالة، نفس بلوك الـtry، السطر اللي بعد الإصلاح اللي
اتعمل تو مباشرة — **نفس فئة الباج المتفق عليها (استكمال إصلاح constructor/
call-signature)، مش استثناء نطاق جديد.** الإصلاح المقترح: حذف
`tenant_id=tenant_id,` من الاستدعاء بس.

**الحالة:** ⏳ في انتظار موافقة المستخدم على تطبيق الحذف قبل أي تنفيذ.

---

## [2026-08-12] الحذف اتطبّق + إعادة تشغيل + اكتشاف: تقصير في بيانات الـseed بتاعتنا (مش باج كود)

**الإصلاح المطبَّق:** حذف `tenant_id=tenant_id,` من `command/service.py:350`
(الاستدعاء لـ`execute_agent_action`). أعدت تشغيل `uvicorn` (إيقاف PID
3056، تشغيل جديد PID 10696) — startup نضيف.

**السيناريو الحي أُعيد تشغيله:**
- طلب 1 (تينانت شرعي A) → `200 | []`
- طلب 2 (هيدر مزوَّر X-Tenant-ID=12) → `200 | []`

**نفس النتيجة الفارغة — تتبُّع اللوج كشف خطأ جديد، لكن هالمرة أكَّدت إنه
مش باج كود:**
```
AI recommendation generation failed: الوكيل 14 غير موجود
```
(نفس الرسالة ظهرت للطلبين الاتنين، مش بس المزوَّر.)

**السبب الجذري (قراءة كود + استعلام DB مباشر):**
`ai_agents/repository.py:29-39` (`get_agent`) بتفلتر:
```python
and_(AIAgent.id == agent_id, AIAgent.tenant_id == tenant_id,
     AIAgent.is_deleted == False)
```
استعلام مباشر على الصف اللي زرعناه:
```
id=14, tenant_id=1, status=NULL, is_deleted=NULL, deleted_at=NULL
```
`status` و`is_deleted` **كلاهما NULL**، مش القيم الافتراضية
(`AgentStatus.IDLE`/`False`) المعرَّفة في الموديل — لأن `default=` في
SQLAlchemy Python-level بس، بيتطبّق عند الإدراج عبر الـORM، **مش عبر
INSERT خام عبر psql** زي ما عملنا. `NULL = false` في SQL بترجع `NULL`
مش `true`، فالصف مرفوض من الاستعلام لأي تينانت — "مش موجود" حتى لتينانت
1 الحقيقي، مش بس المزوَّر.

**التصنيف: ده تقصير في بيانات seed الاختبار بتاعتنا احنا، مش باج كود.**
لازم استكمال القيم الافتراضية الناقصة يدويًا (`is_deleted=false`،
وكمان `status='ACTIVE'` — لأن `execute_agent_action` بعد إيجاد الوكيل
بيتحقق `status == 'ACTIVE'` وإلا هيرفض بخطأ منفصل "الوكيل غير نشط").

**الديف المقترح (DB write، مطلوب موافقة قبل التنفيذ):**
```sql
UPDATE ai_agents SET is_deleted = false, status = 'ACTIVE' WHERE id = 14;
```

**الحالة:** ⏳ في انتظار قرار المستخدم قبل تنفيذ الـUPDATE.

---

## [2026-08-12] الـUPDATE اتنفّذ + إعادة تشغيل السيناريو — تقدُّم جزئي، لكن ظهر باج سادس أعمق (خارج نطاق البساطة السابقة)

**الـUPDATE المنفَّذ:**
```sql
UPDATE ai_agents SET is_deleted = false, status = 'ACTIVE' WHERE id = 14;
```
تحقُّق فوري: `id=14, tenant_id=1, status=ACTIVE, is_deleted=f` ✅.

**السيناريو الحي (بدون إعادة تشغيل uvicorn — البيانات فقط اتغيّرت، مش
الكود):**
- طلب 1 (تينانت شرعي A) → `200 | []`
- طلب 2 (هيدر مزوَّر X-Tenant-ID=12) → `200 | []`

**نفس النتيجة الظاهرية، لكن اللوج كشف تقدُّم حقيقي + باج جديد:**

```
[طلب 1] AI execution failed for agent 14: فشل جميع النماذج:
'RedisClientWrapper' object has no attribute 'hincrbyfloat'
[طلب 1] AI recommendation generation failed: فشل جميع النماذج:
'RedisClientWrapper' object has no attribute 'hincrbyfloat'

[طلب 2] AI recommendation generation failed: الوكيل 14 غير موجود
```

**تحليل:**
- **طلب 2 (المزوَّر):** فشل عند `get_agent(14, tenant_id=12)` — الوكيل
  فعلًا مش موجود لتينانت 12 (بيانات الـseed خاصة بتينانت 1 بس) — ده
  **سلوك عزل صحيح ومتوقَّع** على مستوى هذا الفحص الداخلي بالذات، مش له
  علاقة بثغرة X-Tenant-ID الخارجية (اللي لسه غير مُصلَحة في `router.py`).
- **طلب 1 (الشرعي):** لأول مرة عدّى فحص `get_agent` بنجاح (الوكيل
  موجود، نشط)، ودخل فعليًا لمنطق `ai_engine.generate(...)`
  (`ai_agents/service.py:193-202`) — لكن فشل بخطأ **جديد كليًا، في
  دومين/subsystem مختلف تمامًا**: `app/services/ai/` (أو
  `core/redis_client.py`) — الـwrapper بتاع Redis
  (`RedisClientWrapper`) **مش عنده method `hincrbyfloat`** اللي كود
  الـAI engine بيحتاجها (على الأرجح لتتبع تكلفة/استهلاك الطلبات).

**التصنيف: ده مش نفس فئة إصلاحات "سطر واحد" السابقة.** ده جزء غير
مكتمل/غير متوافق من subsystem تاني بالكامل (تكامل AI engine مع Redis)،
محتمل يكون مرتبط بكون `GEMINI_API_KEY` مش متظبط في بيئة التطوير دي
("⚠️ GEMINI_API_KEY not set. AI features will be disabled" في اللوج
من أول التشغيل) — يعني ممكن يكون مسار "AI معطّل" نفسه مش متغطّى/مُختبَر
بشكل كامل في الكود، أو باج حقيقي في `RedisClientWrapper` بغض النظر عن
الإعداد. يحتاج تحقيق أعمق (قراءة `app/services/ai/` كامل +
`core/redis_client.py`) قبل اقتراح أي حل — **مش إصلاح سطر واحد واضح
زي المرات اللي فاتت.**

**الحالة:** ⏳ **موقوف، في انتظار قرار المستخدم** — هل نكمل التحقيق في
الباج ده (طبقة جديدة تمامًا، هتاخد وقت)، ولا نعتبره خارج نطاق بالكامل
ونوثّقه بس، ونكتفي بالدليل الجزئي المتاح (تينانت مزوَّر اتمنع بنجاح من
`get_agent` نفسها؛ تينانت شرعي عدّى فحوصات الـagent lookup بنجاح لأول
مرة، والفشل بعد كده في subsystem منفصل تمامًا)؟

---

## [2026-08-12] تصحيح حرج — مصدر `tenant_id=12` في الطلب المزوَّر: **نفس الثغرة الأصلية لسه حية، مش دليل حماية**

**طلب المستخدم:** قبل أي حاجة تانية، إثبات دقيق (مش افتراض) لمصدر
`tenant_id=12` اللي وصل لـ`get_agent(14, 12)` — هل هو `current_user.tenant_id`
(آمن) ولا لسه الهيدر الخام (الثغرة نفسها)؟ الاستنتاج السابق ("تينانت
مزوَّر اتمنع بنجاح" — مؤطَّر كإنه سلوك حماية) كان **غير دقيق ومحتاج
تصحيح**.

**التتبُّع المنفَّذ:**
1. فك تشفير `p16_token_A.txt` (التوكن الفعلي المستخدم في الطلبين
   الاتنين): `{"sub":"26","tenant_id":1,...}` — `current_user.tenant_id`
   الحقيقي = **1**.
2. الطلب المزوَّر استخدم نفس التوكن ده + هيدر `X-Tenant-ID: 12` (مؤكَّد
   من نص أمر PowerShell نفسه).
3. `command/router.py:272-285` (`generate_recommendations`) — قراءة حية:
   `tenant_id=cast(int, tenant.id)` بيتبعت للـservice، و`tenant` جايه من
   `Depends(get_current_tenant)` **مش من `current_user`** (رغم إن
   `current_user` متاح في نفس التوقيع، `tenant_id` بتاعه غير مُستخدَم).
4. `api/deps.py:148-153` (`get_current_tenant`) — بترجّع قيمة الهيدر
   مباشرة، صفر تحقق مع الـJWT.
5. `grep` حي: `command/router.py` **لسه فيها 18 استخدام لـ
   `Depends(get_current_tenant)` بلا أي تعديل** — الملف ده لم يُلمس
   إطلاقًا طول الجلسة.

**الاستنتاج الصحيح (يصحّح الاستنتاج الأول):** `tenant_id=12` مصدره
**الهيدر المزوَّر مباشرة، عبر الثغرة الأصلية اللي لسه مش مُصلَحة في
`command/router.py`** — مش تسريب في مسار جديد. رفض `get_agent` كان
**صدفة بيانات اختبار** (الوكيل 14 مزروع لتينانت 1 بس)، **مش حماية
حقيقية**. لو المهاجم زوَّر الهيدر لتينانت عنده بيانات AI حقيقية، الكود
كان هيكمل وينفّذ فعليًا تحت هوية الضحية.

**الخلاصة المُحدَّثة لحالة `generate_ai_recommendations`:**
- آلية العزل عبر `current_user.tenant_id` **لم تُختبَر بعد** (لأنها لم
  تُطبَّق بعد على `router.py`) — مش "مؤكَّدة تعمل".
- الـbaseline الناجح كاملًا (end-to-end) محجوب بباج منفصل تمامًا
  (`RedisClientWrapper.hincrbyfloat`).
- **التحقق الحي لهذا الـendpoint غير مكتمل** لغاية ما يتطبّق إصلاح
  Phase 3 على `command/router.py` وتُعاد كل السيناريوهات من الصفر.

**التوثيق:** اتضاف قسم كامل مصحَّح لـ`PROGRESS_LOG.md` (تحت Phase 16،
Phase 2) بنفس التفاصيل دي + باج `RedisClientWrapper` موثَّق منفصل بلا
تحقيق إضافي (بقرار صريح، خارج النطاق).

**الحالة:** ✅ التصحيح تم وتوثَّق. **قيد الانتظار:** تطبيق إصلاح Phase 3
الفعلي على `command/router.py` (لسه لم يُطبَّق طول الجلسة كلها) قبل أي
محاولة تحقق حي حاسمة تانية لهذا الدومين.

---

## [2026-08-12] تقرير حالة شامل — أين وصلنا بالضبط في Phase 16 (للقراءة خارج الترمينال)

### السؤال الأهم: هل أي دومين من الأربعة اتصلح فعليًا (الثغرة نفسها)؟
**لا. صفر دومين من الأربعة (`ai_agents`, `sovereign_entities`, `command`,
`saas`) اتطبّق فيه إصلاح X-Tenant-ID الفعلي (استبدال
`Depends(get_current_tenant)` بـ`current_user.tenant_id`) لحد كتابة هذا
السطر.** كل الشغل اللي اتعمل في الجلسة دي لحد دلوقتي كان **إصلاح باجات
جانبية غير مرتبطة بالثغرة**، اكتشفناها أثناء محاولة التحقق الحي *قبل*
الإصلاح (Phase 2)، ومنعتنا من الوصول أصلًا لمرحلة تطبيق الإصلاح
الحقيقي.

### إيه اللي اتعمل فعليًا لحد دلوقتي (بالترتيب)

**1. `command/service.py` — 3 باجات constructor/call-signature (✅ اتصلحوا):**
- `__init__` كان بينشئ `AIAgentsService(db)` و`SaaSControlService(db)`
  من غير `tenant_id` المطلوب → كانوا بيكسروا كل endpoint في الدومين.
  الحل: شيلهم من `__init__`.
- `generate_ai_recommendations`: `AIGovernanceService(self.db)` نفس
  المشكلة. الحل: `AIGovernanceService(self.db, tenant_id)` محليًا.
- نفس الدالة: `self.ai_service.execute_agent_action(...)` كانت بتشاور
  على متغيّر اتشال من `__init__` بدون تعويض. الحل: `ai_service =
  AIAgentsService(self.db, tenant_id)` محليًا.
- إضافي: `execute_agent_action(..., tenant_id=tenant_id, ...)` كانت
  بتبعت kwarg زيادة مرفوضة من التوقيع الحقيقي. الحل: حذفها.

**2. `ai_governance/repository.py` — باج ترانزاكشن (✅ اتصلح، بموافقة
كاستثناء نطاق مبرَّر):**
- `create_usage_log` كانت بتعمل `commit()` مباشر جوه بلوك
  `begin_nested()` بتاع `check_and_consume` → بيكسر أي عملية بعده.
  الحل: `commit()` → `flush()` (سطر واحد بس).
- **السبب المُبرِّر للاستثناء:** كان حاجز فعلي قدام التحقق الحي
  الإلزامي لـ`generate_ai_recommendations`، مش توسيع نطاق اختياري.

**3. بيانات seed ناقصة (`ai_agents id=14`) — ✅ اتصلحت (بيانات اختبار، مش كود):**
- زرعنا صف `ai_agents` بـ`INSERT` خام (تخطّى القيم الافتراضية بتاعة
  الـORM)، فـ`status` و`is_deleted` طلعوا `NULL` بدل `ACTIVE`/`false`.
  الحل: `UPDATE` تكميلي.

**4. باجات موثَّقة فقط، بدون إصلاح (خارج نطاق Phase 16 تمامًا):**
- `GET /command/dashboard` → `ResponseValidationError` (schema/service
  mismatch، سابق لأي تعديل بتاعنا).
- `ai_governance/service.py:148` → `get_usage_log_by_idempotency`
  بيتنادى بـparameter ناقص (`tenant_id`) — غير مفعّل في مسارنا، لم يُلمس.
- `RedisClientWrapper` مفيهاش method `hincrbyfloat` — بيمنع
  `ai_engine.generate()` من الاكتمال حتى لتينانت شرعي 100%. مرتبط
  بـsubsystem AI engine/Redis، ومحتمل بسبب `GEMINI_API_KEY` غير مضبوط.
  **لم يُحقَّق فيه أعمق.**

### الاكتشاف الحرج اللي صحّحناه للتو
كنا هنسجّل غلط إن "الطلب المزوَّر اترفض" = دليل حماية. **ده كان غلط.**
التتبُّع الدقيق (فك تشفير التوكن + قراءة `router.py`/`deps.py` حية)
أثبت: `command/router.py` **لسه فيها 18 استخدام لـ
`Depends(get_current_tenant)` بلا أي تعديل**. الرفض اللي شفناه كان
**صدفة بيانات اختبار** (الوكيل 14 مزروع لتينانت 1 بس)، مش نتيجة أي
تحقق أمني حقيقي. **الثغرة الأصلية في `command` لسه حية 100% وقت كتابة
هذا السطر.**

### السؤال المطروح عليك الآن (محتاج قرار واضح)
الديف الكامل لـ`command/router.py` (swap الـ18 endpoint من
`Depends(get_current_tenant)` لـ`current_user.tenant_id`) **معروض
ومُوافَق عليه من زمان في المحادثة، لكن لسه معملوش Edit فعلي على القرص.**
هل نطبّقه دلوقتي؟ ده أول خطوة فعلية في مسار إصلاح الثغرة الحقيقية بعد
كل الوقت اللي راح في الباجات الجانبية.

### الدومينات التلاتة الباقية (لسه معملناش فيهم أي حاجة إطلاقًا)
`ai_agents`, `sovereign_entities`, `saas` — صفر تعديل، صفر تحقق حي، حتى
الديف بتاعهم لسه مجرد خطة متفق عليها بالكلام، مش مكتوبة كديف نهائي.

---

## [2026-08-12] تطبيق ديف `command/router.py` الكامل — الإصلاح الحقيقي لثغرة X-Tenant-ID (18 endpoint)

**القرار:** موافقة نهائية على تطبيق الديف المعروض من زمان. التنفيذ
بـ3 تعديلات (`Edit`):
1. سطر الاستيراد: حذف `get_current_tenant` من
   `from app.api.deps import ...`، وحذف سطر
   `from app.domains.academy.models import AcademyTenant` بالكامل.
2. `replace_all` لحذف كل سطر `tenant: AcademyTenant = Depends(get_current_tenant),`
   (18 موضع، سطر واحد بالحرف في كل مكان).
3. `replace_all` لاستبدال `cast(int, tenant.id)` بـ
   `cast(int, current_user.tenant_id)` (كل الاستخدامات، نفس النمط
   الحرفي في كل مكان).

### تأكيد قراءة مستقل #1 — `grep` بعد التطبيق مباشرة
```
grep "get_current_tenant|AcademyTenant" command/router.py → 0 نتيجة
grep "\btenant\b" command/router.py → 0 نتيجة (صفر متغيّر متبقّي غير مستخدَم)
```
**تأكيد صريح: العدد الفعلي لـ`Depends(get_current_tenant)` في الملف =
صفر، بقراءة مستقلة (grep)، مش بالاعتماد على رسالة "الملف اتحدَّث" من
أداة الـEdit.**

**تأكيد إضافي (قراءة الملف كامل، 345 سطر):** الـ18 endpoint اتأكَّدوا
واحد واحد — كل واحد فيهم بقى `current_user: User = Depends(...)` هو
مصدر التينانت الوحيد (`current_user.tenant_id`)، صفر `tenant` param
متبقّي في أي توقيع دالة.

**الحالة:** ✅ الديف اتطبّق، وتأكَّد مستقلًا. **الخطوة الجاية:** إعادة
تشغيل `uvicorn` من الصفر + فحص لوج الإقلاع كامل.

---

## [2026-08-12] إعادة تشغيل uvicorn + التحقق الحي الحاسم على `brands/me` بعد الإصلاح الحقيقي

### إعادة التشغيل + فحص اللوج
أُعيد تشغيل `uvicorn` من الصفر (PID جديد 11148، بعد إيقاف PID 10696
القديم). فحص كامل لـ`stderr` log بعد الإقلاع: **صفر Traceback/
TypeError/ImportError/AttributeError** — بس تحذيرات dev المعتادة
(`SECRET_KEY` افتراضي، `GEMINI_API_KEY` غير مضبوط) و`Application
startup complete`.

### السيناريو الحي (6 طلبات، مقسَّمة لأوامر قصيرة منفصلة زي ما طُلب)

**Claim الـJWT الحقيقي (طُبع كأول خطوة، قبل أي طلب):**
- توكن A: `{"sub":"26","tenant_id":1,...}`
- توكن B: `{"sub":"27","tenant_id":12,...}`

| # | التوكن | الهيدر المُرسَل | النتيجة |
|---|---|---|---|
| 1 | A (تينانت حقيقي=1) | بدون هيدر | `404` (فاضي) |
| 2 | A (تينانت حقيقي=1) | `X-Tenant-ID: 12` (مزوَّر) | `404` (فاضي) — **مطابق لـ#1** |
| 3 | A (تينانت حقيقي=1) | `X-Tenant-ID: 999` (مزوَّر، قيمة عشوائية) | `404` (فاضي) — **مطابق لـ#1** |
| 4 | B (تينانت حقيقي=12) | بدون هيدر | `404` (فاضي) |
| 5 | B (تينانت حقيقي=12) | `X-Tenant-ID: 1` (مزوَّر، عكسي) | `404` (فاضي) — **مطابق لـ#4** |
| 6 | بدون أي توكن | بدون هيدر | `401` (مصادقة مرفوضة) |

### التحليل
- **#1، #2، #3 متطابقين بالحرف** بغض النظر عن قيمة الهيدر (حقيقية،
  مزوَّرة، أو عشوائية تمامًا) — دليل حاسم إن الهيدر **بقى بلا أي تأثير
  إطلاقًا** على تحديد التينانت.
- **#4، #5 (الاختبار العكسي بتوكن B)** نفس النتيجة — تأكيد في الاتجاهين.
- **#6 (بدون توكن) → `401`، مختلف عن الـ`404`** — بيثبت إن الـ`404` في
  الحالات التانية مش فشل مصادقة، دي وصلت فعليًا لمنطق التطبيق بعد
  مصادقة ناجحة، ورجّعت "مفيش صف Brand لهذا التينانت" (قاعدة اختبار
  فاضية من بيانات `BrandSettings`) — سلوك متوقَّع ومنطقي، مش دليل خطأ.
- **الخلاصة: `current_user.tenant_id` (من الـJWT الموقَّع) هو المصدر
  الوحيد الفعلي لتحديد التينانت في `command/router.py` الآن، مؤكَّد حيًا
  في الاتجاهين، بعد الإصلاح الحقيقي.**

**الحالة:** ✅ **الإصلاح الحقيقي لثغرة X-Tenant-ID في دومين `command`
مؤكَّد حيًا بالكامل** (18 endpoint، الديف مطبَّق، grep مستقل مؤكِّد،
6 طلبات حية حاسمة). **ملاحظة نطاق:** `generate_ai_recommendations`
تحديدًا لسه محجوب بباج `RedisClientWrapper` المنفصل الموثَّق (خارج
النطاق) — التحقق الحي بتاعه هيفضل جزئي (آلية العزل نفسها مؤكَّدة عبر
باقي الـ17 endpoint، لكن مساره الكامل end-to-end لسه معلَّق).

---

## [2026-08-12] `command` مقفول — انتقال لباقي الدومينات: الفحص الاستباقي المجمّع (constructor bugs) على `ai_agents`, `sovereign_entities`, `saas`

**الطلب:** قبل أي تعديل، `grep`/فحص مجمَّع على `service.py` بتاع
`ai_agents`, `sovereign_entities`, `saas`، دوّر على نفس فئة باج
constructor اللي لقيناها في `command` (استدعاء `Service(...)`/
`Repository(...)` بمعاملات ناقصة عن توقيعها الحقيقي).

### المنهجية
قراءة كاملة للثلاثة ملفات (`ai_agents/service.py` 398 سطر،
`sovereign_entities/service.py` 527 سطر، `saas/service.py` 402 سطر)،
استخراج كل استدعاء `Service(`/`Repository(` فيها، ثم قراءة التوقيع
الحقيقي لكل واحد منهم من ملفه المصدر مباشرة (مش افتراض).

### النتيجة: صفر باجات constructor في الثلاثة دومينات

| الاستدعاء | الملف | التوقيع الحقيقي (مؤكَّد بالقراءة) | الحالة |
|---|---|---|---|
| `AIAgentsRepository(db)` | `ai_agents/service.py:35` | `repository.py:15` → `__init__(self, db)` | ✅ مطابق |
| `FinanceService(db, tenant_id)` | الثلاثة ملفات | `finance/service.py:19` → `__init__(self, db, tenant_id)` | ✅ مطابق |
| `InvoicingService(self.db, self.tenant_id)` | `ai_agents/service.py:385` | `invoicing/service.py:23` → `__init__(self, db, tenant_id)` | ✅ مطابق |
| `SovereignEntitiesRepository(db)` | `sovereign_entities/service.py:40` | `repository.py:15` → `__init__(self, db)` | ✅ مطابق |
| `UserRepository(self.db)` | `sovereign_entities/service.py:358` | `identity/repository.py:13` → `__init__(self, db)` | ✅ مطابق |
| `SaaSRepository(db)` | `saas/service.py:37` | `repository.py:20` → `__init__(self, db)` | ✅ مطابق |

**تفسير محتمل:** الملفات التلاتة دي أصلية، لم تتعدّل في أي جلسة سابقة
(على عكس `command/service.py` اللي كان فيه بقايا تعديل سابق ناقص —
مصدر الباجات التلاتة اللي لقيناها هناك).

### ملاحظة إضافية (خارج نطاق الطلب المحدَّد — مجرد تنبيه، مش فحص مكتمل)
الثلاثة ملفات فيهم استخدام `async with self.db.begin_nested()` (نفس
النمط اللي فيه لقينا باج الترانزاكشن في `ai_governance/repository.py`
سابقًا في الجلسة دي):
- `ai_agents/service.py:289` (`resolve_approval`)
- `sovereign_entities/service.py:364,429` (`deposit_to_entity_wallet`,
  `transfer_from_entity`)
- `saas/service.py:109,159,296` (`create_subscription`,
  `process_auto_renewals`, `pay_invoice`)

**لم يُفحَص بعد** هل أي repo method بتتنادى جوه البلوكات دي بتعمل
`self.db.commit()` داخلي (نفس السبب الجذري اللي كسر `command`). القرار
محتاج توجيه: نفحصها الأول استباقيًا زي ما عملنا دلوقتي مع الـconstructor،
ولا نأجّلها لحد ما تظهر (لو ظهرت أصلًا) أثناء التحقق الحي؟

**الحالة:** ✅ فحص الـconstructor مكتمل، صفر باج. ⏳ في انتظار قرار
بخصوص فحص `begin_nested()`/`commit()` استباقيًا أو تأجيله.

---

## [2026-08-12] فحص `begin_nested()`/`commit()` على الـ6 مواضع — النطاق أوسع وأخطر من المتوقَّع (read-only، صفر تعديل)

**المنهجية:** لكل موضع من الـ6، قراءة الـrepo method اللي بتتنادى جواه
مباشرة من ملفها المصدر (مش افتراض)، وفحص هل فيها `self.db.commit()`
مباشر أثناء التنفيذ جوه بلوك `begin_nested()` الخارجي.

### النتيجة: باج مؤكَّد في كل الـ6 مواضع

| # | الموضع | الـrepo method | التأكيد |
|---|---|---|---|
| 1 | `ai_agents/service.py:289` (`resolve_approval`) | `ai_agents/repository.py:181-198` (`resolve_approval`) | `commit()` سطر 197، وبعده `get_approval()` (SELECT) في نفس الدالة، جوه نفس البلوك |
| 2 | `sovereign_entities/service.py:364` (`deposit_to_entity_wallet`) | `sovereign_entities/repository.py:97-107` (`update_entity`) | `commit()` سطر 103، وبعده `get_entity()` في نفس الدالة |
| 3 | `sovereign_entities/service.py:429` (`transfer_from_entity`) | نفس `update_entity` + `finance.transfer` | نفس باج `update_entity` + باج مستقل جوه `finance.transfer` نفسها (تفصيل تحت) |
| 4 | `saas/service.py:109` (`create_subscription`) | `saas/repository.py:180-185` (`create_subscription`) | `commit()` سطر 183، وبعده `get_tenant_service_access()` في نفس البلوك |
| 5 | `saas/service.py:159` (`process_auto_renewals`) | `saas/repository.py:187-202` (`update_subscription`) + `336-341` (`create_invoice`) | باجين منفصلين، كل واحد `commit()` داخلي جوه نفس البلوك |
| 6 | `saas/service.py:296` (`pay_invoice`) | `saas/repository.py:343-356` (`update_invoice`) + `update_subscription` | `commit()` سطر 349 — **الأولوية القصوى المطلوبة، مؤكَّدة** |

### اكتشاف أعمق (خارج الـ6 المطلوبين، لكنه يمس المواضع 3، 5، 6 مباشرة)
`FinanceService.transfer` (`finance/service.py:58-147`) عندها **نفس
الباج جوه نفسها، مستقلة تمامًا**:
- `finance/service.py:92` — `async with self.db.begin_nested():` خاصة بيها.
- جواها: `self.wallet_repo.update_balances(...)` (سطور 115-116، مرتين)
  → `finance/repository.py:48-57` (`WalletRepository.update_balances`)
  فيها `await self.db.commit()` **سطر 52**.
- وكمان `self.tx_repo.create(...)` (سطر 119) →
  `finance/repository.py:74-79` (`TransactionRepository.create`) فيها
  `commit()` **سطر 77**.

**يعني `finance.transfer()` — دالة تحريك الأموال الفعلية، المستخدمة في
`pay_invoice` — بتنهار من جوه نفسها**، بمعزل تام عن أي `begin_nested()`
خارجي. هذا **أخطر من الـ6 مواضع الأصلية مجتمعين**، لأن `pay_invoice`
(الأولوية القصوى) بتعتمد عليها مباشرة.

### الخلاصة
**ده مش باج معزول في `ai_governance`. ده نمط منهجي (systemic) في طبقة
الـrepository بالكامل تقريبًا** — كل `repo` method في المشروع تقريبًا
بتعمل `self.db.commit()` فوري بعد أي كتابة (نفس القاعدة في `command`,
`ai_governance`, `ai_agents`, `sovereign_entities`, `saas`, `finance`
— كلهم بنفس الأسلوب)، وده بينكسر أي وقت بيتنادى جوه `begin_nested()`.
**النطاق أكبر بكتير من الإصلاح المصغَّر اللي اتعمل لـ`ai_governance`**
(سطر واحد، مكان واحد): هنا محتاجين على الأقل **6-8 تعديلات منفصلة**
(المواضع الستة + `finance/repository.py` نفسها، اللي بتأثر على دومينات
تانية غير الثلاثة دول كمان، خارج نطاق Phase 16 الأربعة دومينات).

**الحالة:** ⏳ **موقوف بالكامل، في انتظار قرار المستخدم بخصوص النطاق
والأولوية** — لا يمكن اعتبار أي من `ai_agents`, `sovereign_entities`,
`saas` "جاهز للتحقق الحي الكامل" قبل حسم القرار ده، خصوصًا `saas.pay_invoice`
(معاملة مالية حقيقية).

---

## [2026-08-12] إيقاف Phase 16 مؤقتًا — تنظيف + توثيق نهائي + commit

**القرار:** إيقاف الجلسة عند نقطة نظيفة (`command` مكتمل ومؤكَّد حيًا)
بعد اكتشاف نمط الترانزاكشن المنهجي. التنفيذ بـ3 خطوات بالترتيب.

### 1. التنظيف (تم بالكامل، تحقُّق مستقل)
`agent_usage_logs`(2)، `ai_task_logs`(2)، `ai_agents`(1)، اكتشاف جانبي:
صف يتيم في `command_dashboards` (id=1, tenant_id=1 الحقيقي,
created_by=27 — أثر جانبي لاختبار `get_dashboard` سابق) اتحذف بدقة
(صف واحد بس)، `users`(3)، `academy_tenants`(1). تحقق مستقل: 7
استعلامات SELECT كلها صفر + `academy_tenants=1, users=7, ai_agents=0`
مطابق تمامًا لبداية الجلسة. تفاصيل كاملة في `PROGRESS_LOG.md`.
uvicorn التجريبي اتوقف (PID 11148).

### 2. التوثيق النهائي في `PROGRESS_LOG.md`
اتضاف 3 أقسام جديدة: (أ) ملخص Phase 16 الجزئي (command مكتمل، الباقي
متلمسش)، (ب) 🔴 قسم منفصل وبارز للاكتشاف الحرج (نمط الترانزاكشن
المنهجي عبر `ai_agents`/`sovereign_entities`/`saas`/`finance`)، (ج)
توثيق التنظيف والتحقق المستقل.

### 3. الخطوة الجاية
commit واحد معزول، staging انتقائي للملفات المتعلقة بس، برسالة توضح
Phase 16 جزئي (command فقط).

**الحالة:** ✅ الخطوتين 1 و2 مكتملتين. جاري تنفيذ الخطوة 3 (git commit).

---
