# Session Log — Seed تينانت 1 لخدمتي `insurance`/`real_estate` (متابعة بند Backlog #2)

**Date:** 2026-09-08
**النطاق المطلوب:** seed بيانات فقط (نفس نمط كل الدومينات اليوم). **صفر
تعديل كود، صفر تعديل ملف اختبار.**
**خلفية:** استكمال لتحقيق
`.claude/reports/plan-features-tests-fix-investigation-session-log.md`
(نفس الجلسة السابقة، read-only) اللي أثبت إن تينانت 1 ناقصه صفّان في
جدولين تينانت-specific (`saas_tenant_subscriptions`،
`saas_tenant_service_access`) بينما تينانت 16 عنده الصفّين المكافئين.

---

## 1) الـSeed المُنفَّذ

نُفِّذ عبر `docker exec eppne_db psql` مباشرةً (نفس الحاوية والقاعدة
اللي بيستخدمها `DATABASE_URL` في `.env` — `eppne_v2` على بورت 5435)،
داخل `transaction` واحدة (`BEGIN`...`COMMIT`)، **بلا تحديد `id=` صريح في
أي INSERT** (الـPK سيريال بيتاخد تلقائيًا عبر `nextval()` الافتراضي).

```sql
BEGIN;
INSERT INTO saas_tenant_subscriptions (tenant_id, plan_id, status, payment_method, auto_renew, start_date, created_at, updated_at)
VALUES (1, 101, 'ACTIVE', 'WALLET', true, now(), now(), now())
RETURNING id, tenant_id, plan_id, status;
-- id=132, tenant_id=1, plan_id=101 (insurance-pilot-plan), status=ACTIVE

INSERT INTO saas_tenant_subscriptions (tenant_id, plan_id, status, payment_method, auto_renew, start_date, created_at, updated_at)
VALUES (1, 110, 'ACTIVE', 'WALLET', true, now(), now(), now())
RETURNING id, tenant_id, plan_id, status;
-- id=133, tenant_id=1, plan_id=110 (real-estate-pilot-plan), status=ACTIVE

INSERT INTO saas_tenant_service_access (tenant_id, service_id, access_level, is_active, created_at, updated_at)
VALUES (1, 101, 'BASIC', true, now(), now())
RETURNING id, tenant_id, service_id, is_active;
-- id=61, tenant_id=1, service_id=101 (insurance), is_active=t

INSERT INTO saas_tenant_service_access (tenant_id, service_id, access_level, is_active, created_at, updated_at)
VALUES (1, 107, 'BASIC', true, now(), now())
RETURNING id, tenant_id, service_id, is_active;
-- id=62, tenant_id=1, service_id=107 (real_estate), is_active=t
COMMIT;
```

القيم (`status='ACTIVE'`، `access_level='BASIC'`) مطابقة حرفيًا لنمط
الصفّين المكافئين الموجودين فعلًا لتينانت 16 (`id=114/123` في
`saas_tenant_subscriptions`، `id=51/55` في `saas_tenant_service_access` —
موثَّق في تقرير التحقيق السابق §3.2/§3.3). `payment_method='WALLET'`
مُضاف زيادة (مطابق لصف تينانت 16 الخاص بـ`insurance`، ولنمط باقي
اشتراكات تينانت 1 الفعلية) — بلا أثر على منطق `can_access_service`
(العمود ده مش جزء من فحصها أصلًا).

### 1.1 القاعدة الإلزامية — `setval()`

**غير مطلوبة فعليًا هنا، وتم التحقق من ذلك صراحةً:** الأربعة INSERT
**لم تحدد `id=` صريح أبدًا** — العمود اتاخد تلقائيًا عبر الـ`DEFAULT
nextval(...)` بتاع كل جدول. بما إن الـsequence هو نفسه المصدر الوحيد
للـid في هذه الحالة، **مفيش أي احتمال تعارض/drift أصلًا** — القاعدة
مصمَّمة تحديدًا لحالة `INSERT ... (id, ...) VALUES (<رقم ثابت>, ...)`
اللي بتتجاوز الـsequence، وهذا لم يحصل هنا. تحقُّق مباشر قبل/بعد
للتأكيد:

