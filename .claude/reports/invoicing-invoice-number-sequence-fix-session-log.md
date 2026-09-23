# جلسة: إصلاح توليد invoice_number (غير آمن ضد الحذف → مفتاح مكرر دائم)

- **التاريخ:** 2026-09-23
- **البند المرجعي:** `invoicing-invoice-number-generation-not-deletion-safe-permanent-duplicate-key`
- **المصدر:** `.claude/reports/tourism-sports-transfer-bid-hardcoded-agent-id-6-implementation-session-log.md`
- **الحالة:** الخطوة 1 (قراءة فقط) + الخطوة 2 (تشخيص) — **متوقف بانتظار موافقة المستخدم**. صفر تعديل على الكود، صفر staging/commit، صفر كتابة على PROGRESS_LOG.md.

---

## الملخص التنفيذي

- **المشكلة:** `_generate_invoice_number` يستخدم `COUNT(*) + 1`. أي حذف لفاتورة (ليست الأخيرة) يجعل الرقم التالي يساوي رقمًا موجودًا → `IntegrityError` في كل محاولة، إلى الأبد.
- **الحالة الحية الآن:** tenant 1 **مقفول** (الرقم التالي `INV-1-000015` موجود)، و tenant 16 **مقفول أيضًا** (الرقم التالي `INV-16-000004` موجود) — اكتشاف جديد. tenant 15 سليم (صفر فواتير). أي 100% من التينانتات التي لها فواتير.
- **سبب الحذف:** كود تنظيف الاختبارات (`delete(Invoice)` في 5 ملفات)، وليس كود التطبيق.
- **الأثر:** ~20 مستدعٍ إنتاجي لـ`create_invoice` — بعضها يفشل كليًا، وبعضها يبتلع الخطأ ويترك الجلسة مسمومة (`PendingRollbackError`).
- **التوصية:** الخيار C (جدول عداد per-tenant، migration 068).
- **المطلوب منك:** تعبئة قسم "نموذج الرد" في آخر هذا الملف.

---

## الخطوة 1 — القراءة (read-only)

### 1.1 المنطق الحالي (مؤكَّد، الأسطر لم تتغير جوهريًا)

`eppne-backend/app/domains/invoicing/service.py:115-119`

```python
async def _generate_invoice_number(self, tenant_id: int) -> str:
    prefix = "INV"
    count = await self.repo.count_invoices(tenant_id)
    seq = str(count + 1).zfill(6)
    return f"{prefix}-{tenant_id}-{seq}"
```

`eppne-backend/app/domains/invoicing/repository.py:117-121`

```python
async def count_invoices(self, tenant_id: int) -> int:
    result = await self.db.execute(
        select(func.count()).where(Invoice.tenant_id == tenant_id)
    )
    return result.scalar() or 0
```

يُستدعى من `create_invoice` في `service.py:84`، ثم `repo.create_invoice` (`repository.py:22-31`) يعمل `commit()` مباشر.

### 1.2 الحالة الحية لكل التينانتات (قاعدة `eppne_v2` على `eppne_db`)

| tenant_id | COUNT(*) | MAX(seq) | الرقم التالي المُولَّد | موجود أصلًا؟ | الحالة |
|---|---|---|---|---|---|
| 1 | 14 | 15 | `INV-1-000015` | نعم (id=17) | **مقفول دائمًا** |
| 16 | 3 | 4 | `INV-16-000004` | نعم (id=160) | **مقفول دائمًا** (جديد — لم يكن موثقًا) |
| 15 | 0 | — | `INV-15-000001` | لا | سليم حاليًا، معرض للخطر عند أول حذف |

- **tenant 1:** الفجوة هي `INV-1-000010` (الصف id=12 محذوف). COUNT=14 → الرقم 15 موجود → فشل دائم. **الحالة ما زالت قائمة.**
- **tenant 16:** الفجوة هي `INV-16-000003` (محذوف). COUNT=3 → الرقم 4 موجود → فشل دائم. **اكتشاف جديد: التينانت الثاني مقفول أيضًا.**
- إجمالي التينانتات في `academy_tenants`: 3 (ids 1، 15، 16). **كل تينانت لديه أي فاتورة (2 من 2) مقفول حاليًا.**
- كل الصفوف (17 صف) مطابقة للصيغة `^INV-{tenant_id}-[0-9]+$` — صفر صفوف غير مطابقة (nonconforming = 0).
- مؤشر جانبي: `invoices_id_seq.last_value = 267` بينما `MAX(id) = 160` → ~107 قيمة id مستهلكة بلا صف ناتج (inserts فاشلة/rollback + حذف) — يتسق مع محاولات فشل متكررة.

### 1.3 مصدر الحذف

- `InvoicingRepository.delete_invoice(hard=True)` موجود (`repository.py:65-72`) لكن **صفر مستدعين** له في `app/`.
- الحذف الفعلي مصدره تنظيف الاختبارات: `delete(Invoice)` في:
  - `tests/test_realestate_insurance_savepoint.py:298`
  - `tests/test_realestate_rent_unit_ownership_check.py:90`
  - `tests/test_tenders_auctions_finance_hold_release_settle.py:160`
  - `tests/test_financeservice_tenant_binding_fix.py:95`
  - `tests/test_trigger_renewals_endpoint_missing_commit.py:101`
- بالإضافة لـ `ondelete="CASCADE"` من `academy_tenants` (حذف التينانت كله — لا يسبب المشكلة لأن كل فواتيره تُحذف معًا).
- **الخلاصة:** حتى لو صُحح الكود، أي حذف مستقبلي (اختبار، أو admin، أو hard-delete لاحقًا) يعيد القفل بالتصميم الحالي. المشكلة في التصميم، لا في بيانات معينة.

### 1.4 تعريف العمود والقيود

- `models.py:57`: `invoice_number = Column(String(50), unique=True, nullable=False, index=True)`
- القيود الحية (من `\d invoices`):
  - `invoices_invoice_number_key` UNIQUE CONSTRAINT (invoice_number)
  - `ix_invoices_invoice_number` UNIQUE btree (invoice_number) — **مكرر زائد** (نفس العمود مرتين؛ غير مؤثر على هذا الإصلاح، بند backlog منخفض).
- التفرد **عالمي** (ليس per-tenant)، لكن `tenant_id` جزء من النص → لا تصادم بين التينانتات.
- الصيغة: `INV-{tenant_id}-{seq مُبطَّن بـ6 أرقام}`. استخراج الـseq لنهج MAX:
  ```sql
  SELECT MAX(split_part(invoice_number, '-', 3)::int)
  FROM invoices
  WHERE tenant_id = :t AND invoice_number ~ ('^INV-' || :t || '-[0-9]+$');
  ```
  (الـregex ضروري كحماية من أي صف مستقبلي بصيغة مختلفة، حاليًا صفر.)

### 1.5 كائنات SEQUENCE الموجودة

- لا يوجد أي sequence خاص بأرقام الفواتير. الموجود فقط `invoices_id_seq` (للـPK) و`saas_invoices_id_seq`.
- لا يوجد جدول counters/ترقيم في المشروع يمكن إعادة استخدامه.
- ملاحظة: `saas_invoices` (جدول منفصل تمامًا، `saas/service.py:668`) يستخدم `INV-{uuid12}` — غير متأثر وخارج النطاق.
- آخر migration: `067_site_legal_clearance` (مطابق لـ `alembic_version`) → التالي **068**.

### 1.6 نطاق التأثير (blast radius)

`InvoicingService.create_invoice` يُستدعى من ~20 موضع إنتاج: zamakana، transport (×2)، tasks/employment، tourism_sports (×3)، tenders_auctions، service_marketplace، arbitration_syndicates (×3)، realestate (×2)، manufacturing (×2)، ai_agents، invitations، insurance (×2)، و `POST /invoicing` نفسه.

- بعضها داخل `try/except` (يبتلع الخطأ) — لكن الـflush الفاشل يترك الجلسة في `PendingRollbackError`، فتفشل أي عملية لاحقة على نفس الجلسة (موثق مسبقًا في `tests/test_ai_agents_execute_action.py:344-356` و commit `b4bf356`).
- بعضها **بلا حماية**، مثال `arbitration_syndicates/service.py:133` (create_case) → العملية كاملة تفشل لتينانت 1 و16.
- **يعني عمليًا:** لتينانت 1 و16، كل تدفق تجاري يولّد فاتورة إما يفشل كليًا أو يفقد الفاتورة بصمت ويسمم الجلسة.

