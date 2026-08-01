# migrations/versions/007_add_tenant_id_to_referral_trees.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '007_add_tenant_id_to_referral_trees'
down_revision = '006_add_tenant_id_to_commerce_audit_logs'

def upgrade() -> None:
    op.add_column('referral_trees', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.execute(text("""
        UPDATE referral_trees 
        SET tenant_id = users.tenant_id 
        FROM users 
        WHERE referral_trees.referred_id = users.id
    """))
    op.alter_column('referral_trees', 'tenant_id', nullable=False)
    op.create_foreign_key('fk_referral_trees_tenant_id', 'referral_trees', 'academy_tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_referral_trees_tenant_id', 'referral_trees', ['tenant_id'])

def downgrade() -> None:
    op.drop_index('ix_referral_trees_tenant_id', table_name='referral_trees')
    op.drop_constraint('fk_referral_trees_tenant_id', 'referral_trees', type_='foreignkey')
    op.drop_column('referral_trees', 'tenant_id')