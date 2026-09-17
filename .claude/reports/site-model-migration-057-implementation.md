# تنفيذ الخطوة 2: migration جدول `sites` الموحّد

**نوع الجلسة:** تنفيذ فعلي (migration حقيقي على قاعدة البيانات الشغالة).
جزء من خطة التنفيذ المتسلسلة المتفَق عليها — الخطوة 2 من 4. **بانتظار
موافقة صريحة قبل الانتقال للخطوة 3 (ربط iot/manufacturing/agritech/health
بـsite_id).**

**التاريخ:** 2026-09-17

---

## 1. الملفات المُنشأة/المُعدَّلة

| الملف | التغيير |
|---|---|
| `app/domains/sites/__init__.py` | جديد — دومين جديد، صفر repository/service/router بعد |
| `app/domains/sites/models.py` | جديد — موديل `Site` + enum `SiteType` (`native_enum=False`)، مطابق بالحرف لـ§1.3 من مستند التصميم الأول |
| `migrations/versions/057_create_sites_table.py` | جديد — migration واحد، جدول `sites` فقط، صفر لمس على أي جدول قائم |
| `migrations/env.py` | تعديل سطر واحد فقط — إضافة `from app.domains.sites.models import *` في قسم "المستوى 0: بنية تحتية عامة عابرة للدومينات" (بجانب `app.core.models`)، لتسجيل الموديل الجديد في `target_metadata` |

---

## 2. تفاصيل الموديل (`app/domains/sites/models.py`)

```python
class SiteType(str, enum.Enum):
    ACADEMY_CAMPUS = "ACADEMY_CAMPUS"
    FACTORY = "FACTORY"
    FARM = "FARM"
    HEALTH_FACILITY = "HEALTH_FACILITY"
    SPORTS_CLUB = "SPORTS_CLUB"
    TOURISM_SITE = "TOURISM_SITE"
    TRANSPORT_HUB = "TRANSPORT_HUB"
    WAREHOUSE = "WAREHOUSE"
    GENERIC = "GENERIC"

class Site(Base):
    __tablename__ = "sites"
    id, tenant_id (FK academy_tenants.id CASCADE), parent_site_id (FK sites.id SET NULL),
    site_type (SQLEnum native_enum=False length=50), entity_type + entity_id (polymorphic، بلا FK),
    name, latitude/longitude (Numeric 9,6), address_text, geo_metadata (JSONB),
    manager_id (FK users.id), data_residency_preference (محجوز، بلا منطق فرض),
    is_active, created_at/updated_at, deleted_at/is_deleted (soft delete)
```

---

## 3. تحقق البنية بعد الـmigration — مباشرة على `eppne_db` (منفذ 5435, نفس `DATABASE_URL`)

```
docker exec eppne_db psql -U postgres -d eppne_v2 -c "\d sites"
```

**النتيجة الكاملة:**

```
                                              Table "public.sites"
          Column           |           Type           | Collation | Nullable |              Default
---------------------------+--------------------------+-----------+----------+-----------------------------------
 id                        | integer                  |           | not null | nextval('sites_id_seq'::regclass)
 tenant_id                 | integer                  |           | not null |
 parent_site_id            | integer                  |           |          |
 site_type                 | character varying(50)    |           | not null |
 entity_type               | character varying(50)    |           |          |
 entity_id                 | integer                  |           |          |
 name                      | character varying(255)   |           | not null |
 latitude                  | numeric(9,6)             |           |          |
 longitude                 | numeric(9,6)             |           |          |
 address_text              | character varying(500)   |           |          |
 geo_metadata              | jsonb                    |           |          |
 manager_id                | bigint                   |           |          |
 data_residency_preference | character varying(50)    |           |          |
 is_active                 | boolean                  |           |          | true
 created_at                | timestamp with time zone |           |          | now()
 updated_at                | timestamp with time zone |           |          | now()
 deleted_at                | timestamp with time zone |           |          |
 is_deleted                | boolean                  |           |          | false
Indexes:
    "sites_pkey" PRIMARY KEY, btree (id)
    "ix_site_entity" btree (entity_type, entity_id)
    "ix_site_parent" btree (parent_site_id)
    "ix_site_tenant_type" btree (tenant_id, site_type)
    "ix_sites_entity_id" btree (entity_id)
    "ix_sites_entity_type" btree (entity_type)
    "ix_sites_id" btree (id)
    "ix_sites_manager_id" btree (manager_id)
    "ix_sites_parent_site_id" btree (parent_site_id)
    "ix_sites_site_type" btree (site_type)
    "ix_sites_tenant_id" btree (tenant_id)
Foreign-key constraints:
    "sites_manager_id_fkey" FOREIGN KEY (manager_id) REFERENCES users(id)
    "sites_parent_site_id_fkey" FOREIGN KEY (parent_site_id) REFERENCES sites(id) ON DELETE SET NULL
    "sites_tenant_id_fkey" FOREIGN KEY (tenant_id) REFERENCES academy_tenants(id) ON DELETE CASCADE
```

