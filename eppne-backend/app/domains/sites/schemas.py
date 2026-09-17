# app/domains/sites/schemas.py
"""Schemas لشجرة Site الأكاديمية (ACADEMY_CAMPUS→GRADE_LEVEL→CLASSROOM) —
POST+GET فقط في هذه الدفعة. راجع
.claude/reports/academy-site-hierarchy-endpoints-session-log.md."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.domains.sites.models import SiteType


class AcademyCampusCreate(BaseModel):
    name: str


class GradeLevelCreate(BaseModel):
    name: str


class ClassroomCreate(BaseModel):
    name: str
    max_capacity: int = Field(ge=20, le=60)


class SiteResponse(BaseModel):
    id: int
    tenant_id: int
    parent_site_id: Optional[int] = None
    site_type: SiteType
    name: str
    # max_capacity للفصول مخزّن هنا (geo_metadata JSONB) — صفر عمود مخصص
    # بصفر migration جديدة في هذه الدفعة. راجع §تصميم الشجرة.
    geo_metadata: dict
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
