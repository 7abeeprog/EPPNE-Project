# migrations/versions/060_agritech_smartfarm_site_id.py
from alembic import op
import sqlalchemy as sa

revision = '060_agritech_smartfarm_site_id'
down_revision = '059_manufacturing_facility_site_id'

# إضافة صافية لـsite_id (FK sites.id NOT NULL) في SmartFarm — بعكس
# iot/manufacturing، دي مش استبدال: مفيش location_gps أصلًا، و entity_id
# (ميت، بلا FK) بلا لمس عمدًا (راجع backlog
# agritech-smartfarm-unused-entity-id-column). land_asset_id بلا لمس.
# بحسب §1.4 من مستند التصميم.
#
# سلسلة حذف كاملة موثَّقة قبل فرض NOT NULL (صف throwaway واحد فقط، نمط
# تسمية REGTEST-* واضح، نفس تاريخ 2026-09-03 عبر كل السلسلة):
# smart_farms (1) ← farm_zones (1) ← crop_cycles (1) + bio_asset_cohorts (1)
#   + soil_sensor_readings (1)
# ← harvest_batches (1, من crop_cycles) + bio_product_yields (1, من bio_asset_cohorts)
# ← supply_chain_stages (1) + traceability_qrs (1) (traceable_type=HARVEST)
# + agricultural_certificates (1, certified_entity_type=FARM)
# راجع: .claude/reports/unified-site-model-and-academy-camera-design-proposal.md


def upgrade() -> None:
    op.execute("""
        DELETE FROM supply_chain_stages WHERE traceable_type = 'HARVEST' AND traceable_id IN (
            SELECT id FROM harvest_batches WHERE cycle_id IN (
                SELECT id FROM crop_cycles WHERE zone_id IN (
                    SELECT id FROM farm_zones WHERE farm_id IN (SELECT id FROM smart_farms)
                )
            )
        )
    """)
    op.execute("""
        DELETE FROM traceability_qrs WHERE traceable_type = 'HARVEST' AND traceable_id IN (
            SELECT id FROM harvest_batches WHERE cycle_id IN (
                SELECT id FROM crop_cycles WHERE zone_id IN (
                    SELECT id FROM farm_zones WHERE farm_id IN (SELECT id FROM smart_farms)
                )
            )
        )
    """)
    op.execute("""
        DELETE FROM agricultural_certificates WHERE certified_entity_type = 'FARM' AND certified_entity_id IN (
            SELECT id FROM smart_farms
        )
    """)
    op.execute("""
        DELETE FROM bio_product_yields WHERE cohort_id IN (
            SELECT id FROM bio_asset_cohorts WHERE zone_id IN (
                SELECT id FROM farm_zones WHERE farm_id IN (SELECT id FROM smart_farms)
            )
        ) OR destination_farm_id IN (SELECT id FROM smart_farms)
    """)
    op.execute("""
        DELETE FROM harvest_batches WHERE cycle_id IN (
            SELECT id FROM crop_cycles WHERE zone_id IN (
                SELECT id FROM farm_zones WHERE farm_id IN (SELECT id FROM smart_farms)
            )
        )
    """)
    op.execute("""
        DELETE FROM bio_asset_cohorts WHERE zone_id IN (
            SELECT id FROM farm_zones WHERE farm_id IN (SELECT id FROM smart_farms)
        )
    """)
    op.execute("""
        DELETE FROM soil_sensor_readings WHERE zone_id IN (
            SELECT id FROM farm_zones WHERE farm_id IN (SELECT id FROM smart_farms)
        )
    """)
    op.execute("""
        DELETE FROM crop_cycles WHERE zone_id IN (
            SELECT id FROM farm_zones WHERE farm_id IN (SELECT id FROM smart_farms)
        )
    """)
    op.execute("DELETE FROM farm_zones WHERE farm_id IN (SELECT id FROM smart_farms)")
    op.execute("DELETE FROM smart_farms")

    op.add_column('smart_farms', sa.Column('site_id', sa.Integer(), nullable=False))
    op.create_foreign_key('smart_farms_site_id_fkey', 'smart_farms', 'sites', ['site_id'], ['id'])
    op.create_index('ix_smart_farms_site_id', 'smart_farms', ['site_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_smart_farms_site_id', table_name='smart_farms')
    op.drop_constraint('smart_farms_site_id_fkey', 'smart_farms', type_='foreignkey')
    op.drop_column('smart_farms', 'site_id')
