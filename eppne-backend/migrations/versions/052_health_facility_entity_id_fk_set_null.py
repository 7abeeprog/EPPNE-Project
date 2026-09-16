# migrations/versions/052_health_facility_entity_id_fk_set_null.py
from alembic import op
import sqlalchemy as sa

revision = '052_health_facility_entity_id_fk_set_null'
down_revision = '051_sports_organizations_entity_id_fk_set_null'

# Expand فقط — راجع
# .claude/reports/health-entity-membership-planning-session-log.md
# و.claude/reports/health-entity-membership-implementation-session-log.md
# نفس نمط migration 050/051: health_facilities.entity_id كان عمود Integer
# عادي بفهرس بس (ix_health_facilities_entity_id)، بدون أي
# ForeignKeyConstraint إطلاقًا (اتأكَّد مباشرة على \d health_facilities
# وقت التنفيذ — صفر قيد FK على الاسم، فقط FK على tenant_id). إضافة FK
# جديد بالكامل، مش تصحيح ondelete على قيد موجود.
#
# فُحصت البيانات الحالية قبل الكتابة (2026-09-14، DB المحلي للتطوير):
# صف واحد فقط في health_facilities حاليًا (id=1, name=p_ctor_health_facility)
# — بقية اختبار throwaway، مش بيانات إنتاجية. entity_id لهذا الصف NULL.
# التغيير آمن 100% — صفر backfill مطلوب. entity_id أصلًا nullable=True —
# مفيش تعديل nullable مطلوب هنا.


def upgrade() -> None:
    op.create_foreign_key(
        'fk_health_facilities_entity_id_sovereign_entities',
        'health_facilities', 'sovereign_entities_v2',
        ['entity_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_health_facilities_entity_id_sovereign_entities',
        'health_facilities',
        type_='foreignkey',
    )
