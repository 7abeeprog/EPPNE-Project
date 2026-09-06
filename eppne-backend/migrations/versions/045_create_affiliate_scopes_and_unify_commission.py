# migrations/versions/045_create_affiliate_scopes_and_unify_commission.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '045_create_affiliate_scopes_and_unify_commission'
down_revision = '044_create_transport_tables'

# جلسة referral-affiliate-unified-system-implementation (2026-09-06):
# توحيد نظامي الإحالة/العمولة الثلاثة (A/B/C، راجع
# .claude/reports/referral-affiliate-unified-implementation-session-log.md)
# على نظام A (affiliate domain) بمفهوم AffiliateScope جديد بدل ربط
# ReferralTree/CommissionTier مباشرة بـproduct_id.
#
# TRUNCATE صريح (بموافقة المستخدم): referral_trees/affiliate_commissions/
# affiliate_commission_tiers تحتوي فقط بيانات اختبارية (مؤكَّد من
# .claude/plans/phase10-audit-affiliate-report.md — صف CommissionTier
# تجريبي تحت tenant_id=5 لم يُنظَّف بعد). لا عملاء إنتاج — لا حاجة
# لـbackfill منطقي من entity_type القديم (GLOBAL/PRODUCT/COURSE) إلى
# scopes جديدة. هذا يسمح أيضًا بإضافة FK/NOT NULL صارمة مباشرة بلا
# مخاطرة على بيانات حقيقية.


