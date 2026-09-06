# جلسة: تنفيذ Phase 0 (Migration) لتوحيد Referral/Affiliate — تطبيق فعلي

**تاريخ:** 2026-09-06
**النوع:** تنفيذ فعلي على DB (dev) — استكمال لجلسة
`referral-affiliate-unified-system-implementation`.
**مرجع التصميم الكامل:**
`.claude/reports/referral-affiliate-unified-implementation-session-log.md`
(فيه كل قرارات التصميم المعتمدة + محتوى migration 045 قبل إضافة seed
الـSaaS + تأكيد النقاط الستة السابقة).

هذا الملف يوثِّق **فقط** خطوة إضافة seed الـSaaS المفقودة + التطبيق
الفعلي لـ`alembic upgrade` + التحقق الثلاثي بعده. القرارات التصميمية
والتصميم الكامل موثَّقة في الملف المرجعي أعلاه، لا تُكرَّر هنا.

---

## تأكيد: seed صف `saas_service_catalog(code='affiliate')` — كان فعلاً مفقودًا

**فحصت الملف `045_create_affiliate_scopes_and_unify_commission.py`
سطرًا بسطر — لا يوجد أي `INSERT INTO saas_service_catalog` أو
`saas_service_plans` في `upgrade()` كما كُتب قبل هذه الرسالة.** هذا لم
يكن سقوطًا عشوائيًا بلا سبب — كان قرارًا موثَّقًا في تقرير التصميم
(قسم "4) آلية تفعيل الأفيليت كخدمة SaaS" في
`referral-affiliate-unified-implementation-session-log.md`) بتأجيل الـseed
لمرحلة Phase 7 لاحقًا، بناءً على ملاحظة إن **لا توجد أي سابقة بالمشروع
لـseed بيانات داخل migration** (فحص شامل وقتها لكل ملفات `migrations/versions/`
لـ`INSERT INTO`/`op.bulk_insert`: صفر نتيجة).

**لكن طلبك الحالي صحيح ويُبطل هذا القرار المرجَّح سابقًا:** بدون هذا
الصف، `require_subscription("affiliate")` (مُستخدَمة بالفعل على 5
endpoints في `affiliate/router.py`) ترجع `False` **لأي tenant إطلاقًا**،
مهما كان الكود صحيحًا — فجوة تشغيلية كاملة، وليست مجرد نقص تحسيني.
**تم إضافته الآن كخطوة 9 في `upgrade()`، قبل أي تطبيق فعلي.**

### الكود المُضاف (خطوة 9، نهاية `upgrade()`)

```python
    # ========================================================
    # 9. Seed: تسجيل affiliate كخدمة SaaS قابلة للتفعيل + خطة افتراضية
    #    مجانية — بدونها Phase 7 (تفعيل SaaS) والنظام كله غير قابل
    #    للاستخدام لأي tenant حتى لو كل الكود صحيح 100%
    # ========================================================
    op.execute(
        """
        INSERT INTO saas_service_catalog (name, code, description, is_active, created_at)
        VALUES ('Affiliate Program', 'affiliate', 'برنامج الإحالة والعمولات متعددة المستويات (10 مستويات، مربوط بنطاقات)', true, now())
        ON CONFLICT (code) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO saas_service_plans (
            service_id, name, code, price_monthly, price_yearly, currency,
            features, max_users, max_products, max_courses, is_active,
            created_at, updated_at
        )
        SELECT id, 'الخطة الافتراضية (مجانية)', 'default', 0, 0, 'MR_USDT',
               '[]'::jsonb, 10, 50, 20, true, now(), now()
        FROM saas_service_catalog WHERE code = 'affiliate'
        ON CONFLICT (service_id, code) DO NOTHING
        """
    )
```
`ON CONFLICT DO NOTHING` على `(code)` و`(service_id, code)` — يطابق
الفهارس الفريدة الموجودة فعليًا (`ix_saas_service_catalog_code`،
`ix_saas_service_plans_code`)، يجعل الـseed idempotent (آمن لو تكرر
التشغيل بالخطأ). **ملاحظة صريحة: هذه الخطة الافتراضية `price_monthly=0`
— تفعيل مجاني تلقائي لأي tenant يُفعِّل الخدمة، إلى أن يقرر
superuser لاحقًا (عبر endpoints الـSaaS الموجودة بالفعل) إنشاء خطط
مدفوعة بديلة. هذا قرار افتراضي معقول لمرحلة التطوير، وليس قرار تسعير
نهائي — يحتاج مراجعتك عند الإطلاق الفعلي.**

### `downgrade()` — إضافة مقابلة (أول خطوة، تعكس آخر خطوة في upgrade)

```python
    op.execute(
        "DELETE FROM saas_service_plans WHERE service_id = "
        "(SELECT id FROM saas_service_catalog WHERE code = 'affiliate')"
    )
    op.execute("DELETE FROM saas_service_catalog WHERE code = 'affiliate'")
```

