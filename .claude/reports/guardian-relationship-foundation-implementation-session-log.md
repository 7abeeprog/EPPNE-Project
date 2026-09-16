# علاقة ولي أمر↔طالب — جلسة تنفيذ الأساس (Migration + Models + Schemas)

**تاريخ:** 2026-09-16
**النطاق:** بناء الأساس فقط — migration جديدة + دومين `app/domains/guardian/`
جديد بالكامل (models + schemas + repository). **صفر endpoint، صفر service،
صفر منطق تدفق (طلب/موافقة/رفض/تحقق إداري/تنبيهات)** — هذا كله مرحلة
تانية بموافقة صريحة منفصلة، حسب طلب المستخدم بالحرف.
امتدادًا لـ [[project_guardian_relationship_design_planning]] و
[[project_birth_date_null_percentage_check]].

---

## 1. Migration 056 (`056_create_guardian_relationship_tables.py`)

`down_revision = '055_entertainment_venues_entity_id_fk_set_null'` (تأكَّد
DB الديف كانت فعليًا على `055` قبل التطبيق، عبر `SELECT version_num FROM
alembic_version`).

جدولان جدد بالكامل — **صفر لمس على أي جدول قائم**:

### `guardian_relationships`

```python
op.create_table(
    'guardian_relationships',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tenant_id', sa.Integer(), nullable=False),
    sa.Column('guardian_user_id', sa.Integer(), nullable=False),
    sa.Column('ward_user_id', sa.Integer(), nullable=False),
    sa.Column('relationship_type', relationship_type_enum, nullable=False),
    sa.Column('status', relationship_status_enum, nullable=False, server_default='PENDING_WARD_APPROVAL'),
    sa.Column('initiated_by_user_id', sa.Integer(), nullable=False),
    sa.Column('ward_birth_date_provided', sa.Date(), nullable=True),
    sa.Column('verified_by', sa.Integer(), nullable=True),
    sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('rejection_reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['guardian_user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['ward_user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['initiated_by_user_id'], ['users.id']),
    sa.ForeignKeyConstraint(['verified_by'], ['users.id']),
    sa.UniqueConstraint('guardian_user_id', 'ward_user_id', name='uq_guardian_ward'),
)
```

- `relationship_type` enum: `FATHER/MOTHER/GUARDIAN`.
- `status` enum: `PENDING_WARD_APPROVAL/PENDING_ADMIN_REVIEW/VERIFIED/
  REJECTED`، افتراضي `PENDING_WARD_APPROVAL` (`server_default`، مش قيمة
  تطبيقية بس — تتفرض حتى لو أي INSERT مباشر عبر SQL خام).
- `ward_birth_date_provided`: **منفصل عمدًا** عن `users.birth_date`
  القديمة — راجع [[project_birth_date_null_percentage_check]] (99.16%
  NULL على الإنتاج). القيمة هنا هتُملأ صراحةً وقت طلب/موافقة الربط في
  المرحلة القادمة، مش معتمدة على البيانات القديمة الناقصة.
- `verified_by`/`verified_at`/`rejection_reason`: نفس الشكل بالحرف
  المُقتبَس من `SovereignEntity.kyb_status`/`EntityDocument.status`
  (راجع [[project_guardian_relationship_design_planning]] §3).
- `guardian_user_id`/`ward_user_id`: `ON DELETE CASCADE` (الصف بلا معنى
  لو أي طرف اتحذف — نفس نمط `UserAchievement.user_id` في achievements).
  `initiated_by_user_id`/`verified_by`: بلا `ondelete` صريح (نفس نمط
  `created_by`/`verified_by` في `AchievementDefinition`/
  `SovereignEntity` — إسناد تدقيقي، مش طرف أساسي في العلاقة).

### `guardian_visibility_settings`

```python
op.create_table(
    'guardian_visibility_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('guardian_relationship_id', sa.Integer(), nullable=False),
    sa.Column('sector', visibility_sector_enum, nullable=False),
    sa.Column('is_visible', sa.Boolean(), nullable=False, server_default='true'),
    sa.PrimaryKeyConstraint('id'),
    sa.ForeignKeyConstraint(['guardian_relationship_id'], ['guardian_relationships.id'], ondelete='CASCADE'),
    sa.UniqueConstraint('guardian_relationship_id', 'sector', name='uq_guardian_visibility_relationship_sector'),
)
```

- `sector` enum: `ACADEMY/SOCIAL/TRANSPORT/HEALTH`.
- `guardian_relationship_id`: `ON DELETE CASCADE` (إعدادات الرؤية بلا
  معنى بدون العلاقة الأصلية).

### التطبيق الفعلي

