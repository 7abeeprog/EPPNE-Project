# migrations/versions/020_add_tenant_id_to_maintenance_logs.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '020_add_tenant_id_to_maintenance_logs'
down_revision = '019_add_tenant_id_to_utility_readings'

def upgrade() -> None:
    op.add_column('maintenance_logs', sa.Column('tenant_id', sa.Integer(), nullable=True))

    op.execute(text("""
        UPDATE maintenance_logs
        SET tenant_id = smart_assets.tenant_id
        FROM smart_assets
        WHERE maintenance_logs.asset_id = smart_assets.id
          AND maintenance_logs.tenant_id IS NULL
    """))
    op.execute(text("""
        UPDATE maintenance_logs
        SET tenant_id = utility_grids.tenant_id
        FROM utility_grids
        WHERE maintenance_logs.grid_id = utility_grids.id
          AND maintenance_logs.tenant_id IS NULL
    """))
    op.execute(text("""
        UPDATE maintenance_logs
        SET tenant_id = users.tenant_id
        FROM users
        WHERE maintenance_logs.technician_id = users.id
          AND maintenance_logs.tenant_id IS NULL
    """))

    conn = op.get_bind()
    orphan_count = conn.execute(text(
        "SELECT COUNT(*) FROM maintenance_logs WHERE tenant_id IS NULL"
    )).scalar()
    if orphan_count:
        raise RuntimeError(
            f"لا يمكن إكمال الـ migration: {orphan_count} صف في maintenance_logs بدون tenant_id قابل للاستنتاج. "
            "يتطلب مراجعة يدوية للبيانات قبل المتابعة."
        )

    op.alter_column('maintenance_logs', 'tenant_id', nullable=False)
    op.create_index('ix_maintenance_logs_tenant_id', 'maintenance_logs', ['tenant_id'])
    op.create_foreign_key(
        'fk_maintenance_logs_tenant_id',
        'maintenance_logs',
        'academy_tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    op.drop_constraint('fk_maintenance_logs_tenant_id', 'maintenance_logs', type_='foreignkey')
    op.drop_index('ix_maintenance_logs_tenant_id', table_name='maintenance_logs')
    op.drop_column('maintenance_logs', 'tenant_id')
