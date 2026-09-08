# تقرير جلسة — تدقيق بيانات: خريطة Plans ↔ Services (Dev DB)

**تاريخ الجلسة:** 2026-09-07
**النطاق:** فحص read-only بحت على مستوى البيانات في dev DB. **لا يوجد أي تعديل كود، ولا أي migration، ولا أي تعديل على أي جدول** — الجلسة بالكامل عبارة عن استعلامات `SELECT` مباشرة عبر `asyncpg` على قاعدة `eppne_v2` (`postgresql://127.0.0.1:5435/eppne_v2`, من `eppne-backend/.env`).

---

## 1. مصدر البيانات (الجداول الفعلية)

الجدولان الأساسيان اللي بيطابقا وصف المهمة ("plans" بحقل `features`، و"services" اللي بترتبط بيها) هما:

- **`saas_service_catalog`** (الموديل: `ServiceCatalog` في `eppne-backend/app/domains/saas/models.py:12`) → هذا هو جدول الـ**services**.
- **`saas_service_plans`** (الموديل: `ServicePlan` في نفس الملف، سطر 28) → هذا هو جدول الـ**plans**. عمود `service_id` هو FK مباشر على `saas_service_catalog.id` (علاقة **plan → service واحد فقط**، مش many-to-many).

عمود `features` في `saas_service_plans` هو `JSONB` بدون أي schema أو enum مفروض — نص حر بالكامل (راجع القسم 4).

---

## 2. جدول الـ Services (كل الصفوف الموجودة فعليًا — 8 صفوف)

| service_id | name | code | description | is_active |
|---|---|---|---|---|
| 2 | P-SAAS9-VERIFY-CATALOG-8fa402 | `p_saas9_verify_8fa402` | (فاضي) | true |
| 47 | TEST_REQSECTOR_SESSION_ACADEMY_SERVICE | `academy` | (فاضي) | true |
| 48 | TEST_REQSECTOR_SESSION_AFFILIATE_SERVICE | `affiliate` | (فاضي) | true |
| 74 | المزادات والمناقصات - مناقصات | `tenders` | خدمة إدارة المناقصات ضمن قطاع tenders_auctions | true |
| 75 | المزادات والمناقصات - مزادات | `auctions` | خدمة إدارة المزادات ضمن قطاع tenders_auctions | true |
| 76 | سوق الخدمات | `service_marketplace` | خدمة سوق الخدمات (service_marketplace) | true |
| 77 | زمكانة | `zamakana` | خدمة زمكانة (zamakana) | true |
| 78 | السياحة والرياضة | `tourism` | خدمة حجز البرامج السياحية (tourism_sports.book_program يستخدم كود tourism تحديدًا) | true |

ملاحظة: services #2، #47، #48 أسماؤها بادئة `P-SAAS9-VERIFY-` / `TEST_REQSECTOR_SESSION_` — بوضوح صفوف اختبار (test artifacts) من جلسات تحقق سابقة، مش catalog حقيقي. services #74–78 هي الوحيدة اللي أسماؤها ووصفها عربي حقيقي (تبدو Seed فعلي لقطاع tenders_auctions/service_marketplace/zamakana/tourism).

---

## 3. جدول الـ Plans (كل الصفوف الموجودة فعليًا — 6 صفوف) — features كاملة بدون اختصار

| plan_id | plan_name | plan_code | service_id (FK) | service المرتبط (name/code) | features (كما هي، خام) |
|---|---|---|---|---|---|
| 2 | P-SAAS9-VERIFY-PLAN-8fa402 | `p_saas9_plan_8fa402` | 2 | P-SAAS9-VERIFY-CATALOG-8fa402 / `p_saas9_verify_8fa402` | `["real_estate", "insurance"]` |
| 47 | TEST_REQSECTOR_ACADEMY_PLAN | `test_reqsector_academy_plan` | 47 | TEST_REQSECTOR_SESSION_ACADEMY_SERVICE / `academy` | `[]` |
| 48 | TEST_REQSECTOR_AFFILIATE_PLAN | `test_reqsector_affiliate_plan` | 48 | TEST_REQSECTOR_SESSION_AFFILIATE_SERVICE / `affiliate` | `[]` |
| 77 | TEST plan tenders | `test-tenders` | 74 | المزادات والمناقصات - مناقصات / `tenders` | `null` (مش `[]` — القيمة NULL فعليًا في العمود) |
| 78 | TEST plan auctions | `test-auctions` | 75 | المزادات والمناقصات - مزادات / `auctions` | `null` (نفس الملاحظة) |
| 99 | الخطة الافتراضية (مجانية) | `default` | 48 | TEST_REQSECTOR_SESSION_AFFILIATE_SERVICE / `affiliate` | `[]` |