---

## الخطوة 2 — التشخيص (بانتظار الموافقة)

### 2.1 الحالة المؤكدة

- tenant 1: **ما زال مقفولًا دائمًا** (نفس الحالة الأصلية بالضبط: count=14، الرقم 15 على id=17).
- tenant 16: **مقفول دائمًا أيضًا** (اكتشاف جديد).
- tenant 15: سليم الآن (صفر فواتير)، معرض للخطر.
- **2 من 3 تينانتات مقفولة؛ 100% من التينانتات التي لديها فواتير.**

### 2.2 خيارات الإصلاح

#### الخيار A — `MAX(seq)+1` (بلا migration)

```python
async def _generate_invoice_number(self, tenant_id: int) -> str:
    max_seq = await self.repo.get_max_invoice_seq(tenant_id)  # الاستعلام في 1.4
    return f"INV-{tenant_id}-{str((max_seq or 0) + 1).zfill(6)}"
```

- ✅ يفك القفل فورًا لتينانت 1 و16 دون أي تعديل بيانات أو migration.
- ✅ تغيير صغير (دالة + method repo).
- ❌ race تحت التزامن: طلبان متزامنان يقرآن نفس MAX → الثاني يفشل بـIntegrityError (**عابر** لا دائم، لكنه يسمم الجلسة كما في 1.6).
- ❌ يعيد استخدام رقم آخر فاتورة إذا حُذفت هي تحديدًا (حذف INV-1-000015 → الفاتورة التالية تأخذ 15 مجددًا) — سيئ محاسبيًا/تدقيقيًا.
- ⚠️ يمكن جعله آمنًا تحت التزامن بإضافة `pg_advisory_xact_lock(hashtext('invoice_seq'), tenant_id)` قبل القراءة — القفل يُحرَّر عند `commit()` الموجود في `repo.create_invoice`. لكن يبقى عيب إعادة استخدام الرقم.

#### الخيار B — Postgres SEQUENCE (migration 068)

**B1: sequence عالمي واحد** (`invoice_number_seq`)، الرقم = `INV-{tenant}-{nextval}`:
- ✅ آمن تمامًا تحت التزامن، لا يعيد أي رقم أبدًا، migration بسيطة (`CREATE SEQUENCE ... ; SELECT setval(..., 15)` = أعلى seq عالمي).
- ❌ الأرقام غير متتالية per-tenant (tenant 1 قد يأخذ 16 ثم 19 ثم 22...). غير قابل للـrollback (فجوات عند أي فشل).

**B2: sequence لكل tenant** (`invoice_seq_t{id}`):
- ✅ متتالي تقريبًا per-tenant وآمن تحت التزامن.
- ❌ يتطلب DDL ديناميكي من كود التطبيق (CREATE SEQUENCE عند أول فاتورة/إنشاء تينانت) + أسماء كائنات ديناميكية + صعوبة في الـmigrations/الاختبارات. **لا أوصي به.**

#### الخيار C (توصيتي) — جدول عداد per-tenant (migration 068)

```sql
CREATE TABLE invoice_number_counters (
    tenant_id INTEGER PRIMARY KEY REFERENCES academy_tenants(id) ON DELETE CASCADE,
    last_seq  INTEGER NOT NULL
);
-- seed من البيانات الحالية:
INSERT INTO invoice_number_counters (tenant_id, last_seq)
SELECT tenant_id, MAX(split_part(invoice_number,'-',3)::int)
FROM invoices WHERE invoice_number ~ ('^INV-' || tenant_id || '-[0-9]+$')
GROUP BY tenant_id;
```

```python
# في _generate_invoice_number:
INSERT INTO invoice_number_counters (tenant_id, last_seq) VALUES (:t, 1)
ON CONFLICT (tenant_id) DO UPDATE SET last_seq = invoice_number_counters.last_seq + 1
RETURNING last_seq;
```

- ✅ آمن تحت التزامن (قفل صف عبر UPSERT؛ المتزامن ينتظر حتى `commit()` في `repo.create_invoice` — قفل قصير).
- ✅ **لا يعيد رقمًا أبدًا** حتى لو حُذفت الفواتير (العداد مستقل عن جدول invoices).
- ✅ متتالي per-tenant و**transactional**: إذا فشلت المعاملة يُسترجَع الرقم (بلا فجوات من الفشل — ميزة محاسبية حقيقية مقابل B).
- ✅ يتعامل مع التينانتات الجديدة تلقائيًا (ON CONFLICT).
- ❌ يحتاج migration + جدول جديد + seed.
- ⚠️ القفل على صف العداد يُحمَل حتى commit معاملة المستدعي. بما أن `repo.create_invoice` يعمل commit فورًا بعد الـinsert، القفل قصير. خطر deadlock نظري فقط إذا مستدعٍ ما يحجز قفلًا آخر ثم يولّد فاتورتين بترتيب مختلف — لم أجد ذلك.

#### ملخص المقارنة

| | A: MAX+1 | A+advisory lock | B1: SEQUENCE عالمي | C: جدول عداد |
|---|---|---|---|---|
| يفك القفل الدائم | ✅ | ✅ | ✅ | ✅ |
| آمن تحت التزامن | ❌ | ✅ | ✅ | ✅ |
| لا يعيد رقمًا محذوفًا | ❌ | ❌ | ✅ | ✅ |
| متتالي per-tenant | ✅ | ✅ | ❌ | ✅ |
| بلا فجوات من الفشل | ✅ | ✅ | ❌ | ✅ |
| migration | لا | لا | 068 | 068 |

**توصيتي: C.** إن أردت أقل تغيير ممكن بلا migration: A + advisory lock (مع قبول إعادة استخدام آخر رقم عند حذفه).

### 2.3 خطة التحقق الحي

**قبل الإصلاح (إثبات الفشل):**
1. اختبار على **تينانت throwaway** (إنشاء صف `academy_tenants` جديد — الأعمدة الإلزامية فقط: name، domain، admin_id) + seed صفوف مباشرة: `INV-T-000001` و`INV-T-000003` (فجوة عند 2) → `create_invoice(entity_id=T)` يولّد `INV-T-000003` → **IntegrityError**. نكرره مرتين لإثبات أنه دائم لا عابر.
2. تأكيد للقراءة فقط على tenant 1 و16: استدعاء `_generate_invoice_number` داخل معاملة تُعمل rollback، والتأكد أن الناتج موجود في الجدول (بلا أي insert حقيقي على بيانات حقيقية).

**بعد الإصلاح:**
3. نفس اختبار الـthrowaway → ينجح برقم `INV-T-000004` (أي max+1، لا count+1).
4. **لا إعادة استخدام** (C/B1): إنشاء فاتورة، حذفها، إنشاء أخرى → رقم جديد لا يساوي المحذوف.
5. **اختبار تزامن** (C أو A+lock أو B1): 10 استدعاءات `create_invoice` متوازية بـ`asyncio.gather` كل منها **بجلسة DB مستقلة** (لا جلسة مشتركة — درس `projects/service.py`) → صفر أخطاء، 10 أرقام مختلفة، ولـC: متتالية بلا فجوات.
6. **rollback** (C فقط): توليد رقم داخل معاملة تُعمل rollback → الاستدعاء التالي يأخذ نفس الرقم (إثبات عدم وجود فجوات).
7. للـmigration: التحقق أن الـseed أعطى tenant 1 → 15، tenant 16 → 4، ثم `alembic downgrade -1` / `upgrade head` نظيف.
8. تحقق read-only نهائي لتينانت 1 و16: الرقم التالي المحسوب = `INV-1-000016` و`INV-16-000005` (غير موجودين).
9. regression: تشغيل اختبارات invoicing + المستدعين الموجودين (`test_ai_agents_execute_action`، `test_realestate_*`، `test_tenders_auctions_*`، `test_financeservice_tenant_binding_fix`، `test_trigger_renewals_*`) ومقارنتها بخط الأساس قبل الإصلاح (مع استثناء فشل "Backlog #8" المعروف مسبقًا).
10. تنظيف: حذف صفوف الـthrowaway (فواتير + عداد + تينانت) في `finally` — مع ملاحظة أن حذف فواتير الـthrowaway لم يعد خطرًا بعد الإصلاح C.

### 2.4 ملاحظات جانبية (لا إصلاح هنا)

