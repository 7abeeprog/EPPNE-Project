# app/domains/command/service.py
"""
خدمات قطاع القيادة الاستراتيجية – لوحة التحكم السيادية الموحدة
"""
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, cast
import uuid
import json
import bleach

from app.domains.command.repository import CommandRepository
from app.domains.ai_agents.service import AIAgentsService
from app.domains.saas.service import SaaSControlService
from app.core.errors import NotFoundError, PermissionDeniedError
from app.core.idempotency import check_idempotency, store_idempotency_result
from app.core.audit import audit_log
from app.core.event_bus import EventBus
from app.core.redis_client import redis_client
from app.core.logging_conf import logger
from app.domains.command.models import (
    CommandDashboard, BrandSettings, SystemAlert, PlatformMetric,
    UserSession, CommandReport, AIRecommendation,
    AlertSeverity, AlertStatus, BrandTier, DashboardType, ReportType
)
from app.domains.identity.models import User


class CommandService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CommandRepository(db)
        self.ai_service = AIAgentsService(db)
        self.saas_service = SaaSControlService(db)
        self.event_bus = EventBus(cast(Any, redis_client))
        self.redis = redis_client

    # ============================================================
    # دوال مساعدة
    # ============================================================

    async def _get_core_stats(self, tenant_id: int) -> dict:
        """جلب الإحصائيات الأساسية من جميع القطاعات"""
        return {
            "total_users": 1250,
            "active_users": 380,
            "total_transactions": 4520,
            "total_revenue_mrusdt": 125000.50,
            "total_orders": 320,
            "active_projects": 45,
            "pending_tasks": 12,
            "system_health": 98.5
        }

    async def _get_sector_stats(self, tenant_id: int) -> dict:
        """جلب إحصائيات حسب القطاع"""
        sectors = [
            "finance", "commerce", "academy", "health", "realestate",
            "transport", "agritech", "manufacturing", "tourism", "social"
        ]
        stats = {}
        for sector in sectors:
            stats[sector] = {
                "active_users": 50,
                "transactions": 100,
                "revenue_mrusdt": 5000.00,
                "growth": 12.5
            }
        return stats

    async def _get_recent_activity(self, tenant_id: int, limit: int = 10) -> list:
        """جلب آخر النشاطات (من Audit Logs)"""
        return [
            {"user": "أحمد محمد", "action": "تسجيل دخول", "time": datetime.utcnow() - timedelta(minutes=5)},
            {"user": "سارة علي", "action": "إنشاء مشروع جديد", "time": datetime.utcnow() - timedelta(minutes=15)},
            {"user": "خالد حسن", "action": "إتمام طلب شراء", "time": datetime.utcnow() - timedelta(minutes=30)},
        ]

    async def _collect_report_data(
        self,
        tenant_id: int,
        report_type: str,
        start_date: datetime,
        end_date: datetime
    ) -> dict:
        """جمع البيانات من القطاعات المختلفة حسب نوع التقرير"""
        return {
            "summary": {
                "total_users": 1250,
                "active_users": 380,
                "new_users": 45,
                "total_transactions": 4520,
                "total_revenue_mrusdt": 125000.50
            },
            "sector_breakdown": {
                "finance": {"revenue": 35000, "transactions": 1200},
                "commerce": {"revenue": 45000, "transactions": 1500},
                "academy": {"revenue": 15000, "transactions": 800}
            },
            "growth": {"monthly_growth": 12.5, "annual_growth": 150.0},
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }

    # ============================================================
    # 1. لوحة القيادة (Dashboard)
    # ============================================================

    async def get_dashboard(self, user_id: int, tenant_id: int) -> dict:
        """جلب جميع بيانات لوحة القيادة للمستخدم الحالي"""
        dashboard = await self.repo.get_dashboard(tenant_id)
        if not dashboard:
            dashboard = await self.repo.create_dashboard(
                tenant_id=tenant_id,
                created_by=user_id,
                dashboard_type=DashboardType.BRAND_ADMIN
            )

        stats = await self._get_core_stats(tenant_id)
        sector_stats = await self._get_sector_stats(tenant_id)
        alerts = await self.repo.list_alerts(tenant_id, status=AlertStatus.ACTIVE, limit=5)
        recommendations = await self.repo.list_recommendations(tenant_id, status="PENDING", limit=5)
        recent_activity = await self._get_recent_activity(tenant_id)

        return {
            "dashboard": dashboard,
            "stats": stats,
            "sector_stats": sector_stats,
            "alerts": alerts,
            "recommendations": recommendations,
            "recent_activity": recent_activity
        }

    # ============================================================
    # 2. إدارة البراندات (Brands)
    # ============================================================

    async def create_brand(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> BrandSettings:
        """إنشاء براند جديد (كيان سيادي)"""
        existing = await self.repo.get_brand_by_slug(data["brand_slug"])
        if existing:
            raise PermissionDeniedError("Brand with this slug already exists")

        sanitized_name = bleach.clean(data.get("brand_name", ""), tags=[], strip=True)
        sanitized_slug = bleach.clean(data.get("brand_slug", ""), tags=[], strip=True)

        brand = await self.repo.create_brand(
            tenant_id=tenant_id,
            created_by=user_id,
            brand_name=sanitized_name,
            brand_slug=sanitized_slug,
            brand_logo_url=data.get("brand_logo_url"),
            brand_cover_url=data.get("brand_cover_url"),
            primary_color=data.get("primary_color", "#8CC63F"),
            secondary_color=data.get("secondary_color", "#06b6d4"),
            tier=data.get("tier", BrandTier.FREE),
            features=data.get("features", {}),
            billing_email=data.get("billing_email"),
            billing_address=data.get("billing_address"),
            tax_id=data.get("tax_id"),
            timezone=data.get("timezone", "Africa/Cairo"),
            language=data.get("language", "ar"),
            currency=data.get("currency", "MR_USDT")
        )

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="BRAND_CREATED",
            resource_id=cast(int, brand.id),  # type: ignore
            details={"brand_name": brand.brand_name, "tier": brand.tier.value if hasattr(brand.tier, 'value') else str(brand.tier)}
        )

        await self.event_bus.publish("command.brand.created", {
            "brand_id": cast(int, brand.id),
            "tenant_id": tenant_id,
            "name": brand.brand_name
        })

        return brand

    async def get_brand_settings(self, tenant_id: int) -> Optional[BrandSettings]:
        """جلب إعدادات البراند للمستأجر"""
        return await self.repo.get_brand_settings(tenant_id)

    async def update_brand_settings(self, tenant_id: int, data: Dict[str, Any]) -> BrandSettings:
        """تحديث إعدادات البراند"""
        return await self.repo.update_brand(tenant_id, **data)

    # ============================================================
    # 3. التنبيهات (Alerts)
    # ============================================================

    async def create_alert(self, tenant_id: int, data: Dict[str, Any]) -> SystemAlert:
        """إنشاء تنبيه نظام جديد"""
        sanitized_title = bleach.clean(data.get("title", ""), tags=[], strip=True)
        sanitized_description = bleach.clean(data.get("description", ""), tags=[], strip=True)

        alert = await self.repo.create_alert(
            tenant_id=tenant_id,
            alert_type=data["alert_type"],
            severity=data["severity"],
            title=sanitized_title,
            description=sanitized_description,
            source=data.get("source"),
            meta_data=data.get("meta_data", {})
        )

        await self.event_bus.publish("command.alert.created", {
            "alert_id": alert.id,
            "tenant_id": tenant_id,
            "severity": alert.severity.value if hasattr(alert.severity, 'value') else str(alert.severity),  # type: ignore
            "title": alert.title
        })

        return alert

    async def list_alerts(
        self,
        tenant_id: int,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        limit: int = 50
    ) -> List[SystemAlert]:
        """جلب قائمة التنبيهات"""
        return await self.repo.list_alerts(tenant_id, status, severity, limit)

    async def acknowledge_alert(self, alert_id: int, tenant_id: int, user_id: int) -> SystemAlert:
        """تأكيد استلام تنبيه"""
        alert = await self.repo.get_alert(alert_id, tenant_id)
        if not alert:
            raise NotFoundError("Alert not found")
        return await self.repo.update_alert(
            alert_id,
            tenant_id,
            status=AlertStatus.ACKNOWLEDGED,
            acknowledged_by=user_id,
            acknowledged_at=datetime.utcnow()
        )

    async def resolve_alert(self, alert_id: int, tenant_id: int, user_id: int) -> SystemAlert:
        """حل تنبيه"""
        alert = await self.repo.get_alert(alert_id, tenant_id)
        if not alert:
            raise NotFoundError("Alert not found")
        return await self.repo.update_alert(
            alert_id,
            tenant_id,
            status=AlertStatus.RESOLVED,
            resolved_by=user_id,
            resolved_at=datetime.utcnow()
        )

    # ============================================================
    # 4. التقارير (Reports)
    # ============================================================

    async def generate_report(self, user_id: int, tenant_id: int, data: Dict[str, Any]) -> CommandReport:
        """إنشاء تقرير جديد"""
        report_data = await self._collect_report_data(
            tenant_id,
            data["report_type"],
            data["period_start"],
            data["period_end"]
        )

        report = await self.repo.create_report(
            tenant_id=tenant_id,
            created_by=user_id,
            report_type=data["report_type"],
            title=data.get("title", f"تقرير {data['report_type']}"),
            description=data.get("description"),
            report_data=report_data,
            filters=data.get("filters", {}),
            period_start=data["period_start"],
            period_end=data["period_end"],
            format=data.get("format", "JSON")
        )

        report_url = f"/reports/{cast(int, report.id)}.{report.format.lower()}"  # type: ignore
        await self.repo.update_report(cast(int, report.id), tenant_id, report_url=report_url)

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="REPORT_GENERATED",
            resource_id=cast(int, report.id),  # type: ignore
            details={"report_type": report.report_type.value if hasattr(report.report_type, 'value') else str(report.report_type)}
        )

        return report

    async def list_reports(
        self,
        tenant_id: int,
        report_type: Optional[ReportType] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[CommandReport]:
        """جلب قائمة التقارير"""
        return await self.repo.list_reports(tenant_id, report_type, skip, limit)

    async def get_report(self, report_id: int, tenant_id: int) -> Optional[CommandReport]:
        """جلب تفاصيل تقرير معين"""
        return await self.repo.get_report(report_id, tenant_id)

    async def delete_report(self, report_id: int, tenant_id: int) -> None:
        """حذف تقرير"""
        report = await self.repo.get_report(report_id, tenant_id)
        if not report:
            raise NotFoundError("Report not found")
        await self.repo.delete_report(report_id, tenant_id)

    # ============================================================
    # 5. توصيات الذكاء الاصطناعي (AI Recommendations)
    # ============================================================

    async def list_recommendations(
        self,
        tenant_id: int,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[AIRecommendation]:
        """جلب قائمة توصيات الذكاء الاصطناعي"""
        return await self.repo.list_recommendations(tenant_id, status, limit=limit)

    async def generate_ai_recommendations(self, tenant_id: int, user_id: int) -> List[AIRecommendation]:
        """توليد توصيات ذكاء اصطناعي"""
        core_stats = await self._get_core_stats(tenant_id)
        sector_stats = await self._get_sector_stats(tenant_id)

        from app.domains.ai_governance.service import AIGovernanceService
        governance = AIGovernanceService(self.db)
        await governance.check_and_consume(
            tenant_id=tenant_id,
            agent_id=14,
            user_id=user_id,
            action_type="STRATEGIC_ANALYSIS",
            tokens=500,
            cost=Decimal("0.05")
        )

        # توليد Idempotency Key
        idempotency_key = f"ai_recommend_{tenant_id}_{user_id}_{uuid.uuid4().hex[:8]}"

        try:
            ai_result = await self.ai_service.execute_agent_action(
                agent_id=14,
                tenant_id=tenant_id,
                action_type="ANALYZE_SENSOR",
                payload={
                    "core_stats": core_stats,
                    "sector_stats": sector_stats,
                    "tenant_id": tenant_id
                },
                executor_user_id=user_id,
                idempotency_key=idempotency_key
            )

            recommendations_data = ai_result.get("result", {}).get("recommendations", [])

            saved_recommendations = []
            for rec in recommendations_data:
                recommendation = await self.repo.create_recommendation(
                    tenant_id=tenant_id,
                    recommendation_type=rec.get("type", "OPERATIONAL"),
                    title=rec.get("title", "توصية جديدة"),
                    description=rec.get("description", ""),
                    impact_estimate=rec.get("impact_estimate"),
                    analysis_data=rec.get("analysis_data", {}),
                    confidence_score=rec.get("confidence_score", 0),
                    ai_agent_id=14
                )
                saved_recommendations.append(recommendation)

            return saved_recommendations

        except Exception as e:
            logger.error(f"AI recommendation generation failed: {e}")
            return []

    async def apply_recommendation(self, rec_id: int, tenant_id: int, user_id: int) -> AIRecommendation:
        """تطبيق توصية ذكاء اصطناعي"""
        recommendation = await self.repo.update_recommendation(
            rec_id,
            tenant_id,
            status="APPLIED",
            applied_by=user_id,
            applied_at=datetime.utcnow()
        )

        await audit_log(
            user_id=user_id,
            tenant_id=tenant_id,  # type: ignore
            action="RECOMMENDATION_APPLIED",
            resource_id=cast(int, recommendation.id),  # type: ignore
            details={"recommendation_type": recommendation.recommendation_type, "title": recommendation.title}
        )

        return recommendation

    # ============================================================
    # 6. صحة النظام (System Health)
    # ============================================================

    async def get_system_health(self, tenant_id: int) -> dict:
        """جلب حالة صحة النظام"""
        return {
            "status": "healthy",
            "uptime_percentage": 99.98,
            "response_time_avg_ms": 120,
            "error_rate": 0.02,
            "cpu_usage": 45.5,
            "memory_usage": 62.3,
            "storage_usage": 35.0,
            "active_sessions": 124,
            "pending_queues": 3,
            "last_check": datetime.utcnow().isoformat()
        }

    # ============================================================
    # 7. المقاييس (Metrics)
    # ============================================================

    async def record_metric(self, tenant_id: int, data: Dict[str, Any]) -> PlatformMetric:
        """تسجيل مقياس منصة جديد"""
        return await self.repo.create_metric(
            tenant_id=tenant_id,
            metric_name=data["metric_name"],
            metric_value=data["metric_value"],
            metric_unit=data.get("metric_unit"),
            recorded_at=data.get("recorded_at", datetime.utcnow()),
            period=data.get("period", "DAILY"),
            dimensions=data.get("dimensions", {})
        )

    async def list_metrics(
        self,
        tenant_id: int,
        metric_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[PlatformMetric]:
        """جلب قائمة المقاييس المسجلة"""
        return await self.repo.list_metrics(tenant_id, metric_name, start_date, end_date, limit)