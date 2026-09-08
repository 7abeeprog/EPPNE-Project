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
