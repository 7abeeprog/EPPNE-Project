# مستند تصميم معماري: Site موحّد عابر للقطاعات + كاميرات academy

**نوع الجلسة:** تصميم واقتراحات فقط. **صفر migration فعلي، صفر كود إنتاجي،
صفر تعديل على أي دومين موجود.** كل ما هنا مقترح للمناقشة والموافقة —
مفيش أي جزء يُنفَّذ إلا بعد موافقة صريحة منك على كل بند بالتحديد.

**التاريخ:** 2026-09-17

---

## 0. تحقق أول (إلزامي) — النتيجة

تم فحص الجداول الأربعة + جدول الكاميرا + جدول الـtenants مباشرة على قاعدة
البيانات الشغالة (`eppne_db`, منفذ 5435, نفس `DATABASE_URL` المستخدَم في
التطبيق):

| الجدول | عدد الصفوف | المحتوى |
|---|---|---|
| `smart_assets` | 1 | `asset_code = "P-CTOR-IOT-ASSET-1"` — نمط تسمية اختبار constructor واضح |
| `production_lines` | 1 | `name = "P-CTOR-MFG-LINE"` — نفس النمط |
| `manufacturing_facilities` | 2 | `"P-CTOR-MFG-FACILITY"` و `"MANUFACTURING-CANACCESS-PILOT-TENANT16"` — كلاهما بيانات اختبار/pilot |
| `smart_farms` | 1 | `name = "REGTEST-FARM-6c2f532e34"` — نمط اختبار regression واضح |
| `health_facilities` | 1 | `name = "p_ctor_health_facility"` — نفس نمط constructor |
| `classroom_camera_analyses` | 0 | فاضي تمامًا |
| `academy_tenants` | 3 | `"Local Test Tenant"` (domain=`test.local`), `"نبت"` (domain=`localhost.com`), `"TEST_TENANT_B"` — كل الـ3 عليهم علامات بيئة تطوير/اختبار (domain محلي أو اسم صريح TEST) |

**الخلاصة: كل الصفوف الموجودة اليوم بيانات throwaway/test/pilot واضحة
100%، صفر أي إشارة لبيانات إنتاج حقيقية.** لا يوجد أي صف مشكوك فيه
يستوجب التوقف — أمِنّا للمتابعة في التصميم مباشرة.

---

## 1. تصميم `Site` الموحّد (مقترح)

### 1.1 التشتت الحالي — ليه لازم موديل واحد

فحصت الأربعة دومينات المذكورة، وكل واحد منهم بشكل مختلف تمامًا عن التاني
لنفس المفهوم ("فين الحاجة دي فعليًا؟"):

| الدومين | الموديل الحامل للموقع | آلية الموقع | `entity_id` مربوط بـFK حقيقي؟ |
|---|---|---|---|
| `iot` | `SmartAsset` | `location_gps` (JSONB خام، بلا بنية) | ❌ لا — `Integer` عادي بلا `ForeignKey` |
| `manufacturing` | `ManufacturingFacility` (**مش** `ProductionLine` — دي طفل يشاور على `facility_id`) | `location_gps` (JSONB) + `real_estate_unit_id → property_units.id` | ❌ لا |
| `agritech` | `SmartFarm` | **صفر** `location_gps` — الموقع ضمنيًا عبر `land_asset_id → land_assets.id` فقط | ❌ لا (العمود مش موجود حتى بشكل صريح كـFK) |
| `health` | `HealthFacility` | **صفر موقع جغرافي إطلاقًا** — لا `location_gps` ولا FK لجدول real-estate | ✅ **نعم** — `entity_id → sovereign_entities_v2.id ON DELETE SET NULL` (migration 052) |

أربع طرق مختلفة تمامًا لتمثيل "فين الحاجة دي" و"مين المسؤول عنها"، وكل
واحدة اتبنت مستقلة عن التانية. ده تحديدًا سبب الحاجة لـ`Site` موحّد.

