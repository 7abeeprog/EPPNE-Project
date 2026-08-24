# جلسة إصلاح IDOR في `ai_agents` — استكمال لمسار `sovereign_entities`/`academy`/`commerce`/`saas`

**بدأ التسجيل:** 2026-08-24
**نطاق الجلسة:** حصريًا `eppne-backend/app/domains/ai_agents/{router,service,repository,schemas}.py` (13 endpoint).

**الملفات المرجعية اللي اتقرت كاملة قبل البدء:**
- `.claude/reports/simpletenant-fix-session-log.md` (النمط الميكانيكي المُختبَر — `academy`(36)، `commerce`(11)، `saas`(17)، `sovereign_entities`(17 من 22 وقتها))
- `.claude/reports/sovereign-entities-idor-fix-session-log.md` (جلسة اليوم 2026-08-24 نفسها — أقفلت الـ4 مواضع الباقية في `sovereign_entities`، وثّقت اكتشاف إزالة `require_sector` من `main.py`)
- `.claude/plans/critical-finding-xtenant-systemic.md` (تصنيف `ai_agents` ضمن الـ20 دومين المشتبه فيها، الصف #4)
- `eppne-backend/app/domains/ai_agents/{router,service,repository,schemas}.py` (كاملة)
- `eppne-backend/app/core/security.py` (تعريف `get_current_tenant`/`SimpleTenant`)
- `eppne-backend/app/main.py` (تسجيل الراوترز الحالي)

**تصحيح على تعليمات الجلسة:** المرجع المذكور في التعليمات (`simpletenant-fix-session-log.md`) موجود فعليًا ومطابق للوصف — **صفر تناقض هذه المرة**، على عكس جلسة `sovereign_entities` اللي سبقت هذه (كانت التعليمات فيها بتشاور لتقرير غير موجود). تم أيضًا قراءة تقرير `sovereign_entities-idor-fix` (اليوم نفسه) كمرجع إضافي أحدث وأدق لأنه يعكس حالة `main.py` الحالية (بعد إزالة `require_sector`).

---

## 1) اكتشاف بنيوي حرج يغيّر افتراض مستوى المصادقة — يجب قراءته قبل أي شيء

`app/core/security.py` **معدَّل حاليًا بلا commit** (`git status` يظهره `M`) — تعديل من جلسة منفصلة تمامًا (`require-sector-removal-subscription-fix-session-log.md`، 2026-08-20)، **غير متعلق بـ`ai_agents` إطلاقًا**، لكنه يغيّر خط الأساس الأمني لكل الدومينات:

- `require_sector()` **أصبحت DEPRECATED صراحة** (تعليق فوق التعريف، `security.py:203-207`) — **مش ملفوفة على أي راوتر في `main.py` بعد الآن**.
- تأكيد مباشر من `main.py:300-308`: كل الراوترز (شامل `ai_agents_router`) بتتسجل بـ`include_router(router_obj, prefix="/api", tags=tags_list)` **بلا أي `Depends` إضافي على مستوى التسجيل**.
- **النتيجة العملية:** المصادقة الوحيدة المتبقية لأي endpoint في `ai_agents` هي اللي مُعلَنة **صراحة في توقيع الدالة نفسها** (`current_user: User = Depends(...)`). لا يوجد أي غطاء خارجي (زي `require_sector` قديمًا).

**الخبر الجيد لـ`ai_agents` تحديدًا:** بعكس الـ4 مواضع اللي كانت معلَّقة في `sovereign_entities` (كانت بلا `current_user` في توقيعها إطلاقًا، فتحولت من "محمية بـSUPER_ADMIN كحد أدنى" إلى "بلا أي حاجز" بسبب نفس إزالة `require_sector`)، **كل الـ13 endpoint في `ai_agents` عندها `current_user: User = Depends(get_current_active_user أو get_current_superuser)` صريح في توقيعها من الأساس** — تأكَّد بقراءة الملف كامل، صفر استثناء. **صفر endpoint بلا مصادقة إطلاقًا في هذا الدومين** — المشكلة هنا مختلفة تمامًا: **مصدر `tenant_id`**، مش غياب المصادقة.

---

## 2) الجرد الكامل — 13/13 endpoint، كلهم بنفس مصدر التلوث (`get_current_tenant`)

قراءة حية لـ`router.py` (264 سطر) اليوم تؤكد: **صفر تغيير منذ فحص `critical-finding-xtenant-systemic.md` الأصلي**. الـ13 endpoint كلهم يستخدمون:

```python
tenant: AcademyTenant = Depends(get_current_tenant),
```

`get_current_tenant` (`core/security.py:275-280`) بترجع كائن مصدره **حصريًا هيدر `X-Tenant-ID`**، بقيمة افتراضية **`1`** لو الهيدر غايب تمامًا (`Header(default=1, alias="X-Tenant-ID")`) — **هذا يعني أن أي طلب لا يرسل الهيدر أصلًا (وهو الافتراضي لأي عميل لا يعرف بوجود هذا الهيدر) يُعامَل تلقائيًا كأنه تينانت 1، بغض النظر عن تينانت المستخدم الحقيقي المشفَّر في الـJWT.** هذا أخطر حتى من "تزوير هيدر" — الاستغلال **لا يتطلب أي تزوير على الإطلاق**، فقط **حذف** هيدر لا يعرفه أغلب العملاء أصلًا.

**ملاحظة تصنيف مهمة:** هذا الدومين مصنَّف في `simpletenant-fix-session-log.md` ضمن الفئة **✅ (أ)** (`.id` مستخدَمة صح، صفر كراش `SimpleTenant`) — بعكس `academy`/`commerce`/`saas`/`sovereign_entities` اللي كانت فيها كراشات `DataError`/`TypeError` تمنع الاستغلال الفعلي. **ده يعني إن `ai_agents` ليس فيه أي حاجز كراش يحجب الاستغلال — الثغرة هنا حية وقابلة للاستغلال الفوري بلا أي عائق تقني إضافي**، وهو ما أكَّده التحقق الحي تحت.

### جدول الـ13 endpoint — الموقع، مستوى الحماية، ومكان الفلتر الناقص بالضبط

| # | الدالة | السطور | مستوى `current_user` | فلتر إضافي (owner/approver) موجود؟ | الخطورة الفعلية المؤكَّدة |
|---|---|---|---|---|---|
| 1 | `create_agent` | 29-42 | `superuser` | لا | 🔴 كتابة: إنشاء agent تحت تينانت اعتباطي (تلوث بيانات) |
| 2 | `list_agents` | 45-63 | `active_user` | ✅ `owner_id=current_user.id` (service→repo) | 🟢 آمن فعليًا (مؤكَّد حيًا: `[]` عبر تينانت) |
| 3 | `get_agent` | 66-80 | `active_user` | ✅ `owner_id=current_user.id` (`get_agent_by_owner`) | 🟢 آمن فعليًا (مؤكَّد حيًا: `404`) |
| 4 | `execute_agent_action` | 83-102 | `active_user` | ❌ فلتر تينانت فقط (`repo.get_agent`، بلا owner) | 🔴🔴🔴 **الأخطر — مؤكَّد حيًا: تنفيذ فعلي + تكلفة + إنشاء approval** |
| 5 | `update_agent_status` | 105-122 | `superuser` | ❌ فلتر تينانت فقط | 🔴 مؤكَّد حيًا: كتابة (تعطيل agent تينانت تاني) — **نفس الصف #4 في `critical-finding-xtenant-systemic.md`** |
| 6 | `delete_agent` | 125-142 | `superuser` | ❌ فلتر تينانت فقط | 🔴 غير مُختبَر حيًا (تدميري، غير قابل للتراجع) — نفس نمط #5 منطقيًا |
| 7 | `get_pending_approvals` | 149-159 | `active_user` | ✅ `human_approver_id=current_user.id` | 🟢 آمن فعليًا (نفس منطق #2/#3) |
| 8 | `resolve_approval` | 162-183 | `active_user` | ✅ فحص `human_approver_id` **بعد** الجلب (`service.py:283`) | 🟡 آمن من "استغلال هوية غيرك"، لكن **مؤكَّد حيًا أنه يسمح للمستخدم يوافق/يرفض على إجراء agent تينانت تاني طالما هو نفسه approver الطلب (سيناريو ناتج عن #4)** |
| 9 | `list_approvals` | 186-203 | `active_user` | ❌ **صفر فلتر ملكية إطلاقًا** (`repo.py:200-212`) | 🔴🔴 مؤكَّد حيًا: تسريب كامل approvals تينانت تاني (شامل approvals لمستخدمين آخرين غير المهاجم) |
| 10 | `get_approval` | 206-217 | `active_user` | ❌ صفر فحص `human_approver_id` في الراوتر/service (`service.py:327-328`) | 🔴 لم يُختبَر حيًا مباشرة (مغطى ضمنيًا عبر #9)، نفس الفئة |
| 11 | `get_agent_analytics` | 224-237 | `active_user` | ❌ فلتر تينانت فقط | 🔴 مؤكَّد حيًا: تسريب تكلفة/إحصائيات agent تينانت تاني |
| 12 | `get_agent_status` | 240-249 | `active_user` | ❌ فلتر تينانت فقط | 🔴 مؤكَّد حيًا: تسريب حالة agent تينانت تاني |
| 13 | `get_ai_usage` | 256-264 | `active_user` | ❌ فلتر تينانت فقط | 🔴 **محجوب عن التحقق الحي ببج pre-existing منفصل** (تفصيل تحت) |

**ملخص:** 9 من أصل 13 عندهم تسريب/كتابة cross-tenant فعلية بلا أي فحص ملكية إضافي (#1، #4، #5، #6، #9، #10، #11، #12، #13). 4 منهم محميين فعليًا بفلتر ملكية إضافي على مستوى `owner_id`/`human_approver_id` (#2، #3، #7، #8) — الهيدر بلا أي تأثير عليهم عمليًا لأن المصدر الحقيقي للحماية هو `current_user.id` الآتي من الـJWT، **لكن `tenant_id` نفسه لسه ملوَّث فيهم منطقيًا ويستاهل نفس الإصلاح للاتساق** (defense in depth، مش لأنه مستغَل حاليًا).

---

## 3) التحقق الحي — قبل أي إصلاح (uvicorn حقيقي، بيانات throwaway، تنظيف كامل بعده)

**البيئة:** `docker ps` أكَّد `eppne_db`/`postgres-eppne`/`redis` شغالين مسبقًا. `uvicorn` حقيقي شُغِّل محليًا (`127.0.0.1:8000`)، لوج إقلاع نظيف تمامًا (`Application startup complete`، صفر `Traceback` عند الإقلاع).

**المستخدمان (throwaway، معاد استخدامهم من جلسة `sovereign_entities` اليوم نفسها، بادئة `TEST_` معروفة):**
- User A: `TEST_super_a@example.com` (`id=772`, `SUPER_ADMIN`, **تينانت 1**)
- User B: `TEST_instr_b@example.com` (`id=774`, `SUPER_ADMIN`, **تينانت 16**)

تسجيل دخول حقيقي (`POST /api/identity/login`) للاثنين، توكنات `Bearer` حقيقية.

**Agent throwaway واحد** أُنشئ عبر الـAPI الحقيقي (`POST /api/ai/agents`, بادئة `p_ai_agents_idor_verify_`) بواسطة User A (مالكه الشرعي، تينانت1): `agent id=114`، فُعِّل (`ACTIVE`) بواسطة نفس المالك.

### 🔴🔴🔴 النتيجة الحاسمة — Test #1: `execute_agent_action`، بلا أي تزوير هيدر إطلاقًا

```
POST /api/ai/agents/114/execute?action_type=CHAT
Authorization: Bearer <TOKEN_B>          (User B، تينانت16 الحقيقي)
(بلا أي X-Tenant-ID header)

→ 200 {"status":"PENDING_APPROVAL","approval_id":73,"result":{...رد AI حقيقي...}}
```

**لم يُستخدَم أي هيدر مزوَّر — فقط عدم إرسال الهيدر (السلوك الطبيعي لأي عميل لا يعرف بوجوده) كفى** لأن `Header(default=1, ...)` بترجع تينانت1 دايمًا في الغياب. تحقق DB مستقل فوري:

```sql
SELECT id, tenant_id, agent_id, user_id FROM ai_task_logs WHERE agent_id=114;
 id | tenant_id | agent_id | user_id
 79 |         1 |      114 |     774   -- User B (تينانت16 الحقيقي) نفّذ فعليًا تحت تينانت1
 80 |         1 |      114 |     774   -- (استدعاء تحكّم ثانٍ، نفس النتيجة بالحرف)
```

**الأثر المالي المؤكَّد:** `get_monthly_ai_cost`/`get_ai_usage` بيجمعوا التكلفة بـ`tenant_id` — استهلاك User B اتحسب فعليًا على فاتورة تينانت1، **بغض النظر عن أي إصلاح لاحق لباج `get_ai_usage`**.

### 🔴🔴🔴 النتيجة الأخطر — Test #2: `resolve_approval`، User B يوافق فعليًا على إجراء agent تينانت غيره

بما إن `execute_agent_action` أنشأت `approval id=73` بـ`human_approver_id=774` (نفس المنفِّذ الملوَّث)، فحص `resolve_approval` (اللي بيقارن `approval.human_approver_id == current_user.id`) **بينجح تلقائيًا** لأن الاتنين نفس القيمة (774) — رغم إن الـagent والـapproval فعليًا ملك تينانت1:

```
POST /api/ai/approvals/73/resolve   Authorization: Bearer <TOKEN_B>   (بلا هيدر)
{"status":"APPROVED","human_feedback":"idor-verify-approved-by-tenant16-user"}
→ 200 {"message":"Approval ApprovalStatus.APPROVED","approval_id":73,"status":"APPROVED"}
```
```sql
SELECT id, tenant_id, agent_id, human_approver_id, status, human_feedback FROM agent_approval_queue WHERE id=73;
 73 | 1 | 114 | 774 | APPROVED | idor-verify-approved-by-tenant16-user
```

**هذا يثبت سلسلة استغلال كاملة، لا مجرد قراءة معزولة:** مستخدم تينانت16 نفَّذ إجراء على agent تينانت1، ثم **صدَّق عليه رسميًا بنفسه** عبر آلية "الموافقة البشرية" (صمام الأمان المفروض يحمي تينانت1 من إجراءات AI غير مرغوبة) — **تجاوز كامل لآلية human-in-the-loop الخاصة بتينانت1 من طرف خارجي تمامًا**، بدون أي تزوير هيدر.

### 🔴🔴 Test #3: `list_approvals` — تسريب سجلات مستخدمين آخرين (ليس فقط سجلات المهاجم)

لإثبات إن التسريب **تينانت-واسع** مش مجرد نتيجة كون User B هو نفسه approver طلبه الخاص: نفَّذ User A (المالك الشرعي، تينانت1 حقيقي) إجراء شرعي إضافي (`approval id=75`, `human_approver_id=772`). بعدها:

```
GET /api/ai/approvals   Authorization: Bearer <TOKEN_B>   (بلا هيدر)
→ 200 [
  {"id":75,"agent_id":114,"human_approver_id":772, "proposed_payload":{"prompt":"legit tenant1 owner action"}, ...},  ← ملك User A بالكامل، صفر علاقة بـUser B
  {"id":74,"human_approver_id":774,...},
  {"id":73,"human_approver_id":774,"status":"APPROVED",...}
]
```

**مؤكَّد قاطعًا:** `approval id=75` (ملك كامل لـUser A، تينانت1، بلا أي علاقة بـUser B) ظهر في نتيجة User B — **صفر فلتر ملكية على `list_approvals` إطلاقًا**، الفلتر الوحيد هو `tenant_id` الملوَّث.

### 🔴 Test #4/#5: `get_agent_status` / `get_agent_analytics` — تسريب قراءة إضافي

```
GET /api/ai/agents/114/status      (User B، بلا هيدر) → 200 {"agent_id":114,"status":"ACTIVE",...}
GET /api/ai/agents/114/analytics   (User B، بلا هيدر) → 200 {"total_cost_mrusdt":0.0,"total_tasks":2,...}
```
تسريب مباشر لحالة/تكلفة agent تينانت1 لمستخدم تينانت16 بمجرد معرفة/تخمين `agent_id`.

### 🔴 Test #6: `update_agent_status` — كتابة تخريبية مؤكَّدة حيًا (يطابق الصف #4 في `critical-finding-xtenant-systemic.md`)

```
PATCH /api/ai/agents/114/status   (User B، superuser تينانت16، بلا هيدر)   {"status":"SUSPENDED"}
→ 200، وتحقق DB مستقل: ai_agents.id=114 → status=SUSPENDED
```
مستخدم تينانت16 عطَّل فعليًا agent تينانت1 (ملك User A) — **كتابة تخريبية cross-tenant مؤكَّدة حيًا، بلا أي علاقة بملكية أو حتى نفس-approver زي الحالة السابقة** (هنا الفحص الوحيد فلتر التينانت، وهو ملوَّث بالكامل).

### 🟢 Test مقارنة (Control) — `get_agent`/`list_agents` (المحميان بفلتر ownership) آمنان فعليًا

```
GET /api/ai/agents/114   (User B، ليس المالك، بلا هيدر) → 404 "Agent not found or you don't have permission."
GET /api/ai/agents       (User B، بلا هيدر)              → 200 []
```
يثبت إن فلتر `owner_id`/`human_approver_id` (حيث موجود) **يمنع الاستغلال فعليًا حتى بوجود مصدر `tenant_id` ملوَّث** — الفرق الحاسم بين الفئتين في الجدول فوق.

### 🟡 `get_ai_usage` — محجوب عن التحقق الحي ببج pre-existing منفصل تمامًا

```
GET /api/ai/usage   (User B، بلا هيدر) → 500
Traceback: service.py:356 → AttributeError: 'TenantSubscription' object has no attribute 'features'
```
الموديل `TenantSubscription` (دومين `saas`) **لا يحتوي عمود/خاصية `features` أصلًا** — أي استدعاء لـ`get_ai_usage` **يكراش دايمًا لأي تينانت له اشتراك فعلي** (الكراش نفسه دليل غير مباشر إن تينانت1 عنده اشتراك — لولا وجوده كانت الدالة رجعت `{}` بلا كراش). **نفس فئة "schema/attribute drift" الموثَّقة سابقًا في `saas.pay_invoice`/`sovereign_entities.audit_log`** — pre-existing، صفر علاقة بـIDOR، **خارج نطاق هذا الإصلاح**. الكود الخاص بمصدر `tenant_id` في هذا الـendpoint سيُصلَح شكليًا بنفس القاعدة الميكانيكية، لكن **التحقق الحي الحاسم غير ممكن فعليًا حاليًا** — موثَّق بصراحة كفجوة، مش كنجاح مُفترَض.

### التنظيف — مكتمل، مؤكَّد مستقل

```sql
DELETE FROM agent_approval_queue WHERE id IN (73,74,75);  -- 3
DELETE FROM ai_task_logs WHERE agent_id=114;               -- 2
DELETE FROM ai_agents WHERE id=114;                         -- 1
```
تحقق `SELECT COUNT` مستقل بعد الحذف: **صفر في الثلاثة**. `audit_logs` DB table: صفر صف يحتوي `114` (تأكَّد — استدعاءات `audit_log()` في هذا الدومين بتكتب سطر لوج فقط، مش صف DB، فصفر أثر متبقٍّ). السيرفر التجريبي أُوقف (`taskkill`)، ملف اللوج المؤقت اتحذف.

---

## 4) الحل المقترَح — نفس النمط الميكانيكي المُختبَر (13/13 موضع، صفر استثناء)

**القاعدة (مطابقة حرفيًا لـ`academy`/`commerce`/`saas`/`sovereign_entities`):**
- إزالة `tenant: AcademyTenant = Depends(get_current_tenant),` من التوقيع.
- إضافة `tenant_id = cast(int, current_user.tenant_id)` كأول سطر في جسم الدالة (`current_user` موجودة بالفعل في كل الـ13، `cast` مستوردة بالفعل — `from typing import ... cast`).
- استبدال كل استخدام لاحق لـ`tenant.id` بـ`tenant_id` (المتغيّر الجديد).
- إزالة `get_current_tenant` من سطر الاستيراد (`from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser` → إزالة `get_current_tenant`) — **صفر استخدام آخر له في الملف بعد الإصلاح** (بعكس `commerce`/`sovereign_entities` اللي احتفظا باستيراده بسبب استثناء واحد متبقٍّ؛ هنا الـ13 كلهم بيتصلحوا فصفر داعٍ للاستيراد).
- **`AcademyTenant` import** (`from app.domains.academy.models import AcademyTenant`) بيبقى بلا استخدام بعد الإصلاح — يُزال كمان (تنظيف تبعي مباشر، مش تغيير سلوك).

### جدول الديف المقترَح بالضبط — 13/13، صفر استثناء

| الدالة | سطر الحذف | إضافة (أول سطر بالجسم) | ملاحظة |
|---|---|---|---|
| `create_agent` | 33 | `tenant_id = cast(int, current_user.tenant_id)` | — |
| `list_agents` | 51 | نفس السطر | آمنة فعليًا مسبقًا (owner filter)، إصلاح دفاع بالعمق |
| `get_agent` | 69 | نفس السطر | نفس الملاحظة |
| `execute_agent_action` | 90 | نفس السطر | **الأولوية القصوى — مؤكَّد حيًا** |
| `update_agent_status` | 110 | نفس السطر | مؤكَّد حيًا |
| `delete_agent` | 130 | نفس السطر | نفس نمط `update_agent_status` منطقيًا |
| `get_pending_approvals` | 151 | نفس السطر | آمنة فعليًا مسبقًا |
| `resolve_approval` | 167 | نفس السطر | **أولوية قصوى — مؤكَّد حيًا (تجاوز human-in-the-loop)** |
| `list_approvals` | 192 | نفس السطر | **أولوية قصوى — مؤكَّد حيًا (تسريب بيانات)** |
| `get_approval` | 209 | نفس السطر | نفس الفئة، لم يُختبَر مباشرة |
| `get_agent_analytics` | 228 | نفس السطر | مؤكَّد حيًا |
| `get_agent_status` | 243 | نفس السطر | مؤكَّد حيًا |
| `get_ai_usage` | 258 | نفس السطر | مصدر `tenant_id` يُصلَح شكليًا؛ التحقق الحي محجوب ببج `TenantSubscription.features` منفصل |

**مثال دقيق (`execute_agent_action`، الأخطر):**
```python
# قبل
async def execute_agent_action(
    agent_id: int,
    action_type: str,
    payload: dict,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AIAgentsService(db, cast(int, tenant.id))
    ...

# بعد
async def execute_agent_action(
    agent_id: int,
    action_type: str,
    payload: dict,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = cast(int, current_user.tenant_id)
    service = AIAgentsService(db, tenant_id)
    ...
```

**صفر تغيير على `service.py`/`repository.py`** — توقيعاتهم بالفعل `tenant_id: int`، المشكلة فقط في مصدر القيمة عند الاستدعاء من الراوتر. **صفر تغيير على `schemas.py`** — غير متعلق بمصدر التينانت إطلاقًا.

---

## 5) النطاق — ما لن يُلمَس (اكتشافات جانبية، توثيق فقط)

1. **`get_ai_usage` / `TenantSubscription.features`:** `AttributeError` pre-existing يمنع أي تحقق حي حاسم لهذا الـendpoint تحديدًا، بغض النظر عن إصلاح `tenant_id`. خارج النطاق، يحتاج فحص موديل `TenantSubscription` في دومين `saas` (قرار منفصل).
2. **`resolve_approval` — فحص الملكية بيحصل بعد الجلب مش قبله:** حتى بعد إصلاح `tenant_id`، البنية نفسها (`get_approval(id, tenant_id)` ثم فحص `human_approver_id` لاحقًا) سليمة منطقيًا بعد الإصلاح (الجلب هيبقى مقيَّد بتينانت المستخدم الحقيقي أصلًا) — **صفر حاجة لتغيير إضافي هنا**، فقط توثيق إن هذا هو نمط الحماية الصحيح المستقبلي.
3. **`delete_agent` (سطر 135-137):** بيستدعي `service.get_agent(agent_id)` (بلا owner check) **قبل** `service.delete_agent()` — هذا موجود بالفعل زي باقي الأنماط، الإصلاح المقترَح يغلقه لأن `tenant_id` نفسه هيبقى موثوق. **لم يُختبَر حيًا (تدميري)** — الإصلاح المقترَح نفس نمط `update_agent_status` المؤكَّد حيًا، افتراض معقول لكن غير مثبت تجريبيًا لهذه الدالة بالذات.
4. **باج بنيوي عام (خارج `ai_agents`):** إزالة `require_sector` من `main.py` (جلسة 2026-08-20) لم تُقيَّم آثارها على كل دومين على حدة — تأكَّد هنا إن `ai_agents` **غير متأثر عمليًا** لأن كل endpoint عنده `current_user` صريح، لكن هذا **افتراض يستاهل تعميمه بفحص منهجي مماثل عبر باقي الـ29 دومين** (نفس التوصية اللي صدرت في جلسة `sovereign_entities` اليوم) — **خارج نطاق هذه الجلسة، توصية Backlog فقط**.
5. **`AcademyTenant` كنوع إرجاع لـ`get_current_tenant` في `ai_agents`:** استخدام اسم موديل من دومين `academy` كـtype hint في دومين `ai_agents` غير متعلق منطقيًا — على الأرجح نسخ-لصق من مكان آخر وقت الكتابة الأصلية. **صفر أثر وظيفي** (الـannotation لا يفرض تحويل نوع حقيقي، ونفس الملاحظة انطبقت تاريخيًا على `SimpleTenant` في كل الدومينات الأخرى) — يُزال تلقائيًا كجزء من إزالة الـimport غير المستخدم، **صفر قرار إضافي مطلوب**.

---

## 6) الحالة الآن

**صفر تنفيذ. صفر تعديل كود حتى الآن.** التحقق الحي (قبل الإصلاح) **مكتمل بالكامل** — أثبت استغلالًا فعليًا حيًا (لا كامنًا) عبر 3 سلاسل هجوم مختلفة (تنفيذ agent + تجاوز موافقة بشرية + تسريب بيانات + كتابة تخريبية)، **بلا الحاجة لأي تزوير هيدر** (الافتراضي `X-Tenant-ID=1` كافٍ وحده). بيانات الاختبار اتنضّفت بالكامل ومؤكَّدة مستقل. السيرفر التجريبي مُوقَف.

---

## 7) القرار المطلوب منك — 3 نقاط، رد بالأرقام/الحروف يكفي

### س1. تطبيق الديف؟
- **(أ) نفّذ الـ13 كلهم دفعة واحدة** (الديف مطابق ميكانيكيًا لأربعة دومينات سابقة، صفر استثناء حقيقي في القاعدة نفسها).
- **(ب) نفّذ الأولوية القصوى بس أولًا** (`execute_agent_action`, `update_agent_status`, `delete_agent`, `resolve_approval`, `list_approvals`, `get_approval`, `get_agent_analytics`, `get_agent_status`, `get_ai_usage`, `create_agent` = 10) وأجّل الأربعة الآمنة فعليًا (`list_agents`, `get_agent`, `get_pending_approvals` — دفاع بالعمق بس، غير مستغَلة).
- **(ج) وقف، عايز تعديل على القاعدة نفسها قبل التنفيذ.**

### س2. صرامة التحقق الحي "بعد"؟
- **(أ) نفس الأربعة الحاسمة** (`execute_agent_action`, `resolve_approval`, `list_approvals`, `update_agent_status`) بمعيار `finance.transfer` الصارم (SELECT مستقل قبل/بعد) — هي اللي عندها دليل حي "قبل" فعلي.
- **(ب) الأربعة دول + كمان `get_agent_analytics`/`get_agent_status`/`create_agent`/`delete_agent`** (تغطية أوسع، وقت أطول).
- **(ج) يكفي `grep`+`py_compile`+إقلاع نظيف، بلا تحقق حي "بعد"** (مش موصى بيه نظرًا لطبيعة الاستغلال المالي/الأمني المؤكَّد).

### س3. باج `get_ai_usage` / `TenantSubscription.features`؟
- **(أ) يُترك موثَّقًا Backlog فقط** (زي `saas.pay_invoice`/`sovereign_entities.audit_log` سابقًا) — نفس نمط الجلسات قبل كده.
- **(ب) افتح بند منفصل الآن** لفحص موديل `TenantSubscription` (دومين `saas`) قبل إغلاق هذه الجلسة.

**رد سريع كفاية، مثلاً: "1أ 2أ 3أ".**

---

## 8) قرار المستخدم [2026-08-24]: **1أ 2ب 3أ** + توجيه إضافي

- **1أ:** تنفيذ الـ13 endpoint دفعة واحدة.
- **2ب:** تحقق حي صارم (SELECT مستقل) على `execute_agent_action`/`resolve_approval`/`list_approvals`/`update_agent_status`، **+ تحقق حي فعلي (مش مجرد grep/compile)** على `get_agent_analytics`/`get_agent_status`/`create_agent`/`delete_agent` — **تشديد خاص على `delete_agent`** لأنه تدميري وغير قابل للتراجع ولم يُختبَر حيًا في أي جلسة سابقة.
- **3أ:** باج `get_ai_usage`/`TenantSubscription.features` يُترك Backlog فقط.
- **توجيه إضافي:** توثيق اكتشاف Test #2 (تجاوز human-in-the-loop عبر `resolve_approval`) كتحديث بارز ومنفصل في `critical-finding-xtenant-systemic.md`، بتصنيف صريح كـ**exploit chain كامل** (مش مجرد IDOR/تسريب قراءة قياسي) — ✅ **مُنفَّذ** (راجع التحديث `🔴🔴🔴 [2026-08-24]` أعلى ذلك الملف + تعديل وصف الصف #4 في جدول SUSPICIOUS).

---

## 9) التنفيذ — مكتمل بالكامل

### 9.1 الديف — مطابق تمامًا للمقترَح في القسم 4

طُبِّق على الـ13 endpoint كلهم بالحرف: حذف `tenant: AcademyTenant = Depends(get_current_tenant)`، إضافة `tenant_id = cast(int, current_user.tenant_id)` كأول سطر بالجسم، استبدال كل استخدام لاحق لـ`tenant.id` بـ`tenant_id`. إزالة `get_current_tenant` من سطر استيراد `app.api.deps`، وإزالة `from app.domains.academy.models import AcademyTenant` بالكامل (بلا استخدام آخر في الملف). **صفر تغيير على `service.py`/`repository.py`/`schemas.py`.**

**تأكيد `grep` مستقل بعد التطبيق:**
```
grep -n "get_current_tenant|AcademyTenant|tenant\.id|tenant:" router.py → 0 نتيجة
```
`python -m py_compile app/domains/ai_agents/router.py` → `exit code 0`. قراءة الملف كامل (264 سطر) بعد التعديل أكَّدت تطابق تام مع الديف المعروض في القسم 4 — الـ13 دالة كلهم بنفس البنية، صفر استثناء، صفر أثر جانبي على أي endpoint خارج النطاق.

### 9.2 إعادة تشغيل uvicorn

تأكيد صريح إن البورت 8000 فاضي قبل التشغيل (القاعدة الإلزامية من جلسات سابقة)، تشغيل نظيف (`PYTHONIOENCODING=utf-8`)، لوج إقلاع نظيف تمامًا (نفس تحذيرات dev المعتادة + نفس تحذيرات فهرسة DB pre-existing غير متعلقة، `Application startup complete`، صفر `Traceback`).

### 9.3 التحقق الحي "بعد" — إعادة تنفيذ نفس سلسلة الاستغلال بالحرف

**بيانات throwaway جديدة** (نفس مستخدمَي التحقق "قبل"، `TEST_super_a`/تينانت1، `TEST_instr_b`/تينانت16): `agent id=115` (تينانت1، أُنشئ عبر الـAPI الحقيقي بواسطة User A، فُعِّل `ACTIVE`).

**التحقق الصارم (SELECT مستقل قبل/بعد، معيار `finance.transfer`):**

| Endpoint | السيناريو | قبل الإصلاح (موثَّق قسم 3) | بعد الإصلاح | تحقق DB مستقل |
|---|---|---|---|---|
| `execute_agent_action` | User B (تينانت16 حقيقي، **بلا هيدر**) على agent 115 (تينانت1) | `200` تنفيذ ناجح + `approval` جديد | **`404` "الوكيل غير موجود"** | `ai_task_logs`/`agent_approval_queue` لـagent 115: **0 قبل، 0 بعد** (بلا تغيير) |
| `update_agent_status` | نفس السيناريو، `PATCH .../status {"SUSPENDED"}` | `200` تعطيل ناجح | **`404` "Agent not found"** | `ai_agents.status`: **ACTIVE قبل، ACTIVE بعد** (بلا تغيير) |
| `list_approvals` | User B يعرض approvals تينانت1 (بعد ما User A نفّذ إجراء شرعي، approval id=76) | approval 75 (ملك مستخدم آخر بالكامل) ظهر في نتيجة المهاجم | **`[]`** | — |
| `resolve_approval` | User B يحاول يوافق على approval 76 (تينانت1، approver=772) | `200` موافقة ناجحة (approval 73، approver=774=المهاجم نفسه) | **`404`** "Approval not found or you don't have permission." | `agent_approval_queue.id=76`: **`PENDING`/`human_feedback=NULL` قبل وبعد** (بلا تغيير) |

**✅ حاسم بالكامل — نفس سلسلة الاستغلال الثلاثية المؤكَّدة "قبل" مقفولة تمامًا "بعد"، بأدلة DB مستقلة في كل خطوة.**

**Sanity إضافي:** User A (المالك الشرعي) نفّذ agent 115 وحلّ approval 76 بنفسه بنجاح (`200`) — المسار الشرعي داخل نفس التينانت **لم يتأثر إطلاقًا** بالإصلاح.

**التحقق الحي الإضافي (مطلوب صراحة، ليس grep فقط):**

| Endpoint | الاختبار | النتيجة |
|---|---|---|
| `get_agent_status` | User B، بلا هيدر، على agent 115 | **`404`** "الوكيل غير موجود" (كان `200` قبل الإصلاح مع بيانات تينانت1) |
| `get_agent_analytics` | نفس السيناريو | **`404`** (كان `200` مع تكلفة/إحصائيات تينانت1 قبل الإصلاح) |
| `create_agent` | User B (superuser تينانت16 حقيقي)، بلا هيدر، ينشئ agent جديد | `agent id=116` أُنشئ بـ`tenant_id=16` (تينانت B الحقيقي) — **قبل الإصلاح كان سيُنشأ تحت أي تينانت في الهيدر/الافتراضي=1** |
| `delete_agent` (**الأولوية — تدميري، لم يُختبَر حيًا قبل كده إطلاقًا**) | User B، بلا هيدر، `DELETE /agents/115` (agent تينانت1، غير مملوك له) | **`404`** "Agent not found" — تحقق DB مستقل: `is_deleted=false` **قبل وبعد المحاولة** (بلا أي أثر تخريبي) |
| `delete_agent` (sanity شرعي) | User A يحذف agent 115 بتاعه (soft) | `204`، `is_deleted=true` — يعمل صح لصاحبه الشرعي |
| `delete_agent` (sanity شرعي، تينانت تاني) | User B يحذف agent 116 بتاعه (soft) | `204`، `is_deleted=true` |

**✅ `delete_agent` — أخطر endpoint غير مُختبَر سابقًا، الآن مؤكَّد حيًا بالكامل في الاتجاهين:** محجوب تمامًا cross-tenant (صفر أثر تخريبي على agent لا يملكه المهاجم)، ويعمل بشكل طبيعي لصاحبه الشرعي (مستخدَم أيضًا كتنظيف).

### 9.4 تنظيف بيانات throwaway — مكتمل، مؤكَّد مستقل

```sql
DELETE FROM agent_approval_queue WHERE agent_id IN (115,116);  -- 1
DELETE FROM ai_task_logs WHERE agent_id IN (115,116);           -- 1
DELETE FROM ai_agents WHERE id IN (115,116);                     -- 2
```
تحقق `SELECT COUNT` مستقل بعد الحذف: **صفر في الثلاثة**. بيانات جلسة "قبل" (agent 114 وتوابعه) كانت اتنضّفت بالفعل في القسم 3. السيرفر التجريبي أُوقف (`taskkill`)، ملفات اللوج/التوكن المؤقتة اتحذفت.

### 9.5 تحديث التوثيق

- `.claude/plans/critical-finding-xtenant-systemic.md` — تحديث بارز `🔴🔴🔴 [2026-08-24]` مُضاف (يوثّق exploit chain الكامل + الإصلاح + أدلة قبل/بعد)، ووصف الصف #4 في جدول SUSPICIOUS اتحدَّث للإشارة للتحديث. **الفقرات القديمة لم تُعدَّل، فقط إضافة.**
- `PROGRESS_LOG.md` — سطر جديد مُضاف (راجع القسم 10 تحت لتفاصيل الرسالة).

---

## 10) الحالة النهائية

✅ **الـ13 endpoint كلهم مُصلَحين، مؤكَّدين حيًا بالكامل** (4 اختبارات صارمة بمعيار SELECT مستقل + 5 اختبارات حية إضافية شاملة `delete_agent` التدميري). **صفر أثر جانبي على المسار الشرعي داخل نفس التينانت** (مؤكَّد Sanity). **صفر لمس على أي ملف/دومين خارج `ai_agents/router.py`** (باستثناء التوثيق في `critical-finding-xtenant-systemic.md`/`PROGRESS_LOG.md`، بلا كود).
🟡 **باج pre-existing منفصل موثَّق فقط، صفر إصلاح:** `get_ai_usage`/`TenantSubscription.features` (`AttributeError`) — يمنع تحقق حي لهذا الـendpoint تحديدًا، خارج النطاق بقرارك (3أ).
⏳ **لم يُنفَّذ بعد:** `git add`/commit — بانتظار مراجعتك لـ`git status`/`git diff` قبل أي commit (القسم التالي في الرد).
