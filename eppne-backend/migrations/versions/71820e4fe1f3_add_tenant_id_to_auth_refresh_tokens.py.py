# migrations/versions/xxxx_add_tenant_id_to_auth_refresh_tokens.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'xxxx_add_tenant_id_to_auth_refresh_tokens'
down_revision = '71820e4fe1f3'  # ⚠️ استبدل بالرقم الصحيح

def upgrade() -> None:
    op.add_column('auth_refresh_tokens', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.create_index('ix_refresh_token_tenant_id', 'auth_refresh_tokens', ['tenant_id'])
    op.execute(text("UPDATE auth_refresh_tokens SET tenant_id = 1 WHERE tenant_id IS NULL"))
    op.alter_column('auth_refresh_tokens', 'tenant_id', nullable=False)
    op.create_foreign_key('fk_auth_refresh_tokens_tenant_id', 'auth_refresh_tokens', 'academy_tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_refresh_token_tenant_user', 'auth_refresh_tokens', ['tenant_id', 'user_id'])

def downgrade() -> None:
    op.drop_constraint('fk_auth_refresh_tokens_tenant_id', 'auth_refresh_tokens', type_='foreignkey')
    op.drop_index('ix_refresh_token_tenant_user', table_name='auth_refresh_tokens')
    op.drop_index('ix_refresh_token_tenant_id', table_name='auth_refresh_tokens')
    op.drop_column('auth_refresh_tokens', 'tenant_id')