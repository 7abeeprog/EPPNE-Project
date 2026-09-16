# migrations/versions/054_create_achievement_tables.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '054_create_achievement_tables'
down_revision = '053_logistics_warehouse_entity_id_fk_set_null'

# أساس نظام الإنجازات (achievements) — دومين جديد بالكامل، لا يمس أي
# جدول قائم. 3 جداول فقط، صفر منطق شبكة/AUTO_EVENT فعلي في هذه المرحلة
# (trigger_type=AUTO_EVENT قابل للتخزين كقيمة enum لكن مفيش أي كود بيقرأه
# أو يستهلكه بعد — المرحلة القادمة). راجع:
# .claude/reports/achievements-foundation-implementation-session-log.md


def upgrade() -> None:
    # ========================================================
    # 1. achievement_definitions
    # ========================================================
    achievement_category_enum = postgresql.ENUM(
        'TRAINING', 'TEAM_BUILDING', 'PROJECT_FUNDING',
        name='achievementcategory',
    )
    achievement_trigger_type_enum = postgresql.ENUM(
        'MANUAL', 'AUTO_EVENT',
        name='achievementtriggertype',
    )

    op.create_table(
        'achievement_definitions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', achievement_category_enum, nullable=False),
        sa.Column('icon_url', sa.String(length=512), nullable=True),
        sa.Column('points_value', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('trigger_type', achievement_trigger_type_enum, nullable=False, server_default='MANUAL'),
        sa.Column('trigger_event_name', sa.String(length=100), nullable=True),
        sa.Column('trigger_threshold', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
    )
    op.create_index('ix_achievement_definitions_id', 'achievement_definitions', ['id'], unique=False)
    op.create_index('ix_achievement_definitions_tenant_id', 'achievement_definitions', ['tenant_id'], unique=False)
    op.create_index('ix_achievement_definitions_category', 'achievement_definitions', ['category'], unique=False)
    op.create_index('ix_achievement_definitions_tenant_active', 'achievement_definitions', ['tenant_id', 'is_active'], unique=False)

    # ========================================================
    # 2. user_achievements
    # ========================================================
    op.create_table(
        'user_achievements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('achievement_definition_id', sa.Integer(), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('granted_by', sa.Integer(), nullable=True),
        sa.Column('source_event_name', sa.String(length=100), nullable=True),
        sa.Column('source_payload', postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['achievement_definition_id'], ['achievement_definitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id']),
    )
    op.create_index('ix_user_achievements_id', 'user_achievements', ['id'], unique=False)
    op.create_index('ix_user_achievements_tenant_id', 'user_achievements', ['tenant_id'], unique=False)
    op.create_index('ix_user_achievements_user_id', 'user_achievements', ['user_id'], unique=False)
    op.create_index('ix_user_achievements_achievement_definition_id', 'user_achievements', ['achievement_definition_id'], unique=False)
    # القيد الفريد المطلوب: إنجاز واحد لكل مستخدم لكل تعريف — منع تكرار
    op.create_index(
        'ix_user_achievements_unique_user_definition',
        'user_achievements',
        ['user_id', 'achievement_definition_id'],
        unique=True,
    )

    # ========================================================
    # 3. user_network_stats — الشكل البنيوي فقط، بلا أي منطق حساب
    #    (المرحلة القادمة). عمود واحد تراكمي (bootcamp_network_size)
    #    مبدئيًا default=0، ما بيتحدّثش بأي كود في هذه الجلسة.
    # ========================================================
    op.create_table(
        'user_network_stats',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('bootcamp_network_size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('user_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_user_network_stats_tenant_id', 'user_network_stats', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_user_network_stats_tenant_id', table_name='user_network_stats')
    op.drop_table('user_network_stats')

    op.drop_index('ix_user_achievements_unique_user_definition', table_name='user_achievements')
    op.drop_index('ix_user_achievements_achievement_definition_id', table_name='user_achievements')
    op.drop_index('ix_user_achievements_user_id', table_name='user_achievements')
    op.drop_index('ix_user_achievements_tenant_id', table_name='user_achievements')
    op.drop_index('ix_user_achievements_id', table_name='user_achievements')
    op.drop_table('user_achievements')

    op.drop_index('ix_achievement_definitions_tenant_active', table_name='achievement_definitions')
    op.drop_index('ix_achievement_definitions_category', table_name='achievement_definitions')
    op.drop_index('ix_achievement_definitions_tenant_id', table_name='achievement_definitions')
    op.drop_index('ix_achievement_definitions_id', table_name='achievement_definitions')
    op.drop_table('achievement_definitions')

    postgresql.ENUM(name='achievementtriggertype').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='achievementcategory').drop(op.get_bind(), checkfirst=True)
