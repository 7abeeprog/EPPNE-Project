"""
regression test لجلسة `academy-site-hierarchy-endpoints-implementation`
(2026-09-17) — POST+GET لشجرة Site الأكاديمية (ACADEMY_CAMPUS→GRADE_LEVEL→
CLASSROOM) فوق app/domains/sites/models.py (migration 057، صفر service/
repository قبل هذه الجلسة). راجع الجلسة التصميمية السابقة (read-only) قبل
التنفيذ.

**مؤجَّل عمدًا في هذه الدفعة (مش باج، قرار نطاق):** DELETE، وربط
classroom_camera_analyses.site_id (العمود ده مش موجود أصلًا في الموديل
الحالي — تأكَّد بالفحص المباشر قبل التصميم).

يغطي:
1) الصلاحيات عبر HTTP فعلي: نفس نمط create_cohort/create_track بالحرف —
   get_current_superuser (SUPER_ADMIN/EXECUTIVE_DIRECTOR) — مستخدم عادي
   يترفض بـ403، SUPER_ADMIN يُسمح له وبيرجع site_type=ACADEMY_CAMPUS.
2) تحقق نوع الأصل (parent site_type) عند إنشاء grade/classroom — أصل من
   نوع خطأ → ValidationError (422 عبر core/errors.py).
3) validation على max_capacity (20-60) عند مستوى Pydantic schema.
4) قوائم GET مربوطة بـtenant_id + parent_site_id بشكل صحيح (عزل تينانت).
"""
import uuid

import pytest
import httpx
from sqlalchemy import delete, update

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.core.security import get_current_active_user
from app.core.enums import SystemRole
from app.core.errors import ValidationError, NotFoundError

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.sites.service import SiteService
from app.domains.sites.models import Site, SiteType

TENANT_ID = 1
OTHER_TENANT_ID = 16  # "TEST_TENANT_B" — throwaway، نفس اللي بيستخدمه test_identity_users_search_implementation.py


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str, tenant_id: int = TENANT_ID) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, tenant_id).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


async def _cleanup_sites(site_ids):
    if not site_ids:
        return
    async with AsyncSessionLocal() as cleanup_db:
        await cleanup_db.execute(delete(Site).where(Site.id.in_(site_ids)))
        await cleanup_db.commit()


# ============================================================
# 1) الصلاحيات عبر HTTP فعلي — get_current_superuser بالحرف
# ============================================================

@pytest.mark.asyncio
async def test_create_campus_requires_superuser_via_http(db):
    regular_user = await _create_user(db, "p_regtest_siteshier_regular")
    super_admin = await _create_user(db, "p_regtest_siteshier_superadmin")
    site_ids = []

    try:
        await db.execute(update(User).where(User.id == super_admin.id).values(system_role=SystemRole.SUPER_ADMIN))
        await db.commit()

        transport = httpx.ASGITransport(app=fastapi_app)

        fastapi_app.dependency_overrides[get_current_active_user] = lambda: regular_user
        try:
            async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
                forbidden = await client.post("/api/academy/sites", json={"name": f"REGTEST-CAMPUS-{_suffix()}"})
        finally:
            fastapi_app.dependency_overrides.pop(get_current_active_user, None)
        assert forbidden.status_code == 403, forbidden.text[:500]

        fastapi_app.dependency_overrides[get_current_active_user] = lambda: super_admin
        try:
            async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
                allowed = await client.post("/api/academy/sites", json={"name": f"REGTEST-CAMPUS-{_suffix()}"})
        finally:
            fastapi_app.dependency_overrides.pop(get_current_active_user, None)
        assert allowed.status_code == 201, allowed.text[:500]
        body = allowed.json()
        site_ids.append(body["id"])
        assert body["site_type"] == "ACADEMY_CAMPUS"
        assert body["parent_site_id"] is None
        assert body["tenant_id"] == TENANT_ID
    finally:
        await _cleanup_sites(site_ids)
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(User).where(User.id.in_([regular_user.id, super_admin.id])))
            await cleanup_db.commit()


# ============================================================
# 2) تحقق نوع الأصل + max_capacity (20-60) — منطق الخدمة مباشرة
# ============================================================

