# تنفيذ الخطوة 3 (دومين 2/4): ربط `manufacturing.ManufacturingFacility` بـ`site_id`

**نوع الجلسة:** تنفيذ فعلي (migration + تعديل كود). جزء من خطة التنفيذ
المتسلسلة المتفَق عليها — الخطوة 3، دومين manufacturing فقط. **بانتظار
موافقة صريحة قبل الانتقال لدومين agritech.**

**التاريخ:** 2026-09-17

---

## 1. التغيير الأساسي — استبدال كامل بحسب §1.4 من مستند التصميم الأول

| الملف | التغيير |
|---|---|
| `app/domains/manufacturing/models.py` | `ManufacturingFacility`: حذف `entity_id`/`location_gps`، إضافة `site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)`. `real_estate_unit_id` بلا لمس. `__table_args__`: `ix_manufacturing_facility_entity` → `ix_manufacturing_facility_site` |
| `app/domains/manufacturing/schemas.py` | `ManufacturingFacilityCreate`: حذف `entity_id`/`location_gps`، إضافة `site_id` (إلزامي). `real_estate_unit_id` بلا لمس |
| `app/domains/manufacturing/service.py` | `create_facility()` (سطر ~106-114): استبدال `entity_id=data["entity_id"]` بـ`site_id=data["site_id"]`، حذف سطر `location_gps=data.get("location_gps")` |
| `migrations/versions/059_manufacturing_facility_site_id.py` | migration جديد — تفاصيل كاملة في §2 |

**فرق عن iot لاحظته أثناء الفحص:** `manufacturing.service.create_facility`
(بعكس `iot.repository`) **لا يستخدم `**kwargs` passthrough بحت** — بيستخرج
`entity_id`/`location_gps` صراحةً من الـdict (`data["entity_id"]`,
`data.get("location_gps")`)، فاحتاج تعديل صريح في `service.py` نفسه، لا
مجرد الـschema. `ProductionLine` (الطفل) **بلا أي تعديل** — لسه بيشاور
`facility_id` عادي.

---

## 2. الـmigration (`059_manufacturing_facility_site_id.py`) — سلسلة الحذف الكاملة موثَّقة

### 2.1 فحص كل الجداول التابعة قبل أي حذف (بالترتيب من الأعلى للأسفل)

`manufacturing_facilities` له فرعان مباشران (`product_blueprints.facility_id`,
`production_lines.facility_id`)، وكل واحد منهم له فروع تابعة بدوره. فحصت
السلسلة كاملة قبل كتابة أي `DELETE`:

| الجدول | الصفوف الموجودة | تفاصيل |
|---|---|---|
| `manufacturing_facilities` | **2** | `id=1` (`P-CTOR-MFG-FACILITY`, tenant 1, 2026-08-17) + `id=5` (`MANUFACTURING-CANACCESS-PILOT-TENANT16`, tenant 16, 2026-09-07) |
| `production_lines` (facility_id) | **1** | `id=1`, `facility_id=1`, `name="P-CTOR-MFG-LINE"` |
| `product_blueprints` (facility_id) | **1** | `id=1`, `facility_id=1`, `sku="P-CTOR-SKU-1"` |
| `production_batches` (line_id **أو** product_blueprint_id) | **1** | `id=1`, `line_id=1`, `product_blueprint_id=1` (نفس تاريخ 2026-08-17 — نفس سلسلة constructor test) |
| `predictive_maintenance_logs` (production_line_id=1) | **0** | — |
| `product_digital_twins` (production_line_id=1) | **0** | — |
| `material_consumption_logs` (batch_id=1) | **0** | — |
| `smart_product_items` (batch_id=1) | **0** | — |

**ملاحظة مهمة:** `manufacturing_facilities.id=5` (المنشأة الأخرى، tenant 16)
**صفر تابعين** — لا `production_lines` ولا `product_blueprints` تشاور
عليها. تُحذف مباشرة بلا سلسلة.

**الخلاصة: 5 صفوف حقيقية حُذفت، من 4 جداول (manufacturing_facilities×2,
production_lines×1, product_blueprints×1, production_batches×1)** —
كل واحد منهم بيانات اختبار/pilot throwaway مؤكَّدة (نمط تسمية `P-CTOR-*`/
`*-CANACCESS-PILOT-*`، ونفس تجميع تاريخي 2026-08-17 لسلسلة constructor
واحدة). **صفر إعادة إدراج.**