| الجدول | `MAX(id)` قبل | `last_value` قبل | `MAX(id)` بعد | `last_value` بعد |
|---|---|---|---|---|
| `saas_tenant_subscriptions` | 131 | 131 | **133** | **133** |
| `saas_tenant_service_access` | 60 | 60 | **62** | **62** |

الاتنين متطابقين في الحالتين (قبل وبعد) — الـsequence سليم ومتزامن
تمامًا، صفر حاجة لـ`setval()` يدوي.

---

## 2) تشغيل الأربعة اختبارات حيًا

```
pytest tests/test_saas_active_subscription.py -k "realestate_rent_unit or realestate_buy_fractional or insurance_subscribe or insurance_review_claim" -v
```

**النتيجة: `2 passed, 2 failed`** — مش الأربعة زي المطلوب. التفصيل تحت
يوضح **ليه** بالضبط، ولماذا الاتنين الفاشلين لا يرجعا لبند Backlog #2
نفسه (بوابة الـSaaS)، بل لعطلين مختلفين تمامًا اكتُشفا **بالصدفة** بعد ما
الـseed فتح الطريق لهم.

### 2.1 ✅ `test_insurance_subscribe_saas_check_passes` — **PASSED**

نجح بالكامل — `_check_saas_limits` عدّت (بفضل الـseed)، والمسار المالي
الكامل (خصم القسط من المحفظة + إنشاء الاشتراك) التزم على القرص كما
هو موثَّق أصلًا في التقرير الأصلي.

### 2.2 ✅ `test_insurance_review_claim_saas_check_passes_then_hits_known_bug` — **PASSED**

نجح بالكامل — `_check_saas_limits` عدّت، والكود وصل فعليًا لبوابة
`review_claim` الداخلية وكراش بالظبط بالبج المُوثَّق مسبقًا
(`PermissionDeniedError: "Not authorized to review this claim"`،
Backlog منفصل `insurance-review-claim-issuer-entity-id-reviewer-id-conflict`)
— هذا هو **بالضبط** السلوك المتوقَّع الموثَّق في `docstring` الاختبار
نفسه.

**✅ خلاصة insurance: بند Backlog #2 اتحل بالكامل للاختبارين — الـseed
كان كافيًا 100%، صفر حاجة إضافية.**

### 2.3 ❌ `test_realestate_rent_unit_saas_check_passes` — **FAILED (سبب جديد، خارج نطاق #2)**

**الدليل المباشر إن `_check_saas_limits`/`can_access_service` عدّت
بنجاح تام:** الـtraceback بيوضح إن التنفيذ وصل عميق جوّه منطق
`rent_unit` الداخلي (بعد الـSaaS check بمراحل) وكراش في نقطة مختلفة
تمامًا:

```
app\domains\realestate\service.py:463: PermissionDeniedError
    owner = await self._get_land_owner_for_unit(unit, tenant_id)
    if cast(int, owner.id) != landlord_id:
        raise PermissionDeniedError("ليس لديك صلاحية تعديل هذه الوحدة")
```

**السبب الجذري (تحقُّق DB مباشر):** `_get_land_owner_for_unit`
(`realestate/service.py:683-695`) بتجيب المالك الفعلي عبر
`land_assets.owner_id` — مش عبر أي بارامتر بيمرره الاختبار. صف
`land_assets` المشترك (`EXISTING_LAND_ASSET_ID = 1`، مُعرَّف في ملف
الاختبار سطر 119، ومُعاد استخدامه قراءة فقط من جلسات سابقة) له
`owner_id` ثابت:

```sql
SELECT id, owner_id, tenant_id FROM land_assets WHERE id=1;
-- id=1, owner_id=47, tenant_id=1
```

