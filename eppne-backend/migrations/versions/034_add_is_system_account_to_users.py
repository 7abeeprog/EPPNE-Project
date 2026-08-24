# migrations/versions/034_add_is_system_account_to_users.py
from alembic import op
import sqlalchemy as sa

revision = '034_add_is_system_account_to_users'
down_revision = '033_drop_entity_representatives_table'


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('is_system_account', sa.Boolean(), server_default='false', nullable=False),
    )
    # Partial UNIQUE index: at most one system account per tenant. This also
    # serves as the lookup index for get_or_create_system_account's
    # `WHERE tenant_id = X AND is_system_account = true` query — no separate
    # composite index needed alongside it.
    op.create_index(
        'uq_users_tenant_system_account',
        'users',
        ['tenant_id'],
        unique=True,
        postgresql_where=sa.text('is_system_account = true'),
    )


def downgrade() -> None:
    op.drop_index('uq_users_tenant_system_account', table_name='users')
    op.drop_column('users', 'is_system_account')
