# migrations/versions/001_add_tenant_id_to_wallets.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '001_add_tenant_id_to_wallets'
down_revision = '003_add_tenant_id_to_users'   # ✅ الرقم الصحيح من alembic current

def upgrade() -> None:
    # 1. إضافة العمود مع قيمة NULL مؤقتاً
    op.add_column('wallets', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.create_index('ix_wallets_tenant_id', 'wallets', ['tenant_id'])

    # 2. تعبئة العمود من جدول users
    op.execute(text("""
        UPDATE wallets
        SET tenant_id = users.tenant_id
        FROM users
        WHERE wallets.user_id = users.id
    """))

    # 3. جعل العمود NOT NULL وإضافة المفتاح الخارجي
    op.alter_column('wallets', 'tenant_id', nullable=False)
    op.create_foreign_key(
        'fk_wallets_tenant_id',
        'wallets',
        'academy_tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    op.drop_constraint('fk_wallets_tenant_id', 'wallets', type_='foreignkey')
    op.drop_index('ix_wallets_tenant_id')
    op.drop_column('wallets', 'tenant_id')