الاختبار بينشئ `landlord` **جديد** في كل تشغيلة (`_create_funded_user`)
ويمرر `landlord_id=landlord.id` كأنه هو مالك الأرض — لكن المالك الحقيقي
المسجَّل في `land_assets.owner_id` هو `user_id=47` الثابت، مش `landlord`
الجديد. الفحص (`owner.id != landlord_id`) بيرفض بشكل صحيح تمامًا لأن
`landlord.id` **فعلًا** مش مالك الأرض. **هذا عطل في افتراضات الاختبار
نفسه (test fixture design)** — غير مرتبط إطلاقًا ببوابة الـSaaS
(Backlog #2)، ولم يكن ظاهرًا قبل الـseed لأن التنفيذ كان بيتوقف عند
بوابة الـSaaS أصلًا قبل ما يوصل لهذه النقطة.

### 2.4 ❌ `test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug` — **FAILED (سبب جديد، خارج نطاق #2)**

نفس الدليل: التنفيذ وصل عميق جوّه `buy_fractional_ownership` (بعد
الـSaaS check) وكراش في نقطة مختلفة عن الاتنين المتوقَّعين في
`docstring` الاختبار:

```
app\domains\realestate\service.py:313: PermissionDeniedError
    except InsufficientBalanceError:
        raise PermissionDeniedError("Insufficient balance")
```

**السبب الجذري:** الاختبار بينشئ `buyer` عبر
`_create_funded_user(db, "p_regtest_saas9_re_buyer")` **بلا تمرير
`mr_usdt`** — القيمة الافتراضية `Decimal("0")` (توقيع الدالة، سطر 127
من ملف الاختبار). سعر الوحدة `sale_price_mrusdt=500`، فتكلفة شراء 10%
= 50 MR_USDT — رصيد المشتري (0) غير كافٍ، فـ`finance.transfer()` بترمي
`InsufficientBalanceError` (متحوَّلة لـ`PermissionDeniedError`) **قبل**
ما الكود يوصل أصلًا لاستدعاء `AIAgentsService.execute_agent_action`
(سطر 366) اللي الاختبار بيتوقعه (`pytest.raises(TypeError,
match="tenant_id")`).

**اكتشاف إضافي غير مرتبط، يستحق التوثيق:** بالقراءة المباشرة لسطر 366،
اتضح إن استدعاء `execute_agent_action` **بقى ملفوف بـ`try/except
Exception` (سطر 365-368)** بيسجّل الخطأ بس (`logger.error`) ومكملش
بأي `raise` — يعني حتى لو المشتري كان ممول بالكامل ووصل الكود لهذه
النقطة، **مش هيرمي `TypeError` تاني أصلًا** — بج Backlog #16 (معامل
`tenant_id=` الزايد) بقى **معطَّل التأثير بالكامل** (مُبتلَع صمتًا) في
هذا الموضع تحديدًا، مش مجرد "لسه موجود" زي ما وثَّق تقرير سابق
[2026-08-19]. هذا اكتشاف عرضي **خارج نطاق هذه الجلسة تمامًا** (seed
فقط) — لم يُلمَس، ومُسجَّل هنا للشفافية فقط ليُراجَع في جلسة منفصلة.

---

## 3) الخلاصة

| الاختبار | النتيجة | بند Backlog #2 (بوابة SaaS) | العطل الفعلي (لو فشل) |
|---|---|---|---|
| `test_insurance_subscribe_saas_check_passes` | ✅ PASSED | ✅ اتحل بالكامل | — |
| `test_insurance_review_claim_saas_check_passes_then_hits_known_bug` | ✅ PASSED | ✅ اتحل بالكامل | — |
| `test_realestate_rent_unit_saas_check_passes` | ❌ FAILED | ✅ اتحل (عدّت الفحص، دليل traceback مباشر) | عطل تاني تمامًا: `landlord` المُنشأ في الاختبار مش نفسه `land_assets.owner_id=47` الثابت |
| `test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug` | ❌ FAILED | ✅ اتحل (عدّت الفحص، دليل traceback مباشر) | عطل تاني تمامًا: `buyer` مُنشأ برصيد `0`، التكلفة `50` — `InsufficientBalanceError` قبل الوصول لأي بج AI-agents |

