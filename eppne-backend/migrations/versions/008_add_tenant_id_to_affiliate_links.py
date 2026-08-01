# migrations/versions/008_add_tenant_id_to_affiliate_links.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '008_add_tenant_id_to_affiliate_links'
down_revision = '007_add_tenant_id_to_referral_trees'

def upgrade() -> None:
    op.add_column('affiliate_links', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.execute(text("""
        UPDATE affiliate_links 
        SET tenant_id = affiliate_profiles.tenant_id 
        FROM affiliate_profiles 
        WHERE affiliate_links.affiliate_id = affiliate_profiles.id
    """))
    op.alter_column('affiliate_links', 'tenant_id', nullable=False)
    op.create_foreign_key('fk_affiliate_links_tenant_id', 'affiliate_links', 'academy_tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_affiliate_links_tenant_id', 'affiliate_links', ['tenant_id'])

def downgrade() -> None:
    op.drop_index('ix_affiliate_links_tenant_id', table_name='affiliate_links')
    op.drop_constraint('fk_affiliate_links_tenant_id', 'affiliate_links', type_='foreignkey')
    op.drop_column('affiliate_links', 'tenant_id')