# تحديث تصنيف Backlog — جلسة تنظيف ديون تقنية صغيرة [2026-08-25]

**الغرض:** جلسة قراءة فقط (صفر كود) طلبها المستخدم لمراجعة
`constructor-mismatch-backlog-classification.md` (المُجمَّد بتاريخ
2026-08-17، 20 بند) + `PROGRESS_LOG.md` بالكامل (بما فيه قسم "الجلسات
المُقفلة" اللي فيه بنود Backlog جانبية اتكتشفت **بعد** تجميد ملف
التصنيف ولسه مش مُدمَجة في جدوله)، وبناء ترتيب تنفيذي مقترَح للأسهل
أولًا. **هذا الملف تحديث/توسيع لملف التصنيف الأصلي، مش بديل له** —
الأصل يفضل كما هو (مرجع تاريخي).

**المنهجية:** كل بند من الـ20 في ملف التصنيف الأصلي اتقورن بحالته
**الحالية الفعلية** في `PROGRESS_LOG.md` (مش تصنيف 2026-08-17 وحده، لأن
كتير اتقفلوا من وقتها)، وبعض الحالات اتأكدت إضافيًا بقراءة الكود مباشرة
أو بمراجعة `PROGRESS_LOG_ARCHIVE_2026-08-18.md` للتفاصيل اللي مش موجودة
في النسخة الحالية المختصرة.

---

## ⚠️ اكتشاف مهم: entry فهرسي stale في PROGRESS_LOG.md