**الحالة: تم إضافة الكودين فعليًا للملف — راجع القسم التالي للتأكيد.**

---

## التطبيق الفعلي على DB — 3 محاولات، اكتشافان حقيقيان أثناء التنفيذ

**DB المستهدفة (تأكيد حي عبر `alembic current` قبل أي تعديل):**
`postgresql+asyncpg://eppne:***REDACTED***@127.0.0.1:5435/eppne_v2` (container
`eppne_db`، بورت 5435 — **وليس** `postgres-eppne` على بورت 5433 رغم
كونه الافتراضي المكتوب حرفيًا في `alembic.ini` — `migrations/env.py`
يقرأ `DATABASE_URL` من `.env` فعليًا، مؤكَّد بتشغيل `alembic current`
قبل أي تعديل: كانت `044_create_transport_tables`، مطابقة للمتوقَّع).

### محاولة 1 — فشلت: `DuplicateObjectError: type "affiliatescopetype" already exists`

**السبب:** استدعيت `affiliate_scope_type_enum.create(op.get_bind(),
checkfirst=True)` يدويًا **قبل** `op.create_table(...)` — لكن
SQLAlchemy تدير إنشاء أنواع `postgresql.ENUM` **تلقائيًا** كجزء من
`create_table()` نفسها (نفس آلية `vehicle_type`/`vehiclestatus` في
migration 044، اللي **لا** تستدعي `.create()` يدويًا إطلاقًا). الاستدعاء
اليدوي أنشأ النوع أول مرة بنجاح، ثم `create_table()` حاولت إنشاءه
تاني تلقائيًا فوصطدمت. **الإصلاح:** حذف استدعاء `.create()` اليدوي
بالكامل، الاعتماد فقط على الآلية التلقائية (مطابق لنمط 044 حرفيًا).
**Alembic transactional DDL تعامل مع الفشل بأمان تام** — تحقَّقت بـ
`alembic current` بعد الفشل: لسه `044`، صفر تأثير جزئي على DB.

### محاولة 2 — نجحت: `alembic upgrade head` طبَّق `045` بالكامل بلا أخطاء

### اكتشاف حي أثناء التحقق: صف `saas_service_catalog(code='affiliate')` **كان موجودًا مسبقًا**

الاستعلام بعد التطبيق:
```
 id |   code    |                   name                    | is_active
----+-----------+-------------------------------------------+-----------
 48 | affiliate | TEST_REQSECTOR_SESSION_AFFILIATE_SERVICE   | t
```
هذا **ليس** الصف اللي كتبته في seed الخطوة 9 (كنت كتبت `name='Affiliate
Program'`) — `ON CONFLICT (code) DO NOTHING` اشتغل بالضبط زي ما هو
مصمَّم: وجد صف بنفس `code='affiliate'` من جلسة اختبار سابقة غير مرتبطة
(اسم `TEST_REQSECTOR_SESSION_AFFILIATE_SERVICE` — واضح إنه من جلسة
`require_sector` تجريبية سابقة، نفس فئة "بيانات throwaway لم تُنظَّف"
الموثَّقة في `phase10-audit-affiliate-report.md`)، فتجاهل الـinsert بتاعي
بأمان. **الخطة الافتراضية (`code='default'`, `price_monthly=0`) اتسجَّلت
بنجاح تحت نفس `service_id=48`** (لا تعارض، `code` مختلف).

**هذا الاكتشاف مهم لسببين:**
1. **إيجابي:** يعني `tenant_id=16` (شايفينه تحت) عنده بالفعل اشتراك
   `ACTIVE` سابق على خدمة `affiliate` من تلك الجلسة التجريبية — يقدر
   يُستخدَم فورًا كبيانات اختبار جاهزة لـPhase 9 (tests) بدل إنشاء
   tenant جديد من الصفر.
2. **سلبي/كشف باج في تصميمي الأصلي:** خلّى أول محاولة `alembic downgrade -1`
   تفشل — راجع تحت.

### محاولة round-trip 1 (`alembic downgrade -1`) — فشلت: `ForeignKeyViolationError`

```
update or delete on table "saas_service_plans" violates foreign key
constraint "saas_tenant_subscriptions_plan_id_fkey"
DETAIL: Key (id)=(48) is still referenced from table "saas_tenant_subscriptions".
```
**السبب الجذري:** `downgrade()` كان بيحاول
`DELETE FROM saas_service_plans WHERE service_id = (SELECT id FROM
saas_service_catalog WHERE code='affiliate')` — استعلام **واسع جدًا**:
بيحذف **كل** الخطط تحت `service_id=48`، مش بس الخطة اللي أنشأتها
الـmigration. تحقَّقت من البيانات فعليًا:
```
 id | service_id |             code              |             name              
----+------------+-------------------------------+--------------------------------
 48 |         48 | test_reqsector_affiliate_plan | TEST_REQSECTOR_AFFILIATE_PLAN
 99 |         48 | default                       | الخطة الافتراضية (مجانية)

 id | tenant_id | plan_id |  status
----+-----------+---------+-----------
 49 |        16 |      48 | ACTIVE       ⬅️ اشتراك حي فعلي على الخطة التجريبية
 50 |         1 |      48 | CANCELLED
```
خطة `test_reqsector_affiliate_plan` (id=48) **مرتبطة فعليًا** باشتراك
tenant حي (`ACTIVE`, tenant_id=16) — الحذف الواسع كان هيمسح بيانات
اختبار سابقة **غير مرتبطة بهذه الـmigration إطلاقًا** ومُستخدَمة فعليًا.

