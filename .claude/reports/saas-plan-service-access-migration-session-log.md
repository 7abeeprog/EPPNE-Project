# تقرير جلسة — Migration: `saas_plan_service_access` + `service_id` nullable

**تاريخ الجلسة:** 2026-09-07
**النطاق المطلوب (حرفيًا):** migration واحدة بس تعمل: (1) إنشاء جدول
`saas_plan_service_access` many-to-many بين `saas_service_plans` و
`saas_service_catalog`، (2) تعديل `ServicePlan.service_id` (موديل + DB)
ليصبح `nullable=True` بدون حذف العمود. **ممنوع** أي حذف عمود، وممنوع أي
لمس لـ`check_feature_access`/`can_access_service`/أي router في نفس
الـmigration دي. هذا القرار موثَّق مسبقًا في `PROGRESS_LOG.md`
([2026-09-07] — قرار تصميم: توحيد check_feature_access/can_access_service
عبر جدول many-to-many جديد).

---

## 1. الملفات المتأثرة

| الملف | التغيير |
|---|---|
| `eppne-backend/migrations/versions/046_create_saas_plan_service_access.py` | **ملف جديد** — الـmigration نفسها |
| `eppne-backend/app/domains/saas/models.py:37` | `service_id = Column(Integer, ForeignKey("saas_service_catalog.id"), nullable=True, index=True)` — كانت `nullable=False` |

**Chain:** `revision = '046_create_saas_plan_service_access'`،
`down_revision = '045_create_affiliate_scopes_and_unify_commission'` (كان
الـhead الوحيد وقت الكتابة — تأكَّد بـ`alembic heads`).

---

## 2. محتوى الـmigration كامل (منسوخ حرفيًا من الملف الفعلي)

**المسار الكامل:**
`E:\cc\eppne-backend\migrations\versions\046_create_saas_plan_service_access.py`

```python
# migrations/versions/046_create_saas_plan_service_access.py
from alembic import op
import sqlalchemy as sa

revision = '046_create_saas_plan_service_access'
down_revision = '045_create_affiliate_scopes_and_unify_commission'

# قرار تصميم موثَّق في PROGRESS_LOG.md ([2026-09-07] — قرار تصميم: توحيد
# check_feature_access/can_access_service عبر جدول many-to-many جديد):
# استبدال الاعتماد على plan.features (نص حر JSONB بلا schema enforcement)
# لتحديد الخدمات المتاحة لخطة معيّنة، بجدول ربط many-to-many صريح.
#
# هذه الـmigration فقط: إنشاء الجدول الجديد + جعل service_id nullable
# (Expand-Contract، خطوة Expand). صراحة بدون: حذف service_id، بدون أي
# تعديل على check_feature_access/can_access_service أو أي router.


def upgrade() -> None:
    # ========================================================
    # 1. saas_plan_service_access (جديد) — many-to-many بين plan وservice
    # ========================================================
    op.create_table(
        'saas_plan_service_access',
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('service_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['saas_service_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_id'], ['saas_service_catalog.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('plan_id', 'service_id'),
    )
    # index إضافي على service_id لوحده (البحث العكسي: "هل الخدمة دي متاحة
    # عبر أي plan؟") — الـPK المركّب (plan_id, service_id) لا يغطي هذا
    # النمط بكفاءة لأن service_id هو العمود الثاني في الـcomposite index.
    op.create_index(
        'ix_saas_plan_service_access_service_id',
        'saas_plan_service_access', ['service_id'], unique=False,
    )

    # ========================================================
    # 2. saas_service_plans.service_id: NOT NULL → nullable
    #    (Expand-Contract: العمود القديم يفضل موجود ومقروء، الحذف الفعلي
    #    مؤجَّل لـmigration منفصلة بعد تحقق grep إن صفر كود بيستخدمه)
    # ========================================================
    op.alter_column(
        'saas_service_plans', 'service_id',
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'saas_service_plans', 'service_id',
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_index('ix_saas_plan_service_access_service_id', table_name='saas_plan_service_access')
    op.drop_table('saas_plan_service_access')
```

---

## 3. اختبار round-trip — النتيجة: ✅ نجح بالكامل

الخطوات المنفَّذة فعليًا بالترتيب (DB كانت أصلًا على head =
`045_create_affiliate_scopes_and_unify_commission` قبل البدء، تأكَّد
بـ`alembic current`):

1. **`alembic upgrade head`** (045 → 046) — نجح، بدون أي تحذير أو خطأ.
   تحقّق فعلي بعدها عبر استعلام `information_schema`:
   - `saas_service_plans.service_id` → `is_nullable = 'YES'` ✅
   - `saas_plan_service_access` موجود بعمودين (`plan_id`, `service_id`)
     كلاهما `NOT NULL` ✅
   - الـPK: `saas_plan_service_access_pkey` على `(plan_id, service_id)`
     معًا ✅ (تأكَّد من `information_schema.table_constraints` +
     `key_column_usage`)

