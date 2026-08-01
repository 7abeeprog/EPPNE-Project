# migrations/versions/012_add_tenant_id_to_academy_enrollments.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '012_add_tenant_id_to_academy_enrollments'
down_revision = '011_drop_saas_plans_and_subscriptions'

def upgrade() -> None:
    op.add_column('academy_enrollments', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.execute(text("""
        UPDATE academy_enrollments 
        SET tenant_id = academy_courses.tenant_id 
        FROM academy_courses 
        WHERE academy_enrollments.course_id = academy_courses.id
    """))
    op.alter_column('academy_enrollments', 'tenant_id', nullable=False)
    op.create_foreign_key('fk_enrollments_tenant_id', 'academy_enrollments', 'academy_tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_enrollment_tenant_id', 'academy_enrollments', ['tenant_id'])
    op.create_index('ix_enrollment_tenant_status', 'academy_enrollments', ['tenant_id', 'status'])

def downgrade() -> None:
    op.drop_index('ix_enrollment_tenant_status', table_name='academy_enrollments')
    op.drop_index('ix_enrollment_tenant_id', table_name='academy_enrollments')
    op.drop_constraint('fk_enrollments_tenant_id', 'academy_enrollments', type_='foreignkey')
    op.drop_column('academy_enrollments', 'tenant_id')