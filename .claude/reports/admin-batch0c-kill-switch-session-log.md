# الدفعة 0-C — قراءة فقط: تشخيص الـKill Switch الطارئ (`admin` domain)

**التاريخ:** 2026-09-22
**النوع:** قراءة فقط. صفر تعديل كود، صفر كتابة DB، صفر migrations، صفر تشغيل سيرفر، صفر اختبارات حية، صفر staging/commit، ولم يُكتب شيء في `PROGRESS_LOG.md`.
**ملاحظة إجرائية (انحراف معلن):** أُنشئ هذا الملف بعد إنهاء القراءة بدل إنشائه في الخطوة 0 قبلها (نفس الانحراف المذكور في جلسة 0-B). المحتوى كله مكتوب من نتائج القراءة الفعلية.
**استعلام DB واحد (SELECT فقط):** داخل `SET TRANSACTION READ ONLY`، من سكربت مؤقت في مجلد scratchpad خارج المشروع (لم يُنشأ أي ملف داخل المشروع غير هذا التقرير). موسوم "VERIFIED (ran)" حيث استُخدم.

**مفتاح الوسوم:** **VERIFIED** = نُفِّذ فعليًا (استعلام DB / grep). **READ-ONLY** = مقروء من الكود فقط ولم يُشغَّل.

---

## 0) ما قُرئ
- `CODING_STANDARDS.md` (42 سطر): async، pydantic لكل المدخلات/المخرجات، اختبارات pytest، لا بنود عن الـkill switch.
- دومين `admin`: `app/domains/admin/router.py` (24 سطر) — **الملف الوحيد في المجلد** (لا `__init__.py`، لا `service.py`، لا `schemas.py`، لا `models.py`).
- `app/core/features.py` (33 سطر) — منطق الحالة الفعلي.
- `app/core/redis_client.py` (الغلاف كامل).
- `app/core/security.py` (`get_current_user`, `get_current_active_user`, `get_current_superuser`, `get_current_tenant`) + `app/api/deps.py` (shim).
- `app/main.py`: قائمة الاستيرادات، `routers_config`، حلقة `include_router`، وendpoints الـAI (`/api/ai/chat`, `/api/ai/cost`, `/api/ai/routing`).
- `ai_agents/{service,router,models,schemas}.py` كاملة تقريبًا، `ai_governance/{service,router}.py` كاملة.
- `services/ai/engine.py` (محرك التوليد) و`core/ai_engine.py` (مسار Gemini المنفصل للأكاديمية).
- استدعاءات `AIAgentsService` في `tasks/billing.py`، `tasks/agritech.py`، `insurance/service.py`.
- `core/audit.py`.
- تقارير سابقة تذكر الـkill switch: `comprehensive-services-inventory-session-log.md` (سطر 158-159، 379، 476)، `comprehensive-inventory-section-batch1.md` (90-92)، `comprehensive-inventory-section3-batchB.md` (224)، `batch5-audit-security-iot-translation-zamakana-admin-privacy-automation.md` (179). كلها تقول: "الراوتر غير مسجَّل في main.py" — **تأكد صحتها الآن** (لم يتغير شيء، `git log` للملفين = commit أولي فقط، و`git status` لهما نظيف).
- لم أقرأ `PROJECT_AUDIT.md` سطرًا بسطر (اكتفيت بـgrep على "kill switch/emergency" عبر المشروع كله). **فجوة قراءة معلنة.**

---

## 1) ماذا يفعل الـendpoint بالضبط؟

**الكود (READ-ONLY):** `POST /admin/system/toggle-ai-agents?suspend=<bool>` (`admin/router.py:9-21`)
تستدعي `SystemFeatures.set_system_suspended(suspend)` وترجع `{"message": "AI Agents system is now suspended|active"}`.

- **ماذا يُطفئ؟** لا شيء اليوم. يكتب فقط مفتاح Redis واحدًا.
- **أين تُخزَّن الحالة؟** Redis، المفتاح `system:ai_agents:suspended` (`features.py:6`)، القيمة `json.dumps(bool)`، عبر `setex` بـ**TTL = 30 يومًا** (`features.py:7, 29-33`).
- **عالمي أم لكل tenant؟** عالمي (مفتاح واحد بلا tenant_id في اسمه).
- **هل يقرأ أحد هذه الحالة قبل تشغيل الوكلاء؟** **لا. VERIFIED (grep):**
  `grep -rn "SystemFeatures|get_system_suspended|set_system_suspended|system:ai_agents|ai_agents:suspended"` على `app/` **و** `tests/` يُرجع فقط: تعريفات `features.py` + استدعاء `set_system_suspended` الوحيد في `admin/router.py:19`. **`get_system_suspended` لا يستدعيها أي كود في المشروع كله.** الحالة "write-only".
- **هل الراوتر مسجَّل؟** **لا. VERIFIED (grep):** `admin_router` / `domains.admin` لا يظهران في `main.py` إطلاقًا؛ `routers_config` (main.py:271-308) لا يحوي دومين admin. ولا أي إشارة له في `openapi.json` أو `eppne-web` (grep: صفر).
- **تفاصيل ثانوية في `features.py` (READ-ONLY):**
  - `except:` عارية في `get_system_suspended` (سطر 20) → أي قيمة تالفة تُقرأ `False` (= النظام يعمل) — **fail-open صامت**.
  - لو Redis واقع: `redis_client.get` يرمي استثناء (لا try/except حوله) → سلوك المستهلك المستقبلي غير محدد ما لم يُقرَّر (fail-open أم fail-closed).
  - الـTTL (30 يومًا) يعني أن الإيقاف "الطارئ" **ينتهي وحده بصمت** بعد 30 يومًا ويعود كل شيء للعمل.

---

## 2) من المخوَّل؟ وهل هو صحيح لمفتاح طوارئ عالمي؟

**READ-ONLY (كود) + VERIFIED (DB):**
- الاعتماد: `Depends(get_current_superuser)` (`admin/router.py:12`) → `get_current_active_user` → `get_current_user` (`security.py:209-215, 91-…`).
  الفحص: `system_role in ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]`.
- **مشكلة tenant-from-header: لا.** لا يستخدم `X-Tenant-ID`؛ الـtenant يأتي من claim `tenant_id` داخل الـJWT ويُطابَق مع `user.tenant_id` (`security.py:117-133`). (مشكلة `X-Tenant-ID` المعروفة في `get_current_tenant` لا تمس هذا المسار.)
- **لكن الدور نفسه "لكل tenant" وليس "على مستوى المنصة": VERIFIED (ran):**
  `select tenant_id, system_role, count(*) from users where system_role in ('SUPER_ADMIN','EXECUTIVE_DIRECTOR') group by 1,2` →
  `[(1, 'SUPER_ADMIN', 25), (16, 'SUPER_ADMIN', 1)]`. أي **26 مستخدمًا بصلاحية "superuser" موزَّعين على tenantين**، وصفر `EXECUTIVE_DIRECTOR` (رغم أن `scripts/create_superuser.py:32` يُنشئ EXECUTIVE_DIRECTOR — فالحساب الأول الموثَّق غير موجود بهذا الدور فعليًا).
  `get_current_superuser` **لا يفحص أن المستخدم من tenant المنصة**. النتيجة: superuser الخاص بـtenant 16 (أو أي tenant مستقبلًا) يقدر يوقف AI **لكل المستأجرين** — **DoS عابر للمستأجرين**. الدور غير مناسب كما هو لمفتاح عالمي.
  (نفس النمط موجود في `PUT /api/ai/routing` — `main.py:396-410` — تعديل عالمي محروس بنفس الـdependency. خارج نطاق هذه الجلسة، للتنبيه فقط.)
- **مسار الكوكي:** `get_current_user` يقبل توكن من كوكي `access_token`. الكوكي `samesite="strict"` (`identity/router.py:58`) فمخاطر CSRF على POST هذا منخفضة. ملاحظة فقط.
- **هل الفعل مُدقَّق؟ لا (READ-ONLY):** الـendpoint لا يستدعي `audit_log` ولا يسجّل من غيّر الحالة ولا متى. (وحتى لو أضفناه: `core/audit.py:11-31` يكتب سطر JSON إلى logger فقط — **ليس جدول DB ولا سجلًا محصَّنًا ضد العبث**. هل `AgentAuditLog` في ai_governance صالح لهذا الغرض لم أتحقق — يتطلب `agent_id` على الأرجح، فلا يصلح لحدث عالمي.)
- **شكل الـAPI:** `suspend: bool` كـquery param على POST بلا body ولا `response_model` (مخالف لمعيار "pydantic لكل المدخلات/المخرجات" في CODING_STANDARDS §1). ولا يوجد GET لقراءة الحالة الحالية.

---

## 3) لو سجّلناه اليوم: هل يوقف الوكلاء فعلًا؟ وما نطاق الضرر؟ وهل هو قابل للعكس؟

**التسجيل (READ-ONLY):** `main.py:310-317` يمرّر `prefix="/api"` لكل راوتر (والـprefix/الـsector داخل tuple `routers_config` **مُهمَلان**، `require_sector` أُلغي). الراوتر يحمل بادئته `"/admin/system"`، فالمسار سيكون `POST /api/admin/system/toggle-ai-agents`. يحتاج استيرادًا `from app.domains.admin.router import admin_router` (الاسم غير القياسي `admin_router` لا `router`) + سطر tuple. **`admin/` بلا `__init__.py`** (يعمل كـnamespace package لكن يخالف باقي الدومينات).

**الحكم: لو سُجِّل كما هو يصبح "مفتاحًا موصولًا بلا شيء" — أخطر من غيابه.** المُشغِّل يضغطه، يرى `"suspended"`، ويظن أن AI توقف، بينما:

