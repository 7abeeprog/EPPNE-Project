# migrations/versions/066_site_devices_org_entity_id.py
from alembic import op
import sqlalchemy as sa

revision = '066_site_devices_org_entity_id'
down_revision = '065_classroom_camera_analysis_site_id_not_null'

# إضافة صافية — site_devices.org_entity_id (FK organization_entities.id,
# NOT NULL). سبب الظهور: ClassroomCameraAnalysis.org_entity_id (عمود
# قديم سابق لـsite_id/device auth بالكامل) NOT NULL ولا علاقة له
# بـsite_id ولا بأي بيانات على SiteDevice قبل هذا الملف — صفر مصدر
# موثوق لقيمته وقت استقبال جهاز مُصادَق عليه. اكتُشف هذا أثناء بناء
# endpoint الاستقبال، وحُسم بقرار المستخدم: يُحدَّد مرة واحدة وقت إصدار
# enrollment token (إداري، موثوق)، يُخزَّن على SiteDevice، ويُقرأ من
# هناك وقت كل INSERT — نفس نمط site_id بالضبط. الجدول كان فاضيًا
# بالكامل وقت التنفيذ (0 صف، اتأكَّد مباشرة) — صفر backfill مطلوب.


def upgrade() -> None:
    op.add_column('site_devices', sa.Column('org_entity_id', sa.Integer(), nullable=False))
    op.create_foreign_key(
        'site_devices_org_entity_id_fkey', 'site_devices', 'organization_entities', ['org_entity_id'], ['id']
    )
    op.create_index('ix_site_devices_org_entity_id', 'site_devices', ['org_entity_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_site_devices_org_entity_id', table_name='site_devices')
    op.drop_constraint('site_devices_org_entity_id_fkey', 'site_devices', type_='foreignkey')
    op.drop_column('site_devices', 'org_entity_id')
