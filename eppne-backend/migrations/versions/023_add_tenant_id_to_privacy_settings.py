# migrations/versions/023_add_tenant_id_to_privacy_settings.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '023_add_tenant_id_to_privacy_settings'
down_revision = '022_add_tenant_id_to_iot_request_logs'

def upgrade() -> None:
    op.add_column('privacy_settings', sa.Column('tenant_id', sa.Integer(), nullable=True))

    op.execute(text("""
        UPDATE privacy_settings
        SET tenant_id = users.tenant_id
        FROM users
        WHERE privacy_settings.user_id = users.id
    """))

    conn = op.get_bind()
    orphan_count = conn.execute(text(
        "SELECT COUNT(*) FROM privacy_settings WHERE tenant_id IS NULL"
    )).scalar()
    if orphan_count:
        raise RuntimeError(
            f"لا يمكن إكمال الـ migration: {orphan_count} صف في privacy_settings بدون tenant_id قابل للاستنتاج. "
            "يتطلب مراجعة يدوية للبيانات قبل المتابعة."
        )

    op.alter_column('privacy_settings', 'tenant_id', nullable=False)
    op.create_index('ix_privacy_settings_tenant_id', 'privacy_settings', ['tenant_id'])
    op.create_foreign_key(
        'fk_privacy_settings_tenant_id',
        'privacy_settings',
        'academy_tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    op.drop_constraint('fk_privacy_settings_tenant_id', 'privacy_settings', type_='foreignkey')
    op.drop_index('ix_privacy_settings_tenant_id', table_name='privacy_settings')
    op.drop_column('privacy_settings', 'tenant_id')
