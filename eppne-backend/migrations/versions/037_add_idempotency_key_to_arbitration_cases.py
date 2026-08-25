# migrations/versions/037_add_idempotency_key_to_arbitration_cases.py
from alembic import op
import sqlalchemy as sa

revision = '037_add_idempotency_key_to_arbitration_cases'
down_revision = '036_add_idempotency_key_to_saas_invoices'


def upgrade() -> None:
    op.add_column('arbitration_cases', sa.Column('idempotency_key', sa.String(length=255), nullable=True))
    op.create_index(
        'ix_arbitration_cases_idempotency_key', 'arbitration_cases', ['idempotency_key'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_arbitration_cases_idempotency_key', table_name='arbitration_cases')
    op.drop_column('arbitration_cases', 'idempotency_key')
