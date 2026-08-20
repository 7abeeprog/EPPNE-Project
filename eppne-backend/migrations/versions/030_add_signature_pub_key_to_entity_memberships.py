# migrations/versions/030_add_signature_pub_key_to_entity_memberships.py
from alembic import op
import sqlalchemy as sa

revision = '030_add_signature_pub_key_to_entity_memberships'
down_revision = '029_create_entity_membership_foundation'


def upgrade() -> None:
    op.add_column(
        'entity_memberships',
        sa.Column('signature_pub_key', sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('entity_memberships', 'signature_pub_key')
