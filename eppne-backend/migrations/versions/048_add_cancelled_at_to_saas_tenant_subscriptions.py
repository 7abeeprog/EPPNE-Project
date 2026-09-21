# migrations/versions/048_add_cancelled_at_to_saas_tenant_subscriptions.py
from alembic import op
import sqlalchemy as sa

revision = '048_add_cancelled_at_to_saas_tenant_subscriptions'
down_revision = '047_saas_plan_service_access_fk_restrict'

# نطاق ضيق متعمَّد: بناء المرحلة أ فقط من cleanup_cancelled_subscriptions_task
# (تعطيل TenantServiceAccess.is_active بعد 30 يوم من الإلغاء) — راجع
# .claude/reports/cleanup-cancelled-subscriptions-task-fix-session-log.md.
#
# Expand فقط: عمود جديد nullable، بلا backfill لأي اشتراك CANCELLED قديم
# (زي id=50 — تاريخ الإلغاء الحقيقي غير معروف بدقة كافية من updated_at
# وحده). اشتراكات كهذه تفضل cancelled_at=NULL وتُستبعَد صراحةً من أي
# منطق تنظيف يعتمد على العمود ده.


def upgrade() -> None:
    op.add_column(
        'saas_tenant_subscriptions',
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        'ix_saas_tenant_subscriptions_cancelled_at',
        'saas_tenant_subscriptions', ['cancelled_at'], unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_saas_tenant_subscriptions_cancelled_at', table_name='saas_tenant_subscriptions')
    op.drop_column('saas_tenant_subscriptions', 'cancelled_at')