**بند Backlog #2 نفسه (بوابة `can_access_service` لتينانت 1) مُتحقَّق
منه ✅ للأربعة اختبارات كلهم** — الأربعة عدّوا الفحص بنجاح تام
(اتنين وصلوا لنجاح كامل، واتنين وصلوا لعمق منطق داخلي بعيد جدًا عن
بوابة الـSaaS قبل ما يكراشوا بأعطال منفصلة تمامًا). **لكن الأربعة
اختبارات مش الأربعة "ناجحين" حرفيًا كملف pytest** — الاتنين
الخاصين بـ`realestate` بيحتاجوا إصلاح في **بيانات/افتراضات الاختبار
نفسه** (مش الكود، ومش الـseed) عشان ينجحوا فعليًا: إما تمرير
`landlord_id=47` (المالك الحقيقي) بدل مستخدم جديد في اختبار
`rent_unit`، أو تمويل `buyer` برصيد كافٍ (`>= 50`) في اختبار
`buy_fractional_ownership` — وهذا **تعديل ملف اختبار**، خارج نطاق
هذه الجلسة صراحةً ("صفر تعديل كود أو اختبار").

**القرار [2026-09-08]:** توثيق فقط، بلا إصلاح في هذه الجلسة أو أي
جلسة لاحقة تلقائية — راجع البندين الجديدين في §5 تحت.

---

## 5) بنود Backlog جديدة مفتوحة (توثيق فقط — بلا إصلاح)

بناءً على القرار أعلاه، الاتنين التاليين بيتوثقوا هنا كبندي backlog
مفتوحين، **بلا أي تعديل على كود أو اختبار** في هذه الجلسة ولا أي جلسة
سابقة لها. الأربعة اختبارات نفسها (ملف `test_saas_active_subscription.py`)
**لم تُلمَس** — تفضل بنفس حالتها الحالية (`2 passed, 2 failed`) لحد ما
يُتَّخذ قرار صريح جديد بتعديلها.

### 5.1 `realestate-test-fixture-landlord-not-registered-land-owner`

**الحالة:** 🔴 مفتوح.

**العنوان:** `test_realestate_rent_unit_saas_check_passes`
(`tests/test_saas_active_subscription.py:168-211`) بيفشل بـ
`PermissionDeniedError("ليس لديك صلاحية تعديل هذه الوحدة")`
(`realestate/service.py:463`)، مش بسبب بوابة الـSaaS (بند #2 —
مُتحقَّق منه ✅ مُنفصلًا، راجع §2.3).

**السبب الجذري:** الاختبار بينشئ مستخدم `landlord` جديد عشوائي في كل
تشغيلة (`_create_funded_user`) ويمرره كـ`landlord_id` لـ`rent_unit`،
لكن `_get_land_owner_for_unit` (`realestate/service.py:683-695`)
بتجيب المالك الحقيقي حصريًا من `land_assets.owner_id` — وصف
`land_assets` المشترك (`id=1`، `EXISTING_LAND_ASSET_ID` في ملف
الاختبار سطر 119) له `owner_id=47` **ثابت** (تحقُّق DB مباشر، §2.3).
الفحص `owner.id != landlord_id` بيرفض بحق لأن `landlord` المُنشأ
حديثًا فعلًا مش نفس `user_id=47`.

**الإصلاح المقترح (غير مُنفَّذ — قرار مستخدم مطلوب أولاً):** تمرير
`landlord_id=47` (نفس المالك المسجَّل فعليًا لـ`land_assets` رقم 1)
بدل إنشاء `landlord` عشوائي جديد، **أو** إنشاء `land_asset` throwaway
منفصل مملوك للـ`landlord` الجديد نفسه بدل إعادة استخدام الصف المشترك
`id=1`.

