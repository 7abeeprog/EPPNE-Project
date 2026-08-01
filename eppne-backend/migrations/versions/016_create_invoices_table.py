# migrations/versions/016_create_invoices_table.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import text

revision = '016_create_invoices_table'
down_revision = '014_add_tenant_id_to_payment_installments'

def upgrade() -> None:
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column('invoice_type', sa.Enum('SERVICE', 'AI_USAGE', 'SUBSCRIPTION', 'SAAS', 'PRODUCT', 'RENTAL', 'OTHER', name='invoicetype'), nullable=False, server_default='SERVICE'),
        sa.Column('status', sa.Enum('DRAFT', 'PENDING', 'PAID', 'OVERDUE', 'CANCELLED', name='invoicestatus'), nullable=False, server_default='PENDING'),
        sa.Column('amount', sa.Numeric(30, 8), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='MR_USDT'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('subscription_id', sa.Integer(), nullable=True),
        sa.Column('reference_id', sa.Integer(), nullable=True),
        sa.Column('idempotency_key', sa.String(length=100), nullable=True),
        sa.Column('issue_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('invoice_metadata', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invoice_number'),
        sa.UniqueConstraint('idempotency_key'),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['subscription_id'], ['saas_tenant_subscriptions.id'], ondelete='SET NULL'),
        sa.CheckConstraint('amount >= 0', name='check_amount_non_negative'),
    )

    op.create_index('ix_invoices_tenant_id', 'invoices', ['tenant_id'])
    op.create_index('ix_invoices_user_id', 'invoices', ['user_id'])
    op.create_index('ix_invoices_status', 'invoices', ['status'])
    op.create_index('ix_invoices_due_date', 'invoices', ['due_date'])
    op.create_index('ix_invoices_invoice_number', 'invoices', ['invoice_number'], unique=True)
    op.create_index('ix_invoices_order_id', 'invoices', ['order_id'])
    op.create_index('ix_invoices_subscription_id', 'invoices', ['subscription_id'])
    op.create_index('ix_invoices_reference_id', 'invoices', ['reference_id'])
    op.create_index('ix_invoices_invoice_type', 'invoices', ['invoice_type'])
    op.create_index('ix_invoices_created_at', 'invoices', ['created_at'])
    op.create_index('ix_invoices_updated_at', 'invoices', ['updated_at'])
    op.create_index('ix_invoices_tenant_status_due', 'invoices', ['tenant_id', 'status', 'due_date'])
    op.create_index('ix_invoices_idempotency_key', 'invoices', ['idempotency_key'], unique=True, postgresql_where=text("idempotency_key IS NOT NULL"))


def downgrade() -> None:
    op.drop_index('ix_invoices_idempotency_key', table_name='invoices')
    op.drop_index('ix_invoices_tenant_status_due', table_name='invoices')
    op.drop_index('ix_invoices_updated_at', table_name='invoices')
    op.drop_index('ix_invoices_created_at', table_name='invoices')
    op.drop_index('ix_invoices_invoice_type', table_name='invoices')
    op.drop_index('ix_invoices_reference_id', table_name='invoices')
    op.drop_index('ix_invoices_subscription_id', table_name='invoices')
    op.drop_index('ix_invoices_order_id', table_name='invoices')
    op.drop_index('ix_invoices_invoice_number', table_name='invoices')
    op.drop_index('ix_invoices_due_date', table_name='invoices')
    op.drop_index('ix_invoices_status', table_name='invoices')
    op.drop_index('ix_invoices_user_id', table_name='invoices')
    op.drop_index('ix_invoices_tenant_id', table_name='invoices')
    op.drop_table('invoices')