@pytest.mark.asyncio
async def test_hierarchy_parent_type_validation_and_capacity_range(db):
    service = SiteService(db, TENANT_ID)
    site_ids = []
    try:
        campus = await service.create_academy_campus(f"REGTEST-CAMPUS-{_suffix()}")
        site_ids.append(campus.id)

        grade = await service.create_grade_level(campus.id, f"REGTEST-GRADE-{_suffix()}")
        site_ids.append(grade.id)
        assert grade.site_type == SiteType.GRADE_LEVEL
        assert grade.parent_site_id == campus.id

        classroom = await service.create_classroom(grade.id, f"REGTEST-CLASS-{_suffix()}", max_capacity=30)
        site_ids.append(classroom.id)
        assert classroom.site_type == SiteType.CLASSROOM
        assert classroom.parent_site_id == grade.id
        assert classroom.geo_metadata.get("max_capacity") == 30

        # أصل من نوع خطأ لكلٍ من grade/classroom
        with pytest.raises(ValidationError):
            await service.create_grade_level(classroom.id, f"REGTEST-GRADE-BADPARENT-{_suffix()}")
        with pytest.raises(ValidationError):
            await service.create_classroom(campus.id, f"REGTEST-CLASS-BADPARENT-{_suffix()}", max_capacity=30)

        # أصل غير موجود
        with pytest.raises(NotFoundError):
            await service.create_grade_level(999_999_999, f"REGTEST-GRADE-NOPARENT-{_suffix()}")
    finally:
        await _cleanup_sites(site_ids)


@pytest.mark.asyncio
async def test_classroom_capacity_out_of_range_rejected_via_http(db):
    """20-60 عند مستوى Pydantic schema — HTTP فعلي (422 قبل ما يوصل للخدمة أصلًا).

    لازم تاخد fixture `db` (مش AsyncSessionLocal() يدوي بلا fixture) — teardown
    الـfixture (conftest.py) هو اللي بيعمل engine.dispose() الضروري على
    Windows، وإلا الاختبار اللي بعده بيكراش بـ'Event loop is closed' لما
    يحاول يستخدم connection متسربة من event loop القديم (اتلقط ده حيًا هنا)."""
    super_admin = await _create_user(db, "p_regtest_siteshier_capadmin")
    await db.execute(update(User).where(User.id == super_admin.id).values(system_role=SystemRole.SUPER_ADMIN))
    await db.commit()

    site_ids = []
    service = SiteService(db, TENANT_ID)
    campus = await service.create_academy_campus(f"REGTEST-CAMPUS-{_suffix()}")
    site_ids.append(campus.id)
    grade = await service.create_grade_level(campus.id, f"REGTEST-GRADE-{_suffix()}")
    site_ids.append(grade.id)

    try:
        transport = httpx.ASGITransport(app=fastapi_app)
        fastapi_app.dependency_overrides[get_current_active_user] = lambda: super_admin
        try:
            async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
                too_small = await client.post(
                    f"/api/academy/sites/{grade.id}/classes",
                    json={"name": f"REGTEST-CLASS-{_suffix()}", "max_capacity": 5},
                )
                too_big = await client.post(
                    f"/api/academy/sites/{grade.id}/classes",
                    json={"name": f"REGTEST-CLASS-{_suffix()}", "max_capacity": 200},
                )
        finally:
            fastapi_app.dependency_overrides.pop(get_current_active_user, None)
        assert too_small.status_code == 422, too_small.text[:500]
        assert too_big.status_code == 422, too_big.text[:500]
    finally:
        await _cleanup_sites(site_ids)
        async with AsyncSessionLocal() as cleanup_db:
            await cleanup_db.execute(delete(User).where(User.id == super_admin.id))
            await cleanup_db.commit()


# ============================================================
# 3) GET lists — عزل تينانت + parent_site_id صحيح
# ============================================================

@pytest.mark.asyncio
async def test_list_endpoints_scoped_by_tenant_and_parent(db):
    service = SiteService(db, TENANT_ID)
    other_service = SiteService(db, OTHER_TENANT_ID)
    site_ids = []
    other_site_ids = []
    try:
        campus = await service.create_academy_campus(f"REGTEST-CAMPUS-{_suffix()}")
        site_ids.append(campus.id)
        grade = await service.create_grade_level(campus.id, f"REGTEST-GRADE-{_suffix()}")
        site_ids.append(grade.id)
        classroom = await service.create_classroom(grade.id, f"REGTEST-CLASS-{_suffix()}", max_capacity=25)
        site_ids.append(classroom.id)

        other_campus = await other_service.create_academy_campus(f"REGTEST-CAMPUS-OTHERTENANT-{_suffix()}")
        other_site_ids.append(other_campus.id)

        campuses = await service.list_academy_campuses()
        campus_ids = {c.id for c in campuses}
        assert campus.id in campus_ids
        assert other_campus.id not in campus_ids

        grades = await service.list_grade_levels(campus.id)
        assert {g.id for g in grades} == {grade.id}

        classrooms = await service.list_classrooms(grade.id)
        assert {c.id for c in classrooms} == {classroom.id}
    finally:
        await _cleanup_sites(site_ids)
        await _cleanup_sites(other_site_ids)
