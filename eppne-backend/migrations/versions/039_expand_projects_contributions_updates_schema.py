# migrations/versions/039_expand_projects_contributions_updates_schema.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '039_expand_projects_contributions_updates_schema'
down_revision = '038_add_instructor_id_to_academy_bootcamps'


def upgrade() -> None:
    # projects — fields present in ProjectCreate schema but missing from the model
    op.add_column('projects', sa.Column('city', sa.String(length=100), nullable=True))
    op.add_column('projects', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('projects', sa.Column('longitude', sa.Float(), nullable=True))
    op.add_column('projects', sa.Column('address', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('min_investment_mrusdt', sa.Numeric(30, 8), server_default='0'))
    op.add_column('projects', sa.Column('expected_roi_percentage', sa.Numeric(10, 4), nullable=True))
    op.add_column('projects', sa.Column('expected_irr_percentage', sa.Numeric(10, 4), nullable=True))
    op.add_column('projects', sa.Column('payback_period_years', sa.Integer(), nullable=True))
    op.add_column('projects', sa.Column('projected_cash_flows', postgresql.JSONB(), nullable=True))
    op.add_column('projects', sa.Column('estimated_carbon_emissions_tonnes', sa.Numeric(20, 4), nullable=True))
    op.add_column('projects', sa.Column('estimated_carbon_offset_tonnes', sa.Numeric(20, 4), nullable=True))
    op.add_column('projects', sa.Column('allow_in_kind_contributions', sa.Boolean(), server_default='true'))
    op.add_column('projects', sa.Column('allow_fractional_ownership', sa.Boolean(), server_default='false'))
    op.add_column('projects', sa.Column('shares_total', sa.Numeric(30, 8), nullable=True))
    op.add_column('projects', sa.Column('share_price_mrusdt', sa.Numeric(30, 8), nullable=True))
    op.add_column('projects', sa.Column('cover_image_url', sa.String(length=500), nullable=True))
    op.add_column('projects', sa.Column('gallery_urls', postgresql.JSONB(), server_default='[]'))
    op.add_column('projects', sa.Column('documents_urls', postgresql.JSONB(), server_default='[]'))

    # contributions — fields present in ContributionCreate schema but missing from the model
    op.add_column('contributions', sa.Column('land_area_sqm', sa.Numeric(20, 4), nullable=True))
    op.add_column('contributions', sa.Column('land_address', sa.Text(), nullable=True))
    op.add_column('contributions', sa.Column('land_title_deed_hash', sa.String(length=255), nullable=True))
    op.add_column('contributions', sa.Column('labor_hours', sa.Numeric(10, 2), nullable=True))
    op.add_column('contributions', sa.Column('labor_description', sa.Text(), nullable=True))
    op.add_column('contributions', sa.Column('equipment_description', sa.Text(), nullable=True))
    op.add_column('contributions', sa.Column('equipment_estimated_value', sa.Numeric(30, 8), nullable=True))
    op.add_column('contributions', sa.Column('consulting_hours', sa.Numeric(10, 2), nullable=True))
    op.add_column('contributions', sa.Column('consulting_expertise', sa.String(length=255), nullable=True))

    # project_updates — field present in ProjectUpdateCreate schema but missing from the model
    op.add_column('project_updates', sa.Column('media_urls', postgresql.JSONB(), server_default='[]'))


def downgrade() -> None:
    op.drop_column('project_updates', 'media_urls')

    op.drop_column('contributions', 'consulting_expertise')
    op.drop_column('contributions', 'consulting_hours')
    op.drop_column('contributions', 'equipment_estimated_value')
    op.drop_column('contributions', 'equipment_description')
    op.drop_column('contributions', 'labor_description')
    op.drop_column('contributions', 'labor_hours')
    op.drop_column('contributions', 'land_title_deed_hash')
    op.drop_column('contributions', 'land_address')
    op.drop_column('contributions', 'land_area_sqm')

    op.drop_column('projects', 'documents_urls')
    op.drop_column('projects', 'gallery_urls')
    op.drop_column('projects', 'cover_image_url')
    op.drop_column('projects', 'share_price_mrusdt')
    op.drop_column('projects', 'shares_total')
    op.drop_column('projects', 'allow_fractional_ownership')
    op.drop_column('projects', 'allow_in_kind_contributions')
    op.drop_column('projects', 'estimated_carbon_offset_tonnes')
    op.drop_column('projects', 'estimated_carbon_emissions_tonnes')
    op.drop_column('projects', 'projected_cash_flows')
    op.drop_column('projects', 'payback_period_years')
    op.drop_column('projects', 'expected_irr_percentage')
    op.drop_column('projects', 'expected_roi_percentage')
    op.drop_column('projects', 'min_investment_mrusdt')
    op.drop_column('projects', 'address')
    op.drop_column('projects', 'longitude')
    op.drop_column('projects', 'latitude')
    op.drop_column('projects', 'city')
