# migrations/versions/056_create_guardian_relationship_tables.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '056_create_guardian_relationship_tables'
down_revision = '055_entertainment_venues_entity_id_fk_set_null'

# أساس علاقة ولي أمر↔طالب — دومين جديد بالكامل (app/domains/guardian/)،
# لا يمس أي جدول قائم. جدولان فقط، صفر منطق تدفق (طلب/موافقة/تحقق) فعلي
# في هذه المرحلة — الحالة الافتراضية PENDING_WARD_APPROVAL مجرد قيمة
# مخزَّنة، مفيش أي endpoint أو service بعد يقرأها أو يغيّرها (المرحلة
# القادمة). راجع:
# .claude/reports/guardian-relationship-design-planning-session-log.md
# .claude/reports/birth-date-null-percentage-check-session-log.md
# .claude/reports/guardian-relationship-foundation-implementation-session-log.md


def upgrade() -> None:
    # ========================================================
    # 1. guardian_relationships
    # ========================================================
    relationship_type_enum = postgresql.ENUM(
        'FATHER', 'MOTHER', 'GUARDIAN',
        name='guardianrelationshiptype',
    )
    relationship_status_enum = postgresql.ENUM(
        'PENDING_WARD_APPROVAL', 'PENDING_ADMIN_REVIEW', 'VERIFIED', 'REJECTED',
        name='guardianrelationshipstatus',
    )

    op.create_table(
        'guardian_relationships',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('guardian_user_id', sa.Integer(), nullable=False),
        sa.Column('ward_user_id', sa.Integer(), nullable=False),
        sa.Column('relationship_type', relationship_type_enum, nullable=False),
        sa.Column('status', relationship_status_enum, nullable=False, server_default='PENDING_WARD_APPROVAL'),
        sa.Column('initiated_by_user_id', sa.Integer(), nullable=False),
        # منفصل عمدًا عن users.birth_date القديمة (99.16% NULL — راجع
        # birth-date-null-percentage-check-session-log.md) — القيمة
        # المُدخَلة صراحةً وقت طلب/موافقة الربط.
        sa.Column('ward_birth_date_provided', sa.Date(), nullable=True),
        sa.Column('verified_by', sa.Integer(), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['guardian_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ward_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['initiated_by_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id']),
        sa.UniqueConstraint('guardian_user_id', 'ward_user_id', name='uq_guardian_ward'),
    )
    op.create_index('ix_guardian_relationships_id', 'guardian_relationships', ['id'], unique=False)
    op.create_index('ix_guardian_relationships_tenant_id', 'guardian_relationships', ['tenant_id'], unique=False)
    op.create_index('ix_guardian_relationships_status', 'guardian_relationships', ['status'], unique=False)
    op.create_index('ix_guardian_relationships_guardian_user_id', 'guardian_relationships', ['guardian_user_id'], unique=False)
    op.create_index('ix_guardian_relationships_ward_user_id', 'guardian_relationships', ['ward_user_id'], unique=False)

    # ========================================================
    # 2. guardian_visibility_settings
    # ========================================================
    visibility_sector_enum = postgresql.ENUM(
        'ACADEMY', 'SOCIAL', 'TRANSPORT', 'HEALTH',
        name='guardianvisibilitysector',
    )

    op.create_table(
        'guardian_visibility_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('guardian_relationship_id', sa.Integer(), nullable=False),
        sa.Column('sector', visibility_sector_enum, nullable=False),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['guardian_relationship_id'], ['guardian_relationships.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('guardian_relationship_id', 'sector', name='uq_guardian_visibility_relationship_sector'),
    )
    op.create_index(
        'ix_guardian_visibility_settings_relationship_id',
        'guardian_visibility_settings', ['guardian_relationship_id'], unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_guardian_visibility_settings_relationship_id', table_name='guardian_visibility_settings')
    op.drop_table('guardian_visibility_settings')
    postgresql.ENUM(name='guardianvisibilitysector').drop(op.get_bind(), checkfirst=True)

    op.drop_index('ix_guardian_relationships_ward_user_id', table_name='guardian_relationships')
    op.drop_index('ix_guardian_relationships_guardian_user_id', table_name='guardian_relationships')
    op.drop_index('ix_guardian_relationships_status', table_name='guardian_relationships')
    op.drop_index('ix_guardian_relationships_tenant_id', table_name='guardian_relationships')
    op.drop_index('ix_guardian_relationships_id', table_name='guardian_relationships')
    op.drop_table('guardian_relationships')
    postgresql.ENUM(name='guardianrelationshipstatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='guardianrelationshiptype').drop(op.get_bind(), checkfirst=True)
