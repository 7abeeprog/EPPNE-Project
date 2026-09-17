# app/domains/sites/repository.py
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.sites.models import Site, SiteType


class SiteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_site(self, **kwargs) -> Site:
        site = Site(**kwargs)
        self.db.add(site)
        await self.db.commit()
        await self.db.refresh(site)
        return site

    async def get_site(self, site_id: int, tenant_id: int) -> Optional[Site]:
        result = await self.db.execute(
            select(Site).where(
                Site.id == site_id, Site.tenant_id == tenant_id, Site.is_deleted == False  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list_sites(
        self, tenant_id: int, site_type: SiteType, parent_site_id: Optional[int]
    ) -> List[Site]:
        query = select(Site).where(
            Site.tenant_id == tenant_id,
            Site.site_type == site_type,
            Site.parent_site_id == parent_site_id,
            Site.is_deleted == False,  # noqa: E712
        ).order_by(Site.id)
        result = await self.db.execute(query)
        return list(result.scalars().all())
