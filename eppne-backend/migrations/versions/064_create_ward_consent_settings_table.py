# migrations/versions/064_create_ward_consent_settings_table.py
from alembic import op
import sqlalchemy as sa

revision = '064_create_ward_consent_settings_table'
down_revision = '063_create_site_devices_table'

# جدول جديد بالكامل — WardConsentSetting، تطبيق حرفي لـ§2.3 من
# .claude/reports/unified-site-model-and-academy-camera-design-proposal.md.
# علم موافقة على مستوى الطالب (ward) نفسه، منفصل عن
# GuardianVisibilitySetting عمدًا (ده بيحجب العرض فقط، صفر أثر على أي
# مسار كتابة/استقبال بيانات). consent_type = VARCHAR (native_enum=False
# على الموديل، نفس نمط SiteType) — صفر CHECK constraint، لإضافة نوع
# موافقة جديد مستقبلًا بصفر migration.


def upgrade() -> None:
    op.create_table(
        'ward_consent_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('ward_user_id', sa.Integer(), nullable=False),
        sa.Column('consent_type', sa.String(length=50), nullable=False),
        sa.Column('is_opted_out', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('set_by_user_id', sa.Integer(), nullable=True),
        sa.Column('set_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ward_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['set_by_user_id'], ['users.id']),
        sa.UniqueConstraint('ward_user_id', 'consent_type', name='uq_ward_consent_type'),
    )

    # فهارس مفردة (تطابق index=True على كل عمود بالموديل)
    op.create_index('ix_ward_consent_settings_id', 'ward_consent_settings', ['id'], unique=False)
    op.create_index('ix_ward_consent_settings_tenant_id', 'ward_consent_settings', ['tenant_id'], unique=False)
    op.create_index('ix_ward_consent_settings_ward_user_id', 'ward_consent_settings', ['ward_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_ward_consent_settings_ward_user_id', table_name='ward_consent_settings')
    op.drop_index('ix_ward_consent_settings_tenant_id', table_name='ward_consent_settings')
    op.drop_index('ix_ward_consent_settings_id', table_name='ward_consent_settings')
    op.drop_table('ward_consent_settings')
