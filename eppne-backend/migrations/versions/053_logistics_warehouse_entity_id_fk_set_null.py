# migrations/versions/053_logistics_warehouse_entity_id_fk_set_null.py
from alembic import op
import sqlalchemy as sa

revision = '053_logistics_warehouse_entity_id_fk_set_null'
down_revision = '052_health_facility_entity_id_fk_set_null'

# Expand فقط — راجع
# .claude/reports/logistics-entity-membership-planning-session-log.md
# و.claude/reports/logistics-entity-membership-implementation-session-log.md
# نفس نمط migration 050/051/052: logistics_warehouses.entity_id كان عمود
# Integer عادي بفهرس بس (ix_logistics_warehouses_entity_id)، بدون أي
# ForeignKeyConstraint إطلاقًا (اتأكَّد مباشرة على \d logistics_warehouses
# وقت التخطيط والتنفيذ — صفر قيد FK على الاسم، فقط FK على tenant_id/
# created_by/manager_id). إضافة FK جديد بالكامل، مش تصحيح ondelete على
# قيد موجود.
#
# فُحصت البيانات الحالية قبل الكتابة (2026-09-14، DB المحلي للتطوير):
# صف واحد فقط في logistics_warehouses حاليًا (id=5, tenant_id=16,
# LOGISTICS-CANACCESS-PILOT-TENANT16) — بقية اختبار throwaway، مش بيانات
# إنتاجية. entity_id لهذا الصف NULL. التغيير آمن 100% — صفر backfill
# مطلوب. entity_id أصلًا nullable=True — مفيش تعديل nullable مطلوب هنا.


def upgrade() -> None:
    op.create_foreign_key(
        'fk_logistics_warehouses_entity_id_sovereign_entities',
        'logistics_warehouses', 'sovereign_entities_v2',
        ['entity_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_logistics_warehouses_entity_id_sovereign_entities',
        'logistics_warehouses',
        type_='foreignkey',
    )
