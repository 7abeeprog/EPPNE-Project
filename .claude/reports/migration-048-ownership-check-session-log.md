# جلسة فحص ملكية migration 048 — قراءة فقط

**التاريخ:** 2026-09-21

**النطاق:** تحديد مين أنشأ `048_add_cancelled_at_to_saas_tenant_subscriptions`
(untracked في git)، وإيه اللي بيتغيّر بيه، وهل هي مُطبَّقة على القاعدة،
وأي ملفات uncommitted تخصها، وهل آمن نعمل commit.

**قيود الجلسة:** قراءة فقط. صفر commit، صفر staging، صفر كتابة على القاعدة،
صفر `alembic upgrade/downgrade`، صفر تعديل على أي ملف موجود. الملف الوحيد
المُنشأ هو هذا التقرير (+ سكربت فحص مؤقت في scratchpad خارج المشروع، كل
استعلاماته `SELECT` داخل `SET TRANSACTION READ ONLY`).

> ملاحظة مسار: الـmigrations في `eppne-backend/migrations/versions/`
> (`alembic.ini` → `script_location = migrations`)، مش `alembic/versions`.

---

## 1) متى اتنشأت ومين أنشأها

| البند | القيمة |
|---|---|
| تاريخ إنشاء الملف (birth time) | **2026-09-09 00:50:43 (+03:00)** |
| تقرير الجلسة الأصلية | `.claude/reports/cleanup-cancelled-subscriptions-task-fix-session-log.md` (أُنشئ 2026-09-09 01:11:57 — بعد الـmigration بـ21 دقيقة) |
| حالة التقرير في git | **untracked** أيضًا |

**الجلسة المالكة:** جلسة "إصلاح `cleanup_cancelled_subscriptions_task` — المرحلة أ
فقط". التقرير نفسه بيذكر 048 صراحةً في §2-ب و§6 وبيقول إنها "مُطبَّقة فعليًا
على القاعدة الحية".

**كل مواضع ذكر `048`/`cancelled_at` داخل `.claude/`:**
- `cleanup-cancelled-subscriptions-task-fix-session-log.md` — **المصدر الأصلي**.
- `saas-nonexistent-methods-investigation-session-log.md` (2026-09-08) — تحقيق
  سابق بيقول إن `cancelled_at` غير موجود وقتها (التمهيد للجلسة أعلاه).
- `insurance-entity-membership-gap-fix-session-log.md`،
  `insurance-batch0a-*` (تقارير + patches) — بتذكر 048 كـ**تبعية**: migration 049
  (`down_revision = '048_...'`).
- تطابقات عرضية غير مرتبطة: `academy-product-decisions-...`
  (`cancelled_at` في enrollment)، `remaining-7-domains-...`، `phase9-audit-identity-report.md`.

