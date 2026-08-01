# migrations/versions/002_add_tenant_id_to_audit_logs.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '002_add_tenant_id_to_audit_logs'
down_revision = '001_add_tenant_id_to_wallets'  # ✅ يشير إلى الهجرة الأولى

def upgrade() -> None:
    # 1. إضافة العمود مع قيمة NULL مؤقتاً
    op.add_column('audit_logs', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.create_index('ix_audit_logs_tenant_id', 'audit_logs', ['tenant_id'])
    op.create_index('ix_audit_logs_tenant_user', 'audit_logs', ['tenant_id', 'user_id'])

    # 2. تعبئة العمود من جدول users
    op.execute(text("""
        UPDATE audit_logs
        SET tenant_id = users.tenant_id
        FROM users
        WHERE audit_logs.user_id = users.id
    """))

    # 3. جعل العمود NOT NULL وإضافة المفتاح الخارجي
    op.alter_column('audit_logs', 'tenant_id', nullable=False)
    op.create_foreign_key(
        'fk_audit_logs_tenant_id',
        'audit_logs',
        'academy_tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    op.drop_constraint('fk_audit_logs_tenant_id', 'audit_logs', type_='foreignkey')
    op.drop_index('ix_audit_logs_tenant_user')
    op.drop_index('ix_audit_logs_tenant_id')
    op.drop_column('audit_logs', 'tenant_id')