### 1.2 اكتشاف جوهري أثناء الفحص: **يوجد جدولان "entity" مختلفان بالفعل بالمشروع**

قبل تصميم `entity_id` على `Site`، لازم توضيح ده لأنه يغيّر القرار:

- **`organization_entities`** (دومين `academy`) — شجرة تنظيمية هرمية
  (`parent_id` self-referential) داخل tenant واحد، للفروع/الأقسام.
  `id, tenant_id, parent_id, name, entity_type, description, is_active`.
- **`sovereign_entities_v2`** (دومين `sovereign_entities`) — كيان قانوني
  كامل (شركة/مؤسسة) بحقول KYB كاملة: `legal_name, registration_number,
  tax_id, country_of_origin, city, address, kyb_status, verified_by...`.

هذان جدولان مختلفان تمامًا في الغرض (شجرة تنظيمية داخلية vs كيان قانوني
مُوثَّق). `health_facilities.entity_id` بيربط بالجدول التاني
(`sovereign_entities_v2`) عبر FK حقيقي — **لكن ده استثناء، مش القاعدة**.
القاعدة الفعلية المُتبنّاة عمدًا في `app/core/models.py` (`EntityMembership`)
هي **زوج polymorphic**: `entity_type: String(50)` + `entity_id: Integer`
**بلا** FK قاعدة بيانات صريح — والتعليق في الكود نفسه يوضح السبب:

```python
class EntityMembershipRole(str, enum.Enum):
    """منفصل عمدًا عن sovereign_entities.EntityRole رغم تطابق القيم —
    core لا يستورد من أي دومين وظيفي (entity-membership-technical-design.md §2)."""
```

يعني: `core` (والموديلات المشتركة المبنية على نفس الفلسفة) **متعمَّد
تجنُّب الاعتماد على جدول entity واحد بعينه**، لصالح مرونة "أي دومين
entity مستقبلي يقدر ينضم بدون تعديل الموديل المشترك".

**قراري المقترح لـ`Site.entity_id`:** اتّباع نمط `EntityMembership`
(`entity_type` + `entity_id` بلا FK صريح) **وليس** تقليد استثناء
`health_facilities` (FK صريح لـ`sovereign_entities_v2`). السبب: هذا هو
النمط المعماري المُقرَّر بالفعل في المشروع لهذا الغرض تحديدًا، وتفعيل FK
حقيقي هيقفل `Site` على جدول entity واحد بينما رؤية المدينة الذكية عايزة
مرونة عبر قطاعات (نادي، سياحة) ممكن يكون عندها جدول entity مختلف تمامًا
مستقبلًا. **هذا يعني أننا لن نلمس `health_facilities.entity_id` الحالي
إطلاقًا** (تفصيل كامل في §1.4).

### 1.3 الحقول المقترحة (توضيحي — ليس migration فعلي)

```python
# مقترح توضيحي فقط — app/domains/sites/models.py (دومين جديد مستقل)

class SiteType(str, enum.Enum):
    """قابلة للتوسع — انظر §1.3.1 لسبب اختيار native_enum=False"""
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

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    parent_site_id = Column(Integer, ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True)
    site_type = Column(SQLEnum(SiteType, native_enum=False, length=50), nullable=False, index=True)

    # زوج polymorphic بدل FK صريح لجدول entity واحد — راجع §1.2
    entity_type = Column(String(50), nullable=True, index=True)
    entity_id = Column(Integer, nullable=True, index=True)

    name = Column(String(255), nullable=False)

    latitude = Column(Numeric(9, 6), nullable=True)
    longitude = Column(Numeric(9, 6), nullable=True)
    address_text = Column(String(500), nullable=True)
    geo_metadata = Column(JSONB, default=dict)  # ارتفاع/دقة/ملاحظات حرة

    manager_id = Column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)

    # حقل محجوز فقط — بلا أي منطق فرض فعلي في هذه المرحلة (يطابق نمط
    # academy_tenants.branding المكتشف في جلسة الاستكشاف السابقة)
    data_residency_preference = Column(String(50), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_site_tenant_type", "tenant_id", "site_type"),
        Index("ix_site_parent", "parent_site_id"),
        Index("ix_site_entity", "entity_type", "entity_id"),
    )
```

