# migrations/versions/061_health_facility_site_id.py
from alembic import op
import sqlalchemy as sa

revision = '061_health_facility_site_id'
down_revision = '060_agritech_smartfarm_site_id'

# إضافة صافية لـsite_id (FK sites.id NOT NULL) في HealthFacility —
# الاستثناء الوحيد بحسب §1.4 من مستند التصميم: entity_id هنا FK حقيقي
# لـsovereign_entities_v2 (migration 052، مجهود health entity-membership
# hardening مُغلَق) وبلا لمس إطلاقًا. صفر location_gps هنا من الأساس.
#
# سلسلة حذف كاملة موثَّقة قبل فرض NOT NULL (صف throwaway واحد فقط، نمط
# تسمية p_ctor_* واضح، نفس تاريخ 2026-08-14 عبر السلسلة):
# health_facilities (1) ← medical_appointments (1, facility_id)
#   ← health_consultations (0, appointment_id)
# + facility_departments (0) + emergency_dispatches (0)
# entity_id لهذا الصف كان NULL من الأساس — صفر تأثير على sovereign_entities_v2.
# راجع: .claude/reports/unified-site-model-and-academy-camera-design-proposal.md


def upgrade() -> None:
    op.execute("""
        DELETE FROM health_consultations WHERE appointment_id IN (
            SELECT id FROM medical_appointments WHERE facility_id IN (SELECT id FROM health_facilities)
        )
    """)
    op.execute("DELETE FROM medical_appointments WHERE facility_id IN (SELECT id FROM health_facilities)")
    op.execute("DELETE FROM facility_departments WHERE facility_id IN (SELECT id FROM health_facilities)")
    op.execute("DELETE FROM emergency_dispatches WHERE facility_id IN (SELECT id FROM health_facilities)")
    op.execute("DELETE FROM health_facilities")

    op.add_column('health_facilities', sa.Column('site_id', sa.Integer(), nullable=False))
    op.create_foreign_key('health_facilities_site_id_fkey', 'health_facilities', 'sites', ['site_id'], ['id'])
    op.create_index('ix_health_facilities_site_id', 'health_facilities', ['site_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_health_facilities_site_id', table_name='health_facilities')
    op.drop_constraint('health_facilities_site_id_fkey', 'health_facilities', type_='foreignkey')
    op.drop_column('health_facilities', 'site_id')