### 2.2 محتوى الحذف الفعلي (`upgrade()`)

```python
op.execute("""
    DELETE FROM material_consumption_logs WHERE batch_id IN (
        SELECT id FROM production_batches WHERE line_id IN (
            SELECT id FROM production_lines WHERE facility_id IN (SELECT id FROM manufacturing_facilities)
        ) OR product_blueprint_id IN (
            SELECT id FROM product_blueprints WHERE facility_id IN (SELECT id FROM manufacturing_facilities)
        )
    )
""")
op.execute("""DELETE FROM smart_product_items WHERE batch_id IN (...)""")          # نفس الشرط
op.execute("""DELETE FROM predictive_maintenance_logs WHERE production_line_id IN (
    SELECT id FROM production_lines WHERE facility_id IN (SELECT id FROM manufacturing_facilities)
)""")
op.execute("""DELETE FROM product_digital_twins WHERE production_line_id IN (...)""")  # نفس الشرط
op.execute("""DELETE FROM production_batches WHERE line_id IN (...) OR product_blueprint_id IN (...)""")
op.execute("DELETE FROM production_lines WHERE facility_id IN (SELECT id FROM manufacturing_facilities)")
op.execute("DELETE FROM product_blueprints WHERE facility_id IN (SELECT id FROM manufacturing_facilities)")
op.execute("DELETE FROM manufacturing_facilities")
```

**سبب استخدام subqueries مرتبطة بـ`manufacturing_facilities` (بدل حذف
مباشر بالـid) عمدًا:** يضمن إن الحذف مقصور فعليًا على السلالة التابعة
للمنشآت المحذوفة، لا أي صف تابع مستقبلي غير متعلق — احتياط دفاعي حتى لو
كل الصفوف الحالية مؤكَّدة throwaway.

### 2.3 تأكيد ما بعد الحذف — العدد صفر في كل الجداول الستة، بلا إعادة إدراج

```sql
manufacturing_facilities: 0    production_lines: 0
product_blueprints: 0          production_batches: 0
material_consumption_logs: 0   smart_product_items: 0
```

---

## 3. تحقق البنية بعد الـmigration

```
docker exec eppne_db psql -U postgres -d eppne_v2 -c "\d manufacturing_facilities"
```

```
                                             Table "public.manufacturing_facilities"
         Column          |           Type           | Nullable |                       Default
-------------------------+--------------------------+----------+------------------------------------------------------
 id                      | integer                  | not null | nextval('manufacturing_facilities_id_seq'::regclass)
 tenant_id               | integer                  | not null |
 real_estate_unit_id     | integer                  |          |
 name                    | character varying(255)   | not null |
 facility_type           | facilitytype             | not null |
 manager_id              | bigint                   | not null |
 safety_compliance_score | numeric(5,2)             |          |
 is_active               | boolean                  |          |
 created_at ... deleted_at ... is_deleted
 site_id                 | integer                  | not null |
Foreign-key constraints:
    "manufacturing_facilities_manager_id_fkey" FOREIGN KEY (manager_id) REFERENCES users(id)
    "manufacturing_facilities_real_estate_unit_id_fkey" FOREIGN KEY (real_estate_unit_id) REFERENCES property_units(id)
    "manufacturing_facilities_site_id_fkey" FOREIGN KEY (site_id) REFERENCES sites(id)
    "manufacturing_facilities_tenant_id_fkey" FOREIGN KEY (tenant_id) REFERENCES academy_tenants(id)
```

**تأكيد:** ✅ `entity_id`/`location_gps` غائبان تمامًا. ✅ `site_id NOT NULL`
+ FK حقيقي لـ`sites.id`. ✅ `real_estate_unit_id` بلا لمس (لسه FK لـ`property_units.id`
كما كان). ✅ `production_lines`/`product_blueprints` بلا أي تعديل بنيوي —
لسه بيشاورا `facility_id` عادي.

---

## 4. تأكيد تسجيل `app.domains.sites` — لسه شغّال، صفر إعادة حل مطلوبة

