# Phase 7 — خطة تنفيذ عزل tenant_id لـ iot و privacy (مسودة تخطيط، بدون تنفيذ)

> هذا الملف تراكمي: كل خطوة من phase7-iot-privacy-tenant-isolation-planning.md
> بتتوثق هنا بالنتيجة الفعلية، بدون أي تنفيذ كود أو migration.

---

## الخطوة 1 — فحص models.py الفعلي (تم)

**النتيجة:** الأعمدة العشرة (6 iot + 4 privacy) موجودة فعليًا في `models.py`
كلها بنفس النمط: `Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"),
nullable=False, index=True`.

| دومين | الجدول | tenant_id في models.py |
|---|---|---|
| iot | smart_assets | ✅ |
| iot | utility_grids | ✅ |
| iot | utility_readings | ✅ |
| iot | maintenance_logs | ✅ |
| iot | idempotency_records | ✅ |
| iot | iot_request_logs | ✅ |
| privacy | privacy_settings | ✅ |
| privacy | data_consent_logs | ✅ |
| privacy | data_erasure_requests | ✅ |
| privacy | tombstone_records | ✅ |

هذا يتماشى مع ما ذكره P0 في PROGRESS_LOG.md (سطر 13)، وليس مع
PROJECT_AUDIT.md §4.3 (اللي قال صفر tenant_id) — الأخير يبدو قديم/غير محدَّث
بعد P0.

---

## الخطوة 2 (جزء أول) — فحص محتوى migrations (تم)

**الملفات المفحوصة** (migrations/versions/, بترتيب down_revision متسلسل
017 → 026، ولا يوجد أي ملف migration بعد 026):

- `017_add_tenant_id_to_smart_assets.py`
- `018_add_tenant_id_to_utility_grids.py`
- `019_add_tenant_id_to_utility_readings.py`
- `020_add_tenant_id_to_maintenance_logs.py`
- `021_add_tenant_id_to_idempotency_records.py`
- `022_add_tenant_id_to_iot_request_logs.py`
- `023_add_tenant_id_to_privacy_settings.py`
- `024_add_tenant_id_to_data_consent_logs.py`
- `025_add_tenant_id_to_data_erasure_requests.py`
- `026_add_tenant_id_to_tombstone_records.py`

### النتيجة: كل الـ 10 migrations فيها منطق data migration حقيقي، مش مجرد schema migration بقيمة افتراضية موحّدة

كل ملف بيتبع نفس النمط الأربع خطوات:

1. `op.add_column(..., nullable=True)` — إضافة العمود قابل للـ NULL مبدئيًا.
2. **Backfill بالاستنتاج من علاقة موجودة فعليًا** (مش قيمة ثابتة/افتراضية
   موحّدة زي `DEFAULT 1`):

   | الجدول | مصدر الاستنتاج |
   |---|---|
   | smart_assets | `UPDATE ... SET tenant_id = users.tenant_id FROM users WHERE smart_assets.owner_id = users.id` |
   | utility_readings | من `smart_assets.tenant_id` (عبر asset_id) ثم من `utility_grids.tenant_id` (عبر grid_id) لو النتيجة الأولى NULL |
   | maintenance_logs | من `smart_assets` (asset_id) ثم `utility_grids` (grid_id) ثم `users` (technician_id) — تسلسل fallback ثلاثي |
   | iot_request_logs | من `users.tenant_id` عبر `user_id` |
   | privacy_settings | من `users.tenant_id` عبر `user_id` |
   | data_consent_logs | من `users.tenant_id` عبر `user_id` |
   | data_erasure_requests | من `users.tenant_id` عبر `user_id` |
   | tombstone_records | من `users.tenant_id` عبر `deleted_by_id` |
   | **utility_grids** | ⚠️ **لا يوجد أي عمود ربط بـ user/tenant في الجدول أصلًا** — مفيش backfill ممكن منطقيًا |
   | **idempotency_records** | ⚠️ **لا يوجد أي عمود ربط بـ user/tenant في الجدول أصلًا** (بس key, response_data, expires_at) — مفيش backfill ممكن منطقيًا |

3. **Fail-safe صريح، مش fail-silent**: كل migration بتعمل
   `SELECT COUNT(*) WHERE tenant_id IS NULL` بعد الـ backfill، ولو `orphan_count > 0`
   بترفع `RuntimeError` وتوقف الـ migration بالكامل، بدل ما تحط قيمة افتراضية
   عشوائية (زي tenant_id=1) لصفوف اتفشل استنتاجها. هذا ينطبق حتى على
   `utility_grids` و`idempotency_records` — لو فيهم أي صف موجود وقت التنفيذ،
   الـ migration كانت هتفشل بالضرورة (لأن مفيش أي استنتاج ممكن لهم).