**services من غير أي plan خالص:** `service_marketplace` (76)، `zamakana` (77)، `tourism` (78) — الثلاثة دول (اللي هما بالمناسبة أكتر services شكلها "حقيقي" من ناحية الاسم/الوصف العربي) **مفيش لهم أي صف في `saas_service_plans`**.

---

## 4. ملاحظات الأنماط والتكرار

1. **`features` مش مرتبط دلاليًا بـ `service_id` الفعلي.** plan #2 مربوط بـ`service_id=2` (اللي اسمه/كوده "verify catalog" تجريبي بحت)، لكن محتوى `features` بتاعه هو `["real_estate", "insurance"]` — دول أسماء قطاعات/خدمات تانية تمامًا، مش لها أي علاقة بـservice #2. ده معناه إن حقل `features` بيتلاقى فعليًا يتخزن فيه *أكواد خدمات/قطاعات كنص حر* بشكل منفصل عن الـFK الرسمي `service_id`، مش "مميزات" (features) بالمعنى الحرفي — يعني فيه **مصدرين للحقيقة محتملين** لتحديد "الخدمات اللي الخطة دي بتديها": (أ) `service_id` (FK صريح)، و(ب) محتوى `features` (نص حر بلا schema). لو أي كود في الفرونت/الباك إند بيقرأ `features` عشان يحدد الوصول للخدمات، وده بيختلف عن `service_id`، فده تناقض بيانات حقيقي محتاج قرار تصميمي (مش تقني بحت) قبل أي تعديل.
2. **لا يوجد أي تكرار لنفس اسم/كود service بصيغ مختلفة داخل `features` عبر أكتر من plan** — العينة صغيرة جدًا (6 صفوف بس، و4 منهم `features` فاضي/null)، فمفيش نمط تكرار فعلي ملحوظ حاليًا. الملاحظة الوحيدة المتاحة هي حالة plan #2 المذكورة فوق (عدم تطابق دلالي، مش تكرار بصيغ مختلفة).
3. **`NULL` مقابل `[]` في `features`:** الموديل (`app/domains/saas/models.py:45`) بيحدد `default=list` بس ده default على مستوى ORM/Python وقت الإدراج عبر SQLAlchemy، مش `server_default` على مستوى الـDB. plans #77 و#78 قيمتهم `NULL` فعليًا (مش `[]`) — يعني اتدرجوا بطريقة (SQL خام / migration / seed script) تجاوزت الـORM default. أي كود بيعمل `.get()` أو iterate على `features` من غير فحص `None` هيقع لو قرأ الصفين دول.
4. **service واحد (`affiliate`, id=48) عنده plan-ان مختلفان** (`test_reqsector_affiliate_plan` id=48، و`default`/الخطة الافتراضية id=99) — الـunique constraint في الموديل هو `(service_id, code)` مش `service_id` لوحده (`ix_saas_service_plans_code`, سطر 32)، فده متوقع سكيميًا، بس يستاهل ملاحظة إن مفيش قاعدة تمنع تعدد plans لنفس الـservice، وده ممكن يبقى مقصود (باقات متعددة لنفس الخدمة) أو تكرار غير مقصود — محتاج تأكيد بشري.
5. **الغالبية العظمى من صفوف الجدولين (services وplans) هي بيانات اختبار مؤقتة** (بادئات `TEST_`, `P-SAAS9-VERIFY-`, `TEST plan`) وليست catalog إنتاجي — أي استنتاج "منتجي" من هذا الـdev DB لازم ياخد ده في الاعتبار.

---

## 5. جداول ملحقة اتفحصت (نفس النطاق الدلالي: plan/service) — خارج النطاق الأساسي

بالبحث عن كل الجداول اللي اسمها فيه `%plan%` أو `%service%` في الـschema، طلع فيه جداول تانية غير `saas_service_catalog`/`saas_service_plans`، لكنها تخص دومين تاني تمامًا (**marketplace الخاص بشراء/نشر خدمات جاهزة كمنتج**، مش SaaS subscription plans):