- فهرس فريد مكرر على `invoice_number` (constraint + index) — backlog منخفض.
- اختبار `test_ai_agents_execute_action.py` يتجاوز `create_invoice` بـ`_noop_create_invoice_for_isolation` بسبب هذا البند تحديدًا — بعد الإصلاح يمكن إزالة التجاوز (جلسة منفصلة، بموافقة).
- مسار `create_invoice` في المستدعين الـ`try/except` يترك الجلسة مسمومة عند أي IntegrityError — مشكلة عامة مستقلة (savepoint)، خارج النطاق.

---

### 2.5 ما سيتغير في الكود حسب كل خيار (للعلم — لم يُنفَّذ شيء)

| الملف | A | A+lock | B1 | C |
|---|---|---|---|---|
| `invoicing/service.py` (`_generate_invoice_number`) | تعديل | تعديل | تعديل | تعديل |
| `invoicing/repository.py` (method جديدة) | `get_max_invoice_seq` | + advisory lock | `next_invoice_seq` | `next_invoice_seq` (UPSERT) |
| `invoicing/models.py` | — | — | — | model جديد `InvoiceNumberCounter` |
| `migrations/versions/068_...py` | — | — | CREATE SEQUENCE + setval | CREATE TABLE + seed |
| اختبار جديد `tests/test_invoicing_invoice_number_*.py` | نعم | نعم | نعم | نعم |
| `count_invoices` | يبقى (قد يُستخدم في مكان آخر — سأتحقق) | يبقى | يبقى | يبقى |

### 2.6 المخاطر والتراجع

- **A / A+lock:** بلا migration → التراجع = `git revert` فقط.
- **B1 / C:** التراجع = `alembic downgrade -1` + `git revert`. البيانات الحالية في `invoices` **لا تُمس** في أي خيار (لا update ولا delete على الصفوف القائمة).
- **C تحديدًا:** إذا وُجد مستدعٍ يولّد فاتورتين داخل معاملة واحدة لتينانتين مختلفين بترتيب متعاكس مع معاملة أخرى → خطر deadlock نظري. بحثت ولم أجد هذا النمط.
- **كل الخيارات:** الإصلاح يفك القفل لتينانت 1 و16 فورًا بعد النشر، بلا حاجة لتعديل بيانات يدويًا.

---

## نموذج الرد (املأ وأرسل)

**س1 — أي خيار؟** (ضع ✅ أمام واحد)
- [ ] A — MAX+1 بلا migration
- [ ] A+lock — MAX+1 مع `pg_advisory_xact_lock` بلا migration
- [ ] B1 — SEQUENCE عالمي (migration 068)
- [ ] C — جدول عداد per-tenant (migration 068) ← **موصى به**
- [ ] غير ذلك: ______

**س2 — مكان اختبار "قبل الإصلاح":**
- [ ] tenant throwaway فقط + تحقق read-only (rollback) على 1 و16 ← **موصى به**
- [ ] استدعاء حقيقي على tenant 1 (يفشل، لا يكتب بيانات، لكن يستهلك قيمة من `invoices_id_seq`)

**س3 — اختبار التزامن:**
- [ ] 10 استدعاءات متوازية بجلسات مستقلة ← **موصى به**
- [ ] عدد آخر: ______
- [ ] بدونه (مقبول فقط مع الخيار A)

**س4 — البنود الجانبية (2.4):**
- [ ] وثّقها كـbacklog فقط، لا إصلاح الآن ← **موصى به**
- [ ] أزل أيضًا تجاوز `_noop_create_invoice_for_isolation` في `test_ai_agents_execute_action.py` ضمن هذه الجلسة

**س5 — ملاحظات إضافية:**
______

---

**⏸ متوقف هنا بانتظار قرار المستخدم. صفر تعديل على الكود حتى الآن.**

---

## رد المستخدم (مُسجَّل)

- س1: **C** — جدول عداد per-tenant (migration 068). السبب: عدم إعادة استخدام الرقم متطلب محاسبي حقيقي، والسلوك transactional بلا فجوات ميزة حقيقية على SEQUENCE.
- س2: tenant throwaway + تحقق read-only (rollback) على 1 و16.
- س3: 10 استدعاءات متزامنة بجلسات مستقلة.
- س4: backlog فقط. **ممنوع** إزالة `_noop_create_invoice_for_isolation` في هذه الجلسة — يُوثَّق كبند متابعة.
- س5: (1) الفهرس الفريد المكرر → backlog. (2) تأكيد `alembic current` = 067 قبل كتابة 068. (3) عرض محتوى ملف الـmigration حرفيًا (upgrade و downgrade) قبل تشغيله.

---

## الخطوة 3 — التحقق المسبق + إثبات الفشل قبل الإصلاح

### 3.1 حالة alembic (طلب س5-2)

```
$ alembic current   → 067_site_legal_clearance (head)
$ alembic heads     → 067_site_legal_clearance (head)
Connecting to: postgresql+asyncpg://eppne:***@127.0.0.1:5435/eppne_v2   (eppne_db — ليس الحاوية الشاردة 5433)
```

- رأس واحد فقط، لا فروع، لا migration قيد التنفيذ من جلسة موازية. آخر ملف في `migrations/versions/` هو 067. → **الرقم 068 آمن.**
- ملاحظة: `alembic.ini:70` ما زال يشير لـ5433 (الحاوية الشاردة)، لكن `migrations/env.py:74` يتجاوزه بـ`DATABASE_URL` من `.env` → 5435. مؤكَّد من سطر الاتصال أعلاه. (مرتبط ببند backlog الحاوية الشاردة الموجود.)

### 3.2 ملف الاختبار الجديد (ملف جديد — صفر تعديل على ملف قائم)

`eppne-backend/tests/test_invoicing_invoice_number_counter.py` — 6 حالات:

| # | الاختبار | ماذا يثبت |
|---|---|---|
| A | `test_gap_from_deleted_invoice_does_not_lock_tenant` | throwaway بأرقام 1،3 (2 "محذوف") → استدعاءان متتاليان يأخذان 4 ثم 5 |
| B | `test_deleting_latest_invoice_does_not_reuse_its_number` | إنشاء 1، حذفه، الإنشاء التالي = 2 (لا 1) |
| C | `test_concurrent_creates_get_distinct_contiguous_numbers` | 10 `create_invoice` بـ`asyncio.gather`، كل واحد بجلسة مستقلة → صفر أخطاء، الأرقام 1..10 بالضبط |
| D | `test_rolled_back_generation_does_not_consume_number` | توليد رقم ثم rollback → الإنشاء التالي يأخذ نفس الرقم |
| E1/E2 | `test_real_tenants_next_number_is_free_readonly[1/16]` | read-only: توليد داخل معاملة ثم rollback، الرقم غير موجود — صفر insert على بيانات حقيقية، صفر استهلاك `invoices_id_seq` |

- fixture محلي `_fresh_pool_per_test` (autouse) يعمل `engine.dispose()` + `redis_client.close()` بعد كل اختبار — نفس سبب `conftest.db` (Windows Proactor: "Event loop is closed"). التشغيل الأول بدونه أعطى أخطاء loop مضللة؛ أُضيف وأُعيد التشغيل.
- التنظيف: `_cleanup` يمسح كل جدول فيه `tenant_id` للتينانت throwaway ثم التينانت نفسه (نفس نمط `test_insurance_review_claim_status_guard.py`).

### 3.3 النتيجة على الكود الحالي (قبل الإصلاح) — **الفشل مُثبَت**

```
FAILED test_gap_from_deleted_invoice_does_not_lock_tenant
       DETAIL: Key (invoice_number)=(INV-171-000003) already exists.
FAILED test_deleting_latest_invoice_does_not_reuse_its_number
       AssertionError: assert 'INV-172-000001' == 'INV-172-000002'      ← إعادة استخدام الرقم المحذوف
FAILED test_concurrent_creates_get_distinct_contiguous_numbers
       AssertionError: 9 failed: [IntegrityError ... Key (invoice_number)=(INV-...-000001) already exists ...]
FAILED test_real_tenants_next_number_is_free_readonly[1]
       AssertionError: INV-1-000015 already exists → tenant 1 permanently locked
FAILED test_real_tenants_next_number_is_free_readonly[16]
       AssertionError: INV-16-000004 already exists → tenant 16 permanently locked
PASSED test_rolled_back_generation_does_not_consume_number            ← متوقع: COUNT+1 لا يستهلك شيئًا أيضًا
5 failed, 1 passed in 267.48s
```

