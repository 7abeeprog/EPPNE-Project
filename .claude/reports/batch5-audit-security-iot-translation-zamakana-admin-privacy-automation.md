# جلسة جرد + أمان مدمجة — الدفعة 5: iot, translation, zamakana, admin, privacy, automation

**بدأ التسجيل:** 2026-08-26 · **اكتمل التحقق الحي:** 2026-08-26 · **اكتمل تنفيذ الإصلاحات المعتمَدة:** 2026-08-26
**الحالة:** ✅ **جرد + فحص أمني كامل (6 دومينات) + تحقق حي مكتمل. الإصلاحات الأربعة المعتمَدة (§9.1 بنود 1-4) نُفِّذت وتحقَّقت حيًا بالكامل (§10) — بانتظار موافقتك على الـ`commit` (git status/diff في §10.5).**

**المنهجية:** نفس منهجية batch1-4 بالضبط — قراءة كود كاملة (فوركات متوازية) ثم تحقق حي مباشر (سيرفر uvicorn محلي + DB مباشر) بمعرفة المنسق الرئيسي لأعلى النتائج خطورة.

**المرجع الميكانيكي:** `.claude/plans/critical-finding-xtenant-systemic.md` (تصنيف iot/privacy/admin كـ SAFE من Phase 14، automation SUSPICIOUS #7 — secrets بلا حماية admin، translation/zamakana SAFE)، `.claude/reports/batch4-audit-security-realestate-insurance-health.md` (أحدث منهجية + اكتشاف بادئة المسار المضاعفة).

**⚠️ ملاحظة إلزامية (بطلب المستخدم):** فحص "مربوط بفرونت إند" عبر curl/requests المباشر للباك إند **لا يعكس بالضرورة** الاستخدام الفعلي عبر الواجهة — batch4 اكتشفت باج بادئة مسار مضاعفة عابر لـ13+ دومين (`/domain/domain/...` في `services/*.ts` بينما الباك إند مسجَّل ببادئة واحدة). **لا نفترض "مربوط بفرونت إند = آمن من هذا الباج"** — نوثّق الحالة الفعلية فقط لكل دومين من الستة، والحكم النهائي مؤجَّل لجلسة الفحص الشامل القادمة المخصَّصة لهذا الباج (راجع §9 من batch4).

**سياق خاص بـ automation:** Phase 12 قديمًا صلح جزئيًا endpoints الـ secrets (موثَّقة في PROGRESS_LOG.md القديم) — يجب التحقق هل هذا الإصلاح لسه سليم، والتركيز العميق على أي endpoints لم تُغطَّ وقتها.

**سياق خاص بـ admin/privacy:** موثَّقين كـ"بالإضافة لـ" مش جزء من الـ34 الأساسية في الجرد القديم (Phase 14) — يجب التأكد من نطاقهم الفعلي بالقراءة، لا افتراض الحجم مسبقًا.

---

## 0) ملخص تنفيذي فوري

| الدومين | عدد endpoints | النمط الأمني | الأخطر | مربوط بفرونت إند فعليًا؟ |
|---|---|---|---|---|
| **iot** | 11 | 🟢 نظيف — كل الاستخدامات `current_user.tenant_id` حقيقي + فحوصات ملكية مزدوجة | لا يوجد IDOR — أفضل دومين في السلسلة | ❌ **لا — 3 طبقات أعطال مستقلة** (بادئة مضاعفة + export/import mismatch + مكوّنات مفقودة) |
| **translation** | 4 | 🟢 آمن من IDOR — كل شيء مربوط بـ`current_user` فعليًا | لا يوجد IDOR — باج تصميمي منفصل (`text_hash` unique عالمي) | ❌ بادئة مسار مضاعفة (غير مختبَر حيًا) |
| **zamakana** | 19 مسار | 🔴🔴🔴🔴 **الأخطر في هذه الدفعة** — 8 مسارات GET بلا `current_user` إطلاقًا | `list_nodes`/`get_node`/`get_graph`/`list_campaigns`/`get_campaign`/`list_scenarios`/`get_scenario`/`get_campaign_pledges` — تسريب قراءة كامل بلا أي هوية | ❌ بادئة مسار مضاعفة + **الدومين مقفول عن الجميع حاليًا ببوابة SaaS مفقودة (self-DoS منفصل)** |
| **admin** | 1 | 🟢 آمن تصميميًا، غير قابل للوصول | — | ❌ غير مسجَّل في `main.py`، لا frontend مقابل |
| **privacy** | 7 | 🟢 IDOR-safe لكن 🔴🔴 قسم الإدارة (GDPR) مقفول بالكامل (type mismatch) | `is_privacy_officer(admin_id: int)` — self-DoS، طلبات محو بيانات عالقة للأبد | ❌ بادئة مسار مضاعفة (غير مختبَر حيًا) |
| **automation** | 15 | 🟢 آمن (Phase 12 سليم + JWT ownership حقيقي في 12/12 الباقيين)، عدا تلوّث بيانات في الإنشاء | `create_workflow` — تلوّث تينانت عبر هيدر (تلوّث فقط، لا تسريب) | ✅ **الوحيد بلا باج بادئة مضاعفة — الأكثر ارتباطًا فعليًا بفرونت إند حقيقي عبر كل الدفعات** |

**🔴🔴🔴🔴 الاكتشاف الأخطر في هذه الدفعة — مؤكَّد حيًا بالكامل:** `zamakana` — 8 endpoints قراءة **بلا `current_user` في التوقيع إطلاقًا**، تعتمد فقط على هيدر `X-Tenant-ID` (أو حتى بدونه). زائر مجهول تمامًا بلا أي توكن قرأ فعليًا محتوى `_SECRET` أنشأته `TEST_instr_b` (تينانت16) — راجع §7.1 للدليل الحي الكامل (هجوم + مسار شرعي + `SELECT` مستقل). **التصنيف القديم "zamakana: SAFE (مربوط بـuser_id)" كان صحيحًا فقط للكتابة/التعديل — فوّت تمامًا فئة القراءة العامة.**

**🟢 اكتشافات إيجابية بارزة (خلاف نمط batch1-4):** (1) `iot` نظيف 100% من IDOR — أفضل دومين مُفحوص حتى الآن. (2) ثغرة `sender_id=1` الهاردكودد في `iot.settle_carbon_credits` (موثَّقة كحرجة في الملف المرجعي) **مُصلَحة فعليًا** منذ commit `0e6a4aa` بلا تحديث للوثيقة. (3) `automation` هو **الدومين الوحيد عبر كل الدفعات (1-5) بلا باج بادئة المسار المضاعفة** — مربوط فعليًا بصفحة فرونت إند حقيقية.

**اكتشاف self-DoS جديد (غير IDOR):** بوابة SaaS لـ`zamakana` (`saas_service_catalog`) **لا تحتوي صف `code='zamakana'` إطلاقًا** — يعني الدومين بالكامل غير قابل للاستخدام لأي تينانت حاليًا (بغض النظر عن ثغرة IDOR)، حتى يُضاف الصف. اكتُشف أثناء تحضير التحقق الحي، راجع §7.

---

## 1) جدول `iot` — 11 endpoint ✅ نظيف

**النطاق:** `router.py`(230)، `service.py`(267)، `repository.py`(179)، `models.py`(192)، `schemas.py`(109) — قراءة كاملة (فورك).

| # | Endpoint | الوظيفة الفعلية | `current_user`؟ | مصدر `tenant_id` | فلتر repository | تصنيف |
|---|---|---|---|---|---|---|
| 1 | `POST /iot/assets` | إنشاء أصل ذكي | ✅ active_user | `current_user.tenant_id` | `owner_id=current_user.id` | 🟢 آمن |
| 2 | `GET /iot/assets` | أصولي | ✅ active_user | `current_user.tenant_id` | tenant **و** owner معًا | 🟢 آمن |
| 3 | `GET /iot/assets/{id}` | تفاصيل أصل | ✅ active_user | `current_user.tenant_id` | فلتر tenant + فحص ملكية يدوي في service (404 لو مش المالك) | 🟢 آمن |
| 4 | `PATCH /iot/assets/{id}` | تحديث أصل | ✅ active_user | `current_user.tenant_id` | نفس فحص #3 | 🟢 آمن |
| 5 | `POST /iot/grids` | إنشاء محطة مرافق (سوبريوزر) | ✅ superuser | `current_user.tenant_id` | يُكتب لتينانت المستخدم | 🟢 آمن |
| 6 | `GET /iot/grids` | قائمة المحطات | ✅ active_user | `current_user.tenant_id` | tenant فقط (منطقي — مورد تينانت لا فرد) | 🟢 آمن |
| 7 | `POST /iot/readings` | استقبال قراءة جهاز | ✅ active_user | `current_user.tenant_id` | tenant فقط، بلا فحص ملكية الأصل | 🟠 صلاحية واسعة **داخل-تينانت** (مش IDOR عبر-تينانت) |
| 8 | `GET /iot/readings` | القراءات | ✅ active_user | `current_user.tenant_id` | tenant + ownership عبر subquery | 🟢 آمن |
| 9 | `POST /iot/carbon/settle` | تسييل كربون → تحويل مالي فعلي | ✅ active_user | `current_user.tenant_id` | `owner_id=current_user.id` **و** tenant | 🟢 آمن |
| 10 | `POST /iot/maintenance` | تسجيل طلب صيانة | ✅ active_user | `current_user.tenant_id` | يُكتب لتينانت المستخدم | 🟢 آمن |
| 11 | `POST /iot/maintenance/{id}/resolve` | إغلاق طلب صيانة | ✅ active_user | `current_user.tenant_id` | `log_id` + tenant فقط | 🟠 صلاحية واسعة داخل-تينانت |

**خلاصة X-Tenant-ID:** صفر استخدام لـ`get_current_tenant`/الهيدر (11/11 مؤكَّد). **تصنيف Phase 14 "SAFE" لا يزال دقيقًا 100%** — أفضل من معظم الدومينات الممسوحة (فحوصات ملكية مزدوجة حقيقية).

### 1.1) تصحيح لـ PROJECT_AUDIT.md — "صفر أعمدة tenant_id" لم يعد صحيحًا

كل الجداول الستة (`smart_assets`, `utility_grids`, `utility_readings`, `maintenance_logs`, `idempotency_records`, `iot_request_logs`) عندها عمود `tenant_id` حقيقي (`ForeignKey`, `nullable=False, index=True`) — على الأرجح كان الادعاء صحيحًا وقت التدقيق الأصلي (2026-08-08) وسُدَّ لاحقًا بلا تحديث المستند.

### 1.2) 🟢 اكتشاف إيجابي: hardcoded `sender_id=1` في `settle_carbon_credits` — **مُصلَح فعليًا**، خلافًا لما هو موثَّق في `critical-finding-xtenant-systemic.md`

القراءة الفعلية (`service.py:212-221`) تستخدم `get_or_create_system_account(db, tenant_id)` (`app/core/system_account_service.py:10-46`) — حساب نظام **مخصَّص لكل تينانت** (`is_system_account=True`, `is_active=False`)، **صفر رقم هاردكودد**. مؤكَّد بـ`git log`: commit `0e6a4aa` — *"feat(finance): convert 9 tenant-system-account call sites (7 domains)"*.

**⚠️ يستاهل تحقق منفصل خارج iot:** لو الـcommit فعلاً غطى 7 دومينات، فمن المرجَّح إن `commerce.release_commissions`/`affiliate.withdraw_commissions` (نفس فئة الثغرة الموثَّقة في الملف المرجعي) **مُصلَحين فعليًا كمان** — تحديث حالة الملف المرجعي يحتاج جلسة منفصلة (خارج batch5).

### 1.3) روابط cross-domain

`finance.transfer()` ← `settle_carbon_credits` فقط (تحويل من حساب نظام التينانت لمالك الأصل) + `system_account_service` (core) + `identity.repository.UserRepository` (بريد المالك). **لا استدعاء** لـ`affiliate`/`communications`/`ai_agents`/`invoicing`/`saas` — و**لا بوابة SaaS features** (خلافًا لـ realestate/insurance في batch4).

### 1.4) الربط بالفرونت إند — موثَّق، بلا حكم نهائي

`eppne-web/services/iot.service.ts` (209 سطر) — **نفس باج بادئة المسار المضاعفة** (batch4 §3): يستدعي `/iot/iot/...` بدل `/iot/...` → 404 مضمون (نفس البنية، غير مختبَر حيًا). **+ طبقة عطل إضافية مستقلة:** الملف يُصدِّر `IoTService` (PascalCase) لكن كل المكوّنات (`AssetCard`, `AssetsManager`, `CarbonCreditPanel`, `IoTDashboardStats`) تستورد `{ iotService }` (camelCase) — خطأ `TS2724` قاطع، موثَّق فعليًا في `eppne-web/link-fix-verification.txt:1163-1177`. **+ صفحة `iot/page.tsx` نفسها بها `TS2307` لمكوّنين مفقودين تمامًا** (`ReadingsChart`, `MaintenanceLogs`). **الخلاصة: 3 طبقات أعطال مستقلة — لا يوجد استخدام فرونت إند حقيقي وظيفي لـ iot اليوم**، وليس مجرد باج بادئة مسار.

### 1.5) أنماط منتشرة

| # | النمط | الموقع | ملاحظة |
|---|---|---|---|
| 1 | بادئة مسار مضاعفة | `iot.service.ts` (11 استدعاء) | تأكيد إضافي (batch4 §3) |
| 2 | "Service layer صحيح، استيراد مكسور" | تصدير `IoTService` مقابل استيراد `iotService` | **الموضع الثاني** لنفس الفئة (بعد realestate، batch4 §6.6) — يرفّع احتمال كونه نمط عابر لدومينات |
| 3 | صلاحية واسعة داخل-تينانت (لا IDOR) | `readings`, `resolve_maintenance` | سؤال منتجي لا أمني — قد يكون مقصود (صيانة مشتركة) |
| 4 | ثغرة هاردكودد "مُصلَحة صامتًا" بلا تحديث الوثيقة المرجعية | `settle_carbon_credits` | يستاهل تحديث `critical-finding-xtenant-systemic.md` |

### 1.6) تحقق حي مرشَّح لـ iot

لا توجد فجوة IDOR عبر-تينانت تستاهل أولوية عالية. اختياري/منخفض: تحقق حي إن `settle_carbon_credits` بتستخدم حساب نظام مخصَّص فعليًا (لا `user_id=1`) — سيُنفَّذ ضمن جولة التحقق الحي الشاملة لاحقًا لو الوقت سمح.

---

## 2) جدول `translation` — 4 endpoints ✅ آمن من IDOR (باج تصميمي منفصل)

**النطاق:** `router.py`(75)، `service.py`(254)، `repository.py`(79)، `models.py`(71) — قراءة كاملة (فورك).

| # | Endpoint | الوظيفة الفعلية | `current_user`؟ | مصدر tenant_id | فلتر repository | تصنيف |
|---|---|---|---|---|---|---|
| 1 | `POST /translation/translate` | ترجمة نص (+كاش+خصم رصيد مستقبلي) | ✅ active_user | **هيدر** | `tenant_id`+`text_hash`، لكن `text_hash` unique **عالميًا** (§2.1) | 🟠 باج تصميمي، مش IDOR |
| 2 | `POST /translation/batch-translate` | ترجمة جماعية | ✅ active_user | هيدر (موروث) | نفس أعلاه | 🟠 نفس الباج |
| 3 | `POST /translation/chat-translate` | ترجمة رسالة محادثة | ✅ active_user | هيدر (موروث) | نفس أعلاه | 🟠 نفس الباج |
| 4 | `GET /translation/languages` | قائمة اللغات المدعومة (عامة) | ❌ بلا مصادقة | — | بيانات عامة بالتصميم | 🟢 آمن |

**تحقق التصنيف القديم "SAFE":** ✅ صحيح بخصوص IDOR — لا يوجد أي resource موجود بالفعل يُقرأ/يُكتب لمستخدم/تينانت آخر عبر ID (لا قائمة "ترجماتي").

### 2.1) باج جديد: `text_hash` unique عالميًا يتعارض مع فلترة `tenant_id`

`models.py:16` — `TranslationCache.text_hash` **unique index عالمي**، لكن `repository.py:13-20` يفلتر بـ`tenant_id`+`text_hash` معًا. لو تينانت A ترجم نص X، وتينانت B حاول ترجمة **نفس النص بالحرف** لاحقًا → lookup يرجّع `None` (الصف موجود لكن بـtenant مختلف) → API ترجمة حقيقي يُستدعى → `save_cache` يصطدم بـ`IntegrityError` (انتهاك unique) → **500**. مش تسريب، لكن **DoS محتمل** لنصوص شائعة بين تينانتين. نمط جديد: "uniqueness عالمي (DB) يتعارض مع عزل tenant-scoped بالاستعلام" — يستاهل فحص لو موجود بدومينات أخرى. `_debit_wallet` معطَّلة حاليًا (تعليق "سيُفعَّل لاحقًا") — صفر أثر مالي حقيقي الآن.

**cross-domain:** `translation` لا يستدعي أي دومين آخر — معزول ماليًا (مطابق لـ`health` في batch4).

**الربط بالفرونت إند:** `translation.service.ts` بنفس باج بادئة المسار المضاعفة (`/translation/translation/translate`) — 404 مضمون بنفس آلية batch4 (غير مختبَر حيًا).

---

## 3) جدول `zamakana` — 19 مسار فريد (14 endpoint معلَن) 🔴🔴🔴🔴 التصنيف القديم "SAFE" **غير دقيق — IDOR قراءة بلا أي مصادقة على 8 مسارات**

**النطاق:** `router.py`(313)، `service.py`(661)، `repository.py`(352)، `schemas.py`(124)، `models.py` — قراءة كاملة (فورك).

| # | Endpoint | الوظيفة الفعلية | `current_user`؟ | مصدر tenant_id | فلتر repository | تصنيف |
|---|---|---|---|---|---|---|
| 1 | `POST /nodes` | إنشاء عقدة معرفية | ✅ active_user | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات |
| 2 | `GET /nodes` | قائمة العقد | ❌ **بلا current_user** | **هيدر فقط** | tenant(هيدر) فقط | 🔴🔴🔴🔴 **IDOR بلا مصادقة** |
| 3 | `GET /nodes/{id}` | تفاصيل عقدة | ❌ **بلا current_user** | **هيدر فقط** | نفس أعلاه | 🔴🔴🔴🔴 |
| 4 | `PUT /nodes/{id}` | تحديث عقدة | ✅ active_user | هيدر (lookup) + `created_by==user_id` | owner check حقيقي | 🟠 محمي جزئيًا |
| 5 | `DELETE /nodes/{id}` | حذف عقدة | ✅ active_user | نفس أعلاه | نفس أعلاه | 🟠 نفس الشيء |
| 6 | `POST /edges` | ربط عقدتين (تأثير سببي) | ✅ active_user | **هيدر** | العقدتان تُجلَبان بالهيدر | 🔴 تلوّث بيانات |
| 7 | `GET /graph` | الرسم البياني الكامل | ❌ **بلا current_user** | **هيدر فقط** | tenant(هيدر) فقط | 🔴🔴🔴🔴 |
| 8 | `POST /campaigns` | إنشاء حملة كوكبية | ✅ active_user | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات |
| 9 | `GET /campaigns` | قائمة الحملات | ❌ **بلا current_user** | **هيدر فقط** | نفس النمط | 🔴🔴🔴🔴 |
| 10 | `GET /campaigns/{id}` | تفاصيل حملة | ❌ **بلا current_user** | **هيدر فقط** | نفس النمط | 🔴🔴🔴🔴 |
| 11 | `POST /pledges` | تعهد بساعات (+فاتورة فعلية >10 ساعة) | ✅ active_user | **هيدر** | `campaign` يُجلَب بالهيدر | 🔴🔴🔴 IDOR كتابة + فوترة عبر-تينانت |
| 12 | `POST /pledges/{id}/fulfill` | إثبات إنجاز تعهد | ✅ active_user | هيدر + `pledge.user_id==user_id` | owner check حقيقي | 🟠 محمي عمليًا |
| 13 | `GET /campaigns/{id}/pledges` | قائمة تعهدات حملة | ❌ **بلا current_user** | **هيدر فقط** | نفس النمط | 🔴🔴🔴🔴 |
| 14 | `POST /scenarios` | إنشاء سيناريو مستقبلي | ✅ active_user | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات |
| 15 | `GET /scenarios` | قائمة السيناريوهات | ❌ **بلا current_user** | **هيدر فقط** | نفس النمط | 🔴🔴🔴🔴 |
| 16 | `GET /scenarios/{id}` | تفاصيل سيناريو | ❌ **بلا current_user** | **هيدر فقط** | نفس النمط | 🔴🔴🔴🔴 |
| 17 | `POST /scenarios/{id}/analyze` | تحليل AI (+فاتورة 10 MRUSDT) | ✅ active_user، `created_by==user_id` | هيدر (lookup) | owner check حقيقي بعد الجلب بالهيدر | 🟠 محمي عمليًا |
| 18 | `POST /scenarios/{id}/feedback` | إضافة مراجعة بشرية | ✅ active_user | **هيدر** | `get_scenario` بالهيدر، **صفر ownership check** | 🔴 IDOR كتابة |
| 19 | `POST /scenarios/{id}/confirm` | اعتماد سيناريو | ✅ active_user، owner check حقيقي | هيدر (lookup) | owner check حقيقي | 🟠 محمي عمليًا |

**الحكم:** التصنيف القديم "مربوط بـuser_id في العمليات الحساسة" صحيح **فقط للكتابة/تعديل/حذف** — لكنه فوّت تمامًا **8 مسارات GET بلا `current_user` في التوقيع إطلاقًا**: أي زائر مجهول تمامًا (بلا أي توكن) يقرأ كامل شبكة المعرفة/الحملات/السيناريوهات/التعهدات لأي تينانت بمجرد هيدر `X-Tenant-ID` (أو حتى بدونه — الافتراضي=1 يكفي). **يطابق أعلى فئة خطورة موثَّقة في batch4** (`realestate.get_development`/`units-for-sale`).

### 3.1) روابط cross-domain

```
zamakana ──> ai_governance.check_and_consume (تحليل AI)
         ──> ai_agents.execute_agent_action (تحليل AI فعلي)
         ──> invoicing.create_invoice (فاتورة تعهد >10 ساعة + فاتورة تحليل AI = 10 MRUSDT)
         ──> affiliate.register_commission (عمولة إحالة عند node/campaign/pledge fulfillment)
         ──> saas.can_access_service("zamakana") (بوابة SaaS على كل عملية تقريبًا)
         ──> identity.UserRepository.get_by_id (referred_by)
```
كل الاستدعاءات دي تمرر `tenant_id` من الهيدر الملوَّث — يعني فاتورة حقيقية ممكن تتنشئ تحت تينانت مزوَّر.

### 3.2) الربط بالفرونت إند

`zamakana.ts` بنفس باج بادئة المسار المضاعفة (`/zamakana/zamakana/nodes`، 19 نداء) — 404 مضمون بنفس آلية batch4، غير مختبَر حيًا.

### 3.3) أنماط منتشرة جديدة

| # | النمط | الموقع | ملاحظة |
|---|---|---|---|
| 1 | بادئة مسار مضاعفة (تكرار batch4 §3) | `translation.service.ts`, `zamakana.ts` | يرفع العدّ التراكمي لـ15+ ملف |
| 2 | **GET endpoints بلا `current_user` إطلاقًا، تعتمد على هيدر فقط** | `zamakana` (8 مسارات) | أخطر من "سوبريوزر بهيدر مزوَّر" المعتاد — أقرب لفئة `ai_governance.check_and_consume`/`realestate.get_development` |
| 3 | uniqueness عالمي (DB) يتعارض مع فلترة tenant-scoped | `translation.TranslationCache.text_hash` | نمط جديد، يستاهل فحص بدومينات أخرى |

### 3.4) نقاط تستاهل تحقق حي — **zamakana أولوية قصوى للجولة الحية**

1. 🔴🔴🔴🔴 **أولوية قصوى:** `list_nodes`/`get_node`/`get_knowledge_graph`/`list_campaigns`/`get_campaign`/`list_scenarios`/`get_scenario`/`get_campaign_pledges` — طلب **بلا Authorization header إطلاقًا** مع/بدون `X-Tenant-ID` مزوَّر. سيناريو: تينانت16 ينشئ node/campaign/scenario بمحتوى `_SECRET`، زائر مجهول + `X-Tenant-ID: 16` يقرأها.
2. 🟠 متوسطة: `pledge_time`/`generate_ai_analysis` — تحقق فاتورة `invoicing.create_invoice` عبر-تينانت + تجاوز بوابة SaaS بالهيدر.
3. 🟢 منخفضة (وظيفي لا أمني): `translation.text_hash` تعارض — نفس النص من تينانتين مختلفين، توقع 500.

---

## 4) دومين `admin` — endpoint واحد، غير قابل للوصول (مطابق تمامًا لـ Phase 14)

**النطاق:** ملف واحد فقط `router.py` (21 سطر) — لا `service.py`/`repository.py`/`schemas.py`/`models.py`/`__init__.py` إطلاقًا (فورك).

| # | Endpoint | الوظيفة | `current_user`؟ | مصدر tenant_id | تصنيف |
|---|---|---|---|---|---|
| 1 | `POST /admin/system/toggle-ai-agents` | Kill-switch عالمي لكل وكلاء AI بالمنصة | ✅ `get_current_superuser` | لا يوجد — flag نظامي عالمي | 🟢 آمن تصميميًا (لو وصل) |

**حالة التسجيل في main.py:** `grep -i admin` على الملف كاملًا → **صفر نتيجة**. لا يزال **غير مسجَّل**، بالضبط كما وثَّق Phase 14 (رغم `main.py` يظهر معدَّل في git status الحالي — التعديل لا علاقة له بـ admin). **النطاق لم يزد** — لسه دومين طرف واحد. لا يوجد frontend service مقابل (بحث نصي عن `toggle-ai-agents` في `eppne-web` بالكامل → صفر نتيجة). **لا تحقق حي مطلوب** — endpoint غير قابل للوصول عبر HTTP بأي حال.

---

## 5) دومين `privacy` — 7 endpoints، IDOR-safe لكن 2 باج self-DoS خطيران على قسم الامتثال (GDPR)

**النطاق:** `router.py`(246)، `service.py`(279)، `repository.py`(356)، `models.py`(122)، `schemas.py`(226)، `tasks.py`(117) — قراءة كاملة (فورك). مسجَّل فعليًا: `main.py:52,286` → `/api/privacy/...`.

| # | Endpoint | الوظيفة الفعلية | `current_user`؟ | مصدر tenant_id | فلتر repository | تصنيف |
|---|---|---|---|---|---|---|
| 1 | `GET /privacy/settings` | جلب إعدادات خصوصية | ✅ active_user | `current_user.tenant_id` | `user_id` **و** tenant معًا | 🟢 آمن |
| 2 | `PUT /privacy/settings` | تحديث إعدادات الخصوصية | ✅ active_user | `current_user.tenant_id` | نفس #1 | 🟢 آمن |
| 3 | `POST /privacy/consent/log` | تسجيل موافقة GDPR/PDPL (+تشفير IP) | ✅ active_user | `current_user.tenant_id` | يُكتب بمعرف حقيقي | 🟢 آمن |
| 4 | `POST /privacy/erasure/request` | طلب محو بيانات جديد | ✅ active_user | `current_user.tenant_id` | فحص تكرار `user_id`+tenant | 🟢 آمن |
| 5 | `GET /privacy/erasure/requests` | طلباتي | ✅ active_user | `current_user.tenant_id` | `user_id` **و** tenant معًا | 🟢 آمن |
| 6 | `POST /privacy/admin/erasure/{id}/process` | موافقة/رفض محو (+مسح فعلي 7 قطاعات+حرق توكن+IPFS) | ✅ active_user (فحص صلاحية داخلي) | `current_user.tenant_id` | `request_id` **مُتجاهَل تمامًا** (§5.2) | 🔴🔴 باج وظيفي خطير |
| 7 | `GET /privacy/admin/erasure/pending` | طلبات المحو المعلقة (لمشرفي التينانت) | ✅ active_user | `current_user.tenant_id` | tenant فقط (منطقي) | 🔴 self-DoS (§5.1) |

**خلاصة X-Tenant-ID:** صفر استخدام للهيدر عبر كل الـ7 — مطابق تمامًا لـ Phase 14.

### 5.1) 🔴 اكتشاف جديد — `is_privacy_officer(admin_id: int)`: type mismatch يقفل قسم الإدارة بالكامل

`core/security.py:189` — التوقيع يتوقع `User` كامل (`getattr(user, "system_role", None)`)، لكن موضعا الاستدعاء الوحيدان (`privacy/router.py:237`, `privacy/service.py:124`) يمرّران `int` (`current_user.id`) بدل الكائن. `getattr(<int>, "system_role", None)` → `None` دائمًا → الدالة ترجّع `False` **لأي مستخدم، حتى SUPER_ADMIN حقيقي**. **الأثر:** `GET /admin/erasure/pending` و`POST /admin/erasure/{id}/process` مقفولان بـ403 لأي طالب بلا استثناء — طلبات محو بيانات GDPR حقيقية **عالقة PENDING للأبد**. self-DoS، مش تسريب (لا خطر عبر-تينانت لأن لا أحد يصل أصلًا).

### 5.2) 🔴 اكتشاف جديد — `get_erasure_request` يتجاهل `request_id` تمامًا

`repository.py:102-109` — `WHERE status=PENDING AND tenant_id=X` فقط، **`request_id` غير مستخدَم في أي شرط**. لو باج §5.1 اتصلح مستقبلًا: أي `request_id` (صحيح أو تعسفي) يجلب أول/الوحيد طلب PENDING لنفس التينانت — أو `MultipleResultsFound` (كراش 500) لو أكثر من طلب PENDING واحد. **مستقل تمامًا عن §5.1** — إصلاح واحد لا يكفي.

### 5.2b) 🔴 اكتشاف جديد (تحقق مباشر من المنسق، خارج نطاق الفورك) — `_erase_module_data` يشير لجداول غير موجودة أصلًا لـ 3 من 7 قطاعات

تتبّع أسماء الجداول المُمرَّرة حرفيًا لـ`_delete_and_tombstone` (`service.py:200-252`) ومقارنتها بـ`__tablename__` الفعلي في `models.py` لكل دومين مستهدَف (grep شامل، تأكيد مباشر):

| القطاع (`target_module`) | الجدول المُستخدَم في privacy/service.py | موجود فعليًا؟ | الاسم الصحيح |
|---|---|---|---|
| `health` | `health_records`, `biometrics` | ❌ **غير موجودين** | `medical_profiles`/`biometric_logs`/... (health/models.py) |
| `iot` | `sensor_data`, `devices` | ❌ **غير موجودين** | `smart_assets`, `utility_readings` (iot/models.py، مؤكَّدة من فورك iot §1) |
| `realestate` | `properties`, `leases` | ❌ **غير موجودين** | `property_units`/`land_assets` (properties)، **لا يوجد مكافئ لـ`leases` إطلاقًا** — لا `rental_contracts` ولا غيره اتسمّى بهذا الاسم |
| `identity`, `academy`, `finance`, `commerce` | (8 جداول) | ✅ كلها موجودة بأسمائها الصحيحة | — |

**الأثر:** أي `DataErasureRequestCreate.target_module` من `{"health", "iot", "realestate", "all"}` (4 من 8 قيم صالحة في الـschema) يصطدم بـ`relation "..." does not exist` (خطأ SQL قاطع) أثناء `_erase_module_data`، **داخل `async with self.db.begin_nested()`** — يعني أي مسح جزئي ناجح سبقه (مثلًا identity/academy لو الطلب `"all"`) **يُلغى بالكامل بالـrollback**. هذا **مستقل تمامًا** عن باج §5.1 (`is_privacy_officer`) — حتى لو اتصلح §5.1 غدًا ويقدر Privacy Officer حقيقي يعتمد الطلب، أي طلب يستهدف health/iot/realestate/all **سيفشل عند التنفيذ الفعلي بخطأ SQL 500**، مش مجرد 403. **self-DoS ثالث مستقل في نفس الدومين، على نفس الميزة (الامتثال GDPR/PDPL).**

### 5.3) روابط cross-domain

`_erase_module_data` (service.py:176) يحذف مباشرة (**SQL خام `DELETE FROM <table> WHERE user_id=...`**) من: identity, academy (6 جداول), finance (transactions/wallets/payment_installments), commerce, health, iot, realestate — **صفر استدعاء لأي service layer** لتلك الدومينات (خطر بنيوي منفصل — حذف `wallets` مباشرة قد يكسر افتراضات محاسبية). + `task_queue`(Celery) لـ `unpin_from_ipfs`/`burn_tokens`.

### 5.4) الربط بالفرونت إند

`privacy.service.ts` (146 سطر) — نفس باج بادئة المسار المضاعفة (`/privacy/privacy/settings`، إلخ، 7 استدعاءات) — 404 مضمون بنفس آلية batch4، غير مختبَر حيًا.

### 5.5) أنماط منتشرة جديدة

| # | النمط | الموقع | ملاحظة |
|---|---|---|---|
| 1 | بادئة مسار مضاعفة | `privacy.service.ts` | تأكيد إضافي — الدومين 16+ في العدّ التراكمي |
| 2 | **تمرير `int` (ID) لدالة صلاحيات تتوقع `User` كامل** | `is_privacy_officer` (موضعان) | **نمط جديد تمامًا** — يستاهل grep شامل: أي دالة صلاحيات تانية `(user: User)` بتتنادى بـ`current_user.id` بالغلط |
| 3 | معامل ID مُعرَّف بالتوقيع لكن غير مستخدَم في WHERE | `get_erasure_request` | يستاهل تحقق لو موجود بدومينات تانية |
| 4 | اسم جدول SQL خام مكتوب حرفيًا لا يطابق `__tablename__` الفعلي (schema drift) | `_erase_module_data` (health/iot/realestate، §5.2b) | 3 من 7 قطاعات — يستاهل جرد شامل لأي استخدام `text("...FROM {table_name}...")` مشابه بدومينات تانية |

### 5.6) تحقق حي مرشَّح

أولوية منخفضة (كلا الباجين self-DoS، لا تسريب عبر-تينانت). اختياري: مستخدم عادي → `POST /erasure/request`، ثم SUPER_ADMIN حقيقي يحاول `GET /admin/erasure/pending` → توقع 403 (إثبات self-DoS بدقيقتين وقت). **لا أولوية للجولة الحية مقارنة بـ zamakana.**

---

## 6) دومين `automation` — 15 endpoint. Phase 12 (secrets) لسه سليم؛ 12 endpoint الباقيين آمنون فعليًا (نمط ownership حقيقي)، عدا تلوّث بيانات في الإنشاء

**النطاق:** `router.py`(347)، `service.py`(1105)، `repository.py`(212)، `models.py`(172) — قراءة كاملة (منسق رئيسي مباشرة، بعد فشل فورك أول بسبب حد استخدام الجلسة).

| # | Endpoint | الوظيفة الفعلية | `current_user`؟ | مصدر tenant_id | فلتر repository/service | تصنيف |
|---|---|---|---|---|---|---|
| 1 | `POST /automation/workflows` | إنشاء سير عمل | ✅ active_user | **هيدر** (`get_current_tenant`, router.py:33) | يُكتب مباشرة بـ`tenant_id`(هيدر)، `created_by=current_user.id`(حقيقي) | 🔴 تلوّث بيانات (سير عمل يُنشأ تحت تينانت مزوَّر) |
| 2 | `GET /automation/workflows` | قائمة سير العمل | ✅ active_user | **هيدر** (router.py:53) | `repo.list_workflows(tenant_id=هيدر)` ثم فلترة Python إضافية `created_by==user_id` **حقيقي** | 🟠 محمي عمليًا (owner check حقيقي بعد الجلب) — لا تسريب، لكن الهيدر لا يزال يحدد أي تينانت "يُنشأ" فيه بالخطوة #1 |
| 3 | `GET /automation/workflows/{id}` | تفاصيل سير عمل | ✅ active_user | لا هيدر، لا tenant param | `repo.get_workflow(id)` (بلا فلتر) + `workflow.created_by != user_id` **حقيقي** → 404 | 🟢 آمن (JWT-based ownership، غير قابل للتزوير) |
| 4 | `PUT /automation/workflows/{id}` | تحديث سير عمل | ✅ active_user | لا هيدر | نفس فحص #3 | 🟢 آمن |
| 5 | `DELETE /automation/workflows/{id}` | حذف سير عمل | ✅ active_user | لا هيدر | نفس فحص #3 | 🟢 آمن |
| 6 | `POST /automation/workflows/{id}/trigger` | تشغيل يدوي لسير عمل | ✅ active_user | لا هيدر | نفس فحص #3 + `trigger_type==MANUAL` | 🟢 آمن |
| 7 | `POST /automation/webhook/{path}` | استقبال webhook خارجي وتشغيل سير العمل | ❌ **بلا مصادقة بالتصميم** | — | `get_workflow_by_webhook_path(path)` — أمان الرابط نفسه (UUID4 hex، 128-bit) هو الحاجز الوحيد | 🟠 نمط شائع (secret-URL) لكن **صفر HMAC/توقيع payload تحقق** — أي طرف يعرف/يخمّن الرابط يشغّل الـworkflow بـpayload تعسفي |
| 8 | `GET /automation/ai-agents` | قائمة وكلاء AI متاحين لعقدة AI_AGENT | ✅ active_user | **هيدر** (router.py:223) | `ai_agents.repo.list_agents(tenant_id=هيدر, owner_id=user_id **حقيقي**)` | 🟢 آمن عمليًا (فلتر owner حقيقي يمنع التسريب رغم الهيدر) |
| 9 | `GET /automation/workflows/{id}/executions` | تنفيذات سير عمل | ✅ active_user | لا هيدر | `get_workflow` + `created_by==user_id` **حقيقي** قبل الجلب | 🟢 آمن |
| 10 | `GET /automation/executions/{id}` | تفاصيل تنفيذ | ✅ active_user | لا هيدر | نفس النمط عبر `workflow.created_by` | 🟢 آمن |
| 11 | `GET /automation/executions/{id}/logs` | سجلات عقد تنفيذ | ✅ active_user | لا هيدر | نفس النمط | 🟢 آمن |
| 12 | `POST /automation/secrets` | إنشاء سر (API key مشفّر) | ✅ active_user | `current_user.tenant_id` (router.py:315) | tenant حقيقي + name | 🟢 آمن — **Phase 12 لسه سليم** |
| 13 | `GET /automation/secrets` | قائمة الأسرار | ✅ active_user | `current_user.tenant_id` (router.py:330) | tenant حقيقي | 🟢 آمن — **Phase 12 لسه سليم** |
| 14 | `DELETE /automation/secrets/{name}` | حذف سر | ✅ active_user | `current_user.tenant_id` (router.py:344) | tenant حقيقي + name | 🟢 آمن — **Phase 12 لسه سليم** |

**تأكيد صريح Phase 12:** ✅ **لا يوجد أي regression** — الأسطر 315/330/344 في `router.py` الحالي لسه بتستخدم `cast(int, current_user.tenant_id)` بالحرف، صفر رجوع لاستخدام الهيدر.

### 6.1) الأخطار الحقيقية المتبقية — أضيق كثيرًا مما كان متوقَّعًا من التصنيف القديم "أسوأ من affiliate"

التصنيف القديم في `critical-finding-xtenant-systemic.md` (#7) وصف automation كـ"أسوأ من affiliate: مفيش حتى فحص superuser" — هذا كان **قبل Phase 12** ولم يُحدَّث. الوضع الحالي: **12/12 endpoint الباقيين إما آمنون فعليًا (ownership حقيقي عبر JWT) أو تلوّث بيانات فقط (لا تسريب)**. لا يوجد أي IDOR قراءة/كتابة عبر-تينانت حقيقي متبقٍ في automation — الفئة الوحيدة المتبقية هي "تلوّث بيانات عبر الإنشاء" (endpoint #1)، نفس الفئة الأخف الموجودة في معظم الدومينات الممسوحة عبر batch1-4 (مثال: `realestate.POST /lands`).

### 6.2) روابط cross-domain (من `_dispatch_node` + `AutomationService`)

```
automation._exec_ai_agent ──> ai_agents.execute_agent_action(agent_id, action_type, payload,
   executor_user_id=workflow.created_by, idempotency_key=...)
   ✅ التوقيع الحالي مطابق تمامًا لتوقيع ai_agents/service.py:147-154 الحالي (بعد إصلاح 2026-08-24) —
   **لا يوجد نفس باج realestate (§4.3 batch4) هنا** — automation بتستدعي بالتوقيع الصحيح، صفر kwarg زائد

automation._exec_ai_agent ──> ai_agents._wait_for_approval ──> AIAgentsRepository.get_approval(approval_id, workflow.tenant_id)
automation._exec_notification ──> communications.send_notification(user_id, title, body, ...)
   ⚠️ user_id هنا يجي من config العقدة (self._interpolate(config.get("user_id"))) — قابل للتلاعب من
   منشئ الـworkflow نفسه (نفس تينانته، ليس IDOR عبر-تينانت، لكن أي مستخدم بالتينانت يقدر يبعت إشعار
   باسم النظام لأي user_id تعسفي حتى لو مش بنفس تينانته — communications.send_notification لم تُفحص هنا)
automation._exec_sql / _exec_database ──> تنفيذ SQL خام (SELECT فقط لـ_exec_sql، أي نوع لـ_exec_database
   بما فيها INSERT/UPDATE/DELETE) — قوة تنفيذية خطيرة لكنها محصورة بمن يملك صلاحية إنشاء workflow في
   تينانته (owner-gated، ليست IDOR) — يستاهل سؤال منتجي/أمني منفصل: هل "أي active_user" يُفترض يقدر
   يُشغّل SQL خام عبر عقدة DATABASE؟
list_available_agents ──> ai_agents.repository.list_agents (tenant_id=هيدر + owner_id=حقيقي، آمن)
```

**لا استدعاء finance مباشر في automation نفسها** (التحويلات المالية تحصل داخل الدومينات المستهدفة عبر `CREATE_INVOICE`/`TRANSFER_FUNDS`/إلخ node types المذكورة في `_dispatch_node` — لكن **دوال `_exec_create_invoice`/`_exec_transfer_funds`/`_exec_create_entity`/إلخ (قطاعات identity/sovereign_entities/finance/commerce/academy) غير موجودة فعليًا في هذا الملف** (التعليق سطر 784: "جميع دوال _exec_* موجودة في الملف الأصلي، سأحتفظ بها جميعاً" — لكنها **غائبة فعليًا** من النسخة المقروءة؛ أي `node_type` من فئات CREATE_USER/CREATE_INVOICE/TRANSFER_FUNDS/CREATE_ENTITY/إلخ سيصطدم بـ`AttributeError` عند التنفيذ الفعلي لأن `self._exec_create_invoice` وغيرها غير مُعرَّفة — تناقض بين قائمة `_dispatch_node` (تتوقع وجودها) وجسم الكلاس الفعلي). **هذا باج وظيفي منفصل تمامًا عن IDOR** — يستاهل توثيق كـ self-DoS إضافي (أي workflow يستخدم أي node type من هذه القطاعات الأربعة سيفشل بكراش، لا خطر أمني مباشر).

### 6.3) الربط بالفرونت إند — ✅ استثناء إيجابي نادر: **صفر باج بادئة مسار مضاعفة**

`eppne-web/services/automation.service.ts` — **كل الاستدعاءات (14 نداء) تستخدم بادئة مفردة صحيحة** (`/automation/workflows`, `/automation/secrets`, `/automation/webhook/{path}`, إلخ) مطابقة تمامًا لتسجيل `main.py:272` (`/api/automation/...`). **أول دومين عبر batch4+batch5 بلا هذا الباج إطلاقًا.** الاستيراد أيضًا سليم (`export const AutomationService` ↔ `import { AutomationService }` في `app/(dashboard)/automation/workflows/page.tsx:7`) — **automation هو الدومين الأكثر ارتباطًا فعليًا بفرونت إند حقيقي من بين كل الدومينات الممسوحة حتى الآن** (بلا تأكيد `tsc`/تشغيل فعلي في المتصفح، لكن البنية الساكنة سليمة 100%، خلافًا لكل دومين آخر فُحص).

**ملاحظة أمنية مرتبطة:** `automation.service.ts` (أسطر متعددة، مثال #25-38) **يمرر `X-Tenant-ID` header صراحة من الفرونت إند نفسه كمعامل اختياري** (`headers?: { 'X-Tenant-ID'?: number }`) — يعني تلوّث البيانات الموصوف في §6 (endpoint #1) **ليس نظريًا فقط، الفرونت إند مصمَّم لإرسال هذا الهيدر فعليًا**. يستاهل تحقق من أي مكوّن فعليًا بيمرر قيمة مختلفة عن تينانت المستخدم الحقيقي لهذا المعامل (بحث سريع لم يُنفَّذ ضمن هذه الجلسة — خارج الوقت المتاح).

### 6.4) أنماط منتشرة جديدة

| # | النمط | الموقع | ملاحظة |
|---|---|---|---|
| 1 | **الدومين الأول بلا باج بادئة مسار مضاعفة** | `automation.service.ts` | استثناء إيجابي — يستاهل مقارنة بنيوية: ما الفرق البنيوي بين هذا الملف والملفات المعطوبة؟ (احتمال: كُتب/رُوجع يدويًا لاحقًا) |
| 2 | **تعليق كود يدّعي وجود دوال غير موجودة فعليًا** (`_exec_create_invoice` وغيرها) | `service.py:784` + `_dispatch_node` (سطور 315-363) | نمط جديد: "قائمة توجيه (`dispatch`) تتوقع معالجات غير مكتملة" — self-DoS لأي node type من 4 قطاعات كاملة |
| 3 | webhook بلا تحقق توقيع/HMAC (أمان بالسرية فقط) | `webhook_trigger` | يستاهل مراجعة أمنية عامة (خارج نطاق IDOR) — نمط قد يتكرر في دومينات webhook أخرى (`commerce.handle_visa_webhook` مذكور في الملف المرجعي بفئة مختلفة) |

### 6.5) تحقق حي مرشَّح لـ automation

1. 🟠 **أولوية متوسطة:** `create_workflow` — تسجيل دخول تينانت1، إرسال `X-Tenant-ID: 16` مزوَّر + `POST /automation/workflows` بمحتوى `_TAINT_TEST` → `SELECT` مستقل على `automation_workflows` للتأكد إن الصف اتكتب فعلًا بـ`tenant_id=16` رغم إن `created_by` هو المستخدم الحقيقي من تينانت1 (يثبت "تلوّث بيانات" حي، ليس نظريًا).
2. 🟢 **منخفضة:** لا حاجة تحقق حي لـ #3-#6/#9-#11 (ownership حقيقي عبر JWT، نفس نمط `finance.balances` المؤكَّد آمن سابقًا في الملف المرجعي — درجة ثقة عالية من القراءة وحدها).
3. 🟢 **منخفضة، اختياري:** إثبات باج `_exec_create_invoice` المفقودة — إنشاء workflow بعقدة `CREATE_INVOICE` وتشغيله، توقع `AttributeError` (كراش داخلي، يُلتقط بـ`except Exception` في `_execute_node` فيُسجَّل كـ`FAILED` في `automation_executions.error_message` — تحقق نصي فقط).

---

## 7) التحقق الحي — التفاصيل الكاملة

**السيرفر:** `uvicorn` محلي (`E:\cc\eppne-backend`, venv, منفذ 8000)، شُغِّل هذه الجلسة، **أُوقف في نهاية الجلسة** (`Stop-Process`، مؤكَّد بـ`Get-NetTCPConnection` صفر `LISTENING`).

**المستخدمون:** نفس حسابات throwaway الموثَّقة (`throwaway-test-users.md`) — `TEST_super_a` (id=772، تينانت1) و`TEST_instr_b` (id=774، تينانت16)، كلمة سر `TEST_pass_batch3_2026`، سجّلا دخول بنجاح بلا أي تغيير مطلوب.

**بوابة SaaS لـ zamakana — اكتشاف جانبي أثناء التحضير:** `zamakana._check_saas_limits` يستخدم `SaaSControlService.can_access_service("zamakana")` — آلية **مختلفة تمامًا** عن آلية "أحدث اشتراك نشط بغض النظر عن الخدمة" (features JSON) المستخدَمة في realestate/insurance/logistics/manufacturing (batch3/4). هذه الآلية تتطلب: (أ) صف في `saas_service_catalog` بـ`code='zamakana'`، (ب) صف `saas_tenant_service_access` نشط، (ج) اشتراك نشط لنفس `service_id` تحديدًا. **فحص مباشر أثبت: `saas_service_catalog` لا يحتوي أي صف بـ`code='zamakana'` إطلاقًا** — يعني **دومين zamakana بالكامل مقفول عن كل التينانتات في المنصة حاليًا بواسطة بوابة SaaS نفسها** (self-DoS مستقل تمامًا عن IDOR، لم يكن موثَّقًا في تصنيف الفورك — **اكتشاف إضافي**). لإجراء التحقق الحي، أُنشئت صفوف throwaway (`saas_service_catalog.id=72`, `saas_service_plans.id=74`, `saas_tenant_service_access.id=20`, `saas_tenant_subscriptions.id=85`) لمنح تينانت16 فقط وصولًا مؤقتًا — **كلها محذوفة بالكامل بعد الاختبار (§7.3)**.

### 7.1 🔴🔴🔴🔴 `zamakana` — IDOR قراءة بلا أي مصادقة — مؤكَّد حيًا على كل الـ8 مسارات

```
B (تينانت16، توكن حقيقي) → POST /zamakana/nodes {"TEST_ZAMAKANA_NODE_SECRET_B"} → 201, id=47, tenant_id=16
B → POST /zamakana/campaigns {"TEST_ZAMAKANA_CAMPAIGN_SECRET_B"} → 201, id=3, tenant_id=16
B → POST /zamakana/scenarios {"TEST_ZAMAKANA_SCENARIO_SECRET_B"} → 201, id=1, tenant_id=16

زائر مجهول تمامًا (صفر Authorization header) + X-Tenant-ID: 16 (مزوَّر، بلا أي توكن):
  GET /zamakana/nodes              → 200 [{"title":"TEST_ZAMAKANA_NODE_SECRET_B", ...}]
  GET /zamakana/nodes/47           → 200 {"title":"TEST_ZAMAKANA_NODE_SECRET_B", ...}
  GET /zamakana/graph              → 200 {"nodes":[{"id":47,"title":"TEST_ZAMAKANA_NODE_SECRET_B",...}],"edges":[]}
  GET /zamakana/campaigns          → 200 [{"title":"TEST_ZAMAKANA_CAMPAIGN_SECRET_B", ...}]
  GET /zamakana/campaigns/3        → 200 {"title":"TEST_ZAMAKANA_CAMPAIGN_SECRET_B", ...}
  GET /zamakana/campaigns/3/pledges→ 200 []
  GET /zamakana/scenarios          → 200 [{"scenario_title":"TEST_ZAMAKANA_SCENARIO_SECRET_B", ...}]
  GET /zamakana/scenarios/1        → 200 {"scenario_title":"TEST_ZAMAKANA_SCENARIO_SECRET_B", ...}

زائر مجهول بلا Authorization وبلا X-Tenant-ID إطلاقًا (الافتراضي=1):
  GET /zamakana/nodes → 403 (تينانت1 ماعندوش وصول SaaS لـzamakana — يثبت إن البوابة شغالة صح لكل تينانت
  على حدة، والمشكلة محصورة فعليًا في "أي زائر بلا هوية يقرأ بيانات **أي تينانت مصرَّح له بالميزة**")

مسار شرعي: B (توكنها الحقيقي) → GET /zamakana/nodes/47 → 200 (نفس البيانات، طبيعي)

SELECT مستقل (3 استعلامات منفصلة):
  zamakana_nodes WHERE id=47 → tenant_id=16, created_by=774
  planetary_campaigns WHERE id=3 → tenant_id=16, created_by=774
  future_scenarios WHERE id=1 → tenant_id=16, created_by=774
```
**الحكم:** مؤكَّد حيًا 100% — الفئة الأخطر في هذه الدفعة، مطابقة لأعلى فئة خطورة موثَّقة عبر batch1-4 (`ai_governance.check_and_consume`, `realestate.get_development`).

### 7.2 🟠 `automation.create_workflow` — تلوّث بيانات عبر-تينانت — مؤكَّد حيًا

```
A (تينانت1، توكن حقيقي) + X-Tenant-ID: 16 (مزوَّر) → POST /automation/workflows {"name":"TEST_AUTOMATION_TAINT_A", ...}
→ 201 {"id":2, "tenant_id":16, "created_by":772, "name":"TEST_AUTOMATION_TAINT_A", ...}

SELECT مستقل: automation_workflows WHERE id=2 → tenant_id=16, created_by=772
```
**الحكم:** مؤكَّد حيًا — سير عمل حقيقي مستخدم تينانت1 (`created_by=772`) اتكتب فعليًا تحت `tenant_id=16` بمجرد تزوير الهيدر. **مش تسريب** (لا قراءة/تعديل لمورد تينانت16 الحقيقي — `list_workflows`/`get_workflow` محميان بفحص `created_by==user_id` حقيقي، مؤكَّد من القراءة الكودية §6) — **تلوّث بيانات فقط**، نفس فئة `realestate.POST /lands` في batch4.

### 7.3 تنظيف بيانات throwaway — مكتمل ومؤكَّد مستقل

جميع الصفوف المُنشأة هذه الجلسة محذوفة بالكامل ومؤكَّدة بـ`SELECT count(*)`:
`zamakana_nodes.id=47`, `planetary_campaigns.id=3`, `future_scenarios.id=1`, `automation_workflows.id=2`, `saas_tenant_subscriptions.id=85`, `saas_tenant_service_access.id=20`, `saas_service_plans.id=74`, `saas_service_catalog.id=72` — **صفر residue** من هذه الجلسة. `saas_service_plans.id=48.features` أُعيد لـ`[]` (الأصل، بعد تعديل مؤقت أولي لم يُستخدَم). لم يُلمَس أي شيء من بيانات الجلسات السابقة. **صفر تعديل كود، صفر migration.** السيرفر التجريبي أُوقف (`Stop-Process`، مؤكَّد `Get-NetTCPConnection` صفر LISTENING).

---

## 8) خريطة الترابط الكاملة

```
identity ──(current_user)──> iot, translation, zamakana, admin, privacy, automation (كل الـendpoints)

saas.can_access_service("zamakana") [آلية مختلفة عن batch3/4 — service_id-specific، ليست features-JSON]
   <── zamakana (كل العمليات تقريبًا) — 🔴 دومين مقفول بالكامل حاليًا (صفر صف zamakana في service_catalog)

finance.transfer <── iot.settle_carbon_credits (عبر get_or_create_system_account — 🟢 مُصلَح)
   [translation: _debit_wallet معطَّلة، صفر أثر مالي]
   [zamakana, admin, privacy, automation: لا استدعاء finance مباشر]

invoicing.create_invoice <── zamakana.pledge_time (>10h)، zamakana.generate_ai_analysis (10 MRUSDT)
   (tenant_id من الهيدر الملوَّث — فاتورة قد تُنشأ تحت تينانت مزوَّر)

affiliate.register_commission <── zamakana (node/campaign/pledge fulfillment)

ai_agents.execute_agent_action <── zamakana.generate_ai_analysis، automation._exec_ai_agent
   automation: ✅ توقيع الاستدعاء مطابق للتوقيع الحالي (بعد إصلاح 2026-08-24) — لا regression
   zamakana: لم يُفحص توقيع الاستدعاء بعمق (خارج أولوية هذه الجلسة)
ai_governance.check_and_consume <── zamakana.generate_ai_analysis

communications.send_notification <── automation._exec_notification (user_id من config العقدة،
   قابل للتلاعب من منشئ الـworkflow لأي user_id تعسفي — صلاحية داخل-تينانت واسعة، ليست IDOR عبر-تينانت)

privacy._erase_module_data ──(SQL خام مباشر، بلا service layer)──> identity, academy, finance,
   commerce, health, iot, realestate (7 دومينات) — خطر بنيوي منفصل عن IDOR

sovereign_entities / identity / finance / commerce / academy (عبر automation node types
   CREATE_USER/CREATE_INVOICE/TRANSFER_FUNDS/CREATE_ENTITY/إلخ) ──> 🔴 معالجات هذه العقد
   (_exec_create_invoice وغيرها) غير موجودة فعليًا في service.py رغم إدراجها في _dispatch_node —
   self-DoS لأي workflow يستخدمها (باج منفصل تمامًا، §6.2)

admin ──> (معزول تمامًا — endpoint واحد غير مسجَّل في main.py، لا يستدعي ولا يُستدعى من أي دومين)
iot ──> (لا أحد يستدعيه؛ لا بوابة SaaS، أول دومين ممسوح عبر batch4+5 بهذا الاستقلال المالي الكامل)
```

**ملاحظة ترابط بارزة:** هذه الدفعة (خلافًا لـbatch4) فيها **3 من 6 دومينات بلا أي بوابة SaaS إطلاقًا** (iot, admin, privacy) — مقارنة بـrealestate/insurance اللي كانت كل عملياتها الحساسة تمر ببوابة SaaS. `automation` هو الدومين الوحيد في هذه الدفعة (وأحد قلائل عبر batch1-5) **المربوط فعليًا وبشكل سليم بفرونت إند حقيقي** (§6.3) — عكس نمط "كل شيء 404" السائد.

---

## 9) الفجوات المكتشفة — التصنيف النهائي (بانتظار توجيهك، صفر تنفيذ)

### 9.1 بنود IDOR/أمان حرجة (تحتاج قرار إصلاح)

| # | الدومين | البند | الخطورة | مؤكَّد حيًا؟ |
|---|---|---|---|---|
| 1 | zamakana | `list_nodes`/`get_node`/`get_knowledge_graph`/`list_campaigns`/`get_campaign`/`get_campaign_pledges`/`list_scenarios`/`get_scenario` — **بلا `current_user` إطلاقًا، هيدر فقط** | 🔴🔴🔴🔴 **الأعلى في هذه الدفعة** — تسريب قراءة كامل بلا أي هوية | ✅ §7.1 (كل الـ8 مسارات) |
| 2 | zamakana | `create_node`/`create_edge`/`create_campaign`/`create_scenario`/`pledge_time` — تلوّث بيانات + فوترة عبر-تينانت (هيدر) | 🔴🔴🔴 | ❌ كودًا فقط (غير مختبَر حيًا هذه الجلسة، عدا تأثيره غير المباشر) |
| 3 | zamakana | `add_scenario_feedback` — IDOR كتابة (صفر ownership check، هيدر) | 🔴 | ❌ كودًا فقط |
| 4 | privacy | `is_privacy_officer(admin_id: int)` type mismatch — self-DoS كامل لقسم إدارة طلبات محو GDPR | 🔴🔴 (وظيفي/امتثال، لا تسريب) | ❌ كودًا فقط (سهل التحقق، لم يُنفَّذ) |
| 5 | privacy | `get_erasure_request` يتجاهل `request_id` تمامًا | 🔴 (كامن خلف #4) | ❌ كودًا فقط |
| 6 | automation | `create_workflow` — تلوّث بيانات عبر-تينانت (هيدر) | 🟠 | ✅ §7.2 |
| 7 | automation | `webhook_trigger` — صفر تحقق HMAC/توقيع payload (أمان بسرية الرابط فقط) | 🟠 (تصميمي عام، ليس IDOR) | ❌ لم يُختبَر (يحتاج معرفة رابط حقيقي) |

### 9.2 بنود منفصلة عن IDOR (باجات وظيفية/self-DoS/توثيقية)

| # | الدومين | البند | ملاحظة |
|---|---|---|---|
| 1 | iot | تصحيح مطلوب في `critical-finding-xtenant-systemic.md` — `sender_id=1` هاردكودد **مُصلَح فعليًا** (commit `0e6a4aa`) | توثيق فقط؛ يستاهل تحقق مماثل لـ`commerce`/`affiliate` |
| 2 | translation | `TranslationCache.text_hash` unique عالميًا يتعارض مع فلترة tenant — DoS محتمل لنصوص شائعة بين تينانتين | غير مختبَر حيًا |
| 3 | automation | معالجات node types (`_exec_create_invoice` وغيرها، 4 قطاعات) مُدرَجة في `_dispatch_node` لكن **غير موجودة فعليًا** في الكلاس | self-DoS، صفر خطر أمني مباشر |
| 4 | zamakana | بوابة SaaS (`saas_service_catalog`) **لا تحتوي صف `code='zamakana'` إطلاقًا** — الدومين مقفول عن كل التينانتات حاليًا | اكتُشف أثناء تحضير التحقق الحي (§7)؛ self-DoS مستقل عن IDOR |
| 5 | admin | endpoint وحيد غير مسجَّل في `main.py` — غير قابل للوصول | مطابق تمامًا لـ Phase 14، لا تغيير |
| 6 | عابر للدفعات | بادئة مسار مضاعفة في `services/*.ts` | مؤكَّدة إضافيًا في `iot`, `translation`, `zamakana`, `privacy` (4 ملفات جديدة تنضم لقائمة batch4) — **`automation` استثناء نظيف** |
| 7 | عابر للدفعات | "Service layer صحيح، استيراد مكسور" (export/import mismatch) | **الموضع الثاني** (`iot`، بعد `realestate` في batch4) |
| 8 | عابر للدفعات | تمرير `int` (ID) لدالة صلاحيات تتوقع `User` كامل | **نمط جديد تمامًا** (`privacy.is_privacy_officer`) — يستاهل grep شامل عبر كل الدومينات لنفس الخطأ |

**بانتظار توجيهك:** أولوية الإصلاح المقترحة من شدة الأثر: (1) `zamakana` GET endpoints (§9.1 بند 1 — تسريب بلا هوية)، (2) `zamakana` create endpoints (بند 2-3)، (3) `privacy.is_privacy_officer` (بند 4-5 — امتثال GDPR معطَّل)، (4) `automation.create_workflow` (بند 6 — تلوّث بيانات فقط، أخف الأربعة).

---

## 10) تنفيذ الإصلاحات المعتمَدة [2026-08-26] — مكتمل، مؤكَّد حيًا بالكامل، بانتظار موافقة الـ`commit`

**قرار المستخدم:** موافقة كاملة على §9.1 (التصنيف والترتيب). تنفيذ 4 بنود بالترتيب: (1) `zamakana` الـ8 GET endpoints، (2) `zamakana` create endpoints (`create_node`/`create_edge`/`create_campaign`/`create_scenario`/`pledge_time`) + ownership check من الصفر على `add_scenario_feedback`، (3) `privacy.is_privacy_officer` type mismatch، (4) `automation.create_workflow`. باقي بنود §9.1 (5: `privacy.get_erasure_request` يتجاهل `request_id`، 7: `automation.webhook_trigger`) **لم يُطلَب تنفيذها صراحة في التوجيه المعتمَد — لم تُنفَّذ، لسه بانتظار توجيه** (راجع تحذير §10.4). كل بنود §9.2 (توثيق فقط) اتوثّقت في الملفات المرجعية المناسبة (§10.6)، صفر إصلاح كود لها.

### 10.1) نطاق التعديل الكودي — نفس النمط الميكانيكي المعتاد (`get_current_tenant`/هيدر → `current_user.tenant_id`)

| # | الملف | التغيير |
|---|---|---|
| 1 | `zamakana/router.py` | 8 GET endpoints (`list_nodes`, `get_node`, `get_knowledge_graph`, `list_campaigns`, `get_campaign`, `get_campaign_pledges`, `list_scenarios`, `get_scenario`): حذف `tenant: AcademyTenant = Depends(get_current_tenant)`، إضافة `current_user: User = Depends(get_current_active_user)` (لم يكن موجودًا إطلاقًا)، استبدال `cast(int, tenant.id)` بـ`cast(int, current_user.tenant_id)` |
| 2 | `zamakana/router.py` | 5 create endpoints (`create_node`, `create_edge`, `create_campaign`, `create_scenario`, `pledge_time`): حذف اعتماد الهيدر، `cast(int, current_user.tenant_id)` بدل `cast(int, tenant.id)` |
| 2 | `zamakana/router.py` | `add_feedback` (`/scenarios/{id}/feedback`): نفس الاستبدال — قبل الإصلاح كان الفحص الوحيد (`get_scenario` داخل `add_human_feedback`) يقارن ضد نفس الهيدر المزوَّر (فحص ذاتي المرجعية، بلا معنى أمني)؛ بعد الإصلاح الفحص يقارن ضد `current_user.tenant_id` الحقيقي — هذا **هو** "ownership check من الصفر" (لم يكن هناك فحص فعّال قبله رغم وجود سطر `get_scenario` ظاهريًا) |
| 3 | `privacy/service.py` | `process_erasure_request`: توقيع `admin_id: int` → `admin_user: User`، `is_privacy_officer(admin_id)` → `is_privacy_officer(admin_user)` + `from app.domains.identity.models import User` |
| 3 | `privacy/router.py` | موضعان: `process_erasure_request` (تمرير `current_user` كامل بدل `admin_id`)، `get_pending_erasure_requests` (`is_privacy_officer(admin_id)` → `is_privacy_officer(current_user)`، حذف متغير `admin_id` الميت) |
| 4 | `automation/router.py` | `create_workflow`: حذف `tenant: AcademyTenant = Depends(get_current_tenant)`، `cast(int, current_user.tenant_id)` بدل `cast(int, tenant.id)` |

**لم يُلمَس:** `zamakana.update_node`/`delete_node`/`fulfill_pledge`/`analyze_scenario`/`confirm_scenario` (عندهم فحص ملكية حقيقي بالفعل عبر `created_by`/`user_id` من JWT — 🟠 "محمي عمليًا"، غير مدرَجين في التوجيه المعتمَد)، `zamakana.list_workflows`-المكافئ `automation.list_workflows` (🟠 محمي عمليًا بفلتر Python إضافي)، أي دومين/ملف آخر.

**تحقق قبل التشغيل:** `python -m py_compile` نجح لكل الملفات الأربعة المعدَّلة.

### 10.2) التحقق الحي — بيئة الاختبار

**السيرفر:** `uvicorn` محلي (`E:\cc\eppne-backend`, venv، منفذ 8000)، شُغِّل هذه الجلسة، **أُوقف في نهاية الجلسة** (مؤكَّد: `curl` رجّع فشل اتصال بعد الإيقاف). **DB:** `eppne_db` (docker، منفذ 5435، مطابق لـ`DATABASE_URL`).

**المستخدمون:** نفس حسابات throwaway الموثَّقة (`throwaway-test-users.md`) — `TEST_super_a` (id=772، تينانت1) و`TEST_instr_b` (id=774، تينانت16)، كلمة سر `TEST_pass_batch3_2026`، سجّلا دخول بنجاح بلا أي تغيير مطلوب.

**بوابة SaaS لـ`zamakana`:** لسه مفقودة بالكامل (راجع §9.2 بند 4 + backlog #28 المُوسَّع). لإجراء التحقق الحي، أُنشئت صفوف throwaway (`saas_service_catalog.id=73`, `saas_service_plans.id=75`, `saas_tenant_service_access` لتينانت1 وتينانت16، `saas_tenant_subscriptions.id=86,87`) لمنح **كلا التينانتين** وصولًا مؤقتًا (لازم لاختبار كل من الهجوم المرفوض والمسار الشرعي) — **كلها محذوفة بالكامل بعد الاختبار (§10.3)**.

### 10.3 `zamakana` — الـ8 GET endpoints — مؤكَّد حيًا: الهجوم مرفوض بالكامل

```
B (تينانت16، توكن حقيقي) → POST /zamakana/nodes {"TEST_ZAM_FIX_NODE_SECRET_B"} → 201, id=48, tenant_id=16
B → POST /zamakana/campaigns {"TEST_ZAM_FIX_CAMPAIGN_SECRET_B"} → 201, id=4, tenant_id=16
B → POST /zamakana/scenarios {"TEST_ZAM_FIX_SCENARIO_SECRET_B"} → 201, id=2, tenant_id=16

هجوم 1 — زائر مجهول تمامًا (صفر Authorization) + X-Tenant-ID:16 مزوَّر، كل الـ8 مسارات:
  nodes, nodes/48, graph, campaigns, campaigns/4, campaigns/4/pledges, scenarios, scenarios/2
  → 401 "Not authenticated" (كلهم — كانوا 200 مع تسريب كامل قبل الإصلاح)

هجوم 2 — A (تينانت1، توكن حقيقي) + X-Tenant-ID:16 مزوَّر:
  GET /nodes/48 → 404، GET /campaigns/4 → 404، GET /scenarios/2 → 404 (كانوا 200 قبل الإصلاح)
  GET /nodes (list) → [] لا يحتوي عقدة B
  GET /campaigns (list) → يحتوي فقط بيانات تينانت1 القديمة (لا شيء من B)
  GET /scenarios (list) → [] لا يحتوي سيناريو B

مسار شرعي — B (توكنها الحقيقي):
  GET /nodes/48 → 200 (بياناتها)، GET /campaigns/4 → 200، GET /scenarios/2 → 200

SELECT مستقل: zamakana_nodes id=48 → tenant_id=16, created_by=774 (بلا تغيير)
              planetary_campaigns id=4 → tenant_id=16, created_by=774
              future_scenarios id=2 → tenant_id=16, created_by=774
```

### 10.4 `zamakana` — create endpoints + `add_scenario_feedback` — مؤكَّد حيًا: تلوّث البيانات + IDOR كتابة مقفولان

```
تلوّث بيانات (create_node) — A + X-Tenant-ID:16 مزوَّر → POST /nodes {"TEST_ZAM_FIX_TAINT_CHECK_A"}
  → 201, id=49. SELECT مستقل: tenant_id=1, created_by=772 (تينانت A الحقيقي، لا 16 المزوَّر) ✅

نفس التأكيد لـ create_campaign (id=5)، create_scenario (id=3)، create_edge (id=1، بعد إنشاء node id=50
  للاختبار)، pledge_time (id=4، على campaign تخص تينانت1 نفسه) — كل الأربعة: tenant_id=1 رغم الهيدر=16 ✅

هجوم عبر-تينانت على pledge_time — A + X-Tenant-ID:16 → POST /pledges {"campaign_id":4} (campaign B)
  → 404 "Campaign not active or not found" ✅ مرفوض (lookup بقى بتينانت A الحقيقي=1، مش B)

هجوم على add_scenario_feedback — A + X-Tenant-ID:16 → POST /scenarios/2/feedback (سيناريو B)
  → 404 "Scenario not found" ✅ مرفوض

مسار شرعي — B (توكنها) → POST /scenarios/2/feedback {"scenario_id":2,"feedback_text":"legit feedback"}
  → 200 {"id":1,"reviewer_id":774,...}
  SELECT مستقل: human_feedbacks id=1 → tenant_id=16, scenario_id=2, reviewer_id=774 ✅
```

**⚠️ ملاحظة مهمة — بند §9.1 رقم 7 (`automation.webhook_trigger`) لم يُختبَر ولم يُصلَح** (يحتاج معرفة رابط webhook حقيقي، خارج التوجيه المعتمَد لهذه الجلسة) — **لسه مفتوح**، موثَّق هنا للتذكير فقط.

### 10.5 `privacy.is_privacy_officer` — مؤكَّد حيًا: self-DoS مرفوع بالكامل

```
BEFORE (موثَّق كوديًا §5.1، لم يُعَد اختباره حيًا قبل الإصلاح لتفادي كسر الكود مرتين): كان GET /admin/erasure/pending
  يرجّع 403 لأي مستخدم بلا استثناء، حتى SUPER_ADMIN حقيقي.

AFTER:
A (SUPER_ADMIN حقيقي) → GET /admin/erasure/pending → 200 {"data":[],"total":0,...} ✅ (بدل 403 دائم)

دورة كاملة: A → POST /erasure/request {"target_module":"identity"} → 201, id=2, status=PENDING
A → POST /admin/erasure/2/process?approved=false&comment=batch5_test_reject → 200 {"status":"REJECTED",...} ✅

SELECT مستقل: data_erasure_requests id=2 → status=REJECTED, admin_notes='batch5_test_reject' ✅
```

**ملاحظة نطاق:** الاختبار استخدم `approved=false` (رفض) عمدًا لتفادي تفعيل باج `get_erasure_request` (يتجاهل `request_id`، §5.2/§9.1 بند 5 — **لم يُصلَح**، لأنه لم يكن ضمن التوجيه المعتمَد) و`_erase_module_data` (أسماء جداول خاطئة لـhealth/iot/realestate، §5.2b — توثيق فقط بالتصميم). دور `is_privacy_officer` الصحيح (`SUPER_ADMIN`/`PRIVACY_OFFICER`/`EXECUTIVE_DIRECTOR` فقط، `core/security.py:194`) لم يتغيَّر — الإصلاح لم يفتح الوصول لمستخدم عادي.

### 10.6 `automation.create_workflow` — مؤكَّد حيًا: تلوّث البيانات مقفول

```
A + X-Tenant-ID:16 مزوَّر → POST /automation/workflows {"name":"TEST_AUTOMATION_FIX_TAINT_CHECK",
  "trigger_type":"MANUAL","trigger_config":{}} → 201, id=3, tenant_id=1 (تينانت A الحقيقي، لا 16) ✅

SELECT مستقل: automation_workflows id=3 → tenant_id=1, created_by=772 ✅
```

### 10.7 تنظيف بيانات throwaway — مكتمل ومؤكَّد مستقل (`SELECT count` = صفر لكل جدول)

`zamakana_nodes` (id=48,49,50)، `planetary_campaigns` (id=4,5)، `future_scenarios` (id=2,3)، `zamakana_edges` (id=1)، `time_pledges` (id=4)، `human_feedbacks` (id=1)، `data_erasure_requests` (id=2)، `automation_workflows` (id=3)، `saas_tenant_subscriptions` (id=86,87)، `saas_tenant_service_access` (2 صف، `service_id=73`)، `saas_service_plans` (id=75)، `saas_service_catalog` (id=73) — **كلها صفر residue، مؤكَّد باستعلام `UNION ALL` واحد يغطي كل الجداول**. لم يُلمَس أي شيء من بيانات الجلسات السابقة. السيرفر التجريبي أُوقف ومؤكَّد توقفه (`curl` فشل اتصال).

### 10.8 توثيق البنود المرجعية (§9.2 + الإضافات) — مكتمل، صفر إصلاح كود

| البند | أين وُثِّق |
|---|---|
| `privacy._erase_module_data` (أسماء جداول خاطئة لـ health/iot/realestate) | موثَّق بالفعل في هذا التقرير §5.2b — لا حاجة لملف إضافي، بانتظار فحص تصميمي منفصل بعد إصلاح `is_privacy_officer` (تم) |
| `automation` معالجات node types المفقودة (`_exec_create_invoice` إلخ) | موثَّق بالفعل في هذا التقرير §6.2 |
| `zamakana` بوابة SaaS مفقودة بالكامل | أُضيف لبند `#28 saas-service-catalog-missing-entries` في `constructor-mismatch-backlog-classification.md` (وُسِّع من 2 لـ3 دومينات: `service_marketplace`, `tenders_auctions`, `zamakana`) |
| `iot.settle_carbon_credits` — تأكيد إصلاح `sender_id=1` (commit `0e6a4aa`) | سطر تصحيح ✅ مضاف في `.claude/plans/critical-finding-xtenant-systemic.md` (بعد جدول hardcoded system account) — مع تنبيه إن `commerce`/`affiliate` (نفس الجدول) **لم يُتحقَّق منهما بعد** رغم احتمال شمولهما بنفس الـcommit |
| نمط export/import mismatch (`IoTService`/`iotService`) | بند جديد `#43 frontend-service-export-import-name-mismatch` في `constructor-mismatch-backlog-classification.md` |
| نمط تمرير `int` بدل `User` لدالة صلاحيات | بند جديد `#44 permission-check-passed-id-instead-of-user-object` — مُعلَّم ✅ مُصلَح (هو نفس بند §9.1 رقم 3 المنفَّذ هنا) |
| نمط uniqueness عالمي يتعارض مع tenant scoping (`translation.text_hash`) | بند جديد `#45 global-unique-column-conflicts-with-tenant-scoped-query` في `constructor-mismatch-backlog-classification.md` |

### 10.9 `git status` / `git diff --stat` — بانتظار موافقتك على الـ`commit`

```
$ git status --short (الملفات المتعلقة بهذه الجلسة فقط)
 M .claude/plans/critical-finding-xtenant-systemic.md
 M .claude/reports/constructor-mismatch-backlog-classification.md
 M eppne-backend/app/domains/automation/router.py
 M eppne-backend/app/domains/privacy/router.py
 M eppne-backend/app/domains/privacy/service.py
 M eppne-backend/app/domains/zamakana/router.py
?? .claude/reports/batch5-audit-security-iot-translation-zamakana-admin-privacy-automation.md

$ git diff --stat -- eppne-backend/app/domains/{automation,privacy,zamakana}/*.py
 eppne-backend/app/domains/automation/router.py |  3 +-
 eppne-backend/app/domains/privacy/router.py    |  6 ++--
 eppne-backend/app/domains/privacy/service.py   |  5 +--
 eppne-backend/app/domains/zamakana/router.py   | 50 ++++++++++++--------------
 4 files changed, 28 insertions(+), 36 deletions(-)
```

**لم يُنفَّذ `commit` بعد — بانتظار موافقتك الصريحة.** بنود مفتوحة لم تُنفَّذ (بحاجة توجيه لاحق): `privacy.get_erasure_request` (§9.1 بند 5)، `automation.webhook_trigger` (§9.1 بند 7)، تحقق `commerce`/`affiliate` لنفس إصلاح `sender_id` الخاص بـ`iot`.

---

