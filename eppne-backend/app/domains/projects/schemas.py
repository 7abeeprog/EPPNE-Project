# app/domains/projects/schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from .models import ProjectType, ProjectStatus, ContributionType, CarbonImpactScope


# ---------- Project ----------
class ProjectCreate(BaseModel):
    title: str = Field(..., max_length=255, description="عنوان المشروع")
    description: str = Field(..., description="وصف المشروع")
    project_type: ProjectType = Field(description="نوع المشروع")
    country: Optional[str] = Field(default=None, description="الدولة")
    city: Optional[str] = Field(default=None, description="المدينة")
    latitude: Optional[float] = Field(default=None, description="خط العرض")
    longitude: Optional[float] = Field(default=None, description="خط الطول")
    address: Optional[str] = Field(default=None, description="العنوان التفصيلي")
    funding_goal_mrusdt: Decimal = Field(..., gt=0, description="الهدف التمويلي")
    min_investment_mrusdt: Decimal = Field(default=Decimal('0.0'), description="الحد الأدنى للاستثمار")
    currency: str = Field(default="MR_USDT", description="العملة")
    expected_roi_percentage: Optional[Decimal] = Field(default=None, description="العائد المتوقع %")
    expected_irr_percentage: Optional[Decimal] = Field(default=None, description="معدل العائد الداخلي المتوقع %")
    payback_period_years: Optional[int] = Field(default=None, description="فترة الاسترداد بالسنوات")
    projected_cash_flows: Optional[List[Dict[str, Any]]] = Field(default=None, description="التدفقات النقدية المتوقعة")
    carbon_impact_scope: Optional[CarbonImpactScope] = Field(default=None, description="نطاق الأثر الكربوني")
    estimated_carbon_emissions_tonnes: Optional[Decimal] = Field(default=None, description="الانبعاثات الكربونية المقدرة (طن)")
    estimated_carbon_offset_tonnes: Optional[Decimal] = Field(default=None, description="تعويض الكربون المقدر (طن)")
    allow_in_kind_contributions: bool = Field(default=True, description="السماح بالمساهمات العينية")
    allow_fractional_ownership: bool = Field(default=False, description="السماح بالملكية الجزئية")
    shares_total: Optional[Decimal] = Field(default=None, description="إجمالي الأسهم")
    share_price_mrusdt: Optional[Decimal] = Field(default=None, description="سعر السهم")
    cover_image_url: Optional[str] = Field(default=None, description="رابط صورة الغلاف")
    gallery_urls: List[str] = Field(default=[], description="معرض الصور")
    documents_urls: List[str] = Field(default=[], description="روابط المستندات")


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(default=None, description="العنوان")
    description: Optional[str] = Field(default=None, description="الوصف")
    status: Optional[ProjectStatus] = Field(default=None, description="الحالة")
    expected_roi_percentage: Optional[Decimal] = Field(default=None, description="العائد المتوقع %")
    expected_irr_percentage: Optional[Decimal] = Field(default=None, description="معدل العائد الداخلي المتوقع %")
    actual_carbon_emissions_tonnes: Optional[Decimal] = Field(default=None, description="الانبعاثات الفعلية (طن)")
    actual_carbon_offset_tonnes: Optional[Decimal] = Field(default=None, description="تعويض الكربون الفعلي (طن)")
    is_published: Optional[bool] = Field(default=None, description="منشور؟")


class ProjectResponse(ProjectCreate):
    id: int = Field(description="معرف المشروع")
    owner_id: int = Field(description="معرف المالك")
    status: ProjectStatus = Field(description="الحالة")
    current_funding_mrusdt: Decimal = Field(description="التمويل الحالي")
    start_date: Optional[datetime] = Field(default=None, description="تاريخ البدء")
    expected_completion_date: Optional[datetime] = Field(default=None, description="تاريخ الانتهاء المتوقع")
    actual_completion_date: Optional[datetime] = Field(default=None, description="تاريخ الانتهاء الفعلي")
    is_published: bool = Field(description="منشور؟")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    updated_at: datetime = Field(description="تاريخ التحديث")

    model_config = ConfigDict(from_attributes=True)


