# جلسة جرد + أمان مدمجة — الدفعة 4: realestate, insurance, health

**بدأ التسجيل:** 2026-08-25 · **اكتمل التحقق الحي:** 2026-08-26
**الحالة:** ✅ **جرد + فحص أمني كامل (3 دومينات) + تحقق حي للنتائج الأخطر مكتمل.** بانتظار توجيهك للتصنيف/الأولوية — **صفر تنفيذ إصلاح تم في هذه الجلسة**.

**المنهجية:** نفس منهجية `batch1`/`batch2`/`batch3` بالضبط — قراءة كود كاملة (3 فوركات متوازية، دومين لكل واحد) ثم تحقق حي مباشر (سيرفر `uvicorn` محلي + DB مباشر) بمعرفة المنسق الرئيسي لأعلى النتائج خطورة. **ملاحظة عملية:** فوركين (`realestate`, `insurance`) فشلا أول مرة بسبب حد استخدام الجلسة (`session limit`)، أُعيد تشغيلهما بنجاح بعد انتهاء نافذة إعادة التعيين.

**المرجع الميكانيكي:** `.claude/plans/critical-finding-xtenant-systemic.md` (تصنيف `realestate` #14 "الأسوأ في القائمة كلها"، `insurance` #12)، `.claude/reports/technical-pattern-sweep-session-log.md:340` (باج `payment_tx_hash`)، `.claude/reports/batch3-audit-security-transport-logistics-manufacturing-tourism-sports.md` (أحدث منهجية).

---

## 0) ملخص تنفيذي فوري

| الدومين | عدد endpoints | النمط الأمني | الأخطر | مربوط بفرونت إند فعليًا؟ |
|---|---|---|---|---|
| **realestate** | 13 | 🔴🔴🔴🔴🔴 **الأسوأ في السلسلة كلها (batch1-4) — `revalue_land`/`buy_fraction`/`rent_unit` بصفر فحص تينانت من الأساس، حتى بالهيدر** | `revalue_land` (تغيير قيمة مالية لأي أرض بمعرفة الـID فقط) | ❌ **لا — 0/13، عطبان بطريقتين مستقلتين (§3)** |
| **insurance** | 14 | 🔴🔴🔴🔴 نمط IDOR قياسي (هيدر) + `disburse_pensions` بصفر فحص تينانت بالتصميم | `review_claim` (فحصان معطوبان: أساسي ملوَّث + ثانوي بمقارنة ID عبر مساحتين مختلفتين) | ⚠️ **مطابق بالاسم لكل الـ14 endpoint، لكن 0/14 يعمل حيًا فعليًا (بادئة مسار مضاعفة، §3)** |
| **health** | 13 | 🔴🔴🔴🔴 IDOR حي وفعّال على قراءة المنشآت + ثغرة تصميم حساسة طبيًا (`create_prescription`، معطّلة حاليًا) | `create_prescription` (تلفيق سجل دوائي لمريض حقيقي، معطّلة الآن) / `list_facilities`+`get_facility` (IDOR حي مؤكَّد) | ⚠️ **13/13 موجودة بالاسم، لكن 0/13 يعمل حيًا فعليًا (نفس باج البادئة المضاعفة، §3)** |

**🔴🔴🔴🔴🔴 اكتشاف جانبي حرج وعابر للدفعات — أعلى أولوية في هذا التقرير:** أثناء التحقق من "الربط بالفرونت إند" لتفتيت تعارض بين فوركي `health`/`insurance`، اكتُشف ووُثِّق حيًا (§3) أن **كل استدعاء فرونت إند حقيقي عبر `apiClient` (axios، `baseURL="http://.../api"`) لأي دومين من الثلاثة عشر+ الممسوحة يرجّع `404` مضمون** — الملفات في `eppne-web/services/*.ts` مكتوبة ببادئة مسار مضاعفة (`/insurance/insurance/...`) بينما الباك إند مسجَّل ببادئة واحدة فقط (`/api/insurance/...`). **هذا يقلب جزئيًا استنتاج "مربوط بفرونت إند" في batch1/2/3 لأي دومين استُخدِم فيه نفس نمط الخدمة** — تلك الجلسات تحققت من الباك إند مباشرة (curl/requests بالمسار الصحيح)، لا عبر الفرونت إند الفعلي، فمشكلة البادئة المضاعفة لم تكن لتظهر لهم. **يستاهل جلسة تصنيف مركزية عاجلة خاصة به، منفصلة عن IDOR بالكامل.**

---

## 1) جدول `realestate` — 13 endpoint

**النطاق:** `router.py`(213 سطر)، `service.py`(638 سطر)، `repository.py`(200 سطر)، `models.py`(277 سطر)، `schemas.py`(188 سطر) — قراءة كاملة + تحقق حي.

**تأكيد مصدر `tenant_id`:** `core/security.py:277-282` — `get_current_tenant` يرجّع القيمة من هيدر `X-Tenant-ID` **حصريًا** (افتراضي=1)، **صفر فرع يعتمد على `current_user`** حتى للمسارات المُصادَق عليها. الدالة الآمنة الجاهزة `require_tenant_access` (`security.py:285-293`) موجودة وغير مُستخدَمة في ولا endpoint من الـ13.

| # | Endpoint | الوظيفة الفعلية | `current_user`؟ | مصدر `tenant_id` | فلتر repository | تصنيف | تحقق حي |
|---|---|---|---|---|---|---|---|
| 1 | `POST /lands` | إنشاء أرض سيادية | ✅ active_user | **هيدر** | يُكتب مباشرة، `owner_id` حقيقي | 🔴 تلوّث بيانات | — |
| 2 | `GET /lands/me` | أراضيي | ✅ active_user | **هيدر** | `tenant_id`(هيدر) **و** `owner_id` حقيقي معًا | 🟠 محمي عمليًا | — |
| 3 | `PATCH /lands/{id}/revalue` | تغيير القيمة المالية لأرض (سوبريوزر) | ✅ superuser | **لا يوجد إطلاقًا** — بلا أي tenant dependency | **صفر فحص** | 🔴🔴🔴🔴🔴 **الأسوأ في كل الدفعات — لا حتى تزوير هيدر مطلوب** | ✅ **مؤكَّد حيًا (§4.1)** |
| 4 | `POST /developments` | إنشاء مشروع تطويري | ✅ active_user | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات | — |
| 5 | `GET /developments/{id}` | تفاصيل مشروع (ميزانية، حالة إنشاء) | ❌ **بلا مصادقة إطلاقًا** | — | `id` فقط | 🔴🔴🔴🔴 IDOR + بلا تسجيل دخول | ✅ **مؤكَّد حيًا (§4.2)** |
| 6 | `POST /units` | إنشاء وحدة عقارية | ✅ active_user | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات | — |
| 7 | `GET /units/for-sale` | الوحدات المتاحة للبيع (عالمي) | ❌ **بلا مصادقة إطلاقًا** | — | **صفر فلتر tenant** — كل التينانتات مجمّعة | 🔴🔴🔴🔴🔴 تسريب قوائم عبر كل التينانتات | ✅ **مؤكَّد حيًا (§4.2)** |
| 8 | `POST /units/{id}/buy` | شراء ملكية جزئية (دفع فعلي) | ✅ active_user | **هيدر** (لتسجيل الملكية فقط) | `get_unit` **بلا فلتر tenant حتى بالهيدر** | 🔴🔴🔴🔴🔴 IDOR مالي — **كامنة، معطَّلة حاليًا بطبقتين (§4.3)** | ✅ (كودًا يعمل حتى نقطة الكراش، مؤكَّد §4.3) |
| 9 | `GET /my-ownerships` | ملكياتي | ✅ active_user | — | `owner_user_id` حقيقي فقط | 🟢 آمن | — |
| 10 | `POST /rentals` | إنشاء عقد إيجار (+فاتورة فعلية) | ✅ active_user | **هيدر** | `get_unit` بلا فلتر tenant + `tenant_user_id`(المستأجر) **من جسم الطلب حرفيًا، بلا تحقق** | 🔴🔴🔴🔴🔴 احتيال فوترة: عقد إيجار وهمي لوحدة أي تينانت، فاتورة حقيقية باسم ضحية يختارها المهاجم | ❌ (كودًا فقط — غير مختبَر حيًا هذه الجلسة) |
| 11 | `POST /master-plans` | إنشاء مخطط رئيسي | ✅ active_user | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات | — |
| 12 | `POST /tokenize/{unit_id}` | تجزئة أصل لأسهم | ✅ active_user | **هيدر** | فحص `existing` بالهيدر، الوحدة نفسها بلا فحص | 🔴 IDOR كتابة | — |
| 13 | `POST /smart-contracts` | نشر عقد ذكي (سوبريوزر) | ✅ superuser | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات | — |

### 1.1) باج `purchase_tx_hash` — الموقع الدقيق (مطلوب صراحة)

`service.py:241` — `finance.transfer()` (السطر يرجّع كائن `Transaction` كامل، مؤكَّد من قراءة `finance/service.py:58-147: return tx`) يُمرَّر مباشرة كـ`purchase_tx_hash` لعمود `PropertyOwnership.purchase_tx_hash` (`models.py:160`, `String(100)`). **الدالة المتأثرة:** `buy_fractional_ownership` ← `POST /units/{id}/buy` (endpoint #8، endpoint الشراء الوحيد). **الموضع الخامس المؤكَّد لنفس الفئة** (بعد transport/tourism_sports، ومطابق تمامًا لتوصيف `technical-pattern-sweep-session-log.md:340`). لا مواضع مشابهة أخرى في الدومين (باقي حقول `*_tx_hash` تُولَّد بـ`uuid4()`, سلاسل حقيقية).

---

## 2) جدول `insurance` — 14 endpoint

**النطاق:** `router.py`(285 سطر)، `service.py`(584 سطر)، `repository.py`(196 سطر)، `models.py`(210 سطر)، `schemas.py`(150 سطر) — قراءة كاملة + تحقق حي.

**ملاحظة منهجية:** نسبة غير معتادة من endpoints محمية فعليًا (6 من 14) — كل `GET .../me` وأي عملية مربوطة مباشرة بـ`user_id`(JWT) محمية بالفعل. الخطر محصور بدقة في: إنشاء إداري عبر هيدر، `get_policy`/`list_policies` (IDOR قراءة قياسي)، `subscribe` (IDOR + مالي محدود بنمط "محفظة المهاجم")، `review_claim` (الأسوأ)، `disburse_pensions` (الأخطر تصميميًا).

| # | Endpoint | الوظيفة الفعلية | `current_user`؟ | مصدر `tenant_id` | فلتر repository | تصنيف | تحقق حي |
|---|---|---|---|---|---|---|---|
| 1 | `POST /policies` | إنشاء بوليصة (سوبريوزر) | ✅ superuser | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات | — |
| 2 | `GET /policies` | قائمة بوالص التينانت | ✅ active_user | **هيدر** | ✅ بقيمة ملوَّثة | 🔴🔴🔴🔴 IDOR قراءة | — |
| 3 | `GET /policies/{id}` | تفاصيل بوليصة | ✅ active_user | **هيدر** | مقارنة ضد نفس المصدر الملوَّث | 🔴🔴🔴🔴 IDOR قراءة | ✅ **مؤكَّد حيًا (§4.4)** |
| 4 | `POST /subscriptions` | اشتراك تأميني (دفع فعلي) | ✅ active_user | **هيدر** | مقارنة تينانت البوليصة ضد الهيدر (ملوَّثة) | 🔴🔴🔴🔴 IDOR + مالي محدود ("محفظة المهاجم") | ❌ كودًا فقط |
| 5 | `GET /subscriptions/me` | اشتراكاتي | ✅ active_user | هيدر + فلتر إضافي | `subscriber_user_id==user_id` **حقيقي** | 🟠 محمي عمليًا | — |
| 6 | `POST /subscriptions/{id}/renew` | تجديد اشتراك | ✅ active_user | لا يوجد | `subscriber_user_id != user_id` **حقيقي (JWT)** | 🟢 آمن | — |
| 7 | `POST /claims` | تقديم مطالبة (+AI) | ✅ active_user | **هيدر** | `subscriber_user_id != user_id` **حقيقي** | 🟠 محمي عمليًا | — |
| 8 | `GET /claims/me` | مطالباتي | ✅ active_user | لا يوجد | `claimant_user_id==user_id` **حقيقي فقط** | 🟢 آمن | — |
| 9 | `PUT /claims/{id}/review` | مراجعة/صرف مطالبة (دفع تعويض) | ✅ superuser | **هيدر** | فحص ثانٍ مكسور (§2.1) | 🔴🔴🔴🔴🔴 **الأخطر — فحصان معطوبان** | ❌ كودًا فقط (إعداد حي معقّد، غير منفَّذ هذه الجلسة) |
| 10 | `POST /pensions` | إنشاء سجل معاش (سوبريوزر) | ✅ superuser | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات | — |
| 11 | `GET /pensions/me` | معاشاتي | ✅ active_user | لا يوجد | `beneficiary_id==user_id` **حقيقي فقط** | 🟢 آمن | — |
| 12 | `POST /admin/disburse-pensions` | صرف معاشات شهري جماعي (سوبريوزر) | ✅ superuser | **لا يوجد أصلًا** | **صفر فلتر تينانت بالتصميم** | 🔴🔴🔴🔴🔴 الأسوأ تصميميًا — لكن self-DoS حاليًا | ✅ **مؤكَّد حيًا (§4.5)** |
| 13 | `POST /employee-profiles` | إنشاء ملف تأمين موظف (سوبريوزر) | ✅ superuser | **هيدر** | يُكتب مباشرة | 🔴 تلوّث بيانات | — |
| 14 | `GET /employee-profiles/me` | ملفي التأميني | ✅ active_user | لا يوجد | `user_id==current_user.id` **حقيقي فقط** | 🟢 آمن | — |

### 2.1) `review_claim` — فحصان معطوبان (اكتشاف جديد)

الفحص الأول: `claim.tenant_id != tenant_id` — نمط IDOR قياسي (هيدر). الفحص الثاني (المفروض طبقة حماية حقيقية، `service.py:431`): `policy.issuer_entity_id != reviewer_id` — **مقارنة بين مساحتي معرِّفات مختلفتين تمامًا** (`issuer_entity_id` مفتاح أساسي لـ`sovereign_entities_v2`، `reviewer_id` مفتاح أساسي لـ`users`). **نفس فئة "عمود خطأ" الموثَّقة لـ`arbitration_syndicates`/`tourism_sports.place_transfer_bid`** — لا يحمي من IDOR (الفحص الأول مُخترَق أصلًا سابقًا له)، ولا يسمح لمراجع شرعي حقيقي بالمراجعة في الغالبية العظمى من الحالات الواقعية. **غير مختبَر حيًا** (إعداد بوليصة→اشتراك→مطالبة معقّد، خارج ميزانية الوقت المتاحة هذه الجلسة).

### 2.2) باج `payment_tx_hash` — الموقع الدقيق (مطلوب صراحة)

`service.py:462` (`payout_tx = await finance.transfer(...)`) → `service.py:471-477` (`payout_tx_hash=payout_tx` في `update_claim`) → عمود `InsuranceClaim.payout_tx_hash` (`models.py:144`, `String(100)`). **يمنع `review_claim` فقط في حالة الموافقة الفعلية (`approve=True`)** — الرفض غير متأثر. **الموضع السادس المؤكَّد لنفس الفئة.**

**اكتشاف جديد مرتبط (نمط عكسي):** `subscribe()` (`service.py:198`) — الناتج الحقيقي لـ`finance.transfer()` (`tx_hash`) **لا يُستخدَم إطلاقًا**؛ العمود `subscription_tx_hash` يُكتب فيه UUID عشوائي مُلفَّق بدل الهاش الحقيقي. صفر كراش (نوع البيانات سليم)، لكن **فجوة تدقيق/مطابقة حسابات حقيقية** — يستاهل تصنيف كنمط مستقل ("تجاهل tx_hash الحقيقي صامتًا").

---

## 3) 🔴🔴🔴🔴🔴 الاكتشاف العابر للدفعات: بادئة مسار مضاعفة تكسر الربط الحقيقي بالفرونت إند — مؤكَّد حيًا

**الخلفية:** فورك `insurance` وفورك `health` وصلا لاستنتاجين متناقضين حول نفس الظاهرة (مسار مزدوج `/domain/domain/...` في ملفات `services/*.ts`) — فورك `health` افترض أن `main.py` بيسجّل بادئة إضافية فعليًا فرجّح إن الازدواج "طبيعي ومطابق"، وفورك `insurance` شكّك في هذا الاستنتاج وطلب تحقق حي عاجل.

**التحقق الحي الحاسم (منفَّذ بمعرفة المنسق):**
1. **قراءة مباشرة لحلقة التسجيل في `main.py:300-308`:** `fastapi_app.include_router(router_obj, prefix="/api", tags=tags_list)` — **الحقل الثاني في كل tuple (`"/insurance"`, `"/health"`, إلخ) غير مُستخدَم إطلاقًا في الاستدعاء نفسه**. البادئة الفعلية الوحيدة المسجَّلة هي `/api` + بادئة `router.py` الداخلية (مُعرَّفة مرة واحدة فقط في كل دومين، مؤكَّد بقراءة `insurance/router.py:17`, `health/router.py:14`, `realestate/router.py:15`).
2. **تشغيل السيرفر حيًا + طلبات مباشرة:**
   ```
   GET /api/insurance/policies          -> 401 (يصل لمنطق التطبيق — الموجود فعليًا)
   GET /api/health/profile/me           -> 401 (نفس الشيء)
   GET /api/realestate/lands/me         -> 401 (نفس الشيء)
   GET /api/insurance/insurance/policies -> 404 (المسار اللي الفرونت إند فعليًا بيناديه)
   GET /api/health/health/profile/me     -> 404 (نفس الشيء)
   GET /api/realestate/realestate/lands/me -> 404 (نفس الشيء)
   ```
3. **تأكيد `BASE_URL`:** `eppne-web/lib/api-client.ts:7` — `axios.create({baseURL: "http://localhost:8000/api", ...})`. **صفر rewrite في `next.config.ts`** (ملف فارغ فعليًا، تحقُّق مباشر).
4. **جرد سريع عبر `eppne-web/services/*.ts`:** نفس نمط "اسم الدومين مكرَّر" ظاهر بوضوح في **13+ ملف على الأقل** (عيّنة: `affiliate`, `commerce`, `employment`, `insurance`, `invitations`, `iot`, `logistics`, `marketplace`, `privacy`, `saas`, `social`, `transport`, `zamakana`) — يستاهل جرد شامل منفصل لتحديد الملفات المتأثرة بدقة (بعضها زي `academy`, `ai-agents`, `sovereign-entities` يبدو سليم من نفس الفحص السريع الأولي، غير مؤكَّد بعمق).

**الحكم:** فورك `health` كان مخطئًا — **`health.service.ts` أيضًا مكسور بنفس الطريقة تمامًا** (`/health/health/...` → 404 حي مؤكَّد)، رغم أن الفورك ظنّه "مطابقًا". **realestate عندها هذه المشكلة بالإضافة لمشكلة منفصلة تمامًا** (hooks بتستورد named exports غير موجودة من `services/realestate.ts` — حتى لو المسار كان صح، الاستيراد نفسه هيفشل في build/runtime). **insurance عندها هذه المشكلة فقط** (الأسماء والبنية متطابقة تمامًا مع الباك إند، لكن كل استدعاء حقيقي 404).

**الأثر العملي:** أي محاولة استخدام حقيقية من مستخدم فعلي عبر واجهة الويب الحالية لأي دومين من الثلاثة عشر+ المتأثرة **تفشل حتمًا** — هذا يناقض جزئيًا استنتاجات "مربوط بفرونت إند" في `batch1`/`batch2`/`batch3` لأي دومين يشترك في نفس نمط `services/*.ts` (تلك الجلسات اختبرت الباك إند مباشرة، لم تمرّ عبر الفرونت إند الفعلي). **لا يغيّر أي تصنيف IDOR في هذا التقرير أو التقارير السابقة** (الثغرات حقيقية 100% في الكود، تنتظر فقط إصلاح الربط لتصبح قابلة للاستغلال عبر الواجهة — تمامًا نفس منطق "الثغرة كامنة خلف باج منفصل" الموثَّق لـ`purchase_tx_hash`/`payment_tx_hash` وغيرها).

---

## 4) التحقق الحي — التفاصيل الكاملة

**السيرفر:** `uvicorn` محلي (`E:\cc\eppne-backend`, venv, منفذ 8000)، شُغِّل هذه الجلسة، **أُوقف في نهاية الجلسة** (`Stop-Process` + `Get-NetTCPConnection` يؤكد صفر `LISTENING`، فقط اتصالات `TimeWait` متبقية من الإغلاق الطبيعي).

**المستخدمون:** نفس حسابات throwaway الموثَّقة مسبقًا (`throwaway-test-users.md`) — `TEST_super_a` (id=772، تينانت1) و`TEST_instr_b` (id=774، تينانت16)، كلمة سر `TEST_pass_batch3_2026`، سجّلا دخول بنجاح بلا أي تغيير مطلوب.

**بوابة SaaS:** كل من `realestate`/`insurance` يستخدمان `SaaSControlService.get_active_subscription` (نفس آلية `logistics`/`manufacturing` في batch3 — أحدث اشتراك `ACTIVE`/`TRIAL` بغض النظر عن الخدمة). تينانت1 (اشتراك id=2, plan_id=2) عنده `features=["real_estate","insurance"]` أصلًا (بلا حاجة تعديل). **تينانت16 كان أحدث اشتراك نشط له (id=49, plan_id=48) بـ`features=[]`** — رُفعت مؤقتًا لتشمل الميزات المطلوبة لكل اختبار، **ثم أُعيدت لـ`[]` بالضبط بعد كل استخدام** (مؤكَّد `SELECT` مستقل في نهاية كل قسم).

### 4.1 `realestate.revalue_land` — 🔴🔴🔴🔴🔴 مؤكَّد حيًا، أخطر نتيجة في الدفعة

```
B (تينانت16 حقيقي) -> POST /realestate/lands {...} -> 201, id=5, tenant_id=16, current_value_mrusdt=1000

A (تينانت1 حقيقي، superuser، بتوكنه الحقيقي وX-Tenant-ID:1 — صفر تزوير) 
  -> PATCH /realestate/lands/5/revalue?new_value=99999999
  -> 200 {"current_value_mrusdt":"99999999", "owner_id":774, ...}

SELECT مستقل: land_assets WHERE id=5 -> tenant_id=16, owner_id=774, current_value_mrusdt=99999999.00000000
```
**الحكم:** لا حتى تزوير هيدر مطلوب — `revalue_land` بلا أي `tenant`/`current_user.tenant_id` dependency على الإطلاق. أي سوبريوزر من أي تينانت يغيّر القيمة المالية لأي أرض في المنصة بمجرد معرفة الـ`id`.

### 4.2 `realestate.get_development` / `list_units_for_sale` — 🔴🔴🔴🔴 مؤكَّد حيًا، بلا أي مصادقة

```
B -> POST /realestate/developments {"land_asset_id":5,"name":"TEST_DEV_B_SECRET","total_budget_mrusdt":500000} -> 201, id=80

[زائر مجهول تمامًا، صفر Authorization header] -> GET /realestate/developments/80
-> 200 {"name":"TEST_DEV_B_SECRET","total_budget_mrusdt":"500000.00000000", ...} (كل التفاصيل المالية)

[زائر مجهول] -> GET /realestate/units/for-sale
-> 200 [{"id":5,"development_id":4,"sale_price_mrusdt":"1000.00000000", ...}] (وحدة من جلسة سابقة، عالمي بلا فلتر تينانت)
```

### 4.3 `realestate.buy_fractional_ownership` — 🔴 اكتشاف جديد: طبقة كراش ثالثة أسبق من `purchase_tx_hash`

```
B -> POST /realestate/units {"development_id":80,"unit_number":"U-TEST-B","sale_price_mrusdt":10} -> 201, id=81
[شحن محفظة A مؤقتًا بـ100 MR_USDT throwaway لتفعيل مسار الشراء]

A -> POST /realestate/units/81/buy {"ownership_percentage":10} 
-> 500 Internal Server Error

السجل: TypeError: AIAgentsService.execute_agent_action() got an unexpected keyword argument 'tenant_id'
  (realestate/service.py:232 لسه بيمرر tenant_id= ومش بيمرر idempotency_key= الإجباري —
   توقيع execute_agent_action اتغيّر في جلسة ai-agents-idor-fix بتاريخ 2026-08-24،
   ولم يُحدَّث استدعاء realestate المقابل)

SELECT مستقل: property_ownerships WHERE unit_id=81 -> صفر صفوف (rollback كامل، صفر أثر جانبي)
```
**الحكم:** `buy_fraction` (endpoint الشراء الوحيد، الأخطر ماليًا في الدومين لأنه بلا فحص tenant حتى بالهيدر) **معطَّل حاليًا بطبقتين متتاليتين من الأعطال المستقلة تمامًا عن IDOR نفسه**: (أ) استدعاء `ai_agents` بتوقيع قديم (يكسر أولًا)، ثم لو اتصلح (ب) باج `purchase_tx_hash` (§1.1، يكسر ثانيًا). **الثغرة الأمنية الأساسية (صفر فحص ملكية على الوحدة) حقيقية 100% في الكود، لكن يلزم إصلاح طبقتين منفصلتين قبل أن تصبح قابلة للاستغلال الفعلي حيًا.**

### 4.4 `insurance.get_policy` — 🔴🔴🔴🔴 مؤكَّد حيًا

```
B -> POST /insurance/policies {"issuer_entity_id":4,"name":"TEST_POLICY_B_SECRET",...} -> 201, id=56, tenant_id=16

A (توكن حقيقي تينانت1) + X-Tenant-ID:16 (مزوَّر) -> GET /insurance/policies/56
-> 200 {"name":"TEST_POLICY_B_SECRET", "max_coverage_limit_mrusdt":"50000.00000000", ...}

A (نفس التوكن) + X-Tenant-ID:1 (حقيقي) -> GET /insurance/policies/56
-> 403 PermissionDeniedError  [يثبت أن الفحص موجود، لكنه يثق بالهيدر لا current_user.tenant_id]
```

### 4.5 `insurance.disburse_monthly_pensions` — 🔴🔴🔴🔴🔴 self-DoS مؤكَّد حيًا (اتجاهان)

```
[صفر معاش ACTIVE في DB قبل الاختبار]
A -> POST /insurance/pensions {"beneficiary_id":772,"monthly_amount_mrusdt":50,...} -> 201, id=2, status=ACTIVE

A -> POST /insurance/admin/disburse-pensions
-> 200 {"message":"Disbursed 0 pensions","count":0}

SELECT مستقل: pension_records WHERE id=2 -> status=ACTIVE (بلا تغيير), total_disbursed_mrusdt=0
```
**الحكم:** رغم وجود معاش نشط حقيقي، الدالة أرجعت "نجاح" بـ`count=0` وصفر أثر — يؤكد استنتاج الفورك (`list_pensions_for_beneficiary(None, ...)` → `WHERE beneficiary_id IS NULL` على عمود `NOT NULL` → صفر صف دائمًا). **الثغرة التصميمية (صفر فحص تينانت) حقيقية 100%، لكن غير قابلة للتفعيل حاليًا.**

### 4.6 `health.get_facility` / `list_facilities` — 🔴🔴🔴🔴 مؤكَّد حيًا

```
[منشأة throwaway أُدرجت مباشرة في DB لتينانت16 — create_facility معطوبة، §4.7]

A + X-Tenant-ID:16 (مزوَّر) -> GET /health/facilities/2
-> 200 {"name":"TEST_FACILITY_B_SECRET","facility_category":"CLINIC", ...}

A + X-Tenant-ID:1 (حقيقي) -> GET /health/facilities/2
-> 403 PermissionDeniedError

A + X-Tenant-ID:16 (مزوَّر) -> GET /health/facilities
-> 200 [{"id":2,"name":"TEST_FACILITY_B_SECRET", ...}]
```

### 4.7 `health.create_facility` — NameError self-DoS مؤكَّد حيًا

```
A -> POST /health/facilities {"name":"TEST_CREATE_CHECK","facility_category":"CLINIC"}
-> 500 Internal Server Error

SELECT مستقل: health_facilities WHERE name='TEST_CREATE_CHECK' -> صفر صفوف (صفر أثر جانبي)
```
يطابق تمامًا استنتاج الفورك: `job` غير مُعرَّف في نطاق الدالة (نسخة copy-paste من دومين آخر) — الثغرة (تلوّث تينانت-هيدر) كامنة، غير قابلة للاستغلال عبر `POST` حاليًا (لكن قراءتها عبر `GET` قابلة للاستغلال فورًا كما في §4.6، ببيانات مزروعة مباشرة في DB).

### تنظيف بيانات throwaway — مكتمل ومؤكَّد مستقل

جميع الصفوف المُنشأة هذه الجلسة (land_assets id=5، real_estate_developments id=80، property_units id=81، insurance_policies id=56، pension_records id=2، health_facilities id=2) **محذوفة بالكامل**. `wallets.user_id=772` أُعيدت لـ`{}` (فارغة، الأصل). `saas_service_plans.id=48` أُعيدت لـ`features=[]` (الأصل). فحص نهائي مستقل (استعلام واحد يغطي كل الجداول) أكَّد: **صفر residue** من هذه الجلسة. لم يُلمَس أي شيء من بيانات الجلسات السابقة. **صفر تعديل كود، صفر migration.**

---

## 5) خريطة الترابط الكاملة

```
identity ──(current_user)──> realestate, insurance, health (كل الـendpoints)

saas.get_active_subscription (بوابة "أحدث اشتراك نشط بغض النظر عن الخدمة"،
   نفس آلية logistics/manufacturing في batch3) <── realestate (كل عمليات الإنشاء/الشراء)،
   insurance (create_policy, subscribe, submit_claim)
                                          │
finance.transfer <── realestate.buy_fractional_ownership (معطَّلة، §4.3)،
   insurance.subscribe/renew_subscription/review_claim (يصطدم بـpayment_tx_hash، §2.2)،
   insurance.disburse_monthly_pensions (sender_id=1 هاردكودد — كامن، self-DoS)
   [health: لا يستدعي finance إطلاقًا — استثناء وحيد بين الدومينات الممسوحة عبر batch1-4]
                                          │
invoicing.create_invoice <── realestate.buy_fractional_ownership، realestate.rent_unit
   (منسوبة لـtenant_user_id من جسم الطلب بلا تحقق، §1 صف 10)، insurance.subscribe/review_claim
                                          │
affiliate.register_commission <── realestate.buy_fractional_ownership، realestate.rent_unit،
   insurance.subscribe
                                          │
ai_agents.execute_agent_action + ai_governance.check_and_consume <──
   realestate.buy_fractional_ownership (استدعاء ai_agents مكسور بنيويًا، §4.3)،
   insurance.submit_claim/review_claim
                                          │
communications.send_notification <── realestate.buy_fractional_ownership

روابط FK بنيوية بلا تحقق تشغيلي فعلي:
   realestate.PropertyUnit.smart_asset_id ──> iot.smart_assets
   manufacturing.ManufacturingFacility.real_estate_unit_id ──> realestate.property_units (اتجاه عكسي، batch3)
   insurance.InsuranceSubscription.employment_contract_id ──> employment (بلا تحقق)
   insurance.*.issuer_entity_id / source_entity_id ──> sovereign_entities_v2 (بلا تحقق وجود/نشاط)

health ──> (لا أحد يستدعيه) — أول دومين ممسوح (batch1-4) بلا أي استدعاء finance/invoicing/affiliate/saas/ai_agents إطلاقًا
realestate, insurance ──> (لا أحد يستدعيهما)
```

**ملاحظة ترابط بارزة:** `health` معزول ماليًا بالكامل عن باقي المنصة (لا فوترة، لا عمولة، لا بوابة SaaS، تحليل AI عبر استدعاء خارجي مباشر لـ`Gemini API` منفصل عن `ai_agents`/`ai_governance`) — أول دومين بهذا الشكل عبر الدفعات الأربع.

---

## 6) أنماط منتشرة جديدة تستاهل تصنيف مركزي (بالإضافة لبادئة المسار المضاعفة في §3)

| # | النمط | الموقع المكتشَف هذه الجلسة | ملاحظة |
|---|---|---|---|
| 1 | **بادئة مسار مضاعفة (`/domain/domain/...`) في `services/*.ts`** | `health`, `insurance`, `realestate`، + عيّنة أولية من 13+ ملف آخر | 🔴🔴🔴🔴🔴 الأخطر شمولًا — راجع §3 |
| 2 | **مقارنة ID عبر مساحتي معرِّفات مختلفتين** (`review_claim`: `issuer_entity_id` vs `reviewer_id`) | `insurance.review_claim` | الموضع الثالث لنفس الفئة (بعد `arbitration_syndicates`, `tourism_sports.place_transfer_bid`) |
| 3 | **تجاهل `tx_hash` الحقيقي صامتًا لصالح قيمة مُلفَّقة** (`subscription_tx_hash` UUID عشوائي بدل الهاش الحقيقي) | `insurance.subscribe` | عكس اتجاه باج `payment_tx_hash` (صفر كراش، فجوة تدقيق) — نمط جديد، يستاهل جرد شامل منفصل |
| 4 | **self-DoS يخفي ثغرة تصميم حقيقية** (تكرار) | `insurance.disburse_pensions` (بعد `manufacturing.schedule_maintenance` في batch3) | العدّ التراكمي وصل لموضعين — يستاهل جرد شامل لباقي الدومينات |
| 5 | **استدعاء ميكانيكي مكسور بسبب تغيير توقيع دالة في دومين آخر لم يُحدَّث في المستدعي** (`realestate.buy_fractional_ownership` ← `ai_agents.execute_agent_action`) | `realestate/service.py:232` | اكتشاف جديد تمامًا هذه الجلسة (§4.3) — أثر جانبي غير مقصود لجلسة `ai-agents-idor-fix` (2026-08-24) لم تُراجَع بقية المستدعين |
| 6 | **"Service layer صحيح، Hooks layer مكسورة الاستيراد"** | `realestate` فقط (حتى الآن) | مستقل تمامًا عن بادئة المسار — انفصال فرونت إند داخلي |

---

## 7) الفجوات المكتشفة — التصنيف النهائي (بانتظار توجيهك، صفر تنفيذ)

### 7.1 بنود IDOR/تلوّث بيانات (نفس النمط الميكانيكي المعتاد — `get_current_tenant`/هيدر → `cast(int, current_user.tenant_id)`)

| # | الدومين | البند | الخطورة | مؤكَّد حيًا؟ |
|---|---|---|---|---|
| 1 | realestate | `revalue_land` — صفر فحص تينانت من الأساس | 🔴🔴🔴🔴🔴 **الأعلى في كل الدفعات — لا حتى هيدر مطلوب** | ✅ §4.1 |
| 2 | realestate | `get_development`, `units/for-sale` — بلا مصادقة إطلاقًا | 🔴🔴🔴🔴 تسريب مالي/تجاري عام | ✅ §4.2 |
| 3 | realestate | `buy_fraction`, `rent_unit` — صفر فحص ملكية على الوحدة نفسها | 🔴🔴🔴🔴🔴 IDOR مالي + احتيال فوترة | 🟡 `buy_fraction` كودًا حتى نقطة كراش مستقل (§4.3)، `rent_unit` غير مختبَر |
| 4 | insurance | `get_policy`/`list_policies` — IDOR قراءة قياسي | 🔴🔴🔴🔴 | ✅ §4.4 |
| 5 | insurance | `disburse_pensions` — صفر فحص تينانت بالتصميم | 🔴🔴🔴🔴🔴 شكلًا، لكن self-DoS حاليًا | ✅ (كتابة لا تحصل، لكن الفحص المفقود مؤكَّد) §4.5 |
| 6 | insurance | `review_claim` — فحصان معطوبان (هيدر + مقارنة ID خاطئة) | 🔴🔴🔴🔴🔴 | ❌ كودًا فقط |
| 7 | health | `get_facility`/`list_facilities` — IDOR قراءة قياسي | 🔴🔴🔴🔴 | ✅ §4.6 |
| 8 | health | `create_facility` — تلوّث تينانت-هيدر (كامن خلف NameError) | 🔴🔴🔴 كامن | ✅ (الكراش، لا الثغرة نفسها) §4.7 |
| 9 | health | `create_prescription` — صفر فحص ملكية على `consultation_id` + `patient_id` حر من الطلب | 🔴🔴🔴🔴🔴 **أعلى حساسية طبية بالدفعة، لكن معطَّلة (schema ناقصة)** | ❌ كودًا فقط |

### 7.2 بنود منفصلة عن IDOR (باجات وظيفية/تصميمية موثَّقة بلا إصلاح)

| # | الدومين | البند | ملاحظة |
|---|---|---|---|
| 1 | realestate | `purchase_tx_hash` (§1.1) — الموضع الخامس المؤكَّد لفئة `payment_tx_hash` | معطِّل تام لـ`buy_fraction` |
| 2 | realestate | `ai_agents.execute_agent_action` توقيع قديم (§4.3، §6.5) | يكسر `buy_fraction` **قبل** الوصول لباج `purchase_tx_hash` |
| 3 | insurance | `payout_tx_hash` (§2.2) — الموضع السادس | يمنع `review_claim(approve=True)` فقط |
| 4 | insurance | `subscription_tx_hash` UUID مُلفَّق بدل الهاش الحقيقي (§2.2) | فجوة تدقيق، صفر كراش |
| 5 | health | 3 دوال بنفس باج `NameError` (`book_appointment`, `trigger_emergency`, `create_facility`) | يمنع 3 endpoints بالكامل حاليًا؛ صفر أثر مالي جانبي (تأكيد تحليلي، `finance.transfer` بلا commit داخلي) |
| 6 | health | تلوّث `tenant_id=1` الافتراضي في `get_or_create_profile` عند عدم تمرير التينانت | غير مختبَر حيًا |
| **7** | **عابر للدفعات** | **بادئة مسار مضاعفة في `services/*.ts` (§3)** | **يكسر الربط الحقيقي بالفرونت إند لـ13+ دومين على الأقل — أعلى أولوية** |

---

## 8) تنفيذ IDOR البنود 1-4 [2026-08-26] — مكتمل، مؤكَّد حيًا بالكامل، بانتظار موافقة الـcommit

**قرار المستخدم:** موافقة كاملة على تصنيف §7. ترتيب تنفيذ فوري: (1) `realestate.revalue_land` (2) `realestate.get_development`/`units-for-sale` (3) `insurance.get_policy`/`list_policies` (4) `health.get_facility`/`list_facilities`. باقي بنود §7.1 (بند 5) و§7.2 بالكامل **لم تُنفَّذ** — توثيق فقط (§40-42 في `constructor-mismatch-backlog-classification.md`)، بما فيها منع صريح للمس `health.create_prescription`.

**نطاق التعديل الكودي:** نفس النمط الميكانيكي المعتاد (`get_current_tenant`/هيدر → `cast(int, current_user.tenant_id)`) + إضافة مصادقة من الصفر حيث كانت غائبة تمامًا (`get_development`, `units/for-sale`) + إضافة فحص ملكية حقيقي حيث كان غائبًا تمامًا (`revalue_land`، كان بلا أي `tenant`/`current_user` مقارنة إطلاقًا).

| # | الملف | التغيير |
|---|---|---|
| 1 | `realestate/service.py` | `revalue_land`: أضيف معامل `tenant_id`، فحص `land.tenant_id != tenant_id` → `PermissionDeniedError` قبل التحديث |
| 1 | `realestate/router.py` | `revalue_land`: تمرير `tenant_id=cast(int, current_user.tenant_id)` (لم يكن هناك أي تينانت يُمرَّر سابقًا) |
| 2 | `realestate/service.py` | `get_development`: أضيف معامل `tenant_id`، فحص `dev.tenant_id != tenant_id` → `PermissionDeniedError` |
| 2 | `realestate/router.py` | `get_development`: أضيف `current_user: User = Depends(get_current_active_user)` (لم يكن موجودًا إطلاقًا) + تمرير `tenant_id` |
| 2 | `realestate/service.py` | `list_units_for_sale`: أضيف معامل `tenant_id` أول، يُمرَّر لـ`repo.list_units` |
| 2 | `realestate/repository.py` | `list_units`: أضيف معامل `tenant_id`، فلتر `WHERE tenant_id == tenant_id` مضاف للاستعلام (كان بلا أي فلتر تينانت) |
| 2 | `realestate/router.py` | `list_units_for_sale`: أضيف `current_user: User = Depends(get_current_active_user)` (لم يكن موجودًا إطلاقًا) + تمرير `tenant_id` |
| 3 | `insurance/router.py` | `list_policies`/`get_policy`: حذف `tenant: AcademyTenant = Depends(get_current_tenant)`، استبدال `cast(int, tenant.id)` بـ`cast(int, current_user.tenant_id)` |
| 4 | `health/router.py` | `list_facilities`/`get_facility`: نفس الاستبدال بالضبط |

**تحقق قبل التشغيل:** `python -m ast` (syntax check) لكل الملفات الخمسة المعدَّلة → نجح للجميع.

**تحقق حي — هجوم مرفوض + مسار شرعي + `SELECT` مستقل، لكل بند من الأربعة:**

### 8.1 `realestate.revalue_land`
```
B (تينانت16) → POST /realestate/lands → id=6, tenant_id=16, current_value=1000

هجوم: A (تينانت1، توكن حقيقي، X-Tenant-ID:1 حقيقي — بلا أي تزوير)
  → PATCH /lands/6/revalue?new_value=99999999 → 403 PermissionDeniedError ✅ مرفوض

مسار شرعي: B → PATCH /lands/6/revalue?new_value=2000 (بتوكنها) → 200 ✅ نجح

SELECT مستقل: land_assets WHERE id=6 → current_value_mrusdt=2000.00000000 (قيمة B، ليست قيمة هجوم A) ✅
```

### 8.2 `realestate.get_development` / `list_units_for_sale`
```
B → POST /realestate/developments → id=81, tenant_id=16
B → POST /realestate/units → id=82, tenant_id=16

هجوم 1: A + X-Tenant-ID:16 (مزوَّر) → GET /developments/81 → 403 ✅ مرفوض (current_user.tenant_id الحقيقي=1 يُستخدَم الآن، لا الهيدر)
هجوم 2: زائر بلا أي Authorization → GET /developments/81 → 401 ✅ مرفوض (كان 200 قبل الإصلاح)
مسار شرعي: B → GET /developments/81 (بتوكنها) → 200 ✅ نجح

زائر بلا Authorization → GET /units/for-sale → 401 ✅ مرفوض (كان 200 عالميًا قبل الإصلاح)
A (تينانت1 حقيقي) → GET /units/for-sale → لا يحتوي وحدة B (id=82) ✅ عزل صحيح
B (تينانت16 حقيقي) → GET /units/for-sale → يحتوي وحدتها (id=82) فقط ✅ عزل صحيح
```

### 8.3 `insurance.get_policy` / `list_policies`
```
B → POST /insurance/policies → id=57, tenant_id=16

هجوم: A + X-Tenant-ID:16 (مزوَّر) → GET /policies/57 → 403 ✅ مرفوض
مسار شرعي: B → GET /policies/57 → 200 ✅ نجح
list_policies: A (تينانت1) لا يرى بوليصة B لا بهيدره الحقيقي ولا بهيدر مزوَّر (16) ✅
```

### 8.4 `health.get_facility` / `list_facilities`
```
[منشأة throwaway تينانت16، id=4 — create_facility لسه معطوبة بباج NameError منفصل، خارج نطاق هذه الجلسة]

هجوم: A + X-Tenant-ID:16 (مزوَّر) → GET /facilities/4 → 403 ✅ مرفوض
مسار شرعي: B → GET /facilities/4 → 200 ✅ نجح
list_facilities: A + هيدر مزوَّر لا يرى منشأة B ✅ / B ترى منشأتها ✅
```

**تنظيف بيانات throwaway:** كل الصفوف (land_assets id=6، real_estate_developments id=81، property_units id=82، insurance_policies id=57، health_facilities id=4) محذوفة بالكامل. `saas_service_plans.id=48` مُعاد لـ`features=[]`. فحص نهائي مستقل: صفر residue. السيرفر التجريبي أُوقف.

**توثيق Backlog:** البنود #40 (`ai_agents` توقيع قديم في `buy_fraction`)، #41 (`review_claim` مقارنة ID خاطئة)، #42 (`create_prescription`، ممنوع اللمس) أُضيفت لـ`constructor-mismatch-backlog-classification.md` — توثيق فقط، صفر إصلاح.

**⏳ لم يُنفَّذ `commit` بعد — بانتظار موافقتك الصريحة على الـ`diff`.**

---

## 9) الخطوة التالية المتفق عليها (بعد إغلاق هذه الدفعة)

بتوجيه صريح: فتح جلسة جرد شاملة (مش عينة) لبند `frontend-service-url-prefix-mismatch` (#31 في `constructor-mismatch-backlog-classification.md`) عبر كل الـ34 دومين فرونت إند — مراجعة كل رابط `apiClient.*` في كل ملف `services/*.ts` (لا عيّنة 3 روابط أولى كما في الفحص الأولي)، لتحديد نطاق التصحيح الدقيق ومراجعة استنتاجات "مربوط بفرونت إند" في batch1/2/3/4 على ضوء النتيجة. **لم تبدأ بعد — تُفتح كجلسة منفصلة بعد إغلاق هذه الدفعة.**
