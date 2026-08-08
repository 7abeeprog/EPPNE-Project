# migrations/versions/025_add_tenant_id_to_data_erasure_requests.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '025_add_tenant_id_to_data_erasure_requests'
down_revision = '024_add_tenant_id_to_data_consent_logs'

def upgrade() -> None:
    op.add_column('data_erasure_requests', sa.Column('tenant_id', sa.Integer(), nullable=True))

    op.execute(text("""
        UPDATE data_erasure_requests
        SET tenant_id = users.tenant_id
        FROM users
        WHERE data_erasure_requests.user_id = users.id
    """))

    conn = op.get_bind()
    orphan_count = conn.execute(text(
        "SELECT COUNT(*) FROM data_erasure_requests WHERE tenant_id IS NULL"
    )).scalar()
    if orphan_count:
        raise RuntimeError(
            f"لا يمكن إكمال الـ migration: {orphan_count} صف في data_erasure_requests بدون tenant_id قابل للاستنتاج. "
            "يتطلب مراجعة يدوية للبيانات قبل المتابعة."
        )

    op.alter_column('data_erasure_requests', 'tenant_id', nullable=False)
    op.create_index('ix_data_erasure_requests_tenant_id', 'data_erasure_requests', ['tenant_id'])
    op.create_foreign_key(
        'fk_data_erasure_requests_tenant_id',
        'data_erasure_requests',
        'academy_tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    op.drop_constraint('fk_data_erasure_requests_tenant_id', 'data_erasure_requests', type_='foreignkey')
    op.drop_index('ix_data_erasure_requests_tenant_id', table_name='data_erasure_requests')
    op.drop_column('data_erasure_requests', 'tenant_id')
