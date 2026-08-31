# migrations/versions/043_add_marketing_fields_to_property_units.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '043_add_marketing_fields_to_property_units'
down_revision = '042_add_held_balances_to_wallets'

property_status_enum = postgresql.ENUM(
    'AVAILABLE', 'SOLD', 'RENTED', 'UNDER_CONSTRUCTION',
    name='propertystatus',
    create_type=False,
)


def upgrade() -> None:
    # جلسة realestate-hooks-layer-design-decision (2026-08-31): الفرونت إند
    # (property/[id]/page.tsx وغيره) يفترض شكل "Property" تسويقي/عرضي
    # (عنوان، صورة غلاف، موقع، وصف، حالة عرض) بينما property_units كيان
    # بنيوي بحت (رقم وحدة، طابق، مساحة). القرار المعتمَد: امتداد Schema
    # طبيعي على نفس الجدول بدل إنشاء كيان "Property" منفصل يكرر البيانات.
    op.add_column('property_units', sa.Column('title', sa.String(length=255), nullable=True))
    op.add_column('property_units', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('property_units', sa.Column('location', sa.String(length=255), nullable=True))
    op.add_column('property_units', sa.Column('cover_image_url', sa.Text(), nullable=True))

    # نوع الـEnum لازم يُنشأ صراحة (CREATE TYPE) قبل استخدامه في add_column —
    # على عكس create_table، عمود مُضاف عبر add_column لا ينشئ نوع الـEnum
    # الأصلي تلقائيًا (مؤكَّد حيًا: أول محاولة بدون هذا السطر فشلت بـ
    # `UndefinedObjectError: type "propertystatus" does not exist`، والـDDL
    # كلها اتلفت (transactional DDL) — صفر أعمدة بقيت معلَّقة).
    property_status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'property_units',
        sa.Column('status', property_status_enum, nullable=False, server_default=sa.text("'AVAILABLE'")),
    )


def downgrade() -> None:
    op.drop_column('property_units', 'status')
    op.drop_column('property_units', 'cover_image_url')
    op.drop_column('property_units', 'location')
    op.drop_column('property_units', 'description')
    op.drop_column('property_units', 'title')
    property_status_enum.drop(op.get_bind(), checkfirst=True)