نقاط التنفيذ الفعلية للـAI (كلها لا تقرأ المفتاح):
1. `AIAgentsService.execute_agent_action` (`ai_agents/service.py:147`) — يفحص **حالة الوكيل الفردية فقط**: `agent.status != ACTIVE` → `PermissionDeniedError` (سطر 162-163). لا فحص عالمي. مُستدعى من: `ai_agents/router.py:82` (`POST /agents/{id}/execute`)، `insurance/service.py` (agent_id=10)، `tasks/agritech.py:158+` (agent_id=3)، وحسب اختبارات موجودة أيضًا من `realestate` و`invitations`.
2. `AIEngine.generate` (`services/ai/engine.py:59`) — نقطة التوليد الموحَّدة، لا فحص. مُستدعى من موضعين فقط: `ai_agents/service.py:193` و**`POST /api/ai/chat` (`main.py:363-379`)**.
3. **`POST /api/ai/chat` يستخدم `get_current_user_optional`** (`main.py:366`) — أي أنه يعمل **حتى بدون تسجيل دخول** ولا يمر أصلًا عبر `AIAgentsService`، فأي بوابة على مستوى الوكيل لن توقفه؛ فقط بوابة داخل `AIEngine.generate` توقفه. (ملاحظة أمنية جانبية منفصلة، غير مُعالَجة هنا.)
4. مسار منفصل تمامًا: `core/ai_engine.py` (`analyze_and_recommend_courses`، Gemini، مستدعى من `academy/service.py:20`) — لا يمر بـ`services/ai/engine.py` ولا بأي بوابة.
5. `AIGovernanceService.check_and_consume` (نقطة الخنق لـ~14 دومينًا): تفحص الحصص فقط؛ لا تفحص المفتاح العالمي (`ai_governance/service.py:146-…`).

**سياق مهم — الأثر الفعلي اليوم شبه صفر (VERIFIED + READ-ONLY):**
- `AIEngine._call_model` (`engine.py` ~268-283) **محاكاة**: `await asyncio.sleep(0.5)` ثم يرجع نصًا يحوي "(محاكاة)"؛ الاستدعاء الحقيقي لـHTTP **معلَّق (commented)**، ومفاتيح الـAPI نصوص وهمية (`"kimi-k2.6-key"` …). فلا تكلفة ولا اتصال خارجي فعلي اليوم عبر هذا المحرك.
- DB (VERIFIED, ran): `ai_agents` = وكيل واحد فقط (`ACTIVE`)، و`ai_task_logs` = **0** صف. أي لم يُنفَّذ أي إجراء وكيل قط على هذه القاعدة.
- إذًا: الحاجة ليست عاجلة الآن، لكنها **شرط مسبق قبل تفعيل استدعاء LLM حقيقي** — وقتها يصبح غياب مفتاح الطوارئ خطرًا ماليًا/تشغيليًا.

**نطاق الضرر لو فُعِّل صحيحًا بالغلط (بعد الإصلاح، READ-ONLY):** يوقف على **كل المستأجرين**: تنفيذ إجراءات الوكلاء (تحليل مطالبات التأمين، شراء الملكية الجزئية، `chat_with_ai` في الدعوات، تحليل الحساسات الزراعية عالي الأولوية) و`/api/ai/chat`. **لم أتحقق** من سلوك كل مستدعٍ عند رمي استثناء البوابة (بعضها داخل try/except كتأمين سطر ~372-392، وبعضها قد يفشل الطلب كله) — يُفحص في جلسة التنفيذ. لا أثر على بيانات/DB/مالية؛ فقط حجب ميزة مؤقت.

**قابلية العكس:** نعم — `POST suspend=false` أو `DEL` للمفتاح في Redis. لكن: (أ) الحالة في Redis فقط — لو تم `FLUSHALL`/إعادة إنشاء Redis تعود الحالة "يعمل" (fail-open) دون تنبيه؛ (ب) الـTTL يعيدها لـ"يعمل" تلقائيًا بعد 30 يومًا.

---

## 4) هل توجد آلية طوارئ أخرى تجعله زائدًا عن الحاجة؟ (READ-ONLY)

| الآلية | ماذا توقف | نطاقها | مُطبَّقة فعلًا؟ | تكفي بديلًا؟ |
|---|---|---|---|---|
| `PATCH /ai-agents/agents/{id}/status` → `SUSPENDED` (superuser، `ai_agents/router.py:104-120`) | تنفيذ وكيل واحد | **وكيل واحد داخل tenant الطالب** (`repo.get_agent(agent_id, self.tenant_id)`) | **نعم**: `service.py:162` يرفض غير `ACTIVE` | لا كبديل عالمي: لا bulk، لا يمر عبر tenants، لا يوقف `/api/ai/chat` |
| حصص `ai_governance` (`POST /agents/{id}/quotas` بحد 0) | استهلاك وكيل معيّن عبر الدومينات التي تستدعي `check_and_consume` | وكيل × tenant | جزئيًا: تُطبَّق فقط في ~14 موضعًا لا في `execute_agent_action` ولا `/api/ai/chat`؛ وبلا صفوف حصص تُرجع `True` (سماح) | لا |
| `AgentRateLimit` | — | — | **مخزَّنة ومُدارة عبر API لكن `check_and_consume` لا تقرؤها** (الحلقة على `active_quotas` فقط) | لا |
| `Enum SUSPENDED` للوكيل | كما في الصف الأول | — | — | — |

**الخلاصة:** لا توجد آلية طوارئ **عالمية** أخرى؛ الموجود إيقاف يدوي لكل وكيل/tenant. فالـkill switch ليس مكررًا وظيفيًا، لكنه اليوم بلا أثر. (بالمقابل: **غياب المفتاح حاليًا ≠ خطر فعلي** لأن المحرك محاكاة.)

---

## 5) الاختبارات

**الموجود:** لا اختبار للـadmin/features إطلاقًا (grep `tests/`: صفر إشارات لـ`toggle-ai-agents`/`SystemFeatures`/`admin_router`). الاختبارات القريبة: `test_ai_routing_security.py` (نمط جاهز — `find_route` + `direct_dependency_calls` من `tests/route_utils.py` — يصلح قالبًا لاختبار التسجيل والـauth)، و`test_ai_agents_execute_action.py`، و`test_ai_governance_check_and_consume.py`.

**المطلوب لو اخترنا B:**
1. المسار مُسجَّل وتعتمد على الـdependency الصحيحة (نمط `test_ai_routing_security.py`، بلا سيرفر).
2. مستخدم عادي/ADMIN = 403؛ SUPER_ADMIN من tenant غير المنصة = 403 (بعد قرار D1).
3. `suspended=True` → `execute_agent_action` و`AIEngine.generate` يرفضان؛ `False` → يمران (يحتاج Redis؛ اختبار حي بمفتاح اختباري يُنظَّف).
4. المفتاح بلا TTL (أو تحقق `TTL == -1`).
5. حدث تدقيق يُسجَّل عند التبديل (التقاط logger `eppne.audit`).
6. سلوك Redis-down حسب القرار D2.
7. `GET` الحالة (لو اخترناه) يعكس آخر تبديل.
تقدير: ملف اختبار واحد جديد ~120-160 سطرًا.

---

## 6) الخيارات

### (A) تسجيله كما هو — **غير موصى به**
- الحجم: سطران في `main.py` (استيراد + tuple) (+ `__init__.py` فارغ اختياريًا).
- النتيجة: endpoint يكتب مفتاح Redis لا يقرأه أحد + أي superuser من أي tenant يستدعيه + بلا تدقيق + ينتهي بعد 30 يومًا. **أسوأ من الوضع الحالي** لأنه يخلق إحساسًا زائفًا بالأمان ويفتح سطح هجوم جديد (DoS إداري عابر للمستأجرين) دون أي فائدة.

### (B) تسجيله بعد استكمال الناقص — **الموصى به**
المطلوب (كلها صغيرة):
1. **الإنفاذ (الأهم):** بوابة تقرأ `SystemFeatures.get_system_suspended()`:
   - داخل `AIEngine.generate` (`services/ai/engine.py`) — نقطة الخنق الحقيقية للـLLM، تغطي `/api/ai/chat` أيضًا (~5-6 أسطر).
   - وداخل `AIAgentsService.execute_agent_action` قبل سطر 162 برسالة خطأ واضحة (~4-5 أسطر).
   - مسار Gemini المنفصل في `core/ai_engine.py` (الأكاديمية) قرار اختياري (D3) (~4 أسطر).
2. **إزالة الـTTL:** `features.py` من `setex(...30 يومًا)` إلى `set` بلا انتهاء (أو حذف المفتاح عند الإعادة) (~2-3 أسطر) + استبدال `except:` العارية بمعالجة صريحة.
3. **التفويض على مستوى المنصة:** dependency جديدة (أو فحص داخل الراوتر) تشترط `system_role` عالي **و** `tenant_id == tenant المنصة` (القيمة الموجودة: `PUBLIC_REGISTRATION_TENANT_ID=1` في config، أو إعداد جديد `PLATFORM_TENANT_ID`) (~8-10 أسطر). (D1)
4. **التدقيق:** `audit_log(action="AI_KILL_SWITCH_TOGGLED", user_id, tenant_id, details={"suspend": …})` (~5 أسطر).
5. **شكل الـAPI:** body schema بدل query param + `response_model` + `GET /status` (~25 سطرًا بين schema وendpoint)؛ الدومين `admin` يحتاج `__init__.py` (ملف فارغ).
6. **التسجيل في `main.py`** (سطران).
7. **الاختبارات** (§5، ملف جديد ~120-160 سطرًا).

الحجم الإجمالي: **ملفات موجودة ستُعدَّل: 5** (`features.py`، `admin/router.py`، `main.py`، `services/ai/engine.py`، `ai_agents/service.py`) — و`core/security.py` سادسًا لو وُضعت الـdependency هناك؛ **ملفات جديدة: 2-3** (`admin/__init__.py`، `admin/schemas.py`، ملف اختبار). تعديلات المنطق نفسها ≈ 50-60 سطرًا + ~150 سطر اختبار. **لم يُنفَّذ شيء.**

### (C) حذفه
- الحجم: حذف `admin/router.py` (24 سطر) و`core/features.py` (33 سطر) = **ملفان، ~57 سطرًا، صفر مراجع أخرى** (VERIFIED بـgrep؛ لا اختبارات ولا فرونت ولا openapi).
- الثمن: لا يبقى أي أساس لإيقاف عالمي؛ وحين يُفعَّل المحرك الحقيقي سنعيد بناءه من الصفر. مقبول فقط إن قررنا أن الإيقاف اليدوي per-agent (§4) يكفي تشغيليًا.

