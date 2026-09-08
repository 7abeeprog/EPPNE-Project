# جرد شامل — بند #31 `frontend-service-url-prefix-mismatch` (قراءة فقط، صفر تنفيذ)

**تاريخ:** 2026-08-26
**الغرض:** إغلاق الفجوة المسجَّلة في `constructor-mismatch-backlog-classification.md` §"بند منتشر مستقل — #31" — التصنيف السابق كان **مبني على عيّنة أول 3 روابط فقط** لكل ملف (منهجية `bleach-clean-none-crash`/#23 نفسها)، مع تحذير صريح مكتوب في الملف نفسه: *"العدد (21/30) قابل للتعديل الطفيف لو جلسة grep مخصَّصة لاحقة فحصت كل سطر بدل عيّنة"*. هذه الجلسة نفّذت الجرد الكامل: **كل استدعاء `apiClient` في كل الـ32 ملف** (477 استدعاء)، بلا عيّنة.

**صفر تعديل على أي كود** — هذا الملف توثيق فقط، بانتظار موافقة صريحة على خطة الإصلاح المقترحة بالأسفل.

---

## 1. منهجية التحقق

1. استخراج البادئة الحقيقية لكل راوتر خلفي من `APIRouter(prefix="...")` مباشرة في كل `app/domains/*/router.py` (32 راوتر + `identity`/`admin`).
2. تأكيد أن `main.py:300-308` (حلقة `routers_config`) **لا تستخدم فعليًا** الحقل الثاني (`prefix_path`) في التركيبة على الإطلاق — فقط `prefix="/api"` يُمرَّر لـ`include_router`. المسار الحقيقي المسجَّل = `/api` + `router.prefix` الداخلي **فقط**.
3. تأكيد أن `@router.get/post/...` داخل كل `router.py` **لا تكرر** اسم الدومين في مسار الـroute نفسه (فُحص `employment/router.py` كعيّنة تحقق: `@router.post("/jobs")` مش `@router.post("/employment/jobs")`) — أي أن الباج **ليس** باج خلفي، بل حصرًا في نصوص الروابط المكتوبة يدويًا/المولَّدة داخل ملفات `services/*.ts`.
4. لكل ملف من الـ32: استخراج **كل** استدعاء `apiClient.(get|post|put|patch|delete)` (477 إجمالًا)، عبر مصدرين متقاطعين للتأكيد المزدوج:
   - الكود الفعلي (الـstring/template-literal الممرَّر كمسار).
   - تعليقات التوثيق أعلى كل دالة (نمط `* GET /path` موجود في 27 من 32 ملف، ومطابق 100% لعدد استدعاءات الكود في كل ملف فُحص فيه الاثنان معًا — استُخدم كمصدر تحقق ثانٍ لا كبديل).
5. لكل ملف: تجميع أول segment وأول segmentين من المسار عبر **كل** الاستدعاءات (`uniq -c`) للتأكد من التجانس الداخلي (هل كل الاستدعاءات في نفس الملف بنفس النمط، ولا يوجد خليط صح/غلط داخل نفس الملف).
6. فحص `lib/api-client.ts`: عميل `axios` واحد مشترك (`baseURL = NEXT_PUBLIC_API_URL` أو `http://localhost:8000/api`)، بلا أي `baseURL` أو بادئة إضافية لكل دومين — يستبعد فرضية "كل دومين له عميل axios ببادئة مختلفة".
7. فحص عدم وجود أي أداة codegen لملفات `services/*.ts` نفسها (`api-types.ts` فقط مولَّد من OpenAPI للأنواع، لا للعميل/الاستدعاءات) — يدعم فرضية أن كل ملف `services/*.ts` أُلِّف/كُتب في جلسة/مرحلة منفصلة (Phase) بمعزل عن الباقي، لا عبر قالب موحَّد واحد قابل للتنفيذ.

---

## 2. النتيجة: صفر حالة (ج) "بادئة مضاعفة جزئية" في كل المشروع

**سؤال الجرد الأهم كان:** هل يوجد ملف فيه بعض الاستدعاءات صحيحة وبعضها غلط (فئة ج)، احتمال كان واردًا ولم يُفحَص من قبل؟

**الجواب: لا — صفر حالة واحدة.** كل ملف من الـ32 متجانس داخليًا 100%: إما كل استدعاءاته صحيحة، أو كلها بنفس نمط الخطأ بالحرف. هذا يبسّط خطة الإصلاح بشكل كبير — القرار على مستوى **الملف الكامل**، لا استدعاء بعينه.

---

## 3. الجدول الشامل (32 ملف)

| # | الملف | الدومين الخلفي | عدد استدعاءات `apiClient` | التصنيف | البادئة المستخدَمة فعليًا | البادئة الصحيحة (`APIRouter.prefix` الحقيقي) |
|---|---|---|---|---|---|---|
| 1 | `academy.service.ts` | academy | 42 | (أ) سليم | `/academy/...` | `/academy` |
| 2 | `affiliate.service.ts` | affiliate | 10 | (ب) مضاعفة كاملة | `/affiliate/affiliate/...` | `/affiliate` |
| 3 | `agritech.ts` | agritech | 16 | (ب)+(هـ) مضاعفة **و** راوتر خلفي محذوف بالكامل | `/agritech/agritech/...` | **لا يوجد** — `router.py` محذوف من `main.py` (commit `9e01ede`)، صفر endpoint حي بمعزل عن باج البادئة |
| 4 | `ai-agents.service.ts` | ai_agents | 13 | (أ) سليم | `/ai/...` | `/ai` (وليس `/ai-agents` كما في تسمية tuple `main.py`) |
| 5 | `arbitration-syndicates.ts` | arbitration_syndicates | 12 | (د) مسار مدمج خاطئ | `/arbitration/arbitration-syndicates/...` | `/arbitration-syndicates` |
| 6 | `auth.service.ts` | identity | 9 | (أ) سليم | `/identity/...` | `/identity` |
| 7 | `automation.service.ts` | automation | 14 | (أ) سليم | `/automation/...` | `/automation` |
| 8 | `command.ts` | command | 15 | (ب) مضاعفة كاملة | `/command/command/...` | `/command` |
| 9 | `commerce.service.ts` | commerce | 12 | (ب) مضاعفة كاملة | `/commerce/commerce/...` | `/commerce` |
| 10 | `communications.service.ts` | communications | 15 | (أ) سليم | `/communications/...` | `/communications` |
| 11 | `digital-twin.service.ts` | digital_twin | 12 | (أ) سليم | `/digital-twin/...` | `/digital-twin` |
| 12 | `employment.ts` | employment | 22 | (ب) مضاعفة كاملة | `/employment/employment/...` | `/employment` |
| 13 | `finance.service.ts` | finance | 9 | (أ) سليم | `/finance/...` | `/finance` |
| 14 | `health.service.ts` | health | 13 | (ب) مضاعفة كاملة | `/health/health/...` | `/health` |
| 15 | `insurance.ts` | insurance | 14 | (ب) مضاعفة كاملة | `/insurance/insurance/...` | `/insurance` |
| 16 | `invitations.ts` | invitations | 31 | (ب) مضاعفة كاملة | `/invitations/invitations/...` | `/invitations` |
| 17 | `iot.service.ts` | iot | 11 | (ب) مضاعفة كاملة | `/iot/iot/...` | `/iot` |
| 18 | `logistics.ts` | logistics | 22 | (ب) مضاعفة كاملة | `/logistics/logistics/...` | `/logistics` |
| 19 | `manufacturing.ts` | manufacturing | 18 | (ب) مضاعفة كاملة | `/manufacturing/manufacturing/...` | `/manufacturing` |
| 20 | `marketplace.ts` | service_marketplace | 15 | (ب) مضاعفة كاملة | `/marketplace/marketplace/...` | `/marketplace` |
| 21 | `privacy.service.ts` | privacy | 7 | (ب) مضاعفة كاملة | `/privacy/privacy/...` | `/privacy` |
| 22 | `projects.ts` | projects | 18 | (أ) سليم (بالصدفة البنيوية) | `projects/...` (مسار نسبي، بلا `/` بادئة) | `/projects` |
| 23 | `realestate.ts` | realestate | 13 | (ب) مضاعفة كاملة | `/realestate/realestate/...` | `/realestate` |
| 24 | `saas.service.ts` | saas | 19 | (ب) مضاعفة كاملة | `/saas/saas/...` | `/saas` |
| 25 | `social.ts` | social | 19 | (ب) مضاعفة كاملة | `/social/social/...` | `/social` |
| 26 | `sovereign-entities.ts` | sovereign_entities | 22 | (أ) سليم | `/sovereign-entities/...` | `/sovereign-entities` (وليس `/sovereign` كما في تسمية tuple `main.py`) |
| 27 | `tenders-auctions.ts` | tenders_auctions | 5 | (د) مسار خاطئ تمامًا (نسخ-لصق) | `/tenders/social/...` | `/tenders-auctions` |
| 28 | `tourism-sports.ts` | tourism_sports | 10 | (ب) مضاعفة كاملة | `/tourism-sports/tourism-sports/...` | `/tourism-sports` |
| 29 | `translation.service.ts` | translation | 4 | (ب) مضاعفة كاملة | `/translation/translation/...` | `/translation` |
| 30 | `transport.ts` | transport | 16 | (ب) مضاعفة كاملة | `/transport/transport/...` | `/transport` |
| 31 | `websocket.service.ts` | — | 0 | (هـ) خارج النطاق | — | يستخدم `socket.io-client`، صفر استدعاء `apiClient`/REST إطلاقًا |
| 32 | `zamakana.ts` | zamakana | 19 | (ب) مضاعفة كاملة | `/zamakana/zamakana/...` | `/zamakana` |

**تصحيح صريح لتصنيف batch2 السابق (كان مبنيًا على عيّنة 3 روابط فقط):**
- **`communications.service.ts`**: batch2 وضعها بعلامة "❌ راجع تصحيح" لأن العيّنة الأولى بدت سليمة ولم تكن الجلسة متأكدة إن باقي الملف كذلك. **الجرد الكامل (15/15 استدعاء) يؤكد: الملف سليم بالكامل فعلًا.** يُنقَل رسميًا من عمود "مضاعفة" إلى عمود "سليم".

## 4. الإحصاء الإجمالي

| التصنيف | عدد الملفات | عدد الاستدعاءات المتأثرة | النسبة من 477 |
|---|---|---|---|
| (أ) سليم تمامًا | 9 (`academy`, `ai-agents`, `auth`, `automation`, `communications`, `digital-twin`, `finance`, `projects`, `sovereign-entities`) | 0 من 154 | — |
| (ب) بادئة مضاعفة كاملة | 19 | 290 | 61% |
| (د) مسار خاطئ تمامًا (سببان مختلفان) | 2 (`arbitration-syndicates`, `tenders-auctions`) | 17 | 3.5% |
| (ب)+(هـ) مضاعفة + راوتر خلفي محذوف | 1 (`agritech`) | 16 | 3.3% |
| (هـ) خارج النطاق (غير REST) | 1 (`websocket`) | 0 | — |
| **الإجمالي** | **32** | **477** | **100%** |
| **(ج) بادئة مضاعفة جزئية** | **0 — لم توجد أي حالة** | — | — |

---

## 5. السبب الجذري — تحقق وتعديل الفرضية الأصلية (batch2)

**الفرضية الأصلية (batch2):** "القالب المولِّد يدمج `prefix_path` الميت (الحقل الثاني في تركيبة `routers_config` بـ`main.py`) مع بادئة الراوتر الحقيقية".

### ما تأكد حرفيًا (دليل مباشر لا لبس فيه)

`arbitration-syndicates.ts` تستخدم فعليًا `/arbitration/arbitration-syndicates/...` — أي **تركيز حرفي** لقيمة tuple الميتة (`"/arbitration"`, `main.py:271`) + بادئة الراوتر الحقيقية (`"/arbitration-syndicates"`, `arbitration_syndicates/router.py:14`). هذا **دليل مباشر قاطع** أن مؤلف/مولِّد هذا الملف تحديدًا استخدم كلا القيمتين معًا، بالضبط كما تصف الفرضية.

### ما لا تفسّره الفرضية كما هي (يحتاج تعديل)

لو كانت الفرضية تعمل بشكل آلي حتمي (نفس القالب على كل الملفات)، **كل** الدومينات التي فيها `prefix_path == router.prefix` حرفيًا (وهذا معظمها — 21 دومين تقريبًا، منها الـ19 "مضاعفة" **وأيضًا** `academy`, `automation`, `digital_twin`, `communications`, `finance` النظيفة) كانت ستُصاب بنفس المضاعفة **بلا استثناء**، لأن دمج قيمتين متطابقتين نصيًا ينتج نفس الشكل المضاعَف بغض النظر عن أي عامل آخر. لكن 5 من هذه الدومينات (+`projects`، +`identity` الذي أصلًا خارج حلقة `routers_config`) **سليمة تمامًا**. لا يوجد فرق بنيوي في `main.py`/`router.py` بين المجموعتين يفسّر لماذا انطبق "الدمج" على 19 ملف وتجنَّبه 5 ملفات أخرى تشترك معهم في نفس الشرط بالضبط.

### الاستنتاج المُعدَّل

1. **لا يوجد أداة codegen واحدة** تولِّد ملفات `services/*.ts` (تأكيد: صفر إشارة لأي أداة توليد عميل REST في المشروع؛ `api-types.ts` فقط أنواع TypeScript من OpenAPI). **كل ملف `services/*.ts` كُتب على الأرجح يدويًا/بجلسة Claude منفصلة لكل دومين** (متسق مع تاريخ المشروع القائم على "Phases" ودفعات تدقيق منفصلة موثَّقة في `.claude/reports/`).
2. **السبب الجذري الحقيقي الأدق:** كل جلسة/مرحلة كتبت بادئة الدومين بناءً على **افتراض ذهني** أن "اسم القطاع" (الظاهر في `main.py` كـtag أو كاسم مجلد الدومين) **هو نفسه** المسار الفعلي، ثم **أضافت فوقه أيضًا** بادئة الراوتر الحقيقية عند بناء كل مسار فرعي — سواء لأن الجلسة نسخت المسار من تعليق توثيقي قديم كان يفترض بادئة إضافية، أو لأنها بَنَت الرابط كـ`"/" + domainName + routePath` حيث `routePath` نفسه كان مأخوذًا (أو مفترضًا) بصيغة `"/domainName/actualPath"` بدل `"/actualPath"` وحدها.
3. **`arbitration_syndicates` هي الدليل الأوضح على هذه الآلية بالضبط** — لأن اسم القطاع القصير (`arbitration`) والبادئة الحقيقية الطويلة (`arbitration-syndicates`) **مختلفان نصيًا**، فالنتيجة المضاعَفة تكشف الآلية بدل إخفائها (كما يحدث في باقي الحالات حيث الاثنان متطابقان فيصعب تمييز "دمج قيمتين" عن "كتابة قيمة واحدة مرتين بالغلط").
4. **الدومينات النظيفة (`academy`, `ai-agents`, `auth`, `automation`, `communications`, `digital-twin`, `finance`, `projects`, `sovereign-entities`) لا تشترك في بنية واحدة تفسّر نظافتها** (راجع القسم 6) — الأرجح أن جلسات/مراحل كتابتها راجعت `router.py` الفعلي مباشرة بدل الاعتماد على اسم القطاع من `main.py`/التوثيق، أو كُتبت لاحقًا بعد ملاحظة الباج في ملفات أخرى.
5. **`tenders-auctions.ts` ليست نفس السبب الجذري إطلاقًا** — لو كانت نفس آلية الدمج، كان المتوقع `tenders/tenders-auctions/...` (قياسًا على `arbitration`). الفعلي `tenders/social/...` — **segment "social" منسوخ حرفيًا من ملف `social.ts`** (نفس الملاحظة القديمة في batch2)، على الأرجح خطأ نسخ-لصق أثناء كتابة الملف من قالب/ملف مرجعي مختلف تمامًا، لا علاقة له بـ`prefix_path`. **يجب فصلها عن باقي حالة (د) في أي خطة إصلاح — تحتاج إعادة كتابة يدوية كاملة للـ5 مسارات، لا استبدال آلي بالبادئة الصحيحة.**

**الخلاصة العملية:** الفرضية الأصلية **صحيحة كوصف للشكل النهائي للباج** (ودُلِّلَت حرفيًا في حالة واحدة)، لكنها **غير كافية كتفسير آلي حتمي شامل** — لا يوجد "قالب واحد معطوب" يمكن إصلاحه في مكان واحد ليُصلِح كل الملفات؛ الإصلاح لازم يكون **لكل ملف على حدة** (لحسن الحظ، بيانات نصية بسيطة فقط، صفر منطق).

---

## 6. لماذا الدومينات النظيفة مختلفة بنيويًا؟

| الدومين | السبب البنيوي للنظافة |
|---|---|
| `identity` (`auth.service.ts`) | **الوحيد المُستبعَد بنيويًا من حلقة `routers_config` بالكامل** (`main.py:310-314`، `include_router` منفصل تمامًا) — لم يمرّ إطلاقًا بأي منطق مرتبط بـ`prefix_path`/اسم قطاع. نظافته "بالتصميم"، لا بالصدفة. |
| `sovereign_entities` (`sovereign-entities.ts`) | يستخدم البادئة الحقيقية الطويلة (`/sovereign-entities`) **بدل** اسم القطاع القصير من `main.py` (`/sovereign`) — أي كاتب الملف راجع `router.py` مباشرة، وميّز الاثنين بدل افتراض تطابقهما. **لا يوجد أي مضاعفة لأنه لم يُستخدَم إلا مصدر واحد للحقيقة.** |
| `ai_agents` (`ai-agents.service.ts`) | نفس نمط `sovereign_entities` بالضبط — يستخدم `/ai` الحقيقي (الأقصر) بدل `/ai-agents` (اسم القطاع/الملف). |
| `academy`, `automation`, `digital_twin`, `communications`, `finance` | هنا اسم القطاع == بادئة الراوتر الحقيقية (نفس شرط الـ19 المضاعَفة)، **فلا يوجد دليل نصي يميّز "كتبها كاتب راجع `router.py`" عن "كاتب افترض اسم القطاع"** — الفرق الوحيد الملحوظ هو أن كاتب/جلسة هذه الملفات لم يُضِف بادئة إضافية فوق الأساس عند بناء الرابط الكامل، بعكس الـ19 ملف الأخرى. **لا يوجد نمط بنيوي (تاريخ إنشاء الملف، حجمه، الدومين) يفسّر هذا الفرق بثقة من قراءة الكود وحدها** — الأرجح تفاوت بشري/جلسي (Phase مختلفة، انتباه مختلف)، وليس اختلاف إصدار أداة. **هذا استنتاج صريح غير مؤكَّد 100%، لعدم وجود سجل مراحل كتابة كل ملف individually.** |
| `projects` (`projects.ts`) | حالة خاصة: تستخدم مسارات **نسبية بلا `/` بادئة** (`"projects/"`, `` `projects/${id}` ``) بدل مسار مطلق. هذا **لا يعكس فهمًا صحيحًا للمشكلة عمدًا** — بل نجا بالصدفة البنيوية لآلية `combineURLs` في axios (`baseURL + "/" + relativePath` مع إزالة التكرار)، لأن كاتب الملف لم يضع `/` بادئة أصلًا (ربما نفس نية إضافة اسم القطاع، لكن نُفِّذت بصيغة مختلفة أنقذته بالصدفة). **لا يُعتبَر نمطًا يُحتذى** — لو أُعيدت كتابته ليطابق أسلوب باقي الملفات (مسار مطلق `/projects/...`) يبقى سليمًا، لكن الأسلوب الحالي هش وغير متسق مع بقية المشروع. |

---

## 7. خطة الإصلاح المقترَحة (صفر تنفيذ — بانتظار الموافقة)

بما أن **صفر حالة (ج) جزئية** وُجدت، وبما أن **صفر أداة codegen مركزية** تنتج هذه الملفات (فلا يوجد "قالب واحد" لتعديله وإعادة التوليد)، الخيار العملي الوحيد هو **سكريبت تصحيح جماعي نصي بحت** (لا تعديل منطق)، مقسَّم لمجموعات حسب نوع الإصلاح:

### المجموعة 1 — استبدال آلي بسيط (19 ملف، 290 استدعاء)
لكل ملف في هذه القائمة: `affiliate`, `command`, `commerce`, `employment`, `health`, `insurance`, `invitations`, `iot`, `logistics`, `manufacturing`, `marketplace`, `privacy`, `realestate`, `saas`, `social`, `tourism-sports`, `translation`, `transport`, `zamakana` —
استبدال نصي حرفي لكل استدعاء (regex بسيط لكل ملف):
`"/{domain}/{domain}/` → `"/{domain}/`
(نفس المعادلة على تعليقات التوثيق فوق كل دالة لتبقى متسقة مع الكود). **صفر تغيير في المنطق/التوقيعات/الأنواع.**

### المجموعة 2 — تصحيح مباشر باسم جديد كامل (ملف واحد، 12 استدعاء)
`arbitration-syndicates.ts`: استبدال `"/arbitration/arbitration-syndicates/` → `"/arbitration-syndicates/` (تبسيط، وليس دمج بادئتين).

### المجموعة 3 — إعادة كتابة يدوية (ملف واحد، 5 استدعاءات)
`tenders-auctions.ts`: استبدال `"/tenders/social/` → `"/tenders-auctions/` — **يحتاج مراجعة يدوية لكل من الـ5 استدعاءات قبل التطبيق الآلي** (التأكد من عدم وجود اختلاف إضافي غير مكتشَف بعد segment الأول، رغم أن الجرد الحالي لم يُظهر أي اختلاف آخر).

### المجموعة 4 — قرار منتجي منفصل (ملف واحد، لا يُصلَح ضمن هذه الدفعة)
`agritech.ts`: تصحيح البادئة وحده **لن يعيد تفعيل الدومين** — الراوتر الخلفي محذوف بالكامل (قرار منتجي مؤجَّل موثَّق في commit `9e01ede`). **يُستبعَد من أي إصلاح آلي حتى يُتَّخذ قرار: إما حذف الملف بالكامل (دومين ميت رسميًا)، أو تجميده كما هو لحين بناء راوتر حقيقي.**

### خارج النطاق
`websocket.service.ts` (لا علاقة له ببادئات REST) — لا إصلاح مطلوب.

### لماذا سكريبت جماعي مباشر وليس "تعديل قالب مولِّد"
لا يوجد قالب/أداة توليد واحدة تنتج هذه الملفات (§5 نقطة 1) — فالخيار "عدّل القالب وأعد التوليد" **غير متاح فعليًا**. البديل العملي الوحيد هو تصحيح نصي مباشر بسكريبت واحد يمر على الـ19+1 ملف دفعة واحدة (المجموعتان 1+2)، مع معالجة يدوية منفصلة للحالتين الخاصتين (`tenders-auctions`, `agritech`).

### الأثر المتوقَّع بعد التنفيذ (لو تمت الموافقة)
- 290 + 12 = **302 استدعاء API** ستعمل فعليًا لأول مرة عبر 20 ملف (كانت جميعها تُرجِع `404` من `baseURL` الحقيقي).
- **تحذير مهم لازم يُراعى وقت التنفيذ الفعلي (ليس الآن):** إصلاح البادئة **وحده** لا يضمن أن الـendpoint سيعمل فعليًا — عدة دومينات من نفس القائمة (`invitations`, `arbitration_syndicates`, `tenders_auctions`, `zamakana`, `saas`...) موثَّق أن فيها أعطال خلفية منفصلة تمامًا (بنود #9, #10, #14, #15, #16, #23, #27, #28, #29, #33 وغيرها) ستظهر فورًا بمجرد أن يصل الطلب فعليًا للراوتر الصحيح لأول مرة (كانت هذه الأعطال "مخفية" خلف `404` البادئة الخاطئة). **هذا متوقَّع ومقصود** — إصلاح #31 يكشف الأعطال الحقيقية، لا يخلقها؛ لكنه يعني أن اختبار حي بعد كل إصلاح دومين لازم يتحمَّل احتمال ظهور عطل تالٍ من الـbacklog مباشرة.

---

## 8. ما لم يُنفَّذ في هذه الجلسة الأولى (بالتصميم)
- **صفر تعديل كود** — لا الباك إند ولا الفرونت إند.
- صفر تحقق حي (لا `curl`/طلبات فعلية) — الجرد كوديّ بالكامل (قراءة `router.py` + `services/*.ts` + `main.py`).
- صفر قرار بشأن `agritech.ts` (مؤجَّل لقرار منتجي منفصل كما هو موثَّق مسبقًا).

---

# جلسة التنفيذ (بعد الموافقة) — 2026-08-26

**نطاق التنفيذ المصرَّح به:** المجموعات 1+2+3 فقط (21 ملف فعليًا — 19 مجموعة1 + `arbitration-syndicates.ts` مجموعة2 + `tenders-auctions.ts` مجموعة3؛ العدد "20" في طلب المستخدم كان يقصد عمليًا "20 ملف للتحقق الحي والتصنيف" باستثناء `tenders-auctions.ts` الذي يحتاج مراجعة يدوية منفصلة للـdiff قبل أي تحقق حي عليه — نُفِّذ بالضبط بهذا الترتيب). `agritech.ts` (مجموعة 4) **لم يُلمَس** كما هو مقرَّر.

## 9. التطبيق الآلي (سكريبت `sed` بسيط لكل ملف)

لكل ملف: استبدال حرفي `"/{domain}/{domain}/"` → `"/{domain}/"` (المجموعة 1، 19 ملف)، `"/arbitration/arbitration-syndicates/"` → `"/arbitration-syndicates/"` (`arbitration-syndicates.ts`)، و`"/tenders/social/"` → `"/tenders-auctions/"` (`tenders-auctions.ts`). صفر تغيير آخر.

**تأكيد نظافة الاستبدال:** `git diff --stat` على الـ21 ملف يظهر **614 إضافة / 614 حذف بالضبط** — تطابق 1:1 لعدد الأسطر، صفر إضافة/حذف سطر واحد، يؤكد أن التعديل نصي بحت (لا تغيير بنيوي).

## 10. التحقق البنيوي (TypeScript)

`npx tsc --noEmit` نُفِّذ مرتين: **قبل** التعديل (بعد `git stash` مؤقت للـ21 ملف) و**بعد** التعديل — **1831 سطر خطأ في الحالتين، `diff` بين اللوجّين = صفر سطر اختلاف**. كل الأخطاء الموجودة (استيراد/تصدير أسماء غير متطابقة، أنواع ضمنية `any`، إلخ) **موجودة مسبقًا وبلا علاقة بهذا الإصلاح** (نفس فئة البند #43 الموثَّق سابقًا) — **صفر خطأ TypeScript جديد نتج عن الاستبدال النصي**.

## 11. التحقق الحي — الإعداد

- **الباك إند:** `uvicorn app.main:app` حي على `127.0.0.1:8000` (DB/`postgres:16`/`redis` عبر حاويات Docker كانت شغّالة أصلًا). تسجيل دخول حقيقي بمستخدم throwaway موثَّق مسبقًا (`TEST_super_a`/تينانت1/`SUPER_ADMIN`، من `throwaway-test-users.md`) — كوكيز `access_token`/`refresh_token` حقيقية (نفس آلية `withCredentials` التي يستخدمها `apiClient` فعليًا).
- **الفرونت إند:** `next dev` (Turbopack) بدأ فعليًا وأعلن `✓ Ready`، لكن أول طلب لصفحة `/` ظل عالقًا على `○ Compiling / ...` بلا استجابة (تايم آوت حتى 60 ثانية) — مشكلة بيئة/تشغيل محلية غير مرتبطة ببند #31 (لم تُشخَّص، السيرفر أُوقف). **البديل المُطبَّق:** تكرار نفس الطلب الذي يرسله `apiClient` فعليًا (نفس `baseURL=/api`، نفس كوكيز `withCredentials`) عبر `curl` مباشرة على الباك إند — هذا **يغطي بالضبط** الطبقة التي يخصها بند #31 (تصحيح مسار الشبكة)، بمعزل تام عن أي مشكلة رندر واجهة.
- طلب واحد حقيقي (GET) من كل ملف من الـ20 (باستثناء `tenders-auctions.ts`، مؤجَّل لموافقة صريحة على الـdiff).
- **صفر كتابة/POST** أُرسلت أثناء هذا التحقق (كل الطلبات الاختبارية GET) — صفر بيانات throwaway جديدة تحتاج تنظيف.

## 12. الجدول النهائي (20 ملف)

| # | الملف | الاستدعاء المُختبَر | نتيجة HTTP | التصنيف | التفصيل |
|---|---|---|---|---|---|
| 1 | `affiliate.service.ts` | `GET /affiliate/profile` | 200 | (أ) نجح بالكامل | بيانات حقيقية رجعت (`referral_code`, إلخ) |
| 2 | `command.ts` | `GET /command/dashboard` | 500 | (ب) عطل معروف مسبقًا | `ResponseValidationError` — `DashboardResponse.dashboard` متوقَّع `dict`، `service.get_dashboard` بيرجّع كائن ORM خام. موثَّق مسبقًا في `phase16-session-log.md`§ و`command-idor-fix-session-log.md`:115 — قرار سابق صريح: **لا يُصلَح**، خارج نطاق |
| 3 | `commerce.service.ts` | `GET /commerce/products` | 200 | (أ) نجح بالكامل | `[]` (قائمة فارغة صحيحة) |
| 4 | `employment.ts` | `GET /employment/jobs/open` | 500 | (ب) عطل معروف مسبقًا | `ResponseValidationError` (`required_skills`/`required_certificate_ids` = `None` بدل `list`) — موثَّق حرفيًا مسبقًا في `batch1-audit-security-employment-invitations-communications-invoicing.md`:232 |
| 5 | `health.service.ts` | `GET /health/profile/me` | 200 | (أ) نجح بالكامل | ملف طبي حقيقي رجع كاملًا |
| 6 | `insurance.ts` | `GET /insurance/policies` | 500 | **(ج) عطل جديد** | `ResponseValidationError`: `terms_and_conditions` (`insurance_policies`, عمود `JSONB`) = `None` في صف قديم، بينما `PolicyResponse.terms_and_conditions: Dict[str, Any]` (بلا `Optional`) يرفض `None`. لم يظهر في أي تقرير سابق (`grep` شامل صفر نتيجة) — **بند جديد، راجع §13 أدناه** |
| 7 | `invitations.ts` | `GET /invitations/` | 500 | (ب) عطل معروف مسبقًا (امتداد) | `ResponseValidationError` (6 أخطاء: `click_count`/`discount_percentage`/`gift_coins_amount`/`gift_currency` = `None` عبر عدة صفوف) — نفس جذر البند **#25** (`invitations-legacy-invitation-rows-response-validation-error`)، الموثَّق سابقًا لـ`GET /{id}` فقط (4 أخطاء لصف واحد) — **يُؤكَّد هنا امتداده لـ`GET /` (القائمة) أيضًا، بعدة صفوف** |
| 8 | `iot.service.ts` | `GET /iot/assets` | 200 | (أ) نجح بالكامل | `[]` |
| 9 | `logistics.ts` | `GET /logistics/warehouses` | 200 | (أ) نجح بالكامل | `[]` |
| 10 | `manufacturing.ts` | `GET /manufacturing/raw-materials` | 200 | (أ) نجح بالكامل | `[]` |
| 11 | `marketplace.ts` | `GET /marketplace/services` | 200 | (أ) نجح بالكامل | بيانات throwaway قديمة من جلسة `constructor-mismatch` سابقة رجعت بنجاح |
| 12 | `privacy.service.ts` | `GET /privacy/settings` | 200 | (أ) نجح بالكامل | إعدادات خصوصية حقيقية رجعت |
| 13 | `realestate.ts` | `GET /realestate/lands/me` | 200 | (أ) نجح بالكامل | `[]` |
| 14 | `saas.service.ts` | `GET /saas/services` | 200 | (أ) نجح بالكامل | كتالوج (شبه فارغ فعليًا — راجع §13) رجع بنجاح |
| 15 | `social.ts` | `GET /social/feed` | 403 | (ب) عطل معروف مسبقًا (امتداد) | `PermissionDeniedError`: "Social feature 'social' is not included in your current plan" — تأكيد مباشر بـ`SELECT` من `saas_service_catalog`: **صفر صف `social`** — نفس جذر البند **#28** (`saas-service-catalog-missing-entries`)، **يُضاف `social` لقائمة الدومينات المؤكَّدة** (لم يكن مذكورًا فيه سابقًا) |
| 16 | `tourism-sports.ts` | `GET /tourism-sports/destinations` | 403 | (ب) عطل معروف مسبقًا (امتداد) | نفس النمط — `saas_service_catalog` صفر صف `tourism`/`sports`/`entertainment`. موثَّق مسبقًا في `batch3-audit-security-...`:177 (كان صفر صف *قبل* تلك الجلسة، وأُعيد لصفر بعد تنظيف الـthrowaway) — **يُضاف رسميًا لقائمة #28 بدل بقائه ملاحظة جانبية في تقرير batch3** |
| 17 | `translation.service.ts` | `GET /translation/languages` | 500 | **(ج) عطل جديد** | `TypeError: 'RedisClientWrapper' object is not callable` — السبب: `translation/service.py:23` يستورد **الكائن الوحيد (singleton)** `redis_client` بلقب مضلِّل `as get_redis_client`، ثم يناديه كأنه دالة مصنع: `self.redis = get_redis_client()` (سطر 30) — الكائن لا يملك `__call__`. **مختلف جذريًا عن البند #7** (`redis-client-wrapper-missing-methods` — ده عن دوال ناقصة في الكلاس نفسه، مش عن سوء استخدام alias/factory) — **بند جديد منفصل تمامًا، راجع §13** |
| 18 | `transport.ts` | `GET /transport/hubs` | 403 | (ب) عطل معروف مسبقًا (امتداد) | نفس نمط #28 — `saas_service_catalog` صفر صف `transport`. موثَّق مسبقًا في `batch3-audit-security-...`:177 (نفس ملاحظة `tourism_sports` أعلاه) |
| 19 | `zamakana.ts` | `GET /zamakana/nodes` | 403 | (ب) عطل معروف مسبقًا | `PermissionDeniedError` — **البند #28 يذكر `zamakana` صراحة أصلًا** كدومين مؤكَّد (`batch5-audit-security-...`§7) |
| 20 | `arbitration-syndicates.ts` | `GET /arbitration-syndicates/cases/me` | 500 | (ب) عطل معروف مسبقًا | `TypeError: ArbitrationSyndicatesRepository.list_user_cases() takes 2 positional arguments but 3 were given` — تطابق **حرفي** مع البند **#27** (`arbitration-syndicates-repository-missing-methods`)، المذكور صراحة: "`list_user_cases(user_id)` مقابل استدعاء بوسيطين" |

### إحصاء التصنيف

| التصنيف | العدد | الملفات |
|---|---|---|
| (أ) نجح بالكامل | 10 | `affiliate`, `commerce`, `health`, `iot`, `logistics`, `manufacturing`, `marketplace`, `privacy`, `realestate`, `saas` |
| (ب) عطل backend معروف مسبقًا (بعضه بحاجة تحديث/توسيع في توثيقه) | 8 | `command` (خارج backlog المرقَّم، موثَّق بتقارير phase16/`command-idor-fix`)، `employment` (batch1)، `invitations` (#25، امتداد)، `social` (#28، **إضافة جديدة للقائمة**)، `tourism-sports` (#28، **ترقية من ملاحظة جانبية لبند رسمي**)، `transport` (#28، نفس الترقية)، `zamakana` (#28، مؤكَّد أصلًا)، `arbitration-syndicates` (#27، تطابق حرفي) |
| **(ج) عطل جديد غير موثَّق من قبل** | **2** | `insurance` (`terms_and_conditions` NULL/dict)، `translation` (`RedisClientWrapper` غير قابل للاستدعاء) |

## 13. البندان الجديدان (توثيق فقط — صفر إصلاح، بالضبط كما طُلب)

### جديد #46 — `insurance-policies-response-validation-terms-and-conditions-null`
- **الموضع:** `GET /insurance/policies` (وعلى الأرجح `GET /insurance/policies/{id}` بنفس الصف) — `insurance/schemas.py`: `PolicyResponse.terms_and_conditions: Dict[str, Any]` (بلا `Optional`)، بينما `insurance/models.py:61`: `terms_and_conditions = Column(JSONB, default=dict)` — عمود قابل لـ`NULL` فعليًا (صف/صفوف قديمة قبل أي `default` فعلي، أو أُنشئت بمعزل عن الـschema الحالي).
- **الأثر:** `500 ResponseValidationError` لأي طلب `GET` يشمل صفًا قديمًا بهذه القيمة — يمنع قراءة قائمة البوليصات بالكامل لأي تينانت له صف واحد قديم متأثر (نفس نمط #21/#25 "صف throwaway/قديم يخالف schema حالي").
- **مؤكَّد حيًا:** `GET /insurance/policies` (تينانت1، `TEST_super_a`) → `500`، رسالة الخطأ الدقيقة موثَّقة في §12 صف 6.
- **صفر إصلاح** — توثيق فقط بتوجيه صريح من المستخدم.

### جديد #47 — `translation-redis-client-singleton-called-as-factory`
- **الموضع:** `translation/service.py:23` (`from app.core.redis_client import redis_client as get_redis_client`) + `translation/service.py:30` (`self.redis = get_redis_client()`).
- **السبب الجذري:** `redis_client` في `app/core/redis_client.py` **كائن singleton جاهز** (`RedisClientWrapper` instance)، مش دالة مصنع — الاستيراد بلقب `get_redis_client` (اسم يوحي بأنه دالة) ثم استدعاؤه بـ`()` يحاول استدعاء الكائن نفسه كدالة، لكن `RedisClientWrapper` لا يعرِّف `__call__`.
- **الأثر:** `500 TypeError` لأي استدعاء لأي دالة في `TranslationService` تحتاج `self.redis` (`get_cached_translation`, `cache_translation`, `get_idempotent_response`, `store_idempotent_response`) — يمنع **كل** مسارات الكاش/idempotency في دومين `translation` بالكامل (`GET /translation/languages` نفسها تفشل رغم أنها منطقيًا لا تبدو مرتبطة بالترجمة الفعلية — يستاهل فحص إضافي لماذا `languages` تحديدًا بتلمس `self.redis`).
- **مختلف عن #7** (`redis-client-wrapper-missing-methods`) — #7 عن نقص دوال حقيقية في الكلاس، وهذا عن سوء استخدام/تسمية مضلِّلة لاستيراد كائن جاهز. **لا يُدمَج مع #7**.
- **صفر إصلاح** — توثيق فقط بتوجيه صريح من المستخدم.

## 14. توصية بتحديث `constructor-mismatch-backlog-classification.md` (لجلسة لاحقة، ليس الآن)
- إضافة `social`, `transport`, `tourism_sports` رسميًا لقائمة الدومينات المؤكَّدة تحت **#28**.
- إضافة البندين الجديدين **#46**/**#47** أعلاه للجدول الموحَّد.
- توسيع ملاحظة **#25** لتشمل `GET /invitations/` (قائمة) لا فقط `GET /invitations/{id}`.
- **لم يُنفَّذ أي تعديل فعلي على ملف الـbacklog في هذه الجلسة** — بند #31 فقط هو المطلوب إغلاقه، هذا اقتراح للمستقبل.

## 14.5. `tenders-auctions.ts` — الـ`git diff` الكامل (للمراجعة اليدوية، قبل أي تحقق حي عليه)

**الحالة:** التعديل مُطبَّق على القرص فعليًا (نفس آلية §9: استبدال حرفي `"/tenders/social/"` → `"/tenders-auctions/"`، في كل من سطر الكود وتعليق التوثيق أعلى كل دالة) — **لكن بلا أي تحقق حي بعد**، بانتظار موافقة صريحة على هذا الـdiff تحديدًا (طبيعته يدوية غير آلية بالكامل مقارنة بالمجموعتين 1+2، فاستحق مراجعة منفصلة قبل إطلاق أي طلب حقيقي عليه).

```diff
diff --git a/eppne-web/services/tenders-auctions.ts b/eppne-web/services/tenders-auctions.ts
index a33c2d7..d10c850 100644
--- a/eppne-web/services/tenders-auctions.ts
+++ b/eppne-web/services/tenders-auctions.ts
@@ -15,7 +15,7 @@ type LiveBidResponse = components['schemas']['LiveBidResponse'];
 export const TendersAuctionsService = {
   /**
    * إنشاء مناقصة جديدة
-   * POST /tenders/social/tenders
+   * POST /tenders-auctions/tenders
    * تدعم X-Tenant-ID
    */
   createTender: async (data: TenderCreate, headers?: { 'X-Tenant-ID'?: number }): Promise<TenderResponse> => {
@@ -24,7 +24,7 @@ export const TendersAuctionsService = {
       if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
         reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
       }
-      const { data: result } = await apiClient.post<TenderResponse>("/tenders/social/tenders", data, {
+      const { data: result } = await apiClient.post<TenderResponse>("/tenders-auctions/tenders", data, {
         headers: reqHeaders,
         withCredentials: true,
       });
@@ -36,7 +36,7 @@ export const TendersAuctionsService = {
 
   /**
    * تقديم عرض في مناقصة
-   * POST /tenders/social/bids
+   * POST /tenders-auctions/bids
    * تدعم Idempotency-Key و X-Tenant-ID
    */
   submitBid: async (
@@ -52,7 +52,7 @@ export const TendersAuctionsService = {
       if (idempotencyKey) {
         reqHeaders['Idempotency-Key'] = idempotencyKey;
       }
-      const { data: result } = await apiClient.post<TenderBidResponse>("/tenders/social/bids", data, {
+      const { data: result } = await apiClient.post<TenderBidResponse>("/tenders-auctions/bids", data, {
         headers: reqHeaders,
         withCredentials: true,
       });
@@ -64,7 +64,7 @@ export const TendersAuctionsService = {
 
   /**
    * تقييم عرض (لصاحب المناقصة)
-   * POST /tenders/social/bids/{bid_id}/evaluate
+   * POST /tenders-auctions/bids/{bid_id}/evaluate
    * تدعم Idempotency-Key و X-Tenant-ID
    */
   evaluateBid: async (
@@ -84,7 +84,7 @@ export const TendersAuctionsService = {
         reqHeaders['Idempotency-Key'] = idempotencyKey;
       }
       const { data: result } = await apiClient.post<TenderBidResponse>(
-        `/tenders/social/bids/${id}/evaluate`,
+        `/tenders-auctions/bids/${id}/evaluate`,
         data,
         { headers: reqHeaders, withCredentials: true }
       );
@@ -96,7 +96,7 @@ export const TendersAuctionsService = {
 
   /**
    * تقديم عرض في مزاد
-   * POST /tenders/social/auctions/{auction_id}/bids
+   * POST /tenders-auctions/auctions/{auction_id}/bids
    * تدعم Idempotency-Key و X-Tenant-ID
    */
   placeBid: async (
@@ -116,7 +116,7 @@ export const TendersAuctionsService = {
         reqHeaders['Idempotency-Key'] = idempotencyKey;
       }
       const { data: result } = await apiClient.post<LiveBidResponse>(
-        `/tenders/social/auctions/${id}/bids`,
+        `/tenders-auctions/auctions/${id}/bids`,
         data,
         { headers: reqHeaders, withCredentials: true }
       );
@@ -128,7 +128,7 @@ export const TendersAuctionsService = {
 
   /**
    * إغلاق مزاد
-   * POST /tenders/social/auctions/{auction_id}/close
+   * POST /tenders-auctions/auctions/{auction_id}/close
    * تدعم X-Tenant-ID
    */
   closeAuction: async (auctionId: number, headers?: { 'X-Tenant-ID'?: number }): Promise<void> => {
@@ -139,7 +139,7 @@ export const TendersAuctionsService = {
       if (headers?.['X-Tenant-ID'] !== undefined && headers['X-Tenant-ID'] !== null) {
         reqHeaders['X-Tenant-ID'] = String(headers['X-Tenant-ID']);
       }
-      await apiClient.post(`/tenders/social/auctions/${id}/close`, undefined, {
+      await apiClient.post(`/tenders-auctions/auctions/${id}/close`, undefined, {
         headers: reqHeaders,
         withCredentials: true,
       });
```

**الملخص:** 5 استدعاءات (`createTender`, `submitBid`, `evaluateBid`, `placeBid`, `closeAuction`) — كل واحد له سطر تعليق توثيقي + سطر كود، أي 10 أسطر متغيّرة بالضبط (مطابق لـ`git diff --stat` في §9: 20 سطر تغيير = 10 حذف + 10 إضافة). استبدال حرفي `"/tenders/social/"` → `"/tenders-auctions/"` فقط — صفر تغيير في الـheaders أو المنطق أو أسماء المتغيرات.

## 16. التحقق الحي المؤجَّل — `tenders-auctions.ts` (بعد موافقة صريحة على الـdiff §14.5)

**الاستدعاء المُختبَر:** `POST /tenders-auctions/tenders` (`createTender`) — أُختير لأنه أبسط استدعاءات الملف الخمسة وأقلها أثرًا جانبيًا محتملًا؛ الأربعة الباقية (`submitBid`, `evaluateBid`, `placeBid`, `closeAuction`) تعتمد على وجود مناقصة/مزاد حقيقي مسبقًا (تعقيد إعداد إضافي بلا داعٍ لمجرد تأكيد إصلاح البادئة).

**بيانات throwaway مُرسَلة** (`title` بادئة `P-URLPREFIX31-VERIFY-` للتعريف الواضح كبيانات اختبار معزولة):
```json
{
  "title": "P-URLPREFIX31-VERIFY-throwaway",
  "description": "throwaway tender created solely to verify bug #31 prefix fix, safe to delete",
  "scope_of_work": {"note": "throwaway"},
  "estimated_budget_mrusdt": 100,
  "submission_start": "2026-08-27T00:00:00Z",
  "submission_deadline": "2026-09-01T00:00:00Z"
}
```

**تحقق قبل/بعد (نفس منهجية §11):**
- **قبل:** `POST /api/tenders/social/tenders` (المسار القديم الخاطئ) → **404** — تأكيد إن المسار القديم ما اتغيرش (كان دايمًا خاطئ).
- **بعد:** `POST /api/tenders-auctions/tenders` (المسار المُصحَّح) → **403**، `{"detail":"Tenders & Auctions feature is not included in your current plan.","code":"PermissionDeniedError"}`.

| # | الملف | الاستدعاء المُختبَر | نتيجة HTTP | التصنيف | التفصيل |
|---|---|---|---|---|---|
| 21 | `tenders-auctions.ts` | `POST /tenders-auctions/tenders` | 403 (404→403، تأكيد وصول الطلب فعليًا) | (ب) عطل معروف مسبقًا | `PermissionDeniedError` — نفس جذر البند **#28** (`saas-service-catalog-missing-entries`)، الذي يذكر `tenders`/`auctions` صراحة كأحد الدومينات الثلاثة المؤكَّدة أصلًا منذ `batch2-audit-security-...`§3-أ. **البادئة اتصلحت بنجاح — الطلب وصل فعليًا لمنطق `saas` وليس لـ404 راوتنج** |

**تأكيد صفر بيانات throwaway متبقية:** الـ`403` رجع **قبل** أي كتابة DB (فحص الصلاحية بيحصل قبل `INSERT`) — تأكيد مباشر بـ`SELECT` مستقل من `sovereign_tenders` (الاسم الفعلي للجدول، مش `tenders`) بـ`title LIKE 'P-URLPREFIX31%'` → **صفر صف**. **لا حاجة لأي حذف/تنظيف — لم يُكتب أي شيء أصلًا.**

## 17. الحالة النهائية عند إغلاق الجلسة
- **21 ملف `services/*.ts` مُعدَّلة بالكامل** (19 مجموعة1 + `arbitration-syndicates.ts` + `tenders-auctions.ts`) — **صفر commit** حتى الآن، بانتظار توجيه المستخدم.
- **`tenders-auctions.ts`:** التعديل مُطبَّق + تحقق بنيوي (`tsc`، §10) + تحقق حي (§16) — **مكتمل بنفس معايير باقي الـ20 ملف**.
- **إجمالي 21/21 ملف الآن لهم تحقق حي مكتمل** (20 في §12 + `tenders-auctions.ts` في §16).
- **تنظيف ما بعد الجلسة:** الباك إند (`uvicorn`) **أُوقف** (تأكيد: صفر listener على المنفذ 8000، صفر عملية Python خلفية شغّالة). الفرونت إند (`next dev`) كان أُوقف مسبقًا (§11). كل الكوكيز/ملفات traceback/لوجّات مؤقتة في scratchpad/`/tmp` **محذوفة**. صفر بيانات throwaway باقية في DB (تأكيد §16). حاويات Docker (`postgres`, `redis`) تُركت شغّالة كما كانت **قبل** هذه الجلسة (لم تُنشَأ أو تُوقَف من هذه الجلسة).
- **صفر إصلاح لأي عطل backend ظهر** (`command`, `employment`, `insurance`, `invitations`, `social`, `tourism-sports`, `transport`, `zamakana`, `arbitration-syndicates`, `translation`) — بالضبط كما طُلب: "لا تحاول إصلاح أي عطل backend يظهر في هذه الجلسة".
- **صفر commit** — بانتظار توجيه المستخدم صراحة قبل أي `git commit`/`git push`.

---

# جلسة تنفيذية لاحقة (2026-08-26) — إصلاح 6 أعطال backend المكتشفة أثناء تحقق #31

**توجيه المستخدم:** جلسة تنفيذ مباشر (مش تشخيص) لـ6 أعطال backend من §12/§13 أعلاه، بترتيب محدَّد من الأبسط للأعقد، مع تحقق حي إجباري لكل بند + فحص فعلي (لا افتراض) لبند arbitration_syndicates تحديدًا.

## 18. الإصلاحات المُنفَّذة (بالترتيب المطلوب)

### 1. `translation/service.py:23,30` — استيراد singleton بلقب مضلِّل (#47)
**السبب الجذري:** `from app.core.redis_client import redis_client as get_redis_client` ثم `self.redis = get_redis_client()` — استدعاء كائن جاهز كأنه دالة مصنع.
**الإصلاح:** إزالة الـalias، استيراد `redis_client` مباشرة، استخدامه ككائن بلا `()`.
```diff
-from app.core.redis_client import redis_client as get_redis_client
+from app.core.redis_client import redis_client
...
-        self.redis = get_redis_client()
+        self.redis = redis_client
```

### 2. `arbitration_syndicates` — `list_user_cases` arity (#27)
**فحص الكود الفعلي أولًا (بدون افتراض)، النتيجة:**
- `repository.py:23` — `list_user_cases(self, user_id: int)`: **لا يوجد أي فلترة تينانت داخلها إطلاقًا** (تأكيد: صفر `self.tenant_id` في كل ملف الـrepository).
- `service.py:164` — الاستدعاء يمرر `tenant_id` كوسيط ثانٍ حقيقي (مش زيادة عرضية) — نفس نمط `get_case` المجاور في نفس الملف اللي فعليًا بيرفض الوصول لو `case.tenant_id != tenant_id` (فحص IDOR حقيقي).
- **الاستنتاج:** الفلترة بالتينانت **مفقودة فعليًا** من `list_user_cases` (مش موجودة بشكل ضمني)، وموديل `ArbitrationCase` عنده عمود `tenant_id` حقيقي (`nullable=False`). **القرار: إضافة `tenant_id` كوسيط رسمي + فلترة فعلية بيه** (الخيار الثاني من الاثنين اللي حددهما المستخدم) — يحل عطل الـ`TypeError` **و**يسكّر ثغرة IDOR كانت هتظهر لو اتصلح الـarity بالطريقة السهلة (حذف الوسيط) بمعزل عن إضافة الفلترة الفعلية.
```diff
-    async def list_user_cases(self, user_id: int):
+    async def list_user_cases(self, user_id: int, tenant_id: int):
         result = await self.db.execute(
             select(ArbitrationCase).where(
-                (ArbitrationCase.claimant_id == user_id) | (ArbitrationCase.respondent_id == user_id)
+                and_(
+                    (ArbitrationCase.claimant_id == user_id) | (ArbitrationCase.respondent_id == user_id),
+                    ArbitrationCase.tenant_id == tenant_id,
+                )
             ).order_by(ArbitrationCase.created_at.desc())
```

### 3. `command.get_dashboard` — `ResponseValidationError` (خارج backlog المرقَّم، phase16/`command-idor-fix`)
**الإصلاح:** تحويل كائن ORM (`CommandDashboard`) لـ`dict` قبل الإرجاع، بنفس نمط التحويل المستخدَم أصلًا في `academy/repository.py` (`{c: getattr(obj, c) for c in obj.__table__.columns.keys()}`) — أبسط من تعديل الـschema، وصفر تأثير على أي استهلاك آخر لنفس الكائن.
```diff
+        dashboard_dict = {c: getattr(dashboard, c) for c in dashboard.__table__.columns.keys()}
         return {
-            "dashboard": dashboard,
+            "dashboard": dashboard_dict,
```

### 4. `employment` — `required_skills`/`required_certificate_ids` = `None` (batch1)
**ملاحظة تقنية مهمة:** `default_factory=list` **لا يكفي وحده** — يعمل فقط لو الحقل غايب تمامًا، مش لو قيمته `None` صراحة (وهي حالة `from_attributes=True` مع عمود DB فعليًا `NULL`). الإصلاح الصحيح: `field_validator(mode="before")` يحوّل `None` → `[]` **قبل** فحص النوع.
```diff
+    @field_validator("required_skills", "required_certificate_ids", mode="before")
+    @classmethod
+    def _coerce_none_to_empty_list(cls, v):
+        return [] if v is None else v
```

### 5. `insurance.terms_and_conditions` — `NULL` في DB بلا `Optional` في الـschema (#46)
**الإصلاح (الأبسط، كما طلب المستخدم):** تحويل الحقل لـ`Optional[Dict[str, Any]] = None` مباشرة — يعكس واقع العمود (`nullable` فعليًا في DB)، بلا حاجة لـvalidator إضافي.
```diff
-    terms_and_conditions: Dict[str, Any] = Field(default_factory=dict, description="الشروط والأحكام")
+    terms_and_conditions: Optional[Dict[str, Any]] = Field(default=None, description="الشروط والأحكام")
```

### 6. `invitations` — `click_count`/`discount_percentage`/`gift_coins_amount`/`gift_currency` = `None` (#25، القائمة + `{id}`)
**نفس نمط #4 (`default_factory`/`default` لا يكفي مع `from_attributes` + `NULL` فعلي)** — لكن بمعاملة مختلفة للأرقام مقابل العملة (بالضبط كما طلب المستخدم: "0 للأرقام، None للعملة"):
- `discount_percentage`/`gift_coins_amount` (على `InvitationCreate`، موروثة في `InvitationResponse`): `field_validator(mode="before")` يحوّل `None` → `Decimal("0.0")`.
- `click_count` (على `InvitationResponse` مباشرة، مش موروثة): نفس المبدأ، `field_validator(mode="before")` يحوّل `None` → `0`.
- `gift_currency`: تغيير النوع لـ`Optional[str]` (بلا validator) — يسمح لـ`None` بالمرور كما هو، بدل فرض قيمة وهمية.
```diff
-    gift_currency: str = Field(default="MR_USDT", description="عملة الهدية")
+    gift_currency: Optional[str] = Field(default="MR_USDT", description="عملة الهدية")
...
+    @field_validator("discount_percentage", "gift_coins_amount", mode="before")
+    @classmethod
+    def _coerce_none_to_zero(cls, v):
+        return Decimal("0.0") if v is None else v
...
+    @field_validator("click_count", mode="before")
+    @classmethod
+    def _coerce_click_count_none_to_zero(cls, v):
+        return 0 if v is None else v
```

## 19. التحقق البنيوي
`py_compile` على كل الـ6 ملفات المُعدَّلة → **صفر خطأ syntax** في كل واحد.

## 20. التحقق الحي — نفس الاستدعاء الذي كان يفشل، بعد كل إصلاح

مستخدم throwaway (`TEST_super_a`/تينانت1) نفسه، `uvicorn` حي على `127.0.0.1:8000`. كل الطلبات **GET فقط** — صفر بيانات throwaway جديدة، صفر تنظيف مطلوب.

| # | الاستدعاء | قبل | بعد | ملاحظة |
|---|---|---|---|---|
| 1 | `GET /translation/languages` | 500 | **200** `[]` | |
| 2 | `GET /arbitration-syndicates/cases/me` | 500 | **200** `[]` | |
| 3 | `GET /command/dashboard` | 500 | **200** | `"dashboard":{"id":3,"tenant_id":1,...}` — dict حقيقي، صفر خطأ تحقق |
| 4 | `GET /employment/jobs/open` | 500 | **200** | يشمل الصف اللي فيه `required_certificate_ids:[1]` (اللي كان يكسر قبل كده) بجانب صفوف تانية |
| 5 | `GET /insurance/policies` | 500 | **200** | يشمل الصف القديم (`terms_and_conditions:{}`) بلا كراش |
| 6 | `GET /invitations/` | 500 | **200** | **تأكيد مباشر على الصف المُشكِل نفسه** (`id=1`, `P-CTOR-INV-ACCEPT-TEST`): `discount_percentage:"0.0"`, `gift_coins_amount:"0.0"`, `gift_currency:null`, `click_count:0` — بالضبط السلوك المطلوب (0 للأرقام، null للعملة) |

**6/6 نجحت.**

## 21. الحالة عند إغلاق هذه الجلسة التنفيذية
- **6 ملفات backend مُعدَّلة** (`translation/service.py`, `arbitration_syndicates/repository.py`, `command/service.py`, `employment/schemas.py`, `insurance/schemas.py`, `invitations/schemas.py`) — `git diff --stat`: **28 إضافة / 8 حذف**، صفر ملف إضافي متأثر.
- الباك إند **أُوقف** بعد التحقق (تأكيد: صفر listener على 8000، صفر عملية Python خلفية).
- صفر بيانات throwaway (كل الاختبارات GET).
- **صفر commit** حتى الآن لهذه الـ6 ملفات — بانتظار توجيه المستخدم.
