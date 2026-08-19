# migrations/versions/028_create_affiliate_action_commissions.py
from alembic import op
import sqlalchemy as sa

revision = '028_create_affiliate_action_commissions'
down_revision = '027_create_identity_tenant_invitations'


def upgrade() -> None:
    op.create_table(
        'affiliate_action_commissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('affiliate_profile_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(30, 8), nullable=False),
        sa.Column('currency', sa.String(length=20), nullable=False, server_default='MR_USDT'),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_tx_hash', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['affiliate_profile_id'], ['affiliate_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    op.create_index('ix_affiliate_action_commissions_tenant_id', 'affiliate_action_commissions', ['tenant_id'])
    op.create_index('ix_affiliate_action_commissions_affiliate_profile_id', 'affiliate_action_commissions', ['affiliate_profile_id'])
    op.create_index('ix_affiliate_action_commissions_user_id', 'affiliate_action_commissions', ['user_id'])
    op.create_index('ix_affiliate_action_commissions_status', 'affiliate_action_commissions', ['status'])
    op.create_index('ix_affiliate_action_commissions_entity_type', 'affiliate_action_commissions', ['entity_type'])
    op.create_index('ix_affiliate_action_commissions_created_at', 'affiliate_action_commissions', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_affiliate_action_commissions_created_at', table_name='affiliate_action_commissions')
    op.drop_index('ix_affiliate_action_commissions_entity_type', table_name='affiliate_action_commissions')
    op.drop_index('ix_affiliate_action_commissions_status', table_name='affiliate_action_commissions')
    op.drop_index('ix_affiliate_action_commissions_user_id', table_name='affiliate_action_commissions')
    op.drop_index('ix_affiliate_action_commissions_affiliate_profile_id', table_name='affiliate_action_commissions')
    op.drop_index('ix_affiliate_action_commissions_tenant_id', table_name='affiliate_action_commissions')
    op.drop_table('affiliate_action_commissions')