**في `PROGRESS_LOG.md`:** رأيك صح جزئيًا.
- **لا يوجد أي إدخال يوثّق إنشاء 048 أو إصلاح `cleanup_cancelled_subscriptions_task`.**
- 048 مذكورة فقط في موضعين، كلاهما من جلسة insurance وكتبعية: السطر 19
  والسطر 1034 (`insurance-batch0a-commits-pending`: "049 تعتمد على 048 غير
  tracked من جلسة saas — قرارها لصاحب جلسة saas/المستخدم").
- **تناقض مُكتشَف:** §6 من تقرير الجلسة الأصلية بيقول
  "`PROGRESS_LOG.md` — إدخال جديد يوثِّق الإصلاح"، لكن الملف الفعلي (مسوّدة
  العمل الحالية) ما فيهوش إدخال كده، وبنود `cleanup_cancelled_subscriptions_task`
  (السطور 3148 / 3228 / 3322) لسه مكتوبة 🔴 "لسه مفتوح، يحتاج قرار نطاق
  PDPL/GDPR" — والنص ده موجود أصلًا في HEAD. **يعني الإدخال المزعوم إما ما
  اتكتبش أو ضاع/اتفقد في تعديل لاحق على الملف.**

---

## 2) إيه اللي بتغيّره بالضبط

### الـmigration (`upgrade`)
- `ADD COLUMN saas_tenant_subscriptions.cancelled_at TIMESTAMPTZ NULL`.
- `CREATE INDEX ix_saas_tenant_subscriptions_cancelled_at ON (cancelled_at)`.
- **بلا backfill** عمدًا (اشتراك CANCELLED قديم مثل id=50 يفضل NULL).

### (`downgrade`)
- `DROP INDEX ix_saas_tenant_subscriptions_cancelled_at` ثم `DROP COLUMN cancelled_at`.
  متماثل وسليم.

### الكود المستخدم للعمود (كل diff أُطبق عليه `git diff`)
| الملف | التعديل | ينتمي لـ048؟ |
|---|---|---|
| `app/domains/saas/models.py` | عمود `cancelled_at` + `Index(...cancelled_at)` في `__table_args__` (+7 سطور) | ✅ كامل |
| `app/domains/saas/service.py` | `cancel_subscription` يملأ `cancelled_at=now(utc)` + دالة جديدة `cleanup_cancelled_subscriptions` (+52) | ✅ كامل |
| `app/domains/saas/repository.py` | دالة `get_cancelled_subscriptions_for_cleanup` (30 يوم، `cancelled_at IS NOT NULL`) (+22) | ✅ كامل |
| `app/tasks/saas_tasks.py` | hunk واحد فقط: تصحيح constructor إلى `SaaSControlService(db, 0)` + إزالة `type: ignore` + docstring | ✅ كامل (hunk وحيد) |

لا يوجد ملف كود آخر في المشروع بيستخدم `cancelled_at` الخاص بالاشتراكات
(الباقي `academy/*` و`032` هو `cancelled_at` تبع enrollment — عمود مختلف).

---

## 3) الحالة على القاعدة + سلامة السلسلة

### القاعدة (قراءة فقط)
- `alembic_version` = **`067_site_legal_clearance`** (يعني 048 مُطبَّقة ضمنيًا
  لأن الـhead بعدها).
- العمود موجود: `cancelled_at` — `timestamp with time zone`، `is_nullable = YES`.
- الـindex موجود: `ix_saas_tenant_subscriptions_cancelled_at`.
- صفوف CANCELLED: صف واحد فقط `id=50`، `cancelled_at = NULL` (متوافق مع
  التصميم: بلا backfill).
- **العمود في الموديل مطابق للقاعدة** (نوع، nullable، اسم الـindex).

### سلسلة الـdown_revision (من الملفات)
`046 → 047 → 048 → 049 → 050 → 051 → 052 → 053 → 054 → 055 → 056 → 057 → 058
→ 059 → 060 → 061 → 062 → 063 → 064 → 065 → 066 → 067`

- كل `down_revision` يشير للـrevision الصحيح اللي قبله؛ **لا فجوات، لا
  تفرّع، لا تكرار في `down_revision`**.
- (الملاحظة الوحيدة الجانبية: ملفين بنفس البادئة `71820e4fe1f3` في أول
  السلسلة — قديم وغير مرتبط بـ048، مش من نطاق الجلسة دي.)

### خطر مُكتشَف: سلسلة الـHEAD المُلتزَم (committed) مكسورة أصلًا
Migrations المُتتبَّعة في git من 044 وما بعد: `044-047`، `052`، `054`،
`056-061`. الـuntracked: `048-051`، `053`، `055`، `062-067`.
- `052` (مُلتزَمة) `down_revision = '051_...'` (untracked).
- `054` (مُلتزَمة) `down_revision = '053_...'` (untracked).
- `056` (مُلتزَمة) → `055` (untracked).
- **يعني clone نظيف من HEAD الحالي هيفشل في `alembic upgrade`/`heads`**
  (revision مفقودة) — والوضع ده موجود قبل هذه الجلسة، مش بسبب 048 لكن 048
  هي أول حلقة ناقصة في السلسلة.

---

## 4) الملفات uncommitted اللي تخص 048

### تنتمي مباشرة (مكتملة)
| الملف | الحالة |
|---|---|
| `eppne-backend/migrations/versions/048_add_cancelled_at_to_saas_tenant_subscriptions.py` | ✅ مكتملة، مُطبَّقة، متطابقة مع الموديل |
| `app/domains/saas/models.py` | ✅ كامل (كل الـdiff تبع 048) |
| `app/domains/saas/service.py` | ✅ كامل |
| `app/domains/saas/repository.py` | ✅ كامل |
| `app/tasks/saas_tasks.py` | ✅ كامل (hunk واحد) |
| `.claude/reports/cleanup-cancelled-subscriptions-task-fix-session-log.md` | ✅ تقرير كامل، untracked |

### نصف مكتملة / ناقصة
| البند | الملاحظة |
|---|---|
| **اختبار regression للـcleanup/`cancelled_at`** | ❌ **لا يوجد ملف اختبار** يغطي `cleanup_cancelled_subscriptions` أو `cancelled_at` (grep على `tests/` = صفر). التحقق اللي تم كان حيًّا بصفوف مؤقتة (throwaway) حسب التقرير §3/§4، وما اتحوّلش لاختبار دائم. |
| **إدخال PROGRESS_LOG** | ❌ ناقص/مفقود (انظر §1). بنود 🔴 لسه بتقول "مفتوح". |
| المرحلة ب (تعمية PII) | مؤجَّلة عمدًا بقرار مصمّم — مش نقص. |

### ملفات uncommitted **مش** تبع 048 (بلاش تدخل في commit 048)
- `tests/test_saas_cancel_subscription_silent_write.py` و
  `tests/test_trigger_renewals_endpoint_missing_commit.py` — تعديل
  `PlanServiceAccess` fixture (جلسة `transport-and-related-fixtures-plan-service-access-fix`،
  مرتبطة بـmigration **047** مش 048).
- `app/core/celery_app.py` و`app/core/celery_config.py` — جلسة celery beat
  autodiscover (مذكورة في الـdiff: `app.tasks.saas_tasks`)؛ ما تخصّش 048.
- ملفات insurance (049 وتوابعها)، وبقية migrations 049-067، و`PROGRESS_LOG.md`
  (تعديلات كثيرة من جلسات مختلفة).

---

## 5) هل آمن الـcommit as-is؟

**الخلاصة: نعم، لمجموعة الملفات المحدَّدة في §4 "تنتمي مباشرة" — بشروط.**

المخاطر المفحوصة:
- عدم تطابق العمود: ❌ غير موجود (الموديل = القاعدة = الـmigration).
- تعديل ناقص في الموديل: ❌ غير موجود (كل الـhunks الأربعة كاملة ومترابطة).
- `downgrade`: سليم.
- تبعية insurance 049 → 048: لازم 048 تتلتزم **قبل أو مع** insurance، وإلا
  049 تبقى يتيمة.
- ⚠️ **لا اختبارات لهذا الكود** — مش blocker للـcommit لكنه فجوة تغطية.
- ⚠️ **لم أشغّل أي اختبارات** (الـfixtures بتكتب في القاعدة، وأنت طلبت أسأل
  الأول). لو عايز، أقترح فقط تشغيل `tests/test_saas_cancel_subscription_silent_write.py`
  بعد موافقتك.
- ⚠️ عند الـcommit: فحص `git diff --cached --name-only` قبل الالتزام، و
  `git show --stat` بعده يتأكد من عدد الملفات (ملفات مُستَتجرة مسبقًا من
  جلسات أخرى ممكن تركب).
- ⚠️ ما يتلتزمش `PROGRESS_LOG.md` كامل — تعديلات كثيرة من جلسات مختلفة.

---

### تحديث بعد موافقة المستخدم — تشغيل الاختبار
تم تشغيل `tests/test_saas_cancel_subscription_silent_write.py` فقط (بموافقة
صريحة): **2 passed في 60 ثانية**، صفر فشل. الاختبار يمرّ على
`cancel_subscription` بعد إضافة `cancelled_at=now(utc)`، يعني الكود المعدَّل
بيشتغل فعليًا مع العمود الجديد على القاعدة الحية. لم أشغّل أي اختبارات أخرى.
(ملحوظة: الاختبار ده بيغطي `cancel_subscription` فقط، مش
`cleanup_cancelled_subscriptions` — الفجوة في §4 لسه قائمة.)

---

## 6) التشخيص

048 من جلسة `cleanup_cancelled_subscriptions_task` (2026-09-09)، **مكتملة
تنفيذًا ومُطبَّقة ومتطابقة مع الموديل**، لكنها فضلت untracked مع كودها
وتقريرها لأن جلسة 09-09 ما عملتش commit وما وثّقتش نفسها فعليًا في
PROGRESS_LOG. الأثر الجانبي: HEAD الحالي فيه سلسلة migrations مكسورة
(052 → 051 مفقودة).

## 6-ب) تنفيذ الـcommit بعد الموافقة — فحوصات ما قبل الـcommit [2026-09-21]

- **فحص بقايا الاختبار (SELECT فقط، `SET TRANSACTION READ ONLY`):** بعد تشغيل
  `test_saas_cancel_subscription_silent_write.py` — صفوف `REGTEST-CANCEL*`
  في `saas_service_catalog` = 0، `saas_service_plans` = 0،
  `saas_tenant_subscriptions` = 0. صفوف CANCELLED الإجمالية = 1 (id=50 القديم)
  — **لا بقايا**.
- **hunks الملفات الأربعة (`git diff HEAD`):** `models.py` 2 hunk (+7)،
  `service.py` 2 hunk (+52: سطر `cancelled_at` + دالة cleanup)،
  `repository.py` 1 hunk (+22)، `saas_tasks.py` 1 hunk — كلها 048 فقط، صفر
  hunk من جلسة تانية.
- **hash ملف `PROGRESS_LOG.md` (worktree) قبل الـcommit:**
  `8dc754db9accd24d49aa9ac76910febe22e8f8c8ad5aed3226b5c7ebae805708`
  (يُقارَن بعد الـcommit للتأكد إنه ما اتلمسش).
- الـindex كان فاضي (`git diff --cached --name-only` = 0 ملف) قبل أي `git add`.
- طريقة الـcommit: `git add` بالاسم لكل ملف من السبعة، فحص
  `--cached --name-only/--stat`، ثم `git commit` بدون pathspec.

---

## 6-ج) بنود backlog مسجَّلة (بدون أي كود)

### (أ) سلسلة migrations مكسورة في HEAD
الـmigrations المُلتزَمة (tracked) في HEAD بتشير لأبوين **untracked**:
- `052_health_facility_entity_id_fk_set_null` → `down_revision = 051_...` (untracked)
- `054_create_achievement_tables` → `down_revision = 053_...` (untracked)
- `056_create_guardian_relationship_tables` → `down_revision = 055_...` (untracked)

وملفات `048`-`051` و`053` و`055` و`062`-`067` كلها untracked (048 اتضافت في
commit هذه الجلسة، الباقي لسه). النتيجة: clone نظيف من HEAD مش هيقدر يبني
السلسلة (`alembic upgrade`/`heads` بيفشل بـrevision مفقودة) — الوضع قديم
وليس ناتجًا عن 048. **بعد commit 048 لسه مكسورة** لأن 049-051 و053 و055 مش
مُلتزَمة.

### (ب) بند backlog: `commit-hygiene-untracked-migrations-049-067-and-uncommitted-work`
**الحالة وقت هذه الجلسة (بعد commit 048 تقريبًا، قياس `git status --short`
قبله):** 166 مدخل غير نظيف = **60 ملف معدَّل (M) + 106 غير متتبَّع (??)**
(قدّرتها أنت بـ~174؛ الرقم الفعلي المقاس 166 قبل إضافة ملفات هذه الجلسة).
- **37 commit محلي غير مدفوع** (`git rev-list --count origin/main..HEAD` = 37)
  — مفيش push اتعمل ولا هيتعمل في هذه الجلسة.
- migrations untracked المتبقية: `049`، `050`، `051`، `053`، `055`،
  `062`، `063`، `064`، `065`، `066`، `067` (11 ملف).
- `PROGRESS_LOG.md` معدَّل بتعديلات جلسات كتير ولا يُلتزَم كاملًا
  (يُقسَّم hunks).
- تعديلات insurance/academy/sites/iot/celery/tests متداخلة بين جلسات.
**لا يُلتزَم أي شيء من هذا النطاق في هذه الجلسة.** يحتاج جلسة تخطيط مستقلة
(ترتيب commits حسب سلسلة الـdown_revision، تقسيم الملفات المتداخلة).
**الأولوية:** 🟡 متوسطة-عالية (git hygiene + سلسلة مكسورة، خطر فقد عمل لو
حصل عطل محلي قبل push).

---

## 7) خطة الـcommit المقترحة (اتنفّذت بعد الموافقة — التفاصيل في §6-ب)

**Commit 1 (السطر الأول):**
`feat(saas): add cancelled_at to tenant subscriptions and phase-A cleanup_cancelled_subscriptions_task`

**الملفات (7 + هذا التقرير = 8):**
1. `eppne-backend/migrations/versions/048_add_cancelled_at_to_saas_tenant_subscriptions.py`
2. `eppne-backend/app/domains/saas/models.py`
3. `eppne-backend/app/domains/saas/service.py`
4. `eppne-backend/app/domains/saas/repository.py`
5. `eppne-backend/app/tasks/saas_tasks.py`
6. `.claude/reports/cleanup-cancelled-subscriptions-task-fix-session-log.md`
7. `.claude/reports/migration-048-ownership-check-session-log.md`

طريقة التنفيذ: `git commit -m "..." -- <pathspec>` ثم `git show --stat` للتأكد
من 7 ملفات بالضبط.

**بعده (منفصل، بموافقة):**
- Commit 2: إدخال `PROGRESS_LOG.md` تعويضي (append-only) لإغلاق
  `cleanup_cancelled_subscriptions_task` (المرحلة أ) — hunk فقط، مش الملف كله.
- (اختياري) اختبار regression للـcleanup/`cancelled_at` في جلسة منفصلة.
- بعد 048: commit insurance (049 + توابعها) ثم 050-067 حسب قراراتك، لإصلاح
  السلسلة المكسورة في HEAD.
