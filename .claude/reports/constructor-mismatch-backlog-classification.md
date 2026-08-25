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
| 23 | `bleach-clean-none-crash` [أُضيف 2026-08-25، بعد تجميد هذا الملف] | 🔴 **مركزي — بند منتشر مستقل، مفصول عمدًا عن #24-#26 (المحلية لـ`invitations`)** | **13 دومين، 52 موضع مؤكَّد عبر `grep`** | نمط عابر لـ13 دومين، **معاملته زي `duplicate-kwarg-audit` (#2)** — راجع القسم المخصَّص "🔴 بند منتشر مستقل — #23" مباشرة بعد هذا الجدول، فيه قائمة الـ13 دومين كاملة بعدد المواضع لكل واحد. صفر إصلاح الآن، توثيق موسَّع فقط |
| 24 | `invitations-create-invitation-fully-broken` [أُضيف 2026-08-25، بعد تجميد هذا الملف] | 🟢 محلي (لكن **مُركَّب من عطلين متتاليين**، أحدهما جزء من #23) | 1 دومين (`invitations`، `service.py`) | 🔴🔴 **`POST /invitations/` (إنشاء دعوة) معطوبة بالكامل حاليًا لأي طلب فعليًا ناجح — مش حافة نادرة، دي الوظيفة الأساسية للدومين اللي كله سُمي على اسمها.** عطلان متتاليان: **(أ)** `service.py:170-172` (`sanitized_title`/`sanitized_message`/`sanitized_identifier` عبر `bleach.clean(data.get(field,""),...)` بلا حارس) — نفس نمط #23، أول عائق يواجه أي طلب فيه `title`/`custom_message`/`target_entity_identifier` بقيمة `None` صراحة (الحالة الافتراضية لأي عميل ما حددش القيم دي). **حتى لو اتصلح #23**، عطل ثانٍ منفصل تمامًا يمنع نفس الـendpoint: **(ب)** `service.py:113` (`_assign_ai_agent`) — `agents[0]` على كائن `PaginatedResponse[AIAgentResponse]` (غير قابل للفهرسة بـ`[0]`) بدل قائمة خام، `TypeError: 'PaginatedResponse[AIAgentResponse]' object is not subscriptable`. **الإصلاح الصحيح لازم الاثنين معًا** — إصلاح (أ) وحده يوصّل الطلب لعطل (ب) فورًا، الـendpoint لسه معطوب. مؤكَّد حيًا بالتنفيذ الفعلي (تسلسل الأعطال ظهر بالترتيب ده بالضبط، مرتين، أثناء محاولة اختبار المسار الشرعي في جلسة `batch1-audit-security-...`) — راجع نفس التقرير §10.3 |
| 25 | `invitations-legacy-invitation-rows-response-validation-error` [أُضيف 2026-08-25، بعد تجميد هذا الملف] | 🟢 محلي | 1 دومين (`invitations`، جدول `sovereign_invitations_v2`) | صفوف throwaway قديمة جدًا من جلسات سابقة (`P-CTOR-INV-*`, `P-SAVEPOINT-FIX-*`، الصفوف `id=1,2,3`) اتكتبت قبل ما تتضاف أعمدة `discount_percentage`/`gift_coins_amount`/`gift_currency`/`click_count` كإلزامية (non-null) في الـschema الحالي — قيمتها `NULL` فعليًا في DB، فـ`GET /invitations/{id}` عليها يفشل بـ`ResponseValidationError` (4 أخطاء تحقق). **لا يؤثر على أي صف جديد يُنشأ بعد إصلاح #24** — محصور بالبيانات القديمة تحديدًا. الحل: إما migration لملء قيم افتراضية، أو حذف الصفوف الثلاثة (throwaway بالكامل، بادئة `P-`)، أو تخفيف الـschema لـ`Optional`. مؤكَّد حيًا (جلسة `batch1-audit-security-...` §10.3) |
| 26 | `invitations-update-not-found-500` [أُضيف 2026-08-25، بعد تجميد هذا الملف] | 🟢 محلي (لم يُفحَص انتشاره خارج `invitations`) | 1 دومين مؤكَّد (`invitations`: `update_lead`, `update_ticket`) | تحديث مورد غير موجود (سواء لأنه ينتمي لتينانت تاني بعد إصلاح IDOR، أو لأنه غير موجود إطلاقًا حتى ضمن تينانت المستخدم — مؤكَّد بتجربة معزولة `PUT /leads/9999`) بيرجّع `500 Internal Server Error` بدل `404` نظيف. **آمن تمامًا من ناحية الأمان — صفر كتابة فعلية تحصل** (مؤكَّد بـ`SELECT` مستقل)، بس رمز الخطأ غلط ويكشف تفاصيل تنفيذ داخلية بدل رد نظيف. لم يُفحَص هل نفس النمط موجود في `update_invitation`/`update_campaign` (الأخيرة رجّعت `403` نظيف مش `500` في نفس الجلسة — يحتاج توضيح ليه الفرق) أو دومينات تانية. مؤكَّد حيًا (جلسة `batch1-audit-security-...` §10.2/10.3) |
| 27 | `arbitration-syndicates-repository-missing-methods` [أُضيف 2026-08-25، بعد تجميد هذا الملف] | 🟢 محلي | 1 دومين (`arbitration_syndicates`) | `service.py` يستدعي 5 دوال `repository.py` غير موجودة إطلاقًا (`get_cases_by_claimant`, `get_election_votes`, `get_syndicate_memberships`, `list_syndicate_elections`, `list_user_licenses`) + دالتان معرَّفتان بتوقيع أضيق مما يُستدعى بهما (`list_user_cases(user_id)` مقابل استدعاء بوسيطين، `list_candidates(election_id)` مقابل استدعاء بوسيطين) — يعطّل 4 endpoints بالكامل (`GET /cases/me`, `GET /syndicates/{id}/elections`, `GET /elections/{id}/candidates` بـ`TypeError`/`AttributeError`/500 مؤكَّد حيًا، `GET /licenses/me` بيرجّع `[]` دايمًا بصمت لأن `hasattr` بترجع `False`). محصور بموديل/repository دومين واحد — صفر سبب جذري مشترك مع أي دومين تاني. مؤكَّد حيًا جزئيًا (`GET /cases/me`، `GET /elections/{id}/candidates`) — راجع `.claude/reports/batch2-audit-security-service-marketplace-tenders-auctions-arbitration-syndicates.md` §4، §7.7 |
| 28 | `saas-service-catalog-missing-entries` [أُضيف 2026-08-25، بعد تجميد هذا الملف] | 🟢 محلي (بيانات إعداد، مش كود) | 2 دومين (`service_marketplace`, `tenders_auctions`) | `saas_service_catalog` **بلا أي صف** لـ`tenders`/`auctions`/`service_marketplace` (أو مرادفاتها) — `SaaSControlService.can_access_service(code)` بترجع `False` دايمًا لأي تينانت مهما كانت خطته، لأن `get_service_by_code` نفسها بترجع `None`. يمنع تفعيل الدومينين بالكامل حاليًا (`POST /purchase`, `POST /tenders`, `POST /bids`, `POST /auctions`, `POST /auctions/{id}/bids` كلها `403` لأي مستخدم). فئة "بيانات seed ناقصة" مش خطأ برمجي مشترك — لا علاقة له بأي دومين تاني حاليًا (باقي الدومينات تستخدم آلية SaaS مختلفة، `subscription.plan.features`). مؤكَّد حيًا (استعلام مباشر `saas_service_catalog` = صفر صفوف) — راجع نفس التقرير §3-أ |
| 29 | `finance-service-hold-funds-missing` [أُضيف 2026-08-25، بعد تجميد هذا الملف] | 🟢 محلي | 1 دومين (`tenders_auctions`) | `tenders_auctions/service.py:347,406` يستدعي `finance.hold_funds(...)`/`finance.release_held_funds(...)` (معلَّمتان `# type: ignore[attr-defined]` في الكود نفسه) لكن `FinanceService` (321 سطر) **لا تحتوي غير `transfer()`** — `grep` شامل صفر نتيجة لأي منهما. يعطّل `place_bid`/`close_auction` (فرع الفائز) بالكامل لأي مستخدم بـ`AttributeError`/500، بصرف النظر عن التينانت. شبيه شكليًا بـ#18 (`finance-service-create-invoice-does-not-exist` في `transport`) لكن دالة مختلفة تمامًا ومحصور بدومين مختلف — لم يُفحَص إن كان نفس الاسمين (`hold_funds`/`release_held_funds`) مستخدَمين في دومين تالت. مؤكَّد كوديًا (`grep` مباشر) — راجع نفس التقرير §3-ب |
| 30 | `tenders-auctions-router-no-read-endpoints` [أُضيف 2026-08-25، بعد تجميد هذا الملف] | ⚪ ليس فئة باج (فجوة تصميم/تنفيذ، مش constructor mismatch) | 1 دومين (`tenders_auctions`) | `repository.py` يحتوي دوال قراءة كاملة (`list_tenders`, `get_tender`, `list_auctions`, `get_auction`, `list_bids_for_tender`, `get_live_bids_for_auction`) لكن **صفر `router` handler واحد يستدعيها** — الدومين غير قابل للاستكشاف عبر الـAPI أصلًا (يحتاج تخمين IDs تسلسلية لأي عملية). قرار منتجي/فجوة تنفيذ ناقصة، مش باج تقني عابر للدومينات. راجع نفس التقرير §2 |
| 31 | `frontend-service-url-prefix-mismatch` [أُضيف 2026-08-25، بعد تجميد هذا الملف] | 🔴 **مركزي — بند منتشر مستقل، نفس فئة #23 (`bleach-clean-none-crash`)** | **21 من 30 دومين فرونت إند قابل للتطبيق (تأكيد `grep`+تحقق حي مباشر)** | نمط عابر لغالبية دومينات الفرونت إند بالكامل — راجع القسم المخصَّص "🔴 بند منتشر مستقل — #31" مباشرة بعد هذا الجدول. صفر إصلاح الآن، توثيق موسَّع فقط |
| 32 | `arbitration-syndicates-nominate-candidate-wrong-kwarg` [أُضيف 2026-08-25، بعد تجميد هذا الملف] | 🟡 غير مؤكَّد الانتشار (نفس فئة `duplicate-kwarg-audit`/#2، محلي لحد ما يُفحص) | 1 مؤكَّد (`arbitration_syndicates`) | `service.py:479-486` (`nominate_candidate`) يستدعي `self.repo.create_candidate(..., candidate_user_id=user_id, ...)` لكن عمود الموديل `ElectionCandidate` الفعلي اسمه `user_id`، مش `candidate_user_id` — `TypeError` فوري (`ElectionCandidate(**kwargs)` بيرفض kwarg غير موجود كعمود)، **قبل أي `db.add()`/`commit()`** — يمنع `POST /elections/{id}/candidates` بالكامل لأي مستخدم، بصرف النظر عن التينانت. مؤكَّد حيًا (هجوم IDOR بعد إصلاح `arbitration_syndicates` وصل لنفس العطل — صفر كتابة، `SELECT` مستقل = 0) — راجع `.claude/reports/batch2-audit-security-service-marketplace-tenders-auctions-arbitration-syndicates.md` §13.3. لم يُفحَص انتشار نفس نمط `candidate_user_id`/تسمية kwarg مشابهة في دومين تاني |

**ملاحظة [2026-08-25، استكمال جلسة `batch2-audit-security-...`]:** البند #32 أُضيف بعد تنفيذ إصلاح `arbitration_syndicates` نفسه (اكتشاف جانبي أثناء التحقق الحي، مش جزء من الجرد الأصلي) — بتوجيه صريح من المستخدم.

**ملاحظة [2026-08-24]:** البندان #19 و#20 أُضيفا بعد تجميد هذا الملف (2026-08-17) بتوجيه صريح من المستخدم في جلستي `projects-idor-fix`/`academy-idor-fix`، خلافًا لملاحظة السطر 5 (الملف تصنيف فقط، لا يُضاف له بند جديد عادةً) — المصدر الكامل والتفاصيل في التقارير المذكورة مباشرة، هنا فقط للتصنيف السريع.

**ملاحظة [2026-08-25]:** البنود #21 إلى #26 أُضيفت بنفس الاستثناء، بتوجيه صريح من المستخدم في جلسة `batch1-audit-security-employment-invitations-communications-invoicing`. صفر تنفيذ إصلاح لأي منها بعد — تصنيف/توثيق فقط. **🔴 أولوية خاصة: #24 (`create_invitation` معطوبة بالكامل) أعلى أولوية من أغلب بنود المجموعة أ التالية** — مش خلل حافة، دي الوظيفة الأساسية لدومين كامل غير قابلة للاستخدام إطلاقًا حاليًا (صفر دعوة واحدة ممكن تُنشأ فعليًا عبر الـAPI، بغض النظر عن أي إصلاح IDOR).

**ملاحظة [2026-08-25، جلسة `batch2-audit-security-...`]:** البنود #27 إلى #31 أُضيفت بنفس الاستثناء، بتوجيه صريح من المستخدم بعد جلسة `batch2-audit-security-service-marketplace-tenders-auctions-arbitration-syndicates`. صفر تنفيذ إصلاح لأي منها بعد — تصنيف/توثيق فقط (باستثناء البند الأمني المنفصل `service_marketplace.webhook` سر ثابت، اللي اتصلح فورًا في نفس الجلسة ولا يُضاف هنا لأنه مش نمط باج متكرر، بل تصلب أمني منفَّذ مباشرة).

---

## 🔴 بند منتشر مستقل — #23 `bleach-clean-none-crash` (13 دومين، توثيق موسَّع، **بلا إصلاح الآن**)

**مفصول عمدًا عن #24-#26** (بتوجيه صريح من المستخدم) — دول محليون لـ`invitations` وحدها، بينما #23 نمط تقني عابر لـ13 دومين مستقلة، **نفس فئة `duplicate-kwarg-audit` (#2)** من حيث الشكل: سبب جذري واحد (`.get(key, default)` بترجّع الـ`default` لو الـ`key` غايب بس، **مش لو قيمته `None` صراحة**) منسوخ حرفيًا في كل موضع، بلا دالة/كلاس مشترك واحد يمكن إصلاحه مركزيًا (كل نداء `bleach.clean` مباشر في كود الدومين نفسه).

**السبب الجذري بالتفصيل:** أي حقل `Optional[str]` في Pydantic schema بيتحط `None` صراحة في `data.model_dump()` لو العميل ما بعتوش (الـkey **موجود** بالـdict بقيمة `None`، مش غايب) — فـ`data.get(field, "")` **بيرجّع `None`، مش `""`** (لأن `.get()` بيرجّع الـdefault بس لو الـkey غايب تمامًا). `bleach.clean(None, tags=[], strip=True)` بيرمي `TypeError: argument cannot be of 'NoneType' type` فورًا.

**منهجية التأكيد:** `grep -rn "bleach.clean(data.get(" app/domains/*/service.py | grep -v "if data.get"` (يستبعد المواضع المحمية فعليًا بحارس `if data.get(field) else None` على نفس السطر — هذه المواضع **آمنة**، مش جزء من العدّ). **تصحيح:** العدّ الأول (89) كان خطأ حسابي من grep متعدد الملفات بلا تجميع صحيح — **العدد الصحيح المُعاد حسابه واستقلاليًا لكل ملف: 52 موضع غير محمي عبر 13 دومين.**

| الدومين | عدد المواضع غير المحمية | مؤكَّد حيًا؟ |
|---|---|---|
| `invitations` | 8 | ✅ (`create_invitation`, `create_campaign` — كراش فعلي حي، جلسة `batch1-audit-security-...`) |
| `zamakana` | 8 | ⚪ grep فقط |
| `manufacturing` | 6 | ⚪ grep فقط |
| `tourism_sports` | 5 | ⚪ grep فقط |
| `command` | 4 | ⚪ grep فقط |
| `logistics` | 4 | ⚪ grep فقط |
| `tenders_auctions` | 4 | ⚪ grep فقط |
| `transport` | 4 | ⚪ grep فقط |
| `social` | 3 | ⚪ grep فقط |
| `ai_agents` | 2 | ⚪ grep فقط |
| `employment` | 2 | ⚪ grep فقط |
| `agritech` | 1 | ⚪ grep فقط |
| `realestate` | 1 | ⚪ grep فقط |
| **الإجمالي** | **52** | 1 دومين مؤكَّد حيًا (`invitations`)، 12 مطابقة بالـgrep بس |

**دومينات فُحصت واستُبعدت** (بتستخدم `bleach.clean` بنمط مختلف، غير عرضة لنفس الباج): `insurance` (وصول مباشر `data["key"]`، عطل مختلف — `KeyError` مش `TypeError`)، `arbitration_syndicates` (نفس الشيء)، `projects` (نداء مباشر بلا `.get()`).

**الإصلاح المقترَح (لم يُنفَّذ):** `bleach.clean(data.get(field) or "", ...)` بدل `.get(field, "")` في كل موضع — تعديل ميكانيكي بسيط لكل الـ52 موضع، أو wrapper مركزي `safe_clean(value)` يُستبدَل بيه كل نداء. **أولوية وظيفية عالية** (يمنع إنشاء موارد أساسية، مش قراءة/تعديل هامشي) — لكن يحتاج **جلسة `grep`/تحقق حي منفصلة لباقي الـ12 دومين** قبل أي إصلاح مركزي فعلي (نفس منهجية #2/#7/#8 وقت اكتشافها لأول مرة).

---

## 🔴 بند منتشر مستقل — #31 `frontend-service-url-prefix-mismatch` (21 من 30 دومين فرونت إند، توثيق موسَّع، **بلا إصلاح الآن**)

**اكتُشف أثناء تحقيق §7#15 من `batch2-audit-security-...` (كان محصورًا فيه بحث لـ`service_marketplace`/`tenders_auctions` فقط) — بتوجيه المستخدم اتوسّع لـ`grep` شامل عبر كل الـ32 ملف `services/*.ts`.** نفس فئة `bleach-clean-none-crash` (#23) من حيث الشكل: سبب جذري واحد **متكرر بنفس الآلية** (توليد المسار من دمج تسمية `main.py`/`routers_config` غير الموثوقة مع تسمية الراوتر الداخلي)، لكن بلا دالة/كلاس مشترك واحد — كل ملف `services/*.ts` مكتوب مستقلًا (على الأرجح مولَّد آليًا بنفس الأداة/القالب الخاطئ).

**السبب الجذري بالتفصيل:** `apiClient` (axios) بـ`baseURL = NEXT_PUBLIC_API_URL` (افتراضيًا `http://localhost:8000/api`، مؤكَّد من `.env.local`). المسار الحقيقي المسجَّل فعليًا لكل دومين = `/api` + `prefix` الداخلي لكائن `APIRouter` في `router.py` نفسه فقط (`main.py:300-308`: `include_router(router_obj, prefix="/api", tags=tags_list)` — **صفر استخدام** لحقل `prefix_path` الثاني في تركيبة `routers_config` رغم وجوده، وهو حقل ميت غير مُستخدَم في التسجيل الفعلي إطلاقًا). لكن أغلب ملفات `services/*.ts` تبدو مولَّدة بافتراض إن هذا الحقل الميت **هو المسار الفعلي**، فبتبني الرابط كـ`{prefix_path}{router.prefix}/...` — لما `prefix_path` يساوي `router.prefix` حرفيًا (الحالة الأشيع، 19 دومين)، الناتج بادئة مضاعَفة (`/employment/employment/jobs`)؛ ولما يختلفا (`arbitration_syndicates`: `/arbitration` مقابل `/arbitration-syndicates`)، الناتج مسار غير موجود إطلاقًا؛ و`tenders_auctions` حالة خاصة أسوأ — يبدو نسخ-لصق غير مكتمل من `social.ts` (يستخدم فعليًا segment `"social"` بدل `"tenders-auctions"`).

**منهجية التأكيد:** قراءة أول 3 روابط `apiClient.(get|post|put|delete|patch)` في كل ملف من الـ32 (`grep -oE` على الأنماط الحرفية + فحص القوالب النسبية بلا `/` بادئة)، مقارَنة بـ`APIRouter(prefix=...)` الفعلي في `router.py` المطابق (`grep` مباشر عبر `app/domains/*/router.py`) + `main.py:266-297` (تركيبة `routers_config`). **تحقق حي مباشر واحد إضافي** (خارج ما فعلناه للـ`service_marketplace` في `batch2-audit-security-...` §8) لتأكيد إن الفرضية تنطبق فعليًا لا نظريًا فقط: `GET /api/marketplace/services` (المسار الحقيقي) → `200`، بينما `GET /api/marketplace/marketplace/services` (المسار اللي يستخدمه `services/marketplace.ts` فعليًا بعد `baseURL`) → `404` — **مباشرة من سيرفر uvicorn حقيقي، بلا أي طبقة nginx/proxy/rewrite موجودة في المشروع** (تأكيد: `docker-compose.yml` بلا أي خدمة nginx/proxy، `eppne-web` بلا `next.config.js` rewrites، بلا `app/api/*` وسيط).

| النمط | عدد الدومينات | الدومينات |
|---|---|---|
| **بادئة مضاعَفة** (`{domain}/{domain}/...` — `prefix_path == router.prefix` حرفيًا) | **19** | `affiliate`, `command`, `commerce`, `communications`❌(راجع تصحيح تحت)، `employment`, `health`, `insurance`, `invitations`, `iot`, `logistics`, `manufacturing`, `service_marketplace`(`marketplace.ts`)، `privacy`, `realestate`, `saas`, `social`, `tourism_sports`, `translation`, `transport`, `zamakana` |
| **مسار مغلوط تمامًا** (`prefix_path != router.prefix`، أو نسخ-لصق من دومين آخر) | **2** | `arbitration_syndicates` (`/arbitration/arbitration-syndicates/...` — دمج الاثنين معًا، مسار غير موجود إطلاقًا)، `tenders_auctions` (`/tenders/social/...` — segment "social" منسوخ من دومين تاني بالخطأ) |
| **صحيح (بادئة واحدة، مطابقة للمسار الحقيقي فعليًا)** | **9** | `academy`, `ai_agents`(`ai-agents.service.ts`، يستخدم `/ai` الحقيقي مش `/ai-agents` من `routers_config`)، `identity`(`auth.service.ts`)، `automation`, `digital_twin`, `finance`, `projects`(مسارات نسبية بلا `/` بادئة، تُحل صح عبر `combineURLs` في axios)، `sovereign_entities`(`sovereign-entities.ts`، يستخدم `/sovereign-entities` الحقيقي مش `/sovereign` من `routers_config`) |
| **خارج النطاق** (بلا ملف `services/*.ts` مخصَّص، أو الدومين محذوف من الباك إند) | 3 | `ai_governance`, `invoicing`, `admin` (بلا ملف)، `agritech` (ملف موجود بنفس عيب البادئة المضاعَفة، لكن الراوتر الخلفي **محذوف بالكامل** من `main.py` — العطل هنا أعمق من مجرد مسار خاطئ، غير معدود ضمن الـ21) |

**تصحيح مهم أثناء إعادة التحقق لكتابة هذا الجدول:** `communications.service.ts` أول عيّنة أظهرت مسارات صحيحة (`/communications/devices/register`) — **هذا لا يعني الملف بالكامل سليم بالضرورة**؛ العدّ هنا اعتمد على عيّنة 3 روابط أولى لكل ملف (نفس منهجية `bleach-clean-none-crash` وقت اكتشافه لأول مرة) — **لم يُفحَص كل رابط في كل ملف بالكامل**، فالعدد (21/30) قابل للتعديل الطفيف لو جلسة `grep` مخصَّصة لاحقة فحصت كل سطر بدل عيّنة.

**الإصلاح المقترَح (لم يُنفَّذ):** تصحيح المسار الحرفي (أو القالب المولِّد له لو موجود) في كل ملف من الـ21 ليطابق `APIRouter(prefix=...)` الفعلي مرة واحدة فقط (حذف التكرار، أو تصحيح الاسم بالكامل لحالتي `arbitration_syndicates`/`tenders_auctions`) — تعديل ميكانيكي بسيط في **بيانات نصية فقط** (لا منطق)، لكن **لا يمكن دمجه مع #1 من `constructor-mismatch` نفسه** (فئة مختلفة تمامًا — لا علاقة بتوقيع دالة/kwarg). **يستحق جلسة `grep`+تصحيح مركزية مستقلة كاملة** تراجع كل سطر (مش عيّنة) في الـ32 ملف، **قبل أي جلسة إصلاح فرونت إند تانية** (لأن أي إصلاح TS2305 لأسماء استيراد — زي `service_marketplace`/`tenders_auctions`/`arbitration_syndicates` بالدفعة 2 — عديم الفائدة عمليًا لحد ما هذا البند يتصلح جنبه، الاثنان لازم يتصلحوا معًا في نفس الدومين عشان أي شاشة تشتغل فعليًا).

---

## 🔴 المجموعة أ — تحتاج جلسة تصحيح مركزي واحدة (13 بند: #1, #2, #7, #8, #9, #10, #11, #12, #14, #15, #16, #23, #31)

هذه البنود **كلها من نفس الشكل البنيوي**: كلاس/دالة مشتركة واحدة (`UserRepository`, `RedisClientWrapper`, `SaaSControlService`, `AffiliateService`, `InvoicingService`, `audit_log()`, `AIGovernanceService`, `AIAgentsService`) تغيَّر توقيعها أو ناقصة method — ونفس الخطأ **منسوخ حرفيًا** في كل دومين استخدمها. إصلاح دومين واحد بمفرده **لا يحل** الباقي؛ الإصلاح الصحيح هو تعديل الكلاس/الدالة نفسها (أو `grep` شامل + تعديل كل الاستدعاءات دفعة واحدة) في **جلسة واحدة مخصَّصة لكل بند**.

### ترتيب الأولوية المقترَح داخل هذه المجموعة

0. **#24 (`invitations-create-invitation-fully-broken`, محلي لـ`invitations`)** — 🔴🔴 **أولوية تسبق حتى #11/#9 من ناحية الأثر الوظيفي (لا تسبقهما من ناحية الخطورة الأمنية/المالية)**: وظيفة "إنشاء دعوة" — جوهر دومين `invitations` — **معطوبة 100%، صفر استخدام ناجح ممكن حاليًا عبر الـAPI**، بغض النظر عن أي إصلاح IDOR. عطلها الأول (`bleach.clean` على `None`) مظهر محلي من #23 (راجع القسم المخصَّص أعلاه) — الفرق إن #11/#9 خطورتهما **أمنية/مالية**، و#24 خطورته **وظيفية بحتة** (منع كامل لميزة، صفر تسريب/فقدان بيانات).
0.5. **#23 (`bleach-clean-none-crash`، بند منتشر مستقل — راجع القسم المخصَّص أعلاه، مفصول عمدًا عن #24)** — نفس مرتبة #12/#15/#16 تقريبًا من ناحية الجاهزية (نمط مؤكَّد جزئيًا بالتنفيذ الحي، يحتاج تحقق حي لباقي الـ12 دومين قبل جلسة الإصلاح المركزي الفعلية) — **لا يُصلَح كجزء تلقائي من إصلاح #24** (نفس المنطق: إصلاح موضع `invitations` بمفرده لا يحل باقي الـ12 دومين).
1. **#11 (`realestate-invoicing-savepoint-conflict` + امتداد `invitations`)** — 🔴🔴 **أعلى أولوية مطلقة في كل الـBacklog**. بيانات هوية حقيقية يتيمة على القرص (`users id=52`, `p_ctor_inv_newuser@eppne.com`). جلسة `invitations-user-registration-savepoint-leak` **مقررة بالفعل كالجلسة التالية مباشرة** بعد الانتهاء من مراجعة دفعة `constructor-mismatch` الحالية — راجع `.claude/reports/CRITICAL-invitations-accept-orphaned-user-no-wallet.md`.
2. **#9 (`saas-control-service-missing-methods`)** — 🔴🔴 **محظور إصلاحه بمعزل عن #11**: `get_active_subscription` المفقودة هي نفسها اللي بتحجب (بالصدفة، مش بتصميم آمن) ثغرة `invitations` حاليًا. أي إصلاح لـ#9 **قبل** إغلاق #11 هيفتح الثغرة فورًا في كل دومين بيستخدم نمط `get_active_subscription` (`digital_twin`, `employment`، وربما أكتر).
3. **#14 (`audit-log-wrong-kwargs`)** — الأوسع انتشارًا رقميًا في كل الـBacklog (عشرات المواضع + داخل `InvoicingService` نفسها) — بمجرد إغلاق #11/#9، هذا البند يستاهل الأولوية التالية لأنه بيمنع **كل** عملية `create_invoice`/`audit_log` ناجحة ظاهريًا من الاكتمال فعليًا عبر المشروع كله تقريبًا.
4. **#1 (`user-repository-get-by-id-audit`)** — فشل مالي صامت مؤكَّد حيًا (عمولات affiliate بتضيع بلا أي إشارة خطأ) — أولوية عالية لأنه صامت.
5. **#10 (`affiliate-service-missing-methods`)** — مرتبط مباشرة بـ#1 (نفس الدالة المساعدة `_register_affiliate_commission` في كل دومين تقريبًا) — يستحسن إصلاحهما في نفس الجلسة أو جلستين متتاليتين.
6. **#12، #15، #16** — نفس العائلة (استدعاءات بمعامل `tenant_id` زيادة بعد نقله للـconstructor) — **🔴 تصحيح [2026-08-17]، بعد تدقيق تقني كامل لكل موضع فعلي: التجميع في جلسة واحدة موحّدة كان افتراضًا غير دقيق.** #12 فعلاً متطابق 100% (6/6 مواضع بسيطة). لكن #15 (7 من 13 موضع = 54%) و#16 (13 من 18 موضع = 72%) فيهم نسبة كبيرة من الحالات "المركّبة" (زي `arbitration_syndicates`) — مش استثناء نادر زي ما كان موثَّق، دي الأغلبية فعليًا. التفاصيل الكاملة + جدول مقارَنة موضع بموضع في `.claude/reports/constructor-mismatch-backlog-12-15-16-homogeneity-audit.md`. **القرار المُحدَّث: #12 جلسة ميكانيكية مستقلة، #15+#16 يُقسَّموا لـ3 جلسات فرعية (ميكانيكي / مركّب-سهل / مركّب-صعب) بدل جلسة واحدة.**
7. **#8، #7، #2** — أولوية أقل نسبيًا (أعداد مواضع أصغر، بعضها محمي بـ`try/except` فبيفشل بهدوء) — تُجدوَل بعد ما سبق.

---

## 🟢 المجموعة ب — محلية لدومين واحد (13 بند: #5, #6, #17, #18, #19, #20, #21, #22, #25, #26, #27, #28, #29 — + #24 مُدرَج تصنيفيًا هنا لكن بأولوية استثنائية أعلى، راجع بند 0 بالمجموعة أ)

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
- **#27 (`arbitration-syndicates-repository-missing-methods`)** [أُضيف 2026-08-25، جلسة `batch2-audit-security-...`] — 5 دوال `repository.py` مفقودة + دالتان بتوقيع أضيق، محصور في `arbitration_syndicates` وحده — صفر سبب جذري مشترك مع أي دومين تاني.
- **#28 (`saas-service-catalog-missing-entries`)** [أُضيف 2026-08-25، جلسة `batch2-audit-security-...`] — بيانات seed ناقصة في `saas_service_catalog` لـ`tenders`/`auctions`/`service_marketplace`، محصور بدومينين اثنين فقط، وهي فجوة بيانات إعداد مش خطأ برمجي مشترك.
- **#29 (`finance-service-hold-funds-missing`)** [أُضيف 2026-08-25، جلسة `batch2-audit-security-...`] — `FinanceService.hold_funds`/`release_held_funds` غير موجودتين، محصور في `tenders_auctions` وحده حاليًا (لم يُفحَص انتشاره).

---

## 🟡 المجموعة ج — غير مؤكَّدة الانتشار، تحتاج جرد قبل التصنيف النهائي (بندان: #13, #32)

- **#13 (`invoicing-create-invoice-wrong-kwarg`)** — الجزء الخاص باسم الـkwarg (`tenant_id=` بدل `entity_id=`) مؤكَّد في `service_marketplace` بس لحد الآن، لكن التقرير نفسه ينص صراحة على إن `grep` شامل لباقي الـ12 دومين المستخدمة لـ`InvoicingService.create_invoice` **لم يُنفَّذ بعد**. **ملاحظة مهمة:** امتداده الأخطر (كراش `audit_log` **داخل** `create_invoice()` نفسها، بغض النظر عن صحة اسم الـkwarg الخارجي) **مؤكَّد بالفعل كمركزي 100%** ومُدمَج فعليًا تحت البند #14 — لذلك القرار العملي هو: **عالج #13 كجزء من جلسة #14 مباشرة**، ولا داعي لجلسة `grep` منفصلة قائمة بذاتها.
- **#32 (`arbitration-syndicates-nominate-candidate-wrong-kwarg`)** [أُضيف 2026-08-25] — `candidate_user_id` بدل `user_id` في نداء `ElectionCandidate(**kwargs)`، مؤكَّد في `arbitration_syndicates` وحده لحد الآن — لم يُفحَص انتشار نفس نمط تسمية الـkwarg في دومين تاني.

---

## ⚪ بنود إدارية / ليست أنماط باج (3 بنود: #3, #4, #30)

- **#3 (Phase 16 الأصلي)** — استكمال جلسة سابقة (`phase16-session-log.md`)، مش نمط باج مكتشف حديثًا.
- **#4 (`silent-write-regression` المتبقي)** — موضعان أخيران (`saas.process_auto_renewals` فرع `except`, `saas.can_access_service`) من جلسة `silent-write-regression-session-log.md` القائمة أصلًا وشبه مكتملة (89 موضع اتغطوا already) — إغلاق أخير، مش جلسة مركزية جديدة.
- **#30 (`tenders-auctions-router-no-read-endpoints`)** [أُضيف 2026-08-25، جلسة `batch2-audit-security-...`] — فجوة تصميم/تنفيذ ناقص (صفر `router` handler للقراءة رغم وجود الدوال في `repository.py`)، مش نمط constructor mismatch.

---

## الخلاصة العملية

| السؤال | الإجابة |
|---|---|
| كام بند يحتاج جلسة مركزية واحدة فعلية؟ | **13 بند** (#1, #2, #7, #8, #9, #10, #11, #12, #14, #15, #16, #23, #31 — بعضها ممكن يتجمّع في نفس الجلسة زي #12+#15+#16) |
| كام بند محلي فعلاً، صفر حاجة لجلسة عابرة؟ | **14 بند** (#5, #6, #17, #18, #19, #20, #21, #22, #24, #25, #26, #27, #28, #29 — #24 محلي تصنيفيًا لكن بأولوية استثنائية أعلى، راجع بند 0 بالمجموعة أ) |
| كام بند يحتاج جرد سريع الأول قبل تحديد نوعه؟ | **بندان** (#13 — لكن عمليًا يُعالَج ضمن جلسة #14؛ #32 محلي لحد ما يُفحص انتشاره) |
| كام بند إداري بس؟ | **3 بنود** (#3, #4, #30) |
| إيه أعلى أولوية مطلقة دلوقتي (أمنية/مالية)؟ | **#11 ثم #9** (بالترتيب ده تحديدًا — عكس الترتيب ممنوع لأنه بيفتح ثغرة هوية حقيقية) |
| إيه أعلى أولوية وظيفية (منع كامل لميزة، بمعزل عن الأمان)؟ | **#24 ثم #23** — `invitations.create_invitation` معطوبة 100% حاليًا، صفر دعوة واحدة ممكن تُنشأ عبر الـAPI |
