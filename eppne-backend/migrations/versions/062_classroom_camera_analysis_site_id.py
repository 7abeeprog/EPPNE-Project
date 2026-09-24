# migrations/versions/062_classroom_camera_analysis_site_id.py
from alembic import op
import sqlalchemy as sa

revision = '062_classroom_camera_analysis_site_id'
down_revision = '061_health_facility_site_id'

# إضافة صافية لـsite_id (FK sites.id) في ClassroomCameraAnalysis —
# nullable=True مؤقتًا بقرار صريح (مستند التصميم §2.1): التحويل لـ
# NOT NULL launch gate إلزامي قبل أي استخدام إنتاجي فعلي للكاميرا، مش
# جزء من هذه الدفعة. org_entity_id الموجود بلا أي لمس — صفر استبدال،
# إضافة صافية فقط (لا يوجد عمود قديم يمثل نفس المعنى). الجدول كان فاضي
# بالكامل (0 صف، اتأكَّد مرتين وقت التنفيذ) — صفر DELETE مطلوب (بخلاف
# iot/manufacturing/agritech/health اللي احتاجت سلاسل حذف throwaway قبل
# فرض NOT NULL هناك). راجع:
# .claude/reports/unified-site-model-and-academy-camera-design-proposal.md


def upgrade() -> None:
    op.add_column('classroom_camera_analyses', sa.Column('site_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'classroom_camera_analyses_site_id_fkey', 'classroom_camera_analyses', 'sites', ['site_id'], ['id']
    )
    op.create_index(
        'ix_classroom_camera_analyses_site_id', 'classroom_camera_analyses', ['site_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_classroom_camera_analyses_site_id', table_name='classroom_camera_analyses')
    op.drop_constraint('classroom_camera_analyses_site_id_fkey', 'classroom_camera_analyses', type_='foreignkey')
    op.drop_column('classroom_camera_analyses', 'site_id')