### التوصية
**(B)**، لكن **بجدولة مرتبطة بتفعيل استدعاء الـLLM الحقيقي** لا كأولوية اليوم (المحرك محاكاة، صفر تنفيذات سابقة). الأهم: **لا (A) أبدًا**، و(C) خيار مشروع لو تأجَّل تفعيل LLM لأشهر، لكنه يضيّع أساسًا صغيرًا صحيحًا في فكرته.

### قرارات مطلوبة منك قبل أي تنفيذ
- **D1 — من المخوَّل؟** superuser من tenant المنصة فقط (id=1 اليوم، فيه 25 SUPER_ADMIN — هل هذا العدد مقبول لمفتاح عالمي؟) أم دور/حساب أضيق (مثلًا إنشاء EXECUTIVE_DIRECTOR واحد للمنصة، إذ لا يوجد أي واحد في DB اليوم)؟
- **D2 — سلوك انقطاع Redis:** fail-open (نكمل، مثل الافتراضي الحالي) أم fail-closed (نرفض AI عند تعذر قراءة الحالة)؟ للمفتاح الطارئ عادةً fail-open لتجنب تحويل خلل Redis إلى انقطاع AI شامل، لكنه يعني أن المفتاح قد لا يعمل وقت الحاجة.
- **D3 — أماكن البوابة:** `AIEngine.generate` + `execute_agent_action` (موصى)، هل نضيف مسار Gemini الأكاديمي؟ وهل نمسّ `check_and_consume`؟ (لا أنصح: حصص لا LLM).
- **D4 — هل نضيف `GET /status`؟** (موصى: نعم، وإلا فلا وسيلة لمعرفة الحالة).
- **D5 — الموعد:** الآن أم مؤجَّل حتى تفعيل LLM حقيقي؟
- **إجرائي:** التنفيذ يعدّل ملفات موجودة، فحسب قاعدة "أوقف قبل التعديلات المترتبة" سأنتظر موافقتك الصريحة على D1-D5 قبل أي تعديل.

---

## 7) ملاحظات جانبية (لم تُعالَج، للتسجيل فقط)
1. `POST /api/ai/chat` بلا مصادقة إلزامية (`get_current_user_optional`) — عند تفعيل LLM حقيقي = استهلاك مفتوح لأي زائر. مرشح دفعة أمنية منفصلة.
2. `PUT /api/ai/routing` نفس مشكلة "superuser لكل tenant يغيّر إعدادًا عالميًا" (`main.py:396-410`).
3. حساب EXECUTIVE_DIRECTOR الذي يُنشئه `scripts/create_superuser.py` غير موجود فعليًا في DB (0 صف)؛ كل الـsuperusers الحاليين `SUPER_ADMIN`.
4. `AIEngine._call_model` محاكاة بالكامل (مفاتيح API نصوص وهمية) — لا بدّ من معرفة ذلك قبل أي قرار عن الأولوية.

---

## 8) سؤال جانبي (للجلسة السابقة): هل تُعيد الـlogin تجزئة كلمات المرور (`needs_update` / `verify_and_update`)؟

**الجواب: لا. VERIFIED (grep على `app/`):** لا يوجد في أي مكان `verify_and_update` ولا `needs_update` ولا `.hash(` غير الدوال أدناه.
- تسجيل الدخول: `identity/service.py:111` (`authenticate`) → `verify_password(...)` (`core/security.py:30-31`) = `pwd_context.verify(...)` فقط.
- الكتابة الوحيدة بعد نجاح الدخول: `identity/service.py:113` `user_repo.update(..., last_login_at, last_login_ip, last_login_user_agent)` — **لا تلمس `hashed_password`**.
- الأماكن التي تكتب `users.hashed_password` فعليًا: التسجيل (`identity/service.py:78, 83`)، تغيير كلمة المرور (`service.py:271-272`)، إنشاء حساب النظام (`core/system_account_service.py:35`)، وسكربت `scripts/create_superuser.py` عند الإنشاء فقط.
- ملاحظة: `CryptContext(schemes=["bcrypt"], deprecated="auto")` (`security.py:23`) لا يحوي مخططات قديمة، فحتى لو استُدعي `verify_and_update` مستقبلًا لن يُعيد التجزئة إلا عند تغيير rounds.
- **إذًا `users.hashed_password` لا يتغير عند الدخول** — يتغير فقط عند التسجيل/تغيير كلمة المرور.

---
---

# الجزء الثاني — التنفيذ (Implementation) — الخيار (B)

**التاريخ:** 2026-09-22 · **الحالة الآن: الخطوة 1 (تشخيص + خطة) — لم يُعدَّل أي كود بعد. أُنشئ هذا القسم قبل أي كود كما طُلب.**
**قواعد الجلسة:** لا staging/commit، لا `PROGRESS_LOG.md`. الخطوة 2 (التنفيذ + التحقق الحي) **لا تبدأ إلا بموافقتك الصريحة**.
**فحوص قراءة فقط أُجريت في هذه الخطوة:** قراءة الكود، و`SELECT` واحد داخل `SET TRANSACTION READ ONLY` (سكربت في scratchpad خارج المشروع).

## 1) القرارات المعتمدة (من المراجع بتفويض المالك)
| # | القرار |
|---|---|
| D1 | تفويض = `system_role ∈ {SUPER_ADMIN, EXECUTIVE_DIRECTOR}` **و** `current_user.tenant_id == settings.PLATFORM_TENANT_ID` (جديد، افتراضي 1، إلزامي صراحةً في الإنتاج بنفس نمط `PUBLIC_REGISTRATION_TENANT_ID`). لا enum جديد، لا migration. غير ذلك 403، مجهول 401. |
| D2 | فشل قراءة Redis = **fail-OPEN + سجل ERROR** (بلا `except:` عارية). المفتاح **بلا TTL**. Backlog فقط: تخزين دائم (DB) لحالة المفتاح لمرحلة الـswarm. |
| D3 | البوابة عند أدنى نقاط الـLLM: `AIEngine.generate` + مسار Gemini في `core/ai_engine.py` + فحص مبكر واضح في `AIAgentsService.execute_agent_action`. لا مساس بـ`check_and_consume`. **استثناء مخصص واحد** → HTTP 503 بكود `AI_SYSTEM_SUSPENDED`. |
| D4 | `GET status` بنفس التفويض: الحالة + من/متى (إن وُجد) + هل Redis متاح. |
| D5 | body schema + `response_model` بدل query param، `admin/__init__.py`، وحدث تدقيق `AI_KILL_SWITCH_TOGGLED` (user_id، tenant_id، الحالة السابقة والجديدة). |

## 2) نتائج التشخيص الإضافي المؤثرة على التصميم

**(أ) الاستثناء يُحوَّل تلقائيًا إلى 503 نظيف بلا كود جديد للمعالجة:** `main.py:109-114` معالج عام لـ`SovereignError` يُرجع `{"detail": exc.message, "code": exc.code}` بـ`status_code` الاستثناء. فأي `class X(SovereignError)` بـ`status_code=503, code="AI_SYSTEM_SUSPENDED"` (نفس نمط `AIProviderError` في `errors.py:103`) يعمل فورًا. (READ-ONLY)

**(ب) مكان البوابة داخل `AIEngine.generate` حرج:** الدالة فيها `try/except Exception` يلتقط أي خطأ ويعيد المحاولة بنموذج بديل ثم يرمي `Exception` عاديًا (→ 500). **لذلك يجب أن تكون البوابة أول سطر في الدالة قبل `route_request` وخارج الـtry** وإلا تُبتلع وتتحول إلى 500. (READ-ONLY، `engine.py:59-195`)

**(ج) `core/ai_engine.py::analyze_and_recommend_courses` = كود ميت عمليًا:** مستورَدة في `academy/service.py:20` ولا تُستدعى من أي مكان (grep). ولها `except Exception: return []` داخلية، فالبوابة تُوضع **قبل** الـtry وقبل فحص `AI_API_KEY`. لا يمكن اختبارها حيًا عبر HTTP (لا مستدعٍ) — اختبار وحدة فقط. (VERIFIED grep)

**(د) `execute_agent_action`:** فيها `except Exception` (سطر 209) تُنشئ صف `ai_task_logs` بنوع `ERROR` وتعمل `commit` ثم `raise` (نفس النوع). لذلك البوابة المبكرة **قبل** `_validate_idempotency` (سطر 155) تمنع صفًا جديدًا في الحالة العادية. في نافذة السباق (الـswitch انقلب بين البوابتين، أجزاء من الثانية) يُنشأ صف `ERROR` صادق ويُرمى نفس الاستثناء → يبقى 503. **قررت عدم إضافة `rollback` هناك** (يُنهي صلاحية كائنات الـORM لدى المستدعين — نمط الـidentity-map المعروف في الجلسات السابقة). مقبول ومُوثَّق.

**(هـ) الكتابة تختلف عن القراءة:** D2 (fail-open) للقراءة فقط. **إذا فشل Redis عند التبديل (write) يجب أن يرى المشغّل الفشل** — أقترح 503 بكود `KILL_SWITCH_STORE_UNAVAILABLE` (`SovereignError(...)` مباشرة بلا class جديد) + سجل ERROR. غير ذلك يظن أن المفتاح فُعِّل وهو لم يُفعَّل.

**(و) `who/when` غير مخزَّنين اليوم** (القيمة `json.dumps(bool)` فقط). لتلبية D4 أقترح تخزين JSON: `{"suspended": bool, "changed_by_user_id": int, "changed_by_tenant_id": int, "changed_at": iso}` بلا TTL. القارئ يقبل الصيغة القديمة (`true`/`false`) للتوافق. المفتاح غير موجود اليوم فلا هجرة.

**(ز) وقت الاستجابة عند سقوط Redis:** `redis_client.get` عبر `Retry(ExponentialBackoff, retries=3)` وتهيئة الاتصال قد تأخذ عدة ثوانٍ قبل أن ينجح fail-open → **كل استدعاء AI يتأخر أثناء انقطاع Redis**. مقبول ضمن D2 لكن يُسجَّل كملاحظة.

**(ح) الحصة تُستهلك قبل رفض البوابة:** في الدومينات ذات `check_and_consume` (insurance، arbitration، command، invitations، logistics، manufacturing، realestate، social، tourism، zamakana …) الاستهلاك (يعمل `commit`) يسبق `execute_agent_action`. أثناء الإيقاف يُحتسب استهلاك حصة/سجل استخدام لاستدعاء رُفض لاحقًا. D3 يمنع لمس `check_and_consume` ← **Backlog (لم يُصلَح)**.

