# migrations/versions/057_create_sites_table.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '057_create_sites_table'
down_revision = '056_create_guardian_relationship_tables'

# Site موحّد عابر للقطاعات — جدول جديد بالكامل، صفر لمس على أي جدول
# قائم في هذه الخطوة (ربط iot/manufacturing/agritech/health بـsite_id
# خطوة منفصلة لاحقة). site_type مُخزَّن كـVARCHAR عادي بلا نوع ENUM في
# Postgres وبلا CHECK constraint (native_enum=False على الموديل) —
# لإضافة قيمة جديدة مستقبلًا بصفر migration. entity_type/entity_id
# زوج polymorphic بلا FK صريح (يطابق نمط app.core.models.EntityMembership).
# راجع: .claude/reports/unified-site-model-and-academy-camera-design-proposal.md


def upgrade() -> None:
    op.create_table(
        'sites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('parent_site_id', sa.Integer(), nullable=True),
        sa.Column('site_type', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('latitude', sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column('longitude', sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column('address_text', sa.String(length=500), nullable=True),
        sa.Column('geo_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('manager_id', sa.BigInteger(), nullable=True),
        sa.Column('data_residency_preference', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_site_id'], ['sites.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['manager_id'], ['users.id']),
    )

    # فهارس مفردة (تطابق index=True على كل عمود بالموديل)
    op.create_index('ix_sites_id', 'sites', ['id'], unique=False)
    op.create_index('ix_sites_tenant_id', 'sites', ['tenant_id'], unique=False)
    op.create_index('ix_sites_parent_site_id', 'sites', ['parent_site_id'], unique=False)
    op.create_index('ix_sites_site_type', 'sites', ['site_type'], unique=False)
    op.create_index('ix_sites_entity_type', 'sites', ['entity_type'], unique=False)
    op.create_index('ix_sites_entity_id', 'sites', ['entity_id'], unique=False)
    op.create_index('ix_sites_manager_id', 'sites', ['manager_id'], unique=False)

    # فهارس مُسمّاة صراحةً من التصميم المتفَق عليه (§1.3)
    op.create_index('ix_site_tenant_type', 'sites', ['tenant_id', 'site_type'], unique=False)
    op.create_index('ix_site_parent', 'sites', ['parent_site_id'], unique=False)
    op.create_index('ix_site_entity', 'sites', ['entity_type', 'entity_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_site_entity', table_name='sites')
    op.drop_index('ix_site_parent', table_name='sites')
    op.drop_index('ix_site_tenant_type', table_name='sites')

    op.drop_index('ix_sites_manager_id', table_name='sites')
    op.drop_index('ix_sites_entity_id', table_name='sites')
    op.drop_index('ix_sites_entity_type', table_name='sites')
    op.drop_index('ix_sites_site_type', table_name='sites')
    op.drop_index('ix_sites_parent_site_id', table_name='sites')
    op.drop_index('ix_sites_tenant_id', table_name='sites')
    op.drop_index('ix_sites_id', table_name='sites')

    op.drop_table('sites')
