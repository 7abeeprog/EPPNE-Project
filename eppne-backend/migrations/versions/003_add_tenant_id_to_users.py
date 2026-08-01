# migrations/versions/003_add_tenant_id_to_users.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# ⚠️ يجب أن يشير down_revision إلى آخر هجرة مثبتة (من alembic current)
revision = '003_add_tenant_id_to_users'
down_revision = 'xxxx_add_tenant_id_to_auth_refresh_tokens'  # ← استبدل بالقيمة الصحيحة

def upgrade() -> None:
    # 1. إضافة العمود مع السماح بـ NULL مؤقتاً
    op.add_column('users', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])

    # 2. تعبئة العمود بقيمة افتراضية (1) للصفوف الحالية
    #    لأن الهجرة الأساسية أنشأت المستخدمين بدون tenant_id
    op.execute(text("UPDATE users SET tenant_id = 1 WHERE tenant_id IS NULL"))

    # 3. جعل العمود NOT NULL
    op.alter_column('users', 'tenant_id', nullable=False)

    # 4. إضافة المفتاح الخارجي إلى جدول academy_tenants
    op.create_foreign_key(
        'fk_users_tenant_id',
        'users',
        'academy_tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # 5. إضافة قيد تحقق للتأكد من أن tenant_id موجود في academy_tenants
    #    (يتم ذلك تلقائياً عبر المفتاح الخارجي)

def downgrade() -> None:
    # 1. حذف المفتاح الخارجي
    op.drop_constraint('fk_users_tenant_id', 'users', type_='foreignkey')

    # 2. حذف الفهرس
    op.drop_index('ix_users_tenant_id')

    # 3. حذف العمود
    op.drop_column('users', 'tenant_id')