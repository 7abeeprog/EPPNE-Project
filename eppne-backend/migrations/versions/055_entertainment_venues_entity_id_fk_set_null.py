# migrations/versions/055_entertainment_venues_entity_id_fk_set_null.py
from alembic import op
import sqlalchemy as sa

revision = '055_entertainment_venues_entity_id_fk_set_null'
down_revision = '054_create_achievement_tables'

# Expand فقط — راجع
# .claude/reports/entertainment-venue-endpoint-planning-session-log.md
# و.claude/reports/entertainment-venue-endpoint-implementation-session-log.md
# نفس نمط migration 051 (sports_organizations): entertainment_venues.entity_id
# كان عمود Integer عادي بفهرس بس (ix_venue_tenant لا يخصه، بل index=True
# منفصل على entity_id نفسه)، بدون أي ForeignKeyConstraint إطلاقًا — تأكَّد
# بالبحث الشامل في migrations/versions/*.py: الملف الوحيد اللي بيلمس
# entertainment_venues هو الـinitial migration (71820e4fe1f3)، صفر FK على
# entity_id فيه أو في أي migration لاحق. إضافة FK جديد بالكامل، مش تصحيح
# ondelete على قيد موجود.
#
# فُحصت البيانات الحالية قبل الكتابة (2026-09-16، DB المحلي للتطوير عبر
# asyncpg مباشرة): SELECT count(*) AS total, count(entity_id) AS non_null
# FROM entertainment_venues → total=4, non_null=0. التغيير آمن 100% — صفر
# backfill مطلوب، مفيش أي صف هيتأثر فورًا لأن العمود بالكامل NULL أصلًا.
# entity_id أصلًا nullable=True — مفيش تعديل nullable مطلوب هنا.


def upgrade() -> None:
    op.create_foreign_key(
        'fk_entertainment_venues_entity_id_sovereign_entities',
        'entertainment_venues', 'sovereign_entities_v2',
        ['entity_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_entertainment_venues_entity_id_sovereign_entities',
        'entertainment_venues',
        type_='foreignkey',
    )
