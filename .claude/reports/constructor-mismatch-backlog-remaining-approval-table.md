# جدول الموافقة — البنود المتبقية فعليًا غير المُصلَحة (constructor-mismatch-backlog)

**تاريخ:** 2026-08-26
**الحالة:** جدول للموافقة فقط — **صفر تنفيذ فوري.**
**الاستبعاد المطلوب (كما وُصف):** #23-#26 + #2 (الموضعين الممتدين) + #12 + #17 + #18 (تحفظ) + #19 + #20 +
#25 + #27 (جزئي) + #46 + #47.

---

## ⚠️ ملاحظة سابقة على الجدول — فجوة إضافية اكتُشفت أثناء الجرد

قائمة الاستبعاد اللي طلبتها دقيقة لكل ما هو مُتعلِّق بجلستي `55032eb`/`f17636c`. لكن أثناء مطابقة
**كل** بنود `constructor-mismatch-backlog-classification.md` (1-47) ضد `PROGRESS_LOG.md` (جدول
الـBacklog الداخلي + قسم "الجلسات المُقفلة") و`constructor-mismatch-backlog-classification-update-2026-08-25.md`،
لقيت **13 بند إضافي مُصلَح ومؤكَّد فعليًا** (بعضها من 2026-08-18/19، بعضها من 2026-08-24/25) —
**لكنها مش في قائمة الاستبعاد اللي حددتها، ومعظمها مش معلَّم ✅ في الملف الموحَّد نفسه أصلًا** (نفس
فجوة التوثيق اللي بنسجلها في PROGRESS_LOG.md، بس أقدم/أوسع). **لم ألمسها اليوم (خارج تفويضك
المحدَّد لهذه الجلسة تحديدًا)** — بس تجاهلها بصمت في جدول "المتبقي" تحت كان هيدّي نتيجة غلط
(هيوهم إنها لسه مفتوحة). عرضتها هنا منفصلة للشفافية:

| # | الاسم | تاريخ الإغلاق | المصدر | معلَّم ✅ في الملف الموحَّد؟ |
|---|---|---|---|---|
| 1 | `user-repository-get-by-id-audit` | 2026-08-19 | PROGRESS_LOG.md سطر 144/230 | ❌ لا |
| 5 | `sovereign_entities` (4 endpoints بلا مصادقة) | 2026-08-24 (جلسة `sovereign-entities-idor-fix`) | PROGRESS_LOG.md سطر 246 | ❌ لا |
| 6 | `commerce.visa_webhook` | 2026-08-25 (commit `b55b57c`) | PROGRESS_LOG.md سطر 149 | ❌ لا |
| 7 | `redis-client-wrapper-missing-methods` | 2026-08-19 | PROGRESS_LOG.md سطر 150/226 | ❌ لا |
| 8 | `user-repository-get-user-audit` | 2026-08-19 | PROGRESS_LOG.md سطر 151/232 | ❌ لا |
| 9 | `saas-control-service-missing-methods` | 2026-08-18 | PROGRESS_LOG.md سطر 152 | ❌ لا |
| 11 | `realestate-invoicing-savepoint-conflict` (+ امتداد `invitations`) | 2026-08-18 (#11a + #11b) | PROGRESS_LOG.md سطور 157-158 | ❌ لا (لسه "🔴🔴 أعلى أولوية مطلقة") |
| 14 | `audit-log-wrong-kwargs` | 2026-08-18 | PROGRESS_LOG.md سطر 161 | ❌ لا |
| 15 | `ai-governance-check-and-consume-wrong-kwarg` (الأساسي) | 2026-08-18 | PROGRESS_LOG.md سطر 162 | ❌ لا |
| 34 | `manufacturing-facilities-entity-id-missing` | 2026-08-25 (نفس جلسة الاكتشاف) | الملف الموحَّد نفسه، صف #34 | ✅ **نعم، معلَّم فعلًا** |
| 35 | `manufacturing-repository-hardcoded-tenant-1-fallback` | 2026-08-25 (الموضعان المعروفان فقط) | الملف الموحَّد نفسه، صف #35 | ✅ **نعم، معلَّم فعلًا** (بتحفظ: باقي الانتشار غير مفحوص) |
| 36 | `manufacturing-schedule-maintenance-missing-commit` | 2026-08-25 | الملف الموحَّد نفسه، صف #36 | ✅ **نعم، معلَّم فعلًا** |
| 44 | `permission-check-passed-id-instead-of-user-object` | 2026-08-26 | الملف الموحَّد نفسه، صف #44 | ✅ **نعم، معلَّم فعلًا** |

**خلاصة:** #34/#35/#36/#44 بالفعل معلَّمة ✅ في الملف — دي كانت متسقة أصلًا. لكن **#1، #5، #6، #7،
#8، #9، #11، #14، #15 (9 بنود) مُصلَحة ومؤكَّدة لكن غير معلَّمة إطلاقًا** في الجدول الموحَّد — فجوة
مطابقة تمامًا لنمط `55032eb` اللي بنسجله في PROGRESS_LOG.md، بس أقدم بشهر تقريبًا. **مُستبعَدة من
جدول "المتبقي" تحت (لأنها فعلًا مُصلَحة، مش لأن قائمة استبعادك ذكرتها)** — لكن محتاجة نفس معاملة
اليوم (اقتباس دليل حي + علامة ✅) في جلسة لاحقة لو حبيت.

**كمان #16 و#10 حالتهم "جزئي" (زي #27) — الجزء المُصلَح مستبعَد من جدول "المتبقي"، الجزء المفتوح
باقٍ فيه ومُعلَّم بوضوح.**

---

## ⚠️ ملاحظتان على استبعادين طلبتهم تحديدًا

- **#27 (`arbitration-syndicates-repository-missing-methods`):** استبعدته بالكامل من الجدول
  التالي بناءً على طلبك — لكن **الجزء المُصلَح هو `list_user_cases` فقط**. 4 دوال (`get_cases_by_claimant`,
  `get_election_votes`, `get_syndicate_memberships`, `list_user_licenses`) + `list_candidates`
  **لسه مفقودة/مكسورة فعليًا في الكود، صفر إصلاح**. لو قصدك استبعاد البند كله من "المتبقي" فده تم،
  لكن الجزء ده لسه backlog حقيقي مفتوح — ذكرته هنا بدل ما يضيع.
- **#31 (`frontend-service-url-prefix-mismatch`):** **مش من ضمن الاستبعاد اللي طلبته (مش من
  #23-#26)**، لكن لاحظت أثناء الجرد إنه **يبدو مُصلَحًا فعليًا** عبر commit `6b4703a`
  ("fix(frontend): close backlog #31 - remove duplicated/wrong URL prefixes in 21 services/*.ts files"،
  2026-08-26 19:50) — **غير معلَّم ✅ في الملف الموحَّد، وغير مُتحقَّق منه بنفس منهجية "اقتباس حي" اليوم**.
  أدرجته في الجدول تحت بعلامة ⚠️ خاصة بدل ما أستبعده بصمت (قرار مش طلبته) أو أعرضه كـ"مفتوح تمامًا"
  (غير دقيق كمان).

---

## الجدول — البنود المتبقية فعليًا، مصنَّفة حسب سهولة الإصلاح

### 🟩 سطر واحد / تعديل ميكانيكي بسيط

| # | الاسم | الوصف المختصر | ملاحظة |
|---|---|---|---|
| 22 | `invitations-leads-route-ordering` | باج ترتيب تسجيل routes (`/{invitation_id}` قبل `/leads`) | نفس نمط `sovereign_entities.list_templates/list_components` المُصلَح سابقًا — نقل تسجيل الـroute فقط |
| 32 | `arbitration-syndicates-nominate-candidate-wrong-kwarg` | `candidate_user_id=` بدل `user_id=` في `ElectionCandidate(**kwargs)` | موضع واحد مؤكَّد، لسه محتاج تأكيد صفر انتشار قبل الإغلاق النهائي |
| 33 | `tenders-auctions-naive-vs-aware-datetime` | مقارنة `datetime.utcnow()` (naive) ضد أعمدة `timezone=True` | `datetime.now(timezone.utc)` بدل `datetime.utcnow()` في موضعين |
| 37 | `finance-transfer-payment-tx-hash-broken` | تخزين كائن `Transaction` كامل بدل `.tx_hash` نصي | **مركزي فعليًا (4 مواضع مؤكَّدة عبر 3-4 دومينات)** — الإصلاح نفسه ميكانيكي بسيط لكل موضع (`.tx_hash`)، لكن يستاهل جلسة واحدة تغطي الأربعة معًا بدل موضع بموضع |
| 40 | `realestate-ai-agents-execute-agent-action-stale-signature` | استدعاء `execute_agent_action` بالتوقيع القديم (`tenant_id=` بدل `idempotency_key=`) | نفس نمط #16 بالحرف — امتداد اكتُشف بعد إغلاق #16، يحتاج `grep` تأكيدي لباقي الدومينات |
| 43 | `frontend-service-export-import-name-mismatch` | تصدير `PascalCase` واستيراد `camelCase` في ملفات `services/*.ts` | موضعان مؤكَّدان (`realestate`, `iot`)، محتاج `grep` شامل لباقي الملفات قبل إغلاق نهائي |
| 38 | `tourism-sports-player-profile-wrong-column-filter` | `get_player_profile(player_id)` بتفلتر بعمود خطأ (`user_id` بدل `id`) | موضع واحد مؤكَّد بقراءة الكود فقط (غير مؤكَّد حيًا)، تعديل استعلام بسيط |

### 🟨 Migration بسيطة (إضافة عمود/فهرس)

| # | الاسم | الوصف المختصر | ملاحظة |
|---|---|---|---|
| 28 | `saas-service-catalog-missing-entries` | `saas_service_catalog` بلا صفوف لـ`tenders`/`auctions`/`service_marketplace`/`zamakana` | **بيانات seed ناقصة، مش migration schema** — إدراج صفوف مباشرة، صفر تعديل كود |
| 45 | `global-unique-column-conflicts-with-tenant-scoped-query` | `translation.TranslationCache.text_hash` — `unique=True` عالمي يتعارض مع فلترة tenant-scoped | يحتاج migration لتحويله لـ**partial unique index** (`UNIQUE(text_hash) WHERE tenant_id=...`) — غير مؤكَّد حيًا، وغير مفحوص انتشاره لدومينات تانية |

### 🟥 قرار تصميمي (يحتاج تفكير/تصميم فعلي قبل أي كود)

| # | الاسم | الوصف المختصر | ملاحظة |
|---|---|---|---|
| 10 (الجزء المتبقي) | `identity-user-referred-by-field-missing` | يحجب #10 بالكامل عبر الـ12 دومين — `User.referred_by` غير موجود | قرار نظام إحالة عام (عمود مسطَّح؟ `ReferralTree` بنطاق `GLOBAL`؟) |
| 16 (الجزء المتبقي) | `ai-agents-execute-action-commit-inside-begin-nested` (موضعان: `realestate`, `invitations`) | `commit()` داخل `execute_agent_action` يتعارض مع `begin_nested()` المحيط | إعادة هيكلة حدود transaction، مش مجرد إسقاط kwarg |
| 21 | `invoicing-invoice-response-metadata-collision` | `Invoice.metadata` يصطدم بـ`SQLAlchemy.Base.metadata` | قرار: إعادة تسمية العمود، أم `Column("metadata", key="invoice_metadata")`؟ يمنع `list_invoices`/`GET /invoicing/invoices` بالكامل لأي تينانت عنده فاتورة |
| 29 | `finance-service-hold-funds-missing` | `FinanceService.hold_funds`/`release_held_funds` غير موجودتين | تصميم منطق حجز/تحرير أموال فعلي على `FinanceService`، مش rename |
| 30 | `tenders-auctions-router-no-read-endpoints` | صفر `router` handler لدوال القراءة الموجودة فعلًا بـ`repository.py` | فجوة تصميم/تنفيذ ناقص، مش constructor-mismatch أصلًا |
| 39 | `transport-domain-tables-never-migrated` | 7 جداول أساسية لدومين `transport` غير موجودة إطلاقًا في الـDB | قرار معماري: هل الدومين يستحق تفعيل فعلي؟ |
| 41 | `insurance-review-claim-issuer-entity-id-reviewer-id-mismatch` | فحص ثانوي يقارن مساحتي معرِّفات مختلفتين تمامًا (`sovereign_entities` مقابل `users`) | 🔴 **الإصلاح الساذج قد يفتح ثغرة صلاحية مختلفة** — نفس تحذير `sovereign_entities`/#32 — يحتاج فحص إضافي قبل أي كود |

### ⚪ خارج التصنيف (ليست بند بج قياسي، أو ممنوعة اللمس)

| # | الاسم | السبب |
|---|---|---|
| 3 | Phase 16 الأصلي (استكمال) | استكمال جلسة قديمة، علاقتها بـcommits سابقة غير مؤكَّدة 100% — يحتاج تحقيق مش تصنيف فيزة/migration |
| 42 | `health-create-prescription-zero-ownership-check` | 🔴🔴🔴 **توجيه صريح سابق من المستخدم: ممنوع اللمس (لا كود ولا تصميم) بلا جلسة نقاش منفصلة مخصَّصة — حساسية طبية** |

### 🟡 يحتاج جرد (`grep`) قبل تحديد فئة الإصلاح

| # | الاسم | السبب |
|---|---|---|
| 4 (الجزآن المتبقيان) | `silent-write-regression` — `saas.process_auto_renewals` (فرع `except`)، `saas.can_access_service` | غير مؤكَّدين DB-level بعد (بعكس `cancel_subscription` المُصلَح) |
| 13 | `invoicing-create-invoice-wrong-kwarg` (اسم الـkwarg نفسه) | مؤكَّد في `service_marketplace` بس، محتاج `grep` شامل لباقي الـ12 دومين — القرار السابق كان معالجته مع #14 (مُغلَق) لكن هذا الجزء تحديدًا لم يُعاد تأكيده مستقلًا |

### ⚠️ يحتاج تحقق/تأكيد أولًا (مش تصنيف فيزة مباشر)

| # | الاسم | السبب |
|---|---|---|
| 31 | `frontend-service-url-prefix-mismatch` | **يبدو مُصلَحًا فعليًا** عبر commit `6b4703a` (2026-08-26) — لكن غير مُتحقَّق منه هنا بنفس منهجية "اقتباس حي" — راجع الملاحظة أعلى الجدول |
| 27 (الجزء المتبقي) | `arbitration-syndicates-repository-missing-methods` — 4 دوال + `list_candidates` | مُستبعَد بالكامل من هذا الجدول بناءً على طلبك، لكن الجزء ده **لسه مفتوح فعليًا** — راجع الملاحظة أعلى الجدول |

---

## ملخص عددي (البنود المتبقية فعليًا، بعد كل الاستبعادات)

| الفئة | العدد |
|---|---|
| 🟩 سطر واحد / ميكانيكي | 7 (#22, #32, #33, #37, #40, #43, #38) |
| 🟨 Migration بسيطة | 2 (#28, #45) |
| 🟥 قرار تصميمي | 6 (بقية #10، بقية #16، #21، #29، #30، #39، #41 — 7 فعليًا) |
| ⚪ خارج التصنيف/ممنوع اللمس | 2 (#3, #42) |
| 🟡 يحتاج جرد أولًا | 2 (بقية #4، #13) |
| ⚠️ يحتاج تحقق قبل التصنيف | 2 (#31، بقية #27) |

**صفر تنفيذ فوري — الجدول أعلاه للموافقة على الترتيب/الأولوية فقط.**
