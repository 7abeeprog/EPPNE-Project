# تنفيذ الخطوة 3 (دومين 1/4): ربط `iot.SmartAsset` بـ`site_id`

**نوع الجلسة:** تنفيذ فعلي (migration + تعديل كود). جزء من خطة التنفيذ
المتسلسلة المتفَق عليها — الخطوة 3، دومين iot فقط. **بانتظار موافقة
صريحة قبل الانتقال لدومين manufacturing.**

**التاريخ:** 2026-09-17

---

## 1. التغيير الأساسي — استبدال كامل بحسب §1.4 من مستند التصميم الأول

| الملف | التغيير |
|---|---|
| `app/domains/iot/models.py` | `SmartAsset`: حذف `entity_id`/`location_gps`، إضافة `site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)`. `__table_args__`: `ix_smart_asset_entity` → `ix_smart_asset_site` |
| `app/domains/iot/schemas.py` | `SmartAssetCreate`/`SmartAssetUpdate`: حذف `entity_id`/`location_gps`، إضافة `site_id` (إلزامي في `Create`، اختياري في `Update`) |
| `migrations/versions/058_iot_smart_asset_site_id.py` | migration جديد — تفاصيل كاملة في §2 |

`app/domains/iot/service.py` و`repository.py` **بلا أي تعديل** — كلاهما
`**kwargs` passthrough بحت (`create_asset(tenant_id=..., owner_id=..., **data)`)،
فتغيير حقول الـschema كافٍ بلا أي منطق إضافي.

---

## 2. الـmigration (`058_iot_smart_asset_site_id.py`) — تفاصيل الحذف الصريحة

### 2.1 الصف الذي تم حذفه من `smart_assets` — تأكيد قبل التنفيذ

```sql
SELECT id, tenant_id, asset_code, asset_class, entity_id, created_at FROM smart_assets;
```

```
 id | tenant_id |     asset_code     |  asset_class  | entity_id |          created_at
----+-----------+--------------------+---------------+-----------+-------------------------------
  1 |         1 | P-CTOR-IOT-ASSET-1 | UTILITY_METER |           | 2026-08-14 17:53:48.575479+00
```

صف واحد، بيانات اختبار throwaway مؤكَّدة (نمط تسمية `P-CTOR-*` من جلسات
constructor-mismatch سابقة موثَّقة — راجع مستند التصميم الأول §0).

### 2.2 اكتشاف أثناء التنفيذ — صف تابع في `utility_readings`

أول محاولة تشغيل فشلت بـ`ForeignKeyViolationError` — فحصت **كل** الجداول
المُشيرة لـ`smart_assets.id` (`utility_readings`, `maintenance_logs`,
`farm_zones`, `production_lines`, `property_units`, `vehicles`) قبل أي
حذف إضافي:

```sql
SELECT id, asset_id, grid_id, reading_type, consumed_value, created_at
FROM utility_readings WHERE asset_id = 1;
```
```
 id | asset_id | grid_id | reading_type | consumed_value |          created_at
----+----------+---------+--------------+-----------------+------------------------------
  1 |        1 |         | BIOGAS       |          0.0000 | 2026-08-14 17:54:05.37682+00
```
(باقي الخمس جداول: **صفر صف** مرتبط بـ`asset_id=1`.)

صف واحد فقط، نفس تاريخ إنشاء الصف الاختباري بالضبط (2026-08-14) — نفس
جلسة constructor test، بيانات throwaway مؤكَّدة بنفس المنطق.

### 2.3 محتوى الحذف الفعلي في الـmigration (`upgrade()`)

```python
def upgrade() -> None:
    # اكتُشف أثناء التنفيذ: صف واحد في utility_readings (id=1, asset_id=1,
    # reading_type=BIOGAS, consumed_value=0) يشاور على smart_assets.id=1 —
    # نفس تاريخ إنشاء الصف الاختباري (2026-08-14)، نفس نمط بيانات throwaway
    # مؤكَّد. يُحذف أولًا لفكّ قيد FK قبل حذف smart_assets نفسه.
    op.execute("DELETE FROM utility_readings WHERE asset_id IN (SELECT id FROM smart_assets)")
    op.execute("DELETE FROM smart_assets")

    op.add_column('smart_assets', sa.Column('site_id', sa.Integer(), nullable=False))
    op.create_foreign_key('smart_assets_site_id_fkey', 'smart_assets', 'sites', ['site_id'], ['id'])
    op.create_index('ix_smart_assets_site_id', 'smart_assets', ['site_id'], unique=False)
    op.create_index('ix_smart_asset_site', 'smart_assets', ['site_id'], unique=False)

    op.drop_index('ix_smart_asset_entity', table_name='smart_assets')
    op.drop_index('ix_smart_assets_entity_id', table_name='smart_assets')
    op.drop_column('smart_assets', 'entity_id')
    op.drop_column('smart_assets', 'location_gps')
```