**الإصلاح المعتمد:** حذف محاولة عكس الـseed من `downgrade()` بالكامل
(بدل تضييق نطاق الـDELETE) — **لأن `ON CONFLICT DO NOTHING` بطبيعته
يمنع التمييز بين "صف أنشأته هذه الـmigration" و"صف كان موجودًا مسبقًا"**،
فأي محاولة حذف انتقائي (حتى لو ضيَّقتها بـ`code='default'` بدل `service_id`)
تبقى غير آمنة منطقيًا (لو مستخدم تاني عمل خطة `code='default'` يدويًا
لسبب آخر بعد التطبيق، هتتحذف غلط). **القرار: seed الـSaaS غير قابل
للتراجع عمدًا، بنفس فلسفة عدم قابلية التراجع عن TRUNCATE في الخطوة 0**
— موثَّق كتعليق صريح في `downgrade()` نفسها.

**Alembic transactional DDL تعامل مع هذا الفشل بأمان تام برضو** —
تحقَّقت: لسه `045` (head)، صفر تأثير جزئي.

### محاولة round-trip 2 (بعد الإصلاح) — نجحت بالكامل

1. `alembic downgrade -1` → نجح بلا أخطاء → `alembic current` = `044`.
2. تحقُّق حي: `affiliate_scopes` غير موجود، `affiliate_trees` **عاد
   للوجود** (نظام B، أُعيد إنشاؤه صح)، `affiliate_commission_tiers.target_product_id`
   **عاد بنفس الاسم والـFK الأصلي** (`affiliate_commission_tiers_target_product_id_fkey`
   → `products.id`) — الشكل البنيوي الأصلي بالكامل، مطابق تمامًا لما
   قبل `045`.
3. `alembic upgrade head` → نجح بلا أخطاء → `alembic current` = `045` (head).
4. تحقُّق نهائي: `affiliate_scopes` موجود من جديد، وseed الخطة
   الافتراضية (`id=99, service_id=48, code='default'`) **لم يتكرر**
   (`ON CONFLICT (service_id, code) DO NOTHING` اشتغل صح في المحاولة
   الثانية — الصف كان لسه موجودًا من أول upgrade لأن downgrade متعمدًا
   محَّدش لمسه).

**✅ round-trip كامل ناجح: `downgrade -1` → `upgrade head` بلا أي خطأ،
والحالة النهائية مطابقة تمامًا لما بعد أول `upgrade` ناجح — الـmigration
مستقرة ومتماثلة (idempotent) في الاتجاهين.**

---

## ملخص التحقق الثلاثي المطلوب

| # | المطلوب | النتيجة |
|---|---|---|
| 1 | `alembic current` يؤكد تطبيق `045` | ✅ `045_create_affiliate_scopes_and_unify_commission (head)` |
| 2 | فحص حي لكل جدول جديد بالأعمدة الصحيحة + اختفاء الأربعة المحذوفة | ✅ `affiliate_scopes`/`affiliate_scope_members` بالضبط كما صُمم (Enum، الفهارس الجزئية المزدوجة، كل الـFK)؛ `affiliate_commission_tiers`/`affiliate_commissions` بالأعمدة الجديدة والـnullable الصحيح؛ `users.referred_by_user_id` موجود؛ `affiliate_action_commissions`/`affiliate_trees`/`commission_records`/`affiliate_configs` الأربعة **غير موجودين إطلاقًا** (`\dt` رجع "Did not find any relation" للأربعة) |
| 3 | `downgrade -1` ثم `upgrade head` (round-trip) | ✅ نجح بعد إصلاح باج downgrade المكتشَف حيًا (راجع أعلاه) — النتيجة النهائية مطابقة لحالة ما بعد أول upgrade |

**اكتشافان حقيقيان أثناء التنفيذ الفعلي (وليس نظريًا):**
1. باج `.create()` مزدوج للـENUM — مُصلَح، موثَّق كتعليق في الكود نفسه.
2. باج downgrade الـseed (FK violation على بيانات اختبار سابقة غير
   مرتبطة) — مُصلَح بإزالة محاولة العكس، موثَّق كتعليق في الكود نفسه.

