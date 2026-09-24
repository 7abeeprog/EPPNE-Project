# migrations/versions/050_transport_entity_id_fk_set_null.py
from alembic import op
import sqlalchemy as sa

revision = '050_transport_entity_id_fk_set_null'
down_revision = '049_insurance_issuer_entity_id_set_null'

# Expand فقط — راجع
# .claude/reports/transport-entity-membership-full-implementation-session-log.md
# و.claude/reports/transport-entity-membership-full-implementation-planning-session-log.md
# (بند 3): fleets.entity_id وtransport_hubs.entity_id كانا عمودي Integer
# عاديين بفهرس بس، بدون أي ForeignKeyConstraint إطلاقًا (اتأكَّد مباشرة
# على pg_constraint وقت التخطيط — صفر قيد FK على الاسمين، بس
# ix_fleets_entity_id/ix_transport_hubs_entity_id). خلافًا لـmigration 049
# (insurance)، مفيش drop_constraint مطلوب هنا — الإضافة FK جديد بالكامل،
# مش تصحيح ondelete على قيد موجود.
#
# فُحصت البيانات الحالية قبل الكتابة (2026-09-11، DB المحلي للتطوير):
# صفر صف في fleets وصفر صف في transport_hubs — التغيير آمن 100%، مفيش
# أي صف هيتأثر فورًا.
#
# fleets.entity_id كانت nullable=False — لازم nullable=True هنا عشان
# ondelete='SET NULL' يقدر يشتغل فعليًا (تناقض DB-level وإلا: عمود
# NOT NULL مايقدرش ياخد NULL حتى لو الـFK بيطلب كده).
# transport_hubs.entity_id أصلًا nullable=True — مفيش تعديل nullable لها.


def upgrade() -> None:
    op.alter_column(
        'fleets', 'entity_id',
        existing_type=sa.Integer(), nullable=True,
    )
    op.create_foreign_key(
        'fk_fleets_entity_id_sovereign_entities',
        'fleets', 'sovereign_entities_v2',
        ['entity_id'], ['id'], ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_transport_hubs_entity_id_sovereign_entities',
        'transport_hubs', 'sovereign_entities_v2',
        ['entity_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_transport_hubs_entity_id_sovereign_entities',
        'transport_hubs',
        type_='foreignkey',
    )
    op.drop_constraint(
        'fk_fleets_entity_id_sovereign_entities',
        'fleets',
        type_='foreignkey',
    )
    op.alter_column(
        'fleets', 'entity_id',
        existing_type=sa.Integer(), nullable=False,
    )