**المرجع:** هذا الملف §2.3، `.claude/reports/plan-features-tests-fix-investigation-session-log.md`.

### 5.2 `realestate-test-fixture-buyer-zero-balance-masks-ai-agent-swallowed-exception`

**الحالة:** 🔴 مفتوح (بندين مدمجين — فجوة seed في الاختبار + اكتشاف
عرضي في الكود الإنتاجي).

**العنوان:** `test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug`
(`tests/test_saas_active_subscription.py:273-315`) بيفشل بـ
`PermissionDeniedError("Insufficient balance")`
(`realestate/service.py:313`)، مش بسبب بوابة الـSaaS (بند #2 —
مُتحقَّق منه ✅ مُنفصلًا، راجع §2.4).

**السبب الجذري (فجوة seed الاختبار):** `buyer` بينشأ عبر
`_create_funded_user(db, "p_regtest_saas9_re_buyer")` **بلا تمرير
`mr_usdt`** (القيمة الافتراضية `Decimal("0")`). تكلفة شراء 10% من
وحدة سعرها `500` = `50 MR_USDT` — رصيد المشتري صفر، فـ
`finance.transfer()` بترمي `InsufficientBalanceError` قبل الوصول
لأي منطق تاني في الدالة.

**اكتشاف عرضي في الكود الإنتاجي (غير مُصلَح، خارج نطاق seed-only
لهذه الجلسة):** حتى لو اتصلحت فجوة الرصيد، الاختبار بيتوقع
`pytest.raises(TypeError, match="tenant_id")` من استدعاء
`AIAgentsService.execute_agent_action` (بج Backlog #16 المُوثَّق
مسبقًا) — لكن بالقراءة المباشرة، هذا الاستدعاء
(`realestate/service.py:365-368`) بقى ملفوفًا بـ`try/except
Exception` بيسجّل الخطأ فقط (`logger.error`) بلا `raise`. يعني بج
#16 في هذا الموضع تحديدًا **بقى مُبتلَعًا صمتًا بالكامل** — لن يظهر
كـ`TypeError` تاني أيًا كان رصيد المشتري. هذا يخالف التوثيق السابق
[2026-08-19] اللي أكَّد "لسه موجود فعليًا بالقراءة المباشرة" (بمعنى:
كان بيتصدَّر كـexception غير مُمسوك وقتها). **لم يُتحقَّق متى بالضبط
اتضاف الـ`try/except` ده ولا في أي جلسة** — خارج نطاق هذا التحقيق.

**الإصلاح المقترح (غير مُنفَّذ — قرار مستخدم مطلوب أولاً):**
1. تمويل `buyer` برصيد كافٍ (`>= 50 MR_USDT`) في الاختبار، **و**
2. تحديث توقُّع الاختبار (`pytest.raises`) ليعكس السلوك الفعلي
   الحالي بعد الـ`try/except` (الدالة هترجع نجاح صامت بدل ما ترمي
   `TypeError`) — يحتاج قرار: هل ابتلاع بج #16 صمتًا هنا سلوك مقصود
   (silent-write/silent-failure جديد يستحق بند backlog خاص به من نوع
   `silent-write-regression`)، أم رجعة غير مقصودة يجب التراجع عنها؟

**المرجع:** هذا الملف §2.4، `.claude/reports/plan-features-tests-fix-investigation-session-log.md`،
خلفية بج #16 الأصلي: `.claude/reports/backlog-16-begin-nested-commit-session-log.md`.

---

## 6) ملاحظة منهجية

الـseed (4 صفوف) هو **التعديل الوحيد على أي حالة** في هذه الجلسة —
صفر تعديل على أي ملف كود أو اختبار. `git status` قبل/بعد الجلسة مطابق
تمامًا (نفس مجموعة الملفات المعدَّلة من جلسات سابقة، صفر ملف جديد غير
هذا التقرير).
