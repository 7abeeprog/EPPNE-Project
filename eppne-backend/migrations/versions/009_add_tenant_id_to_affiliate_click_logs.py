# migrations/versions/009_add_tenant_id_to_affiliate_click_logs.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '009_add_tenant_id_to_affiliate_click_logs'
down_revision = '008_add_tenant_id_to_affiliate_links'

def upgrade() -> None:
    op.add_column('affiliate_click_logs', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.execute(text("""
        UPDATE affiliate_click_logs 
        SET tenant_id = affiliate_profiles.tenant_id 
        FROM affiliate_profiles 
        WHERE affiliate_click_logs.affiliate_id = affiliate_profiles.id
    """))
    op.alter_column('affiliate_click_logs', 'tenant_id', nullable=False)
    op.create_foreign_key('fk_affiliate_click_logs_tenant_id', 'affiliate_click_logs', 'academy_tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_affiliate_click_logs_tenant_id', 'affiliate_click_logs', ['tenant_id'])

def downgrade() -> None:
    op.drop_index('ix_affiliate_click_logs_tenant_id', table_name='affiliate_click_logs')
    op.drop_constraint('fk_affiliate_click_logs_tenant_id', 'affiliate_click_logs', type_='foreignkey')
    op.drop_column('affiliate_click_logs', 'tenant_id')