4. `alter_column(nullable=False)` + `create_index` + `create_foreign_key` —
   نفس نمط باقي migrations الـ 16 السابقة (001-014, 016).

**الخلاصة الفنية:** هذا تصميم migration جيد ومسؤول من ناحية سلامة البيانات —
مفيش أي قيمة افتراضية موحّدة اتحطت بشكل أعمى، والاستنتاج منطقي ومبني على
علاقات حقيقية، والفشل صريح (exception) مش صامت.

---

## التحقق من DB (تم — 2026-08-10)

تم الاتصال بنفس بيئة الـ DB المحلية اللي استخدمها P0 (نفس `DATABASE_URL` في
`.env`: `postgresql+asyncpg://eppne:***REDACTED***@127.0.0.1:5435/eppne_v2`، اللي
بيوصّل لكونتينر Docker `eppne_db` — postgres:16، بورت مضبوط `5435:5432`).
تم التنفيذ عبر `docker exec eppne_db psql -U eppne -d eppne_v2 -c "..."`،
استعلامات `SELECT` للقراءة فقط، بدون أي تعديل.

### 1. alembic_version

```sql
SELECT version_num FROM alembic_version;
```
**النتيجة:** `026_add_tenant_id_to_tombstone_records` — ✅ يطابق آخر ملف في
سلسلة migrations (مفيش أي ملف بعد 026 في migrations/versions/). هذا يؤكد
أن سلسلة migrations 017-026 **اتنفذت فعليًا** ضد هذه الـ DB، مش مجرد ملفات
مكتوبة وماشيتش.

### 2. عدد الصفوف + NULL tenant_id لكل جدول (أرقام خام من التنفيذ الفعلي)

كل جدول اتفحص بأمر منفصل:
`SELECT COUNT(*), COUNT(*) FILTER (WHERE tenant_id IS NULL) FROM <table>;`

| # | الجدول | الدومين | COUNT(*) الكلي | COUNT(*) FILTER (tenant_id IS NULL) |
|---|---|---|---:|---:|
| 1 | smart_assets | iot | 0 | 0 |
| 2 | utility_grids | iot | 0 | 0 |
| 3 | utility_readings | iot | 0 | 0 |
| 4 | maintenance_logs | iot | 0 | 0 |
| 5 | idempotency_records | iot | 0 | 0 |
| 6 | iot_request_logs | iot | 0 | 0 |
| 7 | privacy_settings | privacy | 0 | 0 |
| 8 | data_consent_logs | privacy | 0 | 0 |
| 9 | data_erasure_requests | privacy | 0 | 0 |
| 10 | tombstone_records | privacy | 0 | 0 |

**كل الجداول العشرة: 0 صف NULL — مطابق للمتوقع.** لكن كل الجداول العشرة
كمان **فاضية بالكامل (0 صف إجمالي)** في هذه البيئة، بدون أي استثناء.

### ⚠️ التعديل على الافتراض السابق بناءً على نتيجة التحقق الفعلي

الجزء اللي كان "افتراض غير مؤكد" في القسم اللي بعد كده **اتأكد جزئيًا**:

- ✅ **مؤكد الآن (فعليًا من DB حية)**: الـ schema فعلاً `NOT NULL` على
  `tenant_id` في كل الجداول العشرة (لو مكنش، `alter_column(nullable=False)`
  كانت فشلت والـ `alembic_version` ماكانتش توصل لـ 026).
- ✅ **مؤكد الآن**: migrations 017-026 اتنفذت فعليًا ضد هذه الـ DB المحلية
  (مش بس مكتوبة في الكود).
- ⚠️ **لسه غير مؤكد، ولن يتأكد من هذه البيئة تحديدًا**: منطق الـ backfill
  (الاستنتاج من `owner_id`/`asset_id`/`grid_id`/`user_id`/`technician_id`/
  `deleted_by_id`) **لم يُختبَر فعليًا ضد بيانات حقيقية**، لأن كل الجداول
  العشرة كانت (ولسه) فاضية بالكامل وقت تنفيذ الـ migrations. نجاح
  الـ migrations هنا كان لأن شرط الفشل (`orphan_count > 0`) محدش استوفاه
  أصلًا — مش لأن منطق الربط اتحقق من صحته على صف واحد حقيقي.
- ⚠️ هذا التحقق يخص بيئة local development فقط. **لا يوجد أي تأكيد من هذه
  الجلسة عن حالة staging أو production** — لو فيهم بيانات فعلية، احتمال
  فشل الـ backfill (وبالتالي فشل الـ migration بالكامل عبر `RuntimeError`)
  أعلى بكثير، وتحديدًا لـ `utility_grids` و`idempotency_records` اللي
  أصلًا معندهمش أي عمود ربط ممكن — لو فيهم صف واحد حقيقي في أي بيئة تانية،
  الـ migration هتفشل قطعيًا وتحتاج تدخل يدوي (تحديد tenant_id يدويًا
  لكل صف orphan قبل إعادة المحاولة؛ الكود الحالي معندوش أي fallback تلقائي
  لهذه الحالة، وده سيناريو افتراضي لم يحدث فعليًا — مجرد قراءة لما الكود
  هيعمله لو حصل).

