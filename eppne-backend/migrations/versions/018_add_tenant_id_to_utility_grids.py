# migrations/versions/018_add_tenant_id_to_utility_grids.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '018_add_tenant_id_to_utility_grids'
down_revision = '017_add_tenant_id_to_smart_assets'

def upgrade() -> None:
    op.add_column('utility_grids', sa.Column('tenant_id', sa.Integer(), nullable=True))

    # ملاحظة: لا يوجد عمود في utility_grids يربطها مباشرة بـ user أو tenant،
    # فمفيش backfill ممكن هنا. لو الجدول فيه صفوف فعلاً، الـ migration هتوقف
    # بـ raise وتتطلب مراجعة يدوية بدل ما تحط قيمة افتراضية عشوائية.
    conn = op.get_bind()
    orphan_count = conn.execute(text(
        "SELECT COUNT(*) FROM utility_grids WHERE tenant_id IS NULL"
    )).scalar()
    if orphan_count:
        raise RuntimeError(
            f"لا يمكن إكمال الـ migration: {orphan_count} صف في utility_grids بدون tenant_id قابل للاستنتاج "
            "(لا يوجد عمود ربط بـ user/tenant في هذا الجدول). يتطلب مراجعة يدوية للبيانات قبل المتابعة."
        )

    op.alter_column('utility_grids', 'tenant_id', nullable=False)
    op.create_index('ix_utility_grids_tenant_id', 'utility_grids', ['tenant_id'])
    op.create_foreign_key(
        'fk_utility_grids_tenant_id',
        'utility_grids',
        'academy_tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    op.drop_constraint('fk_utility_grids_tenant_id', 'utility_grids', type_='foreignkey')
    op.drop_index('ix_utility_grids_tenant_id', table_name='utility_grids')
    op.drop_column('utility_grids', 'tenant_id')
