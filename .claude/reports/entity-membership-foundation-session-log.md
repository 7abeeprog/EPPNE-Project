# سجل جلسة: بناء الأساس العام — نظام `EntityMembership` (الجلسة 1 من 2)

> جلسة تنفيذية أولى (كود + migration) في مسار الصلاحيات الجديد.
> مصدر المهمة: `.claude/plans/entity-membership-foundation-session-instructions.md`

---

## 1. مرحلة القراءة (تمت)

قُرئت الأربعة مستندات المرجعية بالكامل، بالترتيب المطلوب:

1. `.claude/plans/multilevel-referral-system-design-vision.md` — قرار حذف
   أنظمة العمولة الثلاثة القديمة بلا ترحيل (لا علاقة مباشرة بهذه الجلسة،
   لكنه السند نفسه المستخدَم لاحقًا في تقنية حذف `EntityRole`/
   `EntityRepresentative` — راجع المستند الرابع).
2. `.claude/plans/entity-permissions-and-lifecycle-vision.md` — دورة حياة
   الكيان + RBAC العام (المكوّن 1)، والقرار بفصل جدول Overrides عن جدول
   Audit كمبدأ عام.
3. `.claude/plans/entity-membership-system-vision.md` — قرار تعميم
   `EntityRole`/`EntityRepresentative` الحالية في `sovereign_entities` إلى
   `EntityMembership` عام، زائد Entity-Level Permission Overrides (المكوّنان
   2 و3).
4. `.claude/plans/entity-membership-technical-design.md` — **المرجع
   التقني المباشر**: schema كامل لثلاثة جداول (`entity_memberships`,
   `entity_permission_overrides`, `permission_audit_log`)، الموقع
   (`app/core/`)، قرار الحذف المباشر بلا ترحيل، واستراتيجية Strangler Fig
   على جلستين.

**نطاق هذه الجلسة (تأكيد):** الجلسة 1 فقط — بناء الأساس العام، بمعزل تام
عن `sovereign_entities`. صفر تنفيذ فوري — عرض خطة للموافقة أولاً.

---

## 2. استكشاف الكود الفعلي (تم) — قبل صياغة الخطة

للتأكد أن الخطة تتطابق مع بنية المشروع الفعلية لا الافتراضات النظرية فقط:

- `app/core/` **لا يحتوي على `models.py` حاليًا** (22 ملف أدوات بنية تحتية،
  صفر موديلات ORM). لا تعارض مع خطة وضع الموديلات الثلاثة هناك.
- نمط repository/service قائم فعليًا في المشروع (مثال حي:
  `app/domains/sovereign_entities/repository.py` +
  `app/domains/sovereign_entities/service.py`) — سأتبع نفس النمط.
- **اكتشاف جانبي (يخص دقة الـschema الموثَّق، يتطلب توقف وعرض — راجع §3
  أدناه):** جدول الـtenants الفعلي في المشروع اسمه `academy_tenants`
  (`app/domains/academy/models.py:13`)، **وليس `tenants`** كما ورد حرفيًا
  في `entity-membership-technical-design.md` §3/§4/§5 (`tenant_id ...
  FK → tenants.id`). كل موديل كيان قائم فعليًا (`SovereignEntity`
  `sovereign_entities/models.py:51`، `AffiliateActionCommission`
  `migrations/versions/028_...py:27`) يستخدم فعليًا
  `ForeignKey("academy_tenants.id")`. لا يوجد جدول باسم `tenants` في
  المشروع إطلاقًا (تحقق بحث شامل).
- جدول المستخدمين: `users` (`app/domains/identity/models.py:15`) —
  يطابق الموثَّق بالضبط، لا تعارض.
- قاعدة البيانات الحية فعليًا: حاوية Docker باسم `eppne_db` (منفذ 5435)،
  قاعدة البيانات داخلها اسمها `eppne_v2` (`eppne-backend/.env`). ملف
  `alembic.ini` يحمل رابط اتصال مختلف تمامًا (منفذ 5433، قاعدة `eppne`)
  لكنه **غير مستخدَم فعليًا** — `migrations/env.py:70` يقرأ الرابط من
  `DATABASE_URL`/`settings` مباشرة، فيتجاوز `alembic.ini` تلقائيًا. إذًا
  "قاعدة `eppne_db`" في تعليمات الجلسة تُقصَد بها الحاوية الحية فعليًا —
  لا تعارض حقيقي، فقط توضيح.
