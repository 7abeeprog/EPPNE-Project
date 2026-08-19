# migrations/versions/029_create_entity_membership_foundation.py
from alembic import op
import sqlalchemy as sa

revision = '029_create_entity_membership_foundation'
down_revision = '028_create_affiliate_action_commissions'


def upgrade() -> None:
    # ===== entity_memberships =====
    op.create_table(
        'entity_memberships',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column(
            'role',
            sa.Enum('OWNER', 'EXECUTIVE_DIRECTOR', 'SIGNATORY', 'REPRESENTATIVE',
                    name='entitymembershiprole'),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                   onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('entity_type', 'entity_id', 'user_id', name='uq_entity_membership'),
    )
    op.create_index('ix_entity_memberships_entity', 'entity_memberships', ['entity_type', 'entity_id'])
    op.create_index('ix_entity_memberships_user_tenant', 'entity_memberships', ['user_id', 'tenant_id'])

    # ===== entity_permission_overrides =====
    op.create_table(
        'entity_permission_overrides',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('permission', sa.String(length=100), nullable=False),
        sa.Column('granted', sa.Boolean(), nullable=False),
        sa.Column('granted_by', sa.Integer(), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('entity_type', 'entity_id', 'user_id', 'permission',
                             name='uq_entity_permission_override'),
    )

    # ===== permission_audit_log =====
    op.create_table(
        'permission_audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('scope', sa.Enum('PLATFORM', 'ENTITY', name='auditscope'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('target_user_id', sa.Integer(), nullable=False),
        sa.Column('permission', sa.String(length=100), nullable=False),
        sa.Column('action', sa.Enum('GRANT', 'REVOKE', name='auditaction'), nullable=False),
        sa.Column('performed_by', sa.Integer(), nullable=False),
        sa.Column('performed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['performed_by'], ['users.id'], ondelete='RESTRICT'),
    )
    op.create_index('ix_audit_performed_by', 'permission_audit_log', ['performed_by'])
    op.create_index('ix_audit_target_user', 'permission_audit_log', ['target_user_id'])
    op.create_index('ix_audit_performed_at', 'permission_audit_log', ['performed_at'])


def downgrade() -> None:
    op.drop_index('ix_audit_performed_at', table_name='permission_audit_log')
    op.drop_index('ix_audit_target_user', table_name='permission_audit_log')
    op.drop_index('ix_audit_performed_by', table_name='permission_audit_log')
    op.drop_table('permission_audit_log')

    op.drop_table('entity_permission_overrides')

    op.drop_index('ix_entity_memberships_user_tenant', table_name='entity_memberships')
    op.drop_index('ix_entity_memberships_entity', table_name='entity_memberships')
    op.drop_table('entity_memberships')
