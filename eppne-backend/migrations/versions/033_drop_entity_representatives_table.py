# migrations/versions/033_drop_entity_representatives_table.py
from alembic import op
import sqlalchemy as sa

revision = '033_drop_entity_representatives_table'
down_revision = '032_add_enrollment_cancellation'


def upgrade() -> None:
    op.drop_index('ix_entity_representatives_user_id', table_name='entity_representatives')
    op.drop_index('ix_entity_representatives_id', table_name='entity_representatives')
    op.drop_index('ix_entity_representatives_entity_id', table_name='entity_representatives')
    op.drop_index('ix_entity_rep_unique', table_name='entity_representatives')
    op.drop_table('entity_representatives')
    op.execute('DROP TYPE IF EXISTS entityrole')


def downgrade() -> None:
    entityrole = sa.Enum('OWNER', 'EXECUTIVE_DIRECTOR', 'SIGNATORY', 'REPRESENTATIVE', name='entityrole')
    entityrole.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'entity_representatives',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', entityrole, nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('can_sign_contracts', sa.Boolean(), nullable=True),
        sa.Column('signature_pub_key', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['entity_id'], ['sovereign_entities_v2.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_entity_rep_unique', 'entity_representatives', ['entity_id', 'user_id'], unique=True)
    op.create_index('ix_entity_representatives_entity_id', 'entity_representatives', ['entity_id'], unique=False)
    op.create_index('ix_entity_representatives_id', 'entity_representatives', ['id'], unique=False)
    op.create_index('ix_entity_representatives_user_id', 'entity_representatives', ['user_id'], unique=False)
