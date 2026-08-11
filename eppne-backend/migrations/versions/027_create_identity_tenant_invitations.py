# migrations/versions/027_create_identity_tenant_invitations.py
from alembic import op
import sqlalchemy as sa

revision = '027_create_identity_tenant_invitations'
down_revision = '026_add_tenant_id_to_tombstone_records'


def upgrade() -> None:
    op.create_table(
        'identity_tenant_invitations',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('referrer_user_id', sa.BigInteger(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'ACCEPTED', 'REVOKED', 'EXPIRED', name='tenant_invitation_status'),
            nullable=False,
            server_default='PENDING',
        ),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('current_uses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_by_user_id', sa.BigInteger(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['referrer_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['revoked_by_user_id'], ['users.id'], ondelete='SET NULL'),
    )

    op.create_index('ix_identity_tenant_invitations_token_hash', 'identity_tenant_invitations', ['token_hash'], unique=True)
    op.create_index('ix_identity_tenant_invitations_tenant_status', 'identity_tenant_invitations', ['tenant_id', 'status'])
    op.create_index('ix_identity_tenant_invitations_referrer', 'identity_tenant_invitations', ['referrer_user_id'])
    op.create_index('ix_identity_tenant_invitations_product', 'identity_tenant_invitations', ['product_id'])
    op.create_index('ix_identity_tenant_invitations_email', 'identity_tenant_invitations', ['email'])
    op.create_index('ix_identity_tenant_invitations_status_expiry', 'identity_tenant_invitations', ['status', 'expires_at'])


def downgrade() -> None:
    op.drop_index('ix_identity_tenant_invitations_status_expiry', table_name='identity_tenant_invitations')
    op.drop_index('ix_identity_tenant_invitations_email', table_name='identity_tenant_invitations')
    op.drop_index('ix_identity_tenant_invitations_product', table_name='identity_tenant_invitations')
    op.drop_index('ix_identity_tenant_invitations_referrer', table_name='identity_tenant_invitations')
    op.drop_index('ix_identity_tenant_invitations_tenant_status', table_name='identity_tenant_invitations')
    op.drop_index('ix_identity_tenant_invitations_token_hash', table_name='identity_tenant_invitations')
    op.drop_table('identity_tenant_invitations')
    sa.Enum(name='tenant_invitation_status').drop(op.get_bind(), checkfirst=True)