- **التزامن:** 9 من 10 فشلت — أسوأ من المتوقع (ليس race نادر، بل شبه مؤكد تحت أي تزامن).
- **التحقق بعد التشغيل:** صفر تينانتات `REGTEST_INVNUM_%` متبقية؛ tenant 1 = 14 صف / أعلى `INV-1-000015`، tenant 16 = 3 صفوف / أعلى `INV-16-000004` — **بلا أي تغيير**.
- ملاحظة: الاختبار A يفشل من الاستدعاء الأول، لذلك "الاستدعاء الثاني بنفس الفشل" لم يُمرَّن فعليًا في التينانت throwaway؛ ديمومة القفل مُثبتة بدلًا من ذلك بـE1/E2 (حالة حقيقية قائمة منذ 2026-08-18 لتينانت 1).

---

## الخطوة 4 — المسودة الحرفية للمراجعة (لم يُكتب أي ملف منها بعد، ولم يُشغَّل شيء)

### 4.1 ملف جديد: `eppne-backend/migrations/versions/068_invoice_number_counters.py` (المحتوى الحرفي الكامل)

```python
# migrations/versions/068_invoice_number_counters.py
from alembic import op
import sqlalchemy as sa

revision = '068_invoice_number_counters'
down_revision = '067_site_legal_clearance'

# جدول عداد per-tenant لـinvoice_number بدل COUNT(*)+1 (اللي بيقفل التينانت للأبد
# لو اتحذفت أي فاتورة مش الأخيرة — tenant 1 و16 مقفولين حاليًا). الـseed بياخد أعلى
# seq موجود فعلًا لكل تينانت من invoice_number نفسه (مش COUNT) — الصيغة
# INV-{tenant_id}-{seq}، والـregex بيتجاهل أي صف بصيغة مختلفة (صفر صفوف حاليًا).
# صفر لمس على صفوف invoices الموجودة.


def upgrade() -> None:
    op.create_table(
        'invoice_number_counters',
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('academy_tenants.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('last_seq', sa.Integer(), nullable=False),
        sa.CheckConstraint('last_seq >= 0', name='check_invoice_number_counters_last_seq_non_negative'),
    )
    op.execute(
        """
        INSERT INTO invoice_number_counters (tenant_id, last_seq)
        SELECT tenant_id, MAX(split_part(invoice_number, '-', 3)::int)
        FROM invoices
        WHERE invoice_number ~ ('^INV-' || tenant_id || '-[0-9]+$')
        GROUP BY tenant_id
        """
    )


def downgrade() -> None:
    op.drop_table('invoice_number_counters')
```

- **ناتج الـseed المتوقع** (من استعلام 1.2): `(1, 15)` و`(16, 4)`. tenant 15 بلا صف (يُنشأ تلقائيًا عند أول فاتورة).
- **downgrade:** يحذف الجدول فقط. صفوف `invoices` لا تتأثر في الاتجاهين. بعد downgrade يعود الكود القديم (إن أُرجع) لـCOUNT+1 بنفس القفل — أي أن downgrade بدون `git revert` للكود سيكسر `create_invoice` (الجدول مفقود)، لذلك الاثنان معًا دائمًا.

### 4.2 تعديل: `eppne-backend/app/domains/invoicing/models.py` (إضافة في نهاية الملف، صفر تغيير على `Invoice`)

```diff
     def __repr__(self):
         return f"<Invoice {self.invoice_number} | {self.status.value} | {self.amount} {self.currency}>"
+
+
+class InvoiceNumberCounter(Base):
+    """آخر seq صادر لـinvoice_number لكل تينانت — مستقل عن صفوف invoices، فحذف
+    فاتورة لا يعيد استخدام رقمها أبدًا (migration 068)."""
+    __tablename__ = "invoice_number_counters"
+    __table_args__ = (
+        CheckConstraint("last_seq >= 0", name="check_invoice_number_counters_last_seq_non_negative"),
+    )
+
+    tenant_id = Column(Integer, ForeignKey("academy_tenants.id", ondelete="CASCADE"), primary_key=True)
+    last_seq = Column(Integer, nullable=False)
```

(كل الـimports المطلوبة — `CheckConstraint`, `ForeignKey`, `Integer` — موجودة أصلًا في الملف.) السبب: إبقاء الـmetadata متطابقًا مع الـDB حتى لا يقترح أي `alembic --autogenerate` مستقبلي حذف الجدول.

### 4.3 تعديل: `eppne-backend/app/domains/invoicing/repository.py`

```diff
 from sqlalchemy.ext.asyncio import AsyncSession
-from sqlalchemy import select, update, delete, func, and_, or_
+from sqlalchemy import select, update, delete, func, and_, or_, text
```

```diff
     async def count_invoices(self, tenant_id: int) -> int:
         result = await self.db.execute(
             select(func.count()).where(Invoice.tenant_id == tenant_id)
         )
         return result.scalar() or 0
 
+    async def next_invoice_seq(self, tenant_id: int) -> int:
+        # قفل صف العداد (ON CONFLICT DO UPDATE) بيسلسل الاستدعاءات المتزامنة لنفس التينانت
+        # لحد commit() في create_invoice. GREATEST مع MAX(seq) الفعلي بيغطي تينانت بلا صف
+        # عداد لكن عنده فواتير (مُدرجة مباشرة) — بلا ما يرجع أبدًا لرقم أقل من آخر رقم صادر.
+        result = await self.db.execute(
+            text("""
+                INSERT INTO invoice_number_counters (tenant_id, last_seq)
+                SELECT :tenant_id, COALESCE(MAX(split_part(invoice_number, '-', 3)::int), 0) + 1
+                FROM invoices
+                WHERE tenant_id = :tenant_id AND invoice_number ~ ('^INV-' || tenant_id || '-[0-9]+$')
+                ON CONFLICT (tenant_id) DO UPDATE
+                    SET last_seq = GREATEST(invoice_number_counters.last_seq + 1, EXCLUDED.last_seq)
+                RETURNING last_seq
+            """),
+            {"tenant_id": tenant_id},
+        )
+        return result.scalar_one()
```

### 4.4 تعديل: `eppne-backend/app/domains/invoicing/service.py:115-119`

```diff
     async def _generate_invoice_number(self, tenant_id: int) -> str:
         prefix = "INV"
-        count = await self.repo.count_invoices(tenant_id)
-        seq = str(count + 1).zfill(6)
+        seq = str(await self.repo.next_invoice_seq(tenant_id)).zfill(6)
         return f"{prefix}-{tenant_id}-{seq}"
```

- `count_invoices` يصبح بلا مستدعين (الوحيد كان هنا) — **أتركه** (صفر حذف خارج النطاق)، يُذكر كملاحظة.
- ⚠️ `service.py` فيه أصلًا hunk غير مُلتزَم وغير مرتبط (`process_overdue_invoices`، ~سطر 295، تعديل 2026-09-09). تعديلي hunk منفصل عند سطر 115 → عند الـcommit لاحقًا يلزم hunk-split + التحقق بـ`git show --stat` (نفس درس الجلسات السابقة).

### 4.5 قرار تصميم يحتاج انتباهك: `GREATEST(counter + 1, MAX + 1)`

- **لماذا ليس UPSERT بسيط (`VALUES (:t, 1)`)؟** لأن أي تينانت عنده فواتير لكن بلا صف عداد (فواتير مُدرجة مباشرة بـSQL، أو من اختبار، أو تينانت نشأت فواتيره بين تشغيل الـmigration ونشر الكود) كان سيأخذ الرقم 1 → تصادم = نفس القفل من جديد. الاختبار A يمرّن هذه الحالة تحديدًا.
- **هل يعيد هذا المشكلة الأصلية (إعادة الاستخدام)؟** لا — `last_seq + 1` دائمًا أكبر من كل رقم صدر عبر العداد، و`GREATEST` لا يمكن أن يعطي أقل منه. `MAX` يرفع العداد فقط، لا يخفضه أبدًا.
- **التزامن:** استعلام `MAX` قد يرى snapshot قديمًا قبل انتظار القفل، لكنه لا يُستخدم إلا إذا كان أكبر من العداد المحدَّث → أمان كامل. أول إدراج متزامن لتينانت جديد: الثاني ينتظر على المفتاح الأساسي ثم ينفذ `DO UPDATE` على الصف الملتزَم.
- **التكلفة:** استعلام `MAX` على `invoices` مقيد بـ`tenant_id` (مفهرس `ix_invoices_tenant_id`) — مهمل على الحجم الحالي (17 صفًا).