**(ط) بيانات الاختبار الحي (VERIFIED, ran, SELECT فقط):** الوكيل الوحيد `id=216` (tenant 1، ACTIVE، `requires_human_approval=True`، owner 772) · tenant 1: 25 SUPER_ADMIN فعّال + 96 USER فعّال · tenant 16: المستخدم `774` (SUPER_ADMIN فعّال) · `agent_approval_queue`=0 صف · 259 جدولًا. ⇒ **كل الحسابات المطلوبة موجودة** (لا حاجة لحساب `p_ks_*` مؤقت، مع إبقائه كخطة بديلة فقط).

## 3) (b) — ماذا يحدث عند رمي `AISystemSuspendedError` في **كل** مستدعٍ (21 موضع `execute_agent_action` + `AIEngine.generate` ×2 + Gemini ×0)

**قاعدة عامة:** جميع الاستدعاءات داخل HTTP (لا Celery) عدا واحد. لا يوجد أي مستدعٍ ينتج **500 غير معالَج** ولا **retry storm**. الأنماط:

| المجموعة | المستدعون | السلوك اليوم عند أي فشل AI ← عند الإيقاف | المقترح |
|---|---|---|---|
| **A — يمر → 503 نظيف** | `ai_agents/router.py:94` (`POST /agents/{id}/execute`)، `invitations/service.py:396` (`chat_with_ai`، بلا try، الراوتر `:614-630` بلا try)، `main.py:368` (`/api/ai/chat`) | الاستثناء يصل لمعالج `SovereignError` → 503 + `AI_SYSTEM_SUSPENDED` | **لا تغيير** |
| **A′ — يُحوَّل لحالة خطأ صريحة** | `automation/service.py:707` (`except Exception → {"status":"EXECUTION_ERROR","error":…}`) | خطوة الـworkflow تُسجَّل فاشلة بنص الخطأ (لا 500، لا صمت) | **لا تغيير** (اختياري: حالة `AI_SUSPENDED` مخصصة — لم أقترحه) |
| **B — AI استشاري، يُبتلع ويكمل بلا AI (سلوك مقصود)** | `arbitration:104`، `insurance:385, 493`، `tenders:247, 397`، `tourism:328` (VIP transport)، `manufacturing:311` (batch)، `transport:268`، `realestate:366`، `command:354` (يرجع `[]`)، `employment:143` (يرجع 50)، `invitations:86` (`_analyze_target_user` قيم افتراضية) | يُسجَّل WARNING/ERROR "AI … failed" ثم يكمل العمل الأساسي بلا نتيجة AI. **لا شيء منها يعيد استدعاء AI** | **لا تغيير**؛ البوابة نفسها تسجّل سطر WARNING واضحًا (`AI call refused: system suspended [context=…]`) عند المصدر فلا يبقى الحدث صامتًا |
| **C — الفولباك يُنتج بيانات مُختلَقة تُعرَض/تُخزَّن كأنها ناتج AI** ⚠️ | `social/service.py:355` (`random.randint(100,999)` كـ`suggested_user_id` مع نسب تطابق عشوائية!)، `logistics/service.py:584` (طلب متوقع 100/ثقة 50 يُخزَّن كتوقع)، `manufacturing/service.py:683` (احتمال عطل 0.65 ثابت يُخزَّن `create_predictive_log`)، `zamakana/service.py:537` (تقرير "تعذر التحليل" **ثم تُصدَر فاتورة تحليل**) | اليوم يحدث عند أي فشل نادر؛ **مع الـkill switch يصبح هو السلوك الدائم** طوال الإيقاف | **أضف `except AISystemSuspendedError: raise` قبل `except Exception`** (سطران + import لكل ملف) ← 503 نظيف بدل بيانات مزيّفة |
| **D — فحص أمان يُتخطى بصمت** | `tourism_sports/service.py:504` (فحص طبي: `medical_flag` يبقى False) | نفس اليوم عند أي فشل (وعمليًا اليوم المحرك محاكاة ولا يرجع `flag` أصلًا) | **لا تغيير + Backlog** (قرار E3 أدناه) |
| **E — Celery** | `tasks/agritech.py:168` داخل `_analyze_high_priority` (المهمة `process_soil_reading_high`: `max_retries=3`) | `except Exception` (سطر 200) يلتقط ويطبّق **فولباك حتمي بقاعدة** (رطوبة<30 → حدث ري عاجل) ويرجع ولا يصعد للمهمة ⇒ **لا retry** (الـretry يقع فقط لو خرج استثناء من `_process_soil_reading`). لكنه يُسجَّل "AI analysis failed" بلا تمييز | **تمييز صريح:** لو `AISystemSuspendedError` → `logger.warning("AI suspended (kill switch): skipping AI analysis for reading %s; rule-based fallback only")` ثم نفس الفولباك الحتمي (لا يستدعي AI، وإسقاط تنبيه ري عاجل يضر فعليًا). ~4 أسطر. (قرار E2) |

**ملاحظة `billing.py`:** `tasks/billing.py` يستخدم `AIAgentsService.generate_monthly_invoice` (فوترة، لا تنفيذ AI) ← غير مُبوَّب ولا متأثر.

**استثناء الاختبار:** مسار Gemini (`analyze_and_recommend_courses`) بلا مستدعٍ ← لا أثر على أحد، والبوابة دفاعية للمستقبل.

## 4) (a) الـdiff المقترح بالتفصيل (لم يُطبَّق)

### ملفات جديدة (3)
1. `app/domains/admin/__init__.py` — فارغ.
2. `app/domains/admin/schemas.py` (~28 سطر):
```python
class AIKillSwitchToggle(BaseModel):        # body
    suspend: bool
class AIKillSwitchStatus(BaseModel):        # GET + أساس استجابة POST
    suspended: Optional[bool]               # None = غير معروف (Redis غير متاح → البوابة تعمل fail-open)
    redis_reachable: bool
    changed_by_user_id: Optional[int] = None
    changed_by_tenant_id: Optional[int] = None
    changed_at: Optional[datetime] = None
class AIKillSwitchToggleResponse(AIKillSwitchStatus):
    previous_suspended: Optional[bool]
    message: str
```
3. `tests/test_ai_kill_switch_implementation.py` (~200 سطر، انظر §5).

### ملفات موجودة (14) — الأسطر تقديرية
| الملف | التغيير | ± |
|---|---|---|
| `core/errors.py` (بعد سطر 105) | `class AISystemSuspendedError(SovereignError)`: رسالة عربية، `status_code=503`, `code="AI_SYSTEM_SUSPENDED"` | +7 |
| `core/config.py` (بعد 169، 279، 309) | حقل `PLATFORM_TENANT_ID: int = Field(default=1, …)`؛ فحص الإنتاج `os.getenv("PLATFORM_TENANT_ID") is None → ValueError`؛ تحذير التطوير | +17 |
| `core/features.py` (إعادة كتابة 33→~95) | مفتاح بلا TTL؛ `read_state()` (يلتقط `RedisError/OSError/asyncio.TimeoutError` فقط، ERROR + `exc_info`، وقيمة تالفة → ERROR + fail-open)؛ `get_system_suspended()->bool` (يحافظ على التوقيع)؛ `set_system_suspended(status, by_user_id, by_tenant_id)->previous` (يكتب JSON بـ`set` بلا `ex`، وعند فشل Redis → `SovereignError(503, "KILL_SWITCH_STORE_UNAVAILABLE")`)؛ `ensure_ai_available(context)` (يسجّل WARNING ويرمي الاستثناء) | ±62 |
| `core/security.py` (بعد سطر 215) | `get_current_platform_superuser(current_user=Depends(get_current_superuser))`: `tenant_id != settings.PLATFORM_TENANT_ID` → WARNING + `PermissionDeniedError` | +14 |
| `domains/admin/router.py` (إعادة كتابة 24→~70) | `POST /toggle-ai-agents` (body + `response_model` + `Depends(get_current_platform_superuser)` + `audit_log("AI_KILL_SWITCH_TOGGLED", user_id, tenant_id, details={previous_suspended,new_suspended})`) و`GET /ai-agents-status`. الاسم `admin_router` يبقى (يُستورد كما هو) | ±46 |
| `main.py` | `from app.domains.admin.router import admin_router` + tuple في `routers_config` (المسار النهائي `/api/admin/system/toggle-ai-agents` و`/api/admin/system/ai-agents-status`) | +2 |
| `services/ai/engine.py` | import + `await ensure_ai_available("ai_engine.generate")` كأول سطر بعد الـdocstring (قبل `route_request`، خارج الـtry) | +2 |
| `core/ai_engine.py` | import + `await ensure_ai_available("gemini.recommend_courses")` في أول الدالة (قبل فحص المفتاح والـtry) | +2 |
| `ai_agents/service.py` | import + بوابة مبكرة قبل `_validate_idempotency` في `execute_agent_action` | +3 |
| `tasks/agritech.py` | تمييز `AISystemSuspendedError` في `except` + سطر log (E) | +5 |
| `social/service.py`، `logistics/service.py`، `manufacturing/service.py` (موضع الصيانة فقط)، `zamakana/service.py` | `except AISystemSuspendedError: raise` + import (C) | +3 لكل ملف = +12 |

**الإجمالي:** منطق ≈ 165 سطرًا (منها ~95 إعادة كتابة `features.py`+`router.py`) + ~200 سطر اختبار. **لا migration، لا تغيير schema، لا مساس بـ`check_and_consume` ولا بـ`AIGovernance*`.**

**تنبيه إجرائي:** `config.py`، `security.py`، `main.py`، `ai_agents/service.py`، `manufacturing/service.py`، `social/service.py`، `zamakana/service.py`، `logistics/service.py` (وغيرها) عليها **تعديلات غير مُثبَّتة من جلسات سابقة** (`git status` = M). تعديلاتي ستُضاف فوقها؛ عند الـcommit لاحقًا يلزم تحديد hunks هذه الجلسة تحديدًا (قاعدة `git commit -- <pathspec>` + مراجعة `--stat`). لن أُثبّت شيئًا.

