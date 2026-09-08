# تقرير جلسة — Migration 047: تعديل ondelete على FKs بتاعة `saas_plan_service_access` من CASCADE لـRESTRICT

**تاريخ الجلسة:** 2026-09-07
**النطاق المطلوب (حرفيًا):** migration واحدة بس (047) تعدّل الـondelete على
الـFKين الموجودين فعليًا في `saas_plan_service_access` (اتعرّفوا في
migration 046 بـ`ondelete='CASCADE'`، راجع بند 4 في
`.claude/reports/saas-plan-service-access-migration-session-log.md`)
لـ`RESTRICT`، عبر `drop_constraint` + `create_foreign_key` بديل (Postgres
مايسمحش بتعديل `ondelete` على FK قائم بـ`ALTER` مباشر). **ممنوع** أي حذف
عمود، وممنوع أي لمس لـ`check_feature_access`/`can_access_service`/أي
router في نفس الـmigration دي.

---

## 1. الملفات المتأثرة

| الملف | التغيير |
|---|---|
| `eppne-backend/migrations/versions/047_saas_plan_service_access_fk_restrict.py` | **ملف جديد** — الـmigration نفسها فقط |

لا تعديل على `app/domains/saas/models.py` ولا أي ملف كود تاني في هذه
الجلسة — الموديل (SQLAlchemy) أصلًا بيعرّف `ServicePlan`/`ServiceCatalog`
بس، ومفيش كلاس ORM لـ`saas_plan_service_access` (لم يُطلب إضافته في جلسة
046 ولا في هذه الجلسة)، فمفيش `ondelete` معرَّف على مستوى الموديل يحتاج
تعديل مقابل.

**Chain:** `revision = '047_saas_plan_service_access_fk_restrict'`،
`down_revision = '046_create_saas_plan_service_access'` (كان الـhead
الوحيد وقت الكتابة — تأكَّد بـ`alembic heads` قبل البدء).

---

## 2. محتوى الـmigration كامل (منسوخ حرفيًا من الملف الفعلي)

**المسار الكامل:**
`E:\cc\eppne-backend\migrations\versions\047_saas_plan_service_access_fk_restrict.py`

```python
# migrations/versions/047_saas_plan_service_access_fk_restrict.py
from alembic import op
import sqlalchemy as sa

revision = '047_saas_plan_service_access_fk_restrict'
down_revision = '046_create_saas_plan_service_access'

# متابعة لـ046: الـFKين على saas_plan_service_access اتعرّفوا هناك بـ
# ondelete='CASCADE' كحكم هندسي مؤقت (راجع بند 4 في
# .claude/reports/saas-plan-service-access-migration-session-log.md).
# هذه الـmigration تعدّل الـondelete بس لـRESTRICT — بدون أي حذف عمود، وبدون
# أي لمس لـcheck_feature_access/can_access_service/أي router.
#
# Postgres لا يسمح بتعديل ondelete على FK قائم عبر ALTER — لازم
# drop_constraint ثم create_foreign_key بديل بنفس الأعمدة بالضبط.
# أسماء القيود الفعلية (auto-generated من create_table في 046، تأكَّدت
# بالاستعلام المباشر على information_schema قبل كتابة هذا الملف):
# saas_plan_service_access_plan_id_fkey و
# saas_plan_service_access_service_id_fkey.


def upgrade() -> None:
    op.drop_constraint(
        'saas_plan_service_access_plan_id_fkey',
        'saas_plan_service_access',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'saas_plan_service_access_plan_id_fkey',
        'saas_plan_service_access', 'saas_service_plans',
        ['plan_id'], ['id'], ondelete='RESTRICT',
    )

    op.drop_constraint(
        'saas_plan_service_access_service_id_fkey',
        'saas_plan_service_access',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'saas_plan_service_access_service_id_fkey',
        'saas_plan_service_access', 'saas_service_catalog',
        ['service_id'], ['id'], ondelete='RESTRICT',
    )


def downgrade() -> None:
    op.drop_constraint(
        'saas_plan_service_access_service_id_fkey',
        'saas_plan_service_access',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'saas_plan_service_access_service_id_fkey',
        'saas_plan_service_access', 'saas_service_catalog',
        ['service_id'], ['id'], ondelete='CASCADE',
    )

    op.drop_constraint(
        'saas_plan_service_access_plan_id_fkey',
        'saas_plan_service_access',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'saas_plan_service_access_plan_id_fkey',
        'saas_plan_service_access', 'saas_service_plans',
        ['plan_id'], ['id'], ondelete='CASCADE',
    )
```

---

## 3. اختبار round-trip — النتيجة: ✅ نجح بالكامل

DB كانت أصلًا على head = `046_create_saas_plan_service_access` قبل
البدء (تأكَّد بـ`alembic current`). الخطوات المنفَّذة فعليًا بالترتيب:

1. **`alembic upgrade head`** (046 → 047) — نجح، بدون أي تحذير أو خطأ.
   تحقّق فعلي بعدها عبر `information_schema.referential_constraints`
   (join مع `table_constraints`/`key_column_usage`/`constraint_column_usage`):

   | constraint_name | column | foreign_table | delete_rule |
   |---|---|---|---|
   | `saas_plan_service_access_plan_id_fkey` | `plan_id` | `saas_service_plans` | **RESTRICT** ✅ |
   | `saas_plan_service_access_service_id_fkey` | `service_id` | `saas_service_catalog` | **RESTRICT** ✅ |