### 4.6 خطة التنفيذ بعد موافقتك (بالترتيب)

1. كتابة ملف 068 كما في 4.1 حرفيًا.
2. `alembic upgrade head` → التحقق: `SELECT * FROM invoice_number_counters` = `(1,15),(16,4)`.
3. `alembic downgrade -1` → الجدول محذوف، `alembic current` = 067 → `alembic upgrade head` مرة أخرى (اختبار التراجع النظيف).
4. تطبيق 4.2 + 4.3 + 4.4.
5. تشغيل `test_invoicing_invoice_number_counter.py` → المتوقع 6/6 passed.
6. mutation check: إرجاع 4.4 مؤقتًا لـCOUNT+1 → يجب أن يعود الفشل (ثم استعادة الإصلاح).
7. regression: `test_ai_agents_execute_action`، `test_realestate_*`، `test_tenders_auctions_*`، `test_financeservice_tenant_binding_fix`، `test_trigger_renewals_*`، `test_insurance_review_claim_status_guard` — مقارنة بخط أساس أشغّله **قبل** الخطوة 4.
8. التحقق النهائي: tenant 1/16 صفوف الفواتير بلا تغيير، والعداد `(1,15),(16,4)` لم يتحرك (اختبارات E تعمل rollback)، صفر throwaway متبقٍ.
9. تحديث هذا التقرير + backlog. لا staging/commit/PROGRESS_LOG إلا بموافقة منفصلة.

### 4.7 بنود backlog جديدة (توثيق فقط، لا إصلاح)

1. **`invoices-invoice-number-duplicate-unique-index`** — `invoices_invoice_number_key` (constraint) + `ix_invoices_invoice_number` (index) على نفس العمود؛ زائد، أولوية منخفضة، migration منفصلة إن نُفِّذ.
2. **`ai-agents-test-noop-create-invoice-workaround-removable`** — `tests/test_ai_agents_execute_action.py:344` (`_noop_create_invoice_for_isolation`) أُضيف بسبب هذا البند تحديدًا؛ بعد الإصلاح يمكن إزالته — جلسة منفصلة بموافقة (قرار المستخدم س4).
3. **`invoicing-create-invoice-callers-session-poisoning`** — المستدعون الذين يبتلعون `IntegrityError` بـ`try/except` بلا savepoint يتركون الجلسة في `PendingRollbackError`؛ عام ومستقل عن الترقيم.
4. **`invoicing-count-invoices-now-unused`** — `repository.count_invoices` بلا مستدعين بعد الإصلاح؛ منخفض جدًا.
5. **`alembic-ini-points-to-stray-container`** — `alembic.ini:70` يشير لـ5433؛ غير مؤثر لأن env.py يتجاوزه، لكنه فخ إن فشل تحميل `.env`. مرتبط ببند الحاوية الشاردة.

---

**⏸ متوقف: بانتظار موافقتك على (أ) محتوى ملف 068 الحرفي في 4.1، (ب) تعديلات 4.2–4.4، (ج) قرار GREATEST في 4.5. لم يُكتب أي ملف إنتاج ولم تُشغَّل أي migration.**

---

## رد المستخدم الثاني (مُسجَّل)

موافقة على الثلاثة: (أ) 068 كما هو، مع توثيق شرط اقتران downgrade بـrevert الكود داخل الملف. (ب) 4.2–4.4، وإبقاء `count_invoices`. (ج) `GREATEST`. + تسجيل ملاحظة الـhunk-split لـ`service.py` في ملاحظات الـcommit. تنفيذ 4.6 (1–9) ثم عرض التقرير قبل أي staging/commit.

---

## الخطوة 5 — التنفيذ والتحقق (4.6 خطوة بخطوة)

### 5.1 ملف 068 (خطوة 1)

- كُتب `eppne-backend/migrations/versions/068_invoice_number_counters.py` حرفيًا كما في 4.1، **مع إضافة واحدة فقط** (طلبك): فقرة تحذير في تعليق رأس الملف:

```python
# تحذير downgrade: InvoicingRepository.next_invoice_seq بيعتمد على الجدول ده — downgrade
# من غير revert لكود invoicing (service._generate_invoice_number + repository.next_invoice_seq
# + models.InvoiceNumberCounter) بيكسر create_invoice بالكامل (relation does not exist).
# الاتنين لازم يترجعوا مع بعض دايمًا.
```

- `upgrade()` و`downgrade()` مطابقتان حرفيًا لـ4.1 — صفر تغيير.

### 5.2 upgrade + التحقق من الـseed + جولة downgrade/upgrade (خطوات 2–3)

```
== upgrade
Running upgrade 067_site_legal_clearance -> 068_invoice_number_counters
alembic current → 068_invoice_number_counters (head)
invoice_number_counters → (1, 15), (16, 4)            ✅ مطابق للمتوقع
== downgrade -1
Running downgrade 068_invoice_number_counters -> 067_site_legal_clearance
alembic current → 067_site_legal_clearance
to_regclass('invoice_number_counters') → NULL        ✅ الجدول محذوف نظيفًا
== upgrade head (مرة ثانية)
Running upgrade 067_site_legal_clearance -> 068_invoice_number_counters
alembic current → 068_invoice_number_counters (head)
invoice_number_counters → (1, 15), (16, 4)            ✅ seed قابل للتكرار
invoices: tenant 1 = 14 صف / INV-1-000015، tenant 16 = 3 صفوف / INV-16-000004   ✅ بلا تغيير
```

الـDB الآن على **068 (head)**.

### 5.3 خط أساس الـregression (قبل تطبيق الكود — خطوة 7 "قبل")

شُغِّل على الكود **غير المُعدَّل** (بعد الـmigration، والكود القديم لا يستخدم الجدول): **25 passed, 2 failed, 1 xfailed** (336s).

### 5.4 تطبيق الكود (خطوة 4)

طُبِّقت 4.2 و4.3 و4.4 **حرفيًا** كما عُرضت — صفر انحراف. `git diff --stat` لملفاتي:

```
models.py      | 14 +++++++++++++-     (إضافة InvoiceNumberCounter في نهاية الملف؛ السطر "-" هو newline نهاية الملف فقط)
repository.py  | 20 +++++++++++++++++++-   (import text + next_invoice_seq)
service.py     | hunk واحد عند سطر 114-118 (سطران → سطر)
```

### 5.5 الاختبارات الجديدة بعد الإصلاح (خطوة 5) — **6/6**

```
PASSED test_gap_from_deleted_invoice_does_not_lock_tenant
PASSED test_deleting_latest_invoice_does_not_reuse_its_number
PASSED test_concurrent_creates_get_distinct_contiguous_numbers
PASSED test_rolled_back_generation_does_not_consume_number
PASSED test_real_tenants_next_number_is_free_readonly[1]
PASSED test_real_tenants_next_number_is_free_readonly[16]
6 passed in 894.92s
```

- أثناء التشغيل (لقطة `pg_stat_activity`): عداد تينانت التزامن throwaway (id=180) = **10** → الاستدعاءات العشرة أخذت 1..10 بالضبط. صفر انتظار أقفال؛ البطء (15 دقيقة مقابل 4.5 قبل الإصلاح) سببه `_cleanup` الذي يمسح كل جدول فيه `tenant_id` جدولًا جدولًا مع savepoints (الآن 10 فواتير + 10 audit + أحداث لكل اختبار بدل صفر) — ليس في كود الإنتاج.

### 5.6 mutation check (خطوة 6)

- أُرجع 4.4 مؤقتًا لـ`count_invoices() + 1` (مع بقاء الجدول والـrepository كما هما):

```
FAILED test_gap_from_deleted_invoice_does_not_lock_tenant
FAILED test_deleting_latest_invoice_does_not_reuse_its_number
FAILED test_concurrent_creates_get_distinct_contiguous_numbers     (9 failed: IntegrityError ...)
FAILED test_real_tenants_next_number_is_free_readonly[1]
FAILED test_real_tenants_next_number_is_free_readonly[16]
PASSED test_rolled_back_generation_does_not_consume_number
5 failed, 1 passed
```

