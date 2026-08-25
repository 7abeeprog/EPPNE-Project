# migrations/versions/038_add_instructor_id_to_academy_bootcamps.py
from alembic import op
import sqlalchemy as sa

revision = '038_add_instructor_id_to_academy_bootcamps'
down_revision = '037_add_idempotency_key_to_arbitration_cases'


def upgrade() -> None:
    op.add_column('academy_bootcamps', sa.Column('instructor_id', sa.Integer(), nullable=True))
    op.create_index('ix_academy_bootcamps_instructor_id', 'academy_bootcamps', ['instructor_id'])
    op.create_foreign_key(
        'fk_academy_bootcamps_instructor_id_users', 'academy_bootcamps', 'users',
        ['instructor_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_academy_bootcamps_instructor_id_users', 'academy_bootcamps', type_='foreignkey')
    op.drop_index('ix_academy_bootcamps_instructor_id', table_name='academy_bootcamps')
    op.drop_column('academy_bootcamps', 'instructor_id')