---

### ⚠️ افتراض غير مؤكد (وقت كتابته) — تم حسمه لاحقًا، انظر قسم "التحقق من DB" أعلاه

> **ملاحظة:** هذا القسم كان مكتوبًا وقت الفحص الـ static فقط (قبل الاتصال
> بالـ DB). الأسئلة اللي طرحها اتحسمت فعليًا في قسم "التحقق من DB" أعلاه.
> تم إبقاؤه هنا كسجل تاريخي لمسار التخطيط، مش كحالة حالية.

وقتها، الفحص كان **static لمحتوى ملفات migration فقط** (قراءة كود Python)،
وده كان لا يثبت أن هذه الـ migrations اتنفذت فعليًا (`alembic upgrade head`)
ضد أي قاعدة بيانات حية. الأسئلة المفتوحة وقتها وحسمها الفعلي:

| السؤال المفتوح وقتها | الحسم الفعلي (من قسم "التحقق من DB") |
|---|---|
| هل `tenant_id` فعلاً `NOT NULL` في الـ DB دلوقتي؟ | ✅ نعم — مؤكد من DB حية |
| هل `utility_grids`/`idempotency_records` كانوا فاضيين وقت الـ migration؟ | ✅ نعم — وكمان لسه فاضيين دلوقتي (0 صف) |
| هل فيه صفوف NULL حاليًا في أي من العشرة؟ | ✅ لأ — 0 في كل الجداول العشرة |
| هل `alembic_version` = 026 فعلاً؟ | ✅ نعم — مؤكد بالحرف |

**تنبيه ما زال قائمًا رغم الحسم أعلاه:** التحقق ده كله كان على بيئة
**local development فقط**. لا يوجد أي تأكيد لحالة staging/production. وبما
إن كل الجداول لسه فاضية محليًا، **منطق الـ backfill نفسه لسه معملوش
اختبار حقيقي على بيانات فعلية** — التفاصيل الكاملة في قسم "التحقق من DB"
أعلاه.

---

## الخطوات المتبقية (لسه معلّقة — لم تُنفَّذ في هذه الجلسة)

- [ ] فحص `repository.py` لكل دومين: هل الاستعلامات بتفلتر بـ tenant_id
      يدويًا في مستوى الكود (عزل منطقي في service layer) بالإضافة للعزل
      على مستوى الـ schema؟
- [ ] تحديد هل فيه حاجة فعلية لـ data migration إضافي (لو ثبت إن الجداول
      كانت فاضية وقت 017-026 وفيها بيانات دلوقتي محتاجة معالجة يدوية).
- [ ] اقتراح خطة migrations لو لُقي نقص فعلي (بعد التحقق من الـ DB الحي).
- [ ] اقتراح خطة تعديل كود لكل endpoint/query لو لُقي نقص.
- [ ] اقتراح خطة smoke tests للتأكد إن tenant A مش شايف بيانات tenant B.

---

## قرار مبدئي (محدَّث بعد التحقق من DB — لسه معلّق على repository.py)

بناءً على الخطوة 1، الخطوة 2، والتحقق الفعلي من الـ DB المحلية:

- ✅ **مؤكد فعليًا (schema + تنفيذ)**: عزل tenant_id على مستوى الـ schema
  مكتمل ومُنفَّذ فعليًا لكلا الدومينين على بيئة local — العمود موجود،
  `NOT NULL`، مفهرس، مربوط بـ FK صحيح، وسلسلة migrations 017-026 اتنفذت
  فعليًا لآخرها (`alembic_version = 026`).
- ⚠️ **غير مؤكد**: صحة منطق الـ backfill على بيانات حقيقية (لم يُختبَر —
  الجداول فاضية)، وحالة staging/production (لم يتم فحصها في هذه الجلسة).
- ⚠️ **لسه معلّق بالكامل**: العزل المنطقي في `repository.py` — هل
  الاستعلامات فعليًا بتفلتر بـ `tenant_id` وقت التنفيذ، مش بس معتمدة على
  وجود العمود في الـ schema؟ ده لسه معملوش فحص في هذه الجلسة.

**الخلاصة:** عزل tenant_id "تم" على مستوى الـ schema بثقة عالية الآن (مش
افتراض، بل تحقق فعلي). لكن **ميتفترضش إن العزل الكامل (schema + منطق
الكود) "تم بالكامل"** لحد ما يتم فحص `repository.py` — وهو أول بند في
"الخطوات المتبقية" تحت.
