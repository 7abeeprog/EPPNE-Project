# جلسة: إصلاح أمني عاجل — دومين insurance (Batch 0-A)

**التاريخ:** 2026-09-21
**الحالة الحالية [محدَّثة]:** 🟡 **المرحلة 4 (الإصلاح + التحقق الحي بعده) مكتملة، ومراجَعة أدلتها من المستخدم (§13). صفر migration. التنظيف نُفِّذ ومُتحقَّق منه (§14-أ: zero-diff على 259 جدولًا، محفظة user 1 = 710.0). الفشلان "المسبقان" أُثبتا بالتشغيل على baseline نظيف (§14-ب). بانتظار موافقة المستخدم على النصوص الحرفية لتحديث `PROGRESS_LOG.md` (المسودة الحاكمة: `.claude/reports/insurance-batch0a-progress-log-draft.md`، §15-أ) قبل كتابتها؛ الـcommits معلَّقة بقرار المستخدم (تبعية 048، §15-ب) ولم يُنفَّذ أي commit؛ الدرجة النهائية في §15-د (≈ 657/1000).** الأقسام 1–9 أدناه تاريخية (المراحل 2–3)، والأحدث في §10–§13.

**قرارات المستخدم (2026-09-21):** D1 = الطبقة (أ) فقط (الطبقة (ب) ممنوعة وتُوثَّق كبند backlog واحد `insurance-disburse-pensions-payout-logic-broken`)؛ D2 = موافَق (تحقق انتماء `beneficiary_id`/`user_id` للتينانت)؛ D3 = موافَق (`subscribe`/`submit_claim`/`get_my_subscriptions` — "اكتُشفت أثناء الجلسة، أُصلحت بموافقة صريحة"). **لا يُصلَح:** `review_claim` يدفع من محفظة المراجِع الشخصية، وأي `tenant` dependency غير مستخدمة لا تزول طبيعيًا بالإصلاح.

**المراجع المقروءة (قراءة فقط):**
- `CODING_STANDARDS.md` (42 سطر) — لا قواعد خاصة بالأمان/التينانت، المطبَّق: `async/await`، Pydantic، أسماء واضحة.
- `PROJECT_AUDIT.md` — يصنّف insurance "✅ مكتمل" بنيويًا و"لم يُفحص منطقيًا بعمق" (السطر 411) — أي التصنيف لا يعكس الحالة الأمنية.
- `eppne-backend/app/domains/insurance/{router,service,repository,models}.py` بالكامل.
- `eppne-backend/app/core/security.py` (`get_current_tenant`, `get_current_superuser`, `SimpleTenant`).
- `eppne-backend/app/domains/finance/service.py::transfer` + `FinanceService.__init__`.
- `.claude/reports/ai-agents-idor-fix-session-log.md` و`command-idor-fix-session-log.md` (النمط المعتمَد).
- `.claude/reports/batch4-audit-security-realestate-insurance-health.md` §4.4/§4.5 (تحقق حي سابق لنفس الدومين).
- `.claude/reports/tenant-system-account-phase3-conversion-session-log.md` (نمط حساب النظام الموحَّد).

---

## 1) النمط المرجعي المعتمَد (من ai_agents / command)

**مصدر التلوث:** `get_current_tenant` (`core/security.py:322`) تُرجع `tenant.id` من هيدر `X-Tenant-ID` **حصريًا**، بقيمة افتراضية `1` لو الهيدر غايب — يعني الاستغلال لا يحتاج تزويرًا أصلًا، يكفي حذف الهيدر.

**الإصلاح الميكانيكي المُختبَر (طُبِّق على ai_agents 13/13):**
1. حذف `tenant: AcademyTenant = Depends(get_current_tenant),` من توقيع الـendpoint.
2. إضافة `tenant_id = cast(int, current_user.tenant_id)` كأول سطر بالجسم.
3. استبدال كل `tenant.id` بـ`tenant_id`.
4. إزالة الاستيراد لو صار غير مستخدم.
5. صفر تغيير على `service.py`/`repository.py`/`schemas.py` (في ai_agents).

**ربط FinanceService بالتينانت:** `FinanceService(db, tenant_id)` — `transfer()` يبحث عن المستلم بـ`get_by_email(email, self.tenant_id)` ويرفض لو `receiver.tenant_id != self.tenant_id`. **لا يتحقق من تينانت `sender_id`** إطلاقًا (مهم لـ`disburse`، تحت).

---

## 2) جرد الـ5 endpoints (تشخيص فقط)

### 2.1 `POST /insurance/policies` — `create_policy` (router:24)
- **ما يفعله:** ينشئ بوليصة تأمين. `Depends(get_current_superuser)` + فحص عضوية `OWNER`/`EXECUTIVE_DIRECTOR` على `issuer_entity_id` (`service.py:128-133`).
- **يقرأ:** `EntityMembership` (بحسب `entity_type/entity_id/user_id`، **بلا فلتر تينانت**).
- **يكتب:** صف في `insurance_policies` بـ`tenant_id` القادم من الهيدر + `audit_log`.
- **يحرّك فلوس؟** لا.
- **الثغرة:** superuser في تينانت A + هيدر `X-Tenant-ID: B` → بوليصة تُكتب في تينانت B (حقن بيانات عابر للتينانت؛ مستخدمو B يرونها ويقدرون يشتركوا فيها). فحص العضوية لا يمنع لأنه غير مربوط بالتينانت.
- **الإصلاح المقترح:** النمط المرجعي حرفيًا (`tenant_id = cast(int, current_user.tenant_id)`). صفر تعديل service.

### 2.2 `PUT /insurance/claims/{id}/review` — `review_claim` (router:220)
- **ما يفعله:** يوافق/يرفض مطالبة تعويض، ولو موافقة يصرف التعويض.
- **يقرأ:** `insurance_claims`, `insurance_subscriptions`, `insurance_policies`, `EntityMembership`, خطة SaaS للتينانت.
- **يكتب:** تحديث المطالبة (`PAID`/`REJECTED`)، `finance.transfer` (خصم من محفظة المراجِع وإضافة لمحفظة صاحب المطالبة)، فاتورة، `audit_log`، حدث `event_bus`.
- **يحرّك فلوس؟** **نعم** (`service.py:518`).
- **الثغرة:** `tenant_id` من الهيدر يستخدم في: (أ) فلتر `claim.tenant_id != tenant_id` — فمراجِع بهيدر B يقدر يفتح مطالبات B، (ب) `_check_saas_limits` — يتجاوز بوابة اشتراك تينانته الحقيقي ويستخدم اشتراك تينانت آخر، (ج) `FinanceService(db, tenant_id)` — التحويل يجري على سياق تينانت مزوَّر. فحص العضوية بجانبه يخفف الأثر لكن لا يعالج السبب.
- **الإصلاح المقترح:** النمط المرجعي حرفيًا. صفر تعديل service.

### 2.3 `POST /insurance/pensions` — `create_pension` (router:278)
- **ما يفعله:** ينشئ سجل معاش لمستفيد.
- **يكتب:** صف في `pension_records` بـ`tenant_id = tenant.id` (من الهيدر، router:288) + `audit_log`.
- **يحرّك فلوس؟** لا مباشرة — لكنه يُنتج السجل الذي تصرفه `disburse` لاحقًا.
- **الثغرة:** حقن سجل معاش في تينانت آخر عبر الهيدر. ثغرة ثانوية موجودة أصلًا: `beneficiary_id` **لا يُتحقق إنه ينتمي لنفس التينانت**.
- **الإصلاح المقترح:** النمط المرجعي (`pension_data["tenant_id"] = tenant_id` من `current_user`). **إضافة اختيارية (تحتاج موافقة، D2):** التحقق أن `beneficiary_id` ينتمي لتينانت المستدعي عبر `UserRepository.get_by_id(beneficiary_id, tenant_id)` (موجودة وتقبل tenant_id).

### 2.4 `POST /insurance/admin/disburse-pensions` — `disburse_pensions` (router:349) — الأخطر تصميميًا
- **ما يفعله (المفترض):** يصرف المعاشات الشهرية.
- **الكود الفعلي:** الـendpoint يستقبل `tenant` من الهيدر **ولا يستخدمه إطلاقًا**، ويستدعي `disburse_monthly_pensions()` بلا أي معامل. الدالة تستدعي `repo.list_pensions_for_beneficiary(cast(int, None), status=ACTIVE)`.
- **🔴 اكتشاف يصحّح فرضية التعليمات:** `beneficiary_id == None` يُترجَم لـ`WHERE beneficiary_id IS NULL` (مؤكَّد بتجميع الاستعلام فعليًا)، والعمود `nullable=False` → **الاستعلام يرجّع صفر صف دائمًا**. النتيجة: **الصرف العابر للتينانتات كامن (latent) لا نشط اليوم** — نفس ما وثّقه `batch4` §4.5 حيًا (`count=0` رغم وجود معاش ACTIVE). الثغرة التصميمية (صفر فلتر تينانت) حقيقية 100%، لكن **لا يمكن تفعيلها حاليًا**. أي "إصلاح" لاحق لباج `IS NULL` (مثلًا `list all ACTIVE`) سيحوّلها فورًا لصرف عالمي فعلي.
- **باجات مكدَّسة على نفس الدالة (تمنع الصرف حتى لو أُصلح الاستعلام):**
  1. `finance.transfer(...)` بلا `idempotency_key` وهو معامل إجباري → `TypeError`.
  2. `except Exception: pass` (service:636) يبلع الـTypeError بصمت → الدالة ترجّع `count=0` "نجاح".
  3. `sender_id=1` هاردكودد: `transfer` لا يتحقق من تينانت المرسل، فمعاش تينانت B سيُدفع من محفظة المستخدم 1 (تينانت 1). (هذا الموقع **لم يدخل** ضمن التسعة المحوَّلة لحساب النظام في Phase 3.)
  4. `update_pension(last_payout_tx=tx)` يمرر كائن Transaction لعمود `String(100)`.
  5. `_get_payout_date()` ترجع `utcnow()` دائمًا → أي معاش له `last_payout_tx` يُعتبر "مدفوع هذا الشهر" للأبد.
- **يحرّك فلوس؟** **مصمَّم لذلك** (تحويلات `MR_USDT` جماعية)، لكنه اليوم لا يحرّك شيئًا.
- **الاستدعاءات:** مستدعٍ واحد فقط (`router.py:358`)؛ لا Celery، لا اختبارات، لا مستدعين آخرين (grep شامل).
- **الإصلاح المقترح (طبقتان — تحتاج قرارًا D1):**
  - **الطبقة أ (العزل — إلزامية):** (1) `disburse_monthly_pensions(self, tenant_id: int)` معامل إجباري (مستدعٍ واحد فقط فلا داعي لـopt-in)؛ (2) دالة repo **جديدة** `list_active_pensions(tenant_id)` بفلتر `tenant_id + status == ACTIVE` (لا أعدّل `list_pensions_for_beneficiary` الموجودة)؛ (3) الـendpoint يمرّر `cast(int, current_user.tenant_id)` ويحذف تبعية الهيدر؛ (4) `FinanceService(self.db, tenant_id)` بدل `pension.tenant_id`، وتحقق دفاعي `pension.tenant_id == tenant_id`.
  - **الطبقة ب (مسار الفلوس — اختيارية لكن موصى بها):** إصلاح الباجات 1-5 بنفس نمط Phase 3 (`get_or_create_system_account(db, tenant_id)` كدافع، `idempotency_key` حتمي `pension_{id}_{YYYY-MM}`، تسجيل الاستثناء بدل `pass`، `last_payout_tx=tx.tx_hash`). **بدونها لن أستطيع إثبات "السيناريو المشروع يعمل" عبر HTTP**، لأن الدالة تُرجع 0 دائمًا. **مخاطرة الطبقة ب:** هذه أول مرة يصير فيها الـendpoint يحرّك فلوس فعلًا في أي بيئة — لذلك أحتاج موافقة صريحة منفصلة.

### 2.5 `POST /insurance/employee-profiles` — `create_employee_profile` (router:366)
- **ما يفعله:** ينشئ ملف تأمين موظف (`government_insurance_number`، نسب المساهمة).
- **يكتب:** صف في `employee_insurance_profiles` بـ`tenant_id` من الهيدر + `audit_log`.
- **يحرّك فلوس؟** لا.
- **الثغرة:** حقن عابر للتينانت. ثغرة ثانوية: `user_id` في الجسم غير مُتحقَّق من انتمائه للتينانت، والعمود `unique` عالميًا → مستخدم في تينانت آخر يمكن "حجز" ملفه (منع إنشاء الملف الحقيقي).
- **الإصلاح المقترح:** النمط المرجعي. **إضافة اختيارية (D2):** التحقق أن `data.user_id` ينتمي لتينانت المستدعي.

---

## 3) اكتشافات جانبية (داخل insurance، خارج الـ5 — لم تُلمَس)

| # | الموقع | الوصف |
|---|---|---|
| S1 | `subscribe` (router:103) — **يحرّك فلوس** | نفس ثغرة الهيدر بالضبط (`tenant.id` router:113) |
| S2 | `submit_claim` (router:187) | نفس ثغرة الهيدر (router:197) |
| S3 | `get_my_subscriptions` (router:120) | نفس الثغرة (router:133) — قراءة |
| S4 | `renew_subscription`, `get_my_claims`, `get_my_pensions`, `get_my_employee_profile` | يعلنون `tenant` من الهيدر لكن لا يستخدمونه — خطر صفري حاليًا، ديون تنظيف |
| S5 | `review_claim` | المراجِع يدفع التعويض من **محفظته الشخصية** (`sender_id=reviewer_id`) بدل حساب النظام — قرار تصميم مشكوك فيه، ليس عزل تينانت |
| S6 | `service.create_pension/create_employee_insurance_profile` | `data.get("tenant_id", 1)` fallback على 1 في `audit_log` — لا يُفعَّل عمليًا لأن الراوتر يمرر tenant_id دائمًا |

(لا اكتشافات خارج دومين insurance حتى الآن.)

---

## 4) قرارات مطلوبة من المستخدم قبل أي تنفيذ

- **D1:** `disburse_pensions` — الطبقة (أ) فقط، أم (أ)+(ب)؟ *التوصية: (أ)+(ب)، لأن (أ) وحدها لا تسمح بأي إثبات حي للسيناريو المشروع.*
- **D2:** إضافة التحقق أن `beneficiary_id`/`user_id` ينتميان لتينانت المستدعي (في `create_pension`/`create_employee_profile`)؟ *التوصية: نعم.*
- **D3:** ضم S1-S3 (`subscribe`, `submit_claim`, `get_my_subscriptions`) لنفس الجلسة، أم تركها Batch 0-B؟ *التوصية: ضمّها — نفس الإصلاح الميكانيكي، و`subscribe` تحرّك فلوس.*

## 5) خطة التحقق الحي (بعد الموافقة)
- تينانتان throwaway (A و B)، لكل منهما: superuser + مستخدم مستفيد + محفظة + كيان سيادي + عضوية OWNER + بوليصة/اشتراك/مطالبة + معاش ACTIVE.
- **قبل:** (1) هيدر `X-Tenant-ID: B` من A على `create_policy/create_pension/create_employee_profile/review_claim` → إثبات الكتابة/الصرف في B؛ (2) `disburse` كـA → إثبات أن B لم يتأثر (متوقع: `count=0` لكلا التينانتين — كامنة، يُوثَّق بصدق).
- **بعد:** نفس الهجمات → 403/404؛ سيناريو مشروع (كل تينانت على بياناته) → ينجح؛ `SELECT` مستقل بعد كل خطوة.
- تنظيف كامل + فحص مستقل لصفر residue.

