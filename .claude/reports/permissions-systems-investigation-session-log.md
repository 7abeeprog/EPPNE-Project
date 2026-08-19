# جلسة تشخيص: أنظمة الصلاحيات والأدوار الحالية (identity / command / sovereign_entities)

**النوع:** تشخيص فقط — صفر كود، صفر migration، صفر تعديل. جاري التوثيق أول بأول.

**التاريخ:** 2026-08-19

**المراجع الخلفية المقروءة بالكامل قبل البدء:**
- `.claude/plans/permissions-systems-investigation-session-instructions.md`
- `.claude/plans/entity-permissions-and-lifecycle-vision.md`
- `.claude/plans/multilevel-referral-system-design-vision.md`

---

## سجل التقدم (Live Log)

- [تم] قراءة تعليمات الجلسة + المستندين الخلفيين.
- [تم] القسم 1: `identity` — نظام الأدوار الحالي + اكتشاف تكرار حرج في dependency الصلاحيات (`security.py` مقابل `deps.py`).
- [تم] القسم 2: `command` — لا يوجد نظام صلاحيات مستقل، يعتمد كليًا على `identity` عبر `deps.py`.
- [تم] القسم 3: `sovereign_entities` — نظام صلاحيات محلي مستقل (`EntityRole`) + تأكيد حالة الثغرة الأمنية اليوم (لم تتغيّر، صفر لمس).
- [تم] القسم 4: مسح شامل إضافي — لا يوجد نظام خامس مخفي، مرشح واحد مستبعَد بالتأكيد (`AgentRole`).
- [تم] القسم 5: خريطة التداخل والتعارض النهائية.
- [تم] الجلسة — عُرضت النتائج كاملة، توقفت بلا اقتراح تصميم.

---

## القسم 4 — مسح شامل إضافي: دومينات أخرى محتملة

`grep` شامل عبر كل المشروع لكل من: `Permission`, `Role` (كموديلات/كلاسات)،
`approve_`, `require_role(s)`, `is_admin`, `system_role`, `sovereign_rank`.

**نتائج جديدة لم تُذكر في الأقسام 1-3:**

1. **`app/domains/ai_agents/models.py:12` — `AgentRole`**: فُحص بالكامل
   ووُجد **غير ذي صلة** — تصنيف "وظيفة" لوكلاء الذكاء الاصطناعي أنفسهم
   (`CEO`, `SWARM_ORCHESTRATOR`, `CLIMATE_BROKER`, ...)، **ليس دورًا
   بشريًا ولا آلية صلاحية مستخدم مطلقًا**. مُستبعَد صراحة بعد الفحص، لا
   بالتخمين.
2. **`approve_leave`/`approve_payroll`** (`employment/service.py:506,586`)
   و**`approve_contribution`** (`projects/service.py:245`): أفعال
   موافقة على مستوى العمل التجاري (business workflow)، **مبنية على
   ملكية الكائن (`employer_id == current_user.id`) لا على نظام أدوار
   منفصل** — لا صلاحية ذرية بنمط `approve_x:{TYPE}` كما تقترح رؤية
   `entity-permissions-and-lifecycle-vision.md`. مُوثَّقة هنا فقط
   كتأكيد أنها **ليست** نظام صلاحيات رابع، بلا تحليل أعمق (خارج نطاق
   الثلاثة دومينات المطلوبة صراحة).
3. **`invitation_service.py:39-51`** (`identity`): يستقبل `is_admin: bool`
   كمعامل من الراوتر (مُشتق من `is_admin_or_above(current_user)` —
   نفس نظام `system_role`، ليس نظامًا جديدًا) لتمييز "صاحب الدعوة" عن
   "أدمن يقدر يشوف/يلغي أي دعوة". امتداد طبيعي لنظام `identity`
   الموثَّق في القسم 1، لا نظام إضافي.

**لا يوجد أي نظام خامس مخفي.** الأنظمة الحقيقية المكتشفة في المشروع
كله (بعد الفحص الشامل) هي بالضبط الأربعة الموثَّقة في §5 أدناه — لا أكثر.

---

## القسم 5 — خريطة التداخل والتعارض (الصورة الكاملة)