### قرارات صغيرة أطلب اعتمادها ضمن الموافقة
- **E1 (نطاق المستدعين):** اعتماد مجموعة C (4 ملفات) + E (agritech) كما في §3؟ البديل الأدنى: بلا مساس بالمستدعين (9 ملفات فقط)، لكن حينها يصبح الفولباك المزيّف في social/logistics/manufacturing/zamakana هو السلوك الطبيعي طوال الإيقاف. **توصيتي: اعتمادها.**
- **E2 (agritech):** إبقاء الفولباك الحتمي (تنبيه الري) مع log صريح، أم تخطي المهمة كليًا؟ **توصيتي: الإبقاء.**
- **E3 (tourism الفحص الطبي):** ترك كما هو + Backlog (توصيتي) أم رمي 503 وحجب تحويلات اللاعبين أثناء الإيقاف؟
- **E4 (مسارات الـURL):** `POST /api/admin/system/toggle-ai-agents` (يبقى) و`GET /api/admin/system/ai-agents-status` (جديد) — موافق؟

## 5) (c) خطة الاختبارات — `tests/test_ai_kill_switch_implementation.py`
**اتفاقية المشروع:** DB/Redis حقيقيان بلا mock (فيكستشر `db` في `conftest.py`)؛ الاستثناء الوحيد المسموح هنا: تعطيل `_call_model`/الاستدعاءات الخارجية عند اختبار "يمر بعد الاستئناف". **حماية:** الاختبارات تستبدل `features.SYSTEM_SUSPENDED_KEY` بمفتاح اختباري `test:kill_switch:<uuid>` (`monkeypatch`) وتحذفه في teardown — لا تلمس المفتاح الحقيقي.
1. **التسجيل/التبعية بلا سيرفر** (نمط `test_ai_routing_security.py` + `route_utils`): المساران موجودان؛ `get_current_platform_superuser` ضمن التبعيات المباشرة، و`get_current_user` ليس.
2. **مصفوفة التفويض عبر `httpx.ASGITransport(fastapi_app)` بلا lifespan/سيرفر:** مجهول → 401؛ `USER` → 403؛ SUPER_ADMIN بـ`tenant_id=16` → 403 **ولا تتغير الحالة**؛ SUPER_ADMIN بـ`tenant_id=1` → 200 (باستخدام `dependency_overrides[get_current_user]`).
3. **البوابة:** ON → `AIEngine.generate` يرمي `AISystemSuspendedError` **قبل** `route_request` (نمرّر `route_request` يفشل لو استُدعي)؛ `execute_agent_action` يرمي قبل أي قراءة repo؛ `analyze_and_recommend_courses` يرمي. OFF → يمر (بمحاكاة `_call_model`).
4. **الـ503:** `POST /api/ai/chat` مع ON عبر ASGI → `503` و`code == "AI_SYSTEM_SUSPENDED"`.
5. **بلا TTL:** بعد التبديل `ttl(key) == -1`.
6. **التدقيق:** التقاط لوغر `eppne.audit` (caplog): حدث `AI_KILL_SWITCH_TOGGLED` لـON ثم OFF بـ`user_id/tenant_id/previous/new` صحيحة.
7. **Redis معطَّل (monkeypatch على `redis_client.get/set`):** القراءة → `False` + سجل ERROR (تحقق من نص/مستوى السجل)؛ الكتابة → 503 `KILL_SWITCH_STORE_UNAVAILABLE`؛ `GET status` → `redis_reachable=False`، `suspended=None`.
8. **توافق الصيغ:** قيمة قديمة `"true"/"false"` تُقرأ صحيحًا؛ قيمة تالفة → fail-open + ERROR.
9. **المستدعون المعدَّلون:** agritech (`_analyze_high_priority` مع استثناء الإيقاف ← فولباك حتمي + سطر log، ولا يرمي)؛ social matchmaking ← يعيد رفع الاستثناء (وحدة، بمحاكاة `execute_agent_action`). **logistics/manufacturing/zamakana:** تحتاج بيانات إعداد ثقيلة — أقترح التحقق منها بمراجعة الكود + `py_compile` + اختبار وحدة إن أمكن دون إنشاء بيانات؛ **سأصرّح بأي فجوة تغطية بوضوح** بدل ادعاء تغطية.
10. **الإعداد:** `PLATFORM_TENANT_ID` افتراضيًا 1؛ في `production` بلا متغير بيئة → `ValueError` (اختبار منطق الفحص بعزل الـenv).
**لن تُشغَّل الاختبارات قبل موافقتك.** وستُقاس بعدها: مجموعة الاختبارات ذات الصلة (`test_ai_*`, `test_identity_router_protection`, `test_guardian*`) كخط أساس مقارن بحثًا عن انحدار.

## 6) (d) خطة التحقق الحي (الخطوة 2، بعد الموافقة) — مُكيَّفة لما هو موجود
**الحواجز (نفس السابق):** `DATABASE_URL` يُحلَّل إلى `127.0.0.1:5435/eppne_v2` مع abort لو اختلف (بلا طباعة بيانات الاعتماد)؛ `REDIS_URL=127.0.0.1:6380/0`؛ `uvicorn --host 127.0.0.1 --port 8010` بلا `--reload`؛ **بلا celery**؛ السجل في scratchpad خارج الريبو؛ فحص الأسرار على كل المخرجات؛ إيقاف السيرفر في النهاية؛ `pg_indexes` (count + hash) قبل/بعد؛ لقطة كل الجداول الـ259 (عدد + max id) + بصمات الصفوف المحمية (`users` 774 وغيره، `ai_agents` 216).
**الحسابات:** بلا كلمات مرور — **توكنات JWT تُصكّ وقت التشغيل** بـ`create_access_token` للمستخدمين الموجودين (قراءة `session_version` من DB): SUPER_ADMIN فعّال بأقل id في tenant 1، USER فعّال في tenant 1، والمستخدم `774` (SUPER_ADMIN، tenant 16). لا تُطبع ولا تُخزَّن ⇒ **لا صفوف `auth_refresh_tokens`**. (البديل `p_ks_*` غير لازم لأن الحسابات موجودة.)
**قبل أي شيء:** تسجيل حالة مفتاح الـkill switch وTTL (المتوقع: غائب) + **لقطة Redis كاملة** (SCAN: نوع/TTL لكل مفتاح، ومحتوى الـhashes الخاصة بـ`CostTracker`) — لأن `/api/ai/chat` و`execute` يكتبان مفاتيح Redis (cost tracker/idempotency/rate-limit/semantic cache) خارج لقطة DB؛ سأستعمل `use_cache=false` وأسجّل الفروق لاستعادتها.

**المرحلة 0 — خط الأساس للثغرة (على الكود الحالي، قبل تطبيق الـdiff):** (1) `POST /api/ai/chat` (مجهول) ← 200 بنص "(محاكاة)". (2) `POST /api/ai-agents/agents/216/execute` (USER من tenant 1) ← ينجح ويُنشئ صف `ai_task_logs` + صف `agent_approval_queue` (يُسجَّلان بالـid). (3) **إثبات "لا أحد يقرأ المفتاح":** أكتب المفتاح يدويًا في Redis بقيمة `true` ثم أكرّر (1) و(2) ← **يعملان كأن شيئًا لم يكن**؛ ثم أحذف المفتاح. (4) `POST /api/admin/system/toggle-ai-agents` ← 404 (غير مسجَّل).
**المرحلة 1 — بعد تطبيق الـdiff (إعادة تشغيل السيرفر):** بحسب طلبك:
1. مجهول → 401. 2. USER عادي → 403. 3. SUPER_ADMIN من tenant 16 (`774`) → 403 **وحالة المفتاح لم تتغير**. 4. superuser المنصة (tenant 1) يفعّل ON → 200، `GET status` = ON مع `changed_by_*`، **`TTL` للمفتاح = -1**. 5. أثناء ON: `/api/ai/chat` → 503 + `AI_SYSTEM_SUSPENDED`؛ و`POST /agents/216/execute` → 503 **بلا أي صف جديد في `ai_task_logs`/`agent_approval_queue`** (عدّ قبل/بعد). 6. OFF → `/api/ai/chat` يعمل (محاكاة) والحالة OFF. 7. حدثا التدقيق (ON وOFF) من السجل (سأتحقق أولًا هل يصل لوغر `eppne.audit` إلى مخرجات uvicorn/ملف السجل؛ إن لم يصل أقرأه من معالج الملف الفعلي — و`audit_logs` الجدول لن يتغير بالتصميم، انظر S-3).
+ إضافات صغيرة: جسم غير صالح ← 422؛ استدعاء GET بـ tenant 16 ← 403.
**التنظيف:** حذف مفتاح الـkill switch فقط (وإعادة الحالة المسجَّلة)؛ حذف ما أنشأته فقط (صفوف `ai_task_logs`/`agent_approval_queue` بالـid المسجَّل، ومفاتيح Redis الجديدة، واستعادة قيم الـhashes المتغيّرة)؛ **سأعرض لك الأوامر قبل تنفيذها**؛ ثم لقطة صفرية الفرق على كل الجداول (بما فيها `ai_task_logs`) + بصمات الصفوف المحمية + `pg_indexes` + إيقاف السيرفر والتأكد أن المنفذ 8010 حر.

## 7) بنود Backlog (تُسجَّل فقط — لن تُصلَح في هذه الجلسة)
1. **"LLM activation gate" checklist** — قبل تفعيل استدعاء LLM حقيقي: (أ) الـkill switch (هذه الجلسة) (ب) `POST /api/ai/chat` بلا مصادقة إلزامية (`get_current_user_optional`) (ج) `PUT /api/ai/routing` superuser-per-tenant (د) المحرك محاكاة + مفاتيح API وهمية (هـ) حالة المفتاح غير دائمة (DB).
2. **تخزين دائم (DB) لحالة الـkill switch** لمرحلة الـswarm — Redis flush يعيدها "يعمل".
3. **مراجعة الـ25 حساب SUPER_ADMIN في tenant 1** (كلهم قادرون على تفعيل المفتاح بعد D1 — لأن الشرط هو الـtenant لا حساب بعينه).
4. **حساب EXECUTIVE_DIRECTOR غير موجود في DB** (0 صف رغم `scripts/create_superuser.py`).
5. **(جديد) استهلاك الحصة قبل رفض البوابة** (§2-ح).
6. **(جديد) فولباكات مختلَقة أخرى في المجموعة B/D** (employment=50 يُخزَّن كدرجة، فحص tourism الطبي يُتخطى، insurance/tenders استشارية) — تحتاج قرار منتج: هل تفشل أم تكمل؟
7. **(جديد) بطء ذيلي للبوابة أثناء انقطاع Redis** (§2-ز).
8. **(جديد) `analyze_and_recommend_courses` كود ميت** (مستورد ولا يُستدعى).

