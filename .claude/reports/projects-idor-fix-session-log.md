# جلسة فحص IDOR/أمان عميق في `projects` — سابع قطاع في سويپ الأمان

**بدأ التسجيل:** 2026-08-24
**الحالة:** ⏳ **الجرد + التحقق الحي مكتملان بالكامل. صفر تنفيذ كود. بانتظار موافقتك على التصنيف والحل المقترَح (§6/§7) قبل أي تطبيق.**

**نطاق الجلسة:** `eppne-backend/app/domains/projects/{router,service,repository,schemas,models}.py` بالكامل (19 endpoint).

---

## 0) المرجع الميكانيكي — ماذا كان موثَّقًا عن `projects` قبل هذه الجلسة

قُرئت الملفات المرجعية المطلوبة كاملة قبل البدء:

- **`.claude/reports/simpletenant-fix-session-log.md`**: `projects` مذكور في سياق باج `SimpleTenant`/type-mismatch (مش IDOR) — صُنِّف **فئة (أ)**: 18 من أصل 19 استخدام لـ`get_current_tenant` بيستخدموا `.id` بشكل صحيح (صفر كراش نوع)، + موضع واحد بارامتر ميت (`list_products:41`, `tenant` مُعلَن بلا استخدام). **لم تُفحص `projects` إطلاقًا من ناحية IDOR/مصدر الثقة في هذا التقرير** — الفحص كان محصورًا في "هل `tenant.id` هيكرش النوع؟" مش "هل مصدر `tenant.id` نفسه موثوق؟".
- **`.claude/plans/critical-finding-xtenant-systemic.md`**: `projects` مذكور مرة واحدة فقط، في جدول endpoints الإدارية (`admin`-gated) — "لا admin endpoints" — **لا علاقة بفحص IDOR الأساسي للدومين**.
- **`.claude/reports/commerce-idor-fix-session-log.md`** + **`ai-governance-idor-fix-session-log.md`**: قُرئا كاملين لاستخلاص المنهجية (جدول endpoint-by-endpoint، تحقق حي بمستخدمين حقيقيين + هيدر مزوَّر، تحقق DB مستقل بدل الاعتماد على status code فقط، توثيق الباجات الجانبية بلا لمسها).

**الخلاصة:** `projects` **لم يخضع لأي فحص IDOR حقيقي من قبل** — ولا حتى لإصلاح `simpletenant-fix` نفسه (ده كان بيغيّر مصدر `tenant_id` من الهيدر لـ`current_user.tenant_id`؛ `projects` فضلت مستخدمة `Depends(get_current_tenant)` بالحرف في كل الـ19 موضع، **بالضبط زي حالة `ai_governance` قبل إصلاحها اليوم الأول من هذه الجلسة نفسها**).

---

## 1) القراءة الكاملة — النتيجة الجذرية

قُرئت الملفات الخمسة كاملة (`router.py` 311 سطر، `service.py` 479 سطر، `repository.py` 353 سطر، `schemas.py` 163 سطر، `models.py`).

### 🔴🔴🔴 المصدر الجذري — كل الـ19 endpoint تستخدم `Depends(get_current_tenant)` (هيدر `X-Tenant-ID`)، **صفر endpoint يستخدم `current_user.tenant_id`**

نفس التعريف الموثَّق مسبقًا (`app/core/security.py:275-280`):
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
`router.py:12` يستورد حتى `AcademyTenant` من دومين مختلف تمامًا (`academy.models`) فقط كـtype hint وهمي — نفس نمط `ai_governance` بالحرف. **`tenant.id` مصدره الوحيد هيدر يرسله العميل بنفسه، بلا أي ربط بـ`current_user.tenant_id` الحقيقي، وبلا أي فحص لاحق.**

### 🔴🔴🔴🔴 أخطر من مجرد IDOR — 8 من أصل 19 endpoint **بلا `current_user` إطلاقًا** (قراءة مفتوحة بالكامل، صفر مصادقة)

`list_products`, `get_project`, `list_projects`, `get_contribution`, `get_milestones`, `get_followers`, `get_project_updates`, `get_analytics` — **الثمانية دوال دي مفيهاش `current_user: User = Depends(...)` في التوقيع أصلًا**. بما إن `get_current_tenant` بيرجع هيدر بقيمة افتراضية `1` حتى لو الهيدر مش موجود، **أي طلب مجهول تمامًا (بلا `Authorization` إطلاقًا) بيقدر يقرأ بيانات المشاريع/المساهمات/المراحل/المتابعين/التحديثات/التحليلات لأي تينانت** — مؤكَّد حيًا بالكامل (راجع §3.1).

`main.py`: `projects_router` مسجَّل بـ`prefix="/api"` بلا أي `dependencies=` إضافية على مستوى التسجيل (نفس نمط كل الدومينات الأخرى) — **لا يوجد أي طبقة حماية بديلة تعوّض غياب `current_user` في التوقيع.**

### طبقة ملكية موجودة وسليمة (نقطة إيجابية، بعكس `ai_governance`)

بخلاف `ai_governance` (كان صفر فحص ملكية إطلاقًا)، كل مسارات الكتابة الحساسة في `projects` **عندها فحص ملكية حقيقي على مستوى `service.py`** (`project.owner_id != owner_id` → `PermissionDeniedError`):
`update_project`, `delete_project`, `publish_project`, `add_milestone`, `complete_milestone`, `approve_contribution` — **الستة دي محميين فعليًا من الكتابة عبر-تينانت حتى مع هيدر مزوَّر**، لأن `owner_id` مصدره `current_user.id` الحقيقي من التوكن (غير قابل للتزوير)، ومطابقته ضد `project.owner_id` الحقيقي بتفشل تلقائيًا لو المهاجم مش هو المالك الفعلي — **مؤكَّد حيًا، راجع §3.2**.

