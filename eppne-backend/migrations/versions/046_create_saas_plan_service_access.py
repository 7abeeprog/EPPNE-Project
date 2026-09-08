# migrations/versions/046_create_saas_plan_service_access.py
from alembic import op
import sqlalchemy as sa

revision = '046_create_saas_plan_service_access'
down_revision = '045_create_affiliate_scopes_and_unify_commission'

# قرار تصميم موثَّق في PROGRESS_LOG.md ([2026-09-07] — قرار تصميم: توحيد
# check_feature_access/can_access_service عبر جدول many-to-many جديد):
# استبدال الاعتماد على plan.features (نص حر JSONB بلا schema enforcement)
# لتحديد الخدمات المتاحة لخطة معيّنة، بجدول ربط many-to-many صريح.
#
# هذه الـmigration فقط: إنشاء الجدول الجديد + جعل service_id nullable
# (Expand-Contract، خطوة Expand). صراحة بدون: حذف service_id، بدون أي
# تعديل على check_feature_access/can_access_service أو أي router.


def upgrade() -> None:
    # ========================================================
    # 1. saas_plan_service_access (جديد) — many-to-many بين plan وservice
    # ========================================================
    op.create_table(
        'saas_plan_service_access',
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('service_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['plan_id'], ['saas_service_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_id'], ['saas_service_catalog.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('plan_id', 'service_id'),
    )
    # index إضافي على service_id لوحده (البحث العكسي: "هل الخدمة دي متاحة
    # عبر أي plan؟") — الـPK المركّب (plan_id, service_id) لا يغطي هذا
    # النمط بكفاءة لأن service_id هو العمود الثاني في الـcomposite index.
    op.create_index(
        'ix_saas_plan_service_access_service_id',
        'saas_plan_service_access', ['service_id'], unique=False,
    )

    # ========================================================
    # 2. saas_service_plans.service_id: NOT NULL → nullable
    #    (Expand-Contract: العمود القديم يفضل موجود ومقروء، الحذف الفعلي
    #    مؤجَّل لـmigration منفصلة بعد تحقق grep إن صفر كود بيستخدمه)
    # ========================================================
    op.alter_column(
        'saas_service_plans', 'service_id',
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'saas_service_plans', 'service_id',
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_index('ix_saas_plan_service_access_service_id', table_name='saas_plan_service_access')
    op.drop_table('saas_plan_service_access')