- رأس الـmigrations الحالي (head): `028_create_affiliate_action_commissions`
  (بلا أي migration لاحقة تعتمد عليه).
- نمط الـmigration المتبع فعليًا: ملفات مرقَّمة يدويًا (`op.create_table` +
  `op.create_index` صريحة)، لا Alembic autogenerate — راجع
  `migrations/versions/028_create_affiliate_action_commissions.py` كمرجع
  نمط مباشر.
- `tests/conftest.py`: fixture `db` يعطي جلسة `AsyncSessionLocal` حقيقية
  ضد القاعدة الحية، بلا أي mock — يطابق تمامًا معيار "تحقق حي" المطلوب في
  تعليمات الجلسة.

---

## 3. اكتشاف جانبي يتطلب توقف وعرض (قبل الخطة)

**البند:** `entity-membership-technical-design.md` يكتب صراحة (§3، §4)
`tenant_id ... FK → tenants.id` لكل من `entity_memberships` و
`entity_permission_overrides`. **لا يوجد جدول باسم `tenants` في قاعدة
كود المشروع فعليًا** — الجدول الوحيد الموجود هو `academy_tenants`
(دليل: `app/domains/academy/models.py:13`)، وهو ما يستخدمه بالفعل كل FK
مشابه قائم اليوم (`sovereign_entities.tenant_id`،
`affiliate_action_commissions.tenant_id`).

**القرار المقترَح (معروض للموافقة، لا مُطبَّق):** استخدام
`ForeignKey("academy_tenants.id")` فعليًا في كل من الجدولين — تطبيقًا
حرفيًا لنية المستند (denormalized FK لجدول الـtenant الحقيقي في المشروع)
لا لنص حرفي غير مطابق لاسم جدول غير موجود. **لن يُطبَّق أي كود قبل
موافقتك الصريحة على هذه النقطة تحديدًا ضمن موافقتك على الخطة كاملة.**

> **✅ موافقة صريحة [نفس الجلسة]:** المستخدم وافق على استخدام
> `ForeignKey("academy_tenants.id")` فعليًا في كل من `entity_memberships`
> و`entity_permission_overrides`. **ملاحظة تكميلية على
> `entity-membership-technical-design.md` §3/§4** (بنفس أسلوب الملاحظات
> التكميلية السابقة الموثَّقة في نفس المستند وفي
> `entity-membership-system-vision.md` §5): النص الحرفي `tenant_id ...
> FK → tenants.id` في §3/§4 من ذلك المستند يُقصَد به تقنيًا جدول الـtenant
> الحقيقي في المشروع لتفعيل نمط الـdenormalization الموصوف — وهو فعليًا
> `academy_tenants` (لا يوجد جدول باسم `tenants` في قاعدة الكود، تحقق
> بحث شامل، `app/domains/academy/models.py:13`). كل FK كياني مشابه قائم
> فعليًا اليوم (`sovereign_entities.tenant_id`،
> `affiliate_action_commissions.tenant_id`) يستخدم `academy_tenants.id`
> بالفعل. **هذا تصحيح تطبيقي لاسم الجدول الحرفي فقط — لا تغيير في القرار
> المعماري نفسه (denormalized tenant_id FK) الذي حسمه ذلك المستند.**

---

## 4. خطة التنفيذ الكاملة (معروضة للموافقة — صفر تنفيذ حتى الآن)

راجع الرسالة المرسَلة للمستخدم في نفس توقيت هذا القسم من التقرير لتفاصيل
الخطة الكاملة (الموديلات، الـmigration، تصميم CRUD ومكانه). سيُحدَّث هذا
القسم بعد الموافقة أو التعديل المطلوب.

**✅ موافقة نهائية صريحة من المستخدم على التصميم الكامل** (الموديلات
الثلاثة، migration 029، Repository+Service في `app/core/`،
`ondelete='RESTRICT'`، تعديل `migrations/env.py`)، مع تأكيد إضافي: صفر
استيراد من `sovereign_entities`/أي دومين وظيفي في `EntityMembershipService`،
وdocstring واضح أن فحص التفويض مسؤولية الدومين المستدعي (الجلسة 2).

---

## 5. التنفيذ الفعلي

### 5.1 الملفات

