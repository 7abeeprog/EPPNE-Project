# migrations/versions/049_insurance_issuer_entity_id_set_null.py
from alembic import op
import sqlalchemy as sa

revision = '049_insurance_issuer_entity_id_set_null'
down_revision = '048_add_cancelled_at_to_saas_tenant_subscriptions'

# Expand فقط — راجع .claude/reports/insurance-entity-membership-gap-fix-session-log.md
# بند 2: issuer_entity_id كان nullable=False + ondelete='CASCADE' (يمسح كل
# بوالص التأمين تلقائيًا لو الكيان المُصدِر اتمسح — خطر بيانات مالية غير
# مقصود لبوليصة قد يكون عليها اشتراكات/مطالبات/مدفوعات تاريخية). التعديل:
# nullable=True + ondelete='SET NULL' — البوليصة تفضل موجودة بسجلها
# التاريخي حتى لو الكيان المُصدِر اتمسح، بس تفقد الإشارة له.
#
# فُحصت البيانات الحالية قبل الكتابة (2026-09-10، DB المحلي للتطوير):
# 9 صفوف حقيقية في insurance_policies، صفر NULL حاليًا في issuer_entity_id
# — التغيير آمن، مفيش أي صف هيتأثر فورًا (الأثر فقط على أي حذف مستقبلي
# للكيان المُصدِر).
#
# Postgres لا يسمح بتعديل ondelete على FK قائم عبر ALTER — لازم
# drop_constraint ثم create_foreign_key بديل بنفس الأعمدة بالضبط. اسم
# القيد الفعلي (اتأكَّد بالاستعلام المباشر على pg_constraint قبل كتابة هذا
# الملف): insurance_policies_issuer_entity_id_fkey.


def upgrade() -> None:
    op.alter_column(
        'insurance_policies', 'issuer_entity_id',
        existing_type=sa.Integer(), nullable=True,
    )
    op.drop_constraint(
        'insurance_policies_issuer_entity_id_fkey',
        'insurance_policies',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'insurance_policies_issuer_entity_id_fkey',
        'insurance_policies', 'sovereign_entities_v2',
        ['issuer_entity_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        'insurance_policies_issuer_entity_id_fkey',
        'insurance_policies',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'insurance_policies_issuer_entity_id_fkey',
        'insurance_policies', 'sovereign_entities_v2',
        ['issuer_entity_id'], ['id'], ondelete='CASCADE',
    )
    op.alter_column(
        'insurance_policies', 'issuer_entity_id',
        existing_type=sa.Integer(), nullable=False,
    )
