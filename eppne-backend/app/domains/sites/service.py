# app/domains/sites/service.py
"""منطق شجرة Site الأكاديمية (school→grade→classroom) فقط في هذه
المرحلة — باقي أنواع Site (FACTORY/FARM/...) لسه بلا service/repository
حقيقي (راجع docstring app/domains/sites/router.py)."""
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.domains.sites.models import Site, SiteType
from app.domains.sites.repository import SiteRepository


class SiteService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = SiteRepository(db)

    async def create_academy_campus(self, name: str) -> Site:
        return await self.repo.create_site(
            tenant_id=self.tenant_id,
            site_type=SiteType.ACADEMY_CAMPUS,
            parent_site_id=None,
            name=name,
        )

    async def create_grade_level(self, school_id: int, name: str) -> Site:
        school = await self.repo.get_site(school_id, self.tenant_id)
        if school is None:
            raise NotFoundError("المدرسة غير موجودة")
        if school.site_type != SiteType.ACADEMY_CAMPUS:
            raise ValidationError("الأصل يجب أن يكون من نوع ACADEMY_CAMPUS")
        return await self.repo.create_site(
            tenant_id=self.tenant_id,
            site_type=SiteType.GRADE_LEVEL,
            parent_site_id=school_id,
            name=name,
        )

    async def create_classroom(self, grade_id: int, name: str, max_capacity: int) -> Site:
        grade = await self.repo.get_site(grade_id, self.tenant_id)
        if grade is None:
            raise NotFoundError("المرحلة الدراسية غير موجودة")
        if grade.site_type != SiteType.GRADE_LEVEL:
            raise ValidationError("الأصل يجب أن يكون من نوع GRADE_LEVEL")
        return await self.repo.create_site(
            tenant_id=self.tenant_id,
            site_type=SiteType.CLASSROOM,
            parent_site_id=grade_id,
            name=name,
            geo_metadata={"max_capacity": max_capacity},
        )

    async def list_academy_campuses(self) -> List[Site]:
        return await self.repo.list_sites(self.tenant_id, SiteType.ACADEMY_CAMPUS, parent_site_id=None)

    async def list_grade_levels(self, school_id: int) -> List[Site]:
        school = await self.repo.get_site(school_id, self.tenant_id)
        if school is None:
            raise NotFoundError("المدرسة غير موجودة")
        return await self.repo.list_sites(self.tenant_id, SiteType.GRADE_LEVEL, parent_site_id=school_id)

    async def list_classrooms(self, grade_id: int) -> List[Site]:
        grade = await self.repo.get_site(grade_id, self.tenant_id)
        if grade is None:
            raise NotFoundError("المرحلة الدراسية غير موجودة")
        return await self.repo.list_sites(self.tenant_id, SiteType.CLASSROOM, parent_site_id=grade_id)