**(الحالة وقت الخطوة 1: توقّف بانتظار الموافقة — اعتُمدت E1/E2/E4 وE3 = Backlog عالي الأولوية. ما يلي هو الخطوة 2.)**

---
---

# الجزء الثالث — نتائج التنفيذ والتحقق الحي (الخطوة 2) — **متوقّف قبل التنظيف بانتظار موافقتك**

**التاريخ:** 2026-09-22 · لا staging/commit · لا `PROGRESS_LOG.md`.

## 0) شرطا الموافقة + تصحيحات لخطة الخطوة 1
- **الشرط 1 (حفظ `git diff HEAD` قبل أي تعديل):** ✅ محفوظ في scratchpad (`prediff/*.diff`) لكل ملف موجود مسّته الجلسة. **تصحيح:** في الخطوة 1 قلت إن ~8 ملفات عليها تعديلات غير مُثبَّتة؛ الفحص الفعلي (`git status`/`git diff HEAD`) أثبت **4 فقط**: `core/config.py` (17 سطر diff)، `core/security.py` (68)، `main.py` (20)، `domains/logistics/service.py` (52). الباقي (`ai_agents/service.py`، `social`، `manufacturing`، `zamakana`، `errors.py`، `features.py`، `engine.py`، `core/ai_engine.py`، `tasks/agritech.py`، `admin/router.py`) **نظيفة** قبل الجلسة. بعد التعديل قارنتُ diff كل ملف من الأربعة بنسخته المحفوظة: **الفرق = هنكات هذه الجلسة فقط، ولا سطر سابق اختفى أو تغيّر** (للتقسيم اللاحق عند الـcommit).
- **الشرط 2 (مجموعة C = الحارس + الاستيراد فقط):** ✅ التزمتُ حرفيًا. لكل من `social`/`logistics`/`manufacturing`/`zamakana`: تعديل سطر الاستيراد الموجود (إضافة `AISystemSuspendedError`) + سطران `except AISystemSuspendedError: raise` — لا غير (`git diff --stat` للثلاثة النظيفة: 4 أسطر لكل ملف؛ ولـlogistics فرق الهنكات المقارَن = هذه الأسطر الثلاثة فقط). لم أحتج لمس أي شيء آخر فيها.
- **تعليق `PLATFORM_TENANT_ID`:** ✅ في `config.py` (قسم 6c) — ينص أنه مفهوميًا منفصل عن `PUBLIC_REGISTRATION_TENANT_ID` وأن تساويهما = 1 اليوم صدفة.
- **تصحيح مسار (خطأ في خطة الخطوة 1):** مسار تنفيذ الوكيل الفعلي هو **`POST /api/ai/agents/{id}/execute`** (البادئة `/ai` في `ai_agents/router.py:21`) وليس `/api/ai-agents/...` كما كتبتُ. صُحّح في التنفيذ.

## 1) ما نُفِّذ (مجمَّع كما طُلب)
| الخطوة | الملفات |
|---|---|
| 1 ملفات جديدة | `admin/__init__.py` (فارغ)، `admin/schemas.py` (3 نماذج)، `tests/test_ai_kill_switch_implementation.py` (18 اختبارًا) |
| 2 | `core/errors.py` (+6: `AISystemSuspendedError` → 503 `AI_SYSTEM_SUSPENDED`)، `core/config.py` (+38: `PLATFORM_TENANT_ID` + إلزام الإنتاج + تحذير التطوير + التعليق المطلوب) |
| 3 | `core/features.py` (إعادة كتابة: بلا TTL، JSON مع من/متى، قراءة fail-open مع ERROR بلا `except:` عارية، كتابة تفشل صراحةً بـ503 `KILL_SWITCH_STORE_UNAVAILABLE`، `ensure_ai_available`) |
| 4 | `core/security.py` (+`get_current_platform_superuser` بتحذير عند الرفض) |
| 5 | `admin/router.py` (POST body+`response_model`+تدقيق `AI_KILL_SWITCH_TOGGLED`، GET status) + `main.py` (+2) |
| 6 | `services/ai/engine.py` (بوابة أول سطر خارج try)، `core/ai_engine.py` (بوابة قبل المفتاح والـtry)، `ai_agents/service.py` (بوابة مبكرة قبل idempotency) |
| 7 | `social`، `logistics`، `manufacturing` (موضع الصيانة فقط)، `zamakana` (الحارس فقط)، `tasks/agritech.py` (تمييز الإيقاف بسطر log صريح مع الإبقاء على فولباك الري الحتمي) |
`py_compile` ✅ لكل الملفات. ملفات `features.py`/`router.py`/`schemas.py` حُوِّلت إلى CRLF لتطابق باقي المشروع (تحذير LF→CRLF من git زال).

## 2) الاختبارات (`tests/test_ai_kill_switch_implementation.py`) — **18 passed**
تغطي: التسجيل والتبعية بلا سيرفر؛ بوابة التينانت (+ ربطها بالإعداد)؛ **الإلزام الصريح في الإنتاج** (`ValueError` بلا env، ونجاح مع env)؛ مصفوفة 401/403/422 عبر ASGI (مجهول، USER، ADMIN، SUPER_ADMIN tenant 16 ← الحالة لا تتغير، EXECUTIVE_DIRECTOR المنصة مسموح، query-param القديم مرفوض)؛ ON/OFF مع **TTL=-1** ومن/متى وحدثَي التدقيق (المحتوى مقارَن)؛ البوابات الثلاث (المحرك يُحجب **قبل** `route_request`، Gemini، `execute_agent_action` قبل أي repo وبلا تغيير في `ai_task_logs`) ويمر بعد الاستئناف؛ الـ503 النظيف على `/api/ai/chat` و`/api/ai/agents/{id}/execute`؛ **Redis معطَّل**: قراءة → fail-open + سجل ERROR ("failing OPEN")، كتابة → 503 `KILL_SWITCH_STORE_UNAVAILABLE` بلا مفتاح، `status` → `suspended=None`؛ الصيغة القديمة والقيم التالفة؛ **المستدعون**: social/logistics/manufacturing/zamakana يعيدون رفع الإيقاف **وبالمقابل** خطأ آخر (`RuntimeError`) يبقى على فولباكه القديم (اختبار تحكم يثبت عدم تغيير السلوك الآخر، ومنه: zamakana لا تصدر فاتورة عند الإيقاف)، وagritech لا يرمي (⇒ لا retry) ويسجّل سطر "AI suspended (kill switch)" لا "AI analysis failed".
**فجوة صريحة:** المستدعون الاختباريون استُخدمت فيهم `monkeypatch` لعزل الحوكمة/الـrepo (لا بيانات إعداد حقيقية)؛ لم أختبر عبر HTTP حقيقي لهذه الدومينات الأربعة (ولا داعي: ثبتت البوابة الأدنى عبر `/api/ai/*`).
**الانحدار:** لم أشغّل بعد مجموعات الاختبار الحية الأخرى (تكتب في DB الحقيقية فتلوّث لقطة الفرق الصفري) — **أقترح تشغيلها بعد التنظيف** (انظر §5).

## 3) التحقق الحي (127.0.0.1:8010، بلا celery، الحواجز كما خُطِّط)
**الحواجز:** `DATABASE_URL`→`127.0.0.1:5435/eppne_v2` و`REDIS_URL`→`127.0.0.1:6380/0` مُتحقَّق منهما (guard يُجهض إن اختلفا، بلا طباعة بيانات الاعتماد)؛ `ENVIRONMENT=development`؛ السيرفر بلا `--reload`؛ السجلات في scratchpad (وحتى `LOG_FILE` وُجِّه هناك ليتفادى كتابة `app.log` داخل الريبو)؛ لا عمليات python/uvicorn/celery قبل البدء والمنفذ 8010 حر.
**الحسابات:** JWT مصكوكة وقت التشغيل من مستخدمين موجودين (لا كلمات مرور، لا `auth_refresh_tokens`): superuser المنصة `id=41` (tenant 1)، USER `id=1` (tenant 1)، SUPER_ADMIN `id=774` (tenant 16). لا حاجة لحساب `p_ks_*`. لا تعديل لأي مستخدم.
**حالة المفتاح قبل كل شيء:** غائب (`TTL=-2`) ✅ (لقطة `s0`: 259 جدولًا، 1877 فهرسًا `sha256_16=a3f0a5026ac93ab7`، 25 مفتاح Redis).

### المرحلة 0 — خط الأساس (الكود قبل الـdiff)
- **اكتشاف جانبي مهم:** `POST /api/ai/chat` بجسم افتراضي يرجع **500 دائمًا** (`ValueError: 'arabic_chat' is not a valid TaskType` — الافتراضي `"arabic_chat"` بحروف صغيرة والـenum `ARABIC_CHAT`). خطأ قائم منذ قبل الجلسة؛ **لم يُصلَح** (Backlog). استخدمتُ `task_type="ARABIC_CHAT"` صراحةً.
- المفتاح غائب: `/api/ai/chat` (مجهول) ← **200** نص "(محاكاة)"؛ `execute` على الوكيل 216 ← **200 `PENDING_APPROVAL`** ويُنشئ `ai_task_logs`+`agent_approval_queue`.
- **المفتاح مكتوب يدويًا `true` (بلا TTL):** نفس النداءين ← **200/200 كأن شيئًا لم يكن** (صفّان جديدان أيضًا) ⇒ **أُثبت أنه لا أحد يقرأ المفتاح** قبل البوابة.
- `POST /api/admin/system/toggle-ai-agents` ← **404** (غير مسجَّل). ثم حُذف المفتاح اليدوي.