**ملخص الحذف — للمراجعة اللاحقة:**
- **2 صفوف حُذفت فعليًا، من جدولين، صفر غيرهم:** صف واحد في
  `smart_assets` (id=1, `P-CTOR-IOT-ASSET-1`) + صف واحد في
  `utility_readings` (id=1, تابع للأول عبر `asset_id`).
- **السبب:** كلاهما بيانات اختبار throwaway من جلسة constructor-mismatch
  قديمة (تاريخ 2026-08-14)، صفر علاقة بأي بيانات إنتاج حقيقية (لا يوجد
  إنتاج حقيقي بالمشروع حاليًا — مؤكَّد في مستند التصميم الأول §0).
- **صفر إعادة إدراج** — لا حاجة لبيانات في `smart_assets`/`utility_readings`
  بعد هذه الخطوة، الجدولان فاضيان تمامًا بعد الـmigration (تأكيد §3).

### 2.4 تأكيد ما بعد الحذف — العدد صفر، بلا إعادة إدراج

```sql
SELECT count(*) FROM smart_assets;      -- 0
SELECT count(*) FROM utility_readings;  -- 0
```

---

## 3. تحقق البنية بعد الـmigration — مباشرة على `eppne_db`

```
docker exec eppne_db psql -U postgres -d eppne_v2 -c "\d smart_assets"
```

```
                                           Table "public.smart_assets"
       Column       |           Type           | Collation | Nullable |                 Default
--------------------+--------------------------+-----------+----------+------------------------------------------
 id                 | integer                  |           | not null | nextval('smart_assets_id_seq'::regclass)
 owner_id           | bigint                   |           |          |
 asset_code         | character varying(100)   |           | not null |
 asset_class        | assetclass               |           | not null |
 specs              | jsonb                    |           |          |
 is_online          | boolean                  |           |          |
 health_status      | devicehealthstatus       |           |          |
 hardware_did       | character varying(255)   |           |          |
 iot_wallet_address | character varying(42)    |           |          |
 created_at         | timestamp with time zone |           |          | now()
 updated_at         | timestamp with time zone |           |          | now()
 deleted_at         | timestamp with time zone |           |          |
 is_deleted         | boolean                  |           |          |
 tenant_id          | integer                  |           | not null |
 site_id            | integer                  |           | not null |
Foreign-key constraints:
    "fk_smart_assets_tenant_id" FOREIGN KEY (tenant_id) REFERENCES academy_tenants(id) ON DELETE CASCADE
    "smart_assets_owner_id_fkey" FOREIGN KEY (owner_id) REFERENCES users(id)
    "smart_assets_site_id_fkey" FOREIGN KEY (site_id) REFERENCES sites(id)
```

**تأكيد:** ✅ `entity_id`/`location_gps` غائبان تمامًا. ✅ `site_id`
`NOT NULL` + FK حقيقي لـ`sites.id`. ✅ `real_estate_unit_id` (غير موجود
أصلًا في iot، بلا لمس) و`ProductionLine.facility_id`/`SmartFarm.land_asset_id`
(دومينات تانية، صفر لمس في هذه الخطوة).

---

## 4. اكتشاف حرج أثناء التحقق — Site لم يكن مُسجَّلًا في `Base.metadata` عند التشغيل الفعلي

### 4.1 العطل

أول تشغيل كامل لـpytest بعد migration 058 رجّع **فشل جديد مختلف عن
الـ13 المعروفين**:
```
FAILED tests/test_iot_carbon_settlement_response_schema.py::test_settle_carbon_credits_success_matches_response_schema
sqlalchemy.exc.NoReferencedTableError: Foreign key associated with column
'smart_assets.site_id' could not find table 'sites' ...
```

### 4.2 السبب الجذري (مؤكَّد بفحص `app/main.py` كامل، بطلب صريح من صاحب المشروع)

**كل دومين في المشروع يتسجّل في `Base.metadata` حصريًا عبر استيراد
`router.py` بتاعه في `main.py`** (`from app.domains.X.router import
router as X_router` + سطر في `routers_config`) — الاستيراد ده بيسحب
`service.py`→`repository.py`→`models.py` بالتبعية. **صفر registry مركزي
تاني.** دومين `sites` كان **بلا `router.py` من الأساس** (متعمَّد —
صفر endpoint في خطة التصميم)، فموديل `Site` **لم يكن مُستورَدًا في أي
مكان بمسار تشغيل التطبيق الفعلي** — فقط في `migrations/env.py` (غير
مُستخدَم وقت تشغيل pytest/FastAPI). أي عملية ORM حقيقية على جدول له FK
نصّي لـ`sites.id` (زي `smart_assets` بعد migration 058) كانت ستفشل بنفس
الخطأ **في التطبيق الشغّال نفسه كمان، مش الاختبار بس**.