| # | النظام | الموقع | الغرض | من يستخدمه فعليًا | حي أم ميت | التداخل/التعارض |
|---|---|---|---|---|---|---|
| **A** | `system_role` (`SystemRole` Enum على `User`) | `identity/models.py:50` | صلاحيات إدارية عامة على مستوى المنصة (USER/ADMIN/SUPER_ADMIN/EXECUTIVE_DIRECTOR) | **الأوسع انتشارًا** — كل الدومينات تقريبًا (40 ملف)، عبر نسختين متوازيتين من الـdependencies (راجع B/C) | ✅ حي، العمود الفقري الفعلي لكل فحص صلاحية في المشروع اليوم | يُفحص بمنطقين مختلفين فعليًا (B مقابل C) — مصدر التعارض الأول |
| **B** | `app/core/security.py` (dependencies) | `core/security.py` | تعريف مرجعي لـ`get_current_user`/`require_roles`/إلخ، يقرأ `system_role` | يُستورد في عدة راوترات، من بينها 4 ملفات تستورد B **و**C معًا | ✅ حي | **يتعارض فعليًا مع C**: يفحص `session_version` وتطابق tenant الصارم، C لا يفحصهما — سلوك أمني مختلف لنفس الاسم |
| **C** | `app/api/deps.py` (dependencies) | `api/deps.py` | نسخة موازية شبه متطابقة الأسماء لـB، زائد `SimpleTenant`/`require_subscription`/`get_current_instructor_or_admin` | **الأوسع استخدامًا فعليًا** في الراوترات الأحدث (`command`, `sovereign_entities`, معظم الدومينات القطاعية) | ✅ حي | نفس التعارض مع B من الاتجاه المعاكس؛ `require_sector` بها معطَّل فعليًا (يعتمد على حقل `sector` غير موجود على `User`) |
| **D** | `EntityRole` + `can_sign_contracts` | `sovereign_entities/models.py:39-43` | صلاحيات محلية داخل كيان مؤسسي واحد (Owner/Exec/Signatory/Representative) | فقط داخل `sovereign_entities` (service layer، ليس عبر `Depends`) | ✅ حي | مستقل تمامًا عن A/B/C — **3 طبقات صلاحية متزامنة على نفس الدومين** (A لعمليات الأدمن العليا، D للملكية اليومية، `can_sign_contracts` بوليان منفصل حتى عن D للتوقيع المالي) |
| **E** | `sovereign_rank` (`SovereignRank` Enum على `User`) | `identity/models.py:49` | رتبة فردية معروضة فقط (بيانات وصفية) | **لا أحد** — صفر فحص صلاحية حقيقي يعتمد عليه في كل المشروع | ⚰️ **ميت وظيفيًا** (موجود في الموديل والschema، بلا أي أثر تشغيلي على القرار) | لا تعارض حاليًا لأنه غير مُفعَّل — لكنه **الحقل الذي افترضه مستند الرؤية كأساس محتمل لـ"Platform Admin"** (§2 من `entity-permissions-and-lifecycle-vision.md`) رغم أنه اليوم بلا أي منطق فحص إطلاقًا |
| **F** | `TwinPermission` | `digital_twin/models.py:71` | منح وصول ضيق لكيان "توأم رقمي" واحد لمستخدم/رتبة معينة | فقط `digital_twin` | ✅ حي (محلي) | نطاق ضيق جدًا، لا تعارض — نمط مشابه لـD (صلاحية محلية لكيان واحد) لكن أبسط (بلا أدوار متدرجة) |
| **G** | `min_sovereign_rank` (`String(50)` حر) | `service_marketplace/models.py:63` | نية تصميمية لربط خدمة بحد أدنى من `sovereign_rank` | لا أحد — عمود نص حر غير مرتبط بـEnum ولا بأي منطق تحقق | ⚰️ **ميت** — لا كود يقرأه في أي شرط | يعزز اكتشاف E: نية استخدام `sovereign_rank` موجودة في أكثر من مكان بالتصميم الأصلي، لكن التنفيذ الفعلي توقف قبل الربط في الحالتين |
| **H** | `command` (`DashboardType`, إلخ) | `command/models.py` | **ليس نظام صلاحيات** — تصنيف عرض فقط | — | — | **لا يوجد نظام هنا إطلاقًا** — يُذكَر فقط لأنه أحد الدومينين المطلوب فحصهما صراحة؛ يعتمد كليًا على A عبر C |

### التعارضات الحرجة (ملخَّص)

1. **B مقابل C (الأخطر):** نسختان متوازيتان من كل دالة صلاحية أساسية
   (`get_current_user`, `require_roles`, `is_privacy_officer`, ...)
   بمنطق أمني **متباين فعليًا لا متطابق**، مستوردتان معًا في 4 ملفات،
   ومختلطتان بحرية عبر 40 ملفًا إجمالًا بلا معيار واضح لأيهما "المصدر
   الرسمي". هذا هو أقرب اكتشاف في هذه الجلسة لنمط "النظام B غير
   الموثَّق" من تشخيص العمولات — الفرق الوحيد أن كلا النظامين هنا
   **معروفان ومُستخدَمان علنًا**، لكن **لا أحد وثَّق التباين السلوكي
   بينهما قبل الآن**.
2. **E (`sovereign_rank`) بلا أي دور تشغيلي فعلي اليوم**، رغم أنه
   الحقل الذي افترضته رؤية نظام الصلاحيات الجديد (§2 من
   `entity-permissions-and-lifecycle-vision.md`) كمرشح محتمل لتمثيل
   `Platform Admin`. أي قرار تصميمي مستقبلي يربط `Platform Admin`
   بـ`sovereign_rank` **يُنشئ أول استخدام تشغيلي حقيقي له في تاريخ
   المشروع** — لا يُبنى فوق منطق موجود.
