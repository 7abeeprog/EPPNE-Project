# migrations/versions/014_add_tenant_id_to_payment_installments.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '014_add_tenant_id_to_payment_installments'
down_revision = '013_add_tenant_id_to_course_analytics'

def upgrade() -> None:
    op.add_column('payment_installments', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.execute(text("""
        UPDATE payment_installments 
        SET tenant_id = academy_enrollments.tenant_id 
        FROM academy_enrollments 
        WHERE payment_installments.enrollment_id = academy_enrollments.id
    """))
    op.alter_column('payment_installments', 'tenant_id', nullable=False)
    op.create_foreign_key('fk_installments_tenant_id', 'payment_installments', 'academy_tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_installment_tenant_id', 'payment_installments', ['tenant_id'])

def downgrade() -> None:
    op.drop_index('ix_installment_tenant_id', table_name='payment_installments')
    op.drop_constraint('fk_installments_tenant_id', 'payment_installments', type_='foreignkey')
    op.drop_column('payment_installments', 'tenant_id')