| الملف | الحالة |
|---|---|
| `app/core/models.py` | جديد — `EntityMembershipRole`, `AuditScope`, `AuditAction`, `EntityMembership`, `EntityPermissionOverride`, `PermissionAuditLog` |
| `migrations/versions/029_create_entity_membership_foundation.py` | جديد — `down_revision='028_create_affiliate_action_commissions'` |
| `app/core/entity_membership_repository.py` | جديد — `EntityMembershipRepository` |
| `app/core/entity_membership_service.py` | جديد — `EntityMembershipService` (docstring صريح: صفر استيراد من أي دومين، صفر فحص تفويض، هذا مسؤولية المُستدعي في الجلسة 2) |
| `migrations/env.py` | تعديل وحيد على ملف موجود — إضافة `from app.core.models import *` |

`git status` (مقتصر على `app/core/` و`migrations/`) يطابق الخطة بالضبط —
4 ملفات جديدة + تعديل سطر واحد على `env.py`. **صفر تغيير على أي ملف داخل
`sovereign_entities/`** (تحقق مباشر).

### 5.2 تطبيق الـmigration

```
$ python -m alembic current
028_create_affiliate_action_commissions   # الرأس قبل التنفيذ، كما هو موثَّق

$ python -m alembic upgrade head
INFO  Running upgrade 028_... -> 029_create_entity_membership_foundation
```

نجح بلا أخطاء. تحقق حي مباشر عبر `\d` (داخل حاوية `eppne_db`، قاعدة
`eppne_v2` — نفس القاعدة الحية التي يقرأها `migrations/env.py` فعليًا من
`DATABASE_URL`) على الجداول الثلاثة، طابق الموثَّق بالضبط: كل عمود،
نوعه، `NOT NULL`، القيم الافتراضية، القيود الفريدة (`uq_entity_membership`،
`uq_entity_permission_override`)، الفهارس الثلاثة على كل من
`entity_memberships`/`permission_audit_log`، وكل الـForeign Keys بما فيها
`academy_tenants.id` (بدل `tenants.id` الحرفي) و`ondelete='RESTRICT'` على
`granted_by`/`performed_by`.

### 5.3 تحقق حي لمنطق CRUD (Service layer، بيانات throwaway)

بيانات الاختبار: `entity_type="_TEST_ENTITY"`, `entity_id=999001`,
`tenant_id=1` (tenant حقيقي موجود، مُستخدَم فقط كـFK صالح — لا علاقة
ببيانات SOVEREIGN_ENTITY)، `user_id` 1 و2 (مستخدمان حقيقيان موجودان،
لنفس الغرض). سكريبت تحقق مستقل شغّل عبر `EntityMembershipService`
مباشرة (نفس مسار الاستدعاء الذي سيستخدمه أي دومين مستقبلًا)، ثم **تحقق
مستقل بجلسة `psql` منفصلة تمامًا** (لا اعتماد على القيمة المُرجَعة من
نفس الاستدعاء) لكل نتيجة:

| الاختبار | نتيجة الاستدعاء (Service) | تحقق SQL مستقل | الحالة |
|---|---|---|---|
| `add_member` (OWNER) | `id=1` أُنشئ | — | ✅ |
| قيد فريد: دور ثانٍ لنفس (entity×user) | `IntegrityError` صريح، `rollback()` | `COUNT(*)`=1 لصف `user_id=1` | ✅ **فشل كما يجب** |
| `add_member` (REPRESENTATIVE، عضو ثانٍ) | `id=3` أُنشئ | `SELECT` يعرض صفين (`user_id`=1,2) | ✅ |
| `list_members(_TEST_ENTITY, 999001)` | 2 أعضاء بالضبط | مطابق | ✅ فهرس `(entity_type, entity_id)` |
| `list_entities_for_user(user=1, tenant=1)` | 1 تطابق لكيان الاختبار | `SELECT ... WHERE user_id=1 AND tenant_id=1` → صف واحد مطابق | ✅ فهرس `(user_id, tenant_id)` |
| `change_role(user=2 → EXECUTIVE_DIRECTOR)` | نجح | مطابق في جدول `\d` أعلاه | ✅ |
| `grant_permission(can_sign_contracts, user=1)` | override `id=1`, `granted=True` | `COUNT(*)`=1 | ✅ |
| `check_permission` بعد المنح | `True` | — | ✅ |
| `revoke_permission` لنفس التركيبة | **نفس `id=1`** (upsert)، `granted=False` | `COUNT(*)`=1 (لم يصر 2)، `granted=f` فعليًا في القاعدة | ✅ **upsert مؤكَّد، لا صف مكرَّر** |
| `check_permission` بعد السحب | `False` | — | ✅ |
| `check_permission` لعضو بلا override | `None` | — | ✅ (الحالة الثالثة الموثَّقة: غياب الصف = القرار يرجع لمنطق الدور) |
| **Audit تلقائي** — بلا أي استدعاء منفصل لـ`_insert_audit_row` من سكريبت التحقق | — | `SELECT` على `permission_audit_log` → **صفان بالضبط**: `GRANT` ثم `REVOKE`، بنفس `performed_by=1`، ترتيب زمني صحيح | ✅ **الضمان الأساسي محقَّق** |