# ---------- Contributions ----------
class ContributionCreate(BaseModel):
    project_id: int = Field(description="معرف المشروع")
    contribution_type: ContributionType = Field(description="نوع المساهمة")
    # monetary
    amount_mrusdt: Optional[Decimal] = Field(default=None, description="المبلغ المالي")
    # land / facility
    land_area_sqm: Optional[Decimal] = Field(default=None, description="مساحة الأرض (م²)")
    land_address: Optional[str] = Field(default=None, description="عنوان الأرض")
    land_title_deed_hash: Optional[str] = Field(default=None, description="هاش صك الملكية")
    # labor hours
    labor_hours: Optional[Decimal] = Field(default=None, description="عدد ساعات العمل")
    labor_description: Optional[str] = Field(default=None, description="وصف العمل")
    # equipment
    equipment_description: Optional[str] = Field(default=None, description="وصف المعدات")
    equipment_estimated_value: Optional[Decimal] = Field(default=None, description="القيمة التقديرية للمعدات")
    # consulting
    consulting_hours: Optional[Decimal] = Field(default=None, description="عدد ساعات الاستشارة")
    consulting_expertise: Optional[str] = Field(default=None, description="مجال الخبرة")


class ContributionResponse(BaseModel):
    id: int = Field(description="معرف المساهمة")
    project_id: int = Field(description="معرف المشروع")
    contributor_id: int = Field(description="معرف المساهم")
    contribution_type: ContributionType = Field(description="نوع المساهمة")
    equivalent_value_mrusdt: Decimal = Field(description="القيمة المعادلة")
    status: str = Field(description="الحالة")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    approved_at: Optional[datetime] = Field(default=None, description="تاريخ الموافقة")

    model_config = ConfigDict(from_attributes=True)


class ContributionApprove(BaseModel):
    approved: bool = Field(..., description="True للموافقة، False للرفض")
    notes: Optional[str] = Field(default=None, description="ملاحظات")


# ---------- Milestones ----------
class MilestoneCreate(BaseModel):
    title: str = Field(..., description="عنوان المرحلة")
    description: Optional[str] = Field(default=None, description="وصف المرحلة")
    target_date: datetime = Field(..., description="التاريخ المستهدف")
    funds_to_release: Decimal = Field(default=Decimal('0.0'), description="الأموال المطلقة عند الإكمال")


class MilestoneResponse(MilestoneCreate):
    id: int = Field(description="معرف المرحلة")
    project_id: int = Field(description="معرف المشروع")
    is_completed: bool = Field(description="هل اكتملت؟")
    actual_date: Optional[datetime] = Field(default=None, description="التاريخ الفعلي للإكمال")
    created_at: datetime = Field(description="تاريخ الإنشاء")

    model_config = ConfigDict(from_attributes=True)


class MilestoneComplete(BaseModel):
    actual_date: datetime = Field(..., description="تاريخ الإكمال الفعلي")
    completion_notes: Optional[str] = Field(default=None, description="ملاحظات الإكمال")


# ---------- Updates & Follow ----------
class ProjectUpdateCreate(BaseModel):
    title: str = Field(..., description="عنوان التحديث")
    content: str = Field(..., description="محتوى التحديث")
    media_urls: List[str] = Field(default=[], description="روابط الوسائط")


class ProjectUpdateResponse(ProjectUpdateCreate):
    id: int = Field(description="معرف التحديث")
    project_id: int = Field(description="معرف المشروع")
    author_id: int = Field(description="معرف المؤلف")
    created_at: datetime = Field(description="تاريخ الإنشاء")

    model_config = ConfigDict(from_attributes=True)


class FollowResponse(BaseModel):
    user_id: int = Field(description="معرف المستخدم")
    project_id: int = Field(description="معرف المشروع")
    created_at: datetime = Field(description="تاريخ المتابعة")

    model_config = ConfigDict(from_attributes=True)


# ---------- Analytics ----------
class ProjectAnalyticsResponse(BaseModel):
    project_id: int = Field(description="معرف المشروع")
    title: str = Field(description="عنوان المشروع")
    status: str = Field(description="الحالة")
    total_contributors: int = Field(description="إجمالي المساهمين الفريدين")
    total_monetary_contributions: Decimal = Field(description="إجمالي المساهمات المالية")
    total_in_kind_value: Decimal = Field(description="إجمالي قيمة المساهمات العينية")
    total_funding_mrusdt: Decimal = Field(description="إجمالي التمويل (مالي + عيني)")
    funding_percentage: float = Field(description="النسبة المئوية للتمويل")
    remaining_to_goal: Decimal = Field(description="المتبقي للهدف")
    milestones_completed: int = Field(description="عدد المراحل المكتملة")
    milestones_total: int = Field(description="إجمالي المراحل")
    updated_at: str = Field(description="آخر تحديث للتحليلات")