**تأكيد مطابقة التصميم بالحرف:**
- ✅ الثلاثة فهارس المُسمّاة صراحةً في §1.3: `ix_site_tenant_type`, `ix_site_parent`, `ix_site_entity` — موجودة بالضبط بهذه الأسماء.
- ✅ `site_type` مُخزَّن `character varying(50)` — **صفر نوع ENUM في Postgres، وصفر CHECK constraint** (لا يظهر أي قيد باسمه في الجدول أعلاه) — يطابق قرار `native_enum=False` من §1.3.1 (إضافة قيمة جديدة مستقبلًا = صفر migration).
- ✅ `entity_type`/`entity_id` — **بلا أي FK constraint** (غائبان تمامًا من قسم "Foreign-key constraints" أعلاه) — يطابق قرار polymorphic بلا FK صريح من §1.2 (نمط `EntityMembership`).
- ✅ `parent_site_id` — FK ذاتي (`sites.id`) بـ`ON DELETE SET NULL` — يطابق التصميم (هرمية).
- ✅ `tenant_id` — FK لـ`academy_tenants.id` بـ`ON DELETE CASCADE`.
- ✅ صفر لمس على أي جدول قائم — الجدول الوحيد المُتأثِّر هو `sites` نفسه، جديد بالكامل.

---

## 4. أمر الـmigration نفسه

```
cd eppne-backend
PYTHONIOENCODING=utf-8 ./venv/Scripts/alembic.exe upgrade head
```

**النتيجة:**
```
INFO  [alembic.runtime.migration] Running upgrade 056_create_guardian_relationship_tables -> 057_create_sites_table
✅ [Alembic] Connecting to database at: postgresql+asyncpg://eppne:***REDACTED***@127.0.0.1:5435/eppne_v2
```

(`PYTHONIOENCODING=utf-8` ضروري فقط بسبب مشكلة ترميز console بويندوز
موجودة سلفًا في `migrations/env.py:90` — طباعة emoji بترميز `cp1256`
الافتراضي — **مشكلة قديمة غير متعلقة بهذه الجلسة**، تجاوزتها بدون أي
تعديل على الكود، مجرد متغير بيئة وقت التشغيل.)

`alembic heads` بعد التشغيل: `057_create_sites_table (head)` — رأس واحد
فقط، صفر تفرّع (branch) في تاريخ الـmigrations.

---

## 5. تحقق pytest — ✅ اكتمل، صفر انحدار

```
PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe -m pytest \
  --ignore=tests/test_affiliate_service_missing_methods.py -q
```

نفس استبعاد `test_affiliate_service_missing_methods.py` المعروف
(باج مسجَّل سابقًا غير متعلق بهذه الجلسة — راجع `backlog-review-2026-09-16-session-log.md`
و`redis-celery-env-path-fix-session-log.md`).

**النتيجة النهائية (بعد 22:52 دقيقة):**
```
13 failed, 225 passed, 2 xfailed, 287 warnings in 1372.41s (0:22:52)
```

**التحقق من مطابقة هذه النتيجة لـbaseline موثَّق سابقًا (صفر افتراض):**
قارنت قائمة الـ13 فشل بالضبط بما هو موثَّق في
`backlog-review-2026-09-16-session-log.md:258` — النتيجة المرجعية
المُحقَّقة يومها كانت **`13 failed, 225 passed, 2 xfailed`** بالحرف
(بعد إصلاح فشلين من أصل 15 في baseline الأصلي)، وكل الـ13 اسم اختبار
فاشل اليوم (`test_user_repository_get_by_id_audit.py` ×10،
`test_user_repository_get_user_audit.py` ×2،
`test_realestate_insurance_savepoint.py::test_realestate_buy_fractional_ownership_invoice_ordering`
×1) **مطابقون حرفيًا** لنفس القائمة المرجعية — كلها بنود مفتوحة/مُغلَقة
توثيقيًا بالفعل (تغيير سلوك متعمَّد مُحقَّق [2026-09-07]، وهشاشة اختبار
معروفة `test-savepoint-fragile-source-position-parsing`)، **صفر علاقة
بجدول `sites` أو أي ملف لمسته هذه الجلسة** (لا `app/domains/sites/`،
ولا `migrations/`، ولا `identity`/`realestate`/`affiliate` لمسناها).

**الخلاصة: صفر فشل جديد، صفر انحدار ناتج عن migration 057.** الملفات
الوحيدة المُتأثِّرة بهذه الجلسة (`app/domains/sites/*`,
`migrations/versions/057_*`, `migrations/env.py`) لا تتقاطع مع أي من
الـ13 اختبار الفاشل.

---

## الحالة الحالية — ✅ الخطوة 2 مكتملة ومُتحقَّقة بالكامل

- ✅ الموديل + الـmigration مكتملان ومطابقان للتصميم بالحرف.
- ✅ تحقق البنية على قاعدة البيانات الحية مكتمل ومطابق 100%.
- ✅ pytest الكامل: `13 failed, 225 passed, 2 xfailed` — **مطابق حرفيًا
  لـbaseline موثَّق مسبقًا، صفر فشل جديد**.
- ⏸️ **بانتظار موافقتك الصريحة قبل الانتقال للخطوة 3** (ربط
  iot/manufacturing/agritech/health بـ`site_id` — استبدال كامل في
  iot/manufacturing/agritech، إضافة فقط في health، بحسب المستند الأول).
