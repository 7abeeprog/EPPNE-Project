# migrations/versions/058_iot_smart_asset_site_id.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '058_iot_smart_asset_site_id'
down_revision = '057_create_sites_table'

# استبدال كامل لـentity_id/location_gps القديمين بـsite_id (FK sites.id
# NOT NULL) — بحسب §1.4 من مستند التصميم (iot لا مرحلة انتقالية، صفر
# بيانات حقيقية وقت التنفيذ). الصف الوحيد الموجود فعليًا
# (asset_code='P-CTOR-IOT-ASSET-1') بيانات اختبار throwaway مؤكَّدة
# (راجع تقرير خطوة تحقق التصميم الأول) — يُحذف بدل backfill بصف Site
# وهمي بلا معنى منتجي. صفر لمس على smart_farms/manufacturing_facilities/
# health_facilities في هذه الـmigration (كل دومين على حدة، بحسب الخطة).
# راجع: .claude/reports/unified-site-model-and-academy-camera-design-proposal.md


def upgrade() -> None:
    # اكتُشف أثناء التنفيذ: صف واحد في utility_readings (id=1, asset_id=1,
    # reading_type=BIOGAS, consumed_value=0) يشاور على smart_assets.id=1 —
    # نفس تاريخ إنشاء الصف الاختباري (2026-08-14)، نفس نمط بيانات throwaway
    # مؤكَّد. يُحذف أولًا لفكّ قيد FK قبل حذف smart_assets نفسه.
    op.execute("DELETE FROM utility_readings WHERE asset_id IN (SELECT id FROM smart_assets)")
    op.execute("DELETE FROM smart_assets")

    op.add_column('smart_assets', sa.Column('site_id', sa.Integer(), nullable=False))
    op.create_foreign_key('smart_assets_site_id_fkey', 'smart_assets', 'sites', ['site_id'], ['id'])
    op.create_index('ix_smart_assets_site_id', 'smart_assets', ['site_id'], unique=False)
    op.create_index('ix_smart_asset_site', 'smart_assets', ['site_id'], unique=False)

    op.drop_index('ix_smart_asset_entity', table_name='smart_assets')
    op.drop_index('ix_smart_assets_entity_id', table_name='smart_assets')
    op.drop_column('smart_assets', 'entity_id')
    op.drop_column('smart_assets', 'location_gps')


def downgrade() -> None:
    op.add_column('smart_assets', sa.Column('location_gps', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('smart_assets', sa.Column('entity_id', sa.Integer(), nullable=True))
    op.create_index('ix_smart_assets_entity_id', 'smart_assets', ['entity_id'], unique=False)
    op.create_index('ix_smart_asset_entity', 'smart_assets', ['entity_id'], unique=False)

    op.drop_index('ix_smart_asset_site', table_name='smart_assets')
    op.drop_index('ix_smart_assets_site_id', table_name='smart_assets')
    op.drop_constraint('smart_assets_site_id_fkey', 'smart_assets', type_='foreignkey')
    op.drop_column('smart_assets', 'site_id')
