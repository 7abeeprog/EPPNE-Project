# migrations/versions/013_add_tenant_id_to_course_analytics.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '013_add_tenant_id_to_course_analytics'
down_revision = '012_add_tenant_id_to_academy_enrollments'

def upgrade() -> None:
    op.add_column('course_analytics', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.execute(text("""
        UPDATE course_analytics 
        SET tenant_id = academy_courses.tenant_id 
        FROM academy_courses 
        WHERE course_analytics.course_id = academy_courses.id
    """))
    op.alter_column('course_analytics', 'tenant_id', nullable=False)
    op.create_foreign_key('fk_analytics_tenant_id', 'course_analytics', 'academy_tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_analytics_tenant_id', 'course_analytics', ['tenant_id'])

def downgrade() -> None:
    op.drop_index('ix_analytics_tenant_id', table_name='course_analytics')
    op.drop_constraint('fk_analytics_tenant_id', 'course_analytics', type_='foreignkey')
    op.drop_column('course_analytics', 'tenant_id')