## 6) سجل التنفيذ
- [2026-09-21] قراءة مكتملة، تشخيص مكتمل. ✅ استلام D1/D2/D3.
- [2026-09-21] المرحلة 3 (قبل الإصلاح) مكتملة — التفاصيل في §7. تنظيف كامل مؤكَّد (§8). ⏸️ بانتظار الضوء الأخضر للمرحلة 4.

---

## 7) المرحلة 3 — التحقق الحي قبل الإصلاح (النتائج)

**البيئة:** `uvicorn` محلي منفذ 8000 (أُوقف بعد الانتهاء)، DB `eppne_v2` على `localhost:5435`. تينانتان throwaway جديدان **A=124، B=125** (كل واحد: SUPER_ADMIN + عضو مشترك + مستفيد + موظف + كيان سيادي + عضوية OWNER + اشتراك SaaS للخطة 101 + بوليصتان + اشتراك + مطالبة + معاشان ACTIVE)، أرصدة 500 MR_USDT للأدمن والعضو. **المهاجم = أدمن/عضو تينانت A بتوكنه الحقيقي + هيدر `X-Tenant-ID: 125`.** الأدلة الخام الكاملة: `.claude/reports/insurance-batch0a-evidence-before.txt`.

**بيانات إضافية مزروعة عمدًا:** بوليصة في تينانت B مُصدِرها كيان تينانت A (حالة تنتج فعليًا عن هجوم `create_policy` أولًا) — لأن `review_claim` عنده فحص عضوية يحمي جزئيًا، فهجوم المراجعة لا يمر إلا لو المهاجم عضو في الكيان المُصدِر.

### 7.1 الهجمات (قبل الإصلاح)
| # | الهجوم | HTTP | أثر مؤكَّد بـ`SELECT` مستقل |
|---|---|---|---|
| 1 | `create_policy` (أدمن A + هيدر B) | **201** | بوليصة id=629 `tenant_id=125` (B) ✅ استُغلت |
| 2 | `review_claim` رفض مطالبة B | **200** | مطالبة 157 `tenant_id=125` صارت `REJECTED` بواسطة مستخدم تينانت A ✅ |
| 3a | `create_pension` مستفيد B | **201** | معاش 60 `tenant_id=125` ✅ |
| 3b | `create_pension` مستفيد A بهيدر B | **201** | معاش 61 `tenant_id=125` لمستفيد من تينانت A ✅ |
| 4 | `create_employee_profile` لموظف B | **201** | ملف 54 `tenant_id=125` ✅ |
| 5a | `subscribe` بوليصة B مجانية (premium=0) | **201** | اشتراك 346 `tenant_id=125` لمستخدم A ✅ |
| 5b | `subscribe` بوليصة B مدفوعة (10 USDT) | **403** "Insufficient balance" | لا اشتراك، لا تغيّر أرصدة. **هذا حاجز طبيعي (محفظة B للمهاجم فارغة لأن المحفظة per-tenant) وليس حماية — الإصلاح لا يعتمد عليه.** |
| 6 | `submit_claim` على اشتراك 346 (تينانت B) | **500** | وصل حتى `INSERT` بـ`tenant_id=125` (`Failing row contains (158, 125, ...)` في لوج السيرفر) — أي اجتاز كل فحوص التينانت/الملكية. الـ500 سببه باج منفصل (§9-F1) |
| 7 | `get_my_subscriptions` (هيدر B) | **200** | رجّع اشتراك 346 (تينانت B) لمستخدم A ✅ |

### 7.2 السيناريوهات المشروعة (تينانت A، هيدر A) — تعمل قبل الإصلاح
- `create_policy` 201 (tenant 124) ✅ — `subscribe` مدفوعة 201: **member_A 500→490، premium_receiver_A 0→10** ✅ (money) — `review_claim` approve=20: **PAID، admin_A 500→480، member_A 490→510**، `payout_tx_hash=TX-EAC1C8F3023D` ✅ (money) — `create_pension` 201 ✅ — `create_employee_profile` 201 ✅ — `get_my_subscriptions` 200 ✅.
- `submit_claim` **500 حتى للسيناريو المشروع** (نفس باج §9-F1) — لا يمكن التحقق منه في الاتجاه المشروع.

### 7.3 `disburse_pensions` (D1 — تحقق معدَّل)
- 7 معاشات ACTIVE عبر التينانتين (56،57،62 → A؛ 58،59،60،61 → B).
- `POST /insurance/admin/disburse-pensions` (أدمن A) → **200 `{"message":"Disbursed 0 pensions","count":0}`**؛ المعاشات كلها بلا تغيير (`total_disbursed=0`, `last_payout_tx=NULL`)، **كل الأرصدة بلا تغيير، ومحفظة user 1 (`710.0`) بلا تغيير.**
- الاستعلام القديم `list_pensions_for_beneficiary(None, ACTIVE)` → **`[]`** رغم وجود 7 صفوف ACTIVE فعلًا (تأكيد حي لـ`IS NULL` على عمود NOT NULL).
- `list_active_pensions` غير موجودة بعد. (سيُثبَت العزل في المرحلة 4 بـ: `list_active_pensions(A)` = معاشات A فقط، `(B)` = B فقط، تينانت غير موجود = `[]`.)

---

## 8) التنظيف بعد المرحلة 3
حُذفت كل بيانات throwaway (تينانتان + 10 مستخدمين + كل الصفوف المرتبطة). **صفان في جدول `transactions`** (id=921 قسط 10، id=922 تعويض 20 — بين مستخدمي throwaway فقط) لا يملك الجدول `tenant_id` فمنعا حذف المستخدمين بـFK؛ عُرِّفا بـ`SELECT` أولًا (بالاسم `TMPINS_POLICY_A1_e35b40`) ثم حُذفا بالـid. **تحقق نهائي مستقل:** مقارنة لقطة `count(*)` لكل الـ259 جدولًا (قبل/بعد) → **صفر فرق**، ومحفظة user 1 مطابقة، وصفر مستخدمين/تينانتات `TMPINS*`. (تسلسلات الـid تقدمت فقط — لا أثر وظيفي.)

---

## 9) اكتشافات جديدة أثناء المرحلة 3 (لم تُصلَح)
- **F1 — `insurance.submit_claim` معطوب دائمًا (500) — باج مسبق غير متعلق بالتينانت:** `service.py:407` يبني `create_claim(**{k: v for k, v in data.items() if k not in ["incident_description", "subscription_id"]})` فيستبعد `subscription_id` نفسه → `NotNullViolationError` على `insurance_claims.subscription_id` (مؤكَّد بتشغيل الدالة مباشرة). يعني: `submit_claim` لا يعمل لأي مستخدم في أي تينانت اليوم. **صفر لمس** (خارج نطاق D1-D3). يستدعي قرارًا: بند backlog منفصل `insurance-submit-claim-subscription-id-dropped` (أولوية عالية — endpoint مكسور بالكامل). *تبعية على التحقق:* سيُثبَت إصلاح `submit_claim` في اتجاه الهجوم فقط (404 بدل الوصول للـINSERT)؛ الاتجاه المشروع غير قابل للتحقق حيًا لحين إصلاح F1.
- **F2 — سلوك المحفظة per-tenant يُعطِّل هجمات `subscribe`/`review(approve)` المدفوعة عرضيًا** (المهاجم يحتاج رصيدًا في تينانت الضحية). حاجز عرضي، مش دفاع.
- **F3 — (خارج insurance) أثناء بدء السيرفر:** لوج `UnicodeEncodeError` (cp1256) عند طباعة رسائل عربية/إيموجي، ومحاولة `CREATE INDEX ... transactions (user_id, ...)` تفشل (`column "user_id" does not exist`). موثَّقان فقط، لم يُلمَسا.

> **تحديث المرحلة 4:** تنظيف §8 لتينانتَي 124/125 تمّ بالفعل في نهاية المرحلة 3 (قبل طلب المستخدم "احذف 124/125 فقط"). التينانتات الحالية من المرحلة 4 هي **126/127 (before2) و128/129 (after)** — انظر §12.

---

## 10) المرحلة 4 — الإصلاح (الكود)

**شرط 1 (سبب 500 في `submit_claim`) — الجواب قبل أي لمس:** من لوج السيرفر: `NotNullViolationError: null value in column "subscription_id" of relation "insurance_claims"` — السبب `service.py:403-408`: `create_claim(**{k: v ... if k not in ["incident_description", "subscription_id"]})` يستبعد `subscription_id` صراحة. **ليس** من سطر tenant-from-header → **لم يُصلَح**. طُبِّق جزء عزل التينانت فقط على `submit_claim`. البند: `insurance-submit-claim-500`. **`submit_claim` لا يمكن التحقق منه حيًا في الاتجاه المشروع** (LEGIT-6 = 500 قبل وبعد، ومتوقَّع).

**الملفات المُعدَّلة (كلها داخل `insurance/`؛ صفر migration):**
| الملف | التعديل |
|---|---|
| `router.py` | 8 endpoints: `create_policy`, `subscribe`, `get_my_subscriptions`, `submit_claim`, `review_claim`, `create_pension`, `disburse_pensions`, `create_employee_profile` — حذف `tenant: AcademyTenant = Depends(get_current_tenant)`، إضافة `tenant_id = cast(int, current_user.tenant_id)` كأول سطر، استبدال `tenant.id`. (نفس نمط ai_agents حرفيًا.) |
| `service.py` | `disburse_monthly_pensions(tenant_id)` (معامل إجباري، مستدعٍ وحيد)، يستخدم `list_active_pensions`، فحص دفاعي `pension.tenant_id != tenant_id`، `FinanceService(self.db, tenant_id)`. **D2:** `create_pension` يرفض (`NotFoundError` → 404) لو `beneficiary_id` ليس من تينانت المستدعي؛ `create_employee_insurance_profile` نفس الشيء لـ`user_id` (عبر `_get_user` الموجودة → `UserRepository.get_by_id(…, tenant_id)`). |
| `repository.py` | دالة **جديدة** `list_active_pensions(tenant_id)` (فلتر `tenant_id` + `ACTIVE`)؛ `list_pensions_for_beneficiary` **لم تُلمَس**. |
| `tests/test_insurance_batch0a_tenant_isolation.py` | جديد — regression دائم (2 test، مرّا مرتين، صفر residue). |

**لم يُلمَس عمدًا:** كل الـ4 sub-bugs الخاصة بمنطق الصرف (`sender_id=1`، `idempotency_key` غائب، `last_payout_tx=tx`، `_get_payout_date`)؛ `review_claim` يدفع من محفظة المراجِع الشخصية؛ الـ4 `tenant` dependencies غير المستخدمة (`renew_subscription`, `get_my_claims`, `get_my_pensions`, `get_my_employee_profile`) — لا تزول طبيعيًا بالإصلاح (والاستيرادان `get_current_tenant`/`AcademyTenant` باقيان بسببها).

---

## 11) المرحلة 4 — التحقق الحي: قبل/بعد جنبًا إلى جنب

**القبل الأقوى (`before2`، تينانتات 126/127، كود غير مُصلَح):** أُضيف رصيد 500 لمحفظة `member_A` **داخل تينانت B** (شرط 2) ليصير الاشتراك المدفوع قابلًا للنجاح لو الثغرة موجودة. **البعد (`after`، تينانتات 128/129، كود مُصلَح):** نفس البيانات ونفس السيناريوهات حرفيًا. أدلة خام: `insurance-batch0a-evidence-before.txt` (الأول، 124/125)، `…-before2-funded-ghost-wallet.txt`، `…-after.txt`.

| السيناريو (مهاجم تينانت A + هيدر B) | قبل (before2) | بعد (after) |
|---|---|---|
| 1 `create_policy` | 201، الصف في **تينانت B** | **الهيدر مُتجاهَل — حُلَّ لتينانت المستدعي (128 = A)**؛ 201 مشروع لبوليصة في تينانت A نفسه، لا شيء في B (§13-أ) |
| 2 `review_claim` رفض مطالبة B | 200 → `REJECTED` | **404** "Claim not found" — المطالبة بقيت `SUBMITTED` |
| 3a `create_pension` مستفيد B | 201 في B | **404** "Beneficiary not found" (D2) — لا صف |
| 3b `create_pension` مستفيد A بهيدر B | 201 في **B** | **الهيدر مُتجاهَل — حُلَّ لتينانت المستدعي (128 = A)**؛ 201 مشروع لمعاش مستفيد A داخل تينانت A، لا صف في B (§13-أ) |
| 4 `create_employee_profile` لموظف B | 201 في B | **404** "Employee user not found" (D2) — لا صف |
| 5a `subscribe` مجاني على بوليصة B | 201 في B | **404** "Policy not found or inactive" — لا صف |
| **5b `subscribe` مدفوع (10 USDT) على بوليصة B** | **201؛ محفظة member_A في B: 500→490، مستلم القسط في B: 0→10، اشتراك في تينانت B** (تحريك فلوس حقيقي عابر للتينانت) | **404**؛ **كل الأرصدة في التينانتين بلا تغيير** (member_A@B = 500، مستلم B = None)، لا اشتراك في B |
| 6 `submit_claim` على اشتراك B | 500 (وصل لـ`INSERT` في B) | **404** "Subscription not found" (ثبت الحاجز قبل الوصول للـINSERT) |
| 7 `get_my_subscriptions` | 200 يرجّع اشتراكات B (346) | **الهيدر مُتجاهَل — حُلَّ لتينانت المستدعي (128 = A)**؛ 200 يرجّع اشتراك 354 وهو اشتراك تينانت A نفسه (§13-أ) |
| Ghost-wallet (عدد محافظ تينانت B + محافظ مستخدمي A داخل B) | `unchanged: False` (member_A: 500→490) | **`unchanged: True`** — 6 صفوف قبل/بعد، لا محفظة جديدة، `member_A@B` = 500 |
| بدون هيدر `X-Tenant-ID` إطلاقًا | — | 200، يعمل بتينانت التوكن |

| السيناريو المشروع (تينانت A) | قبل | بعد |
|---|---|---|
| `create_policy` | 201 | 201 |
| `subscribe` مدفوع | 201، member 500→490، مستلم 0→10 | 201، member 500→490، مستلم 0→10 (مطابق) |
| `review_claim` approve 20 | 200 `PAID`، admin 500→480، member +20 | 200 `PAID`، admin 500→480، member +20 (مطابق) |
| `create_pension` / `create_employee_profile` / `get_my_subscriptions` | 201 / 201 / 200 | 201 / 201 / 200 |
| `submit_claim` | **500** (F1) | **500** (F1 — نفس السبب، لم يُصلَح، غير قابل للتحقق) |

**`disburse_pensions` (D1):**
- **بعد:** `POST /admin/disburse-pensions` كأدمن A → 200 `count=0`؛ **وكذلك بهيدر B مزوَّر** → 200 `count=0`؛ المعاشات بلا تغيير (`total_disbursed=0`, `last_payout_tx=NULL`)؛ الأرصدة بلا تغيير؛ **محفظة user 1 = 710.0 بلا تغيير**؛ عدد صفوف `transactions` بـ`notes LIKE 'Pension payment%'` = 0 قبل وبعد الاستدعاء (شرط 3: الاستعلام مُصحَّح — لا `tenant_id` في `transactions` — واستُبدل بـ`notes`/`sender_id`/إجمالي عدد الصفوف).
- **عزل الاستعلام (in-process، بعد):** 6 معاشات ACTIVE عبر 128/129: `list_active_pensions(128)` = `[74,75,70,71]` (كلها 128، `leaks_other_tenant=False`)، `list_active_pensions(129)` = `[72,73]`، `list_active_pensions(999999)` = `[]`. الاستعلام القديم لا يزال `[]` (لم يُلمَس).
- ⚠️ **أثر جانبي مهم يُوثَّق:** الإصلاح جعل حلقة الصرف **تصل لأول مرة** لمعاشات حقيقية. لكن `finance.transfer(...)` بلا `idempotency_key` (معامل إجباري) يرمي `TypeError` **عند الاستدعاء قبل أي أثر**، و`except Exception: pass` يبلعه → `count=0` ولا فلوس تتحرك (مؤكَّد أعلاه). **أي إصلاح لاحق للـ`idempotency_key` وحده سيجعل `sender_id=1` هاردكودد يصرف فعلًا من محفظة user 1** — لذلك البند التالي أولوية عالية.