### المرحلة 1 — بعد الـdiff (إعادة تشغيل السيرفر)
| # | السيناريو | النتيجة |
|---|---|---|
| — | `openapi.json` | المساران مسجَّلان: `/api/admin/system/toggle-ai-agents` و`/api/admin/system/ai-agents-status` |
| 1 | مجهول POST/GET | **401** `Not authenticated` |
| 2 | USER (tenant 1) POST/GET | **403** `Superuser privileges required` |
| 3 | SUPER_ADMIN tenant 16 (`774`) POST/GET | **403** `Platform-level superuser privileges required`، **والمفتاح لا يزال غائبًا** (`exists=false`) |
| 3د/هـ | جسم غير صالح / query-param القديم | **422** (والمفتاح غائب) |
| 4 | superuser المنصة (`41`) ON | **200** `suspended=true`، `previous_suspended=false`، `changed_by_user_id=41`، `changed_by_tenant_id=1`، `changed_at` موجود؛ `GET status` = ON مع نفس من/متى؛ **`TTL = -1`** ✅ |
| 5 | أثناء ON: `/api/ai/chat` و`POST /api/ai/agents/216/execute` | **503** `{"code":"AI_SYSTEM_SUSPENDED"}` للاثنين؛ **`ai_task_logs`: 2→2 (max 673)، `agent_approval_queue`: 2→2 (max 557)** = **لا صف جديد** ✅ |
| 6 | OFF | **200** `suspended=false`، `previous_suspended=true`؛ `GET status` = OFF؛ المفتاح باقٍ بلا TTL؛ `/api/ai/chat` ← **200** (محاكاة) ✅ |
| 7 | التدقيق من السجل | حدثان `AI_KILL_SWITCH_TOGGLED`: ON `{"previous_suspended": false, "new_suspended": true}` وOFF `{"previous_suspended": true, "new_suspended": false}` بـ`user_id=41`, `tenant_id=1` ✅ (وصلا لمخرجات السيرفر وملف السجل معًا؛ جدول `audit_logs` لا يُكتب بالتصميم — S-3). + سطرا `AI call refused… [context=ai_engine.generate]` و`[context=ai_agents.execute_agent_action[agent=216]]`، وسطرا `Platform-level control denied: user=774 tenant=16` |
**فحص أسرار السجلات:** أنماط `eyJ` (JWT) = **0** في `server1.log`/`server1.err.log`/`server_app1.log`؛ لا أخطاء غير ضجيج إنشاء الفهارس المعروف (S-2).
**السيرفر أُوقف** (شجرة العمليات): المنفذ 8010 حر، صفر عمليات python/uvicorn.

## 4) لقطة الحالة قبل التنظيف (`s1` مقابل `s0`) — ما تركته الجلسة (يجب تنظيفه)
- **DB:** جدولان فقط تغيّرا من 259: `ai_task_logs` (0→2: ids **672, 673**، مفتاحا idempotency `KS-P0-f5b59478b0` / `KS-P0-dc9c17949f`، الوكيل 216، tenant 1) و`agent_approval_queue` (0→2: ids **556, 557**، `KS-P0-…-approval`). كلها من **المرحلة 0 (خط الأساس)** فقط. لا FKs تشير إليهما (فُحص).
- **الفهارس:** `pg_indexes` = 1877 قبل وبعد، **نفس hash `a3f0a5026ac93ab7`** (السيرفر أُقلع مرتين).
- **Redis:** 25→39 مفتاحًا: أُضيف 14 (المفتاح `system:ai_agents:suspended` بقيمته OFF، و6 مفاتيح `ai:cost:daily|monthly:*`، و`ai:prompt:*` ×1، و`ai:semantic:*` ×2، و`idem:`/`idempotent:` لمفتاحَي `KS-P0-*` ×4)، وتغيّرت قيم 3 hashes **كانت موجودة قبل الجلسة**: `ai:cost:{hunyuan-mt-7b|kimi-k2.6|mistral-saba}:total` (قيمها الأصلية محفوظة في `s0.json`).
- الباقي: **صفر تغيير** في بقية الجداول (مقارنة محتوى md5 كامل لكل جدول، لا عدد الصفوف فقط)، بما فيها `users` (كل الصفوف المحمية).

## 5) أوامر التنظيف المقترحة (**لم تُنفَّذ — بانتظار موافقتك**)
السكربت: `<scratchpad>\cleanup.py` (40 سطرًا). كل الحذف مشروط بـ`id` **و**`idempotency_key` معًا وبـ`assert rowcount == 1`:
```sql
DELETE FROM agent_approval_queue WHERE id=556 AND idempotency_key='KS-P0-f5b59478b0-approval';
DELETE FROM agent_approval_queue WHERE id=557 AND idempotency_key='KS-P0-dc9c17949f-approval';
DELETE FROM ai_task_logs         WHERE id=672 AND idempotency_key='KS-P0-f5b59478b0';
DELETE FROM ai_task_logs         WHERE id=673 AND idempotency_key='KS-P0-dc9c17949f';   -- ثم COMMIT
```
```
Redis DEL (14 مفتاحًا أُضيفت):
  system:ai_agents:suspended
  ai:cost:daily:{hunyuan-mt-7b,kimi-k2.6,mistral-saba}:2026-09-21
  ai:cost:monthly:{hunyuan-mt-7b,kimi-k2.6,mistral-saba}:2026-09
  ai:prompt:56c5b3ddfd090054beac7ee1279a26e7
  ai:semantic:65a9fb4443d54a16d687e90ea0f3e275 , ai:semantic:871d4cbb852ea62d525751194c843ea5
  idem:/api/ai/agents/216/execute:KS-P0-dc9c17949f , …:KS-P0-f5b59478b0
  idempotent:idempotency:1:KS-P0-dc9c17949f , …:KS-P0-f5b59478b0
Redis RESTORE (DEL + HSET بالقيم الأصلية من s0.json + EXPIRE بالـTTL المسجَّل):
  ai:cost:hunyuan-mt-7b:total  {input_tokens:4,  output_tokens:50,  total_cost:0}        ttl 107043
  ai:cost:kimi-k2.6:total      {input_tokens:0,  output_tokens:50,  total_cost:0.000175} ttl 514065
  ai:cost:mistral-saba:total   {input_tokens:15, output_tokens:150, total_cost:0.000093} ttl 108041
```
**ملاحظة صادقة:** استعادة TTL الـhashes الثلاثة ستكون قيمتها وقت اللقطة (ينقص منها بضع ثوانٍ/دقائق طبيعيًا لو لم أتدخل) — فرق لا يُقاس في مقارنة المحتوى ولا يؤثر وظيفيًا. **العدّاد التسلسلي (sequences)** لـ`ai_task_logs`/`agent_approval_queue` لن يُعاد (سيبقى التسلسل متقدّمًا: 672/673 و556/557 لن تُعاد)؛ هذا أثر لا مفر منه لأي INSERT+DELETE ولا يظهر في المقارنة.
**بعد التنظيف:** لقطة `s2` وفرق صفري مقابل `s0` (كل الجداول بمحتواها + `pg_indexes` + مفاتيح Redis + المفتاح غائب) + تأكيد عدم وجود عمليات والمنفذ حر. **ثم** (بموافقتك) أشغّل مجموعة الانحدار الحية (`test_ai_*`، `test_agritech*`، `test_identity_router_protection`، `test_invitations*`، `test_insurance*`، `test_realestate*`، `test_social*`، `test_tenders*`، `test_tourism*`، `test_transport*`، `test_logistics*`، `test_redis_client_wrapper*`، `test_eventbus*` …) مع لقطة قبل/بعد لها أيضًا.

## 6) Backlog (تُسجَّل فقط — لم يُصلَح شيء منها)
| # | البند | الأولوية |
|---|---|---|
| **B-E3** | **فحص الطبي بالـAI في `tourism_sports/service.py:504` (`medical_flag`) يُتخطّى بصمت عند أي فشل AI — ومنه الإيقاف بالـKill Switch — فتمر تحويلات اللاعبين بلا فحص طبي.** (اليوم المحرك محاكاة ولا يُرجع `flag` أصلًا، فالفحص عمليًا بلا أثر؛ لكن الثغرة حقيقية وتصبح خطيرة عند تفعيل LLM حقيقي.) قرار منتج مطلوب: هل يفشل التحويل (503) أم يتحوّل لمراجعة بشرية إلزامية؟ | 🔴 **HIGH PRIORITY — سلامة طبية** (مستقل عن باقي الـbacklog) |
| B-1 | "LLM activation gate" checklist: Kill Switch ✅ (هذه الجلسة) · `/api/ai/chat` بلا مصادقة إلزامية · `PUT /api/ai/routing` superuser-لكل-tenant · المحرك محاكاة ومفاتيح وهمية · حالة المفتاح غير دائمة | قبل تفعيل LLM |
| B-2 | تخزين دائم (DB) لحالة الـkill switch لمرحلة الـswarm (Redis flush يعيدها "يعمل") | متوسط |
| B-3 | مراجعة الـ25 حساب SUPER_ADMIN في tenant 1 (كلهم قادرون على المفتاح: الشرط tenant لا حساب بعينه) | متوسط |
| B-4 | حساب EXECUTIVE_DIRECTOR غير موجود في DB (0 صف رغم `scripts/create_superuser.py`) | منخفض |
| B-5 | استهلاك الحصة (`check_and_consume`) يسبق رفض البوابة فيُحتسب استهلاك لاستدعاء مرفوض | متوسط |
| B-6 | فولباكات مختلَقة أخرى غير مغطاة: employment=50 يُخزَّن كدرجة، insurance/tenders/transport استشارية | منخفض–متوسط |
| B-7 | بطء ذيلي للبوابة أثناء انقطاع Redis (إعادة المحاولة الأسية قبل fail-open) | منخفض |
| B-8 | `analyze_and_recommend_courses` كود ميت (مستورد ولا يُستدعى) | منخفض |
| **B-9 (جديد)** | **`POST /api/ai/chat` بجسمه الافتراضي = 500 دائمًا** (`task_type` الافتراضي `"arabic_chat"` ≠ enum `ARABIC_CHAT`) | متوسط |
| B-10 (جديد) | نافذة سباق: لو انقلب المفتاح بين بوابتَي `execute_agent_action` والمحرك يُنشأ صف `ai_task_logs` بنوع ERROR صادق (رفضتُ إضافة `rollback` لتفادي انتهاء صلاحية كائنات الـORM لدى المستدعين) | منخفض |
| B-11 (جديد) | الـ`changed_at` بتوقيت UTC (`…Z`) بينما سجلات السيرفر بالتوقيت المحلي (UTC+3) — قد يربك مقارنة الأحداث | منخفض |

