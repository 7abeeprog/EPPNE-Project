# جلسة فحص IDOR في `ai_governance` — استكمال سويپ الأمان

**بدأ التسجيل:** 2026-08-24
**الحالة:** ✅ **الإصلاح مُطبَّق على الـ9 endpoints بالكامل، مؤكَّد حيًا. لم يُنفَّذ commit بعد — بانتظار مراجعتك للـ`git diff` (§8) وموافقتك الصريحة.**

---

## 0) تصنيف المرجع المطلوب فحصه أولًا — `.claude/reports/ai-governance-agents-fix-session-log.md`

**قراءة كاملة للملف (556 سطر) تؤكد:** هذا **ليس فحص/إصلاح IDOR** (مصدر `tenant_id`/`current_user`) لدومين `ai_governance` نفسه. موضوعه الفعلي مختلف تمامًا:

- الجلسة المرجعية عالجت **باج `TypeError` في توقيع دالتين** يُستدعَيان من **13+19 موضعًا في دومينات أخرى تمامًا** (`academy`, `commerce`, `insurance`, `social`, ...): `AIGovernanceService.check_and_consume()` (تعيش في `ai_governance/service.py`) و`AIAgentsService.execute_agent_action()` (تعيش في **`ai_agents`**، دومين مختلف تمامًا عن `ai_governance`).
- المشكلة المُصلَحة: الكود القديم في تلك الـ32 موضع كان يمرر `tenant_id=` صريحة كـkwarg زائد لدالتين لا تقبلانه في توقيعهما الفعلي (الدالتان تستخدمان `self.tenant_id` من الـconstructor)، فيسبب `TypeError` عند كل استدعاء. الإصلاح: حذف الـkwarg الزائد + إضافة `action_type`/`idempotency_key` الناقصين في بعض المواضع.
- **صفر لمس لـ`ai_governance/router.py`** نفسه، **صفر فحص لمصدر `tenant_id` في الـendpoints الخاصة بدومين `ai_governance`**، **صفر تحقق ملكية/IDOR** من أي نوع. الجلسة بأكملها تدور حول *استدعاءات خارجية* لدالتين، لا حول أمان الدومين نفسه.

**الخلاصة (بالضبط زي حالة `affiliate-service-missing-methods` المذكورة كمرجع):** **اسم الملف ("ai-governance-agents-fix") لا يعكس محتواه الفعلي** — لا علاقة له بفحص IDOR لدومين `ai_governance`. **القرار: المتابعة بفحص عميق كامل من الصفر، بنفس منهجية `commerce-idor-fix-session-log.md`.**