**Regression:** اختبارات insurance (`test_insurance_entity_membership_gap_fix`, `…getter_endpoints_wiring`, `…policy_response_null_issuer`, `test_saas_active_subscription -k insurance`, `test_user_repository_get_by_id_audit -k insurance`/`disburse`) → **كلها نجحت إلا واحد مسبق**: `test_insurance_get_user_and_get_user_email_all_three_call_paths` يفشل في السطر 569 (`assert any("referred_by" in r ...)` على `_register_affiliate_commission` — دالة **لم أمسها**، حالة Backlog #10 المعروفة؛ حُكم بالفحص لا بالتشغيل على كود نظيف). وفشل واحد في `test_realestate_insurance_savepoint.py::…buy_fractional_ownership_invoice_ordering` (فحص نصي على `realestate/service.py` — ملف لم أمسه). ⚠️ أثناء الجلسة كسر تعديلي أول نسخة سطرًا نصيًا في `test_user_repository_get_by_id_audit.py` (تأكيد على نص `cast(int, pension.tenant_id)` داخل `disburse_monthly_pensions`)؛ **أعدت السطر لصيغته الأصلية** (متكافئ دلاليًا بسبب الفحص الدفاعي) بدل تعديل الاختبار، وأعدتُ التشغيل — التأكيد النصي يمر.

---

## 12) اكتشافات المرحلة 4 (لم تُصلَح) وحالة التنظيف

**بنود backlog جديدة (تُسجَّل في `PROGRESS_LOG.md`):**
- 🔴 **`insurance-disburse-pensions-payout-logic-broken`** (أولوية عالية، بند واحد): (1) `finance.transfer` بلا `idempotency_key` → TypeError مبلوع، (2) `sender_id=1` هاردكودد (الدافع؛ قرار منتج: من يدفع؟)، (3) `last_payout_tx=tx` كائن في عمود `String(100)`، (4) `_get_payout_date` ترجع `utcnow()` دائمًا → "دُفع هذا الشهر" للأبد لأي معاش له `last_payout_tx`. + `except Exception: pass` يخفي كل ذلك. ⚠️ ترتيب الإصلاح مهم (لا تُصلَح (1) قبل (2)).
- 🔴 **`insurance-submit-claim-500`**: `service.py:407` يستبعد `subscription_id` من `create_claim(...)` → `NotNullViolationError`؛ endpoint مكسور تمامًا لأي مستخدم. (بند الاسم في الرسالة: `insurance-submit-claim-500`.)
- 🟡 ~~`insurance-review-claim-pays-from-reviewer-personal-wallet`~~ **[تصحيح اسم — §14-ج]:** هذا الاسم كان خطأ مني؛ البند **موجود أصلًا** في `PROGRESS_LOG.md` باسم `insurance-review-claim-payout-from-reviewer-personal-wallet` (سطر ~261). **لن يُنشأ بند جديد** — يُلحَق به سطر تحديث مؤرَّخ فقط (design smell، موثَّق بأمر المستخدم).
- 🟡 **`insurance-unused-tenant-header-dependencies`** (4 endpoints: `renew_subscription`, `get_my_claims`, `get_my_pensions`, `get_my_employee_profile`).
- ⚪ خارج insurance (لم تُلمَس): F3 (لوج cp1256 + `CREATE INDEX transactions(user_id...)` يفشل عند بدء السيرفر).

**حالة التنظيف:** ✅ **نُفِّذ لاحقًا بعد موافقة المستخدم — التفاصيل والنتائج في §14-أ** (الوصف التالي تاريخي: كان معلَّقًا وقت كتابة هذا القسم). (تحقق §13-د: تينانتا 124/125 محذوفان فعلًا، فنطاق التنظيف = 126–129 فقط.) المتبقي في DB: تينانتات throwaway **126/127/128/129** (20 مستخدمًا + كل بياناتها) + **5 صفوف في `transactions`** (ids 923–927، كلها بين مستخدمي throwaway، `notes` تحمل `TMPINS_POLICY_*`). محفظة user 1 الآن = **710.0** (بلا تغيير عن القيمة قبل الجلسة).

---

## 13) توضيحات مراجعة المستخدم (بعد مراجعة أدلة ما-بعد-الإصلاح)

### أ) الحالات الثلاث التي ظهرت 201/200 بعد الإصلاح — ليست هجمات فاشلة، بل "الهيدر مُتجاهَل"
**الحقائق المؤكَّدة بـ`SELECT` مستقل على DB (تينانتا المرحلة 4: A=128، B=129):** المهاجم `admin_A` (id=13514) و`member_A` (id=13515) كلاهما `users.tenant_id = 128`.

| الحالة | ما رجع | `tenant_id` الفعلي في DB | التفسير |
|---|---|---|---|
| ATTACK-1 `create_policy` + هيدر `X-Tenant-ID: 129` | 201، `id=643` | **128** (= A، تينانت المستدعي الحقيقي). كيان المُصدِر 1143 أيضًا `tenant_id=128` | الهيدر **لم يُقرأ**؛ السيرفر حلّ التينانت من التوكن (`current_user.tenant_id`) فأنشأ بوليصة مشروعة في تينانت المستدعي. `SELECT` بالاسم `TMPINS_ATTACK_POLICY_after` يرجّع الصف 643 فقط، وهو في 128. **صفر بوليصة في 129.** (قبل الإصلاح: نفس الطلب كتب في تينانت B.) |
| ATTACK-3b `create_pension` (مستفيد A) + هيدر 129 | 201، `id=74` | **128** (مستفيد `13516` = `benef_A`، تينانت A) | نفس التفسير. `SELECT` على `pension_type LIKE 'TMPINS_ATK_%_after'` يرجّع الصف 74 فقط (في 128)؛ **صفر معاش ATK في 129**. (لاحظ: 3a — مستفيد B — رجع 404 بفضل D2.) |
| ATTACK-7 `get_my_subscriptions` + هيدر 129 | 200، `[354]` | الاشتراك **354: `tenant_id=128`**, `policy_id=638` (بوليصة A)، `subscriber_user_id=13515` (= `member_A` نفسه) | 354 هو **اشتراك A المزروع أصلًا** لـ`member_A` في تينانت A. لم يرجع أي اشتراك من تينانت B (اشتراك B هو 355 → `tenant_id=129` ولم يظهر). (قبل الإصلاح: رجع 346 = اشتراك تينانت B.) |

**التصنيف الصحيح لهذه الثلاث:** ✅ **"الهيدر مُتجاهَل، حُلَّ لتينانت المستدعي"** (blocked-by-resolution)، **لا** "هجمات نجحت" ولا "فاشلة". النتيجة الوحيدة الممكنة بعد الإصلاح لطلب من تينانت A هي التعامل مع تينانت A. الدليل الإضافي: `AFTER extra` (طلب بلا هيدر أصلًا) رجع نفس السلوك، و`disburse` بهيدر مزوَّر 129 نفّذ على تينانت 128.

### ب) `submit_claim` — 500 في LEGIT-6: الـtraceback والسبب
**لوج السيرفر (`uvicorn_after.log`، الطلب `POST /api/insurance/claims` من `member_A`، تينانت 128):**
```
File ".../insurance/router.py", line 195, in submit_claim        -> claim = await service.submit_claim(
File ".../insurance/service.py", line 402, in submit_claim       -> claim = await self.repo.create_claim(
File ".../insurance/repository.py", line 113, in create_claim    -> await self.db.flush()
sqlalchemy.exc.IntegrityError: NotNullViolationError: null value in column "subscription_id"
  of relation "insurance_claims" violates not-null constraint
[SQL: INSERT INTO insurance_claims (tenant_id, idempotency_key, subscription_id, claimant_user_id, ...)]
[parameters: (128, None, None, 13515, ..., 'TMPINS legit claim after', '[]', Decimal('12'), 0, 'SUBMITTED', ...)]
```
**السبب الجذري:** `service.py:403-408` يبني `create_claim(**{k: v for k, v in data.items() if k not in ["incident_description", "subscription_id"]})` — يستبعد `subscription_id` صراحة، فيُدرَج `NULL` في عمود `NOT NULL`.
**لا علاقة له بعزل التينانت:** `tenant_id` في الـINSERT سليم (128 = تينانت المستدعي)، والخطأ عمود آخر تمامًا. ✅ مؤكَّد.
**الحالة:** ❌ **لم يُصلَح** عمدًا. مُسجَّل كبند `insurance-submit-claim-500` (§12 + `PROGRESS_LOG.md`).
**⚠️ تصريح صريح: مسار نجاح `submit_claim` (الحالة المشروعة) لم يتحقق منه حيًا ولا يمكن تحقيقه حتى إصلاح `insurance-submit-claim-500`** — 500 قبل وبعد. المُثبَت فقط: (1) الاتجاه الهجومي بعد الإصلاح = 404 "Subscription not found" (يُحجَب قبل الوصول للـINSERT)، (2) قبل الإصلاح الطلب المزوَّر وصل للـINSERT بـ`tenant_id=125`. صحة تعديل الراوتر لـ`submit_claim` (السطر `tenant_id = cast(int, current_user.tenant_id)`) مبنية على الاتجاه الهجومي + التطابق الميكانيكي مع الـ7 endpoints الأخرى المُتحقَّق منها.

### ج) `git diff` لدومين insurance — مصدر كل hunk
**الحالة الأساسية (قبل جلستي، من `git status` بداية الجلسة و`git diff --stat` قبل أي تعديل):** ملفات insurance كانت أصلًا **معدَّلة وغير committed** من جلسات سابقة: `models.py` (2 سطر)، `router.py` (1)، `schemas.py` (1)، `service.py` (19). ومن `git log`: آخر commit يمس الدومين `b77b319` لا يحتوي هذه التعديلات.
**فرق الإحصاء (بعد − قبل) = تعديلاتي فقط:** `router.py` +32، `service.py` +21، `repository.py` +8، + ملف اختبار جديد غير مُتتبَّع.

| hunk | مصدره |
|---|---|
| `models.py` `issuer_entity_id` → `SET NULL`/`nullable=True` | **سابق** — جلسة `insurance-entity-membership-gap-fix` (migration 049) |
| `schemas.py` `issuer_entity_id: Optional[int] = None` | **سابق** — جلسة `insurance-policy-response-schema-fix` |
| `router.py` `update_policy`: `reviewer_id=cast(int, current_user.id)` | **سابق** — `insurance-entity-membership-gap-fix` (§ تقريرها سطر 86-93) |
| `service.py` `create_policy` (فحص عضوية) + `update_policy` (`reviewer_id` + فحص عضوية) | **سابق** — نفس جلسة gap-fix |
| `router.py` ×8 endpoints (حذف `tenant` dependency + `tenant_id = cast(int, current_user.tenant_id)`) | **جلستي** |
| `service.py` `create_pension` D2 (3 أسطر) | **جلستي** |
| `service.py` `create_employee_insurance_profile` D2 (3 أسطر) | **جلستي** |
| `service.py` `disburse_monthly_pensions(tenant_id)` + فحص دفاعي + `FinanceService(self.db, tenant_id)` | **جلستي** (الطبقة أ) |
| `repository.py` `list_active_pensions` (دالة جديدة) | **جلستي** |
| `tests/test_insurance_batch0a_tenant_isolation.py` | **جلستي** (ملف جديد) |

**لا تعديلات جانبية:** لم أمس منطق الصرف (`sender_id=1` وباقي الـ4)، ولا `submit_claim` الداخلية، ولا `review_claim` الداخلية، ولا الـ4 dependencies غير المستخدمة، ولا `list_pensions_for_beneficiary`. تنسيق/مسافات: صفر تغيير.

### د) تينانتا 124/125 (مرحلة ما قبل الإصلاح الأولى)
فحص للقراءة فقط: عدد صفوف `tenant_id IN (124,125)` عبر **كل الـ211 جدولًا** التي فيها عمود `tenant_id` + `academy_tenants` → **صفر صف** لكليهما، وصفر صف في `transactions` مرتبط بمستخدميهما. ✅ **مُنظَّفان فعلًا** (نُظِّفا في نهاية المرحلة 3 وقُورن بلقطة الـ259 جدولًا: صفر فرق). **التينانتات المتبقية فعلًا:** 126 (5 users)، 127 (5)، 128 (5)، 129 (5) = 20 مستخدمًا + 5 صفوف `transactions` (ids 923–927). **أوامر التنظيف المقترحة لا تتغير** (تستهدف 126–129 + ids 923–927).

---

## 14) ما بعد الموافقة على التنظيف (2026-09-21)

### أ) التنظيف — نُفِّذ بالأوامر المعتمَدة
```
1) DELETE FROM transactions WHERE id IN (923,924,925,926,927) AND notes LIKE '%TMPINS_POLICY%'   -> DELETE 5
2) cleanup.py 126 127 128 129   -> حذف صفوف من الجداول ذات tenant_id (audit_logs 5، auth_refresh_tokens 4،
   employee_insurance_profiles 3، entity_memberships 4، insurance_claims 6، insurance_subscriptions 10، invoices 5،
   pension_records 13، saas_tenant_service_access 4، saas_tenant_subscriptions 4، sovereign_entities_v2 4، wallets 22،
   insurance_policies 14، users 20) ثم academy_tenants 4
3) snapshot لكل الجداول ومقارنته بلقطة ما قبل أي بيانات من الجلسة
```
**(أ) الفرق:** `tables compared: 259 | DIFF: ZERO-DIFF across all 259 tables` — لا جداول جديدة/مفقودة.
**(ب) محفظة user 1:** `wallets.id=39` → `MR_USDT = 710.0` (مطابقة لقيمتها قبل الجلسة: `[[39, 1, {'MR_USDT': 710.0}]]`). صفر مستخدمين/تينانتات `TMPINS*`، صفر معاشات `REGTEST_BATCH0A`. (تنظيف تينانتات 124/125 كان قد تمّ في نهاية المرحلة 3، تأكيد §13-د.)

### ب) إثبات أن فشلَي الاختبارين "مسبقان" — بالتشغيل على baseline نظيف (وليس بالفحص)
**الطريقة:** `git worktree` منفصل (detached) على `HEAD = 6f68cb4` مع checkout لمجلد `eppne-backend` فقط (لم أستخدم `git stash` لأن شجرة العمل فيها 163 مدخلًا غير committed من جلسات عديدة ولا أريد لمسها)، مع نسخ `.env`. تحققتُ أن الـworktree يستورد كوده هو (`app imported from: …\wt_head\eppne-backend\app`)، وأنه baseline فعلًا: صفر `list_active_pensions`، و12 dependency هيدر-تينانت في `insurance/router.py` (الحالة الأصلية)، وصفر ملف معدَّل. **ملفا الاختبار tracked وغير معدَّلين** (`git status` لا يُظهر `M` لهما)، فالفرق الوحيد بين baseline والشجرة الحالية هو كود التطبيق.

| الاختبار | baseline نظيف (HEAD `6f68cb4`) | الشجرة الحالية (بعد تعديلاتي) |
|---|---|---|
| `test_user_repository_get_by_id_audit.py::test_insurance_get_user_and_get_user_email_all_three_call_paths` | ❌ FAIL — `assert any("referred_by" in r for r in cap.records)` (السطر 569) | ❌ FAIL — **نفس التأكيد بالحرف، نفس السطر 569** |
| `test_realestate_insurance_savepoint.py::test_realestate_buy_fractional_ownership_invoice_ordering` | ❌ FAIL — `assert 1277 < 928` (`create_invoice()` خارج `try/except`، السطر 159) | ❌ FAIL — **نفس التأكيد بالحرف، `1277 < 928`** |

**الخلاصة:** ✅ الفشلان **مسبقان مُثبَتان بالتشغيل** ولا علاقة لهما بـBatch 0-A (الأول: حالة Backlog #10 المعروفة لـ`referred_by` في `_register_affiliate_commission`؛ الثاني: فحص نصي على `realestate/service.py`). يُصحِّح هذا حكمي السابق في §11 ("حُكم بالفحص لا بالتشغيل"). *(أما التأكيد النصي الذي كسرتُه أنا فعلًا أثناء الجلسة — `cast(int, pension.tenant_id)` — فقد أُصلح بإرجاع السطر، ولا علاقة له بهذين الفشلين.)*
**استعادة الشجرة:** `git worktree remove --force` + `git worktree prune`؛ `git worktree list` → الشجرة الرئيسية فقط؛ `git status --porcelain` **مطابق حرفيًا** للقطة بداية الجلسة (163 سطرًا)؛ `git stash list` = 0؛ staged = 0. وأعدتُ لقطة الـDB بعد تشغيلات الاختبار → **ZERO-DIFF على 259 جدولًا** ومحفظة user 1 = 710.0.

### ج) قرارات الأسماء ومنع التكرار في `PROGRESS_LOG.md` (لم تُكتب بعد — بانتظار موافقة النص)
| البند | القرار |
|---|---|
| مشكلة `review_claim` تدفع من محفظة المراجِع | **لا بند جديد.** البند الموجود `insurance-review-claim-payout-from-reviewer-personal-wallet` (سطر ~261): يُلحَق به سطر تحديث مؤرَّخ واحد فقط. اسم §12 القديم كان خطأ. |
| `submit_claim` | **اسم واحد فقط:** `insurance-submit-claim-500`، وفيه: "عند إصلاح F1 أعِد التحقق الحي العابر للتينانت على المسار المشروع، لأن العزل أُثبت على مسار الهجوم فقط". |
| `insurance-disburse-pensions-payout-logic-broken` | 3 أعطال جديدة فقط؛ `sender_id=1` **إحالة** إلى `finance-transfer-hardcoded-system-account-real-fund-risk` (تحديث 2026-09-16) بلا إعادة توثيق؛ **نص صريح:** قرار الدافع يُحسَم **قبل** إصلاح `idempotency_key` وإلا صرف من user 1؛ نفس التحذير في بانر الحالة. |
| تصحيح وصف بند 2026-09-16 (`insurance-disburse-pensions-hardcoded-system-account`) | **سطر جديد مؤرَّخ** يُلحَق أسفل البند (بعد سطر 4272) — **لا إعادة كتابة** للنص القديم. |
| الـ4 dependencies غير المستخدمة | سطر واحد documented-only |

### د) اقتراح تقسيم الـcommits (اقتراح فقط — لم يُنفَّذ أي commit)
**المشكلة:** ملفا `router.py` و`service.py` يحويان hunks من جلسة gap-fix السابقة **ومن جلستي** في نفس الملف؛ و`models.py`/`schemas.py` كاملان من جلسات سابقة؛ و`repository.py` كامل من جلستي.
**إثبات الجدوى (بلا commit):** قسّمتُ `git diff HEAD` hunk-بـhunk (router: hunk 2 فقط سابق؛ service: hunk 1+2 سابقان) في worktree مؤقت، ثم طبّقتُ المجموعة "أ" على HEAD (نتيجتها بالإحصاء = `models 2، router 1، schemas 1، service 19` — **مطابقة تمامًا للأرقام التي سجّلتُها قبل أي تعديل مني**، دليل مستقل على الإسناد)، ثم "ب" فوقها → الملفات الخمسة **IDENTICAL** للشجرة الفعلية. أُزيل الـworktree. ملفات الـpatch محفوظة في `.claude/reports/insurance-batch0a-commit-split/` (`patchA_whole`، `patchA_shared`، `patchB_whole`، `patchB_shared`).

**⚠️ اعتماد ترتيبي مهم:** migration `049` (insurance) `down_revision = 048_add_cancelled_at_to_saas_tenant_subscriptions`، و**`048` غير tracked** (من جلسة saas أخرى، وباقي 050+ تتسلسل بعد 049). فـcommit "أ" **ليس مكتفيًا ذاتيًا** لو سبق `048` — يلزم commit 048 (مع تغييرات saas المرتبطة به، خارج نطاقي) قبله، أو ضمّه معه.

**الفهرس فارغ حاليًا (0 staged)** — فلا خطر "ملفات غريبة تركب مع الـcommit"؛ يُتحقَّق منه قبل كل commit بـ`git diff --cached --stat`.

**Commit 0 (شرط مسبق، ليس من عملي):** `048_add_cancelled_at_to_saas_tenant_subscriptions.py` + كود saas المرتبط به (يقرره صاحب تلك الجلسة/المستخدم).
**Commit A — عمل insurance السابق (gap-fix + schema-fix)، 14 ملفًا:**
`git apply --cached` لـ`patchA_whole` (models.py + schemas.py كاملان) و`patchA_shared` (router.py hunk 2، service.py hunks 1–2)، ثم `git add`: `migrations/versions/049_insurance_issuer_entity_id_set_null.py`، `tests/test_insurance_entity_membership_gap_fix.py`، `tests/test_insurance_policy_response_null_issuer.py`، `tests/test_insurance_getter_endpoints_wiring.py` (معدَّل)، `eppne-web/components/insurance/PolicyCard.tsx`، `eppne-web/types/insurance.ts`، وتقارير: `insurance-entity-membership-gap-fix`، `insurance-entity-membership-pattern-extraction`، `insurance-policy-response-schema-fix`، `insurance-policy-response-schema-fix-investigation` (`-session-log.md`).
**Commit B — Batch 0-A (عزل التينانت)، 8 ملفات:**
`git apply --cached` لـ`patchB_whole` (repository.py: `list_active_pensions`) و`patchB_shared` (router.py: 8 endpoints؛ service.py: D2 ×2 + `disburse` الطبقة أ) **بعد** A، ثم `git add`: `tests/test_insurance_batch0a_tenant_isolation.py` + `.claude/reports/insurance-batch0a-tenant-isolation-session-log.md` + 3 ملفات `insurance-batch0a-evidence-*.txt`. (مجلد `insurance-batch0a-commit-split/` أدوات مساعدة — لا يُضاف للـcommit ما لم يُرَد.)
**Commit C — `PROGRESS_LOG.md` (منفصل):** ⚠️ الملف نفسه `M` ويحوي إدخالات غير committed من جلسات أخرى كثيرة؛ commit الملف كاملًا يُدخل كل هذا. الخياران: (i) commit مستقل "docs: accumulated PROGRESS_LOG entries" بعد مراجعة المستخدم، أو (ii) تقسيم hunks خاصة بـBatch 0-A بنفس أسلوب `git apply --cached`.
**القاعدة:** كل commit عبر الفهرس (`git apply --cached` + `git add` ثم `git commit` بلا pathspec) وليس `git commit -- <pathspec>` لأن الأخير يأخذ الملف كاملًا ولا يفصل الـhunks.

---

## 15) إضافات بعد مراجعة §14 (2026-09-21)

### أ) نصوص `PROGRESS_LOG.md` — مسودة كاملة بانتظار موافقة المستخدم (لم يُكتب شيء في السجل)
**الملف الحاكم:** `.claude/reports/insurance-batch0a-progress-log-draft.md` — يحوي النص الحرفي لكل إدخال (A البانر، B `insurance-disburse-pensions-payout-logic-broken`، C `insurance-submit-claim-500`، D سطر تحديث `insurance-review-claim-payout-from-reviewer-personal-wallet`، E `insurance-unused-tenant-header-dependencies`، F سطر التصحيح المؤرَّخ أسفل بند [2026-09-16]، **F3** بند منفصل documented-only خارج insurance، **H** بند قرار الـcommits المعلَّق، G سطر الجلسة المُقفلة، I اختياري) مع خريطة مواضع الإدراج. عند الموافقة تُكتب **من هذا الملف حرفيًا**. تنسيق الصفوف مطابق لصفوف الجدول القائمة (`| — | **`name`** [date] — ... | الحالة | المراجع |`) وأسلوب الفقرات المؤرَّخة مطابق لسابقة سطر 258.
**ما أُضيف عن النسخة المعروضة سابقًا:** بند F3 (الفهارس + cp1256)، وبند H (الـcommits)، وجملة "`submit_claim` مكسور و`disburse` معطَّل فعليًا" في البانر وسطر الإغلاق، وإدراج البندين الجديدين في قائمة البنود المفتوحة بالبانر.

### ب) الـcommits — بند معلَّق مُسجَّل، **لم يُنفَّذ أي commit**
البند: `insurance-batch0a-commits-pending` (النص H). المحتوى: تقسيم A (عمل insurance السابق، 14 ملفًا) ثم B (Batch 0-A، 8 ملفات) بـ`git apply --cached` (patches في `.claude/reports/insurance-batch0a-commit-split/`) — التفاصيل في §14-د.
**قرار مطلوب من المستخدم — تبعية migration `048`:** `049` ← `048` (غير tracked، من جلسة saas أخرى)، و050+ تتسلسل بعد 049.
| الخيار | الوصف | التوصية |
|---|---|---|
| 1 | commit `048` + كود saas المرتبط به (يحدده صاحب تلك الجلسة) → ثم A → ثم B | ✅ **موصى به** — يحفظ سلسلة alembic وتطابق الموديل/الـmigration |
| 2 | commit A بدون `049` وتأجيلها | ❌ `models.py` (`SET NULL`) يُسجَّل بلا migration مقابل |
| 3 | `048` وحده بلا كود saas | ❌ migration بلا الموديل/الكود الذي يستخدمه |
**`PROGRESS_LOG.md` — التوصية: hunk-splitting (تفضيل المستخدم، وأنا أؤيده).** جدوى مُتحقَّق منها: (1) **كل** مواضع الإدراج (البانر، سطر 250، 261، 1015، 4272) موجودة في **HEAD** أيضًا (فحص `git show HEAD:PROGRESS_LOG.md`)؛ (2) الملف فيه **hunk واحد فقط** غير committed من جلسات أخرى (`@@ -4506 +4506,670 @@`، +670/−1، HEAD = 4505 سطرًا، الشجرة = 5174) وهو **بعد** كل مواضعنا (أقصاها 4272) فلا تداخل. الطريقة عند التنفيذ: بناء "HEAD + إدخالاتي فقط" ثم `git diff` لتوليد patch وتطبيقه بـ`git apply --cached` (مع `--check` أولًا، مع الانتباه لتحذير `LF→CRLF` الظاهر لهذا الملف)، والتحقق أن الفهرس = HEAD + إدخالاتي فقط قبل أي commit. (الخيار الآخر — commit الملف كاملًا — يُدخل 670 سطرًا من جلسات أخرى، لذا لا أوصي به.)

### ج) ملاحظة جديدة بالقراءة فقط (F4) — **غير مُتحقَّق منها حيًا**
`review_claim` (service.py 452–578) لا يحوي أي فحص لحالة المطالبة الحالية قبل الموافقة (الإشارات الوحيدة لـ`ClaimStatus` عند كتابة `PAID`/`REJECTED`)، ومفتاح الـidempotency للتحويل `claim_payout_{claim_id}_{uuid}` عشوائي (سطر ~517؛ كذلك `renew_{id}_{uuid}` سطر ~305). **الفرضية:** استدعاء `approve=true` مرتين على نفس المطالبة بلا هيدر `Idempotency-Key` قد يدفع مرتين. **لم تُجرَّب** (لا أدّعي أنها ثغرة مؤكَّدة). مُدرَجة كنص **I اختياري** في المسودة، ولن تُكتب في السجل دون قرار المستخدم. أخذتُها في اعتباري في درجة الأمان (§د) كخصم جزئي فقط.

### د) الدرجة الصادقة النهائية لدومين insurance (بعد Batch 0-A)
**ملاحظة منهجية:** لا يوجد في وثائق المستودع rubric أو درجة سابقة لـinsurance (بحثتُ في `PROGRESS_LOG.md`/`PROJECT_AUDIT.md`/`.claude/reports`/`.claude/plans`). طبّقتُ الأوزان التي حدّدها المستخدم (أمان 350 / وظيفي 250 / فرونت 200 / سكيما 100 / تحقق 100 = 1000) وقسّمتُ كل فئة لبنود فرعية **بحكمي الخاص** ليتمكن المستخدم من إعادة الوزن.

| الفئة | الدرجة | التبرير (أدلة) |
|---|---|---|
| **الأمان (350)** | **275** | • عزل التينانت (140/150): كل الـ8 endpoints المعرَّضة تحوّلت لـ`current_user.tenant_id` وأُثبت حيًا (هجوم/مشروع، فلوس، ghost-wallet)؛ خصم لأن `EntityMembership.get_member` بلا فلتر تينانت. • RBAC/الصلاحيات (75/100): superuser + عضوية الكيان لـ`create/update_policy` و`review_claim`؛ خصم لـ`update_claim` (superuser يضبط الحالة/المبلغ بلا فحص عضوية أو صرف — بند موجود `insurance-update-claim-permission-asymmetry`). • السلامة المالية (60/100): `review_claim` يدفع من محفظة المراجِع الشخصية (تصميم)، مفاتيح idempotency عشوائية في `renew`/الصرف وغياب فحص حالة المطالبة (**F4، غير مُتحقَّق**)، و`disburse` معطَّل فعليًا مع `sender_id=1` هاردكودد كامن. |
| **الوظيفي (250)** | **125** | من 23 endpoint: سياسات 40/50 ✅ (create/list/get/update)، اشتراكات 40/50 (subscribe مدفوع وget_my_subscriptions تعمل حيًا؛ `renew`/`cancel` لم تُتحقَّق)، **مطالبات 15/60 — `submit_claim` مكسور (500 دائمًا) فلا يمكن بدء أي مطالبة عبر الـAPI** (المراجعة تعمل على مطالبات موجودة)، **معاشات 15/60 — `disburse_pensions` معطَّل فعليًا (`count=0`)** فلا صرف معاشات (إنشاء/قراءة/إيقاف يعمل)، ملفات الموظفين 15/30 (create يعمل، `me` GET/PUT لم تُتحقَّق حيًا). |
| **الفرونت (200)** | **105** *(ثقة منخفضة — مؤقتة)* | لم أفحص الفرونت في هذه الجلسة إلا بقراءة سطحية: 5 صفحات (`insurance/{,claims,employee-profile,pensions,policies,subscriptions}`) + `services/insurance.ts` + مكونات، ومشكلة البادئة المضاعفة `/insurance/insurance/...` (batch4) **لم تعد موجودة** (المسارات `/insurance/...` مفردة). **لم أشغّل `tsc` ولا متصفحًا** (قيد Chrome المعروف)؛ وأي واجهة "تقديم مطالبة" ستضرب endpoint مكسورًا. |
| **السكيما (100)** | **80** | 5 جداول بـ`tenant_id NOT NULL` + FK، `idempotency_key` فريد جزئي، `CheckConstraint` "هدف تأميني واحد"، schemas بـ`gt=0`/`pattern`، migration 049 (`SET NULL`) للاتساق. خصم: `last_payout_tx String(100)` يُملأ بكائن (عطل الصرف)، اتساق مستفيد/تينانت غير مفروض على مستوى DB (فقط فحص D2 تطبيقيًا)، migration 049 غير committed وأبوها 048 غير tracked. |
| **التحقق (100)** | **72** | + قبل/بعد حي بتينانتين حقيقيين مع أرصدة وghost-wallet، + regression دائم جديد (2 tests) فوق 5 ملفات اختبار insurance قائمة، + إثبات baseline للفشلين المسبقين، + تنظيف zero-diff على 259 جدولًا. − **مسار نجاح `submit_claim` غير قابل للتحقق**، − **صرف المعاشات end-to-end غير قابل للتحقق** (معطَّل)، − `renew`/`cancel`/`update_claim`/`my-*` بلا تحقق حي هذه الجلسة، − اختباران أحمران في الـsuite (مسبقان)، − صفر تحقق فرونت/متصفح، − التغطية (≥80% حسب CODING_STANDARDS) لم تُقَس. |
| **الإجمالي** | **≈ 657 / 1000 (≈ 66%)** | تقدير رجعي لما قبل الجلسة: **≈ 510** (الأمان ≈150 لأن 8 endpoints مالية/بيانات كانت قابلة للاستغلال بالهيدر، والتحقق ≈50) — الزيادة (+≈147) كلها من الأمان والتحقق؛ الوظيفي والفرونت لم يتغيّرا لأن الجلسة أمنية بحتة. |

**تصريح صريح:** الدرجة **محدودة سقفها الوظيفي** لأن **`submit_claim` مكسور** (لا مطالبة تُقدَّم) و**`disburse` معطَّل فعليًا** (لا معاش يُصرف)؛ وأي رفع لها يمر عبر البندين `insurance-submit-claim-500` و`insurance-disburse-pensions-payout-logic-broken` (بشرط حسم قرار الدافع أولًا).

### هـ) F3 (خارج insurance) — موثَّق كبند منفصل
مُدرَج كنص **F3** في المسودة، باسم `server-startup-index-creation-failure-and-cp1256-logging-errors`، مُصنَّف "خارج نطاق insurance، documented-only". مصدر الفهارس: `app/core/database_indexes.py:78` (`idx_transactions_user_date ... (user_id, ...)` وأيضًا `idx_transactions_currency_user`؛ جدول `transactions` بلا `user_id`)، ولوج البدء فيه 176 سطر `InFailedSQLTransactionError` (عدد الكتل الفاشلة الفعلي وأيها فُقد **لم يُحصَر**). الجزء الثاني: `UnicodeEncodeError` (cp1256) في الـlogging على Windows. لم يُلمَس أي شيء.

---

## §15 - Pre-log review package

> **الغرض:** حزمة مراجعة واحدة قابلة للرفع، تحوي **النص الحرفي الكامل** لكل إدخال مخطَّط في `PROGRESS_LOG.md`، والدرجة الكاملة بالفئات الخمس، وبند ملاحظة `review_claim` كبند مستقل، وخيارات migration 048 كما عُرضت.
> **الحالة:** ⏸️ **لم يُكتب شيء في `PROGRESS_LOG.md`، ولم يُنفَّذ أي commit.** (تحقق: `git hash-object PROGRESS_LOG.md` = `0f482af8b5faa2433086ba38e56f6decab5bcdfb` وقت كتابة هذه الحزمة، ويجب أن يبقى كما هو؛ staged = 0؛ `HEAD` = `6f68cb4`.)
> **ملاحظة ترقيم (مهمة للمراجِع):** يوجد أعلاه قسم أقدم بعنوان `15) إضافات بعد مراجعة §14` (أُنشئ قبل هذا الطلب) — أسمّيه هنا **«§15-قديم»**. هذه الحزمة هي **الحاكمة**: عند أي اختلاف بينهما (مثلًا: نص H صار سطرًا واحدًا هنا، وF4 صار بندًا مستقلًا هنا) **النص هنا هو الذي سيُكتب**. ملف المسودة `.claude/reports/insurance-batch0a-progress-log-draft.md` **أصبح مُتجاوَزًا** ولن يُستخدم كمصدر عند الكتابة.

### ترتيب الكتابة وأماكن الإدراج في `PROGRESS_LOG.md` (أرقام الأسطر الحالية؛ كلها موجودة في HEAD أيضًا)
| # | الإدخال | موضع الإدراج |
|---|---|---|
| 1 | `insurance-disburse-pensions-payout-logic-broken` (صف جديد) | بعد سطر 1015 (آخر صف بالجدول، قبل `---` سطر 1017) |
| 2 | `insurance-submit-claim-500` (صف جديد) | بعد الصف السابق مباشرة |
| 3 | `insurance-review-claim-no-status-guard-and-random-payout-idempotency` (صف جديد — **النص في (ج)**) | بعد الصف السابق مباشرة |
| 4 | `insurance-unused-tenant-header-dependencies` (صف جديد) | بعد الصف السابق مباشرة |
| 5 | `server-startup-index-creation-failure-and-cp1256-logging-errors` (F3، صف جديد) | بعد الصف السابق مباشرة |
| 6 | `insurance-batch0a-commits-pending` (H، **سطر واحد**) | بعد الصف السابق مباشرة |
| 7 | سطر التحديث المؤرَّخ لـ`insurance-review-claim-payout-from-reviewer-personal-wallet` | فقرة جديدة بعد سطر 261 (سابقة: سطر 258) |
| 8 | سطر التصحيح المؤرَّخ أسفل بند [2026-09-16] | سطر جديد بعد سطر 4272 — **النص القديم لا يُعدَّل** |
| 9 | سطر الجلسة المُقفلة | بعد سطر 250 (آخر bullet في قائمة الجلسات المُقفلة) |
| 10 | بانر الحالة | استبدال سطر العنوان (9) + إدراج فقرات جديدة تحته + تحويل "آخر إغلاق رسمي:" (سطر 11) إلى "إغلاق رسمي سابق [2026-09-07]:" |

---

### أ) النصوص الحرفية الكاملة (كما ستُكتب بالضبط)

#### أ-1) `insurance-disburse-pensions-payout-logic-broken` — صف جديد
```
| — | **`insurance-disburse-pensions-payout-logic-broken`** [2026-09-21] — اكتُشف أثناء Batch 0-A (`insurance-batch0a-tenant-isolation`) في التشخيص ثم التحقق الحي لـ`POST /insurance/admin/disburse-pensions` (`insurance/service.py::disburse_monthly_pensions`). **الطبقة (أ) — عزل التينانت — اتصلحت في نفس الجلسة (لا تُعاد هنا):** الدالة بقت `disburse_monthly_pensions(tenant_id)` تقرأ `list_active_pensions(tenant_id)` (دالة repo جديدة) وتربط `FinanceService(self.db, tenant_id)`؛ الاستعلام القديم `list_pensions_for_beneficiary(None, ACTIVE)` كان يترجم `WHERE beneficiary_id IS NULL` على عمود `NOT NULL` فيرجّع صفر صف دائمًا (مؤكَّد حيًا: 7 معاشات ACTIVE، `count=0`). **الباقي مفتوح — منطق الصرف نفسه، 3 أعطال جديدة:** (1) **`finance.transfer(...)` بلا `idempotency_key`** رغم إنه معامل إجباري → `TypeError` عند الاستدعاء قبل أي أثر، و`except Exception: pass` في نفس الدالة بيبلعه صامتًا فترجع `count=0` "نجاح" — وده اللي بيخلّي الدالة ما تدفعش حاجة النهارده؛ (2) **كائن `Transaction` كامل بيتخزَّن في `last_payout_tx`** (`update_pension(..., last_payout_tx=tx)` بدل `tx.tx_hash`) بينما العمود `PensionRecord.last_payout_tx` هو `String(100)` — نفس فئة `finance-transfer-returns-transaction-object-not-tx-hash-string` [2026-08-18] أعلاه (المرجع العام للفئة)؛ (3) **فحص "دُفع هذا الشهر" عالق:** `_get_payout_date()` بترجع `datetime.utcnow()` دايمًا بغض النظر عن `tx_hash`، فأي معاش له `last_payout_tx` غير فاضي بيُعتبر مدفوع الشهر الحالي وبيتخطّاه في كل شهر — عمليًا مفيش حماية شهرية حقيقية. **`sender_id=1` هاردكودد — مش بيتوثَّق هنا تاني:** إحالة للبند الموجود `finance-transfer-hardcoded-system-account-real-fund-risk` [تحديث 2026-09-16] (الصف أعلاه؛ تتبُّعه الأول كان تحت اسم `insurance-disburse-pensions-hardcoded-system-account`)؛ الموقع الآن `insurance/service.py` السطر ~638 (كان :626 قبل Batch 0-A). **⚠️ شرط ترتيب صريح: قرار الدافع (مين بيدفع؟ حساب نظام التينانت عبر `get_or_create_system_account`؟) لازم يتحسم قبل إصلاح `idempotency_key` — وإلا فإصلاح المفتاح وحده هيخلّي الصرف يسحب فعليًا من محفظة `user_id=1`**، لأن الإصلاح الحالي جعل الحلقة تصل لأول مرة لمعاشات حقيقية ولا فلوس بتتحرك فقط بسبب العطل (1). | 🔴 **مفتوح، أولوية عالية — الخطر كامن (latent) لا حي:** الـendpoint حاليًا بيرجع `count=0` ولا بيحرّك أي فلوس (مؤكَّد حيًا بعد الإصلاح: أرصدة + جدول `transactions` + محفظة user 1 = 710.0 بلا تغيير)، ولا جدولة تلقائية للدالة | `.claude/reports/insurance-batch0a-tenant-isolation-session-log.md` §2.4، §11، §12؛ `.claude/reports/insurance-batch0a-evidence-after.txt` |
```

#### أ-2) `insurance-submit-claim-500` — صف جديد
```
| — | **`insurance-submit-claim-500`** [2026-09-21] — اكتُشف أثناء التحقق الحي لـBatch 0-A: `POST /insurance/claims` (`submit_claim`) بيرجع **500 دايمًا لأي مستخدم في أي تينانت**، حتى في السيناريو المشروع تمامًا (`member_A` على اشتراك ACTIVE خاص به: تينانت 124 قبل الإصلاح و128 بعده — نفس النتيجة). **السبب الجذري (من لوج السيرفر):** `insurance/service.py` (`submit_claim`، ~سطر 403-408) بيبني `create_claim(**{k: v for k, v in data.items() if k not in ["incident_description", "subscription_id"]})` — **بيستبعد `subscription_id` نفسه**، فيُدرَج `NULL` في `insurance_claims.subscription_id` (`nullable=False`). ملخص الـtraceback: `router.py:195 submit_claim` → `service.py:402 submit_claim` → `repository.py:113 create_claim` (`await self.db.flush()`) → `IntegrityError`/`asyncpg NotNullViolationError: null value in column "subscription_id" of relation "insurance_claims"`؛ والـ`parameters` بتوضح `tenant_id=128` سليم و`subscription_id=None`. **غير متعلق بعزل التينانت** (`tenant_id` سليم في الـINSERT). **الحالة في Batch 0-A:** طُبِّق **جزء عزل التينانت فقط** (`tenant_id = cast(int, current_user.tenant_id)` بدل الهيدر)، **الباج نفسه لم يُصلَح**. **⚠️ مسار النجاح (`submit_claim` المشروع) لم يُتحقَّق منه حيًا ولا يمكن التحقق منه** حتى إصلاح هذا البند — المُثبَت فقط الاتجاه الهجومي (قبل: الطلب المزوَّر بهيدر تينانت آخر وصل للـINSERT بـ`tenant_id=125`؛ بعد: 404 "Subscription not found" قبل الوصول للـINSERT). وأي خطوات بعد الـINSERT (audit / event_bus / idempotency، ومسار AI governance المغلَّف بـ`try/except`) غير مُختبَرة أيضًا. **مطلوب عند إصلاح هذا البند (F1): إعادة تشغيل التحقق الحي العابر للتينانت على المسار المشروع** (مطالبة بتُقدَّم فعليًا بنجاح داخل تينانت المستدعي + محاولة عابرة بهيدر تينانت آخر تفشل)، **لأن العزل أُثبت على مسار الهجوم فقط**. **الحل المتوقَّع (لم يُنفَّذ):** تمرير `subscription_id=data["subscription_id"]` صراحة لـ`create_claim`. | 🔴 **مفتوح، أولوية عالية** — endpoint مكسور بالكامل (لا يمكن تقديم أي مطالبة عبر الـAPI) | `.claude/reports/insurance-batch0a-tenant-isolation-session-log.md` §7.1، §9-F1، §13-ب |
```

#### أ-3) سطر التحديث المؤرَّخ تحت `insurance-review-claim-payout-from-reviewer-personal-wallet` (بند موجود، بلا بند جديد)
```
**✅ تأكيد حي [2026-09-21، Batch 0-A]:** أُعيد تأكيد هذا السلوك حيًا (بند موجود، بلا بند جديد): `PUT /insurance/claims/{id}/review?approve=true&approved_amount=20` في سيناريو مشروع (أدمن تينانت A، عضو OWNER في الكيان المُصدِر) → `200`، المطالبة `PAID`، **محفظة المراجِع (`admin_A`) اتخصم منها 20 (500→480)، ومحفظة صاحب المطالبة (`member_A`) اتضاف لها 20 (490→510)**، `payout_tx_hash=TX-EEC5CFD5BC46` — نفس النتيجة بالحرف قبل الإصلاح (تينانت 124، `TX-EAC1C8F3023D`) وبعده (تينانت 128). السلوك لم يتغيّر (قرار تصميم/منتج، خارج نطاق Batch 0-A، لم يُلمَس بأمر صريح من المستخدم). المرجع: `.claude/reports/insurance-batch0a-tenant-isolation-session-log.md` §7.2، §11.
```

#### أ-4) `insurance-unused-tenant-header-dependencies` — صف واحد، documented-only
```
| — | **`insurance-unused-tenant-header-dependencies`** [2026-09-21] — *documented-only، لا تنفيذ:* 4 endpoints في `insurance/router.py` (`renew_subscription`، `get_my_claims`، `get_my_pensions`، `get_my_employee_profile`) لسه بتعلن `tenant: AcademyTenant = Depends(get_current_tenant)` **بدون أي استخدام لها في الجسم** — صفر خطر فعلي (الهيدر لا يؤثر على شيء فيها)، دين تنظيف فقط؛ واستيراد `get_current_tenant`/`AcademyTenant` باقٍ في الملف بسببها وحدها. | ⚪ **مرجع فقط، أولوية منخفضة** | `.claude/reports/insurance-batch0a-tenant-isolation-session-log.md` §10 |
```

#### أ-5) سطر التصحيح المؤرَّخ الجديد أسفل بند [2026-09-16] `insurance-disburse-pensions-hardcoded-system-account` (سطر جديد؛ النص القديم لا يُعدَّل)
```
**تصحيح مؤرَّخ [2026-09-21، Batch 0-A] — سطر جديد؛ النص أعلاه لم يُعدَّل:** وصف هذا البند أعلاه ("كل معاش شهري لأي تينانت بيتسحب فعليًا من نفس حساب `user_id=1`" و"بتلف على كل pensions عبر كل التينانتس") كان وصفًا **للنية التصميمية** للكود لا لسلوكه الفعلي وقتها: الاستعلام المستخدَم كان `list_pensions_for_beneficiary(None, ACTIVE)` = `WHERE beneficiary_id IS NULL` على عمود `NOT NULL`، فكان يرجّع **صفر صف دائمًا** والحلقة ما اشتغلتش أصلًا (مؤكَّد حيًا في Batch 0-A: 7 معاشات ACTIVE عبر تينانتين، `count=0`، صفر حركة فلوس، محفظة user 1 = 710.0؛ وسبقه `batch4-audit-security-realestate-insurance-health.md` §4.5). **ما تغيّر في Batch 0-A:** (1) عزل التينانت اتصلح (`list_active_pensions(tenant_id)` + `FinanceService(self.db, tenant_id)`)؛ (2) الحلقة بقت **تصل لأول مرة** لمعاشات حقيقية، ولا فلوس بتتحرك فقط لأن `finance.transfer` بيُستدعى بلا `idempotency_key` (TypeError مبلوع). `sender_id=1` **لسه هاردكودد** (السطر ~638 حاليًا، كان :626) — الخطر كامن؛ **قرار الدافع يُحسَم قبل إصلاح `idempotency_key`**. التفاصيل: `insurance-disburse-pensions-payout-logic-broken` (جدول الـBacklog) و`.claude/reports/insurance-batch0a-tenant-isolation-session-log.md` §2.4، §11.
```

#### أ-6) F3 — بند منفصل documented-only، **خارج نطاق `insurance`** — صف جديد
```
| — | **`server-startup-index-creation-failure-and-cp1256-logging-errors`** [2026-09-21] — *documented-only، **خارج نطاق `insurance`** (لم يُلمَس، اكتُشف بالصدفة أثناء تشغيل `uvicorn` محليًا على Windows في Batch 0-A):* (1) **`app/core/database_indexes.py:78`** — كتلة فهارس `transactions` فيها `CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON transactions (user_id, created_at DESC)` (وكمان `idx_transactions_currency_user ... (currency, user_id)`)، لكن جدول `transactions` **ما فيهوش عمود `user_id`** (فيه `sender_id`/`receiver_id`) → `ProgrammingError: column "user_id" does not exist` عند كل بدء سيرفر؛ والكتلة (نص SQL واحد) بتتسجَّل كـ"⚠️ Skipping index (likely exists)" — **رسالة مضلِّلة** لأن السبب خطأ حقيقي مش "الفهرس موجود". وبعده ظهر في لوج بدء واحد 176 سطر `InFailedSQLTransactionError` — يوحي بأن كتل فهارس تانية بتفشل بالتبعية (**لم يُحصَر عددها ولا أيها فاتها الإنشاء فعليًا**). (2) **`UnicodeEncodeError: 'charmap' codec can't encode character`** (كودك cp1256 للكونسول على Windows) عند تسجيل رسائل فيها عربي/إيموجي (✅ 🔄 ⚠️) → "--- Logging error ---" tracebacks بتغرق اللوج (لوج تشغيل واحد فيه أكتر من 10 آلاف سطر) وبتدفن أخطاء حقيقية — traceback باج `submit_claim` كان مدفونًا وسطها. **الأثر:** أداء (إنشاء فهارس `transactions` مش مضمون من هذا المسار) + صعوبة تشخيص؛ صفر أثر أمني/مالي مباشر. **الحل المتوقَّع (لم يُنفَّذ):** تصحيح أعمدة الفهارس (`sender_id`/`receiver_id`) في `database_indexes.py`، وتغيير رسالة الـskip لتعرض الخطأ الفعلي، وضبط ترميز الـlogging (`utf-8`) لبيئة Windows. | ⚪ **مفتوح، أولوية متوسطة–منخفضة، documented-only — خارج نطاق `insurance`** | `.claude/reports/insurance-batch0a-tenant-isolation-session-log.md` §9-F3 |
```

#### أ-7) سطر الجلسة المُقفلة
```
- **insurance-batch0a-tenant-isolation — إصلاح أمني عاجل: عزل التينانت في 8 endpoints بدومين `insurance` [2026-09-21]** — ✅ **مُغلَق رسميًا** (نطاق: عزل التينانت + D2 + الطبقة (أ) من `disburse`). النمط المعتمَد من `ai_agents`: `tenant_id = cast(int, current_user.tenant_id)` بدل هيدر `X-Tenant-ID` (`create_policy`، `subscribe`، `get_my_subscriptions`، `submit_claim`، `review_claim`، `create_pension`، `disburse_pensions`، `create_employee_profile`) + فحص انتماء `beneficiary_id`/`user_id` للتينانت (D2، يرجّع 404) + `list_active_pensions(tenant_id)` جديدة. **تحقق حي قبل/بعد (HTTP حقيقي، تينانتان throwaway):** قبل الإصلاح نجح 8 من 9 سيناريوهات هجوم عابر للتينانت (بوليصة/معاش/ملف موظف/اشتراك/رفض مطالبة اتكتبوا في تينانت B) — والتاسع (`submit_claim`) وصل للـINSERT قبل ما يفشل بباج منفصل؛ والاشتراك المدفوع العابر حرّك فعليًا 10 MR_USDT بعد تمويل محفظة المهاجم داخل B (محفظة في B: 500→490، مستلم B: 0→10). بعد الإصلاح: الكل 404 أو "الهيدر مُتجاهَل، حُلَّ لتينانت المستدعي"، **كل الأرصدة بلا تغيير، صفر محافظ ghost جديدة في تينانت B**، والسيناريوهات المشروعة (`subscribe` مدفوع، `review_claim` approve=20) نتيجتها مطابقة قبل/بعد. `disburse`: 200 `count=0`، صفر فلوس، عزل `list_active_pensions` مُثبَت (A=4 صفوف، B=2، تينانت غير موجود=[])، محفظة user 1 = 710.0 طوال الجلسة. صفر migration، regression دائم `tests/test_insurance_batch0a_tenant_isolation.py` (2 passed ×2). فشلان في suite مسبقان **مُثبَتان بالتشغيل على HEAD نظيف** (`6f68cb4`) وغير متعلقين: `test_insurance_get_user_and_get_user_email_all_three_call_paths` و`test_realestate_buy_fractional_ownership_invoice_ordering`. **⚠️ حدود موثَّقة:** `submit_claim` **مكسور** (مسار نجاحه لم يُتحقَّق منه → `insurance-submit-claim-500`، ويلزم إعادة التحقق العابر للتينانت عند إصلاحه) و`disburse` **معطَّل فعليًا** (الخطر كامن) — راجع تحذير قرار الدافع في البانر. **بنود جديدة:** `insurance-disburse-pensions-payout-logic-broken` (🔴)، `insurance-submit-claim-500` (🔴)، `insurance-review-claim-no-status-guard-and-random-payout-idempotency` (🟡 غير مُتحقَّق، أولوية عالية — تحرّك فلوس)، `insurance-unused-tenant-header-dependencies` (⚪)، `server-startup-index-creation-failure-and-cp1256-logging-errors` (⚪، خارج insurance)، `insurance-batch0a-commits-pending` (⏸️ قرار المستخدم/صاحب جلسة saas)؛ + تحديث مؤرَّخ على `insurance-review-claim-payout-from-reviewer-personal-wallet`، وتصحيح مؤرَّخ أسفل بند [2026-09-16]. **تنظيف:** تينانتات throwaway 124–129 + 5 صفوف `transactions` حُذفت، مقارنة لقطة الـ259 جدولًا **zero-diff**، ومحفظة user 1 = 710.0. **لم يُنفَّذ أي commit.** التقرير: `.claude/reports/insurance-batch0a-tenant-isolation-session-log.md` + 3 ملفات evidence (`insurance-batch0a-evidence-{before,before2-funded-ghost-wallet,after}.txt`).
```

#### أ-8) بانر الحالة (مع تحذير قرار الدافع)
**سطر العنوان يصير:**
```
## 📌 بانر الحالة [آخر تحديث: 2026-09-21]
```
**فقرات جديدة تُدرَج تحته مباشرة (وسطر "آخر إغلاق رسمي:" القديم يصير "إغلاق رسمي سابق [2026-09-07]:"):**
```
آخر إغلاق رسمي: **Batch 0-A — إصلاح أمني عاجل لعزل التينانت في دومين `insurance` (8 endpoints) [2026-09-21]** — ✅ **مُغلَق رسميًا، مُتحقَّق منه حيًا (قبل/بعد عبر HTTP حقيقي، تينانتان throwaway، وتنظيف كامل zero-diff).**

خلفية: كانت 8 endpoints في `insurance` بتاخد التينانت من هيدر `X-Tenant-ID` (قيمته الافتراضية 1 لو غايب) — بما فيها اشتراك مدفوع وصرف تعويض يحرّكوا فلوس. الإصلاح: `current_user.tenant_id` (نمط `ai_agents`) + فحص انتماء المستفيد/الموظف للتينانت (D2) + عزل التينانت في `disburse_monthly_pensions` (الطبقة أ فقط). **لا migration.** التفاصيل والأدلة في قائمة الجلسات المُقفلة تحت و`.claude/reports/insurance-batch0a-tenant-isolation-session-log.md`.

**⚠️ تحذير ترتيب الإصلاح (مهم):** قرار **الدافع** في `disburse_monthly_pensions` (`sender_id=1` هاردكودد — مغطّى في `finance-transfer-hardcoded-system-account-real-fund-risk` [تحديث 2026-09-16]) **يجب أن يُحسَم قبل** إصلاح `idempotency_key` — وإلا فإصلاح المفتاح وحده يجعل الصرف يسحب فعليًا من محفظة `user_id=1`. الصرف حاليًا معطَّل فعليًا (`count=0`، لا فلوس تتحرك)، فالخطر كامن، لكنه قريب خطوة واحدة.

**حدود موثَّقة:** `insurance.submit_claim` **مكسور** (500 لأي مستخدم) و`disburse` **معطَّل فعليًا** — لذلك مسار نجاح `submit_claim` لم يُتحقَّق منه، والتحقق العابر للتينانت عليه يلزم إعادته بعد إصلاحه.

**بنود مفتوحة/موثَّقة نتيجة هذا الإغلاق (بدون تنفيذ):** (1) 🔴 `insurance-disburse-pensions-payout-logic-broken`، (2) 🔴 `insurance-submit-claim-500`، (3) 🟡 `insurance-review-claim-no-status-guard-and-random-payout-idempotency` — **غير مُتحقَّق منه، أولوية عالية (تحرّك فلوس)**، ليس ثغرة مؤكَّدة، (4) ⚪ `insurance-unused-tenant-header-dependencies`، (5) ⚪ `server-startup-index-creation-failure-and-cp1256-logging-errors` (خارج insurance)، (6) ⏸️ `insurance-batch0a-commits-pending` (قرار المستخدم/صاحب جلسة saas: تبعية migration 048). تحديث مؤرَّخ مضاف على البند الموجود `insurance-review-claim-payout-from-reviewer-personal-wallet` (بلا بند جديد)، وسطر تصحيح مؤرَّخ أسفل بند [2026-09-16] `insurance-disburse-pensions-hardcoded-system-account`.
```

#### أ-9) H — `insurance-batch0a-commits-pending` (**سطر واحد فقط**، يُكتب في السجل)
```
| — | **`insurance-batch0a-commits-pending`** [2026-09-21] — بند إداري (git hygiene): **لم يُنفَّذ أي commit** في Batch 0-A؛ تعديلات `insurance` القديمة متداخلة مع Batch 0-A في `router.py`/`service.py` (تقسيم A ثم B بـ`git apply --cached` مُثبَتة جدواه)، وmigration `049` تعتمد على `048` غير tracked من جلسة saas — **`048` لا يُضمّ في commit insurance، وقراره لصاحب جلسة saas/المستخدم**؛ و`PROGRESS_LOG.md` يُقسَّم hunks لا يُلتزَم كاملًا. | ⏸️ **معلَّق — بانتظار قرار المستخدم/صاحب جلسة saas** | `.claude/reports/insurance-batch0a-tenant-isolation-session-log.md` §14-د، §15 - Pre-log review package (د) |
```

---

### ب) الدرجة النهائية لدومين insurance — **الفئات الخمس كاملة** (≈ 657 / 1000 ≈ 66%)
**منهجية:** لا يوجد في وثائق المستودع rubric أو درجة سابقة لـinsurance (بحثتُ في `PROGRESS_LOG.md` و`PROJECT_AUDIT.md` و`.claude/reports` و`.claude/plans`). طبّقتُ أوزانك (أمان 350 / وظيفي 250 / فرونت 200 / سكيما 100 / تحقق 100)، والبنود الفرعية وأوزانها **من حكمي أنا** ليتمكن المراجِع من إعادة الوزن. **سقف الدرجة الوظيفي:** `submit_claim` **مكسور** (500 دائمًا) و`disburse` **معطَّل فعليًا** (`count=0`).

#### 1) الأمان — **275 / 350**
| البند الفرعي | الدرجة | التبرير |
|---|---|---|
| عزل التينانت (150) | **140** | كل الـ8 endpoints المعرَّضة (`create_policy`, `subscribe`, `get_my_subscriptions`, `submit_claim`, `review_claim`, `create_pension`, `disburse_pensions`, `create_employee_profile`) تحوّلت لـ`current_user.tenant_id` وأُثبت حيًا بهجوم/مشروع/فلوس/ghost-wallet (قبل: 8 من 9 هجمات نجحت؛ بعد: كلها محجوبة أو "الهيدر مُتجاهَل"). خصم 10: `EntityMembership.get_member` بلا فلتر تينانت، والـ4 dependencies غير المستخدمة (صفر خطر لكنها دين). |
| RBAC / الصلاحيات (100) | **75** | `create_policy`/`update_policy` يشترطان superuser + عضوية OWNER/EXECUTIVE_DIRECTOR على الكيان المُصدِر، و`review_claim` عضوية الكيان، وD2 يمنع مستفيد/موظف من تينانت آخر. خصم 25: `update_claim` (superuser يضبط `status`/`approved_amount` بلا فحص عضوية ولا صرف — بند موجود `insurance-update-claim-permission-asymmetry`). |
| السلامة المالية / idempotency (100) | **60** | `review_claim` يدفع من محفظة المراجِع الشخصية (تصميم، موثَّق)؛ مفاتيح idempotency عشوائية (`uuid`) في `review_claim` وفي `renew_subscription`، وغياب فحص حالة المطالبة قبل الموافقة (**F4 — غير مُتحقَّق منه، خصم جزئي فقط**؛ لو اتنفى بالتحقق الحي يُضاف ≈ +15)؛ و`disburse` معطَّل فعليًا مع `sender_id=1` هاردكودد كامن (خطر مؤجَّل لا مُلغى). لا سرّ/بيانات حساسة مسرَّبة في الطبقة التي فحصتُها. |

#### 2) الوظيفي — **125 / 250**
| المجال (الوزن) | الدرجة | التبرير |
|---|---|---|
| البوالص (50) | **40** | `create_policy` مُتحقَّق حيًا؛ `list`/`get`/`update` مغطاة باختبار `test_insurance_getter_endpoints_wiring` (لم تُشغَّل حيًا هذه الجلسة). |
| الاشتراكات (50) | **40** | `subscribe` المدفوع (500→490، مستلم 0→10) و`get_my_subscriptions` مُتحقَّقان حيًا؛ `renew`/`cancel`/`get` لم تُتحقَّق هذه الجلسة. |
| المطالبات (60) | **15** | **`submit_claim` مكسور (500 لكل المستخدمين) → لا يمكن بدء أي مطالبة عبر الـAPI.** `review_claim` (approve) يعمل حيًا على مطالبة مزروعة؛ `get_my_claims`/`get_claim`/`update_claim` غير متحقَّق منها حيًا. |
| المعاشات (60) | **15** | **`disburse_pensions` معطَّل فعليًا (`count=0`) → لا صرف معاشات.** `create_pension` مُتحقَّق حيًا؛ `get`/`update`/`suspend`/`me` مغطاة باختبار. |
| ملفات الموظفين (30) | **15** | `create_employee_profile` مُتحقَّق حيًا؛ `GET/PUT me` لم تُتحقَّق حيًا. |

#### 3) الفرونت إند — **105 / 200** *(ثقة منخفضة — مؤقتة)*
| البند | الدرجة | التبرير |
|---|---|---|
| البنية والربط (100) | **60** | 5 صفحات (`insurance/{,claims,employee-profile,pensions,policies,subscriptions}`) + `services/insurance.ts` + مكونات + types؛ مشكلة البادئة المضاعفة `/insurance/insurance/...` (batch4) **لم تعد موجودة** (المسارات `/insurance/...` مفردة). |
| الصحة والتحقق (100) | **45** | **لم أشغّل `tsc` ولا متصفحًا** في هذه الجلسة (قيد Chrome المعروف) — فحص سطحي فقط للملفات. أي واجهة "تقديم مطالبة" تضرب endpoint مكسورًا (`submit_claim`)، ولا واجهة صرف معاشات يمكن أن تعمل فعليًا (`disburse` معطَّل). |

#### 4) السكيما — **80 / 100**
| البند | الدرجة | التبرير |
|---|---|---|
| سلامة الموديلات (40) | **35** | 5 جداول بـ`tenant_id NOT NULL` + FK، `idempotency_key` فريد جزئي، `CheckConstraint chk_exclusive_insurance_target`، فهارس. |
| التحقق في Pydantic (25) | **20** | `gt=0`، `pattern` لعنوان العقد، `ge/le` للنسب، تحقق `end_date > start_date`. |
| الـmigrations (20) | **15** | migration 049 (`issuer_entity_id` → `SET NULL`) متسقة مع الموديل؛ خصم: 049 غير committed وأبوها 048 غير tracked. |
| اتساق الأنواع/العلاقات (15) | **10** | خصم: `last_payout_tx String(100)` يُملأ بكائن Transaction (عطل الصرف)، واتساق مستفيد/تينانت غير مفروض على مستوى DB (فقط فحص D2 تطبيقيًا). |

#### 5) التحقق — **72 / 100**
| البند | الدرجة | التبرير |
|---|---|---|
| إثبات حي قبل/بعد (30) | **30** | تينانتان throwaway حقيقيان، أرصدة، ghost-wallet، قبل/بعد/قبل-أقوى، ومطابقة السيناريوهات المشروعة. |
| اختبارات regression دائمة (25) | **20** | +2 tests جديدة (مرّت ×2، صفر residue) فوق 5 ملفات اختبار insurance قائمة. |
| تغطية الـendpoints حيًا (25) | **14** | ~7 من 23 endpoint مُتحقَّقة حيًا (create_policy، subscribe، my-subscriptions، review approve، create_pension، create_employee_profile، disburse-inert)؛ الباقي بالاختبارات أو غير مُتحقَّق. **`submit_claim` (نجاح) وصرف المعاشات end-to-end غير قابلين للتحقق.** |
| صحة الـsuite (10) | **8** | فشلان مسبقان مُثبَتان بالتشغيل على HEAD نظيف (`6f68cb4`) ولا علاقة لهما بالجلسة. |
| فرونت/متصفح (10) | **0** | صفر تحقق. |
| **ملاحظة:** التغطية (≥80% حسب `CODING_STANDARDS.md`) لم تُقَس. | | |

#### الإجمالي
| الفئة | الدرجة |
|---|---|
| الأمان | 275 / 350 |
| الوظيفي | 125 / 250 |
| الفرونت إند (مؤقت) | 105 / 200 |
| السكيما | 80 / 100 |
| التحقق | 72 / 100 |
| **المجموع** | **657 / 1000 (≈ 66%)** |

**تقدير رجعي لما قبل الجلسة:** ≈ **510** (الأمان ≈150 لأن 8 endpoints مالية/بيانات كانت قابلة للاستغلال بالهيدر؛ التحقق ≈50). الزيادة ≈ +147 كلها من الأمان والتحقق؛ الوظيفي والفرونت لم يتغيّرا لأن الجلسة أمنية بحتة. **أي رفع مستقبلي للدرجة** يمر عبر: `insurance-submit-claim-500` (الوظيفي + التحقق)، و`insurance-disburse-pensions-payout-logic-broken` (الوظيفي، **بشرط حسم قرار الدافع أولًا**)، والتحقق الحي لبند F4 أدناه (الأمان).

---

### ج) بند مستقل: ملاحظة `review_claim` (F4) — **غير مُتحقَّق منه، أولوية عالية (تحرّك فلوس)** — يُكتب كصف ثالث في المجموعة (بعد `insurance-submit-claim-500`)
**قواعد التصنيف:** لا يُصلَح ولا يُسمّى ثغرة مؤكَّدة. الأدلة كلها **قراءة ثابتة للكود** (service.py، أسطر ~452–578، ~517، ~305) وتاريخ السجل؛ لم تُجرَّب.

#### ج-1) النص الحرفي للصف
```
| — | **`insurance-review-claim-no-status-guard-and-random-payout-idempotency`** [2026-09-21] — *ملاحظة بالقراءة الثابتة أثناء Batch 0-A، **غير مُتحقَّق منها حيًا، وليست ثغرة مؤكَّدة**:* (1) `review_claim` (`insurance/service.py` ~452-578) **لا يفحص حالة المطالبة الحالية قبل الموافقة** — الإشارات الوحيدة لـ`ClaimStatus` داخل الدالة هي عند **كتابة** `PAID`/`REJECTED`، فمطالبة `PAID` بالفعل تقدر تدخل نفس المسار تاني؛ (2) **مفتاح idempotency الخاص بالتحويل بيحوي `uuid` عشوائي** (`payment_idempotency = f"claim_payout_{claim_id}_{uuid.uuid4().hex[:12]}"`، ~سطر 517) فبيتغيّر في كل استدعاء ولا يمنع تكرار الدفع أبدًا — الحماية الوحيدة من التكرار هي هيدر `Idempotency-Key` الاختياري اللي بيرجّع نتيجة مخزَّنة (لو مش مبعوت، مفيش حماية)؛ (3) **نفس النمط في `renew_subscription`** (`payment_idempotency = f"renew_{subscription_id}_{uuid...}"`، ~سطر 305، وبلا هيدر idempotency أصلًا). **السياق:** قبل Backlog #41 [2026-08-29] (`insurance-review-claim-issuer-entity-id-reviewer-id-mismatch`) كان فحص الصلاحية في `review_claim` بيقارن مساحتَي معرِّفات مختلفتين فكان يرفض الجميع (المسار عمليًا مقفول، `broken-closed`)، وبعد إصلاحه بقت `review_claim` قابلة للوصول فعليًا؛ وفي Batch 0-A أثبت **LEGIT-2** حيًا إن الدفع بيشتغل (`approve=true`، 20 MR_USDT، المراجِع 500→480، صاحب المطالبة 490→510، `payout_tx_hash` مسجَّل، المطالبة `PAID`) — **يعني لو الفرضية اتأكدت، `approve=true` مرتين على نفس المطالبة ممكن يدفع مرتين** (وبنفس السبب `approve=false` بعد `PAID` ممكن يقلب المطالبة لـ`REJECTED` والفلوس اتدفعت). **الحالة:** لم تُجرَّب ولم تُصلَح. **تحقق حي قصير مقترَح (منفصل، بموافقة قبل التنفيذ):** تينانت throwaway + مطالبة SUBMITTED + مراجِع OWNER ممول → (أ) `approve=true` مرتين بلا `Idempotency-Key`، (ب) `approve=true` مرتين بنفس `Idempotency-Key`، (ج) `approve=false` بعد `PAID`؛ مقارنة أرصدة المراجِع/المطالِب و`transactions` و`status` بعد كل خطوة (بـ`SELECT` مستقل) ثم تنظيف zero-diff. | 🟡 **غير مُتحقَّق منه — أولوية عالية (تحرّك فلوس)**؛ التصنيف النهائي (مؤكَّد/مُنفى) بعد التحقق الحي | `.claude/reports/insurance-batch0a-tenant-isolation-session-log.md` §15 - Pre-log review package (ج)؛ `.claude/reports/insurance-41-review-claim-permission-check-session-log.md` |
```

#### ج-2) خطة التحقق الحي المقترحة (قصيرة، **لم تُنفَّذ**، تحتاج موافقتك قبل التشغيل)
- **الإعداد:** تينانت throwaway واحد يكفي (الاختبار داخل نفس التينانت) بنفس seeder هذه الجلسة: مراجِع SUPER_ADMIN + عضوية OWNER على الكيان المُصدِر + محفظة 500 MR_USDT، وعضو مشترك (صاحب المطالبة) + اشتراك ACTIVE + **مطالبة `SUBMITTED` مزروعة مباشرة** (لأن `submit_claim` مكسور)، وبوليصة `max_coverage_limit` ≥ 20. لقطة أساس لكل الجداول (259) + محفظة user 1 (710.0).
- **الخطوات (كل خطوة: HTTP حقيقي + `SELECT` مستقل لـ`insurance_claims.status/payout_tx_hash/approved_amount` وأرصدة المحفظتين وعدد صفوف `transactions`):**
  1. `PUT /claims/{id}/review?approve=true&approved_amount=20` (بلا `Idempotency-Key`) → توقّع 200، PAID، المراجِع 500→480، المطالِب +20.
  2. **نفس الطلب مرة ثانية** (بلا هيدر) → **إن رجع 200 وتغيّرت الأرصدة مرة أخرى (480→460 / +20) وظهر صف `transactions` ثانٍ = الفرضية مؤكَّدة (دفع مزدوج)**؛ إن رجع رفضًا/بلا تغيير = الفرضية مُنفاة.
  3. (ب) على مطالبة جديدة: `approve=true` مرتين **بنفس** `Idempotency-Key` → توقّع الثانية ترجع المطالبة نفسها بلا دفع جديد (اختبار للحماية الوحيدة الموجودة).
  4. (ج) على مطالبة `PAID`: `approve=false` → هل تنقلب لـ`REJECTED` والفلوس مدفوعة؟ (تحقق من حالة الفساد).
- **مخرجات:** جدول قبل/بعد لكل خطوة + تصنيف نهائي (مؤكَّد/مُنفى) + تحديث الصف في السجل من "غير مُتحقَّق" إلى النتيجة + تنظيف zero-diff (نفس أوامر التنظيف المعتمَدة) + محفظة user 1 = 710.0.
- **لا إصلاح** في هذه الخطة (إن تأكدت الفرضية يُفتح بند إصلاح منفصل بقرارك: فحص `claim.status`، ومفتاح idempotency حتمي `claim_payout_{claim_id}` بدل العشوائي).

---

### د) migration 048 — الخيارات **كما عُرضت حرفيًا** + التوصية

**(1) الجدول كما ورد في التقرير بالعربية (§14-د / §15-قديم-ب):**
| الخيار | الوصف | التوصية |
|---|---|---|
| 1 | commit `048` + كود saas المرتبط به (يحدده صاحب تلك الجلسة) → ثم A → ثم B | ✅ **موصى به** — يحفظ سلسلة alembic وتطابق الموديل/الـmigration |
| 2 | commit A بدون `049` وتأجيلها | ❌ `models.py` (`SET NULL`) يُسجَّل بلا migration مقابل |
| 3 | `048` وحده بلا كود saas | ❌ migration بلا الموديل/الكود الذي يستخدمه |

**(2) الجدول كما ورد في رسالة الطرفية (بالإنجليزية):**
| Option | Recommendation |
|---|---|
| **1.** Commit `048` plus its saas code first, then A, then B. The saas session's owner picks its files. | **Recommended:** it keeps the alembic chain and the model/migration match. |
| **2.** Commit A without `049`. | No: `models.py` (`SET NULL`) would be committed without its migration. |
| **3.** Commit `048` alone. | No: a migration without the model and code that use it. |

**الخلفية (حقائق مُتحقَّق منها):** `049_insurance_issuer_entity_id_set_null.py` → `down_revision = '048_add_cancelled_at_to_saas_tenant_subscriptions'`؛ `048` **غير tracked** (`??`) وتتبع جلسة saas أخرى (وله تعديلات saas مرتبطة `M` في `saas/models.py`… إلخ)؛ ومهاجرات `050+` تتسلسل بعد `049`؛ و`046`/`047` tracked في HEAD.

**التوصية (بعد ميلك الأولي: "لا يُضمّ 048 في commit insurance؛ صاحبه — جلسة saas — هو من يقرر"):** ✅ **أؤيد ميلك، والخيار 1 كما هو مكتوب متوافق معه** — لأنه يقضي بأن `048` (مع كود saas) يُلتزَم **بواسطة صاحبه وبشكل مستقل** قبل insurance، وليس مضمومًا داخل أي commit من commits insurance. بالتحديد:
1. **`048` + كود saas المرتبط به:** commit مستقل يقرره صاحب جلسة saas (أنا لا أحدد ملفاته ولا ألمسها).
2. **Commit A (insurance السابق، 14 ملفًا) وCommit B (Batch 0-A، 8 ملفات):** **لا يحويان `048`**؛ يُنفَّذان **بعد** أن يهبط commit 048 في التاريخ (لأن A يحوي `049` التي تعتمد عليه). لو تأخّر صاحب saas: **A و B ينتظران** (لا نلجأ للخيارين 2/3).
3. **`PROGRESS_LOG.md`:** hunk-splitting بـ`git apply --cached` (تفضيلك؛ مُتحقَّق من جدواه: كل المواضع في HEAD، وhunk واحد فقط آخر غير committed `@@ -4506 +4506,670 @@` بعد كل مواضعنا) — لا commit للملف كاملًا.
4. **لا commit الآن** — البند مُسجَّل كـ"معلَّق" (أ-9) بانتظار قرارك/قرار صاحب saas.

---

### هـ) حالة الملفات والتنفيذ (تصريح)
- **لم يُكتب شيء في `PROGRESS_LOG.md`** — البنود أعلاه نصوص مقترحة فقط.
- **لم يُنفَّذ أي commit** (staged = 0، `HEAD` = `6f68cb4`).
- ملف المسودة القديم `insurance-batch0a-progress-log-draft.md` أصبح مُتجاوَزًا بهذه الحزمة (أُضيف له إشعار في أعلاه).
- الملفات غير المتتبَّعة المضافة في هذه الجلسة (مقصودة): تقارير `insurance-batch0a-*`، مجلد `insurance-batch0a-commit-split/`، `tests/test_insurance_batch0a_tenant_isolation.py`، وملف المسودة.

---

## §16 - Post-approval amendments and PROGRESS_LOG write log (2026-09-21)

> **الحالة:** ✅ كُتبت إدخالات Batch 0-A في `PROGRESS_LOG.md` (الشجرة) ومُرحَّلة للفهرس فقط بأسلوب hunk-splitting. **لم يُنفَّذ أي commit.** لم يُنفَّذ تحقق `review_claim` الحي. الدرجة **خارج** `PROGRESS_LOG.md` (باقية في §15 - Pre-log review package (ب) فقط).
> **الحاكم:** ما كُتب فعليًا في `PROGRESS_LOG.md` هو النص المعتمَد في §15 مع التعديلات الأربعة أدناه. أي اختلاف بين §15 والسجل = هذه التعديلات فقط.

### 1) التعديلات الأربعة المعتمَدة — وكيف طُبِّقت
| # | التعديل | التطبيق |
|---|---|---|
| 1 | **A-7 لا يُضاف كـbullet عند سطر 250**؛ بل قسم `## [2026-09-21] insurance-batch0a-tenant-isolation` بعد سطر 4274 (`---`) وقبل `## [2026-09-17]` | قسم جديد: العنوان في سطر **4297** بعد `---` (4295) وسطر فارغ، وبعده الفقرة ثم `---` ثم قسم 2026-09-17 (سطر 4303). حُوِّل نص الـbullet (حُذف "- ") إلى فقرة تحت العنوان بنفس المحتوى. |
| 2 | إعادة صياغة "8 من 9 سيناريوهات" | صياغة جديدة: في التشغيل الأول (124/125) نجح **7 سيناريوهات هجوم**؛ و5b توقّف بـ403 **فقط بسبب فراغ محفظة المهاجم في تينانت B** (حاجز عرضي)؛ و`submit_claim` وصل للـINSERT؛ وفي `before2` (محفظة ممولة، 126/127) **نجح 5b (201): 500→490 / 0→10**، وفحص ghost-wallet `unchanged: False`. المسار الخام: `E:/cc/.claude/reports/insurance-batch0a-evidence-before2-funded-ghost-wallet.txt` (5,604 بايت؛ مقطع ATTACK-5b في سطر 42، وGHOST-WALLET في سطر 58). |
| 3 | استبدال `~638` بالرقم الفعلي | `grep -n "sender_id=1"` على `insurance/service.py` رجّع **622** (نص docstring) و**638** (سطر الكود `sender_id=1,`). استُخدم **638** في A-1 وA-5. **البانر:** نصه المعتمَد لم يكن يحوي رقم سطر أصلًا، فأضفتُ فيه `insurance/service.py:638` داخل تحذير قرار الدافع (تنفيذًا لروح التعديل، وأُبلغ به المستخدم). |
| 4 | سطر A-3 بعد سطر 261 بسطر فارغ قبله وبعده | سطر 271 = صف `insurance-review-claim-payout-from-reviewer-personal-wallet`، **272 فارغ**، **273 = سطر التحديث المؤرَّخ**، **274 فارغ**، **275 = الصف التالي** `invoicing-generate-invoice-number-count-based-collision` (سابقة سطر 258). تحقق الترتيب بعرض الأسطر صراحة. |

### 2) تحقق اتفاقية المكان (طلب المستخدم) — نتيجة تستحق العلم
- **مؤكَّد:** منذ 2026-09-01 تُسجَّل الجلسات كأقسام `## [date] ...` (وليس bullets).
- **مُلاحَظ يخالف افتراض "الوسط":** ترتيب الملف **ليس مرتَّبًا زمنيًا**؛ (أقسام 09-10 و09-14 و09-15 تأتي بعد أقسام 09-16)، وأحدث الإدخالات (2026-09-17 ثم **2026-09-18** في أسطر 4753 و4877 و4947) **مُلحَقة في نهاية الملف** (وهي ضمن ذيل غير committed من جلسة أخرى). أي أن المتَّبع فعليًا هو "الإلحاق في النهاية"، وقسم 2026-09-21 الآن **بين 09-16 و09-17 (أقدم زمنيًا من مكانه الطبيعي)**.
- **القرار:** نُفِّذ **مكان المستخدم الصريح** (بعد سطر 4274، بجوار بند insurance 2026-09-16 ذي الصلة، وقابل للفصل بـhunk-splitting). الإلحاق في النهاية كان سيدخل داخل ذيل الـ670 سطرًا غير committed لجلسة أخرى ويعقّد فصل الـhunks. **النقل لاحقًا سهل** (السكربت يعتمد anchors نصية) — بقرارك.

### 3) طريقة الكتابة (hunk-splitting) والتحقق
1. **مصدر النصوص:** استُخرجت النصوص من كتل الكود في §15 برمجيًا (لا إعادة كتابة يدوية) ثم طُبِّقت عليها التعديلات الثلاثة النصّية (2، 3، وتحويل A-7 لقسم) — تأكيد أن المكتوب = المعتمَد.
2. **بناء "HEAD + إدخالاتنا فقط":** بأسلوب anchors نصية على blob الـHEAD الخام (`git show HEAD:PROGRESS_LOG.md`)، ثم `diff -u` لتوليد patch من 4 hunks بسياق 3 أسطر (`-6,9`، `-259,6`، `-1013,6`، `-4271,6`؛ وقسم الجلسة وسطر التصحيح متجاوران فيندمجان في hunk واحد).
3. `git apply --cached --check` ✅ ثم `git apply --cached` ✅ (الفهرس فقط؛ الملف نفسه عُدِّل في الشجرة بنفس الإدخالات بالسكربت ذاته).
4. **النتائج (تحقق بالبايتات، بـPython):**
   - `git diff --cached --stat`: **`PROGRESS_LOG.md | 31 +++++---` — 1 file changed, 29 insertions(+), 2 deletions(-)`.** المحذوف سطران فقط: عنوان البانر القديم، وتسمية "آخر إغلاق رسمي:" القديمة (تُستبدل بـ"إغلاق رسمي سابق [2026-09-07]:").
   - **الفهرس = HEAD + إدخالاتنا فقط: مطابق بايت-ببايت** لملف `head_plus_ours.md`.
   - **الشجرة = الفهرس + ذيل الجلسة الأخرى:** سطور الفهرس بادئة تامة لسطور الشجرة، والذيل (669 سطرًا بعد آخر سطر HEAD) **مطابق حرفيًا للذيل الأصلي** قبل أي تعديل. `git diff` (غير المُرحَّل) = **hunk واحد فقط `@@ -4533 +4533,670 @@` (670 إضافة/1 حذف)** — نفس حجم الذيل الأصلي (تحرّك رقمه بمقدار صافي +27 سطرًا).
   - ملفات مُرحَّلة: `PROGRESS_LOG.md` فقط (1).
   - **صفر كلمات درجة** في الإضافات (`657`، `/1000`، `275/350`... = 0 تطابق).
   - `HEAD` = `6f68cb4` بلا تغيير؛ stash = 0؛ worktrees = 1.

### 4) حادثة تنبيه: خطأ في نهايات الأسطر اكتُشف وصُحِّح (شفافية)
في المحاولة الأولى افترضتُ أن الملف CRLF بناءً على `grep -c $'\r'` في هذه البيئة، وهو **قياس غير موثوق** (يطابق كل الأسطر). فأدخل السكربت `\r` في 28 سطرًا مُدخَلًا. **اكتُشف** بفحص البايتات بـPython: **HEAD والملف الأصلي = LF فقط (صفر CRLF)**. **التصحيح:** إلغاء ترحيلي أنا فقط (`git reset -q -- PROGRESS_LOG.md`، الفهرس كان لا يحوي غيره)، واستعادة الملف من النسخة الاحتياطية (تحققتُ أن hash النسخة = `0f482af8b5faa2433086ba38e56f6decab5bcdfb` الأصلي وأن الشجرة رجعت مطابقة قبل إعادة الكتابة)، وتعديل السكربت ليستنتج نهاية السطر من الملف نفسه مع تأكيد `assert` أنه لا CR جديد. النتيجة النهائية: **CR = 0 في HEAD والفهرس والشجرة.** (وفي الأرقام: الإحصاء الصحيح 29+/2- بدل 30+/3- الأولى التي كانت تعكس الخطأ.)

### 5) أرقام أسطر الإدراج النهائية (ترقيم الملف بعد الكتابة؛ مطابق في الفهرس والشجرة لهذه المنطقة)
| الإدخال | السطر النهائي | (السطر الأصلي قبل الكتابة) |
|---|---|---|
| عنوان البانر المحدَّث | **9** | 9 |
| فقرات البانر الجديدة | **11 – 19/20** (آخر فقرة "بنود مفتوحة" سطر 19) | تحت 9 |
| "إغلاق رسمي سابق [2026-09-07]" (الفقرة القديمة المُعاد تسميتها) | **21** | 11 |
| صف `insurance-review-claim-payout-from-reviewer-personal-wallet` (لم يُغيَّر) | 271 | 261 |
| سطر التحديث المؤرَّخ لـreview_claim | **273** (فارغ قبله 272 وبعده 274) | بعد 261 |
| صف `insurance-disburse-pensions-payout-logic-broken` | **1029** | بعد 1015 |
| صف `insurance-submit-claim-500` | **1030** | ↑ |
| صف `insurance-review-claim-no-status-guard-and-random-payout-idempotency` | **1031** | ↑ |
| صف `insurance-unused-tenant-header-dependencies` | **1032** | ↑ |
| صف `server-startup-index-creation-failure-and-cp1256-logging-errors` (F3) | **1033** | ↑ |
| صف `insurance-batch0a-commits-pending` (H، سطر واحد) | **1034** | ↑ |
| سطر التصحيح المؤرَّخ أسفل بند [2026-09-16] | **4293** | بعد 4272 |
| قسم `## [2026-09-21] insurance-batch0a-tenant-isolation` | **4297** (يسبق `## [2026-09-17]` سطر 4303) | بعد 4275 |

### 6) ما لم يُفعل (بحسب التعليمات)
لا commit · لا تحقق حي لـ`review_claim` (F4) · الدرجة لم تُدخَل في السجل · `git worktree`/stash نظيفة.


---

## §17 - before2 evidence excerpt

> **المصدر:** `E:/cc/.claude/reports/insurance-batch0a-evidence-before2-funded-ghost-wallet.txt` — الأسطر **42–61** حرفيًا (ATTACK-5b ثم ATTACK-6/7 ثم GHOST-WALLET). تشغيل `before2`: تينانتات 126 (A) / 127 (B) — كود غير مُصلَح، ومحفظة `member_A` داخل تينانت B مموَّلة بـ500.

```
 42| ### ATTACK-5b subscribe PAID premium 10 policy_B (member_A + header B) - money-moving
 43|   http: 201
 44|   resp: {'id': 352, 'status': 'ACTIVE', 'policy_id': 633}
 45|   db: ['352|127|633']
 46|   wallets_before: {'admin_A@TA': '500', 'member_A@TA': '500', 'benef_A@TA': None, 'premium_receiver_A@TA': None, 'admin_B@TB': '500', 'member_B@TB': '500', 'benef_B@TB': None, 'premium_receiver_B@TB': None, 'member_A@T_B(ghost)': '500', 'admin_A@T_B(ghost)': None}
 47|   wallets_after: {'admin_A@TA': '500', 'member_A@TA': '500', 'benef_A@TA': None, 'premium_receiver_A@TA': None, 'admin_B@TB': '500', 'member_B@TB': '500', 'benef_B@TB': None, 'premium_receiver_B@TB': '10.0', 'member_A@T_B(ghost)': '490.0', 'admin_A@T_B(ghost)': None}
 48| 
 49| ### ATTACK-6 submit_claim on subscription 351 (member_A + header B)
 50|   http: 500
 51|   resp: Internal Server Error
 52|   db: []
 53| 
 54| ### ATTACK-7 get_my_subscriptions (member_A + header B)
 55|   http: 200
 56|   resp: list[2] ids=[352, 351]
 57| 
 58| ### GHOST-WALLET after ATTACK calls
 59|   wallet_rows_in_tenantB_total: ['6']
 60|   tenantA_users_wallets_in_tenantB: ['13505|490.0']
 61|   unchanged: False
```

### مطابقة جملة السجل مع هذه الأسطر (بعد التصحيح)
الجملة كما هي الآن في `PROGRESS_LOG.md` (سطر 4299، قسم `## [2026-09-21] insurance-batch0a-tenant-isolation`): «**نجح 5b كمان (201): محفظة `member_A` في B 500→490، مستلم القسط في B None→10.0، واشتراك اتكتب في تينانت B** — وفحص ghost-wallet أظهر `unchanged: False`».

| ما تقوله جملة السجل | ما في الأسطر | التطابق |
|---|---|---|
| نجح 5b (201) | سطر 43: `http: 201` | ✅ |
| محفظة `member_A` في B: 500→490 | سطر 46 `'member_A@T_B(ghost)': '500'` ← سطر 47 `'490.0'` | ✅ |
| مستلم القسط في B: None→10.0 | سطر 46 `'premium_receiver_B@TB': None` ← سطر 47 `'10.0'` | ✅ **حرفيًا** (كان مكتوبًا `0→10` وهو غير مطابق حرفيًا) |
| اشتراك اتكتب في تينانت B | سطر 45 `db: ['352\|127\|633']` (127 = تينانت B في before2) | ✅ |
| ghost-wallet `unchanged: False` | سطر 61 | ✅ |

**ما تغيّر في السجل:** سطر واحد فقط (4299) وعبارة واحدة فقط: `0→10` ← `None→10.0` (بلا أي إضافة أخرى للنص المعتمَد)، **في الشجرة فقط**. hash الملف صار `47b39fd5d5713971cd2436d83f200100bbabb109` (كان `a033feb22c8d4aa8105376b5b1a9d712707da198`).
**ملاحظة تفسير (استنتاج، غير قابل لإعادة التحقق لأن بيانات التينانتات نُظِّفت):** `None` في المخرجات تعني أن الاستعلام لم يجد قيمة `MR_USDT` لتلك المحفظة؛ وثبات `wallet_rows_in_tenantB_total` (6 ← 6) يرجّح أن صف محفظة المستلم كان موجودًا بلا مفتاح `MR_USDT` (لا أنه أُنشئ حديثًا). لذلك عُدِّلت العبارة إلى الحرفية `None→10.0` بدل "0".

### ملاحظات إجرائية (شفافية)
1. **إضافة بلا استئذان:** في البانر أُضيف `insurance/service.py:638` إلى **نص معتمَد** (تحذير قرار الدافع)؛ النص المعتمَد لم يكن يحوي رقم سطر، وفُسِّر التعديل الثالث بأنه يشمل البانر دون سؤال. (سُجِّل في §16-1 وأُبلغ به المستخدم.)
2. **القاعدة الدائمة:** «اسأل قبل تغيير أي نص معتمَد» — **حُفظت الآن في ذاكرة المشروع** (ملحق بملف الذاكرة `feedback_stop_before_consequential_edits`)، وتشمل: النصوص المعتمَدة تُكتب حرفيًا، وأي اختلاف يُبلَّغ به مع اقتراح التصحيح قبل التنفيذ ما لم يكن التصحيح مأذونًا به صراحة. (تصحيح `0→10` هذا أُذِن به صراحة.)

### إعادة توليد الـpatch (HEAD + إدخالاتنا فقط) — نتائج التحقق
- **الملف:** `.claude/reports/insurance-batch0a-commit-split/patchC_progress_log.patch` (مُعاد توليده، 32,159 بايت). **النسخة السابقة تمامًا محفوظة** كـ`patchC_progress_log.pre-text-fix.patch` (تحوي `0→10`).
- **بُني من:** blob الـHEAD الخام + إدخالاتنا فقط (بعد التصحيح) — **لا يحوي ذيل الجلسة الأخرى** (أعلى hunk يبدأ عند سطر 4271، وذيل الجلسة الأخرى يبدأ بعد 4533).
- `git apply --numstat` = **29 إضافة / 2 حذف**، **4 hunks** (`-6,9`، `-259,6`، `-1013,6`، `-4271,6`).
- `git apply --cached --check` مقابل HEAD: ✅ **PASS**.
- تطبيق الـpatch على نسخة نظيفة من ملف HEAD (مع `core.autocrlf=false`) ينتج ملفًا **مطابقًا بايت-ببايت** لـ"HEAD + إدخالاتنا (مع التصحيح)".
- *(زلتان في أدواتي أثناء التحقق، لا تمسّان محتوى الـpatch: مسار خاطئ لـ`hash-object` جعل سطر `index` ناقصًا في أول توليد، وتحويل `core.autocrlf=true` العالمي حوّل LF→CRLF في نسخة المقارنة؛ صُحِّحتا وأُعيد التوليد والتحقق.)*

### الحالة النهائية
| البند | القيمة |
|---|---|
| ملفات مُرحَّلة (staged) | **0** (`git reset -q -- PROGRESS_LOG.md` نُفِّذ، والفهرس = HEAD لهذا الملف) |
| الشجرة مقابل HEAD | **إدخالاتنا (+29/−2) + ذيل الجلسة الأخرى (+670/−1)** فقط: `git diff --stat` = 699 إضافة/3 حذف؛ سطور الشجرة تبدأ بـ"HEAD + إدخالاتنا" بالضبط، والذيل المتبقي (669 سطرًا) **مطابق للذيل الأصلي** قبل أي كتابة مني |
| نهايات الأسطر | CR = 0 في HEAD والشجرة (LF فقط) |
| كلمات الدرجة في إدخالاتنا | 0 |
| `HEAD` | `6f68cb4` (بلا commit)؛ stash = 0 |
