# migrations/versions/065_classroom_camera_analysis_site_id_not_null.py
from alembic import op
import sqlalchemy as sa

revision = '065_classroom_camera_analysis_site_id_not_null'
down_revision = '064_create_ward_consent_settings_table'

# launch gate من migration 062: site_id كان nullable مؤقتًا لحد "أول
# استخدام إنتاجي فعلي للكاميرا" — هذه اللحظة (endpoint الاستقبال
# الحقيقي مبني في نفس هذه الدفعة). تأكَّد مباشرة وقت التنفيذ: 0 صف في
# الجدول كله (صفر صف بـsite_id=NULL بالتبعية) — صفر DELETE/backfill
# مطلوب.


def upgrade() -> None:
    op.alter_column('classroom_camera_analyses', 'site_id', existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    op.alter_column('classroom_camera_analyses', 'site_id', existing_type=sa.Integer(), nullable=True)