**تنظيف:** كل صفوف `_TEST_ENTITY` (999001) حُذفت من الجداول الثلاثة بعد
التحقق (`DELETE` مباشر، تأكيد `COUNT`=0 نهائيًا). لا أثر لبيانات throwaway
متبقٍّ في القاعدة الحية.

**اكتشاف جانبي بسيط أثناء كتابة سكريبت التحقق (لا يمس الكود المُنتَج
نفسه):** سكريبت تحقق مستقل بلا استيراد كامل لتطبيق FastAPI (`app.main`)
يفشل بـ`NoReferencedTableError`/`InvalidRequestError` عند أي `flush`
يلمس FK لجدول من دومين آخر (`academy_tenants`) أو `relationship()` بأسماء
سلسلة نصية عبر دومينات (`User.wallet` → `finance.models.Wallet`) —
سلوك SQLAlchemy القياسي (تسجيل الكلاسات كسول عبر الاستيراد)، وليس خطأً
في هذا التنفيذ. الحل: استيراد `app.main` في بداية سكريبت التحقق (نفس
مسار تسجيل الموديلات الذي يستخدمه التطبيق الحقيقي وaAlembic `env.py`
بالفعل). **لا يؤثر هذا على تشغيل الموديلات الثلاثة الجديدة داخل التطبيق
الفعلي** — `main.py` يستورد كل الدومينات بالفعل عبر سلسلة الراوترات.

**✅ مراجعة المستخدم للتحقق الحي: مقبولة بلا تعديل.** طُلب استكمال
regression test دائم + README، ثم تحديث `PROGRESS_LOG.md`، ثم عرض
`git status` نهائي قبل أي commit فعلي.

---

## 6. Regression test دائم

**الملف:** `tests/test_entity_membership_foundation.py` (8 اختبارات) +
`tests/test_entity_membership_foundation.md` (README مخصص، بنفس نمط
`test_affiliate_service_missing_methods.md`).

يغطي كل السيناريوهات الحاسمة من التحقق الحي اليدوي (§5.3)، بمنهجية
"تحقق مستقل" (SELECT مباشر، وحيث ينطبق عبر جلسة `AsyncSessionLocal`
منفصلة تمامًا لا نفس جلسة الاستدعاء): إنشاء عضوية + `list_members`، القيد
الفريد، `list_entities_for_user`، `change_role`، `remove_member`،
`grant_permission` + audit تلقائي، `revoke_permission` (upsert) + audit
ثانٍ، و`check_permission` بحالاته الثلاث (`None`/`True`/`False`).

**اكتشاف جانبي أثناء كتابة الاختبار (سبب فشل أول تشغيلة، مُصحَّح فورًا):**
الاختبار رقم 2 (القيد الفريد) استخدم في البداية نفس جلسة `db` لكل من
المحاولة الناجحة، المحاولة الفاشلة (`IntegrityError` متوقَّع)، و`rollback()`
ثم استكمال التحقق — فشل بـ`sqlalchemy.exc.MissingGreenlet` عند أول
استعلام تالٍ (تفاعل `pool_pre_ping=True` مع asyncpg بعد فشل `commit`).
**هذا نمط معروف وموثَّق مسبقًا في المشروع نفسه** — نفس الاحتياط المطبَّق
فعليًا في `test_ai_agents_execute_action.py`
(`"IntegrityError بيسمّم أي جلسة تحصل فيها"`) و`test_saas_active_subscription.py`.
الإصلاح: عزل المحاولة المتوقَّع فشلها في جلسة `AsyncSessionLocal` مستقلة
تمامًا (`async with AsyncSessionLocal() as db2`) — لا إزالة السيناريو ولا
تغيير في منطق `EntityMembershipRepository`/`Service` نفسه (الكود المُنتَج
سليم؛ المشكلة كانت في بنية الاختبار فقط).

