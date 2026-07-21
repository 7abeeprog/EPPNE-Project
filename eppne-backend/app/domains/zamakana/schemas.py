# app/domains/zamakana/schemas.py (الإصدار النهائي المتكامل)
"""
نماذج (Schemas) Pydantic لقطاع الزمكان – التحقق من صحة البيانات وتسلسلها.
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.domains.zamakana.models import ZamakanaNodeType, ScenarioStatus


# ========== Nodes & Edges ==========
class ZamakanaNodeCreate(BaseModel):
    node_type: ZamakanaNodeType = Field(description="نوع العقدة (ERA, INNOVATION, PERSON, EVENT)")
    title: str = Field(..., min_length=1, max_length=255, description="عنوان العقدة")
    description: str = Field(description="وصف العقدة")
    timeline_year: Optional[int] = Field(default=None, description="السنة الزمنية (يمكن أن تكون سالبة)")
    geo_location: Optional[str] = Field(default=None, description="الموقع الجغرافي")
    verified_sources: List[str] = Field(default=[], description="مصادر موثقة (IPFS hashes)")
    extra_data: Dict[str, Any] = Field(default={}, description="بيانات إضافية مرنة")


class ZamakanaNodeResponse(ZamakanaNodeCreate):
    id: int = Field(description="معرف العقدة")
    created_by: int = Field(description="معرف المنشئ")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    updated_at: datetime = Field(description="تاريخ التحديث")
    model_config = ConfigDict(from_attributes=True)


class ZamakanaEdgeCreate(BaseModel):
    source_node_id: int = Field(description="معرف العقدة المصدر")
    target_node_id: int = Field(description="معرف العقدة الهدف")
    impact_description: str = Field(description="وصف التأثير")
    impact_weight: Decimal = Field(default=Decimal('1.0'), description="قوة التأثير (0.1 - 10.0)")
    is_alternative_timeline: bool = Field(default=False, description="مسار زمني بديل (ماذا لو)")


class ZamakanaEdgeResponse(ZamakanaEdgeCreate):
    id: int = Field(description="معرف الحافة")
    created_by: int = Field(description="معرف المنشئ")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)


# ========== Planetary Campaigns ==========
class PlanetaryCampaignCreate(BaseModel):
    title: str = Field(description="عنوان الحملة")
    description: str = Field(description="وصف الحملة")
    target_time_hours: Decimal = Field(..., gt=0, description="الهدف بالساعات")
    end_date: datetime = Field(description="تاريخ الانتهاء")

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v, info):
        start = info.data.get("start_date")
        if start and v <= start:
            raise ValueError("end_date must be after start_date")
        return v


class PlanetaryCampaignResponse(PlanetaryCampaignCreate):
    id: int = Field(description="معرف الحملة")
    created_by: int = Field(description="معرف المنشئ")
    collected_time_hours: Decimal = Field(description="الساعات المجمعة")
    status: str = Field(description="الحالة (ACTIVE, COMPLETED, CANCELLED)")
    campaign_contract_address: Optional[str] = Field(default=None, description="عنوان العقد الذكي")
    start_date: datetime = Field(description="تاريخ البدء")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    updated_at: datetime = Field(description="تاريخ التحديث")
    model_config = ConfigDict(from_attributes=True)


class TimePledgeCreate(BaseModel):
    campaign_id: int = Field(description="معرف الحملة")
    pledged_hours: Decimal = Field(..., gt=0, description="الساعات المتعهد بها")
    skill_category: Optional[str] = Field(default=None, description="فئة المهارة")


class TimePledgeResponse(TimePledgeCreate):
    id: int = Field(description="معرف التعهد")
    user_id: int = Field(description="معرف المستخدم")
    status: str = Field(description="الحالة (PENDING, FULFILLED, CANCELLED)")
    proof_hash: Optional[str] = Field(default=None, description="هاش إثبات الإنجاز")
    verified_by: Optional[int] = Field(default=None, description="معرف المدقق")
    verified_at: Optional[datetime] = Field(default=None, description="تاريخ التحقق")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)


class TimePledgeFulfill(BaseModel):
    proof_hash: str = Field(description="رابط IPFS لإثبات الإنجاز")


# ========== Future Scenarios ==========
class FutureScenarioCreate(BaseModel):
    scenario_title: str = Field(description="عنوان السيناريو")
    description: str = Field(description="وصف السيناريو")
    target_year: int = Field(..., ge=2025, le=3000, description="السنة المستهدفة")
    assumptions: Dict[str, Any] = Field(default={}, description="الافتراضات (اقتصادية، بيئية، اجتماعية)")


class FutureScenarioResponse(FutureScenarioCreate):
    id: int = Field(description="معرف السيناريو")
    created_by: int = Field(description="معرف المنشئ")
    ai_analysis_report: Optional[Dict[str, Any]] = Field(default=None, description="تقرير تحليل الذكاء الاصطناعي")
    ai_agent_id: Optional[int] = Field(default=None, description="معرف وكيل الذكاء الاصطناعي")
    status: ScenarioStatus = Field(description="الحالة (DRAFTING, HUMAN_REVIEW, CONFIRMED)")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    updated_at: datetime = Field(description="تاريخ التحديث")
    model_config = ConfigDict(from_attributes=True)


class HumanFeedbackCreate(BaseModel):
    scenario_id: int = Field(description="معرف السيناريو")
    feedback_text: str = Field(description="نص المراجعة")
    agreement_score: Optional[int] = Field(default=None, ge=0, le=100, description="درجة الاتفاق (0-100)")


class HumanFeedbackResponse(HumanFeedbackCreate):
    id: int = Field(description="معرف المراجعة")
    reviewer_id: int = Field(description="معرف المراجع")
    created_at: datetime = Field(description="تاريخ الإنشاء")
    model_config = ConfigDict(from_attributes=True)