3. **D (`EntityRole` في `sovereign_entities`) نظام صلاحيات ثالث فعلي
   قائم بالفعل**، بمعزل تام عن A/B/C، وبمعزل عن الرؤية الجديدة
   المقترحة (RBAC + Overrides). أي تصميم موحَّد مستقبلي (راجع
   `entity-permissions-and-lifecycle-vision.md` §2) يحتاج أن يقرر
   صراحة: هل `EntityRole` يُستبدَل بالكامل بالنظام الجديد، أم يبقى
   كطبقة محلية إضافية فوقه (نفس سؤال "كيفية التكامل الدقيق" المفتوح
   أصلًا لـ`system_role`/`sovereign_rank`، لكنه ينطبق الآن على D أيضًا).
4. **الثغرة الأمنية في `sovereign_entities`** (§3.4) **لا علاقة لها
   مباشرة بأي من A-H** كنظام صلاحية — سببها فجوة في **المصادقة الأساسية**
   (غياب `current_user` من توقيع 4 endpoints) مدموجة بباج تقني منفصل
   (`SimpleTenant`)، لا خلل في منطق دور/صلاحية بحد ذاته. **لكن أي تصميم
   جديد يلمس `sovereign_entities` يجب أن يتعامل مع هذا التحذير من اليوم
   الأول**، كما نص التحذير الأمني في تعليمات الجلسة.

---

## ملخَّص تنفيذي (للقراءة السريعة)

- **`identity`**: `system_role` هو العمود الفقري الفعلي لكل الصلاحيات
  اليوم. `sovereign_rank` بيانات معروضة فقط، **صفر استخدام تشغيلي حاليًا**.
  لا يوجد جدول `Permission`/`Role` عام في `identity` أو خارجها (باستثناء
  micro-models محلية ضيقة النطاق: `TwinPermission`, `EntityRole`).
- **اكتشاف حرج غير متوقَّع:** يوجد **نسختان متوازيتان ومتباينتان فعليًا**
  من dependencies المصادقة/الصلاحية (`core/security.py` و`api/deps.py`)،
  مستخدَمتان معًا أحيانًا في نفس الملف، بفروقات أمنية حقيقية (فحص
  `session_version`، تطابق tenant صارم، مصدر بيانات `sector`). هذا أهم
  اكتشاف في هذه الجلسة ويحتاج قرارًا معماريًا صريحًا (توحيد لأي نسخة)
  **قبل** بناء أي نظام صلاحيات جديد فوقهما.
- **`command`**: لا نظام صلاحيات مستقل — دومين مستهلك بحت لـ`identity`
  (عبر نسخة `deps.py`). لا أحد يعتمد عليه من الخارج.
- **`sovereign_entities`**: (1) غرضه الفعلي توثيق مؤسسي/KYB لكيانات
  خارجية، **مختلف جوهريًا** عن "الكيانات المتداخلة" في مستند الرؤية —
  لا خطر تكرار مباشر. (2) له **نظام صلاحيات محلي مستقل فعليًا**
  (`EntityRole` + `can_sign_contracts`)، على مستوى service layer لا
  `Depends`. (3) **الثغرة الأمنية المحذَّر منها لا تزال قائمة بالحرف،
  بلا أي تغيير**، لا تزال كامنة بنفس الآلية (باج `SimpleTenant` يحجبها
  حاليًا)، صفر لمس تم في هذه الجلسة.
- **لا يوجد نظام خامس مخفي** بعد مسح شامل إضافي عبر كل الدومينات
  (§4) — الصورة مكتملة بالأنظمة الأربعة الفعلية A/B-C/D الموثَّقة في
  §5، زائد حقلين ميتين وظيفيًا (E, G) يستحقان قرارًا صريحًا (تفعيل أم
  إزالة) في أي تصميم قادم.

**لا تصميم جديد اقتُرح في هذه الجلسة، بالتزام كامل بتعليمات الجلسة.**

---

## القسم 3 — `sovereign_entities`: فحص كامل (مع الالتزام الصارم بالتحذير الأمني — صفر لمس)

### 3.1 الغرض الفعلي (من الكود، لا من الاسم)

الاسم يوحي بـ"كيانات ذات صلاحيات سيادية على المنصة" — **هذا الافتراض غير
صحيح.** الغرض الحقيقي (تعليق أعلى `models.py`, وتأكيد بقراءة كل الحقول):
**تسجيل وتوثيق كيانات مؤسسية/حكومية خارجية** (دول/حكومات، وزارات وهيئات،
منظمات دولية، شركات متعددة الجنسيات، شركات تجارية، منظمات مجتمع مدني،
مؤسسات أكاديمية — `SovereignEntityType`, `models.py:17-28`) على غرار
KYB (Know-Your-Business) في الأنظمة المالية، زائد "Brand Builder"
(بناء صفحة مؤسسية عامة بالسحب والإفلات) ومحفظة مالية سيادية (Web3) لكل
كيان. **لا علاقة لاسم الدومين بـ`sovereign_rank` في `identity`** — رتبة
مستخدم فردية شيء، وتسجيل كيان مؤسسي خارجي شيء مختلف تمامًا؛ لا أي رابط
كود بين الاثنين (تأكيد إضافي: `grep` لـ`SovereignEntityType` أو أي حقل
من هذا الدومين داخل `identity` بأكمله = صفر نتائج).

