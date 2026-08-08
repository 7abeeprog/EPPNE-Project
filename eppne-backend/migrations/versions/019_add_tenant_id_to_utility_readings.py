# migrations/versions/019_add_tenant_id_to_utility_readings.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '019_add_tenant_id_to_utility_readings'
down_revision = '018_add_tenant_id_to_utility_grids'

def upgrade() -> None:
    op.add_column('utility_readings', sa.Column('tenant_id', sa.Integer(), nullable=True))

    op.execute(text("""
        UPDATE utility_readings
        SET tenant_id = smart_assets.tenant_id
        FROM smart_assets
        WHERE utility_readings.asset_id = smart_assets.id
          AND utility_readings.tenant_id IS NULL
    """))
    op.execute(text("""
        UPDATE utility_readings
        SET tenant_id = utility_grids.tenant_id
        FROM utility_grids
        WHERE utility_readings.grid_id = utility_grids.id
          AND utility_readings.tenant_id IS NULL
    """))

    conn = op.get_bind()
    orphan_count = conn.execute(text(
        "SELECT COUNT(*) FROM utility_readings WHERE tenant_id IS NULL"
    )).scalar()
    if orphan_count:
        raise RuntimeError(
            f"لا يمكن إكمال الـ migration: {orphan_count} صف في utility_readings بدون tenant_id قابل للاستنتاج "
            "(لا asset_id ولا grid_id قابلين للربط بـ tenant). يتطلب مراجعة يدوية للبيانات قبل المتابعة."
        )

    op.alter_column('utility_readings', 'tenant_id', nullable=False)
    op.create_index('ix_utility_readings_tenant_id', 'utility_readings', ['tenant_id'])
    op.create_foreign_key(
        'fk_utility_readings_tenant_id',
        'utility_readings',
        'academy_tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    op.drop_constraint('fk_utility_readings_tenant_id', 'utility_readings', type_='foreignkey')
    op.drop_index('ix_utility_readings_tenant_id', table_name='utility_readings')
    op.drop_column('utility_readings', 'tenant_id')
