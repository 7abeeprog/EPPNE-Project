# migrations/versions/044_create_transport_tables.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '044_create_transport_tables'
down_revision = '043_add_marketing_fields_to_property_units'


def upgrade() -> None:
    # جلسة transport-domain-full-build (2026-09-01): دومين transport كان
    # الكود الخلفي (models.py/schemas.py/service.py/repository.py/router.py)
    # مكتمل فعليًا منذ جلسات سابقة، لكن صفر migration أنشأ الجداول السبعة
    # المذكورة فيه — كل الـ16 endpoint كانت تفشل بـ UndefinedTableError عند
    # أول استدعاء حقيقي (موثَّق في batch3-audit-security-...md §1.1). هذه
    # الهجرة تنشئ الجداول بالضبط كما هي مُعرَّفة في models.py الحالي، بلا
    # أي تغيير بنيوي.

    # ========== 1. transport_hubs ==========
    op.create_table(
        'transport_hubs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('hub_type', sa.String(length=50), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('gps_location', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_transport_hubs_id', 'transport_hubs', ['id'], unique=False)
    op.create_index('ix_transport_hubs_tenant_id', 'transport_hubs', ['tenant_id'], unique=False)
    op.create_index('ix_transport_hubs_entity_id', 'transport_hubs', ['entity_id'], unique=False)
    op.create_index('ix_transport_hubs_name', 'transport_hubs', ['name'], unique=False)
    op.create_index('ix_transport_hub_tenant', 'transport_hubs', ['tenant_id'], unique=False)
    op.create_index('ix_transport_hub_created_at', 'transport_hubs', ['created_at'], unique=False)

    # ========== 2. fleets ==========
    op.create_table(
        'fleets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_fleets_id', 'fleets', ['id'], unique=False)
    op.create_index('ix_fleets_tenant_id', 'fleets', ['tenant_id'], unique=False)
    op.create_index('ix_fleets_entity_id', 'fleets', ['entity_id'], unique=False)
    op.create_index('ix_fleet_tenant', 'fleets', ['tenant_id'], unique=False)
    op.create_index('ix_fleet_created_at', 'fleets', ['created_at'], unique=False)

    # ========== 3. vehicles ==========
    vehicle_type_enum = postgresql.ENUM(
        'BICYCLE', 'MOTORCYCLE', 'CAR', 'BUS', 'TRUCK', 'SHIP', 'AIRCRAFT',
        'SPACECRAFT', 'TRAIN',
        name='transporttype',
    )
    vehicle_status_enum = postgresql.ENUM(
        'AVAILABLE', 'IN_TRIP', 'MAINTENANCE', 'OUT_OF_SERVICE',
        name='vehiclestatus',
    )
    op.create_table(
        'vehicles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('fleet_id', sa.Integer(), nullable=False),
        sa.Column('smart_asset_id', sa.Integer(), nullable=True),
        sa.Column('license_plate', sa.String(length=50), nullable=False),
        sa.Column('vehicle_type', vehicle_type_enum, nullable=False),
        sa.Column('capacity_kg', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('capacity_passengers', sa.Integer(), nullable=True),
        sa.Column('fuel_type', sa.String(length=50), nullable=True),
        sa.Column('carbon_per_km', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('status', vehicle_status_enum, nullable=True),
        sa.Column('current_location', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ),
        sa.ForeignKeyConstraint(['fleet_id'], ['fleets.id'], ),
        sa.ForeignKeyConstraint(['smart_asset_id'], ['smart_assets.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_vehicles_id', 'vehicles', ['id'], unique=False)
    op.create_index('ix_vehicles_tenant_id', 'vehicles', ['tenant_id'], unique=False)
    op.create_index('ix_vehicles_fleet_id', 'vehicles', ['fleet_id'], unique=False)
    op.create_index('ix_vehicles_license_plate', 'vehicles', ['license_plate'], unique=True)
    op.create_index('ix_vehicle_tenant', 'vehicles', ['tenant_id'], unique=False)
    op.create_index('ix_vehicle_fleet', 'vehicles', ['fleet_id'], unique=False)
    op.create_index('ix_vehicle_created_at', 'vehicles', ['created_at'], unique=False)

    # ========== 4. transport_routes ==========
    op.create_table(
        'transport_routes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('start_hub_id', sa.Integer(), nullable=False),
        sa.Column('end_hub_id', sa.Integer(), nullable=False),
        sa.Column('waypoints', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('distance_km', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ),
        sa.ForeignKeyConstraint(['start_hub_id'], ['transport_hubs.id'], ),
        sa.ForeignKeyConstraint(['end_hub_id'], ['transport_hubs.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_transport_routes_id', 'transport_routes', ['id'], unique=False)
    op.create_index('ix_transport_routes_tenant_id', 'transport_routes', ['tenant_id'], unique=False)
    op.create_index('ix_route_tenant', 'transport_routes', ['tenant_id'], unique=False)
    op.create_index('ix_route_created_at', 'transport_routes', ['created_at'], unique=False)

    # ========== 5. transport_trips ==========
    trip_category_enum = postgresql.ENUM(
        'PASSENGER', 'FREIGHT', 'MASS_TRANSIT', 'TOURISM', 'MEDICAL', 'EDUCATIONAL',
        name='tripcategory',
    )
    trip_status_enum = postgresql.ENUM(
        'SCHEDULED', 'ONGOING', 'COMPLETED', 'CANCELLED', 'DELAYED',
        name='tripstatus',
    )
    op.create_table(
        'transport_trips',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('route_id', sa.Integer(), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('trip_category', trip_category_enum, nullable=False),
        sa.Column('scheduled_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scheduled_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actual_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', trip_status_enum, nullable=True),
        sa.Column('total_distance_km', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('carbon_footprint_kg', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('base_fare_mrusdt', sa.Numeric(precision=30, scale=8), nullable=True),
        sa.Column('total_fare_mrusdt', sa.Numeric(precision=30, scale=8), nullable=True),
        sa.Column('payment_tx_hash', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ),
        sa.ForeignKeyConstraint(['route_id'], ['transport_routes.id'], ),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
        sa.ForeignKeyConstraint(['driver_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_transport_trips_id', 'transport_trips', ['id'], unique=False)
    op.create_index('ix_transport_trips_tenant_id', 'transport_trips', ['tenant_id'], unique=False)
    op.create_index('ix_transport_trips_route_id', 'transport_trips', ['route_id'], unique=False)
    op.create_index('ix_transport_trips_vehicle_id', 'transport_trips', ['vehicle_id'], unique=False)
    op.create_index('ix_transport_trips_driver_id', 'transport_trips', ['driver_id'], unique=False)
    op.create_index('ix_trips_driver_status', 'transport_trips', ['driver_id', 'status'], unique=False)
    op.create_index('ix_trips_schedule', 'transport_trips', ['scheduled_start', 'scheduled_end'], unique=False)
    op.create_index('ix_trips_created_at', 'transport_trips', ['created_at'], unique=False)

    # ========== 6. trip_bookings ==========
    op.create_table(
        'trip_bookings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.Column('passenger_id', sa.Integer(), nullable=True),
        sa.Column('company_id', sa.Integer(), nullable=True),
        sa.Column('booking_type', sa.String(length=20), nullable=False),
        sa.Column('seats_count', sa.Integer(), nullable=True),
        sa.Column('weight_kg', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('fare_paid_mrusdt', sa.Numeric(precision=30, scale=8), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.CheckConstraint(
            "(passenger_id IS NOT NULL AND company_id IS NULL) OR (passenger_id IS NULL AND company_id IS NOT NULL)",
            name='check_booking_owner',
        ),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ),
        sa.ForeignKeyConstraint(['trip_id'], ['transport_trips.id'], ),
        sa.ForeignKeyConstraint(['passenger_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_trip_bookings_id', 'trip_bookings', ['id'], unique=False)
    op.create_index('ix_trip_bookings_tenant_id', 'trip_bookings', ['tenant_id'], unique=False)
    op.create_index('ix_trip_bookings_trip_id', 'trip_bookings', ['trip_id'], unique=False)
    op.create_index('ix_trip_bookings_idempotency_key', 'trip_bookings', ['idempotency_key'], unique=True)
    op.create_index('ix_trip_booking_tenant', 'trip_bookings', ['tenant_id'], unique=False)
    op.create_index('ix_trip_booking_trip', 'trip_bookings', ['trip_id'], unique=False)
    op.create_index('ix_trip_booking_created_at', 'trip_bookings', ['created_at'], unique=False)
    op.create_index(
        'ix_trip_booking_idempotency_key', 'trip_bookings', ['idempotency_key'],
        unique=True, postgresql_where=sa.text('idempotency_key IS NOT NULL'),
    )

    # ========== 7. delivery_tasks ==========
    op.create_table(
        'delivery_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('trip_id', sa.Integer(), nullable=True),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('receiver_id', sa.Integer(), nullable=False),
        sa.Column('pickup_address', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('dropoff_address', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('estimated_distance_km', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('delivery_proof_hash', sa.String(length=100), nullable=True),
        sa.Column('delivery_fee_mrusdt', sa.Numeric(precision=30, scale=8), nullable=True),
        sa.Column('payment_tx_hash', sa.String(length=100), nullable=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['academy_tenants.id'], ),
        sa.ForeignKeyConstraint(['trip_id'], ['transport_trips.id'], ),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['receiver_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_delivery_tasks_id', 'delivery_tasks', ['id'], unique=False)
    op.create_index('ix_delivery_tasks_tenant_id', 'delivery_tasks', ['tenant_id'], unique=False)
    op.create_index('ix_delivery_tasks_trip_id', 'delivery_tasks', ['trip_id'], unique=False)
    op.create_index('ix_delivery_tasks_idempotency_key', 'delivery_tasks', ['idempotency_key'], unique=True)
    op.create_index('ix_delivery_task_tenant', 'delivery_tasks', ['tenant_id'], unique=False)
    op.create_index('ix_delivery_task_trip', 'delivery_tasks', ['trip_id'], unique=False)
    op.create_index('ix_delivery_task_status', 'delivery_tasks', ['status'], unique=False)
    op.create_index('ix_delivery_task_created_at', 'delivery_tasks', ['created_at'], unique=False)
    op.create_index(
        'ix_delivery_task_idempotency_key', 'delivery_tasks', ['idempotency_key'],
        unique=True, postgresql_where=sa.text('idempotency_key IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_table('delivery_tasks')
    op.drop_table('trip_bookings')
    op.drop_table('transport_trips')
    op.drop_table('transport_routes')
    op.drop_table('vehicles')
    op.drop_table('fleets')
    op.drop_table('transport_hubs')
    postgresql.ENUM(name='tripstatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='tripcategory').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='vehiclestatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='transporttype').drop(op.get_bind(), checkfirst=True)