def upgrade() -> None:
    # ========================================================
    # 0. تفريغ الجداول الثلاثة المتأثرة ببنية scope الجديدة
    #    (بيانات اختبارية بحتة — راجع التعليق أعلاه)
    # ========================================================
    op.execute(
        "TRUNCATE TABLE affiliate_commissions, affiliate_commission_tiers, "
        "referral_trees RESTART IDENTITY CASCADE"
    )

    # ========================================================
    # 1. affiliate_scopes (جديد)
    # ========================================================
    # scope_type: PostgreSQL ENUM حقيقي (نفس نمط transport/vehicle_type
    # في migration 044) — وليس String حر، لمنع أي قيمة غير الثلاث
    # المعروفة على مستوى DB نفسه، مش بس تحقق تطبيقي.
    # ملاحظة: لا نستدعي .create() يدويًا هنا — SQLAlchemy/Alembic ينشئ
    # الـENUM تلقائيًا كجزء من create_table() أدناه (نفس نمط
    # vehicle_type/vehiclestatus في migration 044). استدعاء .create()
    # يدويًا هنا يسبب DuplicateObjectError لأن create_table تحاول
    # إنشاءه مرة تانية (مؤكَّد بالتنفيذ الفعلي — أول محاولة تطبيق فشلت
    # بالضبط بهذا الخطأ، رُصدت هنا للتوثيق).
    affiliate_scope_type_enum = postgresql.ENUM(
        'SINGLE_PRODUCT', 'PRODUCT_GROUP', 'ENTITY_WIDE',
        name='affiliatescopetype',
    )

    op.create_table(
        'affiliate_scopes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('scope_type', affiliate_scope_type_enum, nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_affiliate_scopes_id', 'affiliate_scopes', ['id'], unique=False)
    op.create_index('ix_affiliate_scopes_tenant_id', 'affiliate_scopes', ['tenant_id'], unique=False)
    op.create_index('ix_affiliate_scopes_scope_type', 'affiliate_scopes', ['scope_type'], unique=False)
    # نطاق ENTITY_WIDE واحد فقط لكل tenant (يُنشأ تلقائيًا وقت تفعيل
    # خدمة affiliate كـSaaS — راجع Phase 7 في تقرير الجلسة)
    op.create_index(
        'ix_affiliate_scopes_tenant_entity_wide_unique',
        'affiliate_scopes',
        ['tenant_id'],
        unique=True,
        postgresql_where=sa.text("scope_type = 'ENTITY_WIDE'"),
    )

    # ========================================================
    # 2. affiliate_scope_members (جديد)
    # ========================================================
    op.create_table(
        'affiliate_scope_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('scope_id', sa.Integer(), nullable=False),
        sa.Column('member_type', sa.String(length=30), nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['scope_id'], ['affiliate_scopes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_affiliate_scope_members_id', 'affiliate_scope_members', ['id'], unique=False)
    op.create_index('ix_affiliate_scope_members_scope_id', 'affiliate_scope_members', ['scope_id'], unique=False)
    # باج تصميمي اكتُشف أثناء الجلسة: unique index بسيط على
    # (member_type, member_id) لا يمنع تكرار عضو "على مستوى الدومين
    # كله" (member_id IS NULL) — لأن Postgres يعتبر NULL != NULL في
    # unique index عادي. الحل: index جزئي لكل حالة على حدة.
    op.create_index(
        'ix_affiliate_scope_members_unique_typed',
        'affiliate_scope_members',
        ['member_type', 'member_id'],
        unique=True,
        postgresql_where=sa.text('member_id IS NOT NULL'),
    )
    op.create_index(
        'ix_affiliate_scope_members_unique_untyped',
        'affiliate_scope_members',
        ['member_type'],
        unique=True,
        postgresql_where=sa.text('member_id IS NULL'),
    )

    # ========================================================
    # 3. affiliate_commission_tiers: target_product_id → target_scope_id
    # ========================================================
    # اسم الـFK القديم غير مُسمَّى صراحة وقت الإنشاء الأصلي
    # (71820e4fe1f3_initial_migration_all_34_sectors_final.py:4603) —
    # الاسم التالي هو تسمية Postgres التلقائية القياسية لقيد بلا اسم
    # صريح (<table>_<column>_fkey). إن كانت قاعدة بياناتك الفعلية تحمل
    # اسمًا مختلفًا (تحقق بـ`\d affiliate_commission_tiers` في psql قبل
    # التطبيق)، هذا السطر سيفشل بوضوح (خطأ صريح، لا صمت) ويحتاج تصحيح
    # الاسم هنا قبل إعادة المحاولة.
    op.drop_constraint(
        'affiliate_commission_tiers_target_product_id_fkey',
        'affiliate_commission_tiers',
        type_='foreignkey',
    )
    op.drop_index('ix_affiliate_commission_tiers_unique', table_name='affiliate_commission_tiers')
    op.drop_index('ix_affiliate_commission_tiers_target_product', table_name='affiliate_commission_tiers')

    op.alter_column(
        'affiliate_commission_tiers', 'target_product_id',
        new_column_name='target_scope_id',
    )

    op.create_foreign_key(
        'fk_affiliate_commission_tiers_target_scope_id_affiliate_scopes',
        'affiliate_commission_tiers', 'affiliate_scopes',
        ['target_scope_id'], ['id'], ondelete='CASCADE',
    )
    op.create_index(
        'ix_affiliate_commission_tiers_target_scope',
        'affiliate_commission_tiers', ['target_scope_id'], unique=False,
    )
    op.create_index(
        'ix_affiliate_commission_tiers_unique',
        'affiliate_commission_tiers', ['tenant_id', 'entity_type', 'target_scope_id'],
        unique=True,
    )

    # ========================================================
    # 4. affiliate_commissions: تعميم المصدر (order-only → أي حدث بيع)
    # ========================================================
    op.alter_column('affiliate_commissions', 'order_id', nullable=True)
    op.alter_column('affiliate_commissions', 'order_item_id', nullable=True)
    op.alter_column('affiliate_commissions', 'product_id', nullable=True)

    op.add_column(
        'affiliate_commissions',
        sa.Column('source_type', sa.String(length=30), nullable=False),
    )
    op.add_column(
        'affiliate_commissions',
        sa.Column('source_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'affiliate_commissions',
        sa.Column('scope_id', sa.Integer(), nullable=False),
    )
    op.create_foreign_key(
        'fk_affiliate_commissions_scope_id_affiliate_scopes',
        'affiliate_commissions', 'affiliate_scopes',
        ['scope_id'], ['id'], ondelete='RESTRICT',
    )
    op.create_index('ix_affiliate_commissions_scope_id', 'affiliate_commissions', ['scope_id'], unique=False)
    op.create_index('ix_affiliate_commissions_source_type', 'affiliate_commissions', ['source_type'], unique=False)

    # ========================================================
    # 5. referral_trees: entity_id يشير الآن لـaffiliate_scopes.id
    #    (لا تغيير بنيوي على العمود نفسه — فقط إضافة FK حقيقي، آمن
    #    الآن بعد التفريغ في الخطوة 0)
    # ========================================================
    op.create_foreign_key(
        'fk_referral_trees_entity_id_affiliate_scopes',
        'referral_trees', 'affiliate_scopes',
        ['entity_id'], ['id'], ondelete='CASCADE',
    )

    # ========================================================
    # 6. حذف ActionCommission (نظام C القديم — زائد بعد التعميم، قرار
    #    معتمد صراحة من المستخدم في جلسة design)
    # ========================================================
    op.drop_table('affiliate_action_commissions')

    # ========================================================
    # 7. حذف نظام B بالكامل (commerce.AffiliateTree/CommissionRecord/
    #    AffiliateConfig) — قرار معتمد صراحة، لا عملاء إنتاج
    # ========================================================
    op.drop_table('affiliate_trees')
    op.drop_table('commission_records')
    op.drop_table('affiliate_configs')

    # ========================================================
    # 8. users.referred_by_user_id — مصدر "من أحال من" الموحَّد للـ12
    #    دومين (immutable بعد التسجيل، مفروض على مستوى التطبيق فقط)
    # ========================================================
    op.add_column(
        'users',
        sa.Column('referred_by_user_id', sa.BigInteger(), nullable=True),
    )
    op.create_index('ix_users_referred_by_user_id', 'users', ['referred_by_user_id'], unique=False)
    op.create_foreign_key(
        'fk_users_referred_by_user_id_users',
        'users', 'users',
        ['referred_by_user_id'], ['id'], ondelete='SET NULL',
    )

    # ========================================================
    # 9. Seed: تسجيل affiliate كخدمة SaaS + خطة افتراضية مجانية —
    #    بدونها require_subscription("affiliate") يرجع False دائمًا
    #    لأي tenant، بغض النظر عن صحة أي كود آخر (Phase 7 غير قابلة
    #    للاستخدام بدون هذا الصف)
    # ========================================================
    op.execute(
        """
        INSERT INTO saas_service_catalog (name, code, description, is_active, created_at)
        VALUES ('Affiliate Program', 'affiliate', 'برنامج الإحالة والعمولات متعددة المستويات (10 مستويات، مربوط بنطاقات)', true, now())
        ON CONFLICT (code) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO saas_service_plans (
            service_id, name, code, price_monthly, price_yearly, currency,
            features, max_users, max_products, max_courses, is_active,
            created_at, updated_at
        )
        SELECT id, 'الخطة الافتراضية (مجانية)', 'default', 0, 0, 'MR_USDT',
               '[]'::jsonb, 10, 50, 20, true, now(), now()
        FROM saas_service_catalog WHERE code = 'affiliate'
        ON CONFLICT (service_id, code) DO NOTHING
        """
    )


def downgrade() -> None:
    # ⚠️ عكس seed الـSaaS (خطوة 9 في upgrade) — عمدًا **غير مُنفَّذ** هنا.
    # مؤكَّد بالتنفيذ الفعلي (round-trip test، 2026-09-06): DB فيها بيانات
    # اختبارية سابقة غير مرتبطة بهذه الـmigration تحت نفس code='affiliate'
    # (صف saas_service_catalog id=48 باسم TEST_REQSECTOR_AFFILIATE_SERVICE
    # من جلسة require_sector سابقة، upgrade هنا احترمه بـON CONFLICT DO
    # NOTHING ولم يكتب فوقه) — بما فيها خطة `test_reqsector_affiliate_plan`
    # (id=48) **مرتبطة فعليًا بـsaas_tenant_subscriptions.id=49 (tenant_id=16،
    # ACTIVE)**. أول محاولة downgrade فعلية بـ`DELETE ... WHERE code=
    # 'affiliate'` فشلت بـForeignKeyViolationError على هذا الاشتراك الحي
    # (تفصيل الفشل والدليل الكامل موثَّق في
    # .claude/reports/referral-affiliate-unified-implementation-phase0-execution-session-log.md).
    # بما إن `ON CONFLICT DO NOTHING` يمنعنا من التمييز بين "صف أنشأته
    # هذه الـmigration" و"صف كان موجودًا مسبقًا"، الحذف غير آمن مبدئيًا —
    # نفس فلسفة عدم قابلية التراجع عن TRUNCATE في الخطوة 0 تحت.

    # ⚠️ التفريغ في الخطوة 0 من upgrade() غير قابل للتراجع — أي بيانات
    # كانت موجودة في affiliate_commissions/affiliate_commission_tiers/
    # referral_trees وقت الترقية ضائعة نهائيًا. هذا downgrade يعيد
    # الشكل البنيوي فقط (بجداول فارغة)، وليس أي بيانات.

    op.drop_constraint('fk_users_referred_by_user_id_users', 'users', type_='foreignkey')
    op.drop_index('ix_users_referred_by_user_id', table_name='users')
    op.drop_column('users', 'referred_by_user_id')

    # --- إعادة إنشاء نظام B (commerce) كما كان تمامًا ---
    op.create_table(
        'affiliate_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('level_1_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('level_2_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('level_3_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('level_4_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('level_5_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('level_6_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('level_7_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('level_8_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('level_9_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('level_10_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('system_fee_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_affiliate_configs_id'), 'affiliate_configs', ['id'], unique=False)
    op.create_index(op.f('ix_affiliate_configs_tenant_id'), 'affiliate_configs', ['tenant_id'], unique=False)

    op.create_table(
        'commission_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('beneficiary_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('level_earned', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=30, scale=8), nullable=False),
        sa.Column('currency', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('release_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('release_tx_hash', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['beneficiary_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_commission_records_beneficiary_id'), 'commission_records', ['beneficiary_id'], unique=False)
    op.create_index(op.f('ix_commission_records_id'), 'commission_records', ['id'], unique=False)
    op.create_index('ix_commission_records_level_earned', 'commission_records', ['level_earned'], unique=False)
    op.create_index('ix_commission_records_order_id', 'commission_records', ['order_id'], unique=False)
    op.create_index('ix_commission_records_status', 'commission_records', ['status'], unique=False)

    op.create_table(
        'affiliate_trees',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('sponsor_id', sa.Integer(), nullable=False),
        sa.Column('network_depth', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['sponsor_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_affiliate_trees_id'), 'affiliate_trees', ['id'], unique=False)
    op.create_index('ix_affiliate_trees_network_depth', 'affiliate_trees', ['network_depth'], unique=False)
    op.create_index(op.f('ix_affiliate_trees_sponsor_id'), 'affiliate_trees', ['sponsor_id'], unique=False)
    op.create_index(op.f('ix_affiliate_trees_user_id'), 'affiliate_trees', ['user_id'], unique=True)

    # --- إعادة إنشاء ActionCommission كما كان ---
    op.create_table(
        'affiliate_action_commissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('affiliate_profile_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(30, 8), nullable=False),
        sa.Column('currency', sa.String(length=20), nullable=False, server_default='MR_USDT'),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_tx_hash', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['affiliate_profile_id'], ['affiliate_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_affiliate_action_commissions_tenant_id', 'affiliate_action_commissions', ['tenant_id'])
    op.create_index('ix_affiliate_action_commissions_affiliate_profile_id', 'affiliate_action_commissions', ['affiliate_profile_id'])
    op.create_index('ix_affiliate_action_commissions_user_id', 'affiliate_action_commissions', ['user_id'])
    op.create_index('ix_affiliate_action_commissions_status', 'affiliate_action_commissions', ['status'])
    op.create_index('ix_affiliate_action_commissions_entity_type', 'affiliate_action_commissions', ['entity_type'])
    op.create_index('ix_affiliate_action_commissions_created_at', 'affiliate_action_commissions', ['created_at'])

    # --- عكس تعديلات referral_trees ---
    op.drop_constraint('fk_referral_trees_entity_id_affiliate_scopes', 'referral_trees', type_='foreignkey')

    # --- عكس تعديلات affiliate_commissions ---
    op.drop_index('ix_affiliate_commissions_source_type', table_name='affiliate_commissions')
    op.drop_index('ix_affiliate_commissions_scope_id', table_name='affiliate_commissions')
    op.drop_constraint('fk_affiliate_commissions_scope_id_affiliate_scopes', 'affiliate_commissions', type_='foreignkey')
    op.drop_column('affiliate_commissions', 'scope_id')
    op.drop_column('affiliate_commissions', 'source_id')
    op.drop_column('affiliate_commissions', 'source_type')
    op.alter_column('affiliate_commissions', 'product_id', nullable=False)
    op.alter_column('affiliate_commissions', 'order_item_id', nullable=False)
    op.alter_column('affiliate_commissions', 'order_id', nullable=False)

    # --- عكس تعديلات affiliate_commission_tiers ---
    op.drop_index('ix_affiliate_commission_tiers_unique', table_name='affiliate_commission_tiers')
    op.drop_index('ix_affiliate_commission_tiers_target_scope', table_name='affiliate_commission_tiers')
    op.drop_constraint(
        'fk_affiliate_commission_tiers_target_scope_id_affiliate_scopes',
        'affiliate_commission_tiers', type_='foreignkey',
    )
    op.alter_column(
        'affiliate_commission_tiers', 'target_scope_id',
        new_column_name='target_product_id',
    )
    op.create_foreign_key(
        'affiliate_commission_tiers_target_product_id_fkey',
        'affiliate_commission_tiers', 'products',
        ['target_product_id'], ['id'], ondelete='CASCADE',
    )
    op.create_index('ix_affiliate_commission_tiers_target_product', 'affiliate_commission_tiers', ['target_product_id'], unique=False)
    op.create_index(
        'ix_affiliate_commission_tiers_unique',
        'affiliate_commission_tiers', ['tenant_id', 'entity_type', 'target_product_id'],
        unique=True,
    )

    # --- حذف الجداول الجديدة ---
    op.drop_table('affiliate_scope_members')
    op.drop_table('affiliate_scopes')
    postgresql.ENUM(name='affiliatescopetype').drop(op.get_bind(), checkfirst=True)