| الجدول | الغرض | عدد الصفوف | ملاحظة |
|---|---|---|---|
| `marketplace_services` | خدمات جاهزة للبيع في الـmarketplace (blueprint/schema/template) | 1 | صف واحد فقط: `P-CTOR-SVCMKT-SERVICE` (test artifact) |
| `service_licenses` | تراخيص شراء خدمة marketplace لـtenant | 1 | `subscription_plan` هنا **enum ثابت** (`BASIC`) مش FK لجدول plans — مفهوم مختلف تمامًا عن `saas_service_plans` |
| `service_addons` | إضافات لخدمات الـmarketplace | 1 | صف واحد: `P-CTOR-SVCMKT-ADDON` (test artifact) |
| `service_addon_purchases` | مشتريات addons | 1 | مرتبط بالصف الوحيد فوق |
| `service_versions` | نسخ خدمات marketplace | 0 | فاضي بالكامل |
| `group_subscription_plans` | خطط اشتراك جماعية (عمود `included_features` JSONB مشابه لـ`features`) | 0 | فاضي بالكامل — مفيش بيانات تتفحص |
| `master_plans` | مخططات أراضي/عقارات (domain: realestate/digital-twin، مش SaaS) | 0 | اسم "plans" لكن مفهوم مختلف كليًا (مخطط عقاري)، فاضي |

**الخلاصة:** الجداول دي كلها إما فاضية أو فيها صف اختباري واحد بس، ومفهوميًا منفصلة عن `saas_service_plans`/`saas_service_catalog` (اللي هي المطابقة الفعلية لوصف المهمة بحقل `features`). مفيش داعي لضمها لجدول القسم 3 لأنها مش "plans" بنفس المعنى (بعضها enum ثابت، بعضها مخططات عقارية).

---

## 6. جداول الربط الفعلي (تأكيد إضافي على استخدام الـplans/services دول)

للتأكد هل الـplans/services دي بتُستخدم فعليًا في أي مكان (اشتراكات حقيقية) أو مجرد بيانات يتيمة:

**`saas_tenant_subscriptions`** (7 صفوف):
| id | tenant_id | plan_id | status |
|---|---|---|---|
| 2 | 1 | 2 | ACTIVE |
| 47 | 16 | 2 | ACTIVE |
| 48 | 16 | 47 | ACTIVE |
| 49 | 16 | 48 | ACTIVE |
| 50 | 1 | 48 | CANCELLED |
| 89 | 1 | 77 | ACTIVE |
| 90 | 1 | 78 | ACTIVE |

→ **plan #99** ("الخطة الافتراضية"/default) **مالوش أي اشتراك فعلي على الإطلاق** — plan يتيم بالكامل من ناحية الاستخدام رغم وجوده كصف.

**`saas_tenant_service_access`** (4 صفوف فقط):
| tenant_id | service_id | access_level |
|---|---|---|
| 1 | 74 | BASIC |
| 1 | 75 | BASIC |
| 16 | 47 | (null) |
| 16 | 48 | (null) |

→ services #76 (`service_marketplace`)، #77 (`zamakana`)، #78 (`tourism`) **مالهاش أي صف access خالص** — نفس الـ3 services اللي مالهاش plans (قسم 3)، يعني الثلاثة دول موجودين في الـcatalog بس مش متفعّلين لأي tenant ولا مربوطين بأي plan حتى الآن.

---

## 7. خلاصة سريعة

- الجدولان الحقيقيان هما `saas_service_catalog` (8 صفوف) و`saas_service_plans` (6 صفوف فقط) — عدد صغير جدًا، ومعظمه بيانات اختبار.
- **أكبر ملاحظة تستاهل قرار بشري:** حقل `features` (نص حر) في plan #2 بيحتوي أكواد خدمات (`real_estate`, `insurance`) غير مرتبطة بـ`service_id` الفعلي بتاعه — احتمال وجود مصدرين متعارضين لتحديد "خدمات الخطة".
- 3 من أصل 8 services (الأكثر واقعية من ناحية البيانات: `service_marketplace`, `zamakana`, `tourism`) **بلا أي plan وبلا أي tenant access** — إما ناقصين seed، أو لسه مش مفعّلين عمدًا.
- plan #99 موجود بس يتيم (صفر اشتراكات).
- لا يوجد تكرار واضح لنفس الـservice بصيغ مختلفة عبر عدة plans — العينة صغيرة جدًا للحكم بثقة، لكن الحالة الوحيدة الملحوظة هي عدم التطابق الدلالي في plan #2 (بند 4.1).

**لم يتم تنفيذ أي تعديل على الكود أو migration أو بيانات في هذه الجلسة — فحص read-only فقط.**