### 4.3 الحل المُطبَّق — اتّباع النمط الموجود بالحرف، صفر استثناء جديد

- `app/domains/sites/router.py` **جديد** — `APIRouter(prefix="/sites", tags=["Sites"])`
  بصفر endpoint فعلي، غرضه الوحيد سحب `models.py` بالتبعية (نفس آلية كل دومين).
- `app/main.py` — سطرين فقط: استيراد `sites_router` (بترتيب أبجدي بين
  `service_marketplace` و`social`) + إضافة `(sites_router, "/sites",
  ["Sites"], "sites")` في `routers_config`، **بنفس الصياغة الحرفية** لكل
  سطر تاني في القائمة.
- تحقق: `python -c "import app.main"` نجح بلا أخطاء.

### 4.4 عطل تابع اكتُشف فورًا بعد إصلاح التسجيل

`test_iot_carbon_settlement_response_schema.py` كان بيعمل `SmartAsset`
حقيقي عبر `IoTRepository.create_asset(...)` **بلا `site_id`** (الاختبار
أقدم من التصميم الجديد) — فشل بـ`IntegrityError` (NOT NULL violation)
بعد إصلاح التسجيل. **إصلاح مطلوب ومتوقَّع** (نتيجة طبيعية للاستبدال
الكامل، لا علاقة له بمشكلة التسجيل في §4.2-4.3):

- استوردت `Site`/`SiteType` في الاختبار.
- أنشأت صف `Site` حقيقي (`SiteType.GENERIC`) قبل إنشاء الأصل، ومررت
  `site_id=site.id` لـ`create_asset(...)`.
- أضفت الصف لتنظيف `_cleanup()` (حذف صريح بعد الاختبار — صفر بيانات
  متبقية، بعكس الصف الاختباري القديم `P-CTOR-IOT-ASSET-1` اللي فضل
  متروك لجلسات لاحقة).
- تحقق مُفرَد: `pytest tests/test_iot_carbon_settlement_response_schema.py` → `2 passed`.

---

## 5. تحقق pytest الكامل — ✅ صفر انحدار، مطابقة حرفية لـbaseline

```
PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe -m pytest \
  --ignore=tests/test_affiliate_service_missing_methods.py -q
```

**ملاحظة تشغيلية:** أول محاولة إعادة تشغيل بعد إصلاحات §4 توقفت (`killed`)
بسبب نقص ذاكرة النظام مؤقتًا (توقفت عند ~30% تقدّم، صفر فشل ظاهر قبل
التوقف) — مشكلة بيئة تشغيل، صفر علاقة بالكود. أُعيد التشغيل وأكمل
بنجاح.

**النتيجة النهائية:**
```
13 failed, 225 passed, 2 xfailed, 287 warnings in 4591.98s (1:16:31)
```

**مقارنة الأسماء بالحرف مع baseline الموثَّق (`backlog-review-2026-09-16-session-log.md`,
وتقرير migration 057 السابق):**

| الاختبار الفاشل | في baseline؟ |
|---|---|
| `test_realestate_insurance_savepoint.py::test_realestate_buy_fractional_ownership_invoice_ordering` | ✅ |
| `test_user_repository_get_by_id_audit.py` ×10 (نفس الأسماء بالضبط) | ✅ |
| `test_user_repository_get_user_audit.py` ×2 (نفس الأسماء بالضبط) | ✅ |

**13/13 مطابقون حرفيًا — صفر اسم فشل جديد، صفر اسم غائب.** كل الفشلين
الجديدين اللي ظهروا مؤقتًا أثناء هذه الجلسة (§4) تم تشخيصهم وإصلاحهم
قبل هذا التشغيل النهائي.

---

## الحالة الحالية — ✅ دومين iot مكتمل ومُتحقَّق منه بالكامل

- ✅ استبدال كامل `entity_id`/`location_gps` → `site_id NOT NULL`.
- ✅ الحذف الوحيد المطلوب (صفين throwaway، موثَّق بالتفصيل في §2) — صفر
  إعادة إدراج، العدد صفر مؤكَّد.
- ✅ اكتشاف وإصلاح باج تسجيل حقيقي كان سيكسر التطبيق الشغّال فعليًا
  (`app.domains.sites` غير مُسجَّل) — بنفس نمط المشروع الموجود، صفر
  استثناء جديد.
- ✅ اكتشاف وإصلاح اختبار تابع (`test_iot_carbon_settlement_response_schema.py`).
- ✅ pytest الكامل: `13 failed, 225 passed, 2 xfailed` — **مطابقة حرفية
  100%** لأسماء baseline.
- ⏸️ **بانتظار موافقتك الصريحة قبل الانتقال لدومين manufacturing**
  (`ManufacturingFacility` — استبدال كامل، `real_estate_unit_id` وProductionLine
  بلا لمس).