#### 1.3.1 نقطة تقنية لازم توضيحها: `site_type` — `native_enum=False`

طلبت enum "قابل للتوسع". لو استخدمنا `SQLEnum` عادي (`native_enum=True`,
الافتراضي)، بيُنشئ **نوع ENUM حقيقي في Postgres** — وإضافة قيمة جديدة
(زي `NURSERY` مستقبلًا) بتحتاج `ALTER TYPE ... ADD VALUE` migration في كل
مرة، وده عكس "قابل للتوسع". الحل المقترح: `native_enum=False` — بيخزّن
كـ`VARCHAR` عادي مع تحقق على مستوى Python فقط. **المقايضة:** بنفقد
حماية قاعدة البيانات من قيمة غلط تتكتب مباشرة (SQL خام)، لكن نكسب إضافة
`site_type` جديد بصفر migration. أراه مقايضة مقبولة لأن كل الكتابة تمر
عبر service layer بالفعل في هذا المشروع (لا يوجد insert مباشر بالكود
الحالي).

### 1.4 استراتيجية الربط بالدومينات الأربعة — استبدال كامل أم إضافة جنب القديم؟

**اقتراحي: استبدال كامل لدورَي `location_gps` و`entity_id` في iot/
manufacturing/agritech (زيرو استخدام حقيقي عليهم اليوم بحسب §0)، لكن
health_facilities استثناء — إضافة فقط، بلا لمس `entity_id` الموجود.**

| الدومين | هيتغيّر بالتحديد | السبب |
|---|---|---|
| `iot.SmartAsset` | حذف `location_gps` + دور `entity_id` القديم → إضافة `site_id NOT NULL` (FK `sites.id`) | صفر بيانات حقيقية (صف واحد اختباري)، `entity_id` لم يكن مربوطًا بأي FK من الأساس — استبدال بلا أي كسر |
| `manufacturing.ManufacturingFacility` | حذف `location_gps` + دور `entity_id` القديم → إضافة `site_id NOT NULL`. **`real_estate_unit_id` يبقى كما هو، بلا لمس** | `real_estate_unit_id` يمثّل سؤال مختلف تمامًا ("هذا المصنع مبني على أي عقار مملوك/مؤجَّر؟") — دمجه مع "فين الموقع فعليًا لأغراض IoT/كاميرا" خلط بين اهتمامين مختلفين. `ProductionLine` نفسه (الطفل) غير مُتأثِّر — لسه بيشاور `facility_id`، والـfacility هو اللي حامل `site_id` الجديد |
| `agritech.SmartFarm` | إضافة `site_id` (مش استبدال — الموقع الجغرافي المباشر لم يكن موجودًا أصلًا هنا، كان ضمنيًا فقط عبر `land_asset_id`). **`land_asset_id` يبقى كما هو** | نفس منطق `real_estate_unit_id` أعلاه — "على أي أرض مسجَّلة" سؤال مختلف عن "فين الموقع فعليًا لأجهزة الاستشعار/الكاميرات" |
| `health.HealthFacility` | **إضافة `site_id` فقط، بلا حذف `entity_id` الحالي** | `entity_id → sovereign_entities_v2` هنا FK حقيقي مُنجَز بالفعل عبر migration 052 (جزء من مجهود hardening حديث للدومين — راجع الذاكرة: health entity-membership implementation CLOSED). التراجع عنه = فتح مجهود مُغلَق بدون سبب متعلق بالكاميرات/IoT. `site_id` هنا سيحمل فقط الموقع الجغرافي الفعلي (المُنشأة أصلًا صفر موقع جغرافي عندها) — إضافة صافية بلا تعارض |

**لماذا استبدال كامل بدل مرحلة انتقالية (نفس القديم + الجديد جنب بعض)
لثلاثة دومينات، وإضافة فقط في الرابع؟**