**بيانات throwaway مكتشَفة (خارج نطاق هذه الجلسة، للتوثيق فقط):**
`saas_service_catalog.id=48` (`TEST_REQSECTOR_SESSION_AFFILIATE_SERVICE`)
+ `saas_service_plans.id=48` (`test_reqsector_affiliate_plan`) +
`saas_tenant_subscriptions.id=49` (`tenant_id=16`, `ACTIVE`) — من جلسة
`require_sector` تجريبية سابقة، لم تُنظَّف. **ملاحظة إيجابية:** يمكن
استخدام `tenant_id=16` مباشرة كبيانات جاهزة لاختبار Phase 9 لاحقًا (عنده
اشتراك فعّال جاهز على خدمة `affiliate`) بدل إنشاء tenant throwaway جديد.

**الملف النهائي `045_create_affiliate_scopes_and_unify_commission.py`
مُطبَّق فعليًا على DB (`eppne_v2`)، مستقر، ومتحقَّق منه ثلاثيًا. الحالة:
✅ Phase 0 مكتملة بالكامل.**

---

## Phase 1 — Models (مكتملة)

**الملفات المعدَّلة:**
- `app/domains/affiliate/models.py`: إضافة `AffiliateScopeType` (enum
  Python يطابق `affiliatescopetype` في DB بالاسم التلقائي — نفس نمط
  `TransportType`/`VehicleStatus` في `transport/models.py`)، `AffiliateScope`،
  `AffiliateScopeMember`. `ReferralTree.entity_id` صار `ForeignKey
  ("affiliate_scopes.id", ondelete="CASCADE")` (كان `Integer` عام).
  `Commission`: `order_id`/`order_item_id`/`product_id` → `nullable=True`،
  + أعمدة `source_type`/`source_id`/`scope_id` جديدة. `CommissionTier`:
  `target_product_id` → `target_scope_id` (+ FK لـ`affiliate_scopes`).
  **`ActionCommission` حُذفت بالكامل من الملف.**
- `app/domains/identity/models.py`: إضافة `User.referred_by_user_id`
  (`BigInteger`, FK ذاتي `SET NULL`, nullable).
- `app/domains/commerce/models.py`: حذف `AffiliateTree`/`CommissionRecord`/
  `AffiliateConfig` بالكامل (نظام B).

**تحقُّق:** `py_compile` نظيف على الثلاثة. **لم يُشغَّل `configure_mappers()`
معزولًا لهذه الملفات الثلاثة فقط** — رجع خطأ متوقَّع تمامًا وغير مرتبط
بتعديلاتي (`finance.models`/`academy.models` غير مستوردة في السكريبت
المعزول) — استُبدل بفحص أشمل وأصدق: **استيراد `app.main` كاملة** (راجع
تحت)، وهو الاختبار الحقيقي لأن كل الدومينات تُستورَد فعليًا معًا هناك.

---

## Phase 2 — Repository (مكتملة)

**`app/domains/affiliate/repository.py`:**
- `get_referral_tree(user_id, tenant_id)` → `get_referral_tree(user_id,
  tenant_id, scope_id)` — **إصلاح باج MultipleResultsFound فعليًا**
  (فلترة `entity_type='SCOPE' AND entity_id=scope_id`، مش `referred_id`
  وحده — القيد الفريد الآن يضمن صفًا واحدًا حقيقيًا).
- `get_referral_tree_with_sponsors(...)`: `scope_id` يمشي معه في كل
  استدعاء متكرر عبر السلسلة (يمنع القفز بين نطاقات مختلفة).
- `create_action_commission` **حُذفت**.
- `get_commission_tier_by_product` → `get_commission_tier_by_scope`
  (`target_product_id`→`target_scope_id`، `entity_type="PRODUCT"`→`"SCOPE"`).
- `get_commission_tiers`: `target_product_id.is_(None)` → `target_scope_id.is_(None)`.
- قسم جديد "8. نطاقات العمولة": `get_scope`, `get_default_scope`
  (ENTITY_WIDE)، `create_scope`, `add_scope_member`, `get_scope_member`
  (join على `AffiliateScope` للتقييد بـ`tenant_id`، بما إن
  `AffiliateScopeMember` بلا عمود `tenant_id` مباشر).

**`app/domains/commerce/repository.py`:** حذف قسم "Affiliate"/"Commissions"/
"Affiliate Config" بالكامل (`get_affiliate_tree`, `create_affiliate_tree`,
`get_sponsor_chain`, `create_commission`, `get_pending_commissions`,
`release_commission`, `get_commission`, `get_affiliate_config`,
`create_or_update_config`) + إزالة `CommissionResponse` من imports
(بقيت غير مستخدَمة). `from app.domains.commerce.models import *` يعني
حذف الكلاسات من `models.py` (Phase 1) كفى لسحب `AffiliateTree`/
`CommissionRecord`/`AffiliateConfig` من الاستيراد تلقائيًا — لا حاجة
لتعديل سطر import صريح.

