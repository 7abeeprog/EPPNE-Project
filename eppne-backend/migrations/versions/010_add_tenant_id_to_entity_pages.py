# migrations/versions/010_add_tenant_id_to_entity_pages.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '010_add_tenant_id_to_entity_pages'
down_revision = '009_add_tenant_id_to_affiliate_click_logs'  # آخر هجرة من قطاع Affiliate

def upgrade() -> None:
    # 1. إضافة العمود مع قيمة NULL مؤقتاً
    op.add_column('entity_pages', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.create_index('ix_entity_pages_tenant_id', 'entity_pages', ['tenant_id'])

    # 2. تعبئة العمود من جدول sovereign_entities_v2 (كل صفحة تابعة لكيان)
    op.execute(text("""
        UPDATE entity_pages
        SET tenant_id = sovereign_entities_v2.tenant_id
        FROM sovereign_entities_v2
        WHERE entity_pages.entity_id = sovereign_entities_v2.id
    """))

    # 3. جعل العمود NOT NULL
    op.alter_column('entity_pages', 'tenant_id', nullable=False)

    # 4. إضافة المفتاح الخارجي
    op.create_foreign_key(
        'fk_entity_pages_tenant_id',
        'entity_pages',
        'academy_tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    op.drop_constraint('fk_entity_pages_tenant_id', 'entity_pages', type_='foreignkey')
    op.drop_index('ix_entity_pages_tenant_id', table_name='entity_pages')
    op.drop_column('entity_pages', 'tenant_id')