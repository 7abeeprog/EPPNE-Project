# app/domains/command/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, cast
from datetime import datetime

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_tenant, get_current_superuser
from app.domains.identity.models import User
from app.domains.command.service import CommandService
from app.domains.command.schemas import *
from app.domains.academy.models import AcademyTenant
from app.core.rate_limiter import rate_limit

router = APIRouter(prefix="/command", tags=["Strategic Command"])


# ============================================================
# 1. لوحة القيادة (Dashboard)
# ============================================================

@router.get("/dashboard", response_model=DashboardResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def get_dashboard(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب جميع بيانات لوحة القيادة للمستخدم الحالي"""
    service = CommandService(db)
    dashboard = await service.get_dashboard(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id)
    )
    return dashboard


# ============================================================
# 2. إدارة البراندات (Brands)
# ============================================================

@router.post("/brands", response_model=BrandSettingsResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, window_seconds=60)
async def create_brand(
    data: BrandSettingsCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """إنشاء براند جديد (يتطلب صلاحيات مشرف)"""
    service = CommandService(db)
    brand = await service.create_brand(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return brand


@router.get("/brands/me", response_model=BrandSettingsResponse)
@rate_limit(max_requests=30, window_seconds=60)
async def get_my_brand(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب إعدادات البراند الخاصة بالمستأجر الحالي"""
    service = CommandService(db)
    brand = await service.get_brand_settings(tenant_id=cast(int, tenant.id))
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


@router.put("/brands/me", response_model=BrandSettingsResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_my_brand(
    data: BrandSettingsUpdate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """تحديث إعدادات البراند الخاصة بالمستأجر الحالي"""
    service = CommandService(db)
    brand = await service.update_brand_settings(
        tenant_id=cast(int, tenant.id),
        data=data.model_dump(exclude_unset=True)
    )
    return brand


# ============================================================
# 3. التنبيهات (Alerts)
# ============================================================

@router.post("/alerts", response_model=SystemAlertResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=20, window_seconds=60)
async def create_alert(
    data: SystemAlertCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """إنشاء تنبيه نظام جديد (يتطلب صلاحيات مشرف)"""
    service = CommandService(db)
    alert = await service.create_alert(
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return alert


@router.get("/alerts", response_model=List[SystemAlertResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_alerts(
    status: Optional[AlertStatus] = Query(None, description="حالة التنبيه"),
    severity: Optional[AlertSeverity] = Query(None, description="خطورة التنبيه"),
    limit: int = Query(50, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب قائمة التنبيهات"""
    service = CommandService(db)
    alerts = await service.list_alerts(
        tenant_id=cast(int, tenant.id),
        status=status,
        severity=severity,
        limit=limit
    )
    return alerts


@router.post("/alerts/{alert_id}/acknowledge", response_model=SystemAlertResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def acknowledge_alert(
    alert_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """تأكيد استلام تنبيه"""
    service = CommandService(db)
    alert = await service.acknowledge_alert(
        alert_id=alert_id,
        tenant_id=cast(int, tenant.id),
        user_id=cast(int, current_user.id)
    )
    return alert


@router.post("/alerts/{alert_id}/resolve", response_model=SystemAlertResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def resolve_alert(
    alert_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """حل تنبيه"""
    service = CommandService(db)
    alert = await service.resolve_alert(
        alert_id=alert_id,
        tenant_id=cast(int, tenant.id),
        user_id=cast(int, current_user.id)
    )
    return alert


# ============================================================
# 4. التقارير (Reports)
# ============================================================

@router.post("/reports", response_model=CommandReportResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, window_seconds=60)
async def generate_report(
    data: CommandReportCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """إنشاء تقرير جديد"""
    service = CommandService(db)
    report = await service.generate_report(
        user_id=cast(int, current_user.id),
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return report


@router.get("/reports", response_model=List[CommandReportResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def list_reports(
    report_type: Optional[ReportType] = Query(None, description="نوع التقرير"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب قائمة التقارير"""
    service = CommandService(db)
    reports = await service.list_reports(
        tenant_id=cast(int, tenant.id),
        report_type=report_type,
        skip=skip,
        limit=limit
    )
    return reports


@router.get("/reports/{report_id}", response_model=CommandReportResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def get_report(
    report_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب تفاصيل تقرير معين"""
    service = CommandService(db)
    report = await service.get_report(
        report_id=report_id,
        tenant_id=cast(int, tenant.id)
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit(max_requests=10, window_seconds=60)
async def delete_report(
    report_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """حذف تقرير"""
    service = CommandService(db)
    await service.delete_report(
        report_id=report_id,
        tenant_id=cast(int, tenant.id)
    )
    return None


# ============================================================
# 5. توصيات الذكاء الاصطناعي (AI Recommendations)
# ============================================================

@router.get("/recommendations", response_model=List[AIRecommendationResponse])
@rate_limit(max_requests=20, window_seconds=60)
async def list_recommendations(
    status: Optional[str] = Query(None, description="حالة التوصية"),
    limit: int = Query(50, ge=1, le=200),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب قائمة توصيات الذكاء الاصطناعي"""
    service = CommandService(db)
    recommendations = await service.list_recommendations(
        tenant_id=cast(int, tenant.id),
        status=status,
        limit=limit
    )
    return recommendations


@router.post("/recommendations/generate", response_model=List[AIRecommendationResponse])
@rate_limit(max_requests=5, window_seconds=60)
async def generate_recommendations(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """توليد توصيات ذكاء اصطناعي جديدة"""
    service = CommandService(db)
    recommendations = await service.generate_ai_recommendations(
        tenant_id=cast(int, tenant.id),
        user_id=cast(int, current_user.id)
    )
    return recommendations


@router.post("/recommendations/{rec_id}/apply", response_model=AIRecommendationResponse)
@rate_limit(max_requests=5, window_seconds=60)
async def apply_recommendation(
    rec_id: int,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """تطبيق توصية ذكاء اصطناعي"""
    service = CommandService(db)
    recommendation = await service.apply_recommendation(
        rec_id=rec_id,
        tenant_id=cast(int, tenant.id),
        user_id=cast(int, current_user.id)
    )
    return recommendation


# ============================================================
# 6. صحة النظام (System Health)
# ============================================================

@router.get("/system/health")
@rate_limit(max_requests=30, window_seconds=60)
async def get_system_health(
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب حالة صحة النظام"""
    service = CommandService(db)
    health = await service.get_system_health(tenant_id=cast(int, tenant.id))
    return health


# ============================================================
# 7. المقاييس (Metrics)
# ============================================================

@router.post("/metrics", response_model=PlatformMetricResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=50, window_seconds=60)
async def record_metric(
    data: PlatformMetricCreate,
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    """تسجيل مقياس منصة جديد (يتطلب صلاحيات مشرف)"""
    service = CommandService(db)
    metric = await service.record_metric(
        tenant_id=cast(int, tenant.id),
        data=data.model_dump()
    )
    return metric


@router.get("/metrics", response_model=List[PlatformMetricResponse])
@rate_limit(max_requests=30, window_seconds=60)
async def list_metrics(
    metric_name: Optional[str] = Query(None, description="اسم المقياس"),
    start_date: Optional[datetime] = Query(None, description="تاريخ البداية"),
    end_date: Optional[datetime] = Query(None, description="تاريخ النهاية"),
    limit: int = Query(100, ge=1, le=500),
    tenant: AcademyTenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """جلب قائمة المقاييس المسجلة"""
    service = CommandService(db)
    metrics = await service.list_metrics(
        tenant_id=cast(int, tenant.id),
        metric_name=metric_name,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    return metrics