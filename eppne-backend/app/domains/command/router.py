# app/domains/command/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser
from app.domains.identity.models import User
from app.domains.command.service import CommandService
from app.domains.command.repository import CommandRepository
from app.domains.command.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/command", tags=["Strategic Command"])

# ========== Dashboard ==========
@router.get("/dashboard", response_model=DashboardResponse)
@rate_limit(max_requests=20, window=60)
async def get_dashboard(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommandService(db)
    dashboard = await service.get_dashboard(current_user.id, tenant.id)
    return dashboard

# ========== Brands ==========
@router.post("/brands", response_model=BrandSettingsResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, window=60)
async def create_brand(
    data: BrandSettingsCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = CommandService(db)
    brand = await service.create_brand(current_user.id, tenant.id, data.model_dump())
    return brand

@router.get("/brands/me", response_model=BrandSettingsResponse)
@rate_limit(max_requests=30, window=60)
async def get_my_brand(
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = CommandService(db)
    brand = await service.get_brand_settings(tenant.id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand

@router.put("/brands/me", response_model=BrandSettingsResponse)
@rate_limit(max_requests=10, window=60)
async def update_my_brand(
    data: BrandSettingsUpdate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommandService(db)
    brand = await service.update_brand_settings(tenant.id, data.model_dump(exclude_unset=True))
    return brand

# ========== Alerts ==========
@router.post("/alerts", response_model=SystemAlertResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=20, window=60)
async def create_alert(
    data: SystemAlertCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = CommandService(db)
    alert = await service.create_alert(tenant.id, data.model_dump())
    return alert

@router.get("/alerts", response_model=List[SystemAlertResponse])
@rate_limit(max_requests=30, window=60)
async def list_alerts(
    status: Optional[AlertStatus] = None,
    severity: Optional[AlertSeverity] = None,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = CommandRepository(db)
    alerts = await repo.list_alerts(tenant.id, status, severity, limit)
    return alerts

@router.post("/alerts/{alert_id}/acknowledge", response_model=SystemAlertResponse)
@rate_limit(max_requests=10, window=60)
async def acknowledge_alert(
    alert_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommandService(db)
    alert = await service.acknowledge_alert(alert_id, tenant.id, current_user.id)
    return alert

@router.post("/alerts/{alert_id}/resolve", response_model=SystemAlertResponse)
@rate_limit(max_requests=10, window=60)
async def resolve_alert(
    alert_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommandService(db)
    alert = await service.resolve_alert(alert_id, tenant.id, current_user.id)
    return alert

# ========== Reports ==========
@router.post("/reports", response_model=CommandReportResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, window=60)
async def generate_report(
    data: CommandReportCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommandService(db)
    report = await service.generate_report(current_user.id, tenant.id, data.model_dump())
    return report

@router.get("/reports", response_model=List[CommandReportResponse])
@rate_limit(max_requests=20, window=60)
async def list_reports(
    report_type: Optional[ReportType] = None,
    skip: int = 0,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = CommandRepository(db)
    reports = await repo.list_reports(tenant.id, report_type, skip, limit)
    return reports

# ========== AI Recommendations ==========
@router.get("/recommendations", response_model=List[AIRecommendationResponse])
@rate_limit(max_requests=20, window=60)
async def list_recommendations(
    status: Optional[str] = None,
    limit: int = 50,
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    repo = CommandRepository(db)
    recommendations = await repo.list_recommendations(tenant.id, status, limit=limit)
    return recommendations

@router.post("/recommendations/generate", response_model=List[AIRecommendationResponse])
@rate_limit(max_requests=5, window=60)
async def generate_recommendations(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = CommandService(db)
    recommendations = await service.generate_ai_recommendations(tenant.id, current_user.id)
    return recommendations

@router.post("/recommendations/{rec_id}/apply", response_model=AIRecommendationResponse)
@rate_limit(max_requests=5, window=60)
async def apply_recommendation(
    rec_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = CommandRepository(db)
    recommendation = await repo.update_recommendation(
        rec_id,
        tenant.id,
        status="APPLIED",
        applied_by=current_user.id,
        applied_at=datetime.utcnow()
    )
    return recommendation

# ========== System Health ==========
@router.get("/system/health")
@rate_limit(max_requests=30, window=60)
async def get_system_health(
    tenant: AcademyTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    service = CommandService(db)
    health = await service.get_system_health(tenant.id)
    return health

# ========== Metrics ==========
@router.post("/metrics", response_model=PlatformMetricResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=50, window=60)
async def record_metric(
    data: PlatformMetricCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = CommandService(db)
    metric = await service.record_metric(tenant.id, data.model_dump())
    return metric