- **مطابق تمامًا لنتيجة ما قبل الإصلاح (3.3)** → الاختبارات تكشف الخطأ فعلًا.
- ✅ أُعيد الإصلاح فورًا بعدها؛ `git diff service.py` يؤكد: `- count = ... / - seq = str(count + 1)...` → `+ seq = str(await self.repo.next_invoice_seq(tenant_id)).zfill(6)`.

### 5.7 regression بعد الإصلاح (خطوة 7) — **مطابق حرفيًا لخط الأساس**

```
25 passed, 2 failed, 1 xfailed in 997.94s
diff <(baseline PASSED/FAILED | sort) <(after PASSED/FAILED | sort) → IDENTICAL
```

الفشلان (موجودان في خط الأساس، **غير مرتبطين**):

| الاختبار | السبب |
|---|---|
| `test_realestate_insurance_savepoint.py::test_tourism_sports_place_transfer_bid_invoice_ordering` | `AssertionError: TourismSportsService.place_transfer_bid: create_invoice() لازم تكون مُغلَّفة بـtry/except` — فحص ترتيب نصي على الكود المصدري (`assert 1964 < 1629`) |
| `test_realestate_insurance_savepoint.py::test_realestate_buy_fractional_ownership_invoice_ordering` | نفس النوع لـ`RealEstateService.buy_fractional_ownership` (`assert 1277 < 928`) |

كلاهما فحص ثابت (static) لموقع `try` قبل `create_invoice` في كود المستدعي — لا علاقة لهما بالترقيم، ولا يُنفذان `create_invoice` أصلًا. قائمان قبل هذه الجلسة.

> **تصحيح [2026-09-24]:** التخمين السابق هنا ("يُرجَّح ارتباطهما بتعديلات غير مُلتزَمة") **خاطئ**. السبب موثَّق مسبقًا في `PROGRESS_LOG.md:4402` — بند `test-savepoint-fragile-source-position-parsing` [2026-09-17] (دالة الفحص الثابتة تأخذ أول try/except بعد `commit()` لا الخاص بـ`create_invoice`)، مع "حالة ثانية" [2026-09-23] في `:4430` تغطي هذين الاختبارين بالضبط. فشل كاذب؛ الكود الإنتاجي سليم.

### 5.8 التحقق النهائي read-only (خطوة 8)

```
invoices:                 tenant 1 = 14 / INV-1-000015     tenant 16 = 3 / INV-16-000004   ✅ بلا تغيير
invoice_number_counters:  (1, 15), (16, 4)                                                 ✅ لم يتحرك (اختبارات E عملت rollback)
REGTEST_INVNUM_% متبقٍ:   0                                                                ✅
alembic_version:          068_invoice_number_counters                                      ✅
INV-1-000016 / INV-16-000005 موجودان؟  false                                               ✅ الرقم التالي لكل منهما حر
```

**← tenant 1 و16 لم يعودا مقفولين.** أول `create_invoice` حقيقي لكل منهما سيأخذ `INV-1-000016` و`INV-16-000005`.

### 5.9 نطاق التغيير (لا شيء staged)

```
 M eppne-backend/app/domains/invoicing/models.py         ← هذه الجلسة
 M eppne-backend/app/domains/invoicing/repository.py     ← هذه الجلسة
 M eppne-backend/app/domains/invoicing/service.py        ← هذه الجلسة (hunk ~114) + hunk قديم غير مرتبط (~295)
 M eppne-backend/app/domains/invoicing/router.py         ← ليس من هذه الجلسة (تعديل سابق غير مُلتزَم) — لا يُضمَّن
?? eppne-backend/migrations/versions/068_invoice_number_counters.py   ← هذه الجلسة
?? eppne-backend/tests/test_invoicing_invoice_number_counter.py        ← هذه الجلسة
git diff --cached → فارغ (صفر staging)
```

---

## الخطوة 6 — ملاحظات للـcommit (عند موافقتك على الـstaging)

### 6.1 انضباط الـhunk-split (طلبك)

- **`service.py`** يحتوي hunkين:
  1. **~سطر 114–118** (`_generate_invoice_number`) ← **هذه الجلسة، يُضمَّن**.
  2. **~سطر 294–328** (`process_overdue_invoices`، تعديل 2026-09-09 قديم غير مُلتزَم) ← **لا يُضمَّن**.
- الطريقة: stage الـhunk الأول فقط (`git apply --cached` لـpatch يحتوي hunk 114 فقط — `git add -p` تفاعلي غير متاح هنا)، ثم التحقق بـ`git diff --cached eppne-backend/app/domains/invoicing/service.py` (hunk واحد فقط) و`git diff eppne-backend/app/domains/invoicing/service.py` (hunk 295 ما زال unstaged).
- **`router.py`** — لا يُضمَّن إطلاقًا.
- **ممنوع** `git commit -- <pathspec>` على `service.py` (يعيد stage الملف كاملًا ويُدخل hunk 295 — درس الذاكرة).
- بعد الـcommit: `git show --stat HEAD` يجب أن يُظهر **5 ملفات بالضبط**: models.py، repository.py، service.py (±3 أسطر تقريبًا)، 068، ملف الاختبار.

### 6.2 مسودة رسالة الـcommit

```
fix(invoicing): replace COUNT(*)+1 invoice numbering with per-tenant counter table

_generate_invoice_number used COUNT(*)+1, so deleting any non-latest invoice made the
next number collide with an existing one — a permanent duplicate-key lock, not a race.
Tenant 1 (count 14, INV-1-000015 exists) and tenant 16 (count 3, INV-16-000004 exists)
were both permanently unable to create invoices; under concurrency 9/10 creates failed.

- migration 068: invoice_number_counters(tenant_id PK, last_seq), seeded from existing
  MAX(seq) per tenant -> (1,15), (16,4). Downgrade drops the table only; it must be
  paired with a revert of this code (documented in the migration).
- repository.next_invoice_seq: INSERT ... ON CONFLICT DO UPDATE SET
  last_seq = GREATEST(last_seq + 1, MAX(seq) + 1) RETURNING — row lock serializes
  concurrent creates, never reuses a deleted number, rolls back with the transaction.
- models.InvoiceNumberCounter keeps metadata in sync with the DB.
- count_invoices left in place (now unused, backlog).

Note: service.py also carries an unrelated uncommitted hunk (process_overdue_invoices,
~line 295) that is intentionally NOT part of this commit (hunk-split staging).

Tests: new tests/test_invoicing_invoice_number_counter.py 6/6 (pre-fix 5 fail/1 pass,
mutation check reproduces the same 5 failures); regression identical to baseline
(25 passed, 2 pre-existing unrelated static-ordering failures, 1 xfailed).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

### 6.3 بنود backlog النهائية (من 4.7، بلا تغيير) + بند جديد

1. `invoices-invoice-number-duplicate-unique-index` — منخفض.
2. `ai-agents-test-noop-create-invoice-workaround-removable` — `test_ai_agents_execute_action.py:344`، جلسة منفصلة.
3. `invoicing-create-invoice-callers-session-poisoning` — عام.
4. `invoicing-count-invoices-now-unused` — منخفض جدًا.
5. `alembic-ini-points-to-stray-container` — مرتبط ببند الحاوية الشاردة.
6. ~~`realestate-insurance-savepoint-2-static-ordering-failures`~~ — **مُلغى [2026-09-24] بقرار المستخدم: مكرر** لبند قائم `test-savepoint-fragile-source-position-parsing` (`PROGRESS_LOG.md:4402` + "حالة ثانية" `:4430`). نتيجة هذه الجلسة تُذكر فقط كتأكيد مستقل إضافي داخل فقرة الإغلاق.

---

**⏸ متوقف: بانتظار موافقتك على (1) الـstaging بالـhunk-split الموصوف في 6.1، (2) رسالة الـcommit 6.2، (3) كتابة PROGRESS_LOG.md. صفر staging/commit/push حتى الآن.**

---

## رد المستخدم الثالث (مُسجَّل) [2026-09-24]

- تصحيح: بند #6 مكرر لـ`test-savepoint-fragile-source-position-parsing` — لا بند جديد؛ نتيجة الـregression تُذكر كتأكيد مستقل في فقرة الإغلاق.
- موافقة على staging بالـhunk-split (6.1) ورسالة الـcommit (6.2) كما هي.
- stage الملفات الخمسة، عرض `--name-only` و`--stat`، و**انتظار موافقة صريحة قبل `git commit`**.
- صياغة مسودة إدخال PROGRESS_LOG.md في التقرير (لا كتابة) — إغلاق البند + بنود الـbacklog الصحيحة 1–5.

---

## الخطوة 7 — الـstaging (تم) — بانتظار موافقة الـcommit

### 7.1 التحقق المسبق

- `git diff --cached` كان **فارغًا** قبل البدء.
- `git diff models.py repository.py` احتوى **فقط** تعديلات هذه الجلسة (لا hunks قديمة) → آمن لـ`git add` كامل الملف.
- `service.py`: hunkان — `@@ -114,8 +114,7 @@` (هذه الجلسة) و`@@ -295,28 +294,35 @@` (`process_overdue_invoices`، قديم).

### 7.2 الطريقة

```
git diff service.py > service_full.patch
awk: استخراج الـheader + الـhunk الأول فقط → service_hunk114.patch
git apply --cached --check service_hunk114.patch   → OK
git apply --cached service_hunk114.patch           → APPLIED
git add models.py repository.py 068_invoice_number_counters.py test_invoicing_invoice_number_counter.py
```

(لا `git add` على `service.py` ولا على `router.py`؛ لا pathspec commit.)

### 7.3 النتيجة

```
$ git diff --cached --name-only
eppne-backend/app/domains/invoicing/models.py
eppne-backend/app/domains/invoicing/repository.py
eppne-backend/app/domains/invoicing/service.py
eppne-backend/migrations/versions/068_invoice_number_counters.py
eppne-backend/tests/test_invoicing_invoice_number_counter.py

