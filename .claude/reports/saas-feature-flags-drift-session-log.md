# saas-feature-flags-dev-environment-drift — سجل الجلسة

**بدأت:** 2026-08-31
**المصدر:** اكتُشفت أثناء جلسة `realestate-design-decision` (خطوة 9) — 3
اختبارات فشلت بـ`PermissionDeniedError: "Real Estate feature is not
included in your current plan"` رغم إن الكود (ownership check) سليم.

**الحالة:** 🔍 تحقيق فقط — صفر تنفيذ حتى الآن، بانتظار قرار المستخدم.

---

## 1) السبب الجذري الفعلي — مش مجرد "بيانات ناقصة"

في البداية افترضنا إن المشكلة هي مجرد إن خطة tenant_id=1 ناقصة feature
`real_estate`. الفحص الفعلي كشف حاجة أعمق:

### الآلية كما هي مبرمجة الآن

كل دومين محمي (13 دومين) بيعرّف نسخته الخاصة من `_check_saas_limits`
(دالة **مكررة** حرفيًا 12 مرة تقريبًا بنفس المنطق، مش دالة مشتركة
واحدة). كل نسخة بتعمل:

```python
subscription = await saas.get_active_subscription(tenant_id)  # wrapper
# ↓ في saas/repository.py
async def get_any_active_subscription(self, tenant_id: int):
    """اشتراك واحد شامل نشط/تجريبي للـtenant، بغض النظر عن الخدمة"""
    ... .where(tenant_id == X, status IN (ACTIVE, TRIAL))
        .order_by(TenantSubscription.created_at.desc())
        .limit(1)
```

**المشكلة:** الدالة دي بترجع "أحدث اشتراك نشط" للـtenant **بغض النظر عن
الخدمة (service) المطلوبة فعليًا**. الافتراض المعماري الضمني: كل tenant
له اشتراك واحد "شامل" (comprehensive) يغطي كل الميزات. لكن الواقع في
قاعدة بيانات الديف الحالية: tenant_id=1 عنده **4 اشتراكات منفصلة** لخطط
مختلفة (تراكمت من جلسات اختبار معزولة كل واحدة عملت catalog/plan/
subscription خاص بيها)، مش اشتراك شامل واحد.

النتيجة: أي استدعاء لـ `_check_saas_limits` — من أي دومين، مش بس
realestate — بيتحدد نجاحه أو فشله حسب **آخر اشتراك اتعمل زمنيًا**
لـtenant_id=1، مش حسب هل الميزة المطلوبة فعلاً متاحة. هذا باج منطقي
(logic bug) في `get_any_active_subscription`، مكشوف بواسطة بيانات ديف
مبعثرة — مش مجرد نقص بيانات.

---

## 2) حالة قاعدة بيانات الديف الفعلية (فحص مباشر عبر asyncpg، 2026-08-31)

DSN: `postgresql://eppne:***REDACTED***@127.0.0.1:5435/eppne_v2`

### `saas_service_catalog` (8 صفوف فقط، كلها تقريبًا مخلّفات اختبارات)

| id | code | name |
|---|---|---|
| 2 | `p_saas9_verify_8fa402` | مخلّف اختبار (P-SAAS9-VERIFY) |
| 47 | `academy` | TEST_REQSECTOR_SESSION_ACADEMY_SERVICE |
| 48 | `affiliate` | TEST_REQSECTOR_SESSION_AFFILIATE_SERVICE |
| 74 | `tenders` | (نص عربي تالف/mojibake في التخزين) |
| 75 | `auctions` | (نفس المشكلة) |
| 76 | `service_marketplace` | (نفس المشكلة) |
| 77 | `zamakana` | (نفس المشكلة) |
| 78 | `tourism` | (نفس المشكلة) |

⚠️ ملاحظة جانبية اكتُشفت بالصدفة: أسماء `tenders`/`auctions`/
`service_marketplace`/`zamakana`/`tourism` مخزّنة بترميز تالف (mojibake
— نص عربي اتخزن/اتقرأ بترميز غلط). النطاق: خارج مهمة هذه الجلسة، يُوثَّق
كملاحظة منفصلة فقط.

### `saas_service_plans` (5 صفوف)

| id | service_id | code | features |
|---|---|---|---|
| 2 | 2 | `p_saas9_plan_8fa402` | `["real_estate", "insurance"]` |
| 47 | 47 | `test_reqsector_academy_plan` | `[]` |
| 48 | 48 | `test_reqsector_affiliate_plan` | `[]` |
| 77 | 74 (tenders) | `test-tenders` | `NULL` |
| 78 | 75 (auctions) | `test-auctions` | `NULL` |

### `saas_tenant_subscriptions` — tenant_id=1 (4 اشتراكات نشطة/ملغاة)

| id | plan_id | status | ملاحظة |
|---|---|---|---|
| 2 | 2 | ACTIVE | فيها `real_estate` + `insurance` |
| 50 | 48 | CANCELLED | — |
| 89 | 77 (tenders) | ACTIVE | features=NULL |
| **90** | **78 (auctions)** | **ACTIVE** | features=NULL — **آخر واحد اتعمل زمنيًا** |

بما إن `get_any_active_subscription` بترتب بـ`created_at DESC LIMIT 1`،
فهي بترجع **الصف id=90** (اشتراك auctions، features=NULL) لأي استدعاء
`_check_saas_limits(tenant_id=1, ...)` — حتى لو المطلوب فعليًا
`real_estate` أو `insurance` أو أي حاجة تانية. الاشتراك id=2 (اللي فيه
فعلاً `real_estate`+`insurance`) موجود ونشط، لكن **مش بيتقرأ أبدًا** لأنه
مش الأحدث.

- tenant_id=16: نفس النمط (3 اشتراكات منفصلة، plan_id=2/47/48) — نفس
  الباج محتمل هناك أيضًا، لم نختبره مباشرة.
- `saas_tenant_service_access`: صفين بس لـtenant_id=1 (tenders, auctions)
  — آلية تانية شبه منفصلة، مش مرتبطة بـ`_check_saas_limits`.
- `saas_tenant_feature_flags` (آلية الـper-feature toggle المنفصلة عبر
  `toggle_feature_flag`/`get_feature_flag`): **فاضية تمامًا** لـtenant_id=1
  — مش مستخدَمة في أي مسار حالي من الـ13 دومين المفحوصة.
- لا يوجد أي سكربت seed لبيانات SaaS plans/subscriptions في المشروع
  (`scripts/seed_tenant.py` الوحيد الموجود بيزرع tenant/org entities بس،
  صفر علاقة بخطط SaaS). البيانات الحالية تراكمت عضويًا من اختبارات
  متفرقة، مفيش تصميم متعمد وراها.

---

## 3) الصورة الكاملة — كل الدومينات المحمية بـ`_check_saas_limits` (13 دومين)

> **⚠️ تصحيح [2026-08-31، بعد التنفيذ الفعلي — راجع §9.2]:** الجدول تحت
> كان بيفترض إن كل الـ13 دومين (ما عدا `service_marketplace`) بيستخدموا
> نفس المسار المكسور (`get_active_subscription(tenant_id)` بدون
> `service_id`، عبر wrapper `_check_saas_limits`). **الفحص الفعلي لمحتوى
> الكود (مش بس اسم الدالة المشتركة) بيّن إن 5 من الـ13 — `transport`,
> `tourism_sports`, `tenders_auctions`, `social`, `zamakana` — كانوا من
> الأول بيستخدموا `can_access_service(feature)`**، نفس آلية
> `service_marketplace` السليمة (المفلترة بـ`service_id` أصلًا)، مش
> المسار المكسور. يعني **العدد الحقيقي للدومينات المصابة فعليًا بباج
> `get_any_active_subscription` كان 8 بس، مش 12/13** — الافتراض هنا كان
> غير دقيق (خلط بين اسم `_check_saas_limits` المتكرر في كل دومين
> والتنفيذ الداخلي الفعلي المختلف لكل واحد). عمود "الآلية الفعلية" تحت
> مُضاف بأثر رجعي ليعكس الفحص الصحيح — القيم في عمود feature keys لسه
> كما وُثِّقت وقتها (صحيحة، غير متأثرة بهذا التصحيح).