**تحقُّق:** `py_compile` نظيف على الملفين. `python -c "import app.main"`
بعد Phase 2: **الخطأ انتقل تمامًا كما متوقَّع** من `repository.py` (Phase 2)
إلى `service.py` (`ImportError: cannot import name 'ActionCommission'
from app.domains.affiliate.models`، بيتوقف الآن عند سطر الاستيراد في
`affiliate/service.py`) — يؤكد Phase 1+2 سليمتان تمامًا وخاليتان من أي
مرجع مكسور لأنفسهما، والفشل المتبقي محصور في Phase 3 (Service) كما
هو متوقَّع بالضبط من ترتيب المراحل المعتمد.

---

## Phase 3 — Service (مكتملة) — أكبر مرحلة منطقية

**⚠️ كشف تصميمي جانبي حي أثناء التنفيذ:** `academy/service.py:390-401`
يستدعي `track_referral` **لكنه لا يستدعي أي دالة توزيع عمولة إطلاقًا
بعدها** — يسجّل الشجرة فقط، صفر توزيع فعلي حتى قبل هذه الجلسة. هذا
لم يكن مذكورًا صراحة في تقرير 2026-08-19 ولا تقرير التصميم — اكتشاف
جديد يخص Phase 5، مُسجَّل هنا للمتابعة، **لم يُعالَج بعد** (خارج نطاق
Phase 3 بالضبط كما خُطِّط، سيُصلَح في Phase 5).

### `app/domains/affiliate/service.py`
- **`ensure_referral_link(referrer_user_id, referred_user_id, scope_id) -> (ReferralTree|None, created: bool)`**
  جديدة — المنطق العام المشترك (upsert idempotent + حساب depth)، تُستخدَم
  مباشرة من الـ12 دومين (user_id→user_id) وداخليًا من `track_referral`
  (code→user_id، بعد حل الكود لـuser_id).
- **`track_referral(referrer_code, referred_user_id, scope_id)`** —
  أُعيدت كتابتها فوق `ensure_referral_link`. **السلوك الخارجي محفوظ
  حرفيًا** لكل المستدعين الحاليين: لسه بترجع `None` لو الرابط موجود
  بالفعل (مش الشجرة الموجودة) — قرار متعمَّد لتفادي كسر أي منطق مستقبلي
  في `academy`/`commerce` يعتمد على "`None` = لا شيء جديد حصل".
- **`resolve_scope_id_for_member(member_type, member_id=None)`** +
  **`get_default_scope_id()`** جديدتان — يفضّلان عضوية `AffiliateScopeMember`
  محدَّدة، ويسقطان لنطاق `ENTITY_WIDE` الافتراضي للـtenant. `None` يعني
  صراحة "خدمة affiliate غير مفعَّلة SaaS لهذا الـtenant بعد" (Phase 7).
- **`distribute_commissions(order_id)`** → **`distribute_commissions_for_order(order_id, affiliate_code=None)`**:
  لكل عنصر في السلة، يُحلّ scope خاص به (يدعم **تقسيم العمولة حسب نطاق
  كل منتج في سلة مختلطة** — القرار المعتمد صراحة)، وينشئ رابط الإحالة
  أولًا لو `affiliate_code` مُمرَّر (بديل `register_affiliate` المنفصل
  في نظام B المحذوف).
- **`distribute_commissions_for_sale_event(referred_user_id, scope_id, sale_amount, source_type, source_id)`**
  جديدة — نقطة الدخول العامة لأي بيع بلا `Order` تجاري (academy، الـ12
  دومين) — ستُستخدَم في Phase 5/6.
- **`_distribute_levels`/`_get_commission_rate`**: `product_id` →
  `scope_id` في كل مكان، ويمشيان عبر السلسلة **داخل نفس scope_id في كل
  مستوى** (إصلاح باج `MultipleResultsFound` مُطبَّق هنا فعليًا في مسار
  التنفيذ، مش بس في الـrepository).
- **`register_commission`/`ActionCommission` حُذفا بالكامل.**
- **`create_product_tier` → `create_scope_tier`** (`target_product_id`→`target_scope_id`).
- **`get_referral_tree(user_id, scope_id, max_depth=5)`** — أضيف
  `scope_id` كمعامل إجباري (كان بلا نطاق، endpoint `GET /affiliate/tree`
  هيحتاج `scope_id` كـquery param جديد — Phase 4).

### `app/domains/affiliate/schemas.py` — **تعديل مسحوب مبكرًا من Phase 4 (ضرورة حتمية)**
اكتُشف أثناء الكتابة إن ترك `CommissionBase.order_id/order_item_id/
product_id` كحقول `int` إجبارية (غير nullable) كان سيُسقِط أي استدعاء
لـ`GET /affiliate/commissions` بـ`ValidationError` فور وجود أي عمولة
غير تجارية (academy/12 دومين) — تناقض مباشر مع تعميم `Commission`
(§1.د). **صُحِّح الآن**: الثلاثة أصبحوا `Optional[int] = None`، +
إضافة `source_type: str`, `source_id: Optional[int]`, `scope_id: int`.
`CommissionTierBase`/`CommissionTierUpdate.target_product_id` →
`target_scope_id` (نفس سبب الضرورة — بدونه `repo.create_commission_tier(**data.model_dump())`
كان سيرمي `TypeError` فورًا). **هذا تعديل ضيّق مقصود على حقلين فقط —
باقي عمل Phase 4 (router endpoints، schemas إضافية) لسه مؤجَّل كما هو
مخطَّط.**