اتطبَّقت عبر `venv/Scripts/alembic.exe upgrade head` (استخدام الـvenv
المحلي — `alembic` غير مثبَّت على Python النظام). نجحت من `055` لـ`056`
بلا أخطاء:

```
INFO  [alembic.runtime.migration] Running upgrade 055_entertainment_venues_entity_id_fk_set_null -> 056_create_guardian_relationship_tables
✅ [Alembic] Connecting to database at: postgresql+asyncpg://eppne:***REDACTED***@127.0.0.1:5435/eppne_v2
```

**تحقق مباشر بعدها عبر `psql \d`** على الجدولين — كل الأعمدة، الفهارس،
الـFKs، والقيود الفريدة مطابقة تمامًا للمطلوب (تفاصيل كاملة في قسم
الاختبار تحت).

---

## 2. `app/domains/guardian/` — الدومين الجديد

نفس هيكل أي دومين موجود (زي `achievements`): `__init__.py` فارغ،
`models.py`، `schemas.py`، `repository.py`. **لا `service.py` ولا
`router.py`** — بالحرف حسب نطاق الجلسة (بلا endpoint/منطق تدفق).
**صفر تعديل على `main.py`** — لا يوجد router يُسجَّل.

### `models.py`

3 enums (`GuardianRelationshipType`, `GuardianRelationshipStatus`,
`GuardianVisibilitySector`) + موديلين (`GuardianRelationship`,
`GuardianVisibilitySetting`) مطابقين تمامًا لبنية الـmigration، بنفس
نمط تعليقات `achievements/models.py` (توضيح إن الحالة الافتراضية مجرد
تخزين، صفر منطق تدفق يقرأها بعد).

### `schemas.py`

`GuardianRelationshipCreate`/`GuardianRelationshipResponse`،
`GuardianVisibilitySettingCreate`/`GuardianVisibilitySettingResponse` —
Pydantic عادي، `model_config = ConfigDict(from_attributes=True)` على
الـResponse، نفس نمط `achievements/schemas.py` بالحرف. **موجودة لكن
غير مستخدَمة بعد من أي service/router** (زي ما كانت `VenueCreate`/
`VenueResponse` يتيمة قبل جلسة entertainment-venue).

### `repository.py`

`GuardianRepository` — 5 دوال فقط، الحد الأدنى المطلوب للاختبار الحي:
`create_relationship`, `get_relationship`,
`get_relationship_by_guardian_and_ward`, `create_visibility_setting`,
`list_visibility_settings`. صفر منطق فوق CRUD خام (`flush` + `refresh`،
مفيش `commit` داخل الـrepo نفسه — نفس نمط `achievements/repository.py`
اللي بيسيب الـcommit لطبقة الـservice، غير الموجودة هنا بعد عمدًا).

---

## 3. الاختبار الحي

`tests/test_guardian_relationship_foundation_implementation.py` — 3
سيناريوهات، عبر `GuardianRepository` مباشرة، **بلا أي service أو
endpoint**:

1. **`test_create_relationship_and_visibility_settings_for_all_sectors`**:
   إنشاء `GuardianRelationship` (guardian↔ward، `FATHER`) + 4 صفوف
   `GuardianVisibilitySetting` (كل قيم `GuardianVisibilitySector`).
   يتأكد: `status == PENDING_WARD_APPROVAL` (افتراضي)،
   `ward_birth_date_provided/verified_by/verified_at` كلهم `None`،
   و`list_visibility_settings` بترجع الـ4 صفوف بكل القطاعات. **PASSED**.
2. **`test_duplicate_guardian_ward_pair_rejected_by_unique_constraint`**:
   إنشاء علاقة، ثم محاولة إنشاء علاقة تانية بنفس
   `(guardian_user_id, ward_user_id)` (نوع علاقة مختلف حتى) — يترفض
   بـ`IntegrityError` فعلي من DB (القيد `uq_guardian_ward`)، مش مجرد
   فحص تطبيقي. **PASSED**.
3. **`test_duplicate_visibility_sector_rejected_by_unique_constraint`**:
   إنشاء صف رؤية لقطاع `ACADEMY`، ثم محاولة تكراره لنفس العلاقة —
   يترفض بـ`IntegrityError` فعلي (القيد
   `uq_guardian_visibility_relationship_sector`). **PASSED**.

**النتيجة: 3/3 نجحوا** (`57.75s`، عبر `pytest tests/test_guardian_relationship_foundation_implementation.py -v`).

### اكتشاف جانبي أثناء كتابة الاختبار: Deadlock حقيقي (اتصلح، صفر تعديل على الكود الأساسي)

أول محاولة تشغيل **عَلَّقت بلا نهاية** (اتأكَّد بفحص `pg_stat_activity`
مباشرة على DB، مرتين، بنفس النمط بالضبط):

