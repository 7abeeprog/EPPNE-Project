# migrations/versions/031_create_quiz_submissions.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '031_create_quiz_submissions'
down_revision = '030_add_signature_pub_key_to_entity_memberships'


def upgrade() -> None:
    op.create_table(
        'quiz_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quiz_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('answers', postgresql.JSONB(), nullable=False),
        sa.Column('score', sa.Numeric(5, 2), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='SUBMITTED', nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['quiz_id'], ['node_quizzes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_quiz_submission_quiz_user', 'quiz_submissions', ['quiz_id', 'user_id'])
    op.create_index('ix_quiz_submission_tenant', 'quiz_submissions', ['tenant_id'])


def downgrade() -> None:
    op.drop_index('ix_quiz_submission_tenant', table_name='quiz_submissions')
    op.drop_index('ix_quiz_submission_quiz_user', table_name='quiz_submissions')
    op.drop_table('quiz_submissions')
