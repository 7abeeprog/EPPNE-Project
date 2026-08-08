# migrations/versions/022_add_tenant_id_to_iot_request_logs.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '022_add_tenant_id_to_iot_request_logs'
down_revision = '021_add_tenant_id_to_idempotency_records'

def upgrade() -> None:
    op.add_column('iot_request_logs', sa.Column('tenant_id', sa.Integer(), nullable=True))

    op.execute(text("""
        UPDATE iot_request_logs
        SET tenant_id = users.tenant_id
        FROM users
        WHERE iot_request_logs.user_id = users.id
    """))

    conn = op.get_bind()
    orphan_count = conn.execute(text(
        "SELECT COUNT(*) FROM iot_request_logs WHERE tenant_id IS NULL"
    )).scalar()
    if orphan_count:
        raise RuntimeError(
            f"لا يمكن إكمال الـ migration: {orphan_count} صف في iot_request_logs بدون tenant_id قابل للاستنتاج. "
            "يتطلب مراجعة يدوية للبيانات قبل المتابعة."
        )

    op.alter_column('iot_request_logs', 'tenant_id', nullable=False)
    op.create_index('ix_iot_request_logs_tenant_id', 'iot_request_logs', ['tenant_id'])
    op.create_foreign_key(
        'fk_iot_request_logs_tenant_id',
        'iot_request_logs',
        'academy_tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    op.drop_constraint('fk_iot_request_logs_tenant_id', 'iot_request_logs', type_='foreignkey')
    op.drop_index('ix_iot_request_logs_tenant_id', table_name='iot_request_logs')
    op.drop_column('iot_request_logs', 'tenant_id')
