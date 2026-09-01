"""
regression test لجلسة `frontend-category-b-phase1-cheap-wins` (2026-09-01).
تقرير الجلسة: .claude/reports/frontend-category-b-phase1-session-log.md

السياق: `getJob` كانت مطلوبة من الفرونت إند (`app/(dashboard)/employment/jobs/[jobId]/page.tsx`)
عبر `GET /employment/jobs/{job_id}`، ولم يكن لها service method ولا router
endpoint، رغم أن `EmploymentRepository.get_job_listing(job_id, tenant_id)`
كانت جاهزة بالفعل بدون أي وصلة. هذا الاختبار يتحقق حيًا (DB حقيقية، صفر
mock) من الوصلة الجديدة `EmploymentService.get_job` (+ `GET /employment/jobs/{job_id}`
في router.py الذي ينادي نفس الميثودز).
"""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import delete

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels
from app.core.database import AsyncSessionLocal
from app.core.errors import NotFoundError

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.employment.service import EmploymentService
from app.domains.employment.repository import EmploymentRepository
from app.domains.employment.models import JobListing

TENANT_ID = 1
OTHER_TENANT_ID = 2


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
async def test_get_job_returns_real_record_and_scopes_tenant(db):
    employer = await _create_user(db, "p_regtest_getjob_employer")
    repo = EmploymentRepository(db)
    job = await repo.create_job_listing(
        tenant_id=TENANT_ID,
        employer_id=employer.id,
        title=f"REGTEST-JOB-{_suffix()}",
        description="regression test job",
        required_skills=[],
        required_certificate_ids=[],
        salary_min=Decimal("1000"),
        salary_max=Decimal("2000"),
        currency="MR_USDT",
        employment_type="FULL_TIME",
        is_active=True,
    )
    job_id = job.id

    service = EmploymentService(db)
    try:
        result = await service.get_job(job_id, tenant_id=TENANT_ID)
        assert result.id == job_id
        assert result.employer_id == employer.id
        assert result.title == job.title

        # معرف غير موجود → NotFoundError
        with pytest.raises(NotFoundError):
            await service.get_job(999_999_999, tenant_id=TENANT_ID)

        # نفس المعرف لكن tenant_id غلط → NotFoundError (تأكيد الـtenant scoping)
        with pytest.raises(NotFoundError):
            await service.get_job(job_id, tenant_id=OTHER_TENANT_ID)
    finally:
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(JobListing).where(JobListing.id == job_id))
            await cleanup_db.execute(delete(User).where(User.id == employer.id))
            await cleanup_db.commit()
