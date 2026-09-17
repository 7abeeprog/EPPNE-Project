# migrations/versions/059_manufacturing_facility_site_id.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '059_manufacturing_facility_site_id'
down_revision = '058_iot_smart_asset_site_id'

# استبدال كامل لـentity_id/location_gps القديمين بـsite_id (FK sites.id
# NOT NULL) في ManufacturingFacility — بحسب §1.4 من مستند التصميم.
# real_estate_unit_id بلا لمس (سؤال مختلف: على أي عقار مبني المصنع).
# ProductionLine (الطفل) بلا تعديل — لسه بيشاور facility_id عادي.
#
# سلسلة حذف كاملة موثَّقة (كل الصفوف بيانات throwaway/pilot مؤكَّدة —
# راجع تقرير التنفيذ لتفاصيل كل صف قبل الحذف):
# manufacturing_facilities (2 صف) ← production_lines (1) + product_blueprints (1)
# ← production_batches (1) ← material_consumption_logs/smart_product_items (0)
# + predictive_maintenance_logs/product_digital_twins (0)
# راجع: .claude/reports/unified-site-model-and-academy-camera-design-proposal.md


def upgrade() -> None:
    op.execute("""
        DELETE FROM material_consumption_logs WHERE batch_id IN (
            SELECT id FROM production_batches WHERE line_id IN (
                SELECT id FROM production_lines WHERE facility_id IN (SELECT id FROM manufacturing_facilities)
            ) OR product_blueprint_id IN (
                SELECT id FROM product_blueprints WHERE facility_id IN (SELECT id FROM manufacturing_facilities)
            )
        )
    """)
    op.execute("""
        DELETE FROM smart_product_items WHERE batch_id IN (
            SELECT id FROM production_batches WHERE line_id IN (
                SELECT id FROM production_lines WHERE facility_id IN (SELECT id FROM manufacturing_facilities)
            ) OR product_blueprint_id IN (
                SELECT id FROM product_blueprints WHERE facility_id IN (SELECT id FROM manufacturing_facilities)
            )
        )
    """)
    op.execute("""
        DELETE FROM predictive_maintenance_logs WHERE production_line_id IN (
            SELECT id FROM production_lines WHERE facility_id IN (SELECT id FROM manufacturing_facilities)
        )
    """)
    op.execute("""
        DELETE FROM product_digital_twins WHERE production_line_id IN (
            SELECT id FROM production_lines WHERE facility_id IN (SELECT id FROM manufacturing_facilities)
        )
    """)
    op.execute("""
        DELETE FROM production_batches WHERE line_id IN (
            SELECT id FROM production_lines WHERE facility_id IN (SELECT id FROM manufacturing_facilities)
        ) OR product_blueprint_id IN (
            SELECT id FROM product_blueprints WHERE facility_id IN (SELECT id FROM manufacturing_facilities)
        )
    """)
    op.execute("DELETE FROM production_lines WHERE facility_id IN (SELECT id FROM manufacturing_facilities)")
    op.execute("DELETE FROM product_blueprints WHERE facility_id IN (SELECT id FROM manufacturing_facilities)")
    op.execute("DELETE FROM manufacturing_facilities")

    op.add_column('manufacturing_facilities', sa.Column('site_id', sa.Integer(), nullable=False))
    op.create_foreign_key('manufacturing_facilities_site_id_fkey', 'manufacturing_facilities', 'sites', ['site_id'], ['id'])
    op.create_index('ix_manufacturing_facilities_site_id', 'manufacturing_facilities', ['site_id'], unique=False)
    op.create_index('ix_manufacturing_facility_site', 'manufacturing_facilities', ['site_id'], unique=False)

    op.drop_index('ix_manufacturing_facility_entity', table_name='manufacturing_facilities')
    op.drop_index('ix_manufacturing_facilities_entity_id', table_name='manufacturing_facilities')
    op.drop_column('manufacturing_facilities', 'entity_id')
    op.drop_column('manufacturing_facilities', 'location_gps')


def downgrade() -> None:
    op.add_column('manufacturing_facilities', sa.Column('location_gps', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('manufacturing_facilities', sa.Column('entity_id', sa.Integer(), nullable=True))
    op.create_index('ix_manufacturing_facilities_entity_id', 'manufacturing_facilities', ['entity_id'], unique=False)
    op.create_index('ix_manufacturing_facility_entity', 'manufacturing_facilities', ['entity_id'], unique=False)

    op.drop_index('ix_manufacturing_facility_site', table_name='manufacturing_facilities')
    op.drop_index('ix_manufacturing_facilities_site_id', table_name='manufacturing_facilities')
    op.drop_constraint('manufacturing_facilities_site_id_fkey', 'manufacturing_facilities', type_='foreignkey')
    op.drop_column('manufacturing_facilities', 'site_id')