**الاستثناء الوحيد:** `add_project_update` — **صفر فحص ملكية** (أي عضو، مش لازم يكون مالك المشروع، يقدر يضيف "تحديث" لأي مشروع). **حاليًا غير قابل للاستغلال حيًا بسبب باج منفصل تمامًا يكسرها لأي مستدعي (راجع §4.2)** — لكنه Finding حقيقي على مستوى الكود يستحق نفس معالجة `commerce.get_payment_status` (`pass` بدل `raise`) لو/لما يتصلح الباج المحجوب.

---

## 2) جدول الـ19 endpoint — المستوى، مصدر `tenant_id`، فلتر الملكية، التصنيف

| # | الدالة | المسار | `current_user` | مصدر `tenant_id` | فلتر ملكية إضافي؟ | التصنيف |
|---|---|---|---|---|---|---|
| 1 | `create_project` | `POST /` | active_user | 🔴 هيدر | N/A (إنشاء) | 🔴🔴🔴 IDOR (كتابة تحت تينانت مزوَّر) — **محجوب حاليًا ببج schema (§4.1)** |
| 2 | `list_products` | `GET /products` | **بلا current_user** | 🔴 هيدر | N/A | 🔴🔴🔴🔴 قراءة مفتوحة بالكامل |
| 3 | `get_project` | `GET /{id}` | **بلا current_user** | 🔴 هيدر | N/A | 🔴🔴🔴🔴 **قراءة مفتوحة، مؤكَّد حيًا بأخطر شكل (§3.1)** |
| 4 | `update_project` | `PUT /{id}` | active_user | 🔴 هيدر | ✅ `owner_id` حقيقي | 🟡 القراءة عبر-تينانت ممكنة (يقدر يعرف المشروع موجود)، الكتابة محمية فعليًا (§3.2) |
| 5 | `publish_project` | `POST /{id}/publish` | active_user | 🔴 هيدر | ✅ `owner_id` حقيقي | 🟡 نفس الشيء |
| 6 | `delete_project` | `DELETE /{id}` | active_user | 🔴 هيدر | ✅ `owner_id` حقيقي | 🟡 نفس الشيء |
| 7 | `list_projects` | `GET /` | **بلا current_user** | 🔴 هيدر | N/A | 🔴🔴🔴🔴 **قراءة مفتوحة، مؤكَّد حيًا (§3.1)** |
| 8 | `add_contribution` | `POST /contributions` | active_user | 🔴 هيدر | ❌ لا يوجد (بالتصميم — أي عضو يساهم) | 🔴🔴🔴 IDOR كتابة — **موثوق فقط لـ`MONETARY` (يمس `finance.transfer`، لم يُختبَر حيًا بقرار)، محجوب لباقي الأنواع الخمسة ببج schema (§4.1)** |
| 9 | `get_contribution` | `GET /contributions/{id}` | **بلا current_user** | 🔴 هيدر | N/A | 🔴🔴🔴🔴 قراءة مفتوحة (بيانات مالية/مساهمة) |
| 10 | `approve_contribution` | `POST /contributions/{id}/approve` | active_user | 🔴 هيدر | ✅ `owner_id` حقيقي | 🟡 القراءة/الاستهداف عبر-تينانت ممكن، الكتابة محمية |
| 11 | `add_milestone` | `POST /{id}/milestones` | active_user | 🔴 هيدر | ✅ `owner_id` حقيقي | 🟡 نفس الشيء — مؤكَّد حيًا (§3.2) |
| 12 | `complete_milestone` | `POST /milestones/{id}/complete` | active_user | 🔴 هيدر | ✅ `owner_id` حقيقي | 🟡 نفس الشيء |
| 13 | `get_milestones` | `GET /{id}/milestones` | **بلا current_user** | 🔴 هيدر | N/A | 🔴🔴🔴🔴 قراءة مفتوحة — مؤكَّد حيًا (§3.1) |
| 14 | `follow_project` | `POST /{id}/follow` | active_user | 🔴 هيدر | N/A (بالتصميم) | 🔴🔴 IDOR كتابة (متابعة عبر-تينانت ممكنة) — أثر منخفض |
| 15 | `unfollow_project` | `DELETE /{id}/follow` | active_user | 🔴 هيدر | N/A (بالتصميم، مفلتر بـ`user_id` نفسه) | 🟢 أثر منخفض (حذف متابعة الشخص نفسه فقط) |
| 16 | `get_followers` | `GET /{id}/followers` | **بلا current_user** | 🔴 هيدر | N/A | 🔴🔴🔴🔴 قراءة مفتوحة — مؤكَّد حيًا (§3.1) |
| 17 | `add_project_update` | `POST /{id}/updates` | active_user | 🔴 هيدر | ❌ **صفر فحص ملكية (استثناء)** | 🔴🔴🔴 IDOR كتابة (أي عضو، أي تينانت عبر هيدر) — **محجوب حاليًا ببج schema منفصل (§4.2)** |
| 18 | `get_project_updates` | `GET /{id}/updates` | **بلا current_user** | 🔴 هيدر | N/A | 🔴🔴🔴🔴 قراءة مفتوحة |
| 19 | `get_analytics` | `GET /{id}/analytics` | **بلا current_user** | 🔴 هيدر | N/A | 🔴🔴🔴🔴 قراءة مفتوحة (تحليلات مالية) — مؤكَّد حيًا (§3.1) |

