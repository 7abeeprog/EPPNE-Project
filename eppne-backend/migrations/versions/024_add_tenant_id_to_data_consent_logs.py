# migrations/versions/024_add_tenant_id_to_data_consent_logs.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '024_add_tenant_id_to_data_consent_logs'
down_revision = '023_add_tenant_id_to_privacy_settings'

def upgrade() -> None:
    op.add_column('data_consent_logs', sa.Column('tenant_id', sa.Integer(), nullable=True))

    op.execute(text("""
        UPDATE data_consent_logs
        SET tenant_id = users.tenant_id
        FROM users
        WHERE data_consent_logs.user_id = users.id
    """))

    conn = op.get_bind()
    orphan_count = conn.execute(text(
        "SELECT COUNT(*) FROM data_consent_logs WHERE tenant_id IS NULL"
    )).scalar()
    if orphan_count:
        raise RuntimeError(
            f"لا يمكن إكمال الـ migration: {orphan_count} صف في data_consent_logs بدون tenant_id قابل للاستنتاج. "
            "يتطلب مراجعة يدوية للبيانات قبل المتابعة."
        )

    op.alter_column('data_consent_logs', 'tenant_id', nullable=False)
    op.create_index('ix_data_consent_logs_tenant_id', 'data_consent_logs', ['tenant_id'])
    op.create_foreign_key(
        'fk_data_consent_logs_tenant_id',
        'data_consent_logs',
        'academy_tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    op.drop_constraint('fk_data_consent_logs_tenant_id', 'data_consent_logs', type_='foreignkey')
    op.drop_index('ix_data_consent_logs_tenant_id', table_name='data_consent_logs')
    op.drop_column('data_consent_logs', 'tenant_id')