### 3.2 علاقته بـ"الكيانات المتداخلة" في مستند الرؤية — **مفهوم مختلف، لا تطبيق مسبق لنفس الفكرة**

مستند `multilevel-referral-system-design-vision.md` §5 يصف: أي مستخدم
مؤهَّل يبني كيانًا (كورس، متجر، تطبيق نقل ركاب) **فورًا وذاتيًا**، يدخل
Trial تلقائي، يُفعَّل بالدفع، ويحتاج بوابتي موافقة مستقلتين (ظهور عام +
إضافة شريك) — موصوف بالتفصيل في `entity-permissions-and-lifecycle-vision.md`.

`sovereign_entities` **لا يطابق هذا النموذج على الإطلاق**، رغم تشابه
الاسم والبنية الهرمية السطحية (`parent_id` ذاتي الإشارة + نوعا
`DIVISION`/`TEAM` للهيكل الداخلي، `models.py:27-28,88`):

| الجانب | `multilevel-referral...vision.md` §5 | `sovereign_entities` الفعلي اليوم |
|---|---|---|
| من يُنشئ | "مستخدم مؤهَّل" (شرط التأهيل غير محسوم) | أي `current_user` نشط (`get_current_active_user`) — لا شرط تأهيل مطبَّق فعليًا |
| Trial تلقائي عند الإنشاء | ✅ مطلوب صراحة | ❌ لا يوجد — الكيان `is_active=True` فور الإنشاء، بلا مفهوم trial |
| تفعيل عند الدفع | ✅ مطلوب صراحة | ❌ لا علاقة بالدفع إطلاقًا — الكيان "فعّال" فور الإنشاء |
| بوابة موافقة للظهور العام | ✅ صلاحية ذرية منفصلة | ❌ **غير موجودة** — أي ممثِّل (`_is_representative`) يقدر ينشر الصفحة (`publish_entity_page`) بلا أي موافقة أدمن، **وبلا أي شرط أن يكون `kyb_status == VERIFIED`** (تأكيد: `service.py:280-287`، `_is_representative` فقط، صفر فحص لـ`kyb_status`) |
| بوابة موافقة لإضافة شريك | ✅ صلاحية ذرية منفصلة | 🟡 موجودة لكن **بمنطق مختلف تمامًا**: `add_representative`/`remove_representative` تتطلب أن يكون الطالب نفسه `OWNER`/`EXECUTIVE_DIRECTOR` **على نفس الكيان** (`service.py:154-162`) — **صلاحية داخلية لصاحب الكيان نفسه، وليست موافقة Platform Admin خارجية** كما يصف المستند |
| نوع العمولة/الإحالة | جزء أساسي من التصميم | ❌ غير موجود إطلاقًا في هذا الدومين |
| التحقق (KYB) | غير مذكور في المستند | ✅ موجود (`kyb_status`) لكنه **منفصل تمامًا وغير مربوط** ببوابة "الظهور العام" — تحقق هوية الكيان القانوني شيء، الموافقة على ظهوره للعامة شيء آخر لم يُطبَّق أصلًا هنا |

**الخلاصة:** `sovereign_entities` **ليس تطبيقًا موجودًا مسبقًا لنفس فكرة
"الكيانات المتداخلة"** من مستند الرؤية — هو نظام مختلف الغرض (توثيق
مؤسسي/KYB لكيانات خارجية رسمية: حكومات وشركات كبرى)، **لا كيانات
منتج/خدمة يبنيها أي مستخدم عادي** كما في الرؤية. **لا خطر تكرار مباشر
بينهما** طالما بقي الفهم بهذا الوضوح — لكن التشابه السطحي في المصطلحات
(entity, representative/owner, hierarchy) يستحق الانتباه في أي جلسة
تصميم لاحقة لتفادي لبس التسمية.

### 3.3 نظام صلاحيات مستقل بالكامل — `EntityRole` (اكتشاف: نظام رابع فعليًا)

`sovereign_entities` **له نظام صلاحيات خاص به، مستقل تمامًا عن
`system_role`/`sovereign_rank` وعن أي من نسختي `security.py`/`deps.py`**:

```python
# models.py:39-43
class EntityRole(str, enum.Enum):
    OWNER = "OWNER"
    EXECUTIVE_DIRECTOR = "EXECUTIVE_DIRECTOR"
    SIGNATORY = "SIGNATORY"
    REPRESENTATIVE = "REPRESENTATIVE"
```