كل دومين بيعرّف نسخته الخاصة (كود مكرر، مش دالة مشتركة). قائمة كل
feature key مُستخدَم فعليًا في الكود:

| الدومين | الملف | feature keys المستخدَمة | الآلية الفعلية |
|---|---|---|---|
| realestate | `app/domains/realestate/service.py` | `real_estate`, `real_estate_development`, `real_estate_tokenization`, `real_estate_smart_contracts` | 🔴 كانت مكسورة (`get_active_subscription(tenant_id)`) — ✅ اتصلحت |
| insurance | `app/domains/insurance/service.py` | `insurance` | 🔴 كانت مكسورة — ✅ اتصلحت |
| employment | `app/domains/employment/service.py` | `hr_management`, `payroll` | 🔴 كانت مكسورة — ✅ اتصلحت |
| invitations | `app/domains/invitations/service.py` | `crm` | 🔴 كانت مكسورة — ✅ اتصلحت |
| logistics | `app/domains/logistics/service.py` | `logistics` | 🔴 كانت مكسورة — ✅ اتصلحت |
| manufacturing | `app/domains/manufacturing/service.py` | `manufacturing` | 🔴 كانت مكسورة — ✅ اتصلحت |
| arbitration_syndicates | `app/domains/arbitration_syndicates/service.py` | `arbitration`, `syndicates` | 🔴 كانت مكسورة — ✅ اتصلحت |
| digital_twin | `app/domains/digital_twin/service.py` | `digital_twin` (مثبّت جوّه الدالة، بدون باراميتر) | 🔴 كانت مكسورة — ✅ اتصلحت |
| transport | `app/domains/transport/service.py` | `transport` | 🟢 **`can_access_service` من الأول — لم تكن مصابة، صفر لمس مطلوب** |
| tourism_sports | `app/domains/tourism_sports/service.py` | `tourism`, `entertainment`, `sports` | 🟢 **`can_access_service` من الأول — لم تكن مصابة، صفر لمس مطلوب** |
| tenders_auctions | `app/domains/tenders_auctions/service.py` | `tenders`, `auctions` | 🟢 **`can_access_service` من الأول — لم تكن مصابة، صفر لمس مطلوب** |
| social | `app/domains/social/service.py` | `social` | 🟢 **`can_access_service` من الأول — لم تكن مصابة، صفر لمس مطلوب** |
| zamakana | `app/domains/zamakana/service.py` | `zamakana` | 🟢 **`can_access_service` من الأول — لم تكن مصابة، صفر لمس مطلوب** |
| service_marketplace | `app/domains/service_marketplace/service.py` | **آلية مختلفة تمامًا** — `can_access_service("service_marketplace")` (بتفحص `saas_tenant_service_access` + `saas_service_catalog` بالكود، مش `plan.features`) | 🟢 سليمة من الأول (نفس آلية الخمسة فوق) |

**دومينات بدون أي بوابة SaaS إطلاقًا** (بحثنا فيها ولقينا صفر استدعاء):
`finance`, `health` — مفتوحة بالكامل من ناحية SaaS gating (قد يكون
متعمد، خارج نطاق هذه الجلسة).

**ملاحظة تصميمية إضافية (لسه صحيحة رغم التصحيح فوق):** `can_access_service`
مسار تحقق مختلف تمامًا عن مسار `get_active_subscription(tenant_id)`
المكسور. ده تناقض معماري قائم مسبقًا (وجود نمطين مختلفين للتحقق تحت نفس
اسم `_check_saas_limits`)، غير مرتبط بباج `get_any_active_subscription`
مباشرة (فعليًا هو اللي **حمى** الخمسة+`service_marketplace` من الباج من
الأساس)، لكنه يعني إن أي توحيد مستقبلي لازم يتعامل مع نمطين مختلفين
فعليًا، مش نمط واحد بانحراف طفيف.

---

## 4) الخلاصة قبل القرار

المشكلة مش "خطة ناقصة feature واحد". هي طبقتين:

1. **باج منطقي حقيقي** في `get_any_active_subscription` (وبالتبعية في كل
   نسخ `_check_saas_limits` الـ12 اللي بتعتمد عليها): بتفترض اشتراك واحد
   شامل لكل tenant، بينما الـschema (والبيانات الفعلية) بتسمح بعدة
   اشتراكات منفصلة لخدمات مختلفة — فبتختار عشوائيًا (بحكم "الأحدث
   زمنيًا") مش حسب الخدمة المطلوبة.
2. **بيانات ديف مبعثرة** بدون أي seed script متعمد — تراكمت من جلسات
   اختبار معزولة، فمفيش "خطة ديف شاملة" واحدة موثوقة تغطي كل الـfeature
   keys الـ21 المستخدَمة فعليًا عبر الكود.

حل الطبقة الثانية بس (تعديل بيانات) هيسكت الأعراض الحالية مؤقتًا لكن
الباج المنطقي هيفضل موجود وهيتكرر تلقائيًا في أي جلسة مستقبلية تنشئ
اشتراك تجريبي جديد لأي دومين (لأنه هيبقى "الأحدث" ويكسر كل الدومينات
التانية بالنسبة لنفس الـtenant).

---

## 5) خيارات القرار (بانتظار اختيار المستخدم — صفر تنفيذ)

- **أ) إصلاح البيانات فقط (سريع، مؤقت):** تحديث `plan.features` لخطة
  الاشتراك الأحدث لـtenant_id=1 (id=90) لتشمل كل الـ21 feature key
  الموثقة أعلاه — أو حذف الاشتراكات الثلاثة الزائدة والإبقاء على واحد
  شامل. بيسكت الأعراض بس الباج المنطقي فاضل.
- **ب) إصلاح الباج المنطقي (جذري):** تعديل `get_any_active_subscription`
  (أو استبدالها بدالة تفحص كل الاشتراكات النشطة للـtenant وتجمع
  features منها، أو تفلتر حسب service المطلوب) — يحتاج قرار معماري
  (single comprehensive plan؟ ولا multi-subscription per service؟) +
  تعديل في مكان واحد يُطبَّق تلقائيًا عبر كل الـ12 دومين.
- **ج) الاثنين معًا:** إصلاح الباج + تنظيف/توحيد بيانات الديف بخطة شاملة
  واحدة نظيفة تحل محل الـ4 اشتراكات المبعثرة الحالية.
- **د) توثيق فقط الآن:** الاكتفاء بهذا التقرير كمرجع، وتأجيل أي تنفيذ
  لجلسة لاحقة منفصلة (حسب قاعدة المشروع: أي تغيير معماري كبير يحتاج
  موافقة صريحة في جلسة منفصلة).

---

## 6) سؤال أمني عاجل مُطلوب من المستخدم — هل `get_any_active_subscription`
   قابل للاستغلال (permissive) ولا false-negative بس؟

**السؤال المحدد:** هل فيه سيناريو حقيقي ممكن تنفيذه فعليًا عبر التطبيق
الحي (مش عبر DB مباشر) يخلي tenant يستخدم feature Y ما اشتركش فيه فعليًا،
بسبب إن اشتراك تاني (لخدمة مختلفة) طلع "الأحدث"؟