**ملاحظة تأكيدية إضافية من `.claude/plans/critical-finding-xtenant-systemic.md` (صف #5):** الدومين **موثَّق بالفعل كـ`SUSPICIOUS`** (غير مُصلَح) في جدول ثغرة X-Tenant-ID المنهجية — `ai_governance/router.py:26-43,75-90,93-110,130-145,148-172` — **بلا أي تحديث "مُصلَح" لاحق** (بعكس `ai_agents` في نفس الجدول). هذا يتفق تمامًا مع القراءة الحية أدناه.

---

## 1) قراءة حية كاملة — `app/domains/ai_governance/{router,service,repository,schemas,models}.py`

قُرئت الملفات الخمسة كاملة (203+224+186+61+108 سطر). **نتيجة حاسمة: `ai_governance` لم يخضع لإصلاح `simpletenant-fix` (2026-08-13) إطلاقًا — لا هو من الأربعة دومينات المُصلَحة (`academy`/`commerce`/`saas`/`sovereign_entities`) ولا من الدومينات التي كانت SAFE من الأساس.**

### 🔴🔴🔴 المصدر الجذري — `Depends(get_current_tenant)` في **كل** الـ9 endpoint، بلا استثناء واحد

`router.py:8` يستورد `get_current_tenant` من `app.api.deps`، لكن التعريف الفعلي المُنفَّذ فعليًا (تتبُّع الاستيراد) في `app/core/security.py:275-280`:

```python
class SimpleTenant:
    id: int

async def get_current_tenant(
    x_tenant_id: int = Header(default=1, alias="X-Tenant-ID")
) -> SimpleTenant:
    tenant = SimpleTenant()
    tenant.id = x_tenant_id
    return tenant
```

**`tenant.id` مصدره الوحيد هو هيدر `X-Tenant-ID` الذي يرسله العميل بنفسه — بلا أي ربط بـ`current_user.tenant_id` الحقيقي، وبلا أي فحص لاحق.** هذا **بالضبط** نمط الثغرة الكلاسيكية الموثَّقة والمُصلَحة سابقًا في `academy`/`commerce`/`saas`/`sovereign_entities` — لكنها **لم تُصلَح هنا إطلاقًا**. كل التسعة endpoint في `ai_governance/router.py` تبني `AIGovernanceService(db, cast(int, tenant.id))` من هذا المصدر الملوَّث مباشرة، **صفر endpoint يستخدم `current_user.tenant_id`.**

### 🔴🔴🔴🔴 اكتشاف أخطر — `POST /agents/{agent_id}/check-and-consume` بلا أي مصادقة إطلاقًا

`router.py:175-186`:
```python
@router.post("/agents/{agent_id}/check-and-consume")
async def check_and_consume(
    agent_id: int,
    action_type: str,
    tokens: int,
    cost: float,
    user_id: int,
    request_tokens: int = 0,
    completion_tokens: int = 0,
    idempotency_key: Optional[str] = None,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
```
**لا يوجد `current_user: User = Depends(...)` في التوقيع إطلاقًا** — هذا الـendpoint الوحيد في كامل ملف `router.py` بلا أي معامل مصادقة. تأكَّد أيضًا من `main.py:270,300-308`: التسجيل عبر `include_router(ai_governance_router, prefix="/api", tags=[...])` بلا أي `dependencies=` إضافية (بعكس `identity_protected_router` الوحيد اللي بيتحط عليه `Depends(get_current_active_user)` صراحة عند التسجيل). **الخلاصة: `POST /api/ai-governance/agents/{agent_id}/check-and-consume` قابل للاستدعاء من أي طرف غير مسجَّل دخول إطلاقًا**، بـ`X-Tenant-ID` هيدر حر الاختيار و`user_id` حر الاختيار تمامًا (رقم عشوائي، بلا أي تحقق من وجوده حتى) — يستهلك حصة أي وكيل AI في أي تينانت، ويسجّل استخدام/تكلفة منسوبة لأي `user_id` يختاره المُرسِل.

### 🟡 باج تشغيلي منفصل — `_check_agent_ownership` مُستدعاة في الراوتر لكنها **غير مُعرَّفة إطلاقًا** في `AIGovernanceService`

`router.py:54,68,121` تستدعي `await service._check_agent_ownership(agent_id, current_user.id)` في 3 endpoints (`get_agent_quotas`, `get_agent_remaining_quotas`, `get_rate_limit`). **قراءة `service.py` كاملة (224 سطر) تؤكد: لا يوجد `def _check_agent_ownership` في الكلاس إطلاقًا.** كل استدعاء لهذه الثلاثة سيرمي `AttributeError` غير محمي بـ`try/except` في الراوتر → **`500` مضمون لكل طلب، بغض النظر عن التينانت أو الصلاحية**. هذا **ليس IDOR بحد ذاته** (الطلب يفشل بدل أن ينجح خطأً) لكنه يعني أن "فحص الملكية" المفترض في هذه الثلاثة **لا يعمل إطلاقًا حاليًا** — فئة مختلفة تمامًا (كراش وظيفي pre-existing)، موثَّقة هنا للاكتمال، **خارج نطاق إصلاح IDOR نفسه**.

---

## 2) جدول الـ9 endpoint — المستوى، مصدر tenant_id، فلتر الملكية، التصنيف

| # | الدالة | المسار | `current_user` | مصدر `tenant_id` | فلتر ملكية إضافي؟ | التصنيف |
|---|---|---|---|---|---|---|
| 1 | `set_agent_quota` | `POST /agents/{id}/quotas` | superuser | 🔴 `Depends(get_current_tenant)` (هيدر) | N/A | 🔴🔴🔴 IDOR عبر-تينانت مؤكَّد — كتابة إدارية (تعديل حصة) |
| 2 | `get_agent_quotas` | `GET /agents/{id}/quotas` | active_user | 🔴 هيدر | `_check_agent_ownership` (**غير مُعرَّفة — 500 دائمًا**) | 🟡 مكسور وظيفيًا (500)، غير قابل للاستغلال كـIDOR حاليًا بسبب الكراش |
| 3 | `get_agent_remaining_quotas` | `GET /agents/{id}/quotas/remaining` | active_user | 🔴 هيدر | نفس الشيء (**500 دائمًا**) | 🟡 نفس الشيء |
| 4 | `reset_agent_quotas` | `POST /agents/{id}/quotas/reset` | superuser | 🔴 هيدر | N/A | 🔴🔴🔴 IDOR عبر-تينانت مؤكَّد — كتابة إدارية (تصفير حصة) |
| 5 | `update_rate_limit` | `PUT /agents/{id}/rate-limit` | superuser | 🔴 هيدر | N/A | 🔴🔴🔴 IDOR عبر-تينانت مؤكَّد — كتابة إدارية |
| 6 | `get_rate_limit` | `GET /agents/{id}/rate-limit` | active_user | 🔴 هيدر | نفس الشيء (**500 دائمًا**) | 🟡 نفس الشيء |
| 7 | `get_agent_audit_logs` | `GET /agents/{id}/audit-logs` | superuser | 🔴 هيدر | N/A | 🔴🔴🔴 IDOR عبر-تينانت مؤكَّد — قراءة سجل تدقيق إداري حساس |
| 8 | `get_usage_summary` | `GET /agents/{id}/usage-summary` | superuser | 🔴 هيدر | N/A | 🔴🔴🔴 IDOR عبر-تينانت مؤكَّد — قراءة بيانات استخدام/تكلفة |
| 9 | `check_and_consume` (router) | `POST /agents/{id}/check-and-consume` | **بلا current_user إطلاقًا** | 🔴 هيدر | N/A | 🔴🔴🔴🔴 **الأخطر — بلا مصادقة على الإطلاق** |

**لا يوجد أي endpoint آمن في هذا الملف.** كل التسعة يعتمدون على تينانت مصدره هيدر غير موثوق.

---

## 3) التحقق الحي — مكتمل بالكامل

**البيانات:** وكيل throwaway حقيقي `P_AIGOV_AGENT_A` (`ai_agents id=127`، تينانت1، أُنشئ عبر الـAPI الحقيقي بواسطة `p_aigov_a` id=945 سوبريوزر تينانت1)، `p_aigov_b` (id=946، سوبريوزر تينانت16 — نُقل عبر SQL، نفس نمط الجلسات السابقة). **الدومين لا يمس `finance`/محافظ إطلاقًا — صفر خطر مالي في أي اختبار هنا.**

### 3.1 🔴🔴🔴🔴 `check-and-consume` — كتابة حقيقية بلا أي مصادقة، مؤكَّدة DB-level

طلب **بلا أي `Authorization` header أو كوكي إطلاقًا** (زائر غير مسجَّل دخول تمامًا):
```
POST /api/ai-governance/agents/127/check-and-consume?action_type=UNAUTH_TEST&tokens=42&cost=0.01&user_id=946
Header: X-Tenant-ID: 1
```
**الرد:** `200 {"allowed":false,"error":"'bool' object is not subscriptable","retry_after":null}` — يبدو كفشل ظاهريًا (بسبب باج منفصل تحت في §3.4)، **لكن**:

**تحقق DB مستقل فوري:**
```sql
agent_usage_logs: id=58, tenant_id=1, agent_id=127, user_id=946, action_type='UNAUTH_TEST', total_tokens=42, cost_mrusdt=0.01, status='SUCCESS'
```
**صف حقيقي اتكتب في `agent_usage_logs` رغم إن الطلب بلا أي هوية مُصادَق عليها إطلاقًا**، و`user_id=946` (رقم اختاره الطالب بحرية تامة في الـquery string — لاحظ إنه حتى تصادف كونه مستخدم حقيقي **من تينانت مختلف تمامًا (16)**، بلا أي علاقة بالطلب) **اتسجَّل كمصدر الاستهلاك**. **الرد المرجَّع للعميل كان مضلِّلًا (`allowed: false`) بينما الكتابة الفعلية نجحت بالكامل** — أخطر من مجرد IDOR: تسجيل بيانات مزوَّرة تمامًا في نظام تدقيق تينانت حقيقي، بلا أي هوية يمكن تتبعها.

### 3.2 🔴🔴🔴 قراءة إدارية عبر-تينانت — مؤكَّدة DB-level، مطابقة تامة لرد المالك الحقيقي

خطوة 1 (شرعية): `p_aigov_a` (تينانت1 الحقيقي) نادى `POST /agents/127/quotas/reset` بتوكنه الحقيقي بلا أي هيدر → `204`، اتسجَّل `agent_audit_logs id=3` (`action=RESET_QUOTA`).

خطوة 2 (الهجوم): `p_aigov_b` (سوبريوزر **تينانت16 حقيقي**، توكنه الحقيقي) نادى:
```
GET /api/ai-governance/agents/127/audit-logs
Header: Authorization: Bearer <توكن B الحقيقي>
Header: X-Tenant-ID: 1   ← مزوَّر، تينانت B الحقيقي هو 16
```
**الرد:** `200` مع نفس السجل بالحرف:
```json
[{"id":3,"agent_id":127,"admin_user_id":945,"action":"RESET_QUOTA","old_value":null,"new_value":{"current_usage":0},"ip_address":"127.0.0.1","created_at":"2026-08-24T10:16:31.024608Z"}]
```
**مطابق حرفيًا** لما رجع لـ`p_aigov_a` (المالك الحقيقي) عند نفس الاستدعاء بتوكنه هو. **الهيدر المزوَّر هو الفرق الوحيد بين الطلبين — العزل بين التينانتات معدوم تمامًا لهذا المسار.** سجل تدقيق إداري حساس (مين عمل إيه، إمتى، من أنهي IP) لتينانت كامل مكشوف لأي سوبريوزر في أي تينانت آخر بمجرد تغيير هيدر واحد.

### 3.3 🔴🔴🔴 كتابة إدارية عبر-تينانت — مؤكَّدة جزئيًا (وصلت فعليًا لمرحلة INSERT بـ`tenant_id` المزوَّر، قبل ما تصطدم ببج منفصل)

نفس `p_aigov_b` حاول `POST /agents/127/quotas` (`set_agent_quota`) بهيدر `X-Tenant-ID: 1` مزوَّر → `500`. **اللوج يؤكد إن المحاولة وصلت فعليًا لعبارة `INSERT INTO agent_quotas (tenant_id, agent_id, ...) VALUES (1, 127, ...)`** — يعني التينانت المُستخدَم في محاولة الكتابة الفعلية هو **`1` (المزوَّر من هيدر B)**، مش `16` (تينانت B الحقيقي) — **دليل تشغيلي مباشر إضافي إن مسار الكتابة بالكامل يثق بالهيدر بلا استثناء**. فشل الطلب فعليًا بسبب `IntegrityError: null value in column "reset_at"` — **باج schema منفصل تمامًا وpre-existing** (`AgentQuotaCreate` schema لا يحتوي `reset_at`، والعمود `NOT NULL` بلا `server_default`) يمنع أي إنشاء حصة جديدة عبر هذا الـendpoint **لأي تينانت، مش بس المزوَّر** — موثَّق في §3.4، **خارج نطاق IDOR نفسه**.

### 3.4 🟡 باجات pre-existing منفصلة تمامًا، مؤكَّدة حيًا، خارج نطاق IDOR

1. **`_check_agent_ownership` غير معرَّفة → 500 دائمًا:** `p_aigov_a` (المالك الحقيقي، تينانت1، بتوكنه الصحيح بلا أي تزوير) نادى `GET /agents/127/quotas` → **`500 Internal Server Error`**. يؤكد حيًا الاكتشاف الثابت في §1 — الثلاثة endpoints (`get_agent_quotas`, `get_agent_remaining_quotas`, `get_rate_limit`) **معطَّلة بالكامل لأي طلب، بغض النظر عن الهوية أو التينانت** (فشل بأمان، مش IDOR — لكنه يعني إن "الحماية" المفترضة فيهم غير قابلة للتقييم حاليًا لأنها لا تُنفَّذ أصلًا).
2. **`set_agent_quota` مكسورة schema-يًا لأي تينانت** (`reset_at` مفقود من `AgentQuotaCreate`/الاستدعاء، `NOT NULL` بلا افتراضي) — راجع §3.3. **لا علاقة بـIDOR، لا يُلمَس هنا.**
3. **`router.check_and_consume` — تناقض نوع الإرجاع:** `service.check_and_consume` توقيعها `-> bool` وترجع `True`/`False` فعليًا، لكن الراوتر يتعامل مع الناتج كـ`dict` (`result["allowed"]`) → `TypeError` مُلتقَط داخل `try/except` عام في الراوتر نفسه فيترجم لرد **مضلِّل** (`"allowed": false` حتى لو الاستهلاك الحقيقي نجح فعلًا، كما أثبت §3.1). **هذا الباج تحديدًا يستاهل رفع أولوية** — لأنه يخفي نجاح كتابة غير مصرَّح بها (§3.1) وراء رسالة فشل ظاهرية، لكنه من ناحية "الفئة" مختلف تمامًا عن IDOR (باج نوع بيانات/عقد استدعاء، لا علاقة بمصدر tenant_id).
4. **ملاحظة غير مؤكَّدة بعمق (مش IDOR، هامشية):** `get_usage_summary` رجع أصفار (`total_requests:0`) حتى وقت وجود سجل مطابق فعليًا في `agent_usage_logs` (id=58، نفس `tenant_id`/`agent_id`، خلال نافذة الـ30 يوم). لم يُحقَّق السبب الجذري (على الأرجح تعامل `datetime.utcnow()` الساذج/aware مقابل `timestamptz` في `.between()`) — **خارج نطاق هذه الجلسة، موثَّق للإشارة فقط.**

### تنظيف بيانات throwaway — مكتمل، مؤكَّد مستقل

`agent_usage_logs`(1)، `agent_audit_logs`(1)، `ai_agents`(1، id=127)، `users`(2، id=945/946) — كل الأربعة `SELECT COUNT` مستقلة بعد الحذف = **صفر**. السيرفر التجريبي أُوقف، البورت 8000 مؤكَّد فاضي.

---

## 4) الخلاصة والتصنيف النهائي

| # | الاكتشاف | الخطورة | مؤكَّد حيًا؟ |
|---|---|---|---|
| 1 | كل الـ9 endpoint: `tenant_id` مصدره `X-Tenant-ID` هيدر (`get_current_tenant`/`SimpleTenant`)، صفر ربط بـ`current_user.tenant_id` | 🔴🔴🔴 IDOR عبر-تينانت جذري، النمط الكلاسيكي نفسه المُصلَح سابقًا في 4 دومينات أخرى | ✅ (قراءة `security.py` + §3.2/3.3) |
| 2 | `check-and-consume`: بلا `current_user` إطلاقًا — كتابة حقيقية بلا أي مصادقة | 🔴🔴🔴🔴 **الأخطر — أعلى من أي IDOR اكتُشف في السويپ حتى الآن (لا يحتاج حتى هوية مزوَّرة، فقط طلب مجهول)** | ✅ (§3.1، صف DB حقيقي) |
| 3 | `_check_agent_ownership` غير معرَّفة | 🟡 كراش وظيفي (500 دائمًا)، pre-existing، خارج IDOR | ✅ (§3.4.1) |
| 4 | `set_agent_quota` — `reset_at` NOT NULL بلا مصدر | 🟡 pre-existing، خارج IDOR | ✅ (§3.3/3.4.2) |
| 5 | `check_and_consume` router — bool مُعامَل كـdict | 🟠 يخفي نجاح كتابة غير مصرَّح بها وراء رد مضلِّل — يستاهل إصلاح مصاحب لبند #2 | ✅ (§3.1/3.4.3) |
| 6 | `get_usage_summary` يرجع أصفار رغم بيانات مطابقة | ⚪ غير محقَّق بعمق، هامشي | جزئي |

### الحلول المقترَحة (معروضة فقط — صفر تنفيذ)

**1) الإصلاح الجذري (يغلق #1 بالكامل):** استبدال `tenant: AcademyTenant = Depends(get_current_tenant)` بـ`current_user: User = Depends(get_current_superuser)` (أو `get_current_active_user` حسب مستوى كل endpoint الحالي) + `tenant_id = cast(int, current_user.tenant_id)` — **نفس النمط الميكانيكي بالحرف المُطبَّق في `academy`/`commerce`/`saas`/`sovereign_entities`** (جلسة `simpletenant-fix`). يمس 8 من الـ9 endpoint (كلهم عدا `check-and-consume` نفسها).

**2) `check-and-consume` (الأخطر، #2):** يحتاج قرارًا تصميميًا صريحًا منك قبل أي ديف — هل هذا الـendpoint **مفروض يكون داخليًا فقط** (يُستدعى من دومينات أخرى backend-to-backend، وبالتالي يحتاج مصادقة خدمة/API key بدل مستخدم نهائي)، أم **مفروض مستخدم نهائي مسجَّل** (وبالتالي `current_user` + `tenant_id = current_user.tenant_id` زي باقي الملف)؟ الفرق يغيّر شكل الإصلاح جذريًا. **لا اقتراح إصلاح واحد بلا توجيهك.**

**3) `router.check_and_consume` نوع الإرجاع (#5):** تصحيح التعامل مع الناتج — إما تغيير `service.check_and_consume` لترجع `dict` (`{"allowed": bool, "idempotent": bool}`) بدل `bool` خام (يمس `check_and_consume` نفسها — **قد يتقاطع مع بند `ai-governance-quota-result-ignored` الموثَّق مسبقًا في `PROGRESS_LOG.md`**)، أو تصحيح الراوتر ليتعامل مع `bool` مباشرة (`{"allowed": result}`). **يُفضَّل تأجيله لجلسة إصلاح `check_and_consume` المخصَّصة (نفس البند الموثَّق مسبقًا)، لا يُلمَس هنا كجزء من IDOR.**

**4) `_check_agent_ownership` (#3) و`reset_at` (#4):** Backlog فقط — pre-existing، خارج نطاق IDOR بالكامل، نفس نمط الجلسات السابقة.

---

## 5) قرار المستخدم [2026-08-24]

1. ✅ الإصلاح الجذري (#1) — موافقة على تنفيذه على الـ8 endpoints.
2. ✅ `check-and-consume` (#2) — **نفس نمط الـ8 الباقيين بالضبط** (`current_user` + `tenant_id` من التوكن). السبب: المسار الداخلي الحقيقي من الدومينات الأخرى يستدعي `AIGovernanceService.check_and_consume()` مباشرة (in-process)، **مش عبر HTTP** — فمفيش داعٍ لاستثناء الـendpoint من الحماية الأساسية. أي حاجة لوصول خدمة-لخدمة حقيقي عبر HTTP مستقبلًا = قرار تصميمي منفصل لاحق (API key/mTLS)، خارج نطاق هذه الجلسة.
3. ✅ `router.check_and_consume` نوع الإرجاع (#5) — مؤجَّل لجلسة `check_and_consume` المخصَّصة.
4. ✅ باجات pre-existing (#3, #4, #6) — Backlog فقط.

**توجيه إضافي:** تحديث `critical-finding-xtenant-systemic.md` **قبل** التنفيذ بتصنيف `check-and-consume` كأعلى خطورة موثَّقة في السويپ حتى الآن (فوق `ai_agents`) — ✅ تم (بانر جديد مضاف أعلى الملف + تحديث صف #5 في الجدول، راجع الملف مباشرة). تحقق حي بعد الإصلاح لنفس الأربعة سيناريوهات، خصوصًا `check-and-consume` بطلب مجهول تمامًا (لازم يرجع `401`).

---

## 6) التنفيذ — مكتمل، مؤكَّد حيًا بالكامل

### 6.1 الديف المُطبَّق — ملف واحد فقط (`router.py`)، نفس النمط الميكانيكي على الـ9 endpoints

لكل endpoint: حذف `tenant: AcademyTenant = Depends(get_current_tenant)` من التوقيع، إضافة `tenant_id = cast(int, current_user.tenant_id)` كأول سطر في الجسم، استبدال `cast(int, tenant.id)` بـ`tenant_id` في بناء `AIGovernanceService`. الاستثناء الوحيد: `check_and_consume` (كانت بلا `current_user` إطلاقًا) — أُضيف `current_user: User = Depends(get_current_active_user)` (نفس مستوى القراءة الأدنى في باقي الملف، بما إن `check_and_consume` عملية استهلاك/تسجيل وليست إدارية بحتة).

إزالة `get_current_tenant` من استيراد `app.api.deps`، وإزالة `AcademyTenant`/استيرادها من `app.domains.academy.models` بالكامل (غير مُستخدَمة بعد الإصلاح). `py_compile` → `exit code 0`. صفر import جديد غير مُستخدَم.

### 6.2 إعادة تشغيل uvicorn

تأكيد فعلي إن البورت 8000 فاضي قبل التشغيل، تشغيل نظيف (`PYTHONIOENCODING=utf-8`)، لوج إقلاع نظيف تمامًا (`Application startup complete`، صفر `Traceback`).

### 6.3 التحقق الحي بعد الإصلاح — بيانات throwaway جديدة (بادئة `p_aigov2_*`)، نفس الأربعة سيناريوهات بالضبط

**الإعداد:** وكيل throwaway جديد `P_AIGOV2_AGENT_A` (`ai_agents id=128`، تينانت1، عبر الـAPI الحقيقي)، `p_aigov2_a`(id=947، سوبريوزر تينانت1 حقيقي)، `p_aigov2_b`(id=948، سوبريوزر تينانت16 حقيقي).

| # | السيناريو | قبل الإصلاح (§3) | بعد الإصلاح |
|---|---|---|---|
| 1 | **`check-and-consume` بلا أي `Authorization` إطلاقًا** (`X-Tenant-ID: 1`، `user_id=948` عشوائي) | `200 {"allowed":false,"error":"'bool' object is not subscriptable"}` **+ صف حقيقي مكتوب في DB** | **`401 {"detail":"Not authenticated"}`** — تحقق DB مستقل: `agent_usage_logs` لـ`agent_id=128` = **صفر صف** |
| 1s | Sanity: A (توكن حقيقي، تينانت1) ينادي نفس الـendpoint على وكيله | — | `200` (نفس باج bool/dict المؤجَّل §3.4.3، غير متعلق بالمصادقة) — **تحقق DB: صف مكتوب صح، `tenant_id=1, agent_id=128, user_id=947`** ✅ المسار الشرعي سليم |
| 2 | **قراءة إدارية عبر-تينانت**: B (سوبريوزر تينانت16 حقيقي) يقرأ `GET /agents/128/audit-logs` بهيدر `X-Tenant-ID: 1` مزوَّر | `200` + نفس سجل A بالحرف | **`200 []`** — الهيدر المزوَّر بلا أي تأثير، B شاف بيانات تينانته الحقيقي (فاضية) بس |
| 2s | Sanity: A يقرأ نفس الـendpoint بتوكنه الحقيقي | — | `200` مع السجل الحقيقي (`RESET_QUOTA`, `admin_user_id=947`) — ✅ المالك لسه يشوف بياناته |
| 3 | **كتابة إدارية عبر-تينانت**: B يحاول `POST /agents/128/quotas` بهيدر `X-Tenant-ID: 1` مزوَّر | وصلت فعليًا لـ`INSERT ... tenant_id=1` (المزوَّر) | **اللوج يؤكد: `INSERT ... tenant_id=16` (تينانت B الحقيقي من التوكن، الهيدر تجاهُل تام)** — فشلت لاحقًا بنفس باج `reset_at` pre-existing غير المتعلق (§3.4.2)، **لأي تينانت وليس بسبب التزوير** |

**✅ حاسم:** الأربعة سيناريوهات اللي أثبتت الثغرة قبل الإصلاح **مرفوضة/محايَدة الآن بالكامل** (الهيدر المزوَّر بلا أي تأثير في كل الحالات)، والمسارات الشرعية (A على بياناته الحقيقية) سليمة 100%.

### 6.4 تنظيف بيانات throwaway — مكتمل، مؤكَّد مستقل

`agent_usage_logs`(1)، `agent_audit_logs`(1)، `ai_agents`(1، id=128)، `users`(2، id=947/948) — `SELECT COUNT` مستقل بعد الحذف = **صفر في الأربعة**. السيرفر التجريبي أُوقف، البورت 8000 مؤكَّد فاضي.

---

## 7) بند Backlog — تنويه في `PROGRESS_LOG.md` (لو رغبت لاحقًا)

الثلاثة بنود pre-existing المؤجَّلة صراحة (§3.4، خارج نطاق هذه الجلسة تمامًا): `ai-governance-check-agent-ownership-undefined` (كراش 500 دائم لـ3 endpoints)، `ai-governance-set-quota-reset-at-missing` (يمنع إنشاء أي حصة جديدة، أي تينانت)، `ai-governance-check-and-consume-bool-vs-dict-response` (يخفي نجاح/فشل الاستهلاك الحقيقي وراء رد مضلِّل — **الأولوية الأعلى بين الثلاثة**، لأنه يتقاطع مباشرة مع خطورة #2 المُصلَحة اليوم). **لم تُضَف بعد لـ`PROGRESS_LOG.md` — بانتظار توجيهك: نفس نمط الجلسات السابقة (سطر جديد لكل بند) أم دمجهم في سطر واحد؟**

---

## 8) `git status` / `git diff --stat` — للمراجعة قبل أي commit

**الملفات التي عدّلتها هذه الجلسة:**
```
M eppne-backend/app/domains/ai_governance/router.py
M .claude/plans/critical-finding-xtenant-systemic.md
?? .claude/reports/ai-governance-idor-fix-session-log.md       (جديد، هذا الملف)
```

**باقي الملفات الظاهرة في `git status` من جلسات/أعمال سابقة غير متعلقة بهذه الجلسة إطلاقًا** — لم تُلمس، لن تُضاف لأي commit من هنا.

**الحالة النهائية:** ✅ **الإصلاح مُطبَّق على الـ9 endpoints، مؤكَّد حيًا (4 سيناريوهات هجوم مرفوضة + مسارات شرعية سليمة)، بيانات throwaway منضَّفة بالكامل.** ⏳ **لم يُنفَّذ commit بعد** — بانتظار موافقتك الصريحة على الـ`diff`.