```
pid=113557 | idle in transaction | SELECT ... FROM guardian_visibility_settings ...
pid=113568 | active | Lock/transactionid | DELETE FROM users WHERE users.id IN ($1, $2)
```

**السبب الجذري:** `INSERT` في `guardian_relationships` (جدول عنده FK
على `users.id`) بياخد قفل `FOR KEY SHARE` من Postgres تلقائيًا على صفوف
`users` المُشار إليها (guardian/ward)، ويفضل هذا القفل قائم لحد ما
الترانزاكشن الحالية تتقفل (`commit`/`rollback`). الاختبار الأصلي كان
بيعمل `flush()` بس جوّه فيكستشر `db` (بلا `commit()` صريح)، وبعدين
الـ`finally` بيفتح `session` **منفصلة** (`AsyncSessionLocal()`) وتحاول
`DELETE FROM users` لنفس الصفوف. النتيجة: **تعليق دائري (self-deadlock)**
— الـ`finally` مستني القفل يتفكّ (ما بيتفكّش غير لما فيكستشر `db`
تعمل rollback تلقائي بعد ما الـtest function *كلها* تخلص)، والـtest
function مش هتخلص لحد ما الـ`finally` نفسه يخلص.

**الفرق عن `achievements`:** نفس النمط بالضبط (INSERT فيه FK على
`users` + `finally` بـsession منفصلة)، لكن معلَّق شغال هناك عادي —
لأن `AchievementService.grant_achievement` بيعمل `await self.db.commit()`
صريح **جوّه الـservice نفسه** بعد كل إنشاء ناجح، فبيفكّ القفل قبل ما
الـtest يوصل للـ`finally`. هنا مفيش service بعد (بالحرف حسب نطاق
الجلسة)، فالاختبار نفسه لعب الدور المؤقت وأضاف `await db.commit()`
صريح بعد كل `create_relationship`/`create_visibility_setting` ناجح —
3 مواضع في الملف. هذا **تعديل على ملف الاختبار الجديد نفسه فقط**، صفر
تعديل على `models.py`/`schemas.py`/`repository.py`/الـmigration.

**تنظيف أثناء التشخيص:** عمليتين python عالقتين اتقفلوا يدويًا
(`Stop-Process -Force`)، وصف من `pg_stat_activity` عالق (`idle in
transaction`) اتصفّى بـ`pg_terminate_backend`، و7 صفوف throwaway
(`p_regtest_guardian*`/`p_regtest_ward*`) من محاولات فاشلة سابقة
اتمسحوا يدويًا من `users`. بعد الإصلاح: **صفر بقايا بيانات** (اتأكَّد
مباشرة: `guardian_relationships`, `guardian_visibility_settings`, و
مستخدمين `p_regtest_*` كلهم `count=0` بعد كل تشغيلة ناجحة).

---

## 4. Regression

- **`pytest --collect-only -q` على كامل `tests/`** (226 اختبار): صفر
  خطأ استيراد جديد ناتج عن الدومين الجديد. الخطأ الوحيد الموجود
  (`ImportError: cannot import name 'ActionCommission' from
  app.domains.affiliate.models`, في
  `tests/test_affiliate_service_missing_methods.py`) **مسبق وموثَّق من
  قبل** كـside-finding من جلسة
  [[project_tourism_sports_entity_membership_implementation_closed]]
  (لم يُصلَح وقتها، خارج نطاق تلك الجلسة أيضًا) — **صفر علاقة** بهذه
  الجلسة أو بدومين `guardian`.
- **عيّنة تشغيل فعلية** (`test_achievements_foundation_implementation.py`
  + `test_achievement_auto_grant_training_implementation.py`, 7
  اختبارات، أقرب دومين هيكليًا لـ`guardian`): **7/7 نجحوا**.
- **صفر تعديل على أي ملف موجود مسبقًا** — الجلسة إضافة بحتة (migration
  جديدة + دومين جديد + ملف اختبار جديد)، فمخاطر الـregression على أي
  دومين قائم صفرية بنيويًا (مفيش أي كود قائم بيستورد أو يعتمد على
  `guardian` بعد).

---

## الحالة النهائية

- **مبني ومتحقَّق منه حيًا:** migration 056، `app/domains/guardian/`
  (models + schemas + repository)، اختبار حي 3/3.
- **غير مبني عمدًا (المرحلة القادمة):** أي `service.py`/`router.py`،
  منطق طلب/موافقة الطالب، تحقق إداري فعلي، تنبيهات، أو أي فحص لعمر
  القاصر.
- **لم يُعمَل commit على git بعد** — بانتظار طلب المستخدم.
- **PROGRESS_LOG.md** اتحدَّث بإدخال جديد لهذه الجلسة.