### `app/domains/commerce/service.py` + `router.py`
- `register_affiliate`, `distribute_commissions` (B)، `get_user_commissions`،
  `release_commissions` **حُذفوا بالكامل** (كانوا يعتمدون على جداول
  محذوفة أصلًا منذ Phase 0).
- `checkout()`: استبدال نداء `self.distribute_commissions(...)` بنداء
  موحَّد جديد: `AffiliateService(db, tenant_id).distribute_commissions_for_order(order.id, affiliate_code=checkout_data.affiliate_code)`.
- `router.py`: حذف 3 endpoints مكسورة حتمًا (`POST /affiliate/link`,
  `GET /affiliate/commissions`, `POST /affiliate/commissions/release`
  تحت prefix `/commerce`) — **مسحوب مبكرًا من Phase 4** لنفس سبب
  الضرورة (كانت ستفشل بـ`AttributeError` فور استدعائها، الدوال المقابلة
  حُذفت من الـservice).
- تنظيف: إزالة `import get_or_create_system_account` غير المستخدَم بعد
  حذف `release_commissions` (السبب الوحيد لاستخدامه).

**تحقُّق نهائي حاسم:**
```
$ python -c "import app.main; print('APP IMPORT OK')"
APP IMPORT OK
```
**كل الدومينات الـ35 + main.py يستوردون بنجاح تام بلا أي خطأ.** هذا أول
تحقق ناجح لاستيراد التطبيق الكامل منذ بداية الجلسة — يؤكد Phase 0-3
متسقة داخليًا بالكامل. **ملاحظة صريحة عن حدود هذا التحقق:** استيراد
ناجح يعني عدم وجود أخطاء وقت التحميل (imports/class definitions) فقط —
**لا يعني** إن كل endpoint هيشتغل صح فعليًا؛ مثال معروف: `affiliate/router.py`
لسه بينادي `service.create_product_tier(data)` (الاسم القديم، اتغيّر
لـ`create_scope_tier`) و`service.get_referral_tree(user_id, max_depth)`
(بلا `scope_id` الإجباري الجديد) — هذول هيفشلوا بـ`AttributeError`/
`TypeError` **وقت الاستدعاء الفعلي فقط**، مش وقت الاستيراد، لأنهم داخل
أجسام دوال. **هذا متوقَّع تمامًا ومحجوز عمدًا لـPhase 4 (Router/Schemas)
التالية** — لم يُصلَح الآن لتفادي دمج نطاق مرحلتين.

---

## Phase 4 + 7 — Router/Schemas + تفعيل SaaS (مكتملتان، نُفِّذتا معًا كما خُطِّط)

- **`affiliate/schemas.py`:** أضيفت `AffiliateScopeCreate/Response`،
  `AffiliateScopeMemberCreate/Response`.
- **`affiliate/service.py`:** `list_scopes`, `create_scope`,
  `add_scope_member` جديدة (تغليف رقيق حول repo).
- **`affiliate/router.py`:** إصلاح `GET /tree` (أضيف `scope_id` كـquery
  param إجباري)، `create_product_commission_tier` → `create_scope_commission_tier`
  (ينادي `create_scope_tier` الجديدة)، + 3 endpoints جديدة تحت
  `/admin/scopes*` (list/create scope، إضافة عضو).
- **`saas/service.py` — Hook Phase 7:** داخل `create_subscription`،
  بعد `commit()`: لو `service.code == "affiliate"`، يُنشئ تلقائيًا
  `AffiliateScope(scope_type=ENTITY_WIDE)` للـtenant لو مش موجود بالفعل
  (`get_default_scope_id()` أولًا — idempotent، آمن لو استُدعيت المهمة
  أكتر من مرة بعد تجديد/تغيير خطة).

**تحقُّق:** `py_compile` نظيف على كل الملفات. `import app.main` ناجح.

---

## Phase 5 — ربط academy (مكتملة)

`academy/service.py:390-407` (تسجيل كورس بكود إحالة):
- **اكتشاف حي مهم (لم يكن موثَّقًا صراحة في أي تقرير سابق):** الكود
  الأصلي كان يستدعي `track_referral` فقط — **يسجّل شجرة الإحالة بلا أي
  توزيع عمولة فعلي أبدًا**، حتى قبل أي تعديل في هذه الجلسة. أي عمولة
  "متوقَّعة" من تسجيل كورس بكود إحالة **لم تتولَّد فعليًا من أي وقت
  مضى** في الإنتاج.