بند #6 (`commerce.visa_webhook`) **اتقفل فعليًا** بـcommit
`b55b57c` (2026-08-25 09:55:48، "fix(commerce): close visa_webhook
open auth gap — last deferred commerce IDOR item") — لكن
`PROGRESS_LOG.md` سطر 149 لسه بيقول "🔴 مفتوح، لم يبدأ". هذا تحديث
فهرسي بسيط منفصل تمامًا عن نطاق هذه الجلسة، مذكور هنا كملاحظة فقط.

---

## المجموعة أ — سطر واحد / إسقاط kwarg زايد (الأسهل، صفر migration)

| المصدر | الدومين/الدالة | الباج | الحالة | المرجع |
|---|---|---|---|---|
| #12 | `saas`×6 (`service_marketplace`, `social`, `tenders_auctions`, `tourism_sports`, `transport`, `zamakana`) — `can_access_service` | `tenant_id=` زايدة بعد نقلها للـconstructor | 🔴 مفتوح — **مؤكَّد 100% ميكانيكي متطابق** في `constructor-mismatch-backlog-12-15-16-homogeneity-audit.md` | PROGRESS_LOG.md سطر 159، 60 |
| PL#23 | `invoicing.list_invoices` (كل الـcallers) | `router.py:150` بيمرر `tenant_id=` على استدعاء بلا هذا الباراميتر إطلاقًا | 🔴 مفتوح، موضع واحد فقط | أرشيف ~3168 |
| PL#24 | `invoicing.get_invoice_stats` (كل الـcallers) | `router.py:307` بيمرر معامل موضعي زايد (الدالة `-> Dict` بلا معاملات إطلاقًا) | 🔴 مفتوح، موضع واحد فقط | أرشيف ~3169 |
| امتداد #2 | `commerce.create_payment_request` (`service.py:325-364`) | **تأكَّد بقراءة الكود مباشرة الآن:** `pr_data` dict فيها `"tenant_id": self.tenant_id`، وبعدين `self.repo.create_payment_request(self.tenant_id, **pr_data)` بتمررها تاني → `TypeError: multiple values for keyword argument 'tenant_id'` | 🔴 مفتوح — نفس نمط `academy.create_course`/`create_org_entity` المُصلَح فعلًا في جلسة `academy-priority-fix` | `constructor-mismatch-backlog-classification.md` بند #2 (الحالة الأصلية) |
| امتداد #2 [2026-08-20] | `sovereign_entities.create_entity` | نفس الازدواج بالحرف (`tenant_id` داخل `entity_data` dict + كباراميتر صريح `tenant_id=self.tenant_id` في `repo.create_entity(...)`) | 🔴 مفتوح — **يمنع `POST /sovereign-entities/` بالكامل**، أولوية أعلى من باقي هذه المجموعة | PROGRESS_LOG.md سطر 195 |
| — [2026-08-24] | `ai_governance/router.py` (`check-and-consume` endpoint) | الراوتر بيعامل ناتج `check_and_consume()` (`-> bool`) كأنه `dict` (`result["allowed"]`) → `TypeError` مُلتقَط بـ`try/except` عام فيترجم لرد **مضلِّل**، حتى لو الاستهلاك الحقيقي نجح وسُجِّل فعليًا | 🟠 مفتوح — بيخفي نتيجة كتابة حقيقية وراء رد كاذب | PROGRESS_LOG.md سطر 264 |

## المجموعة ب — إضافة عمود/migration بسيطة (schema↔model)

| المصدر | الدومين | الباج | ملاحظة |
|---|---|---|---|
| #17 | `arbitration_syndicates.create_dispute` | `repo.create_case(idempotency_key=..., ...)` بينادي `ArbitrationCase(**kwargs)` مباشرة، لكن الموديل **بلا عمود `idempotency_key`** (بعكس 4 موديلات تانية بنفس الملف عندها العمود فعليًا) | قرار صغير: إضافة العمود (migration قصيرة، نفس نمط الموديلات التانية) **أو** إسقاط تمرير الـkwarg لو مش لازم فعليًا |
| — [2026-08-25] | `ai_governance.create_or_update_quota` | `agent_quotas.reset_at` عمود `NOT NULL` بلا `server_default`، و`AgentQuotaCreate` schema/الكود ما بيوفروش قيمة افتراضية → `IntegrityError` لأي إنشاء حصة عبر الـAPI الرسمي | إضافة default في الكود (أبسط، صفر migration) أو `server_default` عبر migration — راجع PROGRESS_LOG.md سطر 268 |
| #20 | `academy.create_bootcamp` | `AcademyRepository.create_bootcamp()` بتمرر `instructor_id` لـ`Bootcamp(**kwargs)`، لكن جدول `academy_bootcamps` **بلا عمود `instructor_id` إطلاقًا** (تأكيد `\d` حي) | نفس نمط #19 لكن أبسط (جدول واحد، عمود واحد) — قرار: إضافة العمود أو استبعاد الـkwarg من `create_bootcamp` |

## المجموعة ج — تنظيف بيانات فقط (صفر كود)

| البند | الوصف | الأولوية |
|---|---|---|
| `saas-test-reqsector-leaked-throwaway-data-breaks-get-my-subscriptions` [2026-08-24] | صفان throwaway متسربان من جلسة `require-sector-removal-subscription-fix` القديمة (`saas_tenant_subscriptions.id=50`, `saas_service_plans.id=48`) بحقول `NULL` غير قابلة للقراءة عبر `TenantSubscriptionResponse` — بيكسروا `GET /saas/subscriptions` بـ`500` **فعليًا اليوم** لأي مستخدم حقيقي في تينانت1 | **عالية** — تأثير إنتاجي حي، حل بـ`UPDATE`/`DELETE`/تعبئة القيم فقط، صفر تعديل كود — راجع PROGRESS_LOG.md سطر 255 |
| `stale-test-user-system-eppne-com` [2026-08-25] | مستخدم throwaway خامل (`system@eppne.com`, `id=43`) — الكود الحالي (بعد Phase 3) لا يشير له إطلاقًا، بلا أي تأثير وظيفي، بس ممكن يلخبط جلسة تشخيص مستقبلية | منخفضة جدًا — حذف اختياري — راجع PROGRESS_LOG.md سطر 201 |

## المجموعة د — محلية لكن محتاجة تفكير فعلي (مش مجرد rename)

| المصدر | الدومين | ليه أعقد |
|---|---|---|
| #18 | `transport.book_trip`/`pay_delivery` (`service.py` سطر 355، 529) | `FinanceService.create_invoice` **مش موجودة إطلاقًا** على الكلاس — القرار مش rename بسيط، لازم يتحدد: تبني method جديدة على `FinanceService`، ولا توصل `transport` بـ`InvoicingService` زي باقي الدومينات (`transport` أصلًا معندهوش `InvoicingService` مُنشأة في `__init__`)؟ |
| — [2026-08-24] | `ai_governance` (`get_agent_quotas`, `get_agent_remaining_quotas`, `get_rate_limit`) | `service._check_agent_ownership()` **غير معرَّفة إطلاقًا** — لازم تصميم منطق "ملكية" فعلي (مش مجرد نسخ استدعاء موجود بمكان تاني)، `500` مضمون حاليًا للثلاثة endpoints — راجع PROGRESS_LOG.md سطر 266 |
| #19 | `projects` (3 موديلات: `Project`, `Contribution`, `ProjectUpdate`) | نطاق أكبر (20+ حقل schema مقابل أقل من نصفهم موجود كأعمدة) — قرار: تقليم الـschema ولا توسيع الموديلات الثلاثة؟ يمنع `POST /projects/` بالكامل + 5 من 6 أنواع مساهمة + `add_project_update` بالكامل |

## المجموعة هـ — مُستبعَدة من هذه الجلسة (قرارات منتجية/معمارية حقيقية)

- **#3** (استكمال Phase 16) — علاقته بكوميتات قديمة (`2d4ef59`/`ab73c8c`) غير مؤكَّدة 100%، محتاج تحقيق مش إصلاح مباشر.
- **#5 / `sovereign_entities-unauthenticated-endpoints`** — قرار منتجي معلَّق صراحة (هل الـ4 endpoints المفروض تفضل بلا مصادقة).
- **`identity-user-referred-by-field-missing`** — يحجب Backlog #10 بالكامل (كل الـ12 دومين)، لكنه قرار تصميم نظام إحالة عام (عمود مسطَّح؟ `ReferralTree` بنطاق `GLOBAL`؟)، ليس إصلاح كود مباشر.
- **#4 المتبقي** (`process_auto_renewals` فرع `except`, `can_access_service`) — لسه غير مؤكَّد DB-level (بعكس `cancel_subscription` اللي اتصلح فعليًا)، يحتاج تحقق قبل تصنيفه كإصلاح بسيط.
- **#13** (الجزء غير المؤكَّد الانتشار — اسم kwarg `tenant_id=` مقابل `entity_id=` عبر باقي الـ12 دومين المستخدمة لـ`InvoicingService`) — يحتاج `grep` شامل أولًا (مش إصلاح مباشر)، القرار العملي الموثَّق هو معالجته ضمن جلسة #14 (المُقفلة فعلًا) — يحتاج تأكيد هل الجزء الخارجي (اسم الـkwarg نفسه) اتغطى فعلًا ولا لسه مفتوح.
- **#2 (باقي الانتشار غير المؤكَّد)** — الأربع حالات الأصلية اتغطت (2 مُصلَحة، 2 موثقة فوق)، لكن الملف الأصلي بيقول "يُشتبه في وجود أكتر" — يحتاج `grep` شامل لتأكيد الإغلاق الكامل.
- **`three-competing-affiliate-commission-systems`**, **`finance-transfer-hardcoded-system-account-real-fund-risk`**, **`saas-pay-invoice-sender-id-user-id-collision`** — قرارات معمارية/مالية كبيرة (منها launch blocker صريح)، برّه نطاق "ديون تقنية صغيرة".

## بنود مُقفلة فعلًا (لا تُلمَس — للتوثيق بس، لتفادي إعادة عمل)

#1, #7, #8, #9, #11a, #11b, #14, #15 (الأساسي)، #16 (17 من 19 موضع، موضعان مستثنيان عمدًا لبند منفصل)، و**#6** (حديثًا اليوم 2026-08-25، لكن الفهرس stale — راجع الملاحظة فوق).

بند #10 مُغلَق **جزئيًا** فقط (المنطق الجديد شغّال، لكن كل الـ12 دومين لسه محجوبين بـ`identity-user-referred-by-field-missing` أعلاه).

---

## الترتيب المقترَح للموافقة (من الأسهل)

1. **المجموعة أ** (6 بنود) — كلها rename/drop-kwarg بلا migration، أقل خطر ممكن. أولوية داخلية: `sovereign_entities.create_entity` أولًا (بيمنع endpoint كامل).
2. **المجموعة ج** (تنظيف بيانات) — `saas-test-reqsector` أولًا (بتكسر إنتاج فعليًا اليوم)، بعدين `stale-test-user` (اختياري تمامًا).
3. **المجموعة ب** (3 بنود migration بسيطة) — كل واحد قرار عمود/default صغير قبل التنفيذ (تُعرض كخيارات، مش تُنفَّذ افتراضيًا).
4. **المجموعة د** (3 بنود) — تحتاج قرار تصميم مصغّر قبل الكود، تُجدوَل آخر حاجة في نفس الجلسة أو تُفصَل لجلسة إضافية صغيرة.

**صفر تنفيذ حتى الآن — بانتظار موافقة المستخدم على النطاق/الترتيب.**