**نتيجة التشغيل (تشغيلتان متتاليتان، بعد الإصلاح):**
```
================== 8 passed, 9 warnings in 108.59s ==================
================== 8 passed, 9 warnings in 111.49s ==================
```
صفر تذبذب. تحقق مستقل عبر `psql` بعد كل تشغيلة أكَّد **صفر بيانات
throwaway متبقية** (`entity_memberships`/`entity_permission_overrides`/
`permission_audit_log` بـ`entity_type='_TEST_ENTITY'`، و`users` بـ
`username LIKE 'em_%'` — كلها `0`).

**الحالة الحالية: regression test مكتمل ومُتحقَّق منه حيًا. التالي:
تحديث `PROGRESS_LOG.md` ثم عرض `git status` نهائي — لم يحدث أي commit
بعد.**

---

## 7. تحديث `PROGRESS_LOG.md`

- **بانر الحالة** (لأعلى الملف) استُبدل بالكامل — كان يوثّق آخر إغلاق
  (`security-deps-unification`)، صار يوثّق `entity-membership-foundation`
  كآخر إغلاق رسمي، بنفس مستوى التفصيل (الموديلات الثلاثة كاملة،
  الـmigration، مكان/توقيعات CRUD، نتيجة التحقق الحي المزدوج، وتأكيد صريح
  "صفر لمس على `sovereign_entities`").
- **قائمة الجلسات المُقفلة** (append-only): سطر جديد أُضيف بعد
  `security-deps-unification` مباشرة (قبل ملاحظة "لم تُراجَع بثقة كافية"
  الختامية) — بنفس محتوى البانر مختصرًا لنمط سطر واحد كثيف كباقي القائمة.
- **لا إضافة لجدول الـBacklog النشط عمدًا** — هذا بناء بنية تحتية جديدة
  ضمن خارطة طريق معلنة (المستندات الأربعة)، وليس إصلاح باج/فجوة مكتشَفة،
  فلا يطابق غرض ذلك الجدول (نفس المنطق المتبع مع `security-deps-unification`
  نفسها، غير مُدرَجة في جدول الـBacklog أيضًا).

تحقق بنيوي بعد التعديل: تسلسل الأقسام الثلاثة (`بانر الحالة` →
`جدول الـBacklog النشط` → `الجلسات المُقفلة`) سليم، صفر فساد encoding
(تأكيد Python UTF-8 مباشر)، 4 إشارات لـ`entity-membership-foundation`
عبر الملف (البانر + القائمة).

---

## 8. الحالة النهائية — بانتظار موافقة الـcommit

**كل الخطوات المطلوبة اكتملت:**
1. ✅ قراءة المستندات الأربعة.
2. ✅ عرض خطة تفصيلية كاملة، موافقة صريحة (بما فيها تصحيح `academy_tenants.id`).
3. ✅ تنفيذ الموديلات + الـmigration + Repository/Service.
4. ✅ تحقق حي كامل يدوي، مراجعة وموافقة المستخدم.
5. ✅ Regression test دائم (8 اختبارات) + README، تشغيلتان متتاليتان
   نظيفتان.
6. ✅ تحديث `PROGRESS_LOG.md` (البانر + قائمة الجلسات المُقفلة).

**لم يحدث بعد:** أي `git add`/`git commit`. `git status` النهائي معروض
في رسالة الرد للمستخدم مباشرة، بانتظار موافقته الصريحة على الـcommit قبل
تنفيذه.

---

## 9. Commit — منفَّذ

**✅ موافقة صريحة من المستخدم** على الثمانية ملفات المعروضة بالضبط.
`git add` مقيَّد بالمسارات الثمانية صراحة (لا `git add -A`/`.`) — تحقق
`git status --short` بعد الإضافة أكَّد: كل باقي تغييرات الـrepo (جلسات
أخرى غير مرتبطة، `eppne-web/`، دومينات أخرى) بقيت **بلا `M`/`A`** في
العمود الأول (غير مُدرَجة).

```
[main c0ee2c2] feat(permissions): build EntityMembership foundation (session 1/2)
 8 files changed, 1172 insertions(+), 183 deletions(-)
```

رسالة الـcommit وثّقت صراحة: الثلاثة جداول + الموقع + Strangler Fig
(جلسة 1 من 2) + **تأكيد صريح أن `sovereign_entities` لم يُلمَس** + إشارة
للجلسة 2 المستقبلية المنفصلة + مرجع regression test + مرجع تقرير الجلسة.

**الجلسة مُغلَقة رسميًا.** لا كود إضافي أُنتج بعد هذا الـcommit. الجلسة 2
(الربط الفعلي بـ`sovereign_entities`) تنتظر جلسة منفصلة تمامًا، بموافقة
صريحة مستقبلية.
