# migrations/versions/005_add_tenant_id_to_payment_requests.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '005_add_tenant_id_to_payment_requests'
down_revision = '004_add_tenant_id_to_orders'

def upgrade() -> None:
    # 1. إضافة العمود مع قيمة NULL مؤقتاً
    op.add_column('payment_requests', sa.Column('tenant_id', sa.Integer(), nullable=True))
    
    # 2. تعبئة العمود من جدول orders
    op.execute(text("""
        UPDATE payment_requests 
        SET tenant_id = orders.tenant_id 
        FROM orders 
        WHERE payment_requests.order_id = orders.id
    """))
    
    # 3. جعل العمود NOT NULL
    op.alter_column('payment_requests', 'tenant_id', nullable=False)
    
    # 4. إضافة المفتاح الخارجي
    op.create_foreign_key(
        'fk_payment_requests_tenant_id',
        'payment_requests',
        'academy_tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # 5. إضافة الفهرس
    op.create_index('ix_payment_requests_tenant_id', 'payment_requests', ['tenant_id'])

def downgrade() -> None:
    op.drop_index('ix_payment_requests_tenant_id', table_name='payment_requests')
    op.drop_constraint('fk_payment_requests_tenant_id', 'payment_requests', type_='foreignkey')
    op.drop_column('payment_requests', 'tenant_id')