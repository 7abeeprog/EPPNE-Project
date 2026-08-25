# migrations/versions/036_add_idempotency_key_to_saas_invoices.py
from alembic import op
import sqlalchemy as sa

revision = '036_add_idempotency_key_to_saas_invoices'
down_revision = '035_add_system_to_systemrole_enum'


def upgrade() -> None:
    op.add_column('saas_invoices', sa.Column('idempotency_key', sa.String(length=255), nullable=True))
    op.create_index(
        'ix_saas_invoices_idempotency_key', 'saas_invoices', ['idempotency_key'],
        unique=True, postgresql_where=sa.text('idempotency_key IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('ix_saas_invoices_idempotency_key', table_name='saas_invoices')
    op.drop_column('saas_invoices', 'idempotency_key')