2. **`alembic downgrade -1`** (047 → 046) — نجح، بدون أي خطأ. تحقّق فعلي
   بعدها بنفس الاستعلام أكَّد رجوع الاثنين لـ`delete_rule = 'CASCADE'`
   (زي حالة migration 046 الأصلية).

3. **`alembic upgrade head`** (046 → 047 تاني) — نجح تاني بنفس النتيجة
   بالضبط زي الخطوة 1 (كلا الـconstraint رجعوا `RESTRICT`). `alembic
   current` في الآخر أكَّد: `047_saas_plan_service_access_fk_restrict
   (head)`.

**لا فشل حصل في أي خطوة من الثلاثة.** الجدول كان فاضي طول الوقت (مفيش
صفوف اتضافت في أي جلسة لحد الآن)، فمفيش أي بيانات كان ممكن تتأثر
بـdrop/recreate الـconstraints.

---

## 4. ملاحظات ومفاجآت أثناء الكتابة والتنفيذ

1. **أسماء الـconstraints الفعلية كانت لازم تتأكَّد من الـDB مش تُخمَّن.**
   migration 046 عرَّفت الـFKs عبر `sa.ForeignKeyConstraint(...)` بلا اسم
   صريح — يعني Postgres ولَّد الأسماء تلقائيًا وقت `create_table`.
   استعلمت مباشرة عن `information_schema` **قبل** كتابة migration 047
   للتأكد من الاسمين الحقيقيين: `saas_plan_service_access_plan_id_fkey`
   و`saas_plan_service_access_service_id_fkey` (نمط Postgres القياسي
   `<table>_<column>_fkey`، وده أكَّد صحة الافتراض، لكن مفيش ضمان عام إن
   كل FK بلا اسم صريح هيتبع هذا النمط بالضبط في كل حالة — خصوصًا لو فيه
   أكتر من FK على نفس العمود أو تعارض تسمية).
2. **توضيح دقيق لـ"الـdefault في Postgres" (تصحيح بسيط لصياغة الطلب):**
   الطلب افترض إن حذف `ondelete` خالص "يرجع للـdefault اللي هو RESTRICT
   في Postgres" — الدقة التقنية: **الـdefault الفعلي في Postgres هو
   `NO ACTION`، مش `RESTRICT`** (الاتنين بيمنعوا الحذف لو فيه صفوف مرتبطة
   في نفس اللحظة، لكن `NO ACTION` قابل لـdeferred constraint checking
   جوه transaction واحدة، بينما `RESTRICT` بيتفحص فورًا وميقبلش
   deferring حتى لو الـconstraint اتعرَّف كـ`DEFERRABLE`). بما إن الطلب
   نفسه قدَّم `ondelete='RESTRICT'` الصريح كخيار أول، اخترت الصريح
   (`ondelete='RESTRICT'` في `create_foreign_key`) بدل الاعتماد على
   حذف الـpassing خالص — عشان النية تبقى مكتوبة صراحة في الكود، مش
   متروكة لـdefault ضمني قد يتغيّر تفسيره. **تحقّق فعلي بالاستعلام
   المباشر:** `delete_rule` في `information_schema.referential_constraints`
   رجع فعليًا القيمة الحرفية `'RESTRICT'` (مش `'NO ACTION'`) — يعني
   الاختيار الصريح هو اللي انعكس فعليًا في الـDB، مؤكَّد لا مفترض.
3. **`downgrade()` مكتوبة بترتيب عكسي مضبوط** (drop/recreate
   `service_id` الأول ثم `plan_id`) — عكس ترتيب `upgrade()` بالظبط (اللي
   بدأ بـ`plan_id`). ده مش إجباري وظيفيًا هنا (القيدين مستقلّين عن بعض،
   مفيش تبعية ترتيب بينهم)، لكن اتّبعته كأسلوب دفاعي متسق مع نمط
   migration 045 السابقة (اللي بتعكس ترتيب كل خطوات الـupgrade في
   الـdowngrade بدقة).
4. **مفيش أي بيانات في الجدول طول الجلسة** (تأكَّد: الجدول اتعمله
   upgrade في 046 بلا أي seed، ومفيش أي migration أو كود تاني ضاف له
   صفوف لحد كتابة هذا التقرير) — يعني اختبار الـround-trip هنا بيغطي
   البنية (schema) فقط، مش سلوك الحذف الفعلي (`RESTRICT` بيمنع حذف صف
   مرتبط) تحت بيانات حقيقية. ده متوقَّع ومقبول لأن نطاق المهمة كان تغيير
   الـconstraint نفسه، لا اختبار سلوكه وظيفيًا.

---

## 5. ما لم يُنفَّذ عمدًا (خارج نطاق هذه الجلسة)

- لا حذف لأي عمود.
- لا تعديل على `check_feature_access`/`can_access_service` في أي دومين.
- لا تعديل على أي router.
- لا تعديل على `app/domains/saas/models.py` (مفيش كلاس ORM لهذا الجدول
  أصلًا يحتاج تعديل).
- لا إضافة/حذف أي صف بيانات.

**الحالة النهائية لقاعدة البيانات وقت انتهاء الجلسة:** `head` =
`047_saas_plan_service_access_fk_restrict` (بعد round-trip كامل ناجح،
والـconstraints الاتنين مؤكَّدين `RESTRICT` فعليًا عبر
`information_schema.referential_constraints`).
