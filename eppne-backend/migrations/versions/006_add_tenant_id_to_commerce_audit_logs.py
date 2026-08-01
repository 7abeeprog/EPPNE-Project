# migrations/versions/006_add_tenant_id_to_commerce_audit_logs.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '006_add_tenant_id_to_commerce_audit_logs'
down_revision = '005_add_tenant_id_to_payment_requests'

def upgrade() -> None:
    # 1. إضافة العمود مع قيمة NULL مؤقتاً
    op.add_column('commerce_audit_logs', sa.Column('tenant_id', sa.Integer(), nullable=True))
    
    # 2. تعبئة العمود من جدول orders (عبر order_id)
    op.execute(text("""
        UPDATE commerce_audit_logs 
        SET tenant_id = orders.tenant_id 
        FROM orders 
        WHERE commerce_audit_logs.order_id = orders.id
    """))
    
    # 3. جعل العمود NOT NULL
    op.alter_column('commerce_audit_logs', 'tenant_id', nullable=False)
    
    # 4. إضافة المفتاح الخارجي
    op.create_foreign_key(
        'fk_commerce_audit_logs_tenant_id',
        'commerce_audit_logs',
        'academy_tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # 5. إضافة الفهارس
    op.create_index('ix_commerce_audit_logs_tenant_id', 'commerce_audit_logs', ['tenant_id'])
    op.create_index('ix_commerce_audit_logs_tenant_user', 'commerce_audit_logs', ['tenant_id', 'user_id'])

def downgrade() -> None:
    op.drop_index('ix_commerce_audit_logs_tenant_user', table_name='commerce_audit_logs')
    op.drop_index('ix_commerce_audit_logs_tenant_id', table_name='commerce_audit_logs')
    op.drop_constraint('fk_commerce_audit_logs_tenant_id', 'commerce_audit_logs', type_='foreignkey')
    op.drop_column('commerce_audit_logs', 'tenant_id')