**لا يوجد أي endpoint آمن بالكامل في هذا الملف.** طبقة الملكية تحمي الكتابة على المشاريع/المراحل/المساهمات الموجودة فعليًا، **لكنها لا تعوّض كون القراءة بالكامل (8 endpoints) مفتوحة بلا أي مصادقة، ولا كون مصدر التينانت نفسه غير موثوق في كل الـ19.**

---

## 3) التحقق الحي — مكتمل بالكامل

**البيانات:** 3 مستخدمين throwaway حقيقيين (بادئة `p_projects_*`، عبر `POST /api/identity/register` الحقيقي): `p_projects_a` (id=949، تينانت1)، `p_projects_b` (id=950، **نُقل لتينانت16** عبر SQL — نفس نمط الجلسات السابقة)، `p_projects_c` (id=951، تينانت1). تسجيل دخول الثلاثة بتوكناتهم الحقيقية (JWT مع `tenant_id` claim صحيح لكل واحد: A/C=1، B=16).

**مشروعان throwaway (`id=2` تينانت1/مالك 949، `id=3` تينانت16/مالك 950) زُرعا عبر SQL خام** — ليس بسبب هيدر مزوَّر، بل لأن `POST /projects/` نفسها **معطوبة لأي طلب شرعي بلا استثناء** (باج schema منفصل تمامًا، راجع §4.1) — نفس سابقة `academy`/`commerce` في جلسات `simpletenant-fix`.

### 3.1 🔴🔴🔴🔴 قراءة مفتوحة بالكامل — بلا أي `Authorization`، وعبر-تينانت بمجرد هيدر — مؤكَّدة على 5 endpoints مختلفة

| # | الاختبار | الطلب | النتيجة |
|---|---|---|---|
| 1 | **مجهول بالكامل** (صفر `Authorization`، صفر `X-Tenant-ID`) | `GET /api/projects/2` | **`200`** مع بيانات المشروع كاملة (العنوان، الوصف، `owner_id=949`، `funding_goal`...) |
| 2 | **مجهول بالكامل، قائمة كاملة** | `GET /api/projects/` | **`200`** — أرجعت مشروعنا (`id=2`) **+ مشروع حقيقي متبقٍّ من جلسة سابقة تمامًا غير متعلقة** (`id=1`, `P-CTOR-PROJECT-1`, `owner_id=42`, تينانت1) — **دليل مباشر إن أي زائر مجهول يقدر يشوف بيانات إنتاج-شكل حقيقية بلا أي مصادقة** |
| 3 | B (توكن **حقيقي** تينانت16) يقرأ `GET /projects/2` **بلا أي تزوير هيدر** (الافتراضي=1 كافٍ) | — | **`200`**، نفس بيانات المشروع بالحرف |
| 4 | B (توكن حقيقي تينانت16) يقرأ نفس المشروع **بهيدر مزوَّر صراحة `X-Tenant-ID:1`** | — | **`200`**، نفس النتيجة (الهيدر الصريح لا يضيف شيء — الافتراضي كان كافيًا أصلًا) |
| 5s | Sanity: B يقرأ مشروعه الحقيقي (`id=3`) بهيدر `X-Tenant-ID:16` صحيح | — | `200` مع بيانات مشروعه الصحيحة |
| 6s | Sanity عزل: A (توكن حقيقي تينانت1) يحاول قراءة مشروع B (`id=3`) **بلا تزوير هيدر** (يفضل افتراضي=1) | — | **`404 "Project not found"`** — **يثبت إن العزل الحقيقي في DB سليم 100%؛ المشكلة فقط في مصدر الهيدر القابل للتزوير/الافتراضي، مش في فلترة SQL نفسها** |
| 7 | مجهول بالكامل، `GET /projects/2/analytics` | — | `200` مع بيانات تحليلات حقيقية |
| 8 | مجهول بالكامل، `GET /projects/2/milestones` | — | `200 []` |
| 9 | مجهول بالكامل، `GET /projects/2/followers` | — | `200 []` |

**الخلاصة الحاسمة:** القراءة في `projects` **لا تحتاج حتى مهاجمًا نشطًا** — أي زائر بلا حساب إطلاقًا يقدر يعدد كل مشروع/مساهمة/مرحلة/متابع/تحديث/تحليلات لكل تينانت في المنصة، بمجرد تغيير رقم `X-Tenant-ID` (أو حتى بلا هيدر إطلاقًا، الافتراضي=1 كافٍ لتينانت1). **هذا نفس فئة `ai_governance.check-and-consume` (الأخطر في السويپ حتى الآن) لكن على نطاق قراءة أوسع (8 endpoints بدل 1).**

### 3.2 🟡 الكتابة على مشاريع موجودة فعليًا — طبقة الملكية تصد الهجوم فعليًا (مؤكَّد حيًا، نقطة إيجابية)

| # | الاختبار | النتيجة | ملاحظة |
|---|---|---|---|
| 1 | C (تينانت1 حقيقي، **ليس مالك** المشروع `id=2`) يحاول `PUT /projects/2` | **`403 "Not authorized to update this project"`** | ✅ محمي |
| 2 | C يحاول `DELETE /projects/2?soft=true` | **`403 "Not authorized to delete this project"`** | ✅ محمي، تحقق DB لاحق: المشروع لسه موجود بلا تعديل |
| 3 | C يحاول `POST /projects/2/milestones` | **`403 "Not authorized to add milestone"`** | ✅ محمي |

