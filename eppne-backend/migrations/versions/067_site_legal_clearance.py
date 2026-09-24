# migrations/versions/067_site_legal_clearance.py
from alembic import op
import sqlalchemy as sa

revision = '067_site_legal_clearance'
down_revision = '066_site_devices_org_entity_id'

# إضافة صافية على sites — بوابة الموافقة الإدارية (جمع موافقات أولياء
# الأمور فعليًا) قبل تفعيل استقبال الكاميرا الحي لمدرسة معيّنة. صفر لمس
# على أي جدول تاني. الجدول فيه 61 صف حاليًا (مدرسة الـpilot الحية) —
# server_default='false' يضمن كل الصفوف الموجودة تبدأ "غير معتمدة"
# (الافتراض الآمن)، صفر backfill يدوي مطلوب.


def upgrade() -> None:
    op.add_column('sites', sa.Column('legal_clearance_approved', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('sites', sa.Column('legal_clearance_attestation_note', sa.Text(), nullable=True))
    op.add_column('sites', sa.Column('legal_clearance_set_by_user_id', sa.Integer(), nullable=True))
    op.add_column('sites', sa.Column('legal_clearance_set_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        'sites_legal_clearance_set_by_user_id_fkey', 'sites', 'users', ['legal_clearance_set_by_user_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('sites_legal_clearance_set_by_user_id_fkey', 'sites', type_='foreignkey')
    op.drop_column('sites', 'legal_clearance_set_at')
    op.drop_column('sites', 'legal_clearance_set_by_user_id')
    op.drop_column('sites', 'legal_clearance_attestation_note')
    op.drop_column('sites', 'legal_clearance_approved')