- **الإصلاح:** `resolve_scope_id_for_member("COURSE", course_id)` أولًا
  (بدل تمرير `entity_type`/`entity_id` مباشرة لـ`track_referral` —
  توقيعها اتغيّر لـ`scope_id`)، ثم — **لو الدفع اكتمل بمبلغ حقيقي
  (`amount > 0 and payment_status == "COMPLETED"`)** — استدعاء
  `distribute_commissions_for_sale_event` فعليًا (`source_type=
  "ACADEMY_ENROLLMENT"`, `source_id=enrollment.id`). لو `scope_id`
  رجعت `None` (خدمة affiliate غير مفعَّلة SaaS للـtenant)، يتخطَّى
  بصمت — نفس نمط "لا referral" الأصلي.

---

## Phase 6 — ربط الـ12 دومين (مكتملة)

فحص شامل أول (`grep` على `user.referred_by` كامل المشروع): **12 ملف
بالضبط**، مطابق تمامًا للعدد الموثَّق سابقًا. **11 منهم بنمط متطابق
حرفيًا** (فرق فقط في حساب المبلغ ووصف الرسالة): `zamakana`, `transport`,
`insurance`, `tourism_sports`, `tenders_auctions`, `service_marketplace`,
`employment`, `realestate`, `manufacturing`, `arbitration_syndicates`,
`invitations`. **`digital_twin` مختلف (اكتُشف أثناء القراءة قبل
التعديل):** يدعم إضافيًا تمرير `affiliate_code` مباشرة (بديل
`user.referred_by_user_id` لو المستخدم أول مرة يتفاعل بلا رابط
مُسجَّل مسبقًا) — عولج بحرص للحفاظ على هذا المسار البديل.

