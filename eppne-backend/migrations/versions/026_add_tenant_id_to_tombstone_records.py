# migrations/versions/026_add_tenant_id_to_tombstone_records.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '026_add_tenant_id_to_tombstone_records'
down_revision = '025_add_tenant_id_to_data_erasure_requests'

def upgrade() -> None:
    op.add_column('tombstone_records', sa.Column('tenant_id', sa.Integer(), nullable=True))

    op.execute(text("""
        UPDATE tombstone_records
        SET tenant_id = users.tenant_id
        FROM users
        WHERE tombstone_records.deleted_by_id = users.id
    """))

    conn = op.get_bind()
    orphan_count = conn.execute(text(
        "SELECT COUNT(*) FROM tombstone_records WHERE tenant_id IS NULL"
    )).scalar()
    if orphan_count:
        raise RuntimeError(
            f"لا يمكن إكمال الـ migration: {orphan_count} صف في tombstone_records بدون tenant_id قابل للاستنتاج. "
            "يتطلب مراجعة يدوية للبيانات قبل المتابعة."
        )

    op.alter_column('tombstone_records', 'tenant_id', nullable=False)
    op.create_index('ix_tombstone_records_tenant_id', 'tombstone_records', ['tenant_id'])
    op.create_foreign_key(
        'fk_tombstone_records_tenant_id',
        'tombstone_records',
        'academy_tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    op.drop_constraint('fk_tombstone_records_tenant_id', 'tombstone_records', type_='foreignkey')
    op.drop_index('ix_tombstone_records_tenant_id', table_name='tombstone_records')
    op.drop_column('tombstone_records', 'tenant_id')
