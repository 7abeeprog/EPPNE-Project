"""
regression test لجلسة `frontend-category-b-phase2-remaining-domains` (2026-09-02).
تقرير الجلسة: .claude/reports/frontend-category-b-phase2-session-log.md

السياق: `hooks/command/useBrands.ts` كان ملفًا فارغًا تمامًا رغم أن
`CommandRepository.list_brands` كانت جاهزة بالكامل بدون service/router.
و`hooks/command/useCommandStats.ts` كان يستدعي `getDashboardMetrics(period)`
دون أن يكون هناك دعم لفلترة `period` في `list_metrics` رغم أن الحقل نفسه
موجود على الموديل ويُخزَّن فعليًا عبر `record_metric`.
هذا الاختبار يتحقق حيًا (DB حقيقية) من: `CommandService.list_brands`
(الجديدة) و`CommandService.list_metrics` بعد إضافة فلتر `period`.
"""
import uuid
from decimal import Decimal
from datetime import datetime

import pytest
from sqlalchemy import delete

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.command.service import CommandService
from app.domains.command.repository import CommandRepository
from app.domains.command.models import BrandSettings, PlatformMetric

TENANT_ID = 1


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


@pytest.mark.asyncio
async def test_list_brands_returns_real_record(db):
    creator = await _create_user(db, "p_regtest_command_brand_creator")
    repo = CommandRepository(db)
    suffix = _suffix()
    brand = await repo.create_brand(
        tenant_id=TENANT_ID, brand_name=f"REGTEST-BRAND-{suffix}",
        brand_slug=f"regtest-brand-{suffix}", created_by=creator.id,
    )
    brand_id = brand.id

    service = CommandService(db)
    try:
        result = await service.list_brands(TENANT_ID)
        assert any(b.id == brand_id for b in result)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(BrandSettings).where(BrandSettings.id == brand_id))
            await cleanup_db.execute(delete(User).where(User.id == creator.id))
            await cleanup_db.commit()


@pytest.mark.asyncio
async def test_list_metrics_filters_by_period(db):
    repo = CommandRepository(db)
    suffix = _suffix()
    daily = await repo.create_metric(
        tenant_id=TENANT_ID, metric_name=f"REGTEST-METRIC-{suffix}",
        metric_value=Decimal("10"), recorded_at=datetime.utcnow(), period="DAILY",
    )
    monthly = await repo.create_metric(
        tenant_id=TENANT_ID, metric_name=f"REGTEST-METRIC-{suffix}",
        metric_value=Decimal("100"), recorded_at=datetime.utcnow(), period="MONTHLY",
    )
    daily_id, monthly_id = daily.id, monthly.id

    service = CommandService(db)
    try:
        daily_results = await service.list_metrics(TENANT_ID, metric_name=f"REGTEST-METRIC-{suffix}", period="DAILY")
        assert any(m.id == daily_id for m in daily_results)
        assert not any(m.id == monthly_id for m in daily_results)

        monthly_results = await service.list_metrics(TENANT_ID, metric_name=f"REGTEST-METRIC-{suffix}", period="MONTHLY")
        assert any(m.id == monthly_id for m in monthly_results)
        assert not any(m.id == daily_id for m in monthly_results)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(PlatformMetric).where(PlatformMetric.id.in_([daily_id, monthly_id])))
            await cleanup_db.commit()
