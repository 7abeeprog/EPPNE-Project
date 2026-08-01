# migrations/versions/004_add_tenant_id_to_orders.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '004_add_tenant_id_to_orders'
down_revision = '002_add_tenant_id_to_audit_logs'

def upgrade() -> None:
    # 1. إضافة العمود مع قيمة NULL مؤقتاً
    op.add_column('orders', sa.Column('tenant_id', sa.Integer(), nullable=True))
    
    # 2. تعبئة العمود من جدول store_profiles
    op.execute(text("""
        UPDATE orders 
        SET tenant_id = store_profiles.tenant_id 
        FROM store_profiles 
        WHERE orders.store_id = store_profiles.id
    """))
    
    # 3. جعل العمود NOT NULL
    op.alter_column('orders', 'tenant_id', nullable=False)
    
    # 4. إضافة المفتاح الخارجي
    op.create_foreign_key(
        'fk_orders_tenant_id',
        'orders',
        'academy_tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # 5. إضافة الفهارس
    op.create_index('ix_orders_tenant_id', 'orders', ['tenant_id'])
    op.create_index('ix_orders_tenant_status', 'orders', ['tenant_id', 'status'])

def downgrade() -> None:
    op.drop_index('ix_orders_tenant_status', table_name='orders')
    op.drop_index('ix_orders_tenant_id', table_name='orders')
    op.drop_constraint('fk_orders_tenant_id', 'orders', type_='foreignkey')
    op.drop_column('orders', 'tenant_id')