**التعديل الموحَّد لكل الـ12:**
```python
if user and user.referred_by_user_id:
    commission = <نفس حساب المبلغ الأصلي، بلا تغيير>
    scope_id = await affiliate_service.resolve_scope_id_for_member("<DOMAIN_NAME>")
    if scope_id:
        await affiliate_service.ensure_referral_link(user.referred_by_user_id, user_id, scope_id)
        await affiliate_service.distribute_commissions_for_sale_event(
            referred_user_id=user_id, scope_id=scope_id,
            sale_amount=commission, source_type="<DOMAIN_NAME>",
        )
```
**الأثر الجوهري:** عمولة الـ12 دومين كانت (لو `referred_by` كان
موجودًا أصلًا) ستكون **مستوى واحد مباشر فقط** (`ActionCommission`) —
أصبحت الآن **تصعيدًا حقيقيًا لـ10 مستويات** بنفس منطق commerce/academy
(قرار #3 المعتمد من المستخدم). كل استدعاء يبقى ملفوفًا بنفس
`try/except Exception` الأصلي — فشل تسجيل عمولة لا يكسر العملية
الأساسية للمستخدم أبدًا (مبدأ معماري قائم، لم يتغيّر).

`grep` تأكيدي نهائي: صفر بقايا `.referred_by` (بلا `_user_id`) في كل
`app/domains/` — الـ12 كلهم مُحدَّثون بالكامل.

---

## Phase 8 — إصلاح Celery (مكتملة)

`tasks/affiliate.py` — 3 أعطال توقيع مستقلة، كلها موثَّقة سابقًا في
تقارير قديمة (Phase 10 audit) وأُصلحت الآن فعليًا:
1. `distribute_commissions_task`: `service.distribute_commissions(order_id, tenant_id)`
   (توقيع قديم غير موجود أصلًا) → `service.distribute_commissions_for_order(order_id)`.
2. `release_commissions_task`: كانت ناقصة `tenant_id` **في توقيع
   الـtask نفسها** (مش بس في استدعاء `AffiliateService`) — أُضيف
   `tenant_id: int` كمعامل جديد. **اكتشاف جانبي:** كانت كمان تتجاهل
   `idempotency_key` الممرَّر لها بالكامل (تنادي `release_commissions(user_id)`
   بلا تمريره) — أُصلح كمان (`release_commissions(user_id, idempotency_key=idempotency_key)`).
3. `clean_expired_links_task`: كانت تنادي `delete_expired_invitations(cutoff_date)`
   بمعامل واحد فقط، بينما التوقيع الحقيقي يتطلب `tenant_id` إجباري.
   **لا يوجد نمط "loop عبر كل الـtenants" جاهز بالمشروع** (فُحص
   `saas_tasks.py`/`agritech.py`/`celery_config.py` قبل الكتابة — صفر
   سابقة) — أول نمط من نوعه، مكتوب هنا: استعلام `AcademyTenant` لكل
   tenant نشط (`is_active=True`) ثم loop على كل واحد.
4. **تسجيل فعلي في `beat_schedule`** (`core/celery_config.py`) —
   `clean_expired_links` كانت مُعرَّفة بالكود منذ البداية **بلا أي
   جدولة Celery Beat تنادي عليها إطلاقًا** (موثَّق كملاحظة في تقارير
   سابقة، لم يُصلَح قبل الآن) — أُضيف entry جديد (`5:00 صباحًا يوميًا`).

---

## تحقق حي شامل (Phase 9 — جزء منها، ليس الملف الرسمي الدائم)

**سكريبت مؤقت** (`scratchpad/live_test_phase9.py`، غير مُلتزَم بـgit —
للتحقق الفوري فقط، ليس بديلًا عن ملف `pytest` رسمي) نُفِّذ ضد DB حقيقية
(`eppne_v2`)، مستخدِمًا `tenant_id=16` الموجود بالفعل (throwaway، عنده
اشتراك `ACTIVE` سابق على خدمة `affiliate` — اكتُشف في Phase 0). المسار
الكامل المُختبَر فعليًا:

```
✅ users created: referrer=1560 referred=1561
✅ scope_id=1 (ENTITY_WIDE جديد لـtenant 16 — لم يكن موجودًا)
✅ tier level_1_pct=10.00 (CommissionTier افتراضي GLOBAL جديد)
✅ referrer affiliate profile id=68 active=True
✅ ensure_referral_link: created=True tree_id=1 depth=1
✅ get_referral_tree (post-fix) OK: 1        ⬅️ إصلاح باج MultipleResultsFound يعمل فعليًا
✅ distribute_commissions_for_sale_event -> 1 commission(s)
   level=1 amount=10.00000000 scope_id=1 source_type=LIVE9_TEST affiliate_id=68
✅ DB re-fetch referred.referred_by_user_id = 1560
```

**هذا يثبت حيًا (مش استيراد ناجح فقط):** إنشاء scope تلقائي، ربط
إحالة idempotent، المشي عبر السلسلة بعد إصلاح الباج بلا
`MultipleResultsFound`، وتوزيع عمولة حقيقي بنسبة صحيحة (10% من 100 =
10.00) في صف `Commission` حقيقي بكل الأعمدة الجديدة (`scope_id`,
`source_type`) مملوءة صح.

**تنظيف بعد التحقق:** `DELETE FROM users WHERE id IN (1560, 1561)` —
الـCASCADE على الـFK (`affiliate_profiles.user_id`, `referral_trees.
referrer_id/referred_id`, `affiliate_commissions.user_id`) نظَّف كل
البيانات المرتبطة تلقائيًا (تحقَّق: 3 استعلامات `COUNT(*)` بعد الحذف،
كلها `0`). **النطاق `ENTITY_WIDE` الجديد لـtenant 16 (`scope_id=1`)
أُبقي عليه عمدًا** (وليس بيانات اختبار — هذا بالضبط ما كان Phase 7
سينشئه تلقائيًا لو الـhook كان موجودًا وقت إنشاء اشتراك tenant 16
الأصلي)، وأُعيد تسميته من `"LIVE9 default scope"` إلى `"كل مبيعات
المستأجر"` ليطابق تسمية الـhook الفعلية.

---

## الحالة النهائية للجلسة

**Phases 0-8 مكتملة بالكامل، مُتحقَّق منها (syntax + import تراكمي بعد
كل مرحلة + تحقق حي end-to-end واحد شامل).** الملفات المعدَّلة: 24 ملف
عبر 15 دومين + `core/celery_config.py` + migration واحدة + `PROGRESS_LOG.md`.

**متبقٍ صراحة (لم يُنفَّذ، Phase 9 الرسمية):**
1. ملف `tests/test_referral_affiliate_unified_*.py` دائم (pytest، ملتزَم
   بـgit) يغطي نفس السيناريو المُختبَر يدويًا أعلاه + حالات حافة
   (سلة بنطاقات مختلطة، تفعيل SaaS الفعلي عبر `create_subscription`،
   الـ12 دومين كل واحد على حدة).
2. تنظيف بقايا صغيرة غير حرجة خارج نطاق الجلسة: `@rate_limit` غير
   الفعّال (موثَّق في تقرير Phase 10 قديم، غير ممسوس هنا)، ودور
   `Store.is_affiliate_enabled` النهائي (أُبقي عليه بقرار معتمد، بلا
   تغيير كود إضافي).

**لا تنفيذ إضافي بدون توجيه صريح جديد من المستخدم.**

---

## Phase 9 — توقفت عند سيناريو #3 (تفعيل SaaS عبر create_subscription)

أثناء كتابة اختبارات Phase 9 الرسمية، اكتُشف باج مسدود (`get_plan_by_id`
chicken-and-egg) يمنع `POST /saas/subscriptions/{plan_id}` من العمل
لأي tenant/خدمة إطلاقًا — وتحذير أمني موثَّق صراحة داخل الكود يمنع
إصلاحه بمعزل عن ثغرة `check_feature_access` الكامنة. **توضيح كامل
بكل التفاصيل والخيارات الأربعة:**
`.claude/reports/saas-get-plan-by-id-security-tradeoff-note.md`.
**في انتظار قرار المستخدم — صفر تنفيذ حتى الآن.**