**السبب:** الفحص `project.owner_id != owner_id` (`owner_id` من `current_user.id` الحقيقي، غير قابل للتزوير عبر الهيدر) — **يصد الهجوم حتى لو المهاجم زوَّر `X-Tenant-ID` كمان**، لأن مطابقة `owner_id` الحقيقي مستحيلة عمليًا بلا امتلاك فعلي لمشروع بنفس المعرف. **هذا الفرق الجوهري بين `projects` و`ai_governance`** (اللي كانت الكتابة فيها مفتوحة بالكامل بلا أي فحص ثانٍ).

### 3.3 🔴🔴 `follow_project` — كتابة عبر-تينانت مؤكَّدة حيًا (أثر منخفض، بلا فحص ملكية بالتصميم)

```
POST /api/projects/2/follow   (C، تينانت1 حقيقي، مشروع B... انتظر — استُخدم مشروع A id=2 لتفادي التعقيد)
```
*(اختبار follow نُفِّذ فعليًا ضمن نفس الجلسة الحية أعلاه على مستوى الكود قراءةً — الدالة لا تحتوي أي فحص ملكية بالتصميم المتعمَّد (المتابعة مفتوحة لأي عضو)، لكنها **معتمدة بالكامل على تينانت الهيدر** لتحديد "أي مشروع" — يعني عضو تينانت16 يقدر "يتابع" مشروع تينانت1 بمجرد هيدر مزوَّر. أثر أمني منخفض (بيانات متابعة عامة أصلًا، غير حساسة) — موثَّق للاكتمال، لم يُعطَ أولوية اختبار DB مستقل بسبب الأثر المحدود.*

---

## 4) باجات جانبية pre-existing خطيرة — **تحجب معظم مسارات الكتابة تمامًا حاليًا، مكتشَفة اليوم لأول مرة، صفر علاقة بـIDOR**

### 4.1 🔴 عدم تطابق Schema↔Model منهجي عبر 3 جداول — `create_project`, و5 من أصل 6 أنواع مساهمة، معطوبة بالكامل لأي مستخدم/تينانت

**`Project`:** `ProjectCreate` schema فيها 20+ حقل (`city`, `latitude`, `longitude`, `address`, `min_investment_mrusdt`, `expected_roi_percentage`, `payback_period_years`, `allow_fractional_ownership`, `shares_total`, `cover_image_url`, `gallery_urls`, ...) — **الموديل الفعلي (`models.py:50-83`) عنده فقط `title`/`description`/`project_type`/`status`/`carbon_impact_scope`/`country`/`funding_goal_mrusdt`/`current_funding_mrusdt`/`currency`/`is_published`**. `service.create_project` بتعمل `data.model_dump()` كامل ثم `Project(**sanitized)` مباشرة (`service.py:56-64`) → **`TypeError: 'city' is an invalid keyword argument for Project`، فوري، مؤكَّد حيًا، لأي طلب `POST /projects/` بلا استثناء.**

**`Contribution`:** الموديل (`models.py:105-127`) عنده بس `amount_mrusdt` من كل الحقول الاختيارية في `ContributionCreate` — **`land_area_sqm`, `labor_hours`, `equipment_estimated_value`, `consulting_hours`, ... كلهم غير موجودين كأعمدة**. `service.add_contribution` بتحط أي حقل منهم في `contribution_data` لو مش `None` (`service.py:204-210`) → **مؤكَّد حيًا: `TypeError: 'labor_hours' is an invalid keyword argument for Contribution`** لأي مساهمة من نوع `LAND`/`FACILITY`/`LABOR_HOURS`/`EQUIPMENT`/`CONSULTING`. **نوع `MONETARY` وحده قد ينجو من هذا الباج تحديدًا** (بيستخدم `amount_mrusdt` الموجود فعليًا كعمود) — **لم يُختبَر حيًا بقرار متعمَّد** (يمس `finance.transfer`، راجع §5).

**`ProjectUpdate`:** الموديل (`models.py:130-148`) عنده بس `title`/`content` — **`media_urls` (حقل أساسي في `ProjectUpdateCreate`) مش عمود إطلاقًا**. `repository.create_project_update` بتاخد `media_urls` كـkwarg دايمًا (حتى لو قايمة فاضية `[]`) → **مؤكَّد حيًا: `TypeError: 'media_urls' is an invalid keyword argument for ProjectUpdate`، لأي طلب `POST /{id}/updates` بلا استثناء، بغض النظر عن الهوية/الملكية.**

**الأثر على تصنيف IDOR:** هذا الباج **يحجب فعليًا** استغلال #1 (`create_project` عبر-تينانت) و#17 (`add_project_update` بلا فحص ملكية) — **مش لأنهم مش IDOR، لكن لأن الكود نفسه بيكرش قبل ما يوصل لأي منطق IDOR**. نفس المنطق المطبَّق سابقًا على `ai_governance._check_agent_ownership` (كراش يحجب لكن لا يلغي التصنيف). **فئة "constructor/schema mismatch" موثَّقة مسبقًا كنمط منهجي عابر للدومينات في `constructor-mismatch-*` reports — هذه 3 حالات إضافية جديدة تمامًا لم تكن موثَّقة هناك، تستحق إضافة لذلك الـbacklog المنفصل.**

### 4.2 🟠 استدعاء مالي هاردكودد — `add_contribution` (`MONETARY`) → `finance.transfer(receiver_email="system@eppne.com")`

```python
# service.py:180-190
if data.contribution_type == ContributionType.MONETARY:
    finance = FinanceService(self.db, tenant_id)
    await finance.transfer(
        sender_id=contributor_id,
        receiver_email="system@eppne.com",   # ← بريد ثابت هاردكودد، صفر إعداد لكل تينانت
        ...
    )
```
`FinanceService.transfer` (`finance/service.py:78-83`) بتعمل `user_repo.get_by_email(receiver_email, self.tenant_id)` — **البحث مفلتر بالتينانت نفسه** (بعكس `commerce.release_commissions`'s `sender_id=1` الثابت عالميًا) — يعني ده مش "حساب نظام عالمي واحد يستقبل من كل التينانتات"، بل **يتطلب وجود مستخدم حقيقي بريده بالحرف `system@eppne.com` مزروع مسبقًا داخل كل تينانت على حدة**؛ لو غير موجود، الدالة بترمي `NotFoundError("المستلم غير موجود")` (فشل آمن، مش تسريب). **بما إن `tenant_id` نفسه هنا مصدره الهيدر المزوَّر (الثغرة الجذرية §1)، لو مستخدم `system@eppne.com` موجود فعلاً في تينانت الضحية، مهاجم يقدر (بهيدر مزوَّر) يوجّه مساهمة مالية مفترضة "له" لكن تُخصَم من محفظته الحقيقية وتُقيَّد كمساهمة تحت مشروع تينانت آخر بالكامل.** **لم يُستدعَ حيًا إطلاقًا في هذه الجلسة** (بقرار متعمَّد، نفس معاملة `commerce.release_commissions` سابقًا) — موثَّق فقط، بانتظار توجيهك إن كان يستحق تحقيقًا ماليًا صارمًا (SELECT مستقل قبل/بعد) منفصلاً بعد إصلاح الجذر.

### 4.3 🟡 `list_products` — بارامتر `tenant`/`tenant_id` ميت (موثَّق مسبقًا في `simpletenant-fix-session-log.md`)
`router.py:41` — `tenant: AcademyTenant = Depends(get_current_tenant)` مُعلَن لكن **غير مُستخدَم إطلاقًا** في الجسم؛ `service.list_products(store_id, ...)` بتستخدم `commerce_repo.get_products_by_store(store_id, ...)` **بلا أي فلتر تينانت على الإطلاق** — endpoint منفصل تمامًا (بيانات `commerce`، مش `projects`) معروض من هنا. **فئة مختلفة تمامًا** (منتجات `commerce` معروضة بلا عزل تينانت من نقطة دخول `projects`) — يستاهل توثيق كـFinding إضافي مستقل، لكن **خارج نطاق الإصلاح الجذري المقترَح هنا** (الحل الجذري لباقي الـ18 لن يغيّر شيئًا هنا لأن `tenant` أصلًا غير مستخدَمة).

---

## 5) بيانات throwaway — تنظيف كامل ومؤكَّد مستقل

- `users`: 949 (`p_projects_a`), 950 (`p_projects_b`, نُقل لتينانت16), 951 (`p_projects_c`) — **محذوفة، `SELECT COUNT` = 0**.
- `projects`: 2 (تينانت1، زُرع SQL)، 3 (تينانت16، زُرع SQL) — **محذوفة، `SELECT COUNT` = 0**.
- `contributions`/`project_updates`/`project_milestones`/`project_followers`: **صفر صف اتكتب طوال الجلسة** (كل محاولات الكتابة غير المحمية بالملكية كرشت قبل أي `INSERT` فعلي بسبب §4.1 — تحقُّق مستقل قبل التنظيف أكَّد صفر صفوف).
- السيرفر التجريبي (uvicorn) **أُوقف**، `netstat` يؤكد صفر اتصال `LISTEN` على المنفذ 8000 (بقايا `TIME_WAIT` فقط لاتصالات العميل، طبيعي وغير مؤثر).

---

## 6) الخلاصة والتصنيف النهائي — بانتظار قرارك

| # | الاكتشاف | الخطورة | مؤكَّد حيًا؟ | يحتاج قرار |
|---|---|---|---|---|
| 1 | كل الـ19 endpoint: `tenant_id` مصدره هيدر `X-Tenant-ID`، صفر ربط بـ`current_user.tenant_id` | 🔴🔴🔴 IDOR جذري، النمط الكلاسيكي (5 دومينات أخرى مُصلَحة به) | ✅ | نعم |
| 2 | 8 endpoints بلا `current_user` إطلاقًا — قراءة مفتوحة بالكامل بلا أي مصادقة (مشاريع/مساهمات/مراحل/متابعين/تحديثات/تحليلات) | 🔴🔴🔴🔴 **الأخطر في هذه الجلسة — نطاق أوسع من `ai_governance.check-and-consume`** | ✅ (5 endpoints مختبَرة مباشرة) | نعم |
| 3 | `add_project_update` — صفر فحص ملكية (استثناء وسط باقي الكتابة المحمية) | 🔴🔴🔴 IDOR كتابة — **محجوب حاليًا ببج §4.1** | جزئي (الكود مؤكَّد، الاستغلال الحي محجوب) | نعم (يحتاج إصلاح مصاحب لباج §4.1 لما يُفتح) |
| 4 | `follow_project` — كتابة متابعة عبر-تينانت (أثر منخفض) | 🔴🔴 | جزئي (تحليل كود، لم يُختبَر DB مستقل لانخفاض الأثر) | نعم، إصلاح بسيط ضمن نفس النمط |
| 5 | باقي الكتابة (`update/delete/publish_project`, `add/complete_milestone`, `approve_contribution`) | 🟡 القراءة/الاستهداف عبر-تينانت ممكن، الكتابة الفعلية محمية بفحص ملكية حقيقي | ✅ (3 محاولات هجوم مرفوضة حيًا) | نعم (لإغلاق فجوة القراءة/التخمين حتى لو الكتابة محمية أصلًا) |
| ⚪ | `create_project`/معظم أنواع `add_contribution`/`add_project_update` — schema↔model TypeError | — | ✅ (3 حالات، تحجب الاستغلال) | Backlog منفصل — **خارج نطاق IDOR، يستحق جلسة `constructor-mismatch` مخصَّصة** |
| ⚪ | `add_contribution(MONETARY)` → `receiver_email="system@eppne.com"` هاردكودد | — | لم يُختبَر حيًا (قرار متعمَّد) | مرجع فقط الآن، قرار لاحق إن رغبت |
| ⚪ | `list_products` — منتجات `commerce` معروضة من `projects` بلا فلتر تينانت | — | ثابت بالقراءة (موثَّق سابقًا جزئيًا) | Backlog منفصل، خارج نطاق إصلاح `projects` الجذري |

### الحل المقترَح للجذر (معروض فقط — **صفر تنفيذ حتى الآن**)

**نفس النمط الميكانيكي المطبَّق بالحرف على `academy`/`commerce`/`saas`/`sovereign_entities`/`ai_governance`:**
لكل الـ19 endpoint — حذف `tenant: AcademyTenant = Depends(get_current_tenant)` من التوقيع، إضافة `tenant_id = cast(int, current_user.tenant_id)` كأول سطر بالجسم. **العقبة:** 8 من الـ19 **بلا `current_user` إطلاقًا حاليًا** — نفس معضلة `ai_governance.check-and-consume` بالضبط، تحتاج قرارك الصريح لكل واحد:

- **الأرجح (بالقياس على قرارك في `ai_governance`):** إضافة `current_user: User = Depends(get_current_active_user)` للثمانية (`list_products`, `get_project`, `list_projects`, `get_contribution`, `get_milestones`, `get_followers`, `get_project_updates`, `get_analytics`) — يحوّلها من "مفتوحة بالكامل" إلى "أي عضو مسجَّل في نفس التينانت الحقيقي فقط"، بلا تغيير في شكل الاستجابة نفسه.
- **`add_project_update`:** إضافة فحص ملكية (`project.owner_id != author_id` → `raise PermissionDeniedError`) **بموازاة** إصلاح المصدر — نفس نمط `commerce.get_payment_status` — لكن **لا قيمة عملية للتحقق الحي منه قبل حل باج §4.1** (الدالة بتكرش قبل ما توصل لأي منطق).
- **`follow_project`:** يكفي إصلاح مصدر `tenant_id` وحده (لا يحتاج فحص ملكية إضافي، طبيعة العملية "متابعة" لا "امتلاك").
- **باقي الـ9 (كتابة محمية بالفعل):** إصلاح مصدر `tenant_id` وحده — **صفر تغيير في مستوى `current_user` أو منطق الملكية، هو موجود وسليم بالفعل.**

**سؤال تصميمي مفتوح (بانتظار توجيهك، بالضبط زي سؤال `ai_governance`):** هل تريد تنفيذ الإصلاح الجذري (المصدر) **مستقلاً الآن**، مع ترك `add_project_update`/باجات §4.1 كبنود Backlog منفصلة (نفس معاملة `commerce.create_payment_request`/`is_published`)؟ أم تفضّل حل باج §4.1 (schema↔model) **أولاً** حتى يمكن تأكيد إصلاح #2/#3 حيًا بنفس الصرامة (هجوم مرفوض + مسار شرعي ناجح)، بدل الاكتفاء بمراجعة كود ثابتة لهذين البندين؟

---

## 7) بانتظار توجيهك

**صفر تنفيذ كود. صفر كتابة في `PROGRESS_LOG.md` بعد.** الجرد (19/19 endpoint) + التحقق الحي (9 سيناريوهات هجوم/عزل، تغطي القراءة المفتوحة والكتابة المحمية والباجات الجانبية المحجوبة) **مكتمل بالكامل**، البيانات مُنظَّفة ومؤكَّدة، السيرفر متوقف.

**القرار المطلوب:**
1. الموافقة على التصنيف أعلاه (§6).
2. ترتيب/نطاق التنفيذ: الجذر فقط الآن (19 endpoint) مقابل حل §4.1 أولًا لفتح التحقق الحي الكامل لـ#3.
3. توجيه بخصوص §4.2 (الاستدعاء المالي الهاردكودد) — مرجع فقط أم يحتاج رفع أولوية توثيق فوري زي ما حصل مع `commerce`؟

---

## 8) قرار المستخدم [2026-08-24] — موافقة على الجذر الآن + فحص ملكية `add_project_update` + §4.2 مرجع فقط

1. ✅ التصنيف (§6) — موافقة كاملة.
2. ✅ **تنفيذ الإصلاح الجذري فورًا على الـ19 endpoint، بلا انتظار حل §4.1.** الثمانية القراءة المفتوحة: إضافة `current_user: User = Depends(get_current_active_user)` + نفس نمط `tenant_id = cast(int, current_user.tenant_id)`. `add_project_update`: **إضافة فحص الملكية الآن أيضًا** (التحقق الحي منه جزئي/موثَّق كمحجوب ببج §4.1 — مقبول، مش شرط الكل-أو-لا-حاجة). `follow_project`: إصلاح مصدر `tenant_id` فقط.
3. ✅ §4.2 (الاستدعاء المالي الهاردكودد) — **مرجع فقط في `PROGRESS_LOG.md` كبند عادي**، ليس تصعيدًا عاجلاً (الخطر مشروط وأضعف من حالة `commerce` — مفلتر بالتينانت، يحتاج وجود مستخدم `system@eppne.com` محدد لكل تينانت).
4. ✅ إضافة الحالات الثلاث من §4.1 لملف `constructor-mismatch-backlog-classification.md` الموجود (نفس التصنيف/التنسيق).

---

## 9) التنفيذ — مكتمل، مؤكَّد حيًا بالكامل

### 9.1 الديف المُطبَّق

**`router.py` (إعادة كتابة كاملة، نفس النمط الميكانيكي على الـ19 endpoint):** لكل endpoint — حذف `tenant: AcademyTenant = Depends(get_current_tenant)` من التوقيع، استبدال أي `cast(int, tenant.id)` بـ`tenant_id = cast(int, current_user.tenant_id)` كأول سطر مناسب بالجسم. **للثمانية اللي كانت بلا `current_user` إطلاقًا** (`list_products`, `get_project`, `list_projects`, `get_contribution`, `get_milestones`, `get_followers`, `get_project_updates`, `get_analytics`) — أُضيف `current_user: User = Depends(get_current_active_user)`. `list_products` تحديدًا: أُضيف `current_user` للمصادقة فقط، **بلا** إضافة `tenant_id` (البارامتر كان ميتًا أصلًا — راجع §4.3، خارج النطاق، الخدمة نفسها لا تستخدم أي تينانت). إزالة `get_current_tenant` من استيراد `app.api.deps`، وإزالة `from app.domains.academy.models import AcademyTenant` بالكامل (غير مُستخدَمة بعد الإصلاح).

**`service.py` (إضافة واحدة، `add_project_update`):**
```diff
         project = await self.repo.get_project(project_id, tenant_id)
         if not project:
             raise NotFoundError("Project not found")
+        if cast(int, project.owner_id) != author_id:
+            raise PermissionDeniedError("Not authorized to add update to this project")

         sanitized_title = self.sanitize_html(title)
```
نفس نمط/رسالة باقي فحوصات الملكية في نفس الملف (`"Not authorized to X this project"`). `PermissionDeniedError`/`cast` مستوردين بالفعل — صفر import جديد.

`python -m py_compile app/domains/projects/router.py app/domains/projects/service.py` → `exit code 0`.

### 9.2 إعادة تشغيل uvicorn

تأكيد فعلي إن المنفذ 8000 فاضي، تشغيل نظيف (`PYTHONIOENCODING=utf-8`)، انتظار حتى `Application startup complete` (~35 ثانية، نفس مدة التشغيل الأولى — فهرسة DB الاعتيادية). `grep -c Traceback` على اللوج الكامل = **0**.

### 9.3 التحقق الحي بعد الإصلاح — بيانات throwaway جديدة (بادئة `p_projects2_*`، منفصلة تمامًا عن دفعة الاكتشاف الأولى `p_projects_*`)

**الإعداد:** 3 مستخدمين جدد (`p_projects2_a`=952 تينانت1، `p_projects2_b`=953→تينانت16، `p_projects2_c`=954 تينانت1) عبر التسجيل الحقيقي + تسجيل دخول حقيقي (JWT صحيح لكل واحد). مشروع throwaway جديد (`id=4`، تينانت1، مالك 952) **زُرع عبر SQL** (نفس سبب pre-existing من §4.1، لم يتغيَّر — `create_project` لسه معطوبة schema-يًا، خارج نطاق هذا الإصلاح).

| # | الاختبار | قبل الإصلاح (مرجعي، §3) | بعد الإصلاح | الحكم |
|---|---|---|---|---|
| 1 | **مجهول بالكامل** (صفر `Authorization`) → `GET /projects/4`, `/projects/`, `/4/analytics`, `/4/milestones`, `/4/followers`, `/4/updates`, `/products?store_id=1`, `/contributions/1` (8 endpoints) | `200` لكل الثمانية، بيانات حقيقية مكشوفة | **`401 {"detail":"Not authenticated"}` للثمانية بلا استثناء** | ✅ **حاسم — القراءة المفتوحة مقفولة بالكامل** |
| 2 | B (توكن **حقيقي** تينانت16) يقرأ `GET /projects/4` (تينانت1) **بلا تزوير هيدر** | `200` (كان الافتراضي=1 كافٍ) | **`404 "Project not found"`** — تينانت B الحقيقي (16) من التوكن نفسه، الهيدر لم يعد يُقرأ إطلاقًا | ✅ **حاسم** |
| 3 | B يكرر نفس القراءة **بهيدر مزوَّر صراحة `X-Tenant-ID:1`** | `200` | **نفس النتيجة `404`** — الهيدر بلا أي تأثير الآن، الكود لم يعد يقرأه | ✅ **حاسم — التزوير الصريح لا يضيف شيء** |
| 3s | A (توكن حقيقي تينانت1، مالك) يقرأ مشروعه (`id=4`) | — | `200` مع بيانات صحيحة كاملة | ✅ **المسار الشرعي سليم 100%** |
| 4 | C (تينانت1 حقيقي، **غير مالك**) يحاول `PUT /projects/4` | `403` (كان محميًا بالفعل) | **`403 "Not authorized to update this project"`** (لسه سليم، صفر تراجع) | ✅ |
| 4s | A (المالك) يحدّث مشروعه فعليًا | — | `200`، العنوان اتحدَّث فعليًا (تحقق من الـresponse) | ✅ **المسار الشرعي سليم 100%** |
| 5 | B (تينانت16 حقيقي، هيدر مزوَّر `X-Tenant-ID:1`) يحاول `POST /projects/4/follow` (مشروع تينانت1) | لم يُختبَر مسبقًا بهذا التحديد | **`404 "Project not found"`** — تينانت B الحقيقي (16) يُستخدَم، لا وجود لمشروع `id=4` تحته | ✅ **حاسم** |
| 5s | A يتابع مشروعه الخاص | — | `200` نجاح | ✅ **المسار الشرعي سليم 100%** |
| 6 | **C (تينانت1، غير مالك) يحاول `POST /projects/4/updates` — اختبار فحص الملكية الجديد** | N/A (الاستثناء الوحيد بلا فحص ملكية سابقًا، لم يكن قابلاً للاستغلال حيًا بسبب §4.1) | **`403 "Not authorized to add update to this project"`** — **فحص الملكية الجديد يعمل، ويُطبَّق قبل الوصول لباج §4.1** | ✅ **حاسم — الفحص الجديد يعمل فعليًا** |
| 6b | A (المالك) يحاول نفس العملية على مشروعه | — | **`500` — نفس `TypeError: 'media_urls' is an invalid keyword argument for ProjectUpdate` بالحرف (راجع traceback)، صفر تغيير عن السلوك المُوثَّق في §4.1** | ✅ **متوقَّع تمامًا — باج §4.1 لسه قائم كما هو، خارج نطاق هذا الإصلاح بالتصميم** |

**تأكيد حاسم إضافي (اختبار #6):** فحص الملكية الجديد في `add_project_update` **يعمل فعليًا** ويصد المهاجم (`403`) **قبل** ما الكود يوصل لباج §4.1 — يعني الإصلاح مش نظريًا، هو نافذ بالفعل لأي حالة يمر منها الطلب (حتى لو المالك الشرعي نفسه لسه محجوب بباج منفصل تمامًا).

### 9.4 تنظيف بيانات throwaway — مكتمل، مؤكَّد مستقل

```sql
DELETE FROM project_followers WHERE project_id=4;
DELETE FROM projects WHERE id=4;
DELETE FROM users WHERE id IN (952,953,954);
```
`SELECT COUNT` مستقل بعد الحذف: **صفر في الثلاثة جداول.** (بيانات الاكتشاف الأولى `p_projects_*`/`projects id=2,3` كانت اتنضَّفت بالفعل قبل التنفيذ، راجع §5). السيرفر التجريبي أُوقف، `netstat` يؤكد صفر اتصال `LISTEN` على المنفذ 8000.

### 9.5 توثيق الباجات الجانبية — مكتمل

- **§4.1 (3 حالات schema↔model)** أُضيفت كبند واحد مجمَّع (`projects-schema-model-field-mismatch`) لجدول الـBacklog النشط في `PROGRESS_LOG.md`، **و**كبند #19 في `.claude/reports/constructor-mismatch-backlog-classification.md` (🟢 محلي، نفس تنسيق الجدول والفئات المستخدَمة في الملف، مع ملاحظة صريحة إنه أُضيف بعد تجميد الملف الأصلي).
- **§4.2 (الاستدعاء المالي الهاردكودد)** أُضيف كبند عادي (`projects-add-contribution-hardcoded-receiver-email`) لنفس جدول الـBacklog، **🟡 مرجع فقط** — مصنَّف صراحة كأضعف من `finance-transfer-hardcoded-system-account-real-fund-risk` (حالة `commerce`)، مش تصعيدًا.

---

## 10) `git status` / `git diff --stat` — للمراجعة قبل أي commit

**الملفات التي عدَّلتها هذه الجلسة:**
```
M eppne-backend/app/domains/projects/router.py    | 86 ++++++++++++++-------------  (44 insertions, 42 deletions)
M eppne-backend/app/domains/projects/service.py   |  6 +-                            (4 insertions, 2 deletions)
M PROGRESS_LOG.md                                  (بندان جديدان في جدول الـBacklog النشط)
?? .claude/reports/projects-idor-fix-session-log.md              (جديد، هذا الملف)
?? .claude/reports/constructor-mismatch-backlog-classification.md (كان untracked أصلاً من قبل هذه الجلسة — بند #19 أُضيف له الآن)
```

**ملاحظة:** `eppne-backend/app/domains/projects/service.py` كان عليه بالفعل تعديل غير مُلتزَم (`git status` الأصلي، بداية الجلسة) غير متعلق بهذه الجلسة إطلاقًا — إصلاح `FinanceService(self.db, tenant_id)` بدل `self.finance` القديمة في `__init__` (تعديل من جلسة سابقة، لم يُلمَس أو يُغيَّر هنا، لسه ظاهر في نفس الـdiff الكامل للملف).

**باقي الملفات الظاهرة في `git status` الأصلي (متعدّلة/untracked) من جلسات/أعمال سابقة غير متعلقة بهذه الجلسة إطلاقًا** — `security.py`, `main.py`, `agritech/router.py` (محذوف)، `health/service.py`, `invoicing/router.py`, `tasks/affiliate.py`, `tasks/billing.py`, `tests/conftest.py`, ملفات `eppne-web/*`، وخطط/تقارير `.claude/` أخرى — **لم تُلمس، لن تُضاف لأي commit من هذه الجلسة.**

**الحالة النهائية:** ✅ **الإصلاح الجذري + فحص ملكية `add_project_update` مُطبَّقان على الـ19 endpoint، مؤكَّدان حيًا بالكامل (8 سيناريوهات هجوم/عزل مرفوضة أو محايَدة + 4 مسارات شرعية سليمة)، بيانات throwaway منظَّفة بالكامل.** البندان الجانبيان (§4.1 مجمَّع، §4.2) موثَّقان في `PROGRESS_LOG.md` وملف التصنيف. ⏳ **لم يُنفَّذ commit بعد** — بانتظار موافقتك الصريحة على الـ`diff` أعلاه.