### التحليل (قراءة كود فقط، صفر تنفيذ)

**أ) الثغرة البنيوية موجودة فعلاً وهي حقيقية:**
`_check_saas_limits` في كل الـ12 دومين بيثق في "أحدث اشتراك نشط للـ
tenant" (`get_any_active_subscription`، `saas/repository.py:153-169`)
**بدون أي ربط بين الاشتراك المُرجَع وخدمة الدومين المطلوبة فعليًا**. لو
أي `plan.features` احتوى feature من نطاق تاني (زي البيانات الفعلية اللي
لقيناها: plan id=2 مربوط بـ`service_id=2` placeholder، لكن
`features=["real_estate","insurance"]`) — أي tenant عنده اشتراك نشط
لهذه الخطة بالذات (كأحدث اشتراك) هيعدي أي فحص `real_estate` أو
`insurance` بغض النظر عن كونه اشترك فعلاً في خدمة العقارات أو التأمين.
هذا genuine authorization design flaw — نوع "confused deputy": مفيش
تحقق إن الاشتراك المُستخدَم في القرار هو فعلاً مخصص للخدمة المطلوبة.

**ب) لكن — مش قابل للاستغلال فعليًا عبر التطبيق الحي دلوقتي، لسببين
مستقلين بيقفلوا المسار بالصدفة (مش بتصميم أمني متعمد):**

1. **إنشاء الخطط (`plan.features`) مقصور على superuser فقط:**
   `POST /saas/plans` محمي بـ`Depends(get_current_superuser)`
   (`saas/router.py:75-79`). مفيش أي tenant (حتى admin) يقدر يصنع خطة
   بـ`features` مفصّلة على مقاسه.

2. **إنشاء اشتراك جديد (`POST /saas/subscriptions/{plan_id}`) معطّل
   بالكامل حاليًا ببَج منفصل تمامًا (chicken-and-egg):**
   `SaaSControlService.create_subscription` (`saas/service.py:106-134`)
   بينادي `repo.get_plan_by_id(plan_id, tenant_id)`
   (`saas/repository.py:55-75`) — والدالة دي **بتشترط وجود اشتراك ACTIVE/
   TRIAL سابق لنفس الـ`plan_id` بالذات** عشان ترجّع الخطة أصلاً؛ لو معندوش
   (وهو دايمًا معندوش، لأنه بيحاول يشترك لأول مرة)، بترجع `None` →
   `NotFoundError`. يعني **مفيش tenant — ولا حتى admin — يقدر ينشئ أي
   اشتراك جديد عبر الـAPI الحي دلوقتي، لأي خطة كانت**، بصرف النظر عن
   موضوع الـfeatures خالص. الـendpoint كله dead code فعليًا في وضعه
   الحالي (404 مضمون لأي محاولة اشتراك أول مرة).

**النتيجة:** الاشتراكات الأربعة الموجودة فعليًا لـtenant_id=1 (بما فيها
plan id=2 المُختلط) **مستحيل تكون اتعملت عبر أي مسار تطبيق حي أو حتى
لوحة admin موجودة بالكود** — لازم تكون اتحقنت مباشرة في الـDB (سكربت
اختبار بينادي `repo.create_subscription()` مباشرة زي
`tests/test_saas_active_subscription.py:378` و
`tests/test_saas_cancel_subscription_silent_write.py:72`، بيتخطّوا طبقة
الـservice/router بالكامل عن قصد لأغراض الاختبار). مفيش مسار لمهاجم
خارجي أو حتى tenant admin مخترَق يوصل لنفس النتيجة عبر التطبيق نفسه
اليوم.

### الحكم النهائي على السؤال

**لأ — مش permissive/قابل للاستغلال فعليًا اليوم عبر التطبيق الحي.**
أسوأ ما يحصل عمليًا في الوضع الحالي هو **false negative** (رفض غير
مبرر لـfeature مدفوعة فعليًا) — لأن مسار الاستغلال العكسي (tenant
يشترك عمدًا في خطة رخيصة/مش متعلقة بميزة مطلوبة عشان يكسب features
تانية) **محظور بالصدفة** بسبب بَج تاني منفصل تمامًا (`get_plan_by_id`
chicken-and-egg) + قصر إنشاء الخطط على superuser.