$ git diff --cached --stat
 eppne-backend/app/domains/invoicing/models.py      |  14 +-
 eppne-backend/app/domains/invoicing/repository.py  |  20 ++-
 eppne-backend/app/domains/invoicing/service.py     |   3 +-
 .../versions/068_invoice_number_counters.py        |  39 ++++++
 .../tests/test_invoicing_invoice_number_counter.py | 155 +++++++++++++++++++++
 5 files changed, 227 insertions(+), 4 deletions(-)

$ git diff --cached service.py | grep ^@@    → @@ -114,8 +114,7 @@   (staged: هذه الجلسة فقط)
$ git diff service.py | grep ^@@             → @@ -294,28 +294,35 @@  (unstaged: process_overdue_invoices باقٍ)
router.py في الـindex؟                        → 0   (ما زال unstaged، غير مُضمَّن)
```

✅ 5 ملفات بالضبط، `service.py` = 3 أسطر (سطران حُذفا، سطر أُضيف).

---

## الخطوة 8 — مسودة إدخال PROGRESS_LOG.md (لم يُكتب شيء بعد)

### 8.1 اكتشاف أثناء الصياغة: البند نفسه مُتتبَّع تحت 3 إدخالات أقدم

فحصت PROGRESS_LOG.md لتجنب تكرار خطأ #6، ووجدت أن **نفس الخطأ** موثَّق مسبقًا بأسماء مختلفة (كلها 🔴 مفتوح):

| السطر | الاسم | التاريخ |
|---|---|---|
| `:136` | `invoicing-generate-invoice-number-count-based-collision` | 2026-08-18 |
| `:277` | `invoicing-generate-invoice-number-count-based-collision` (تكرار بنفس الاسم) | 2026-08-29 |
| `:1120` (قسم مستقل) | `invoicing-create-invoice-numbering-collision` — **الشق (أ) فقط** | 2026-09-01 |
| `:1056` | `invoicing-invoice-number-generation-not-deletion-safe-permanent-duplicate-key` (البند الحالي) | 2026-09-23 |

→ فقرة الإغلاق أدناه **تغلق الأربعة معًا** بالإحالة. قسم `:1120` له شق (ب) منفصل (rollback بعد استثناء DB) — **يبقى مفتوحًا**.

### 8.2 اكتشاف ثانٍ: بند backlog #3 مكرر أيضًا

بند #3 المقترح (`invoicing-create-invoice-callers-session-poisoning`) **مكرر** لـ:
- `:135` `invoicing-missing-rollback-on-exception-11b` [2026-08-18] (🔴 أولوية عالية جدًا)، و
- `:1120` الشق (ب) [2026-09-01].

→ **أسقطته** (نفس منطق قرارك في #6). **يتبقى 4 بنود جديدة لا 5**: #1، #2، #4، #5. تحققت أن الأربعة غير موجودة (`grep`: `ix_invoices_invoice_number` / `_noop_create_invoice_for_isolation` / `alembic.ini` / `5433` → صفر نتائج؛ `count_invoices` يظهر فقط داخل وصف الخطأ نفسه).

### 8.3 الموضع

- **4 صفوف backlog جديدة:** تُلحق بجدول الـbacklog بعد آخر صف حالي `tenders-min-increment-no-nonnegative-constraint` (`:1070`).
- **فقرة الإغلاق:** بعد آخر فقرة إغلاق حالية (`:1072`، إغلاق `insurance-review-claim-negative-approved-amount-reverses-transfer`)، بنفس نمط "✅ إغلاق مؤرَّخ".
- `<COMMIT>` = placeholder يُستبدل بالـhash بعد الـcommit.

### 8.4 النص الحرفي — 4 صفوف backlog

```markdown
| — | **`invoices-invoice-number-duplicate-unique-index`** [2026-09-24] — اكتُشف في جلسة `invoicing-invoice-number-sequence-fix` (§1.4): عمود `invoices.invoice_number` عليه قيدا تفرد متطابقان — `invoices_invoice_number_key` (UNIQUE CONSTRAINT من `unique=True`) و`ix_invoices_invoice_number` (UNIQUE INDEX من `Index(..., unique=True)` في `invoicing/models.py:41`). زائد: تكلفة كتابة/تخزين مضاعفة بلا فائدة. صفر أثر وظيفي. الحل: migration منفصلة تحذف أحدهما + إزالة التعريف المقابل من الـmodel. | 🟢 منخفض | `.claude/reports/invoicing-invoice-number-sequence-fix-session-log.md` |
| — | **`ai-agents-test-noop-create-invoice-workaround-removable`** [2026-09-24] — نفس الجلسة (§2.4): `tests/test_ai_agents_execute_action.py:344` (`_noop_create_invoice_for_isolation`) يتجاوز `create_invoice` بـmonkeypatch **بسبب** تصادم ترقيم الفواتير تحديدًا (commit `b4bf356`). بعد إغلاق الترقيم (commit `<COMMIT>`) لم يعد التجاوز ضروريًا لهذا السبب — إزالته تجعل الاختبار يمرّن مسار الفاتورة الحقيقي. **تحفّظ:** قد يظل مطلوبًا جزئيًا بسبب `invoicing-missing-rollback-on-exception-11b` (`:135`) إن فشلت الفاتورة لسبب آخر — يُتحقق عند الإزالة. جلسة منفصلة بموافقة (قرار مستخدم: لا تُزال في جلسة الإصلاح). | 🟢 منخفض | `tests/test_ai_agents_execute_action.py` |
| — | **`invoicing-count-invoices-now-unused`** [2026-09-24] — نفس الجلسة: `InvoicingRepository.count_invoices` (`invoicing/repository.py:117`) بلا أي مستدعٍ بعد استبدال `_generate_invoice_number` بـ`next_invoice_seq` (المستدعي الوحيد كان هو). أُبقي عمدًا (صفر حذف خارج النطاق). | 🟢 منخفض جدًا | `eppne-backend/app/domains/invoicing/repository.py` |
| — | **`alembic-ini-points-to-stray-container`** [2026-09-24] — نفس الجلسة (§3.1): `alembic.ini:70` `sqlalchemy.url` يشير لـ`127.0.0.1:5433` (حاوية `postgres-eppne` اليتيمة، كلمة سر قديمة) لا للقاعدة الحقيقية `eppne_db:5435`. غير مؤثر حاليًا لأن `migrations/env.py:74` يتجاوزه بـ`DATABASE_URL` من `.env` (مؤكَّد من سطر الاتصال: `...@127.0.0.1:5435/eppne_v2`)، لكنه فخ: لو `.env`/`DATABASE_URL` لم يُحمَّل، الـmigrations تُطبَّق بصمت على الحاوية الخطأ. الحل: تصحيح/حذف القيمة في `alembic.ini`، ويُحسم مع قرار الحاوية اليتيمة نفسها. | 🟡 منخفض-متوسط | `eppne-backend/alembic.ini` |
```

### 8.5 النص الحرفي — فقرة الإغلاق

```markdown
**✅ إغلاق مؤرَّخ [2026-09-24] — `invoicing-invoice-number-generation-not-deletion-safe-permanent-duplicate-key`: مُغلَق (commit `<COMMIT>`)، ويُغلِق معه نفس الخطأ المُتتبَّع تحت أسماء أقدم: `invoicing-generate-invoice-number-count-based-collision` (`[2026-08-18]` و`[2026-08-29]` أعلاه) والشق (أ) من `invoicing-create-invoice-numbering-collision` (`[2026-09-01]` أدناه — الشق (ب) الخاص بـrollback بعد استثناء DB يبقى مفتوحًا، وكذلك `invoicing-missing-rollback-on-exception-11b`).** جلسة `invoicing-invoice-number-sequence-fix` (`.claude/reports/invoicing-invoice-number-sequence-fix-session-log.md`). **الحالة الحية قبل الإصلاح:** ليس tenant 1 وحده — **tenant 16 مقفول أيضًا** (count=3، `INV-16-000004` موجود؛ فجوة عند 3)، أي 100% من التينانتات التي لها فواتير (2/2؛ tenant 15 بلا فواتير). مصدر الحذف: تنظيف الاختبارات (`delete(Invoice)` في 5 ملفات)، لا كود التطبيق. **الإصلاح (الخيار C بقرار المستخدم، من بين MAX+1 / MAX+advisory lock / SEQUENCE عالمي / جدول عداد):** migration `068_invoice_number_counters` — جدول `invoice_number_counters(tenant_id PK → academy_tenants ON DELETE CASCADE, last_seq)` مع seed من أعلى seq فعلي لكل تينانت → `(1,15), (16,4)`؛ `InvoicingRepository.next_invoice_seq` بـ`INSERT ... ON CONFLICT DO UPDATE SET last_seq = GREATEST(last_seq + 1, MAX(seq) + 1) RETURNING` — قفل صف يسلسل التزامن، لا يعيد رقمًا محذوفًا أبدًا، transactional (rollback يسترجع الرقم)، و`GREATEST` يغطي تينانت له فواتير بلا صف عداد؛ `models.InvoiceNumberCounter` لتطابق الـmetadata. **downgrade 068 يجب أن يقترن دائمًا بـrevert للكود** (موثَّق داخل ملف الـmigration). **التحقق:** `alembic current` = 067 (رأس واحد) قبل كتابة 068؛ جولة upgrade → downgrade → upgrade نظيفة والـseed متطابق مرتين؛ اختبار جديد `tests/test_invoicing_invoice_number_counter.py` — قبل الإصلاح 5 فشل/1 نجاح (التزامن: 9/10 استدعاءات فشلت بـduplicate key)، بعده **6/6**، وmutation check (إرجاع `count+1` مؤقتًا) أعاد نفس الـ5 فشل بالضبط؛ التحقق على tenant 1 و16 read-only داخل rollback (صفر insert حقيقي، العداد لم يتحرك). **Regression** (7 ملفات، مقارنة بخط أساس على الكود غير المُعدَّل): **25 passed, 2 failed, 1 xfailed — مطابق حرفيًا لخط الأساس**؛ الفشلان (`test_tourism_sports_place_transfer_bid_invoice_ordering`، `test_realestate_buy_fractional_ownership_invoice_ordering`) هما بالضبط حالتا `test-savepoint-fragile-source-position-parsing` (`[2026-09-17]` + "حالة ثانية" `[2026-09-23]`) — **تأكيد مستقل إضافي** أنهما مسبقان وغير مرتبطين بهذا الإصلاح، لا بند جديد. **بعد الإصلاح:** الرقم التالي `INV-1-000016` و`INV-16-000005` (غير موجودين) — التينانتان لم يعودا مقفولين. **الـstaging:** `service.py` كان يحمل hunk قديمًا غير مرتبط (`process_overdue_invoices`، ~295) — hunk-split بـ`git apply --cached`، الـcommit يضم 5 ملفات بالضبط، `router.py` مستبعد. `count_invoices` أُبقي بلا مستدعين (backlog). 4 بنود backlog جديدة أعلاه (`invoices-invoice-number-duplicate-unique-index`، `ai-agents-test-noop-create-invoice-workaround-removable`، `invoicing-count-invoices-now-unused`، `alembic-ini-points-to-stray-container`).
```

### 8.6 سؤال واحد للمستخدم

الإدخالات الثلاثة القديمة (`:136`، `:277`، `:1120`) ما زالت خلاياها تقول 🔴 مفتوح. نمط الإغلاق المتبع سابقًا (مثل `:1041`) = فقرة إغلاق منفصلة **بلا تعديل** الصفوف القديمة. أقترح نفس النمط (فقرة 8.5 فقط، صفر تعديل على الصفوف القديمة). البديل: تعديل خلايا الحالة الثلاث لـ"✅ مُغلَق — راجع إغلاق [2026-09-24]".

---

**⏸ متوقف: (1) الـstaging جاهز (7.3) — بانتظار موافقتك الصريحة على `git commit`. (2) مسودة PROGRESS_LOG.md في 8.4–8.5 — بانتظار موافقتك + قرار 8.6. صفر commit، صفر كتابة على PROGRESS_LOG.md.**

---

## الخطوة 9 — commit الإصلاح + staging التوثيق [2026-09-24]

قرار المستخدم 8.6: فقرة الإغلاق فقط، **صفر تعديل** على الصفوف القديمة (`:136`، `:277`، `:1120`).

### 9.1 commit الإصلاح

```
474d3afa3c28890c442750938bf79242777594db  fix(invoicing): replace COUNT(*)+1 invoice numbering with per-tenant counter table