1. **صفر بيانات حقيقية = صفر تكلفة/خطر migration الآن** (§0) — هذه
   النافذة مؤقتة، تنعدم بمجرد دخول أول tenant حقيقي بالإنتاج.
2. **الاحتفاظ بحقلين متوازيين لنفس المعنى لمرحلة طويلة = مصدر حقيقة
   مزدوج**، وهذا النمط بالذات هو سبب معظم الـbugs المُكتشَفة في جلسات
   سابقة بهذا المشروع (drift بين مصدرين للحقيقة عبر عشرات الـbacklog
   items المسجَّلة). لا داعي لتكرار النمط ده وإحنا لسه في مرحلة بناء.
3. **خطط "مرحلة انتقالية، هنكمّل لاحقًا" في هذا المشروع تحديدًا نادرًا ما
   تُستكمَل فعليًا في الوقت المحدَّد** (عدة تقارير `-planning` بلا
   `-implementation` مقابل موجودة بالفعل بالمشروع) — استبدال كامل فورًا
   (لما التكلفة صفر) أضمن من الاعتماد على مرحلة تنظيف مستقبلية.

### 1.5 كيف يصلح `Site` لقطاعات معندهاش دومين أصلًا (نادي/سياحة)؟

`Site` لا يحتوي **أي** FK لجدول دومين مُحدَّد (لا `manufacturing_facilities`
ولا `smart_farms` ولا غيره) — العلاقة اتجاه واحد فقط: **الدومين هو اللي
يشاور على `Site`، مش العكس**. فأي قطاع جديد مستقبلًا (مثلًا `SportsClub`
في `tourism_sports`) بس يضيف عمود `site_id → sites.id` في موديله الخاص
من أول يوم — **صفر تعديل على `Site` نفسه**. الهرمية (`parent_site_id`)
والموقع (lat/lng) وربط الجهة القانونية (`entity_type`/`entity_id`)
كلهم مفاهيم عامة بما يكفي لأي قطاع فعليًا.

**قيد معروف غير محلول بهذا التصميم (أُفضِّل الإفادة به صراحة بدل
تجاهله):** `Site` مُصمَّم لموقع **ثابت** (نقطة GPS واحدة لكل صف). قطاع
مستقبلي فيه "موقع متحرك" (سفينة، عيادة متنقلة، أسطول نقل نفسه) هيحتاج
تصميم منفصل (سجل تتبع زمني، مش صف Site ثابت) — خارج نطاق هذا المستند.

---

## 2. كاميرات `academy` فوق `Site` الجديد

### 2.1 `ClassroomCameraAnalysis` — تعديل ولا حقل إضافي؟

الموديل الحالي (`academy/models.py:487-508`) **صفر حقل موقع من الأساس**
— بيشاور فقط على `org_entity_id → organization_entities.id` (نطاق
تنظيمي/صلاحيات، فرع المدرسة) و`session_id → live_sessions.id` (الحصة).

**اقتراحي: إضافة `site_id` (FK `sites.id`, `nullable=True` مبدئيًا)،
بدون لمس `org_entity_id`.** هذه ليست حالة "استبدال" مثل §1.4 — لا يوجد
حقل قديم يتعارض، فالإضافة هنا صافية. لماذا `nullable` هنا تحديدًا (بعكس
اقتراح §1.4 بجعل `site_id` إجباري في iot/manufacturing/agritech)؟ لأن
academy لسه معندها **صفر صفوف `Site` فعلية** (لا يوجد حتى مفهوم "حرم
جامعي"/"فصل" ككيان — يحتاج بناء شجرة `Site` كاملة للمدرسة أولًا قبل ما
أي كاميرا تقدر تشاور عليها إجباريًا). أقترح `nullable` مؤقتًا حتى تُبنى
شجرة Site الأكاديمية، ثم `NOT NULL` بعد ذلك — **قرار توقيت ده يحتاج
موافقتك أيضًا، مش حتمي.**