```
python -c "import app.main; from app.domains.sites.models import Site; print('sites OK:', Site.__tablename__)"
```
```
sites OK: sites
[exited with code 0]
```

الحل المُطبَّق في دومين iot (`app/domains/sites/router.py` + تسجيله في
`main.py`) **لسه سليم وشغّال بلا أي تعديل إضافي** — كما هو متوقَّع (حل
مركزي مرة واحدة، صالح لكل الدومينات الجاية).

---

## 5. تحقق pytest — ثلاث محاولات، محاولتان `killed` بسبب الذاكرة (موثَّق صراحةً)

```
PYTHONIOENCODING=utf-8 ./venv/Scripts/python.exe -m pytest \
  --ignore=tests/test_affiliate_service_missing_methods.py -q
```

### المحاولة 1 — `killed`
توقفت عند ~65% تقدّم بسبب نقص ذاكرة النظام (`vmmem`/Docker لوحده ~2GB +
عمليات claude متراكمة من جلسات سابقة). ظهر مؤشر فشل واحد (`F`) قبل
التوقف، بلا اسم واضح (وضع `-q` بلا تفاصيل وسط التشغيل).

### المحاولة 2 — `killed` أيضًا
أُعيدت المحاولة فورًا. توقفت هذه المرة عند ~95% تقدّم (تقدّم أكبر من
المحاولة الأولى). **ظهرت 3 مؤشرات فشل (`F`) في مواضع مختلفة عن المحاولة
الأولى** — التناقض في المواضع بين المحاولتين (لا نفس الاختبارات فشلت في
نفس المكان) هو الدليل الأول على إن هذه الفشول **آثار جانبية لضغط الذاكرة
نفسه** (احتمال انقطاع اتصال DB/Redis مؤقت تحت الضغط)، **لا فشل كود
حقيقي وحتمي** — تأكَّد ده بشكل قاطع بالمحاولة 3.

### المحاولة 3 — ✅ نجحت بالكامل، **أسرع من baseline المرجعي**

```
13 failed, 225 passed, 2 xfailed, 287 warnings in 722.74s (0:12:02)
```

**12 دقيقة فقط** — أسرع بكثير من الـ~76 دقيقة المرجعية لدومين iot (على
الأغلب نتيجة تراجع ضغط الذاكرة بعد انتهاء المحاولتين السابقتين، لا أي
تغيير في حجم الاختبارات نفسها).

**مقارنة الأسماء بالحرف مع baseline:**

جميع الـ13 اسم فشل **مطابقون حرفيًا** لنفس قائمة baseline المستخدَمة في
تقرير دومين iot (`test_realestate_insurance_savepoint.py` ×1,
`test_user_repository_get_by_id_audit.py` ×10,
`test_user_repository_get_user_audit.py` ×2) — **صفر اسم فشل جديد، صفر
اسم غائب.** هذا يؤكد رجعيًا إن الفشول المؤقتة في المحاولتين 1-2 كانت
فعليًا آثار ذاكرة، لا مشكلة حقيقية في تعديلات manufacturing.

---

## الحالة الحالية — ✅ دومين manufacturing مكتمل ومُتحقَّق منه بالكامل

- ✅ استبدال كامل `entity_id`/`location_gps` → `site_id NOT NULL`،
  `real_estate_unit_id`/`ProductionLine` بلا لمس.
- ✅ سلسلة حذف كاملة موثَّقة بالتفصيل (5 صفوف، 4 جداول، كلها throwaway
  مؤكَّدة) — صفر إعادة إدراج، العدد صفر في كل الجداول الستة المفحوصة.
- ✅ تسجيل `app.domains.sites` تأكَّد إنه لسه شغّال بلا أي مشكلة.
- ✅ pytest: `13 failed, 225 passed, 2 xfailed` — **مطابقة حرفية 100%**
  بعد محاولتين `killed` بسبب ذاكرة النظام (موثَّقتين بالتفصيل أعلاه) ونجاح
  كامل في المحاولة الثالثة (12 دقيقة).
- ⏸️ **بانتظار موافقتك الصريحة قبل الانتقال لدومين agritech**
  (`SmartFarm` — إضافة `site_id` فقط، مش استبدال؛ `land_asset_id` بلا لمس).
