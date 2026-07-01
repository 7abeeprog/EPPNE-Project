# app/domains/zamakana/models.py (الإصدار النهائي المتكامل)
"""
نماذج (Models) قطاع الزمكان – محرك المعرفة والتأثير عبر الزمن
يدير: عقد المعرفة (الحقب، الابتكارات، الأحداث، الشخصيات)،
تأثير الفراشة (العلاقات السببية)، الحملات الكوكبية (تجميع ساعات تطوعية)،
وتحليل السيناريوهات المستقبلية.
"""
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Text, Boolean,
    Numeric, JSON, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ZamakanaNodeType(str, enum.Enum):
    ERA = "ERA"               # حقبة زمنية (العصر الجيولوجي، العصر الذهبي، الثورة الصناعية)
    INNOVATION = "INNOVATION" # اختراع أو ابتكار (العجلة، الإنترنت، الذكاء الاصطناعي، تقنية البلوكشين)
    PERSON = "PERSON"         # شخصية مؤثرة (عالم، قائد، فنان)
    EVENT = "EVENT"           # حدث تاريخي (حرب، معاهدة، اكتشاف، كارثة طبيعية)


class ScenarioStatus(str, enum.Enum):
    DRAFTING = "DRAFTING"         # الذكاء الاصطناعي يقوم بالتحليل
    HUMAN_REVIEW = "HUMAN_REVIEW" # بانتظار مراجعة البشر
    CONFIRMED = "CONFIRMED"       # معتمد وموثق


class ClaimStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"       # تم تقديم الادعاء
    FIELD_VERIFIED = "FIELD_VERIFIED"  # تم التحقق ميدانياً (للجهد البشري)
    ADMIN_APPROVED = "ADMIN_APPROVED"
    REJECTED = "REJECTED"


class PledgeStatus(str, enum.Enum):
    PENDING = "PENDING"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"


# ========== 1. عقد المعرفة (Knowledge Graph) ==========
class ZamakanaNode(Base):
    __tablename__ = "zamakana_nodes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    node_type = Column(SQLEnum(ZamakanaNodeType), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    timeline_year = Column(Integer, nullable=True)          # يمكن أن يكون سالب (قبل الميلاد)
    geo_location = Column(String(255), nullable=True)      # منطقة جغرافية (مثال: "مصر"، "أوروبا"، "الفضاء")

    verified_sources = Column(JSON, default=list)          # قائمة بـ IPFS hashes للمصادر أو الروابط

    # بيانات إضافية خاصة بالنوع
    extra_data = Column(JSON, default=dict)                  # حقل مرن للتوسع

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_zamakana_node_type_year", "node_type", "timeline_year"),
        Index("ix_zamakana_node_title", "title"),
    )


# ========== 2. حواف المعرفة (مع Multi-Tenancy + Idempotency) ==========
class ZamakanaEdge(Base):
    __tablename__ = "zamakana_edges"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    source_node_id = Column(Integer, ForeignKey("zamakana_nodes.id"), nullable=False, index=True)
    target_node_id = Column(Integer, ForeignKey("zamakana_nodes.id"), nullable=False, index=True)

    impact_description = Column(Text, nullable=False)
    impact_weight = Column(Numeric(4, 2), default=1.0)      # قوة التأثير (0.1 - 10.0)
    is_alternative_timeline = Column(Boolean, default=False)  # مسار بديل (ماذا لو)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_zamakana_edge_tenant", "tenant_id"),
        Index("ix_zamakana_edge_pair", "source_node_id", "target_node_id", unique=True),
    )


# ========== 3. الحملات الكوكبية والتعهدات الزمنية (Planetary Campaigns) ==========
class PlanetaryCampaign(Base):
    __tablename__ = "planetary_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    target_time_hours = Column(Numeric(15, 2), nullable=False)   # إجمالي الساعات المطلوبة
    collected_time_hours = Column(Numeric(15, 2), default=0)

    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=False)

    status = Column(String(50), default="ACTIVE")  # ACTIVE, COMPLETED, CANCELLED
    campaign_contract_address = Column(String(42), nullable=True)  # عقد ذكي على السلسلة

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)


# ========== 4. التعهدات الزمنية (مع Multi-Tenancy + Idempotency) ==========
class TimePledge(Base):
    __tablename__ = "time_pledges"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    campaign_id = Column(Integer, ForeignKey("planetary_campaigns.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    pledged_hours = Column(Numeric(10, 2), nullable=False)
    skill_category = Column(String(100), nullable=True)          # مجال المهارة (مثل برمجة، تصميم، تدريس)

    status = Column(SQLEnum(PledgeStatus), default=PledgeStatus.PENDING)
    proof_hash = Column(String(100), nullable=True)               # إثبات إنجاز الساعات (IPFS hash)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_time_pledge_tenant", "tenant_id"),
    )


# ========== 5. المحاكاة المستقبلية (Future Scenarios) ==========
class FutureScenario(Base):
    __tablename__ = "future_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    scenario_title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    target_year = Column(Integer, nullable=False)                # سنة الهدف (مثال 2050)

    # الافتراضات الاقتصادية، البيئية، التكنولوجية، الاجتماعية
    assumptions = Column(JSON, default=dict)

    # تقرير الذكاء الاصطناعي (يتم إنشاؤه بواسطة AI Agent)
    ai_analysis_report = Column(JSON, nullable=True)
    ai_agent_id = Column(Integer, nullable=True)                # معرف الوكيل الذي أنشأ التقرير

    status = Column(SQLEnum(ScenarioStatus), default=ScenarioStatus.DRAFTING)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)


# ========== 6. المراجعات البشرية (مع Multi-Tenancy + Idempotency) ==========
class HumanFeedback(Base):
    __tablename__ = "human_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)  # 🔥 جديد
    idempotency_key = Column(String(255), unique=True, nullable=True, index=True)  # 🔥 جديد
    scenario_id = Column(Integer, ForeignKey("future_scenarios.id"), nullable=False, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    feedback_text = Column(Text, nullable=False)
    agreement_score = Column(Integer, nullable=True)            # 0-100, مدى الاتفاق مع تقرير AI

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_human_feedback_tenant", "tenant_id"),
    )