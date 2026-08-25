# ملخص Backlog نهائي (18 بند) — تصنيف: جلسة تصحيح مركزي واحدة مقابل إصلاح محلي لدومين واحد

**تاريخ الإعداد:** 2026-08-17
**الغرض:** الإجابة على السؤال "اجمع ملخص Backlog نهائي (الآن 18 بند) مع تمييز واضح: أيها يحتاج جلسة تصحيح مركزي واحدة (زي #14 audit_log، #11 InvoicingService) مقابل أيها محلي لدومين واحد".
**المصدر:** قائمة الـBacklog الكاملة (البند 1 إلى 18) في `PROGRESS_LOG.md`، قسم "📋 قائمة انتظار الجلسات المستقبلية"، مع التحديثات اللاحقة المُلحَقة بكل بند. لم يُضَف أي بند جديد هنا — هذا الملف تصنيف/تجميع فقط، صفر تعديل على المحتوى الأصلي.

---

## معيار التصنيف

| الفئة | التعريف | الإصلاح المطلوب |
|---|---|---|
| 🔴 **مركزي** | سبب جذري واحد (توقيع method تغيَّر، أو method/عمود مفقود في كلاس/موديل مشترك) يتكرر بنفس الشكل عبر **عدة دومينات مستقلة** (call sites مختلفة، كود مختلف حرفيًا لكل واحد) | إصلاح **الكلاس/الدالة المشتركة نفسها مرة واحدة** (أو `grep` شامل + تعديل كل الاستدعاءات دفعة واحدة في جلسة واحدة) — إصلاح دومين بمفرده لا يحل المشكلة في الباقي |
| 🟢 **محلي** | خطأ مرتبط بدومين واحد تحديدًا (منطق عمل خاص، أو موديل/schema خاص بدومين واحد) — لا يوجد دليل أو احتمال منطقي لتكراره في دومين تاني بنفس الشكل | إصلاح الموضع/الدومين المحدَّد فقط، لا يستدعي جلسة عابرة للدومينات |
| 🟡 **غير مؤكَّد الانتشار** | ثبت حدوثه في موضع واحد على الأقل، لكن لم يُنفَّذ `grep`/جرد شامل لتأكيد أو نفي وجوده في دومينات أخرى | يحتاج **جلسة جرد قصيرة أولاً** (`grep` بس، بدون إصلاح) لتحديد الفئة الحقيقية قبل تقرير حجم الجلسة اللازمة |
| ⚪ **ليس فئة باج** | بند إداري/قرار منتجي أو استكمال جلسة قائمة، مش نمط باج جديد قابل للتصنيف مركزي/محلي | يُدار حسب طبيعته الخاصة، غير مشمول بمعيار مركزي/محلي |

---

## الجدول الموحّد

