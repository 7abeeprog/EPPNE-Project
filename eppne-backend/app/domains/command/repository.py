# app/domains/command/repository.py
"""
مستودع (Repository) قطاع القيادة الاستراتيجية
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.domains.command.models import *
from app.core.errors import NotFoundError


class CommandRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ========== Dashboards ==========
    async def get_dashboard(self, tenant_id: int) -> Optional[CommandDashboard]:
        result = await self.db.execute(
            select(CommandDashboard).where(CommandDashboard.tenant_id == tenant_id, CommandDashboard.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def create_dashboard(self, **kwargs) -> CommandDashboard:
        dashboard = CommandDashboard(**kwargs)
        self.db.add(dashboard)
        await self.db.commit()
        await self.db.refresh(dashboard)
        return dashboard

    async def update_dashboard(self, tenant_id: int, **kwargs) -> CommandDashboard:
        await self.db.execute(
            update(CommandDashboard).where(CommandDashboard.tenant_id == tenant_id).values(**kwargs)
        )
        await self.db.commit()
        return await self.get_dashboard(tenant_id)

    # ========== Brands ==========
    async def create_brand(self, **kwargs) -> BrandSettings:
        brand = BrandSettings(**kwargs)
        self.db.add(brand)
        await self.db.commit()
        await self.db.refresh(brand)
        return brand

    async def get_brand_settings(self, tenant_id: int) -> Optional[BrandSettings]:
        result = await self.db.execute(
            select(BrandSettings).where(BrandSettings.tenant_id == tenant_id, BrandSettings.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def get_brand_by_slug(self, slug: str) -> Optional[BrandSettings]:
        result = await self.db.execute(
            select(BrandSettings).where(BrandSettings.brand_slug == slug, BrandSettings.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def list_brands(self, tenant_id: int, skip: int = 0, limit: int = 50) -> List[BrandSettings]:
        result = await self.db.execute(
            select(BrandSettings).where(BrandSettings.tenant_id == tenant_id, BrandSettings.is_deleted == False)
            .order_by(BrandSettings.created_at.desc()).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def update_brand(self, tenant_id: int, **kwargs) -> BrandSettings:
        await self.db.execute(
            update(BrandSettings).where(BrandSettings.tenant_id == tenant_id).values(**kwargs)
        )
        await self.db.commit()
        return await self.get_brand_settings(tenant_id)

    async def delete_brand(self, tenant_id: int) -> None:
        await self.db.execute(
            update(BrandSettings).where(BrandSettings.tenant_id == tenant_id).values(is_deleted=True, deleted_at=func.now())
        )
        await self.db.commit()

    # ========== Alerts ==========
    async def create_alert(self, **kwargs) -> SystemAlert:
        alert = SystemAlert(**kwargs)
        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)
        return alert

    async def get_alert(self, alert_id: int, tenant_id: int) -> Optional[SystemAlert]:
        result = await self.db.execute(
            select(SystemAlert).where(SystemAlert.id == alert_id, SystemAlert.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list_alerts(
        self,
        tenant_id: int,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        limit: int = 50
    ) -> List[SystemAlert]:
        query = select(SystemAlert).where(SystemAlert.tenant_id == tenant_id)
        if status:
            query = query.where(SystemAlert.status == status)
        if severity:
            query = query.where(SystemAlert.severity == severity)
        query = query.order_by(SystemAlert.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_alert(self, alert_id: int, tenant_id: int, **kwargs) -> SystemAlert:
        await self.db.execute(
            update(SystemAlert).where(SystemAlert.id == alert_id, SystemAlert.tenant_id == tenant_id).values(**kwargs)
        )
        await self.db.commit()
        return await self.get_alert(alert_id, tenant_id)

    # ========== Metrics ==========
    async def create_metric(self, **kwargs) -> PlatformMetric:
        metric = PlatformMetric(**kwargs)
        self.db.add(metric)
        await self.db.commit()
        await self.db.refresh(metric)
        return metric

    async def list_metrics(
        self,
        tenant_id: int,
        metric_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[PlatformMetric]:
        query = select(PlatformMetric).where(PlatformMetric.tenant_id == tenant_id)
        if metric_name:
            query = query.where(PlatformMetric.metric_name == metric_name)
        if start_date:
            query = query.where(PlatformMetric.recorded_at >= start_date)
        if end_date:
            query = query.where(PlatformMetric.recorded_at <= end_date)
        query = query.order_by(PlatformMetric.recorded_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    # ========== Reports ==========
    async def create_report(self, **kwargs) -> CommandReport:
        report = CommandReport(**kwargs)
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def get_report(self, report_id: int, tenant_id: int) -> Optional[CommandReport]:
        result = await self.db.execute(
            select(CommandReport).where(CommandReport.id == report_id, CommandReport.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list_reports(
        self,
        tenant_id: int,
        report_type: Optional[ReportType] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[CommandReport]:
        query = select(CommandReport).where(CommandReport.tenant_id == tenant_id, CommandReport.is_deleted == False)
        if report_type:
            query = query.where(CommandReport.report_type == report_type)
        query = query.order_by(CommandReport.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_report(self, report_id: int, tenant_id: int, **kwargs) -> CommandReport:
        await self.db.execute(
            update(CommandReport).where(CommandReport.id == report_id, CommandReport.tenant_id == tenant_id).values(**kwargs)
        )
        await self.db.commit()
        return await self.get_report(report_id, tenant_id)

    async def delete_report(self, report_id: int, tenant_id: int) -> None:
        await self.db.execute(
            update(CommandReport).where(CommandReport.id == report_id, CommandReport.tenant_id == tenant_id).values(is_deleted=True, deleted_at=func.now())
        )
        await self.db.commit()

    # ========== AI Recommendations ==========
    async def create_recommendation(self, **kwargs) -> AIRecommendation:
        rec = AIRecommendation(**kwargs)
        self.db.add(rec)
        await self.db.commit()
        await self.db.refresh(rec)
        return rec

    async def list_recommendations(
        self,
        tenant_id: int,
        status: Optional[str] = None,
        recommendation_type: Optional[str] = None,
        limit: int = 50
    ) -> List[AIRecommendation]:
        query = select(AIRecommendation).where(AIRecommendation.tenant_id == tenant_id)
        if status:
            query = query.where(AIRecommendation.status == status)
        if recommendation_type:
            query = query.where(AIRecommendation.recommendation_type == recommendation_type)
        query = query.order_by(AIRecommendation.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_recommendation(self, rec_id: int, tenant_id: int, **kwargs) -> AIRecommendation:
        await self.db.execute(
            update(AIRecommendation).where(AIRecommendation.id == rec_id, AIRecommendation.tenant_id == tenant_id).values(**kwargs)
        )
        await self.db.commit()
        result = await self.db.execute(select(AIRecommendation).where(AIRecommendation.id == rec_id))
        return result.scalar_one()

    # ========== Sessions ==========
    async def create_session(self, **kwargs) -> UserSession:
        session = UserSession(**kwargs)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_token: str) -> Optional[UserSession]:
        result = await self.db.execute(
            select(UserSession).where(UserSession.session_token == session_token, UserSession.is_active == True)
        )
        return result.scalar_one_or_none()

    async def update_session_activity(self, session_token: str) -> None:
        await self.db.execute(
            update(UserSession).where(UserSession.session_token == session_token).values(last_activity=func.now())
        )
        await self.db.commit()

    async def end_session(self, session_token: str) -> None:
        await self.db.execute(
            update(UserSession).where(UserSession.session_token == session_token).values(
                is_active=False, logout_time=func.now()
            )
        )
        await self.db.commit()