git show --stat HEAD:
 models.py | 14 +-   repository.py | 20 ++-   service.py | 3 +-
 068_invoice_number_counters.py | 39 +++   test_invoicing_invoice_number_counter.py | 155 +++
 5 files changed, 227 insertions(+), 4 deletions(-)      ✅ 5 ملفات بالضبط
بعد الـcommit: service.py unstaged → @@ -294,28 +294,35 @@ فقط (process_overdue_invoices سليم)؛ الـindex فارغ.
```

### 9.2 staging التوثيق (hunk-only من blob الـHEAD)

- `git show HEAD:PROGRESS_LOG.md` → نسخة (LF)؛ النص من 8.4/8.5 مستخرج حرفيًا من هذا التقرير مع `<COMMIT>` → `474d3af` (مرتان).
- سكربت إدراج واحد طُبِّق على **نسخة الـHEAD** (LF) و**ملف العمل** (CRLF، محفوظ) بنفس المراسي: 4 صفوف بعد صف `tenders-min-increment-no-nonnegative-constraint` (1070)، وسطر فارغ + فقرة الإغلاق بعد إغلاق `insurance-review-claim-negative-...` (1072) — مع assert أن المرساتين فريدتان ومتجاورتان في النسختين.
- `git hash-object -w` + `git update-index --cacheinfo` → الـindex = HEAD + إدراج هذه الجلسة فقط.

```
$ git diff --cached --name-only
PROGRESS_LOG.md

$ git diff --cached --stat
 PROGRESS_LOG.md | 6 ++++++
 1 file changed, 6 insertions(+)          (4 صفوف + سطر فارغ + فقرة إغلاق؛ صفر حذف)

$ git diff --stat PROGRESS_LOG.md         (الباقي unstaged)
 PROGRESS_LOG.md | 671 +++-
 1 file changed, 670 insertions(+), 1 deletion(-)    ✅ مطابق تمامًا لما قبل (670/-1)
```

### 9.3 مسودة رسالة commit التوثيق

```
docs: close invoicing invoice-number permanent duplicate-key lock (474d3af) + 4 backlog items

Closes invoicing-invoice-number-generation-not-deletion-safe-permanent-duplicate-key and
the same bug's older entries (invoicing-generate-invoice-number-count-based-collision
x2, invoicing-create-invoice-numbering-collision part (a)). Regression's 2 failures are
recorded as further confirmation of test-savepoint-fragile-source-position-parsing, not
a new item.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

---

**⏸ متوقف: commit التوثيق staged — بانتظار موافقتك الصريحة. صفر push.**