`org_entity_id` يبقى كما هو — نطاق صلاحيات/tenant-scoping غير متعلق
بالموقع الجغرافي الفعلي.

### 2.2 أول endpoint — اقتراحي: **الاستقبال (ingestion) قبل الاستعلام**

**سبب واضح ومباشر:** الجدول فاضي تمامًا (0 صف، §0) — بناء endpoint
استعلام (`GET`) الآن بيرجّع فاضي دايمًا، صفر قيمة للتحقق منه. الاستقبال
هو الوحيد اللي بيولّد بيانات حقيقية للاختبار عليها.

**اكتشاف حرج أثناء الفحص لازم يُحسم قبل بناء أي endpoint استقبال:**
**لا يوجد أي آلية مصادقة للأجهزة (device auth) في المشروع كله.** فحصت
`app/api/deps.py` بالكامل — الاعتماد الوحيد المتاح هو `get_current_active_user`
(JWT بشري عادي). حتى endpoint الاستقبال الموجود فعليًا في `iot`
(`POST /iot/readings`) بيفترض **مستخدم بشري مسجَّل دخول** هو مصدر
القراءة (تقني بيدخل يدويًا يقرأ عداد مثلًا)، وليس جهاز مستقل بيبعت
تلقائيًا. الحقول `hardware_did`/`iot_wallet_address` على `SmartAsset`
موجودة كـmetadata وصفية فقط — **صفر استخدام فعلي منهم في أي منطق
مصادقة بالكود الحالي**.

يعني: **قبل ما نبني endpoint استقبال حقيقي لكاميرا hardware**، لازم قرار
منفصل عن "إزاي الكاميرا نفسها تتوثّق مع الـbackend" (API key لكل جهاز؟
mutual TLS؟ service account مستخدم نظام؟) — هذا خارج نطاق هذا المستند
التصميمي (مستند الـSite/الكاميرا)، لكنه **مانع تنفيذي حقيقي** يجب حسمه
كخطوة صفر من أي عمل تنفيذي فعلي على endpoint الاستقبال.

### 2.3 ترجمة opt-out لمنع الالتقاط الفعلي وقت التسجيل — المشكلة المعمارية الحقيقية

هذا أهم جزء في المستند لأن **الآلية الموجودة حاليًا (`GuardianVisibilitySetting`)
لا تحل المطلوب على الإطلاق، وده لازم يكون واضح قبل أي بناء.**

