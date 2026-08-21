# migrations/versions/032_add_enrollment_cancellation.py
from alembic import op
import sqlalchemy as sa

revision = '032_add_enrollment_cancellation'
down_revision = '031_create_quiz_submissions'


def upgrade() -> None:
    op.add_column('academy_enrollments', sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('academy_enrollments', sa.Column('cancellation_reason', sa.String(length=50), nullable=True))
    op.add_column('academy_enrollments', sa.Column('cancellation_note', sa.Text(), nullable=True))
    op.add_column('academy_enrollments', sa.Column('refund_status', sa.String(length=20), nullable=True))
    op.add_column('academy_enrollments', sa.Column('refund_amount', sa.Numeric(30, 8), nullable=True))
    op.add_column('academy_courses', sa.Column('is_foundational', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('academy_courses', 'is_foundational')
    op.drop_column('academy_enrollments', 'refund_amount')
    op.drop_column('academy_enrollments', 'refund_status')
    op.drop_column('academy_enrollments', 'cancellation_note')
    op.drop_column('academy_enrollments', 'cancellation_reason')
    op.drop_column('academy_enrollments', 'cancelled_at')
