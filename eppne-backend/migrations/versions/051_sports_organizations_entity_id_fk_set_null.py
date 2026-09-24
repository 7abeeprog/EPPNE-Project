# migrations/versions/051_sports_organizations_entity_id_fk_set_null.py
from alembic import op
import sqlalchemy as sa

revision = '051_sports_organizations_entity_id_fk_set_null'
down_revision = '050_transport_entity_id_fk_set_null'

# Expand فقط — راجع
# .claude/reports/tourism-sports-entity-membership-planning-session-log.md
# و.claude/reports/tourism-sports-entity-membership-implementation-session-log.md
# نفس نمط migration 050 (transport): sports_organizations.entity_id كان
# عمود Integer عادي بفهرس بس (ix_sports_organizations_entity_id)، بدون أي
# ForeignKeyConstraint إطلاقًا (اتأكَّد مباشرة على \d sports_organizations
# وقت التنفيذ — صفر قيد FK على الاسم). إضافة FK جديد بالكامل، مش تصحيح
# ondelete على قيد موجود.
#
# فُحصت البيانات الحالية قبل الكتابة (2026-09-14، DB المحلي للتطوير):
# 12 صف حقيقي في sports_organizations حاليًا — لكنها كلها بقايا اختبار
# throwaway (أسماء P-TOURISM-VERIFY-*/REGTEST-*، tenant_id=1 لكل الصفوف)
# وليست بيانات إنتاجية. الأهم: entity_id كله NULL بلا استثناء في الـ12
# صف (SELECT count(*) AS total, count(entity_id) AS non_null FROM
# sports_organizations → total=12, non_null=0). التغيير آمن 100% —
# صفر backfill مطلوب، مفيش أي صف هيتأثر فورًا لأن العمود بالكامل NULL
# أصلًا. entity_id أصلًا nullable=True — مفيش تعديل nullable مطلوب هنا
# (خلافًا لـfleets.entity_id في migration 050 اللي احتاج alter_column).


def upgrade() -> None:
    op.create_foreign_key(
        'fk_sports_organizations_entity_id_sovereign_entities',
        'sports_organizations', 'sovereign_entities_v2',
        ['entity_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_sports_organizations_entity_id_sovereign_entities',
        'sports_organizations',
        type_='foreignkey',
    )