## 7) الحالة
**(الحالة وقت هذا القسم: متوقّف بانتظار الموافقة على §5 — اعتُمد التنظيف، والنتائج في الجزء الرابع.)**

---
---

# الجزء الرابع — التنظيف المعتمَد + مجموعة الانحدار + الحالة النهائية

**التاريخ:** 2026-09-22 · لا staging/commit · لا `PROGRESS_LOG.md`.

## 1) التنظيف المعتمَد (§5) — نُفِّذ بالشروط الثلاثة
1. **قبل التنفيذ:** `CLIENT LIST` على `127.0.0.1:6380`: اتصال واحد فقط = اتصال الفحص نفسه (لا جلسة أخرى)؛ صفر عمليات python/uvicorn/celery؛ المنفذ 8010 حر.
2. **التنفيذ كما اقتُرح:** حذف الصفوف الأربعة (2 `agent_approval_queue` + 2 `ai_task_logs`، شرط `id` **و**`idempotency_key`، `assert rowcount==1`، ثم COMMIT)؛ Redis: حذف 14 مفتاحًا مضافًا واستعادة الـhashes الثلاثة `ai:cost:*:total` بـDEL+HSET+EXPIRE بالقيم والـTTL المسجَّلة بالضبط.
3. **لقطة `s2` مقابل `s0`:** جداول 259 → **0 تغيّر** (مقارنة عدد + max id + md5 محتوى كامل)؛ `pg_indexes` 1877 وnفس hash `a3f0a5026ac93ab7`؛ مفاتيح Redis 25 → 25 بلا إضافة/حذف/تغيّر قيمة؛ مفتاح الـkill switch **غائب** (`TTL=-2`)؛ المنفذ 8010 حر وصفر عمليات. ✅

## 2) مجموعة الانحدار الحية — 32 ملفًا / 147 اختبارًا (بلقطة `s2` قبلها و`s3` بعدها)
الملفات: `test_ai_*` (تشمل الاختبارات الجديدة)، `test_agritech*`، `test_identity_router_protection`، `test_invitations*`، `test_insurance*`، `test_realestate*`، `test_social*`، `test_tenders*`، `test_tourism*`، `test_transport*`، `test_logistics*`، `test_redis_client_wrapper*`، `test_eventbus*`. المدة 1:04:51.
**النتيجة: 144 passed · 2 xfailed · 1 failed.**

### الفشل الوحيد: `test_realestate_insurance_savepoint.py::test_realestate_buy_fractional_ownership_invoice_ordering`
`AssertionError: create_invoice() لازم تكون مُغلَّفة بـtry/except — assert 1277 < 928`. **غير مرتبط بهذه الجلسة (تقدير مبني على أدلة، لا تشغيل على HEAD):**
- الاختبار حارس **بنيوي على نص المصدر** (`inspect.getsource` لـ`RealEstateService.buy_fractional_ownership`)، ولا يشغّل أي منطق من الملفات التي عدّلتُها.
- `realestate/service.py` **لم يُعدَّل** (`git status` نظيف لها، وليست بين ملفات هذه الجلسة) وآخر commit لها `b77b319`؛ وملف الاختبار نفسه غير معدَّل.
- سبب الفشل مقروء من الكود: الحارس يأخذ **أول** `try:` بعد `commit()`، وفي الدالة الآن كتلة `try/except` لاستدعاء `execute_agent_action` (سطر ~363-368) **تسبق** كتلة `create_invoice` (`except` الأولى عند 928 قبل موضع `create_invoice` عند 1277) — أي الحارس قديم مقابل بنية الكود الحالية (إضافة كتلة AI قبل الفاتورة)، لا انحدار من الـkill switch.
سجَّلتُه Backlog (B-12). لم يُصلَح.

## 3) ما تركته مجموعة الانحدار (لقطة `s3` مقابل `s2`) — وما تم بشأنه
| النوع | التفصيل | الإجراء |
|---|---|---|
| **Redis — 132 مفتاحًا مضافًا** (142 وقت اللقطة، انتهى 10 منها بـTTL) | `idempotent:REGTEST-*` (4)، `idempotent:idempotency:{1,15}:AI-*/REALESTATE-FRAC-*/REGTEST-*` (12)، و`user:{13587..13702}:{1,15,16}` (116 كاش مستخدمين أُنشئوا وحُذفوا أثناء الاختبارات). مطابقة regex صارمة لعلامات الاختبار قبل الحذف (`assert`) | ✅ **عُرضت قائمة dry-run ثم حُذفت (130 مفتاحًا وقت التنفيذ)** |
| **Redis — طابور `celery` (قائمة الـbroker)** | أُضيفت **رسالتان** `send_notification_task` (notification_id 912 لـuser 13580، و911 لـuser 13576 — إشعارات "شراء ملكية جزئية" من اختبارات realestate) على رأس القائمة، وأصلها `gen1756@…` = عملية pytest الخاصة بي. الباقي (931 رسالة) قديم من جلسات سابقة (أصول pids أخرى) | ✅ `LREM` للرسالتين فقط بنصهما الخام (بعد التحقق من الأصل والـid)؛ **hash قائمة `celery` بعد الحذف = hash `s0` تمامًا** |
| **DB — `wallets`** | **صفّان فقط تغيّرا** (العدد وmax id كما هما، محتوى md5 تغيّر): `wallets.id=41` (المستخدم `43` = `p_ctor_proj_sysrecv`، بريده `system@eppne.com` — **مستلم رسوم النظام**) الآن `{'MR_USDT': 110.0}` و`updated_at=2026-09-22 00:27:19+00`؛ و`wallets.id=45` (المستخدم `47` = `p_ctor_re_owner`، مالك عقارات الاختبار) الآن `{'MR_USDT': 1400.0}` و`updated_at=2026-09-21 23:36:42+00`. كلاهما داخل نافذة الانحدار (23:28–00:33 UTC) | ⚠️ **لم يُستعَد — القيم السابقة غير مسجَّلة** (لقطاتي تحفظ md5 للجدول لا صفوفه؛ جدول `transactions` لم يتغير — 192 صفًا — فلا سجل لتقدير الفروق). كلاهما حساب اختبار دائم من جلسات سابقة يستقبل مدفوعات (رسوم `system@eppne.com` في `invoicing/service.py:191`، `tenders_auctions/service.py:495`، `tasks/billing.py:353`؛ وإيجار/ملكية realestate) وقد راكمت مجموعات الانحدار السابقة رصيدهما دون توثيق. **أي "استعادة" ستكون تخمينًا وكتابة غير مسجَّلة فلم أفعلها.** قرارك: (أ) تركها كما هي — موصى به، (ب) تعديلها بفروق مستنتجة من كود الاختبارات — تخمين. |
**بقية القاعدة:** بعد التنظيف (`s4` مقابل `s0`): **258 جدولًا بلا أي تغيّر، `wallets` الاستثناء الوحيد؛ `pg_indexes` 1877 بنفس الـhash؛ Redis 25→25 (كل الـ25 مفتاحًا مطابقة لـ`s0`)؛ مفتاح الـkill switch غائب.** المنفذ 8010 حر، صفر عمليات python/uvicorn/celery.

## 4) Backlog إضافي (تُسجَّل فقط)
| # | البند | الأولوية |
|---|---|---|
| B-12 | حارس `test_realestate_buy_fractional_ownership_invoice_ordering` قديم مقابل بنية `buy_fractional_ownership` الحالية (كتلة AI try/except قبل كتلة الفاتورة) | منخفض |
| B-13 | **مجموعات الاختبار تُغيّر محافظ حسابات اختبار دائمة (`wallets` 41 و45) وتترك رسائل `send_notification_task` يتيمة في طابور `celery`** (931 رسالة متراكمة من جلسات سابقة: لو شُغِّل worker يومًا ستُنفَّذ كلها لمستخدمين محذوفين) وتترك كاش Redis لمستخدمين محذوفين | متوسط |
| B-14 | لا يوجد baseline على مستوى الصفوف لجدولَي الحسابات (أستعمل md5 الجدول) — لقطاتي المستقبلية يجب أن تحفظ صفوف `wallets`/`users` الحساسة كاملة لتمكين استعادة دقيقة | منخفض (منهجي) |

## 5) الحالة النهائية
- **الميزة:** Kill Switch مُنفَّذ ومُتحقَّق حيًا (Part 3) + 18 اختبارًا + 144/147 انحدار (الفشل الوحيد سابق وغير مرتبط).
- **مفتوح يحتاج قرارك:** `wallets` 41/45 (أعلاه). لا شيء آخر معلَّق.
- الخادم متوقف؛ **لا staging ولا commit**؛ **لا كتابة في `PROGRESS_LOG.md`**. الملفات المعدَّلة الموجودة (14) والجديدة (3: `admin/__init__.py`، `admin/schemas.py`، ملف الاختبار) غير مُثبَّتة؛ عند الـcommit تُفصل هنكات هذه الجلسة عن التعديلات السابقة في `config.py`/`security.py`/`main.py`/`logistics/service.py` بمساعدة نسخ `git diff HEAD` المحفوظة في scratchpad (`prediff/`).

---

## 6) القرار النهائي وإغلاق الدفعة 0-C
**قرار المالك (بعد مراجعة §3):** **ترك `wallets` 41 و45 كما هما — لا استعادة.** المبرر: جدول `transactions` لم يتغيّر (192 صفًا)، فلم يُفقد أي سجل محاسبي حقيقي؛ وأي استعادة الآن ستكون تخمينًا وكتابة غير مسجَّلة. الحسابان (`p_ctor_proj_sysrecv` / `p_ctor_re_owner`) حسابا اختبار دائمان؛ الحالة الحالية: المحفظة 41 = `{'MR_USDT': 110.0}`، والمحفظة 45 = `{'MR_USDT': 1400.0}`. مرتبط بالبندين B-13/B-14.

**الدفعة 0-C مُغلَقة.** لا staging، لا commit، لا كتابة في `PROGRESS_LOG.md` في هذه الجلسة. الخادم متوقف والمنفذ 8010 حر.