مخزَّن في جدول منفصل `EntityRepresentative` (علاقة user↔entity، ليس على
`User` نفسه) — بلا أي FK أو علاقة لـ`system_role`/`sovereign_rank`.
الفحص يتم **على مستوى الـservice layer حصرًا** (ليس عبر FastAPI
`Depends` كباقي المشروع)، بدالتين مساعدتين:

- `_is_representative(entity_id, user_id)` — عضوية بأي دور (`service.py:492-494`).
- `_is_authorized_representative(entity_id, user_id, allowed_roles)` —
  عضوية بدور محدَّد ضمن قائمة (`service.py:496-506`).

**نمط الاستخدام الفعلي (بالدليل):**

| العملية | الدالة | من المخوَّل |
|---|---|---|
| تعديل/حذف الكيان | `update_entity`, `delete_entity` | أي ممثِّل (`_is_representative` — أي دور من الأربعة) |
| رفع مستندات KYB / عرضها | `upload_kyb_document`, `get_kyb_documents` | أي ممثِّل |
| تعديل/نشر صفحة الكيان | `update_entity_page`, `publish_entity_page` | أي ممثِّل |
| إضافة/إزالة ممثِّل جديد | `add_representative`, `remove_representative` | **فقط** `OWNER`/`EXECUTIVE_DIRECTOR` |
| إيداع في محفظة الكيان | `deposit_to_entity_wallet` | **فقط** `OWNER`/`EXECUTIVE_DIRECTOR` |
| تحويل من محفظة الكيان | `transfer_from_entity` | يتطلب `can_sign_contracts=True` (حقل بوليان منفصل تمامًا عن `role`، **حتى `OWNER` بلا `can_sign_contracts=True` مرفوض** — تأكيد `service.py:424-426`) |
| مراجعة/اعتماد KYB (`review_kyb`) | — | **ليس عبر `EntityRole` إطلاقًا** — `Depends(get_current_superuser)` من `identity.system_role` مباشرة (`router.py:195`) |

**هذا يعني عمليًا 3 طبقات صلاحية متداخلة تحكم دومينًا واحدًا في نفس
الوقت:** (1) `system_role` من `identity` — لعمليات إدارية عليا فقط
(`review_kyb`, إنشاء قوالب/`create_page_template`)، (2) `EntityRole`
محلي لكل كيان — لعمليات الملكية اليومية، (3) `can_sign_contracts`
بوليان مستقل حتى عن `EntityRole` نفسه — لعمليات التوقيع المالي تحديدًا.
**لا تكامل أو مرجعية موحَّدة بين الطبقات الثلاث** — كل واحدة مكتوبة
ومفحوصة بشكل منفصل تمامًا بمنطقها الخاص.

### 3.4 ⚠️ حالة الـ4 endpoints بلا مصادقة — التحقق الحي اليوم (2026-08-19)