| # | الاسم | الفئة | عدد الدومينات المؤكَّدة | ملاحظة الأولوية |
|---|---|---|---|---|
| 1 | `user-repository-get-by-id-audit` | 🔴 مركزي | 13 دومين (15 موضع) | فشل مالي/عمولة **صامت** مؤكَّد حيًا (`service_marketplace`) — أولوية مرتفعة |
| 2 | `duplicate-kwarg-audit` | 🔴 مركزي | 4+ دومينات | مؤكَّد سابقًا في جلسة `simpletenant-fix` |
| 3 | Phase 16 الأصلي (استكمال) | ⚪ ليس فئة باج | — | استكمال جلسة قائمة، مش نمط باج جديد |
| 4 | `silent-write-regression` (المتبقي) | ⚪ ليس فئة باج (متبقي من جلسة مركزية سابقة) | 1 دومين (`saas`، موضعان) | إغلاق أخير لجلسة `silent-write-regression-session-log.md` القائمة أصلًا |
| 5 | `sovereign_entities` (4 endpoints بلا مصادقة) | 🟢 محلي | 1 دومين | قرار منتجي معلَّق، مش باج تقني عابر للدومينات |
| 6 | `commerce.visa_webhook` | 🟢 محلي | 1 دومين | مراجعة أمنية مخصَّصة لبوابة دفع واحدة |
| 7 | `redis-client-wrapper-missing-methods` | 🔴 مركزي | 2 مؤكَّدة (`ai_agents`, `projects`) + احتمال انتشار غير مفحوص | `RedisClientWrapper` كلاس مشترك — نفس السبب الجذري (subset ناقص من مكتبة `redis`) |
| 8 | `user-repository-get-user-audit` | 🔴 مركزي | 5 دومينات (6 مواضع) | `UserRepository.get_user()` غير موجودة أصلًا — نفس الاستدعاء الخاطئ متكرر حرفيًا |
| 9 | `saas-control-service-missing-methods` | 🔴 مركزي | 2+ مؤكَّدة (`digital_twin`, `employment`) | 🔴🔴 **محظور الإصلاح قبل مراجعة تقرير `invitations` الحرج** — راجع تحذير مخصَّص أسفل |
| 10 | `affiliate-service-missing-methods` | 🔴 مركزي | 6+ دومينات (كل دومين بيستخدم `_register_affiliate_commission`) | إصلاح الكلاس مرة واحدة يحل كل الدومينات دفعة واحدة |
| 11 | `realestate-invoicing-savepoint-conflict` (+ امتداد identity) | 🔴 مركزي | 4+ دومينات (`realestate`, `arbitration_syndicates`, `insurance`, `invitations`) | 🔴🔴 **أعلى أولوية في كل الـBacklog** — جلسة `invitations-user-registration-savepoint-leak` مقررة، تُنفَّذ التالية مباشرة |
| 12 | `saas-control-service-wrong-arity-call` | 🔴 مركزي | 6+ دومينات (`service_marketplace`, `social`, `tenders_auctions`, `tourism_sports`, `transport`, `zamakana`) | نفس التوقيع الجديد لـ`can_access_service`، نفس الإصلاح يطبَّق حرفيًا في كل دومين |
| 13 | `invoicing-create-invoice-wrong-kwarg` (الجزء الخاص باسم الـkwarg نفسه) | 🟡 غير مؤكَّد الانتشار | 1 مؤكَّد (`service_marketplace`) | يحتاج `grep` شامل لباقي الـ12 دومين المستخدمة لـ`InvoicingService` — **امتداده الداخلي (كراش `audit_log` جوه `create_invoice`) مغطّى بالفعل تحت #14 كمركزي 100%** |
| 14 | `audit-log-wrong-kwargs` | 🔴 مركزي (الأوسع انتشارًا في كل الـBacklog) | عشرات المواضع عبر كل دومين تقريبًا + **داخل `InvoicingService.create_invoice()` نفسها** | المثال المرجعي اللي طلبته — إصلاح دالة `audit_log()` الواحدة (أو تحديث كل الاستدعاءات دفعة واحدة) يحل كل الدومينات فورًا |
| 15 | `ai-governance-check-and-consume-wrong-kwarg` | 🔴 مركزي | 8+ دومينات | بعضها محمي (`insurance`, `tenders_auctions`, `transport`)، بعضها **غير محمي** (`arbitration_syndicates`, `manufacturing`, `logistics`, `social`, `zamakana`) — الإصلاح المركزي واحد لكل الحالتين |
| 16 | `ai-agents-execute-agent-action-wrong-kwarg` | 🔴 مركزي | 9+ دومينات | أغلبها محمي بـ`try/except` (فشل هادئ) — نفس السبب الجذري، نفس الإصلاح لكل الدومينات |
| 17 | `arbitration-case-model-idempotency-key-mismatch` | 🟢 محلي | 1 دومين (`arbitration_syndicates`) | مشكلة schema في موديل `ArbitrationCase` تحديدًا — لا سبب جذري مشترك مع أي دومين تاني |
| 18 | `finance-service-create-invoice-does-not-exist` | 🟢 محلي (مبدئيًا) | 1 دومين (`transport`، موضعان) | خطأ نسخ/استدعاء محلي (استدعاء method مش موجودة على `FinanceService`) — لم يُفحَص شموليًا لكن لا يوجد سبب جذري "توقيع تغيَّر" يبرر التكرار |
| 19 | `projects-schema-model-field-mismatch` [أُضيف 2026-08-24، بعد تجميد هذا الملف] | 🟢 محلي | 1 دومين (`projects`، 3 موديلات: `Project`, `Contribution`, `ProjectUpdate`) | فئة فرعية جديدة من `constructor-mismatch` — عدم تطابق **schema↔model** (حقول Pydantic بلا أعمدة SQLAlchemy مقابلة)، مش duplicate/unexpected-kwarg زي #2/#12/#15/#16. يمنع `create_project` بالكامل، و5 من 6 أنواع `add_contribution`، و`add_project_update` بالكامل. مُكتشَف أثناء التحقق الحي لجلسة `projects-idor-fix` — راجع `PROGRESS_LOG.md` (جدول الـBacklog النشط) و`.claude/reports/projects-idor-fix-session-log.md` §4.1 |
| 20 | `academy-create-bootcamp-instructor-id-mismatch` [أُضيف 2026-08-24، بعد تجميد هذا الملف] | 🟢 محلي | 1 دومين (`academy`، موديل `Bootcamp`) | نفس فئة #19 (schema↔model) — `AcademyRepository.create_bootcamp()` بتمرر `instructor_id` لـ`Bootcamp(**kwargs)`، لكن جدول `academy_bootcamps` الفعلي **بلا عمود `instructor_id` إطلاقًا** (تأكيد `\d academy_bootcamps` حي). `TypeError` فوري، `POST /academy/bootcamps` معطوبة بالكامل لأي طلب. مُكتشَف أثناء التحقق الحي لجلسة `academy-idor-fix` — راجع `.claude/reports/academy-idor-fix-session-log.md` §1/§3.4 |
| 21 | `invoicing-invoice-response-metadata-collision` [أُضيف 2026-08-25، بعد تجميد هذا الملف] | 🟢 محلي | 1 دومين (`invoicing`، `InvoiceResponse`) | فئة مختلفة عن #19/#20 (schema↔model) — `InvoiceResponse.metadata` (حقل Pydantic) يصطدم بخاصية `metadata` المحجوزة في SQLAlchemy `Base` بدل عمود `invoice_metadata` الفعلي، فيفشل `model_validate(from_attributes=True)` بـ`400` مضلِّل **لكل استدعاء `POST /invoicing/invoices` بلا استثناء** — رغم أن الكتابة في DB تنجح فعليًا قبل هذا الخطأ (نفس نمط "رد مضلِّل مع نجاح كتابة حقيقية" الموثَّق سابقًا في `commerce.handle_visa_webhook`/`ai_governance.check-and-consume`). مُكتشَف أثناء التحقق الحي لجلسة `batch1-audit-security-employment-invitations-communications-invoicing` — راجع `.claude/reports/batch1-audit-security-employment-invitations-communications-invoicing.md` §4-أ |
| 22 | `invitations-leads-route-ordering` [أُضيف 2026-08-25، بعد تجميد هذا الملف] | 🟢 محلي | 1 دومين (`invitations`، `router.py`) | فئة مختلفة تمامًا (باج ترتيب تسجيل routes، مش constructor/schema) — نفس نمط `sovereign_entities.list_templates/list_components` الموثَّق سابقًا: `GET /{invitation_id}` مُسجَّلة قبل `GET /leads` (وعلى الأرجح `/campaigns`/`/tickets`) في نفس الملف، فأي طلب لـ`/invitations/leads` يقع تحت نمط `/{invitation_id}` (int) أولًا ويُرفض بـ`422` قبل ما يوصل للهاندلر الحقيقي. **لا يلغي خطورة IDOR الأصلية** — القراءة/الكتابة المباشرة بالـID (`GET/PUT /leads/{id}`) شغالة بمعزل عن هذا الباج. مُكتشَف أثناء التحقق الحي لنفس الجلسة أعلاه — راجع نفس التقرير §4.2 |
| 23 | `bleach-clean-none-crash` [أُضيف 2026-08-25، بعد تجميد هذا الملف] | 🔴 مركزي (نمط واسع، مؤكَّد حيًا في `invitations` فقط لحد الآن) | **13 دومين مؤكَّدة عبر `grep`** (`agritech`, `ai_agents`, `command`, `employment`, `invitations`, `logistics`, `manufacturing`, `realestate`, `social`, `tenders_auctions`, `tourism_sports`, `transport`, `zamakana`) — **89 موضع** بنمط `bleach.clean(data.get(field, ""), ...)` بلا حارس `if data.get(field) else None` | **نفس فئة `duplicate-kwarg-audit` (#2) بالضبط من حيث الانتشار** — السبب الجذري: `.get(key, default)` بترجّع الـdefault لو الـkey غايب بس، **مش لو قيمته `None` صراحة** — وأي حقل `Optional[str]` في schema بيتحط `None` صراحة في `model_dump()` لو العميل ما بعتوش، فـ`bleach.clean(None, ...)` بيرمي `TypeError` فوري. **مؤكَّد حيًا بالتنفيذ الفعلي في `invitations.create_invitation`/`create_campaign` فقط** (جلسة `batch1-audit-security-...`) — باقي الـ12 دومين **مطابقة بالـgrep بس، لم تُختبَر حيًا بعد** (نفس منهجية تصنيف #2/#7/#8 وقت اكتشافها). **لا يوجد سبب جذري "دالة واحدة" يمكن إصلاحها مركزيًا** (كل موضع نداء `bleach.clean` مباشر، مش عبر wrapper مشترك) — الإصلاح المقترَح: `bleach.clean(data.get(field) or "", ...)` بدل `.get(field, "")` في كل موضع، أو wrapper مركزي `safe_clean()` واحد يُستبدَل بيه كل الـ89 نداء. **أولوية أعلى من أغلب بنود المجموعة أ لأنه بيمنع وظائف إنشاء أساسية (مش قراءة/تعديل) عبر 13 دومين محتمَل** |
| 24 | `invitations-create-invitation-fully-broken` [أُضيف 2026-08-25، بعد تجميد هذا الملف] | 🟢 محلي (لكن **مُركَّب من عطلين متتاليين**، أحدهما جزء من #23) | 1 دومين (`invitations`، `service.py`) | 🔴🔴 **`POST /invitations/` (إنشاء دعوة) معطوبة بالكامل حاليًا لأي طلب فعليًا ناجح — مش حافة نادرة، دي الوظيفة الأساسية للدومين اللي كله سُمي على اسمها.** عطلان متتاليان: **(أ)** `service.py:170-172` (`sanitized_title`/`sanitized_message`/`sanitized_identifier` عبر `bleach.clean(data.get(field,""),...)` بلا حارس) — نفس نمط #23، أول عائق يواجه أي طلب فيه `title`/`custom_message`/`target_entity_identifier` بقيمة `None` صراحة (الحالة الافتراضية لأي عميل ما حددش القيم دي). **حتى لو اتصلح #23**، عطل ثانٍ منفصل تمامًا يمنع نفس الـendpoint: **(ب)** `service.py:113` (`_assign_ai_agent`) — `agents[0]` على كائن `PaginatedResponse[AIAgentResponse]` (غير قابل للفهرسة بـ`[0]`) بدل قائمة خام، `TypeError: 'PaginatedResponse[AIAgentResponse]' object is not subscriptable`. **الإصلاح الصحيح لازم الاثنين معًا** — إصلاح (أ) وحده يوصّل الطلب لعطل (ب) فورًا، الـendpoint لسه معطوب. مؤكَّد حيًا بالتنفيذ الفعلي (تسلسل الأعطال ظهر بالترتيب ده بالضبط، مرتين، أثناء محاولة اختبار المسار الشرعي في جلسة `batch1-audit-security-...`) — راجع نفس التقرير §10.3 |
| 25 | `invitations-legacy-invitation-rows-response-validation-error` [أُضيف 2026-08-25، بعد تجميد هذا الملف] | 🟢 محلي | 1 دومين (`invitations`، جدول `sovereign_invitations_v2`) | صفوف throwaway قديمة جدًا من جلسات سابقة (`P-CTOR-INV-*`, `P-SAVEPOINT-FIX-*`، الصفوف `id=1,2,3`) اتكتبت قبل ما تتضاف أعمدة `discount_percentage`/`gift_coins_amount`/`gift_currency`/`click_count` كإلزامية (non-null) في الـschema الحالي — قيمتها `NULL` فعليًا في DB، فـ`GET /invitations/{id}` عليها يفشل بـ`ResponseValidationError` (4 أخطاء تحقق). **لا يؤثر على أي صف جديد يُنشأ بعد إصلاح #24** — محصور بالبيانات القديمة تحديدًا. الحل: إما migration لملء قيم افتراضية، أو حذف الصفوف الثلاثة (throwaway بالكامل، بادئة `P-`)، أو تخفيف الـschema لـ`Optional`. مؤكَّد حيًا (جلسة `batch1-audit-security-...` §10.3) |
| 26 | `invitations-update-not-found-500` [أُضيف 2026-08-25، بعد تجميد هذا الملف] | 🟢 محلي (لم يُفحَص انتشاره خارج `invitations`) | 1 دومين مؤكَّد (`invitations`: `update_lead`, `update_ticket`) | تحديث مورد غير موجود (سواء لأنه ينتمي لتينانت تاني بعد إصلاح IDOR، أو لأنه غير موجود إطلاقًا حتى ضمن تينانت المستخدم — مؤكَّد بتجربة معزولة `PUT /leads/9999`) بيرجّع `500 Internal Server Error` بدل `404` نظيف. **آمن تمامًا من ناحية الأمان — صفر كتابة فعلية تحصل** (مؤكَّد بـ`SELECT` مستقل)، بس رمز الخطأ غلط ويكشف تفاصيل تنفيذ داخلية بدل رد نظيف. لم يُفحَص هل نفس النمط موجود في `update_invitation`/`update_campaign` (الأخيرة رجّعت `403` نظيف مش `500` في نفس الجلسة — يحتاج توضيح ليه الفرق) أو دومينات تانية. مؤكَّد حيًا (جلسة `batch1-audit-security-...` §10.2/10.3) |

**ملاحظة [2026-08-24]:** البندان #19 و#20 أُضيفا بعد تجميد هذا الملف (2026-08-17) بتوجيه صريح من المستخدم في جلستي `projects-idor-fix`/`academy-idor-fix`، خلافًا لملاحظة السطر 5 (الملف تصنيف فقط، لا يُضاف له بند جديد عادةً) — المصدر الكامل والتفاصيل في التقارير المذكورة مباشرة، هنا فقط للتصنيف السريع.

**ملاحظة [2026-08-25]:** البنود #21 إلى #26 أُضيفت بنفس الاستثناء، بتوجيه صريح من المستخدم في جلسة `batch1-audit-security-employment-invitations-communications-invoicing`. صفر تنفيذ إصلاح لأي منها بعد — تصنيف/توثيق فقط. **🔴 أولوية خاصة: #24 (`create_invitation` معطوبة بالكامل) أعلى أولوية من أغلب بنود المجموعة أ التالية** — مش خلل حافة، دي الوظيفة الأساسية لدومين كامل غير قابلة للاستخدام إطلاقًا حاليًا (صفر دعوة واحدة ممكن تُنشأ فعليًا عبر الـAPI، بغض النظر عن أي إصلاح IDOR).

---

## 🔴 المجموعة أ — تحتاج جلسة تصحيح مركزي واحدة (10 بنود: #1, #2, #7, #8, #9, #10, #11, #12, #14, #15, #16, #23)

هذه البنود **كلها من نفس الشكل البنيوي**: كلاس/دالة مشتركة واحدة (`UserRepository`, `RedisClientWrapper`, `SaaSControlService`, `AffiliateService`, `InvoicingService`, `audit_log()`, `AIGovernanceService`, `AIAgentsService`) تغيَّر توقيعها أو ناقصة method — ونفس الخطأ **منسوخ حرفيًا** في كل دومين استخدمها. إصلاح دومين واحد بمفرده **لا يحل** الباقي؛ الإصلاح الصحيح هو تعديل الكلاس/الدالة نفسها (أو `grep` شامل + تعديل كل الاستدعاءات دفعة واحدة) في **جلسة واحدة مخصَّصة لكل بند**.

### ترتيب الأولوية المقترَح داخل هذه المجموعة

0. **#24 (`invitations-create-invitation-fully-broken`, محلي لكن مُدرَج هنا بالأولوية) و#23 (`bleach-clean-none-crash`)** — 🔴🔴 **أولوية تسبق حتى #11/#9 من ناحية الأثر الوظيفي (لا تسبقهما من ناحية الخطورة الأمنية/المالية)**: #24 يعني وظيفة "إنشاء دعوة" — جوهر دومين `invitations` — **معطوبة 100%، صفر استخدام ناجح ممكن حاليًا عبر الـAPI**، بغض النظر عن أي إصلاح IDOR. إصلاح #23 (النمط المركزي) هو نصف الحل (العطل الأول من عطلين)، فيستحق معالجة فورية موازية لـ#11/#9 مش بعدهما — الفرق إن #11/#9 خطورتهما **أمنية/مالية** (بيانات يتيمة، ثغرة IDOR)، و#24/#23 خطورتهما **وظيفية بحتة** (منع كامل لميزة، صفر تسريب/فقدان بيانات).
1. **#11 (`realestate-invoicing-savepoint-conflict` + امتداد `invitations`)** — 🔴🔴 **أعلى أولوية مطلقة في كل الـBacklog**. بيانات هوية حقيقية يتيمة على القرص (`users id=52`, `p_ctor_inv_newuser@eppne.com`). جلسة `invitations-user-registration-savepoint-leak` **مقررة بالفعل كالجلسة التالية مباشرة** بعد الانتهاء من مراجعة دفعة `constructor-mismatch` الحالية — راجع `.claude/reports/CRITICAL-invitations-accept-orphaned-user-no-wallet.md`.
2. **#9 (`saas-control-service-missing-methods`)** — 🔴🔴 **محظور إصلاحه بمعزل عن #11**: `get_active_subscription` المفقودة هي نفسها اللي بتحجب (بالصدفة، مش بتصميم آمن) ثغرة `invitations` حاليًا. أي إصلاح لـ#9 **قبل** إغلاق #11 هيفتح الثغرة فورًا في كل دومين بيستخدم نمط `get_active_subscription` (`digital_twin`, `employment`، وربما أكتر).
3. **#14 (`audit-log-wrong-kwargs`)** — الأوسع انتشارًا رقميًا في كل الـBacklog (عشرات المواضع + داخل `InvoicingService` نفسها) — بمجرد إغلاق #11/#9، هذا البند يستاهل الأولوية التالية لأنه بيمنع **كل** عملية `create_invoice`/`audit_log` ناجحة ظاهريًا من الاكتمال فعليًا عبر المشروع كله تقريبًا.
4. **#1 (`user-repository-get-by-id-audit`)** — فشل مالي صامت مؤكَّد حيًا (عمولات affiliate بتضيع بلا أي إشارة خطأ) — أولوية عالية لأنه صامت.
5. **#10 (`affiliate-service-missing-methods`)** — مرتبط مباشرة بـ#1 (نفس الدالة المساعدة `_register_affiliate_commission` في كل دومين تقريبًا) — يستحسن إصلاحهما في نفس الجلسة أو جلستين متتاليتين.
6. **#12، #15، #16** — نفس العائلة (استدعاءات بمعامل `tenant_id` زيادة بعد نقله للـconstructor) — **🔴 تصحيح [2026-08-17]، بعد تدقيق تقني كامل لكل موضع فعلي: التجميع في جلسة واحدة موحّدة كان افتراضًا غير دقيق.** #12 فعلاً متطابق 100% (6/6 مواضع بسيطة). لكن #15 (7 من 13 موضع = 54%) و#16 (13 من 18 موضع = 72%) فيهم نسبة كبيرة من الحالات "المركّبة" (زي `arbitration_syndicates`) — مش استثناء نادر زي ما كان موثَّق، دي الأغلبية فعليًا. التفاصيل الكاملة + جدول مقارَنة موضع بموضع في `.claude/reports/constructor-mismatch-backlog-12-15-16-homogeneity-audit.md`. **القرار المُحدَّث: #12 جلسة ميكانيكية مستقلة، #15+#16 يُقسَّموا لـ3 جلسات فرعية (ميكانيكي / مركّب-سهل / مركّب-صعب) بدل جلسة واحدة.**
7. **#8، #7، #2** — أولوية أقل نسبيًا (أعداد مواضع أصغر، بعضها محمي بـ`try/except` فبيفشل بهدوء) — تُجدوَل بعد ما سبق.

---

## 🟢 المجموعة ب — محلية لدومين واحد (10 بنود: #5, #6, #17, #18, #19, #20, #21, #22, #25, #26 — + #24 مُدرَج تصنيفيًا هنا لكن بأولوية استثنائية أعلى، راجع بند 0 بالمجموعة أ)

هذه البنود **لا تشترك في سبب جذري مع أي بند تاني** — كل واحد مرتبط بمنطق/schema/قرار خاص بدومين واحد فقط. لا تحتاج جلسة عابرة للدومينات؛ إصلاح كل واحد منفصل تمامًا عن الباقي.

- **#5 (`sovereign_entities`)** — قرار منتجي (هل الـ4 endpoints دي المفروض تفضل بلا مصادقة ولا لأ) — مش باج تقني.
- **#6 (`commerce.visa_webhook`)** — مراجعة أمنية خاصة ببوابة دفع واحدة (توقيع، تكرار، مصدر tenant_id) — بطبيعتها محلية.
- **#17 (`arbitration-case-model-idempotency-key-mismatch`)** — عمود مفقود في موديل SQLAlchemy واحد (`ArbitrationCase`) — إصلاحه هو إضافة العمود، صفر علاقة بأي دومين تاني.
- **#18 (`finance-service-create-invoice-does-not-exist`)** — استدعاء خاطئ لـmethod غير موجودة، محصور في `transport` فقط حاليًا. **تحفظ:** لم يُنفَّذ `grep` شامل لتأكيد عدم وجود نفس الخطأ (`self.finance.create_invoice`) في دومين تاني — لو حبيت تأكيد 100%، ده أقرب لبند #13 (يحتاج جرد سريع أولاً) أكتر من كونه محلي مؤكَّد نهائيًا.
- **#19 (`projects-schema-model-field-mismatch`)** [أُضيف 2026-08-24] — 3 حقول/جداول Pydantic schema بلا أعمدة SQLAlchemy مقابلة، محصورة في دومين `projects` وحده (`Project`, `Contribution`, `ProjectUpdate`) — صفر سبب جذري مشترك مع أي دومين تاني.
- **#20 (`academy-create-bootcamp-instructor-id-mismatch`)** [أُضيف 2026-08-24] — `instructor_id` بيتمرر لـ`Bootcamp(**kwargs)` لكن العمود غير موجود في الموديل الفعلي، محصور في `academy.create_bootcamp` وحدها — صفر سبب جذري مشترك مع أي دومين تاني.
- **#21 (`invoicing-invoice-response-metadata-collision`)** [أُضيف 2026-08-25] — تصادم اسم حقل `metadata` مع `SQLAlchemy.Base.metadata`، محصور في `InvoiceResponse`/`Invoice` بدومين `invoicing` وحده — صفر سبب جذري مشترك مع أي دومين تاني.
- **#22 (`invitations-leads-route-ordering`)** [أُضيف 2026-08-25] — باج ترتيب تسجيل routes، محصور في `invitations/router.py` وحده (نفس الفئة الميكانيكية زي `sovereign_entities` سابقًا، لكن حالة مستقلة تمامًا) — صفر سبب جذري مشترك مع أي دومين تاني.
- **#24 (`invitations-create-invitation-fully-broken`)** [أُضيف 2026-08-25] — مُركَّب من عطلين (أحدهما مظهر محلي لـ#23 المركزي، والتاني `_assign_ai_agent` محلي بحت) — **🔴🔴 أولوية عالية استثنائية رغم كونه محليًا**: يمنع الوظيفة الأساسية للدومين بالكامل، راجع الملاحظة أعلى.
- **#25 (`invitations-legacy-invitation-rows-response-validation-error`)** [أُضيف 2026-08-25] — بيانات throwaway قديمة تالفة (NULL في أعمدة صارت إلزامية لاحقًا)، محصور في 3 صفوف بجدول `sovereign_invitations_v2` — صفر سبب جذري مشترك مع أي دومين تاني.
- **#26 (`invitations-update-not-found-500`)** [أُضيف 2026-08-25] — معالجة أخطاء ناقصة في `update_lead`/`update_ticket` (500 بدل 404)، محصور في `invitations` (لم يُفحَص انتشاره) — صفر سبب جذري مشترك مؤكَّد مع أي دومين تاني حاليًا.

---

## 🟡 المجموعة ج — غير مؤكَّدة الانتشار، تحتاج جرد قبل التصنيف النهائي (بند واحد: #13)

- **#13 (`invoicing-create-invoice-wrong-kwarg`)** — الجزء الخاص باسم الـkwarg (`tenant_id=` بدل `entity_id=`) مؤكَّد في `service_marketplace` بس لحد الآن، لكن التقرير نفسه ينص صراحة على إن `grep` شامل لباقي الـ12 دومين المستخدمة لـ`InvoicingService.create_invoice` **لم يُنفَّذ بعد**. **ملاحظة مهمة:** امتداده الأخطر (كراش `audit_log` **داخل** `create_invoice()` نفسها، بغض النظر عن صحة اسم الـkwarg الخارجي) **مؤكَّد بالفعل كمركزي 100%** ومُدمَج فعليًا تحت البند #14 — لذلك القرار العملي هو: **عالج #13 كجزء من جلسة #14 مباشرة**، ولا داعي لجلسة `grep` منفصلة قائمة بذاتها.

---

## ⚪ بنود إدارية / ليست أنماط باج (بندان: #3, #4)

- **#3 (Phase 16 الأصلي)** — استكمال جلسة سابقة (`phase16-session-log.md`)، مش نمط باج مكتشف حديثًا.
- **#4 (`silent-write-regression` المتبقي)** — موضعان أخيران (`saas.process_auto_renewals` فرع `except`, `saas.can_access_service`) من جلسة `silent-write-regression-session-log.md` القائمة أصلًا وشبه مكتملة (89 موضع اتغطوا already) — إغلاق أخير، مش جلسة مركزية جديدة.

---

## الخلاصة العملية

| السؤال | الإجابة |
|---|---|
| كام بند يحتاج جلسة مركزية واحدة فعلية؟ | **10 بنود** (#1, #2, #7, #8, #9, #10, #11, #12, #14, #15, #16, #23 — بعضها ممكن يتجمّع في نفس الجلسة زي #12+#15+#16) |
| كام بند محلي فعلاً، صفر حاجة لجلسة عابرة؟ | **11 بند** (#5, #6, #17, #18, #19, #20, #21, #22, #24, #25, #26 — #24 محلي تصنيفيًا لكن بأولوية استثنائية أعلى، راجع بند 0 بالمجموعة أ) |
| كام بند يحتاج جرد سريع الأول قبل تحديد نوعه؟ | **بند واحد** (#13 — لكن عمليًا يُعالَج ضمن جلسة #14) |
| كام بند إداري بس؟ | **بندان** (#3, #4) |
| إيه أعلى أولوية مطلقة دلوقتي (أمنية/مالية)؟ | **#11 ثم #9** (بالترتيب ده تحديدًا — عكس الترتيب ممنوع لأنه بيفتح ثغرة هوية حقيقية) |
| إيه أعلى أولوية وظيفية (منع كامل لميزة، بمعزل عن الأمان)؟ | **#24 ثم #23** — `invitations.create_invitation` معطوبة 100% حاليًا، صفر دعوة واحدة ممكن تُنشأ عبر الـAPI |