2. **`alembic downgrade -1`** (046 → 045) — نجح، بدون أي خطأ (لا
   `ForeignKeyViolationError` ولا غيره — متوقَّع لأن الجدول الجديد ماكانش
   فيه أي صفوف بعد، وعمود `service_id` مفيهوش أي قيمة `NULL` فعلية في أي
   صف حالي عشان يمنع الرجوع لـ`NOT NULL`). تحقّق فعلي بعدها:
   - `saas_service_plans.service_id` → `is_nullable = 'NO'` (رجع لأصله) ✅
   - `saas_plan_service_access` → غير موجود في `information_schema.tables`
     (`EXISTS` رجع `False`) ✅

3. **`alembic upgrade head`** (045 → 046 تاني) — نجح تاني بنفس النتائج
   بالضبط زي الخطوة 1. `alembic current` في الآخر أكَّد:
   `046_create_saas_plan_service_access (head)`.

**لا فشل حصل في أي خطوة من الثلاثة.**

---

## 4. ملاحظات ومفاجآت أثناء الكتابة والتنفيذ

1. **تسمية الملف/الـrevision id:** المشروع بيستخدم نمط رقمي متسلسل
   (`045_...`) مش hash-based (زي `71820e4fe1f3_...` القديم من الـinitial
   migration). اتّبعت نفس النمط الرقمي: `046_create_saas_plan_service_access.py`
   مع `revision`/`down_revision` = اسم الملف بالضبط (بدون `.py`) — نفس
   اتفاقية migration 045 السابقة تمامًا.
2. **`alembic current`/`alembic upgrade` بيفشلوا افتراضيًا على Windows
   PowerShell/Git Bash console** بـ`UnicodeEncodeError` عند طباعة رموز
   emoji (`✅`, `⚠️`) اللي مكتوبة صراحة في `migrations/env.py` (كود صفحة
   `cp1256` الافتراضي للـconsole مش UTF-8). الحل: `export
   PYTHONIOENCODING=utf-8` قبل أي أمر alembic. هذا باج بيئة تشغيل (dev
   environment) مش متعلق بمحتوى الـmigration نفسها، ومفيش تعديل تم على
   `env.py` — سُجِّل هنا للتوثيق فقط.
3. **الاسم الفعلي للـFK constraint على `saas_service_plans.service_id`**
   (من الـinitial migration، سطر 371) غير مُسمَّى صراحة → Postgres ولّد
   اسم تلقائي (`saas_service_plans_service_id_fkey`). **لم يكن محتاج لمسه
   في هذه الـmigration** (تغيير `nullable` عبر `alter_column` لا يتطلب
   إعادة تعريف الـFK نفسه)، فذُكر هنا فقط للتوثيق تحسبًا لو migration
   مستقبلية احتاجت اسمه.
4. **قرار غير مطلوب صراحة، اتخذته كحكم هندسي بسيط ضمن حدود المهمة:**
   أضفت `ondelete='CASCADE'` على الـFKين الجديدين في
   `saas_plan_service_access` (بدل الترك بلا `ondelete` → `RESTRICT`
   الافتراضي)، وأضفت index منفرد على `service_id` (`ix_saas_plan_service_access_service_id`)
   للبحث العكسي. المطلوب الأصلي ذكر بس "FK + composite PK" بلا تفاصيل
   `ondelete`/index إضافي — الاثنين دول تفاصيل تنفيذية صغيرة داخل نفس
   الجدول المطلوب، مش توسيع نطاق. **لو الاتجاه التصميمي المفضَّل مختلف
   (مثلاً `RESTRICT` بدل `CASCADE`)، سهل تعديله لاحقًا في migration
   منفصلة قبل ما يبقى فيه بيانات حقيقية في الجدول.**
5. **لا توجد بيانات إنتاج تأثرت:** الجدول الجديد فاضي تمامًا وقت الإنشاء
   (لا seed ولا insert في هذه الـmigration)، وعمود `service_id` في كل
   الصفوف الـ6 الحالية في `saas_service_plans` كانت أصلًا `NOT NULL`
   بقيمة فعلية (راجع
   `.claude/reports/plan-service-mapping-data-audit-session-log.md`) —
   تحويله لـ`nullable=True` توسيع صلاحية العمود بس، لا يغيّر أي قيمة
   موجودة فعليًا.

---

## 5. ما لم يُنفَّذ عمدًا (خارج نطاق هذه الجلسة)

- لا تعديل على `check_feature_access`/`can_access_service` في أي دومين
  من الـ8.
- لا تعديل على أي router.
- لا حذف لعمود `service_id` (مؤجَّل لـmigration منفصلة، بعد تحقق grep
  إن صفر كود بيعتمد عليه — الخطوة "Contract" من استراتيجية
  Expand-Contract الموثَّقة في `PROGRESS_LOG.md`).
- لا إضافة موديل ORM (`class`) جديد في `models.py` يمثّل
  `saas_plan_service_access` — الطلب حدد فقط تعديل `ServicePlan.service_id`
  في الموديل، فاقتصرت عليه.
- لا backfill أو seed لأي بيانات في الجدول الجديد.

**الحالة النهائية لقاعدة البيانات وقت انتهاء الجلسة:** `head` =
`046_create_saas_plan_service_access` (بعد round-trip كامل ناجح).
