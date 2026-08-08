# migrations/versions/017_add_tenant_id_to_smart_assets.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '017_add_tenant_id_to_smart_assets'
down_revision = '016_create_invoices_table'

def upgrade() -> None:
    op.add_column('smart_assets', sa.Column('tenant_id', sa.Integer(), nullable=True))

    op.execute(text("""
        UPDATE smart_assets
        SET tenant_id = users.tenant_id
        FROM users
        WHERE smart_assets.owner_id = users.id
    """))

    conn = op.get_bind()
    orphan_count = conn.execute(text(
        "SELECT COUNT(*) FROM smart_assets WHERE tenant_id IS NULL"
    )).scalar()
    if orphan_count:
        raise RuntimeError(
            f"لا يمكن إكمال الـ migration: {orphan_count} صف في smart_assets بدون tenant_id قابل للاستنتاج. "
            "يتطلب مراجعة يدوية للبيانات قبل المتابعة."
        )

    op.alter_column('smart_assets', 'tenant_id', nullable=False)
    op.create_index('ix_smart_assets_tenant_id', 'smart_assets', ['tenant_id'])
    op.create_foreign_key(
        'fk_smart_assets_tenant_id',
        'smart_assets',
        'academy_tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    op.drop_constraint('fk_smart_assets_tenant_id', 'smart_assets', type_='foreignkey')
    op.drop_index('ix_smart_assets_tenant_id', table_name='smart_assets')
    op.drop_column('smart_assets', 'tenant_id')