**ما تم التأكد منه بقراءة `guardian/service.py` كاملة:** `is_visible`
على `GuardianVisibilitySetting` **يُقرأ فقط داخل تجميع استجابة
`GET /guardian/wards/{id}/overview`** (`hidden_sectors` تُستخدَم لاستبعاد
قسم من الـresponse). **صفر أي قراءة له في أي مسار كتابة/استقبال بيانات
بالمشروع كله.** بمعنى آخر: هذه الآلية تحجب **العرض فقط**، والبيانات
لسه بتُسجَّل وتُخزَّن بالكامل بغض النظر عن قيمة `is_visible` — عكس
المطلوب صراحةً في طلبك ("منع التسجيل الفعلي وقت الالتقاط، مش بس وقت
العرض").

**سبب تصميمي إضافي ليه `GuardianVisibilitySetting` مش المكان الصحيح
لهذا القرار حتى لو غيّرنا وقت قراءته:**

1. **مستوى الحبيبية غلط.** `GuardianVisibilitySector` enum الحالي
   (`ACADEMY, SOCIAL, TRANSPORT, HEALTH`) — تعطيل قطاع `ACADEMY` بالكامل
   يحجب/يمنع **كل** بيانات academy (درجات، حضور، كاميرا، كل شيء)، وليس
   "تسجيل الكاميرا فقط" تحديدًا. المطلوب سؤال أضيق كتير من مستوى القطاع.
2. **الجهة الخاطئة.** الإعداد مرتبط بـ`guardian_relationship_id` (أي
   **علاقة ولي أمر↔طالب واحدة بعينها**)، لا بالطالب نفسه. طالب عنده أب
   وأم (علاقتان)، لو الأب فعّل `is_visible=False` والأم لأ — مين قرار
   الالتقاط الفعلي بيتحدد بيه؟ التصميم الحالي مالوش إجابة لهذا التعارض
   لأنه مصمَّم لسؤال "ماذا يرى **هذا** الولي" مش "هل الطفل نفسه موافَق
   على تسجيله بيولوجيًا/بصريًا بالكامل".

**اقتراحي: علم موافقة جديد ومنفصل، على مستوى الطالب (الـward) نفسه، لا
على مستوى علاقة ولي أمر واحدة، ولا على مستوى قطاع عريض:**

```python
# مقترح توضيحي فقط — دومين جديد صغير، مثلًا app/domains/consent/models.py

class ConsentType(str, enum.Enum):
    CLASSROOM_CAMERA_ANALYTICS = "CLASSROOM_CAMERA_ANALYTICS"
    # قابل للتوسع لاحقًا لأنواع بيانات حساسة أخرى

class WardConsentSetting(Base):
    __tablename__ = "ward_consent_settings"
    __table_args__ = (
        UniqueConstraint("ward_user_id", "consent_type", name="uq_ward_consent_type"),
    )
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), nullable=False)
    ward_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type = Column(SQLEnum(ConsentType, native_enum=False, length=50), nullable=False)

    # الافتراضي "نظام opt-out" — المشاركة مفعّلة بشكل افتراضي (False)،
    # وأي ولي أمر (من أي علاقة verified) يقدر يحوّلها True = رفض صريح
    is_opted_out = Column(Boolean, nullable=False, default=False)

    set_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    set_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**كيف يُفرَض فعليًا وقت الالتقاط (لا وقت العرض)؟** endpoint/service
الاستقبال (§2.2) — **قبل** أي `INSERT` في `classroom_camera_analyses` —
يستعلم `WardConsentSetting` للطالب/الطلاب المُحدَّدين في الفريم، ولو
`is_opted_out=True`:
- `active_speaker_id` (الحقل الوحيد اللي بيحدد هوية طالب معيّن بشكل
  مباشر) → يُخزَّن `NULL` له، لا يُخزَّن أصلًا.
- أي بيانات هوية داخل `emotions_summary`/`raw_analysis_log` خاصة بهذا
  الطالب بالتحديد → تُستبعَد/تُنقَّى **قبل الكتابة**، لا بعدها.

**مشكلة تقنية حقيقية غير محلولة بهذا المستند — تحتاج قرارك:**
`attention_score`/`detected_faces_count` غالبًا قيم **مُجمَّعة على
مستوى الفصل كله** (عدد وجوه مكتشَفة، متوسط انتباه)، وليست مرتبطة بهوية
طالب واحد. هل هذه القيم تُعتبر "بيانات شخصية للطفل المرفوض" وتستوجب
استبعاد الفصل كله من التسجيل لو فيه طالب واحد رافض؟ أم تُعتبر "بيانات
مُجمَّعة غير قابلة لعزو فردي" ويسمح بتسجيلها دايمًا؟ **هذا قرار
منتجي/قانوني لازم تحسمه أنت، مش تقني** — مذكور هنا كنقطة صريحة تحتاج
قرارك، بجانب سؤال الاحتفاظ في §3.

---

## 3. سؤال صريح يحتاج قرارك — مدة الاحتفاظ بالبيانات (Retention)

**لم أجد أي نمط retention موجود بالفعل في المشروع** (بحثت في دومين
`privacy` بالكامل عن `retention/ttl_days/data_retention` — صفر
مطابقة). هذا قرار جديد بالكامل، وأنا **لن أقرره بنفسي** — ثلاثة خيارات
بمقايضاتهم:

### خيار أ — احتفاظ قصير (30–90 يومًا للبيانات الخام)
- ✅ أقل تكلفة تخزين، أقل خطر قانوني بشكل واضح (بيانات بصرية/بيومترية
  لقاصرين لفترة محدودة جدًا).
- ❌ يفقد القدرة على تحليل اتجاه طويل المدى (مثلًا "تطور انتباه الطالب
  على مدار الفصل الدراسي") **إلا لو حُسبت مؤشرات مُجمَّعة (aggregates)
  بشكل منفصل وتُحفظ هي لمدة أطول بدل الخام** — وهذا يحتاج بناء طبقة
  تجميع/ملخصات، غير موجودة اليوم.

### خيار ب — احتفاظ متوسط (سنة دراسية واحدة، ثم حذف/أرشفة بارد)
- ✅ توازن معقول: تحليل اتجاه على مدار سنة كاملة، مع سقف زمني واضح
  للتعرّض القانوني.
- ❌ يحتاج **مهمة حذف مجدولة فعلية** (Celery task جديد بالكامل — صفر
  مهمة مشابهة موجودة اليوم في المشروع للحذف الدوري لبيانات حساسة)،
  وقرار "أرشفة بارد" لو مطلوب يحتاج بنية تخزين إضافية (مثلًا نقل لـMinIO
  بصيغة مضغوطة بدل حذف تام).

### خيار جـ — احتفاظ طويل/مرتبط بمدة تسجيل الطالب في المدرسة
- ✅ أعلى قيمة تحليلية (سجل تعليمي/سلوكي كامل عبر سنوات الدراسة، مفيد
  فعليًا لمدارس عايزة تاريخ طويل).
- ❌ أعلى خطر قانوني/سمعي بوضوح — الاحتفاظ لسنوات ببيانات بصرية/بيومترية
  لقاصرين، خصوصًا مع **صفر بنية data residency/multi-region فعلية
  اليوم** (تأكَّدنا من ده في جلسة الاستكشاف السابقة — لا يوجد أي ضمان
  حاليًا لمكان تخزين البيانات جغرافيًا). لو قانون حماية بيانات (محلي أو
  دولي حسب الأسواق المستهدَفة) فرض سقف احتفاظ أقصر مستقبلًا، هذا الخيار
  يحتاج بناء مهمة حذف تحت ضغط وقت لاحقًا، عكس البناء المُخطَّط له من
  الأول في الخيار ب.

**محتاج قرارك: أ، ب، جـ، أم مزيج (مثلًا خام قصير + مُجمَّعات طويلة)؟**

---

## ملخص نقاط تحتاج موافقتك الصريحة قبل أي تنفيذ

1. **`Site` model الجديد** — الحقول المقترحة في §1.3، وتحديدًا: `entity_type`+`entity_id`
   polymorphic بدل FK صريح (§1.2)، و`native_enum=False` لـ`site_type` (§1.3.1).
2. **استراتيجية الاستبدال المتفاوتة**: استبدال كامل في iot/manufacturing/agritech،
   إضافة فقط في health (§1.4) — وتوقيت `NOT NULL` لكل حالة.
3. **`ClassroomCameraAnalysis.site_id`**: إضافة `nullable` مؤقتًا لحد بناء شجرة Site
   الأكاديمية (§2.1) — وتوقيت التحويل لـ`NOT NULL`.
4. **أولوية البناء**: endpoint استقبال قبل استعلام (§2.2) — مع الإقرار بأن **مصادقة
   الجهاز (device auth) مانع منفصل يحتاج حسم قبل أي كود فعلي** لهذا الـendpoint.
5. **`WardConsentSetting` الجديد** بديل `GuardianVisibilitySetting` لسؤال "التسجيل"
   (§2.3) — وتحديدًا: هل `attention_score`/`detected_faces_count` المُجمَّعة تُعتبر
   بيانات شخصية تستوجب استبعاد الفصل كله لو فيه طالب رافض واحد؟
6. **مدة الاحتفاظ بالبيانات** (§3) — أ/ب/جـ/مزيج، قرارك بالكامل.

**صفر من هذه النقاط تم تنفيذه أو حتى كتابة migration فعلي لها — كل ما
سبق مستند اقتراحي بانتظار ردّك بندًا ببند.**
