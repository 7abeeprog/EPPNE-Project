# migrations/versions/021_add_tenant_id_to_idempotency_records.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '021_add_tenant_id_to_idempotency_records'
down_revision = '020_add_tenant_id_to_maintenance_logs'

def upgrade() -> None:
    op.add_column('idempotency_records', sa.Column('tenant_id', sa.Integer(), nullable=True))

    # ملاحظة: idempotency_records ماعندهاش أي عمود يربطها بـ user أو tenant
    # (key, response_data, expires_at بس). لو الجدول فيه صفوف، الـ migration
    # هتوقف بـ raise بدل قيمة افتراضية عشوائية.
    conn = op.get_bind()
    orphan_count = conn.execute(text(
        "SELECT COUNT(*) FROM idempotency_records WHERE tenant_id IS NULL"
    )).scalar()
    if orphan_count:
        raise RuntimeError(
            f"لا يمكن إكمال الـ migration: {orphan_count} صف في idempotency_records بدون tenant_id قابل للاستنتاج "
            "(لا يوجد عمود ربط بـ user/tenant في هذا الجدول). يتطلب مراجعة يدوية للبيانات قبل المتابعة."
        )

    op.alter_column('idempotency_records', 'tenant_id', nullable=False)
    op.create_index('ix_idempotency_records_tenant_id', 'idempotency_records', ['tenant_id'])
    op.create_foreign_key(
        'fk_idempotency_records_tenant_id',
        'idempotency_records',
        'academy_tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    op.drop_constraint('fk_idempotency_records_tenant_id', 'idempotency_records', type_='foreignkey')
    op.drop_index('ix_idempotency_records_tenant_id', table_name='idempotency_records')
    op.drop_column('idempotency_records', 'tenant_id')