**⚠️ تحذير مهم للمستقبل (مش تصعيد عاجل، لكن لازم يُوثَّق كـdependency):**
الثغرة البنيوية (عدم ربط الاشتراك المُختار بخدمة الدومين) **لسه موجودة
كامنة**. لو حد أصلح بَج `get_plan_by_id` مستقبلًا (مثلاً بحذف شرط "لازم
يكون عندك اشتراك سابق لنفس الخطة") **من غير ما يصلح `get_any_active_
subscription` معاه في نفس الوقت**، هيبقى فجأة قابل للاستغلال فعليًا: أي
tenant admin هيقدر يشترك (عبر `POST /subscriptions/{plan_id}` بأي
`plan_id` ظاهر له عبر `GET /services/{id}/plans` — endpoint مفتوح لأي
مستخدم authenticated) في أي خطة catalog موجودة (حتى لو رخيصة/غير
متعلقة)، ولو خطة زي id=2 الحالية (features مختلطة من خدمة تانية) كانت
لسه موجودة في الـcatalog وقت الإصلاح، هيكسب real_estate+insurance مجانًا
بدون ما يشترك فيهم فعليًا. **التوصية: أي إصلاح لـ`get_plan_by_id` لازم
يترافق إجباريًا مع إصلاح `get_any_active_subscription` في نفس الـPR/
الجلسة، وإلا هيتفتح باب تصعيد صلاحيات حقيقي وقتها.**

**التصنيف المقترح:** يُسجَّل كـ"عيب تصميم أمني كامن (latent
authorization design flaw)" في هذا التقرير — مش أولوية أمنية طارئة بنفس
درجة #41 (لأنه غير قابل للوصول اليوم)، لكن **يُمنع دمج أي إصلاح لـ
get_plan_by_id بمعزل عنه**. يُنصح بإضافته كبند صريح في backlog الأمان
العام (مش بس تقرير هذه الجلسة) عشان ميضيعش لو الجلستين اتفصلوا مستقبلًا.

---

## 7) دليل حي إضافي — regression test موجود بالفعل انكسر بنفس الباج

قبل كتابة أي تصميم، شغّلت الملف الموجود أصلًا
`tests/test_saas_active_subscription.py` (كان موثَّق كـ"تحقق حي كامل،
نجاح تام" في جلسة سابقة `saas-control-service-get-active-subscription-fix`،
Backlog #9). النتيجة:

```
FAILED tests/test_saas_active_subscription.py::test_realestate_rent_unit_saas_check_passes
app.core.errors.PermissionDeniedError: Real Estate feature is not included in your current plan.
  at app/domains/realestate/service.py:69, داخل _check_saas_limits
```

**السبب الدقيق مؤكَّد من قراءة `created_at` مباشرة من الـDB:**

| id | plan_id | status | created_at |
|---|---|---|---|
| 89 | 77 (tenders) | ACTIVE | `2026-08-29 20:40:49.865034 UTC` |
| **90** | **78 (auctions)** | **ACTIVE** | **`2026-08-29 20:40:49.865034 UTC`** ← مطابق تمامًا لـ89 بالميكروثانية |
| 50 | 48 | CANCELLED | `2026-08-21 01:05:02` |
| 2 | 2 (real_estate+insurance) | ACTIVE | `2026-08-18 04:08:42` |

id=89 و id=90 اتعملوا في **نفس اللحظة بالضبط** (batch واحد، على الأغلب
سكربت اختبار واحد أنشأهم في نفس الاستدعاء). `ORDER BY created_at DESC
LIMIT 1` مع تعادل تام في التوقيت بيرجع نتيجة **غير محددة فعليًا** (بتعتمد
على ترتيب فيزيائي/فهرسي داخلي في Postgres مش على أي منطق عمل)، ووقعت
على id=90 (features=NULL) بدل id=2. هذا إثبات حي إضافي إن الباج مش نظري
— بيكسر تغطية موثَّقة ومُتحقَّق منها فعليًا سابقًا، دلوقتي وبدون أي تغيير
في الكود من يومها.

هذا الملف نفسه هيكون أداة التحقق الحية الأساسية للتصميم المقترح تحت —
بيغطي `realestate.rent_unit` و`insurance.subscribe` بمنطق حقيقي (بلا
`monkeypatch` على `_check_saas_limits` نفسها)، فنجاحه بعد الإصلاح دليل
مباشر مش استنتاج.

---

## 8) التصميم المقترح الكامل — إصلاح `_check_saas_limits` عبر الـ12 دومين

> **الحالة: تصميم فقط، صفر تنفيذ.** بانتظار موافقة صريحة قبل أي كتابة
> فعلية على الكود.

### 8.1) توقيع الدالة الجديدة الكامل

#### طبقة الـrepository — `app/domains/saas/repository.py`

تُحذف: `get_any_active_subscription(self, tenant_id: int) -> Optional[TenantSubscription]`
(السطور 153-169 الحالية — الجذر المباشر للباج).

تُضاف بدلها:

```python
async def get_all_active_subscriptions(
    self,
    tenant_id: int,
) -> List[TenantSubscription]:
    """كل اشتراكات الـtenant النشطة/التجريبية عبر كل الخدمات — بديل
    get_any_active_subscription القديمة اللي كانت بترجع 'الأحدث زمنيًا'
    فقط (صف واحد) وبتكسر أي tenant عنده أكتر من اشتراك فعّال لخدمات
    مختلفة في نفس الوقت. تعدد الاشتراكات النشطة لنفس الـtenant حالة
    طبيعية ومتوقعة في هذا الـschema (كل خدمة ليها اشتراكها المستقل عبر
    saas_tenant_subscriptions.plan_id → saas_service_plans.service_id)
    — مش استثناء نادر لازم نتعامل معاه كـ'صف واحد بس'.

    ⚠️ تحذير للمستقبل: لو حد فكّر يرجّع لمنطق 'صف واحد بس' (مثلاً
    لتحسين أداء)، لازم يتأكد إن أي استخدام جديد بيفلتر بالخدمة/الميزة
    المطلوبة أولًا (زي get_active_subscription(tenant_id, service_id)
    الموجودة فعلًا تحت في نفس الملف) — مش يرجع لـ'أحدث اشتراك بغض النظر
    عن الخدمة'، وهو بالظبط الباج اللي بيتصلح هنا."""
    result = await self.db.execute(
        select(TenantSubscription)
        .where(
            and_(
                TenantSubscription.tenant_id == tenant_id,
                TenantSubscription.status.in_(["ACTIVE", "TRIAL"]),
            )
        )
    )
    return list(result.scalars().all())
```

**ملاحظة توافق:** الدالة `get_active_subscription(self, tenant_id, service_id)`
الموجودة فعلًا (السطور 133-149 الحالية، بتفلتر صح بـ`service_id` عبر
`JOIN ServicePlan`) **تفضل زي ما هي بدون تعديل** — هي مُستخدَمة بشكل
صحيح أصلًا في `create_subscription` (فحص "هل عندك اشتراك نشط لهذه
الخدمة بالفعل") و`can_access_service`. المشكلة كانت حصريًا في
`get_any_active_subscription` (بدون `service_id`)، مش في الدالة المسمّاة
بشكل مشابه دي — الاسمان متقاربان بشكل مربك، فا وضّحت الفرق صراحة في
الـdocstring الجديد.

#### طبقة الـservice — `app/domains/saas/service.py` (`SaaSControlService`)

تُحذف: `get_active_subscription(self, tenant_id: int) -> Optional[TenantSubscription]`
(السطور 102-104 الحالية — wrapper صرف حول الدالة المحذوفة فوق).

تُضاف بدلها (التفاصيل الكاملة للمنطق في القسم 8.2 تحت):

```python
async def check_feature_access(
    self,
    tenant_id: int,
    feature: str,
) -> "FeatureAccessCheck":
    ...
```

### 8.2) منطق `check_feature_access` بالتفصيل الكامل

الاسم المقترح: **`check_feature_access`** (مش `has_feature_access`) —
السبب: القيمة المرجعة مش bool بسيط (راجع القسم 8.3)، فاسم بادئ بـ`has_`
هيوهم القارئ إنها بترجع bool. `check_` أنسب لدالة بترجع نتيجة غنية.

```python
async def check_feature_access(
    self,
    tenant_id: int,
    feature: str,
) -> FeatureAccessCheck:
    """يفحص هل عند الـtenant صلاحية استخدام feature معيّن، عبر union كل
    اشتراكاته النشطة/التجريبية الحالية (مش 'الأحدث' بس).

    المنطق:
    1. يجيب كل الاشتراكات النشطة/التجريبية للـtenant (بغض النظر عن
       الخدمة — هذا هو الفرق الجوهري عن get_active_subscription(tenant_id,
       service_id) المستخدَمة في أماكن تانية، واللي بتحتاج معرفة service_id
       مسبقًا. هنا مش عندنا service_id — عندنا اسم feature حر مُعرَّف على
       مستوى الكود في كل دومين (زي 'real_estate_tokenization')، مش
       مربوط بجدول service catalog رسميًا. لذلك الفلترة الوحيدة الممكنة
       فعليًا دلوقتي هي 'كل الاشتراكات النشطة'، ثم فحص عضوية الـfeature
       داخل features array كل واحد منها على حدة).
    2. لو مفيش ولا اشتراك نشط واحد → NO_ACTIVE_SUBSCRIPTION.
    3. لو فيه اشتراك واحد أو أكتر، لكن ولا واحد منهم عنده plan محمّل
       بشكل سليم (سيناريو نادر: plan_id بيشاور على صف محذوف — تكامل
       بيانات معطوب) أو عنده plan لكن الـfeature مش موجودة في features
       array بتاعه → FEATURE_NOT_INCLUDED.
    4. أول ما نلاقي اشتراك واحد (subscription.plan.features يحتوي
       الـfeature المطلوب) → GRANTED فورًا (short-circuit، مفيش داعي
       نكمل فحص الباقي).

    ⚠️ حدود متعمدة لهذا التصميم (وليست عيوبًا خفية): الدالة دي **مش**
    بتتحقق إن الاشتراك اللي منحك الـfeature هو فعلًا اشتراك لنفس 'خدمة'
    الدومين اللي بتطلب الفحص (زي احتمالية plan.features تحتوي feature
    من نطاق خدمة تانية بالغلط — راجع القسم 6 من هذا التقرير، 'عيب
    تصميم أمني كامن'). حل هذه النقطة يحتاج ربط رسمي feature→service_id
    (مش موجود في الـschema الحالي)، وهو خارج نطاق هذا الإصلاح المحدد —
    هذا الإصلاح بيعالج الـfalse negative (رفض غير مبرر) بس، مش
    الـconfused-deputy الكامن (غير قابل للاستغلال حاليًا كما وثّقنا)."""
    subscriptions = await self.repo.get_all_active_subscriptions(tenant_id)
    checked_ids = [cast(int, s.id) for s in subscriptions]

    if not subscriptions:
        return FeatureAccessCheck(
            status=FeatureAccessStatus.NO_ACTIVE_SUBSCRIPTION,
            tenant_id=tenant_id,
            feature=feature,
            checked_subscription_ids=checked_ids,
        )

    for sub in subscriptions:
        plan_features = sub.plan.features if sub.plan else None
        if plan_features and feature in plan_features:
            return FeatureAccessCheck(
                status=FeatureAccessStatus.GRANTED,
                tenant_id=tenant_id,
                feature=feature,
                checked_subscription_ids=checked_ids,
                granting_subscription_id=cast(int, sub.id),
            )

    return FeatureAccessCheck(
        status=FeatureAccessStatus.FEATURE_NOT_INCLUDED,
        tenant_id=tenant_id,
        feature=feature,
        checked_subscription_ids=checked_ids,
    )
```

**كيف بيتفلتر بالضبط ("بالخدمة/الميزة المطلوبة تحديدًا")؟** الفلترة
الفعلية بتحصل على مستوى الـ`feature` (string membership داخل
`plan.features` JSON array لكل اشتراك على حدة)، مش على مستوى `service_id`
— لأن الاستدعاء الأصلي من كل دومين أصلًا بيمرر `feature` string بس (زي
`"real_estate_tokenization"`)، مش `service_id`. يعني: بدل ما نختار
اشتراك واحد "عشوائيًا" ثم نفحص فيه بس، بقينا **نلف على كل الاشتراكات
النشطة ونفحص كل واحد منهم لوحده** لحد ما نلاقي واحد فعلاً بيمنح الـfeature
المطلوب — وده بالظبط الفرق الجوهري عن السلوك القديم (فحص "الأحدث" بس).

### 8.3) شكل القيمة المرجعة — ليه enum/dataclass أفضل من bool بسيط

**الحالات الثلاث المطلوب تمييزها:**
- (أ) لا يوجد اشتراك نشط إطلاقًا للـtenant.
- (ب) يوجد اشتراك نشط واحد أو أكتر، لكن ولا واحد منهم عنده الـfeature
  المطلوبة ضمن `features`.
- (ج) يوجد اشتراك نشط والـfeature موجودة ضمن `features` بتاعه.

**لماذا bool بسيط (`True`/`False`) غير كافٍ هنا:**

```python
# ❌ لو رجّعنا bool بسيط:
async def has_feature_access(self, tenant_id: int, feature: str) -> bool:
    ...
    return False  # مين بيعرف: (أ) ولا (ب)؟ الاستدعاء مايقدرش يميّز
```

لو الدالة رجّعت `False` بس، الكود المستدعي (كل نسخ `_check_saas_limits`)
هيضطر يرجع لنفس المشكلة الأصلية — يحتاج يعمل استعلام تاني بنفسه عشان
يعرف "هل أعرض على المستخدم 'مفيش اشتراك خالص' ولا 'اشتراكك الحالي مش
شامل هذه الميزة'؟" — رسالتين مختلفتين تمامًا من ناحية تجربة المستخدم
(الأولى بتقول "اشترك"، التانية بتقول "رقّي خطتك"). النسخة القديمة من
الكود (12 مرة مكررة) كانت أصلًا بتفرّق بين الحالتين (`"No active
subscription found."` مقابل `"X feature is not included..."`) —
الرجوع لـbool بسيط هيفقد هذا التمييز اللي كان موجود أصلًا، وهيبقى
تراجع (regression) في تجربة المستخدم، مش مجرد تبسيط بريء.

**زيادة على كده:** أثناء التحقيق في هذه الجلسة، ضيّعنا وقت فعلي في
معرفة *أي اشتراك بالظبط* اتفحص واختير (id=90 مش id=2) — لو الدالة كانت
من الأساس بترجع بس `True`/`False`، محدش كان هيقدر يعرف السبب الجذري من
غير قراءة الكود والدخول للـDB يدويًا زي ما عملنا. لذلك ضفت
`checked_subscription_ids` و`granting_subscription_id` في القيمة
المرجعة — مش للاستخدام في رسالة الخطأ للمستخدم النهائي، لكن كـhook جاهز
لأي `logger.debug`/`logger.warning` مستقبلي لو نفس نوع اللغز اتكرر (توفّر
تمامًا نوع المعلومة اللي احتجناها اليوم بالضبط).

**التصميم المقترح: enum + dataclass صغير، مش tuple خام:**

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class FeatureAccessStatus(str, Enum):
    GRANTED = "granted"
    NO_ACTIVE_SUBSCRIPTION = "no_active_subscription"
    FEATURE_NOT_INCLUDED = "feature_not_included"


@dataclass(frozen=True)
class FeatureAccessCheck:
    status: FeatureAccessStatus
    tenant_id: int
    feature: str
    checked_subscription_ids: List[int] = field(default_factory=list)
    granting_subscription_id: Optional[int] = None

    @property
    def granted(self) -> bool:
        return self.status == FeatureAccessStatus.GRANTED
```

**ليه `enum` + `dataclass` مش `tuple` خام (زي `(bool, str)` أو
`(subscription, features)` القديمة)؟**
- **Tuple خام بيعتمد على الترتيب الصحيح للعناصر** — أي حد يستخدم
  `result[0]` بدل `result.granted` غلط بسهولة وبصمت (النوع مايشتكيش،
  التنفيذ يكمل بمنطق غلط). النسخة القديمة كانت أصلًا بترجع
  `subscription, features` (tuple فعلي) — ومحدش من الـ12 دومين كان
  فعليًا بيستخدم القيمة المرجعة دي (تأكدنا بالـgrep، القسم 8.4 تحت)،
  يعني كانت "قيمة مرجعة ميتة" من الأساس، درس إضافي ليه الـtuple الضمني
  مش شكل جيد للتواصل بين الطبقات.
- **`enum` بيمنع قيم غير صالحة عند وقت الكتابة** (IDE/type-checker
  هيرفض `status == "grnted"` بغلطة إملائية، بعكس string خام).
- **`dataclass` بيديك أسماء حقول واضحة** (`.status`, `.granted`,
  `.granting_subscription_id`) بدل الاعتماد على مواضع الـtuple، ومهيأ
  لإضافة حقل جديد مستقبلًا (زي `checked_at: datetime` لو احتجنا) من
  غير ما نكسر أي كود مستخدِم موجود (كل الاستخدامات بالاسم، مش بالموضع).
- **الخاصية `.granted`** بتدّي أبسط استخدام ممكن للحالة الشائعة (`if not
  check.granted: raise ...`) من غير ما تفقد التفاصيل الغنية لو احتجتها
  دالة تانية مستقبلًا.

### 8.4) تحديث الـ12 دومين — مثال كامل + توضيح الفرق عن القديم

مثال `realestate/service.py:60-70` (النمط مطابق حرفيًا في الـ11 ملف
الباقيين، بس تتغيّر رسالة الخطأ حسب الدومين):

```python
# قبل (الحالي):
async def _check_saas_limits(self, tenant_id: int, feature: str = "real_estate"):
    saas = SaaSSubscriptionService(self.db, tenant_id)
    subscription = await saas.get_active_subscription(tenant_id)  # type: ignore
    if not subscription:
        raise PermissionDeniedError("No active subscription found.")
    if not subscription.plan:
        raise PermissionDeniedError("No valid subscription plan found.")
    features = subscription.plan.features or []
    if feature not in features:
        raise PermissionDeniedError("Real Estate feature is not included in your current plan.")
    return subscription, features  # ⚠️ قيمة مرجعة ميتة — صفر استدعاء بيستخدمها فعليًا (تأكدنا بالـgrep عبر الـ12 دومين)


# بعد (المقترح):
async def _check_saas_limits(self, tenant_id: int, feature: str = "real_estate"):
    saas = SaaSSubscriptionService(self.db, tenant_id)
    check = await saas.check_feature_access(tenant_id, feature)
    if check.status == FeatureAccessStatus.NO_ACTIVE_SUBSCRIPTION:
        raise PermissionDeniedError("No active subscription found.")
    if check.status == FeatureAccessStatus.FEATURE_NOT_INCLUDED:
        raise PermissionDeniedError("Real Estate feature is not included in your current plan.")
    # check.status == GRANTED → يكمل عادي، صفر return (مفيش أي مكان بيستخدم القيمة القديمة)
```

**ملاحظتان مهمتان اكتشفتهم أثناء صياغة هذا المثال:**
1. الرسالتان النصيتان **نفسهم بالحرف** زي الكود الحالي — صفر تغيير في
   نص أي رسالة خطأ يشوفها المستخدم النهائي. الفرق الوحيد: مصدر القرار
   (union الاشتراكات بدل "الأحدث فقط")، مش صياغة الرسائل. هذا يحسم
   تريد-أوف "دمج الرسائل في واحدة" المطروح في القسم السابق من الجلسة —
   **مش محتاجين ندمجهم أصلًا**، الـenum بيحافظ على الثلاثة بالظبط
   (`NO_ACTIVE_SUBSCRIPTION` → رسالة 1، `FEATURE_NOT_INCLUDED` → رسالة
   2، `GRANTED` → استمرار عادي بدون رسالة) — نفس السلوك الملحوظ الخارجي
   القديم 100%، تصحيح داخلي بس.
2. الحالة الثالثة القديمة (`if not subscription.plan: raise
   PermissionDeniedError("No valid subscription plan found.")`) دُمجت
   ضمن `FEATURE_NOT_INCLUDED` في التصميم الجديد (لأن اشتراك بدون plan
   محمّل مايقدرش يمنح أي feature أصلًا، فبيتفحص وبيفشل بنفس نتيجة "الميزة
   مش موجودة" منطقيًا). هذا فرق سلوكي **دقيق جدًا** (رسالة مختلفة في
   سيناريو نادر جدًا — تلف بيانات: `plan_id` بيشاور على صف محذوف) —
   أذكره صراحة عشان موافقتك عليه تحديدًا، مش بس على التصميم العام. لو
   عايز نحافظ على الرسالة الثالثة منفصلة تمامًا، سهل نضيف حالة رابعة
   للـenum (`SUBSCRIPTION_PLAN_MISSING`) — بس شخصيًا مش شايفها لازمة
   (سيناريو تلف بيانات نادر، والرسالة الحالية "الميزة مش متاحة" كافية
   وصحيحة تقنيًا في هذه الحالة كمان).

**تأكيد "القيمة المرجعة الميتة":** فحصت بالـgrep كل استدعاءات
`_check_saas_limits` عبر الـ12 دومين (26+ موقع استدعاء) — **صفر واحد**
بيعمل `subscription, features = await self._check_saas_limits(...)` أو
أي شكل تاني بيستخدم القيمة المرجعة. كلهم `await
self._check_saas_limits(tenant_id, "...")` كـstatement مستقل. يعني حذف
الـ`return subscription, features` من التصميم الجديد **صفر تأثير** على
أي كود موجود.

### 8.5) خطة الانتقال — كل الـ12 دومين دفعة واحدة، مش تدريجيًا

**التوصية: دفعة واحدة، commit واحد.** الأسباب:

1. **التغيير في الطبقة المشتركة إجباري الذرّية (atomic) بطبيعته.**
   بمجرد ما نحذف `SaaSControlService.get_active_subscription(tenant_id)`
   ونستبدلها بـ`check_feature_access`، أي دومين من الـ12 **لسه بيستخدم
   الاسم القديم** هيكسر فورًا بـ`AttributeError` عند أول استدعاء —
   مش "سلوك قديم أبطأ" أو "تحذير" ممكن نتعايش معاه لحد ما نكمل باقي
   الدومينات. مفيش شكل "تدريجي آمن" غير الإبقاء على الدالتين معًا
   مؤقتًا (`get_active_subscription` القديمة + `check_feature_access`
   الجديدة جنبًا لجنب) كـcompatibility shim — وده **يتعارض مباشرة** مع
   قاعدة المشروع الصريحة ("Don't use feature flags or backwards-
   compatibility shims when you can just change the code")، وهيسيب
   الباج الأصلي شغّال فعليًا في أي دومين لسه بيستخدم المسار القديم لحد
   ما نوصله.

2. **الدومينات الـ12 كلهم مكشوفين لنفس الباج بالفعل، دلوقتي، بغض النظر
   عن أي ترتيب تنفيذ.** إصلاح 2 وترك 10 معلّقين لجلسة تانية معناه 10
   دومينات فاضلة بالضبط بنفس الخطورة اللي بدأنا نتحقق منها النهارده —
   التأجيل هنا مابيقللش المخاطرة، بيأجّلها بس من غير أي فايدة موازية
   (مفيش "وقت مراقبة" أو "rollout تدريجي" له معنى في تغيير منطقي داخلي
   زي ده، بعكس مثلًا feature تواجه المستخدم النهائي بشكل مباشر ومحتاجة
   قياس تأثير حقيقي بالتدريج).

3. **التعديل ميكانيكي وموحّد** (نفس الـ3 أسطر بالحرف تتغير في كل ملف،
   راجع القسم 8.4) — مش منطق معقد مختلف لكل دومين يستاهل مراجعة منفصلة
   بطيئة لكل واحد. المشروع عنده سابقة موثَّقة مباشرة لنفس النمط: جلسة
   "frontend mechanical fix pass1" (راجع الذاكرة) أصلحت نفس نوع الباج
   الميكانيكي المتكرر عبر 23 دومين فرونت إند في جلسة واحدة.

4. **أداة تحقق حية جاهزة فعلًا** (`test_saas_active_subscription.py`)
   بتغطي دومينين مباشرة (realestate + insurance) بمنطق حقيقي بلا
   monkeypatch على الفحص نفسه — تكفي لإثبات صحة الطبقة المشتركة
   (`repository` + `service`) بشكل قاطع. الدومينات الـ10 الباقية
   بتستخدم **نفس الطبقة المشتركة بالحرف** (نفس `check_feature_access`)
   — بمجرد ما نثبت الطبقة المشتركة صح حيًا مرتين، صحتها في الباقي مضمونة
   منطقيًا (نفس الكود بالظبط)، والفرق الوحيد بينهم هو رسائل الخطأ
   النصية وأسماء الـfeatures الممرّرة (تفاصيل ثابتة، صفر منطق).

**لكن — "دفعة واحدة" مش يعني "بلا تحقق فردي لكل دومين":** هعمل لكل
الـ12 ملف بعد التعديل:
- فحص `import`/syntax سليم (`python -c "import app.domains.X.service"`
  أو ما يعادله) للتأكد من صفر خطأ كتابة أثناء التعديل الميكانيكي.
- تشغيل أي regression test موجود فعلًا لكل دومين (مش كلهم عندهم تغطية
  مباشرة زي realestate/insurance — هوثّق بدقة أي دومين اتحقق منه حيًا
  مقابل أي دومين اتأكد منه بصريًا/باستيراد بس، بنفس منهجية الشفافية
  المتبعة في تقارير الجلسات السابقة).
- تشغيل `test_saas_active_subscription.py` كامل كدليل حي أساسي قبل أي
  commit.

### 8.6) رأيي الصريح — تنظيف بيانات tenant_id=1 (وفحص tenant_id=16):
   جزء من هذا التصميم، ولا خطوة تالية منفصلة؟

**رأيي: خطوة منفصلة تمامًا، بعد الإصلاح الكودي، وبموافقة صريحة إضافية
خاصة بيها — مش جزء من نفس الـcommit، ومش حتى نفس نوع القرار.** الأسباب:

1. **الإصلاح الكودي المقترح فوق لا يعتمد على تنظيف البيانات إطلاقًا —
   وده مقصود، مش صدفة.** جوهر التصميم هو الانتقال من "افحص اشتراك واحد
   مختار عشوائيًا" إلى "افحص union كل الاشتراكات النشطة". بيانات
   tenant_id=1 الحالية (4 اشتراكات مبعثرة) **هي بالظبط الحالة اللي
   التصميم الجديد مصمَّم يتعامل معها بشكل صحيح** — مش عائق قدامه.
   `check_feature_access(1, "real_estate")` هيلاقي id=2 ضمن الـunion
   ويرجع `GRANTED` **حتى لو ماحدش لمس أي صف في الـDB خالص**. لو
   نظّفنا البيانات في نفس الوقت اللي بنغيّر فيه الكود، مش هنقدر نميّز
   إثباتيًا "الفحص نجح بسبب الكود ولا بسبب البيانات؟" — وده بالظبط نوع
   الغموض اللي القسم 7 فوق حاول يتجنبه (الإثبات الحي المباشر لازم يكون
   قاطع السبب).

2. **فئة مخاطرة مختلفة تمامًا، مش مجرد "خطوة تانية في نفس القائمة".**
   تعديل الكود قابل للمراجعة بالـdiff، وقابل للتراجع الكامل بـ`git
   revert` لو طلع فيه خطأ. عمليات حذف/دمج صفوف في `saas_tenant_
   subscriptions` (DML على DB مشتركة) **مش قابلة للتراجع بنفس الطريقة**
   — `git revert` مش هيرجّع صف اتحذف من الـPostgres. قاعدة المشروع
   نفسها بتفرّق بين النوعين ("قبل أي عملية ممكن تمسح شغل غير محفوظ...
   شغّل git status... واعمل stash" — نفس المنطق بينطبق بشكل أقوى على
   حذف DB rows، مش ملفات).

3. **"التنظيف" نفسه محتاج تصميم منفصل قبل أي تنفيذ — مش عملية واضحة
   المعالم دلوقتي.** إيه بالظبط معنى "نظيف" هنا؟ خيارات مطروحة أصلًا في
   القسم 5 (أ/ب/ج) بس محتاجة قرار إضافي أدق: هل ندمج الأربعة في اشتراك
   واحد "شامل" (يرجع لافتراض التصميم القديم الخاطئ أصلًا — "اشتراك واحد
   شامل لكل tenant" هو نفسه الافتراض اللي سبب الباج من الأول)؟ ولا نسيب
   تعدد الاشتراكات (الحالة الصحيحة معماريًا بعد الإصلاح) بس نصلّح خطة
   id=2 تحديدًا (features مختلطة تحت service_id=2 غير متعلق)؟ ولا نحذف
   الاشتراكات الميتة/CANCELLED بس (id=50) ونسيب الباقي؟ كل خيار بيؤدي
   لنتيجة نهائية مختلفة، وكل واحد يستاهل نفس مستوى "اعرض التصميم قبل
   التنفيذ" اللي طبّقناه على إصلاح الكود، مش قرار سريع يتاخد كجزء من
   commit تاني.

4. **tenant_id=16 لسه مش مفحوص بالعمق المطلوب أصلًا.** عندنا بس قائمة
   الاشتراكات (3 اشتراكات، plan_id=2/47/48) من فحص أولي — لسه محتاجين
   نفس مستوى الفحص اللي عملناه لـtenant_id=1 (هل نفس نمط الـcreated_at
   المتطابق موجود؟ هل فيه tenant آخرين غير 1 و16 أصلًا؟) قبل أي قرار
   تنظيف شامل. ده بحد ذاته خطوة تحقيق منفصلة قبل أي تنفيذ، مش تفصيلة
   صغيرة تتضاف لنفس الـcommit.

**خلاصة التسلسل المقترح (يتوافق مع ترتيبك الأصلي في الرسالة السابقة):**
① اعتماد هذا التصميم → ② تنفيذ الإصلاح الكودي وحده + تحقق حي (نفس
`test_saas_active_subscription.py` بيانه الحالي الفوضوي بالضبط، بدون
لمس البيانات) → ③ **بعد ما نثبت حيًا إن الكود لوحده كافي**، نفتح جلسة
تحقيق فرعية قصيرة لتصميم "التنظيف" (تشمل فحص tenant_id=16 بعمق) كخطوة
منفصلة واضحة، بموافقة صريحة إضافية عليها تحديدًا.

---

## 9) الحالة الفعلية عند إعادة الفحص [2026-08-31، جلسة متابعة]

**السؤال:** هل التصميم في القسم 8 اتنفذ فعليًا (repository.py + service.py
+ الـ12 دومين) + `test_saas_active_subscription.py` اتشغّل؟

### 9.1) طبقة `saas/repository.py` + `saas/service.py` — ✅ منفَّذة بالكامل ومطابقة للتصميم حرفيًا

تحقّق مباشر بـ`git diff`:
- `saas/repository.py`: `get_any_active_subscription` (الأحدث فقط، `LIMIT 1`)
  اتشالت بالكامل، واتحلّت محلها `get_all_active_subscriptions` بالضبط زي
  §8.1 (بدون `ORDER BY`/`LIMIT`، بترجع `List[TenantSubscription]` كامل).
- `saas/service.py`: `FeatureAccessStatus` (enum) و`FeatureAccessCheck`
  (`dataclass(frozen=True)` + خاصية `.granted`) مُضافين حرفيًا زي §8.3،
  و`check_feature_access` مُنفَّذة حرفيًا زي §8.2 (نفس منطق الـloop + الـ
  short-circuit + `checked_subscription_ids`/`granting_subscription_id`).
  الدالة القديمة `get_active_subscription(self, tenant_id)` (wrapper
  الـ8 دومين) اتشالت بالكامل.

### 9.2) الدومينات — ✅ 8 دومين اتصلّحوا فعليًا (مش 12/13 زي ما كان متوقَّع في وقت التصميم)

`git status` + فحص محتوى كل ملف يأكد: **`realestate`, `insurance`,
`employment`, `invitations`, `logistics`, `manufacturing`,
`arbitration_syndicates`, `digital_twin`** — كل الـ8 فيهم `_check_saas_limits`
بقت بتنادي `saas_service.check_feature_access(tenant_id, feature)` وتفحص
`FeatureAccessStatus.NO_ACTIVE_SUBSCRIPTION`/`FEATURE_NOT_INCLUDED` بالضبط
زي مثال §8.4، ونص رسائل الخطأ للمستخدم النهائي **متطابق حرفيًا** مع القديم
(صفر تغيير ملحوظ خارجيًا، بالضبط كما وُعِد). الاستيراد
`from app.domains.saas.service import ..., FeatureAccessStatus` موجود
وسليم في الـ8 ملفات كلهم.

**🔍 اكتشاف مهم يصحّح افتراض التصميم الأصلي:** القسم 3 فوق كان مفترض إن
`transport`, `tourism_sports`, `tenders_auctions`, `social`, `zamakana`
(5 دومينات من أصل الـ13 المسرودة) كانوا بيستخدموا نفس المسار المكسور
(`get_active_subscription(tenant_id)` بدون `service_id`). **الفحص المباشر
لمحتوى الكود الفعلي (مش git diff، لأن الملفات دي أصلًا بلا أي تعديل) بيّن
إن الخمسة دول كانوا من الأول بيستخدموا `can_access_service(feature)`** —
نفس آلية `service_marketplace` اللي القسم 3 وصفها كـ"استثناء وحيد بآلية
مختلفة تمامًا" — مش المسار المكسور. `can_access_service` بتستخدم
`get_active_subscription(tenant_id, service_id)` (بمعاملين، الدالة اللي
القسم 8.1 نفسه قال صراحة إنها "سليمة أصلًا وتفضل زي ما هي") — يعني الخمسة
دومينات دول **ما كانوش فعليًا مصابين بالباج من الأساس**، رغم ظهورهم في
جدول القسم 3. تصنيف التقرير الأصلي لهم كان غير دقيق (خلط بين اسم الدالة
المشتركة `_check_saas_limits` في كل دومين وآلية التحقق الداخلية الفعلية
اللي بتستخدمها — الاسم متشابه، التنفيذ الداخلي مختلف). **النتيجة: صفر
لمس مطلوب على الخمسة دول — مش نقص تنفيذ، كانوا أصلًا سليمين.** هذا يعدّل
عدد الدومينات "المصابة فعليًا" من 12/13 إلى **8 بالظبط** — العدد ده
يتوافق تمامًا مع عدد الملفات اللي `git status` أظهرها معدّلة.

`service_marketplace` نفسها: صفر لمس (متوقَّع، مسرودة صراحة في §8 كاستثناء).
`health`/`finance`: صفر بوابة SaaS من الأساس (زي ما وثّق القسم 3) — ملف
`health/service.py` ظهر معدَّل في `git status` لكن من جلسة تانية تمامًا
(تحويل Decimal-as-string، سابقة على هذه الجلسة) — صفر علاقة بموضوعنا هنا.

### 9.3) نتيجة تشغيل `test_saas_active_subscription.py` الفعلي (2026-08-31)

```
./venv/Scripts/python.exe -m pytest tests/test_saas_active_subscription.py -v
```

```
test_realestate_rent_unit_saas_check_passes                                    FAILED
test_insurance_subscribe_saas_check_passes                                     PASSED
test_realestate_buy_fractional_ownership_saas_check_passes_then_hits_known_bug FAILED
test_insurance_review_claim_saas_check_passes_then_hits_known_bug              PASSED
2 passed, 2 failed
```

**الحكم المهم: الفشلان الاتنين مش رجوع لباج #9 (باج الـSaaS نفسه) —**
`_check_saas_limits` عدّت بنجاح **في الأربعة اختبارات كلهم بلا استثناء**
(صفر `PermissionDeniedError` بخصوص "feature is not included"/"No active
subscription"). الإصلاح شغّال 100%. الفشلان راجعين لباجات تانية تمامًا،
مش متعلقين بالـSaaS إطلاقًا:

1. **`test_realestate_rent_unit_saas_check_passes`** — العدّاء وصل بعد
   الـSaaS check لسطر `app/domains/realestate/service.py:453`:
   `PermissionDeniedError("انت مش مالك الوحدة اللي عايز تأجرها")`. السبب:
   الاختبار بيستخدم `EXISTING_LAND_ASSET_ID = 1` (أصل أرض ثابت موجود
   مسبقًا في قاعدة بيانات الديف)، لكن **مالكه الفعلي المخزَّن مش نفس
   `landlord` المستخدم الجديد اللي الاختبار بينشئه** — الاختبار افترض
   ملكية مالكش يثبتها فعليًا. هذا الاختبار **قبل إصلاح باج #9 كان بيفشل
   دايمًا عند سطر الـSaaS check الأول (`PermissionDeniedError: Real
   Estate feature is not included`)** — يعني الوصول لسطر التحقق من
   الملكية دلوقتي هو **أول مرة الكود يوصل هناك أصلًا** بعد الإصلاح.
   الباج ده كان **مقنّع بالكامل** ورا باج #9 القديم، مش تراجع جديد
   سببه هذه الجلسة. **يحتاج تحقيق منفصل** (هل بيانات الديف لأصل الأرض
   id=1 قديمة/غلط، ولا الاختبار نفسه ناقص خطوة تعيين ملكية صريحة قبل
   استدعاء `rent_unit`؟) — خارج نطاق `saas-feature-flags-drift` تمامًا.

2. **`test_realestate_buy_fractional_ownership_...`** — الاختبار بيتوقع
   صراحة (بتعليقه الخاص وبـ`pytest.raises(TypeError, match="tenant_id")`)
   إنه يكراش بباج قديم موثَّق (Backlog #16). لكن الاستثناء الفعلي اللي
   طلع دلوقتي `NotFoundError("وكيل 2 غير موجود")` من
   `app/domains/ai_agents/service.py:161` — مش `TypeError`. يعني **باج
   Backlog #16 القديم اللي الاختبار مبني عليه يبدو إنه اتصلح فعلًا في
   جلسة تانية** (خارج نطاق هذه الجلسة، لم أتحقق من أيها)، فالكود بقى
   يوصل أعمق ويصطدم ببيانات ديف ناقصة (`AI Agent id=2` مش موجود في DB
   الديف الحالية) بدل الباج القديم. تصنيف الاختبار (`_then_hits_known_bug`)
   بقى **قديم/غير دقيق** بالنسبة لحالة الكود الحالية — يحتاج تحديث
   لاحقًا (إما تحديث الـ`pytest.raises` المتوقَّع، أو seed لـAI Agent
   id=2)، **مش متعلق بـSaaS إطلاقًا**.

**الخلاصة النهائية:** طبقة `saas/repository.py` + `saas/service.py` +
الـ8 دومينات المصابة فعليًا **منفَّذة بالكامل ومُتحقَّق منها حيًا** —
باج #9 (`get_any_active_subscription` بترجع "الأحدث" بغض النظر عن
الخدمة) **مُصلَح تمامًا ومُثبَت بدليل تشغيل حي**. الفشلان المتبقيان في
`test_saas_active_subscription.py` باجات مستقلة تمامًا (ملكية أرض في
بيانات ديف، وseed ناقص لـAI Agent) اتكشفوا **بسبب** نجاح إصلاح #9 (كانوا
مقنّعين وراه)، مش نتيجة له — **صفر لمس عليهم في هذه الجلسة**، يحتاجوا
بند backlog منفصل لكل واحد. القسم 8.6 (تنظيف بيانات tenant_id=1/16)
لسه **مفتوح تمامًا زي ما هو** — لم يُلمس، بانتظار موافقة صريحة منفصلة
كما حدد القسم نفسه.

**الحالة النهائية لهذه الجلسة:** 🟢 **التصميم (§8) مُنفَّذ بالكامل ومُتحقَّق
منه حيًا لكل الدومينات المصابة فعليًا (8، مش 12/13) — صفر عمل متبقٍ على
تصميم §8 نفسه.** 🟡 **مفتوح (بنود backlog منفصلة جديدة):** ملكية أرض
`EXISTING_LAND_ASSET_ID=1` في بيانات الديف، وseed ناقص لـ`AI Agent id=2`.
🟡 **مفتوح (زي ما كان):** تنظيف بيانات tenant_id=1/16 (§8.6)، الثغرة
الأمنية الكامنة في §6، باج mojibake في أسماء الخدمات، فحص tenant_id=16
بعمق.
