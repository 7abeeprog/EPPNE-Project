# migrations/versions/063_create_site_devices_table.py
from alembic import op
import sqlalchemy as sa

revision = '063_create_site_devices_table'
down_revision = '062_classroom_camera_analysis_site_id'

# جدول جديد بالكامل لدعم device authentication (كاميرات academy) —
# صفر لمس على أي جدول قائم. تطبيق حرفي لـ§2 من
# .claude/reports/camera-device-authentication-design-proposal.md —
# الخيار جـ (Service Account + JWT قصير الأجل + Enrollment Token بالجملة
# على مستوى site). site_id يعتمد على جدول sites (migration 057،
# موجود بالفعل قبل هذا الملف بترتيب صريح متفَق عليه في نفس المستند §3).


def upgrade() -> None:
    op.create_table(
        'site_devices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.Column('device_label', sa.String(length=255), nullable=True),
        sa.Column('credential_hash', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='ACTIVE'),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('enrolled_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('credential_hash', name='uq_site_devices_credential_hash'),
    )

    # فهارس مفردة (تطابق index=True على كل عمود بالموديل)
    op.create_index('ix_site_devices_id', 'site_devices', ['id'], unique=False)
    op.create_index('ix_site_devices_tenant_id', 'site_devices', ['tenant_id'], unique=False)
    op.create_index('ix_site_devices_site_id', 'site_devices', ['site_id'], unique=False)
    op.create_index('ix_site_devices_credential_hash', 'site_devices', ['credential_hash'], unique=True)

    # فهارس مُسمّاة صراحةً من التصميم المتفَق عليه (§2)
    op.create_index('ix_site_device_site', 'site_devices', ['site_id'], unique=False)
    op.create_index('ix_site_device_status', 'site_devices', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_site_device_status', table_name='site_devices')
    op.drop_index('ix_site_device_site', table_name='site_devices')
    op.drop_index('ix_site_devices_credential_hash', table_name='site_devices')
    op.drop_index('ix_site_devices_site_id', table_name='site_devices')
    op.drop_index('ix_site_devices_tenant_id', table_name='site_devices')
    op.drop_index('ix_site_devices_id', table_name='site_devices')
    op.drop_table('site_devices')
