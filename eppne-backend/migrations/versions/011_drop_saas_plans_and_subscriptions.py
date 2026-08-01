# migrations/versions/011_drop_saas_plans_and_subscriptions.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '011_drop_saas_plans_and_subscriptions'
down_revision = '010_add_tenant_id_to_entity_pages'

def upgrade() -> None:
    # حذف المفاتيح الخارجية أولاً (إن وجدت)
    op.execute(text("""
        DO $$ 
        DECLARE 
            r RECORD;
        BEGIN
            FOR r IN (SELECT conname FROM pg_constraint WHERE conrelid = 'saas_subscriptions'::regclass)
            LOOP
                EXECUTE 'ALTER TABLE saas_subscriptions DROP CONSTRAINT ' || r.conname;
            END LOOP;
        END $$;
    """))

    op.execute(text("""
        DO $$ 
        DECLARE 
            r RECORD;
        BEGIN
            FOR r IN (SELECT conname FROM pg_constraint WHERE conrelid = 'saas_plans'::regclass)
            LOOP
                EXECUTE 'ALTER TABLE saas_plans DROP CONSTRAINT ' || r.conname;
            END LOOP;
        END $$;
    """))

    # حذف الجداول
    op.drop_table('saas_subscriptions')
    op.drop_table('saas_plans')

def downgrade() -> None:
    # إعادة إنشاء الجداول (إذا لزم الأمر في حالة التراجع)
    op.create_table(
        'saas_plans',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('price_monthly', sa.Numeric(30, 8), nullable=False),
        sa.Column('price_yearly', sa.Numeric(30, 8), nullable=False),
        sa.Column('currency', sa.String(20), default='MR_USDT'),
        sa.Column('features', sa.JSON, default=dict),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_table(
        'saas_subscriptions',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tenant_id', sa.Integer, nullable=False),
        sa.Column('plan_id', sa.Integer, nullable=False),
        sa.Column('idempotency_key', sa.String(255), unique=True, nullable=True),
        sa.Column('status', sa.String(50), default='ACTIVE'),
        sa.Column('features', sa.JSON, default=dict),
        sa.Column('last_billed_month', sa.DateTime(timezone=True)),
        sa.Column('trial_end_date', sa.DateTime(timezone=True)),
        sa.Column('start_date', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('end_date', sa.DateTime(timezone=True)),
        sa.Column('next_billing_date', sa.DateTime(timezone=True)),
        sa.Column('payment_method', sa.String(50), default='WALLET'),
        sa.Column('auto_renew', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_foreign_key('fk_saas_subscriptions_tenant', 'saas_subscriptions', 'academy_tenants', ['tenant_id'], ['id'])
    op.create_foreign_key('fk_saas_subscriptions_plan', 'saas_subscriptions', 'saas_plans', ['plan_id'], ['id'])