**تم التحقق بقراءة كود مباشرة فقط (بلا أي تنفيذ/طلب حي، بلا لمس) —
مطابقة سطرًا بسطر لما وثَّقه `PROGRESS_LOG_ARCHIVE_2026-08-18.md`
(القسم بتاريخ `[2026-08-13]`، "تسريب بيانات مالية/KYB بلا أي مصادقة
إطلاقًا"). لم يُعثر على تقرير منفصل باسم
`CRITICAL-sovereign-entities-unauthenticated-endpoints.md` في
`.claude/reports/` وقت هذا الفحص — المرجع الفعلي الوحيد الموجود هو
الأرشيف المذكور.**

**النتيجة: الحالة اليوم مطابقة تمامًا لما وُثِّق سابقًا، بلا أي تغيير:**

1. **الأربعة endpoints لسه بلا `current_user` في توقيعها** (تأكيد مباشر
   من `router.py` المقروء في هذه الجلسة):
   - `list_entities` — `router.py:39-48` — فقط `tenant_id: int = Depends(get_current_tenant)`.
   - `get_entity` — `router.py:72-80` — نفس الشيء.
   - `list_templates` — `router.py:339-346` — نفس الشيء.
   - `list_components` — `router.py:349-356` — نفس الشيء.
2. **لكن `main.py:300-306` لسه بيغلِّف كل الراوترات (شامل `sovereign_router`,
   بقطاع `"sovereign"` — `main.py:292`) بـ`Depends(require_sector(sector))`
   على مستوى تسجيل الراوتر** — يعني توكن JWT صالح **لا يزال شرطًا أساسيًا
   فعليًا** لكل الأربعة، عكس الانطباع الأول من قراءة توقيع الـendpoint وحده.
3. **`identity/service.py` لسه لا يُصدر claim `sector` لأي مستخدم عادي**
   (تأكيد `grep` — صفر نتائج لكلمة `sector` في الملف بأكمله) — يعني
   **الاستغلال لسه محصور فعليًا في حسابات `SUPER_ADMIN`/`EXECUTIVE_DIRECTOR`
   فقط** (اللي بتتخطى فحص القطاع كليًا، `security.py:215-216`)، مش أي
   مستخدم عادي، ومؤكَّد أيضًا مش أي زائر مجهول بلا توكن أساسًا.
4. **باج `SimpleTenant` (الكائن الخام بدل `.id`) لسه موجود بالحرف في نفس
   الأربعة دوال تحديدًا** — تأكيد مباشر من `repository.py` (`get_entity`
   سطر 26، `list_entities` سطر 63-65، `list_templates` سطر 283،
   `list_components` سطر 287) — كل توقيعاتها لسه `tenant_id: int` بينما
   المصدر الفعلي (`get_current_tenant` من `deps.py`) بيرجع كائن
   `SimpleTenant` كامل، مش `int`. **هذا هو الـ"باج المنفصل" المذكور في
   التحذير الأمني اللي بيحجب الثغرة حاليًا** — أي استعلام DB فعلي هيكراش
   (`DataError: 'SimpleTenant' object cannot be interpreted as an
   integer`) قبل ما يوصل لأي تسريب بيانات فعلي.
5. **`SovereignEntityResponse` (`schemas.py:55-64`) لسه بترجع
   `treasury_balance_mrusdt` صراحة** ضمن استجابة `get_entity`/`list_entities`
   — لو اتصلح باج `SimpleTenant` بمعزل عن ربط `tenant_id` بمصدر موثوق
   (`current_user.tenant_id`)، التسريب (رصيد خزينة + حالة KYB لكيانات أي
   تينانت تاني) هيشتغل فورًا، بالضبط زي ما حذَّر التقرير الأصلي.

**الخلاصة: صفر تغيير في حالة الثغرة منذ آخر توثيق. لا تزال "كامنة"
(latent) بنفس الآلية بالضبط، ومحصورة بنفس القيد (حساب
`SUPER_ADMIN`/`EXECUTIVE_DIRECTOR` + كسر باج `SimpleTenant` أولًا).
صفر لمس أو تعديل تم في هذه الجلسة على أي من الملفات الأربعة أو الكود
المرتبط.**

### 3.5 ملاحظة جانبية موثَّقة (بلا إصلاح) — لعلاقتها المباشرة بموضوع الصلاحيات

`review_kyb` و`update_entity` (`service.py:134-140, 193-218`) ما زالا
بلا `begin_nested()`/`commit()` صريح — نفس "نمط الكتابة الصامتة" الموثَّق
سابقًا في الأرشيف (`repository.py:97-107`, `update_entity` — `flush()`
فقط، تأكيد مباشر في هذه الجلسة). **هذا يعني عمليًا أن قرار موافقة/رفض
KYB الإداري (`review_kyb`) قد لا يُكتب فعليًا في قاعدة البيانات رغم
إرجاع استجابة 200 ناجحة** — أثر مباشر على مصداقية أي نظام موافقات مستقبلي
يُبنى فوق هذا الدومين. **خارج نطاق هذه الجلسة (ليس عن الصلاحيات مباشرة)،
يُذكَر فقط للربط لأنه يمس نفس الكود المفحوص.**

---

## القسم 1 — `identity`: التوثيق الكامل للنظام الحالي

### 1.1 حقول الأدوار في `User` (`identity/models.py:49-51`)

```python
sovereign_rank = Column(SQLEnum(SovereignRank), default=SovereignRank.CITIZEN_L1)
system_role = Column(SQLEnum(SystemRole), default=SystemRole.USER, nullable=False)
kyc_status = Column(SQLEnum(KYCStatus), default=KYCStatus.UNVERIFIED)
```

كلا الحقلين **Python Enum مضبوط عبر `SQLEnum`** (ليس نص حر)، معرَّفين في
`app/core/enums.py:16-29`:

```python
class SystemRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"
    EXECUTIVE_DIRECTOR = "EXECUTIVE_DIRECTOR"

class SovereignRank(str, enum.Enum):
    CITIZEN_L1 = "CITIZEN_L1"
    VETERAN_L2 = "VETERAN_L2"
    INVESTOR_L3 = "INVESTOR_L3"
    LEADER_L4 = "LEADER_L4"
    GOVERNOR_L5 = "GOVERNOR_L5"
    MINISTER_L6 = "MINISTER_L6"
    FOUNDER_L7 = "FOUNDER_L7"
```

**هل هما مستقلان أم متداخلان؟** — **مستقلان تمامًا فعليًا اليوم.** لا
`CheckConstraint`، لا validator، لا أي منطق كود يربط قيمة أحدهما بالآخر.
`system_role` له قيمة افتراضية `USER` و`nullable=False`. `sovereign_rank`
له قيمة افتراضية `CITIZEN_L1` لكنه **`nullable=True`** فعليًا في الموديل
(بلا `nullable=False` صريح) — عمود قابل لأن يكون `NULL` في قاعدة البيانات
رغم وجود default على مستوى Python.

**اكتشاف حاسم:** `sovereign_rank` **لا يُستخدم في أي فحص صلاحية واحد في
كل المشروع.** تأكيد بـ`grep` شامل — كل الاستخدامات الفعلية الوحيدة:
- تعيينه عند إنشاء superuser (`scripts/create_superuser.py:33`).
- إرجاعه في schema استجابة (`identity/schemas.py:41`).
- استثناؤه صراحة من التعديل الذاتي في `update_user`
  (`identity/service.py:242`، ضمن قائمة `forbidden`).
- عمود `min_sovereign_rank` (نص حر `String(50)`، **ليس FK ولا Enum**) في
  `service_marketplace/models.py:63` — غير مربوط بأي منطق تحقق فعلي وقت
  الفحص (راجع §4 أدناه لتفصيل إضافي).

أي فحص صلاحية حالي في المشروع (Admin/Superuser/Sector/Roles) يعتمد **حصرًا
على `system_role`** — `sovereign_rank` بيانات وصفية معروضة فقط، بلا أي أثر
تشغيلي على الصلاحيات اليوم.

### 1.2 اكتشاف حرج: نظامان متوازيان ومتباينان لفحص الصلاحيات

`grep` شامل لأنماط فحص الصلاحية (`if current_user.system_role`,
`Depends(require_...)`, إلخ) كشف عن **وحدتين منفصلتين بالكامل**، كلتاهما
حيّتان ومُستخدَمتان فعليًا في نفس الوقت عبر الراوترات:

1. **`app/core/security.py`** — الوحدة "الأقدم/الأشمل": تحتوي `get_current_user`,
   `get_current_active_user`, `get_current_superuser`, `is_admin_or_above`,
   `require_admin_or_above`, `is_privacy_officer`, `get_privacy_officer`,
   `require_sector`, `require_roles`, `get_current_user_optional`.
2. **`app/api/deps.py`** — وحدة مستقلة تعيد تعريف **نفس الأسماء تقريبًا
   حرفيًا**: `get_current_user`, `get_current_active_user`,
   `get_current_superuser`, `require_sector`, `is_privacy_officer`,
   `get_current_privacy_officer`, `require_roles`,
   `get_current_instructor_or_admin`, زائد إضافات غير موجودة في `security.py`
   (`SimpleTenant`, `get_current_tenant`, `require_tenant_access`,
   `require_subscription`).

**الاثنتان تُستوردان من 40 ملفًا مختلفًا في المشروع.** وأخطر من ذلك: **4
ملفات تستورد من الوحدتين معًا في نفس الوقت**:
`app/domains/communications/router.py`, `app/domains/identity/router.py`,
`app/domains/privacy/router.py`, `tests/test_identity_router_protection.py`.

مثال موثَّق (`identity/router.py:17-18`):
```python
from app.api.deps import get_current_tenant, SimpleTenant
from app.core.security import get_current_active_user, is_admin_or_above
```

`privacy/router.py:8` يستخدم `get_current_active_user` من `deps.py`، بينما
سطر 236 (داخل نفس الملف) يستورد `is_privacy_officer` من `security.py` محليًا.

`communications/router.py:13` يستخدم `get_current_active_user`,
`get_current_tenant`, `get_current_superuser`, `get_current_user_optional`
من `deps.py`، بينما سطر 18 يستورد `decode_token` من `security.py`.

**الفروق الفعلية الخطيرة بين النسختين (ليست مجرد تكرار متطابق):**

| الجانب | `core/security.py` | `api/deps.py` |
|---|---|---|
| فحص `session_version` (إبطال الجلسة عن بُعد) في `get_current_user` | ✅ موجود (سطر 141-142) | ❌ **غائب تمامًا** |
| فحص تطابق `tenant_id` بين التوكن والمستخدم | ✅ صارم، يرفض عند التعارض (سطر 138-140) | ❌ غير موجود إطلاقًا |
| `require_sector` — مصدر قطاع المستخدم | `ContextVar` (`get_sector()`) يُضبط وقت فك التوكن (سطر 145 في `get_current_user`) | `getattr(current_user, "sector", None)` — **`sector` غير موجود كحقل في `User` model إطلاقًا** (راجع `identity/models.py` أعلاه) → دائمًا `None` → يسقط لمنطق افتراضي مختلف (`"academy"` لغير الأدمن) |
| `is_privacy_officer` roles list | `["PRIVACY_OFFICER", "SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]` | نفس المجموعة (ترتيب مختلف فقط) — متطابقة فعليًا |
| دوال إضافية غير موجودة بالطرف الآخر | `require_admin_or_above`, `is_admin_or_above` | `SimpleTenant`, `get_current_tenant`, `require_tenant_access`, `require_subscription`, `get_current_instructor_or_admin` |

**الأثر العملي:** endpoint يعتمد على `get_current_user` من `deps.py` **لا
يتحقق من إبطال الجلسة (`session_version`) ولا من تطابق tenant الصارم** —
بعكس أي endpoint يعتمد على نسخة `security.py`. هذا **نفس نمط اكتشاف نظام
B غير الموثَّق في تشخيص العمولات** — تكرار غير مقصود لنفس المسؤولية بمنطق
متباين فعليًا، لا مجرد نسخ حرفي.

**ملاحظة إضافية:** `SimpleTenant` (المذكورة في التحذير الأمني الخاص
بـ`sovereign_entities` أدناه) معرَّفة في `deps.py:144-153` — كلاس بسيط جدًا
`id: int` من `Header` باسم `X-Tenant-ID`، **بلا أي تحقق من أن هذا الـtenant
فعليًا موجود أو أن المستخدم منتمٍ له فعلًا** (`get_current_tenant` نفسها لا
تتحقق — التحقق يحدث فقط لاحقًا وبشكل منفصل في `require_tenant_access` إن
استُخدمت).

### 1.3 هل يوجد جدول/موديل صلاحيات منفصل في `identity` أو أي مكان آخر؟

`grep` شامل لـ`class \w*Permission\w*(Base)` و`class \w*Role\w*(Base)` عبر
كل المشروع: **نتيجة واحدة فقط خارج `identity`، ولا شيء داخل `identity`
نفسها:**

- `app/domains/digital_twin/models.py:71` — `TwinPermission(Base)`: موديل
  صلاحية **ضيق النطاق جدًا**، خاص فقط بمنح وصول لكيان "توأم رقمي" (Digital
  Twin) بعينه لمستخدم بعينه (`grantee_user_id`) أو لرتبة معينة
  (`grantee_rank` — عمود **نص حر `String(50)`, غير مرتبط بـ`SovereignRank`
  Enum ولا FK**), مع `access_granted: bool` و`override_fee: bool`. **لا
  علاقة له بنظام صلاحيات عام/إداري** — هذا access-grant محلي لكيان واحد،
  ليس RBAC.

لا يوجد أي جدول `Permission`/`Role` عام أو حتى مقترَح جزئيًا في
`identity` نفسها اليوم.

---

## القسم 2 — `command`: فحص كامل من الصفر

**الغرض الفعلي (من الكود، لا من الاسم):** لوحة تحكم إدارية موحَّدة
("Strategic Command" — تعليق أعلى `models.py`: "لوحة التحكم السيادية
الموحدة") لعرض/إدارة: Dashboards (`CommandDashboard`)، إعدادات البراند
(`BrandSettings`)، تنبيهات النظام (`SystemAlert`)، مقاييس المنصة
(`PlatformMetric`)، جلسات المستخدمين (`UserSession` — تتبع فقط، غير
مرتبط بـ`RefreshToken` من `identity`)، تقارير (`CommandReport`)،
وتوصيات ذكاء اصطناعي (`AIRecommendation`).

**هل يحتوي مفهوم أدوار/صلاحيات خاص به؟** **لا.** `DashboardType` Enum
(`SUPER_ADMIN`/`BRAND_ADMIN`/`OPERATOR`, `models.py:16-19`) هو **حقل
تصنيف تجميلي لنوع عرض اللوحة فقط** — تأكيد بـ`grep`: يُستخدم مرة واحدة
فقط كـ default عند الإنشاء (`service.py:117`)، **لا يظهر في أي شرط `if`
أو فحص صلاحية إطلاقًا في كل الدومين.** لا موديل `Permission`/`Role` خاص
بـ`command`.

**فحص الصلاحيات الفعلي في `command/router.py`:** يعتمد **كليًا** على
`app.api.deps` (`get_current_active_user`, `get_current_superuser` —
سطر 8) — أي النسخة **الثانية** من القسم 1.2 أعلاه (بلا فحص
`session_version`، بلا فحص tenant صارم). معظم الـendpoints (dashboard،
قراءة alerts/reports/metrics/recommendations، acknowledge/resolve alert)
تتطلب فقط `get_current_active_user` — **أي مستخدم مُسجَّل عادي (`USER`)
يملك صلاحية قراءة alerts/reports/metrics الخاصة بمستأجره بلا أي دور
إداري**؛ فقط الإنشاء (`create_brand`, `create_alert`, `record_metric`)
مقيَّد بـ`get_current_superuser`. **هذا اكتشاف جانبي يُوثَّق فقط بلا
إصلاح** (قد يكون مقصودًا أو لا — خارج نطاق هذه الجلسة التشخيصية).

**هل يعتمد عليه أي دومين آخر لفحص صلاحيات؟** `grep` شامل لـ
`from app.domains.command` / `domains.command.` عبر كل المشروع: **لا أحد
يعتمد عليه** — الاستخدامات الوحيدة خارج الدومين نفسه هي تسجيل الراوتر في
`app/main.py` وملفات `alembic/env.py`/`migrations/env.py` (تسجيل موديلات
فقط، لا منطق صلاحيات). `command` **دومين مستقل تمامًا**، لا نظام رابع
منفصل بمنطق "نظام B" — فقط مستهلك لنظام `identity` (عبر نسخة `deps.py`
تحديدًا).

