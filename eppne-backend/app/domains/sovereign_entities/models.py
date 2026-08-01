"""
نماذج قطاع الكيانات السيادية والهوية المؤسسية
يدعم: تسجيل الكيانات (دول، وزارات، شركات، منظمات)، التحقق (KYB)، الهيكل الهرمي،
بناء الصفحات التفاعلية (Drag & Drop)، والتكامل مع القطاعات الأخرى.
"""
from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey, DateTime, Text,
    Boolean, Numeric, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base
import enum


# ========== أنواع الكيانات السيادية ==========
class SovereignEntityType(str, enum.Enum):
    STATE_GOVERNMENT = "STATE_GOVERNMENT"              # دولة/حكومة
    MINISTRY_AUTHORITY = "MINISTRY_AUTHORITY"          # وزارة/هيئة حكومية
    INTERNATIONAL_ORGANIZATION = "INTERNATIONAL_ORGANIZATION"  # منظمة دولية
    MULTINATIONAL_CORP = "MULTINATIONAL_CORP"          # شركة متعددة الجنسيات
    ENTERPRISE = "ENTERPRISE"                          # شركة تجارية/صناعية
    NGO_CIVIL_SOCIETY = "NGO_CIVIL_SOCIETY"            # منظمة مجتمع مدني
    ACADEMIC_INSTITUTION = "ACADEMIC_INSTITUTION"      # جامعة/مركز بحثي
    
    # 🟢 النوعان الجديدان للهيكل الداخلي
    DIVISION = "DIVISION"      # إدارة / قطاع داخل المؤسسة
    TEAM = "TEAM"              # فريق عمل / فرع


class KYBStatus(str, enum.Enum):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class EntityRole(str, enum.Enum):
    OWNER = "OWNER"                  # المالك/المؤسس
    EXECUTIVE_DIRECTOR = "EXECUTIVE_DIRECTOR"  # المدير التنفيذي
    SIGNATORY = "SIGNATORY"          # مفوض بالتوقيع
    REPRESENTATIVE = "REPRESENTATIVE" # ممثل عام


# ========== 1. جدول الكيان الرئيسي ==========
class SovereignEntity(Base):
    __tablename__ = "sovereign_entities_v2"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    # البيانات الأساسية
    name = Column(String(255), nullable=False, index=True)
    legal_name = Column(String(255), nullable=True)          # الاسم القانوني المسجل
    entity_type = Column(SQLEnum(SovereignEntityType), nullable=False, index=True)

    # التسجيل القانوني
    registration_number = Column(String(100), unique=True, nullable=True)  # رقم التسجيل الضريبي/التجاري
    tax_id = Column(String(100), nullable=True)
    country_of_origin = Column(String(100), nullable=False)
    city = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)

    # التواصل الرسمي
    official_email = Column(String(255), nullable=False)
    official_phone = Column(String(50), nullable=True)
    website = Column(String(255), nullable=True)

    # المحفظة المالية السيادية (Web3)
    wallet_address = Column(String(42), unique=True, nullable=True)   # محفظة لامركزية للكيانات
    treasury_balance_mrusdt = Column(Numeric(30, 8), default=0)

    # العلامة التجارية والهوية
    logo_url = Column(String(512), nullable=True)
    cover_image_url = Column(String(512), nullable=True)
    primary_color = Column(String(7), default="#8CC63F")   # لون العلامة التجارية
    secondary_color = Column(String(7), default="#06b6d4")

    # التحقق (KYB)
    kyb_status = Column(SQLEnum(KYBStatus), default=KYBStatus.PENDING, index=True)
    kyb_documents = Column(JSONB, default=list)            # قائمة بالمستندات المرفوعة
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # العلاقات الهرمية (لربط الشركات التابعة، الإدارات، إلخ)
    parent_id = Column(Integer, ForeignKey("sovereign_entities_v2.id"), nullable=True, index=True)

    # الحالة العامة
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # الطوابع الزمنية
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_entity_type_status", "entity_type", "kyb_status"),
        Index("ix_entity_parent", "parent_id"),
    )


# ========== 2. ممثلو الكيان (الموظفون المفوضون) ==========
class EntityRepresentative(Base):
    __tablename__ = "entity_representatives"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("sovereign_entities_v2.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    role = Column(SQLEnum(EntityRole), nullable=False)          # دوره في الكيان
    is_active = Column(Boolean, default=True)

    # صلاحيات التوقيع الإلكتروني
    can_sign_contracts = Column(Boolean, default=False)
    signature_pub_key = Column(String(512), nullable=True)      # مفتاح التوقيع

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_entity_rep_unique", "entity_id", "user_id", unique=True),
    )


# ========== 3. الهوية المؤسسية (Brand Builder – Drag & Drop) ==========
class EntityPageTemplate(Base):
    __tablename__ = "entity_page_templates"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(String(512), nullable=True)

    # قالب الصفحة (JSON قابل للتصدير)
    page_structure = Column(JSONB, nullable=False)   # مكونات الصفحة (sections, blocks)
    is_public = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EntityPage(Base):
    __tablename__ = "entity_pages"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("sovereign_entities_v2.id"), unique=True, nullable=False, index=True)
    
    # 🔥 إضافة tenant_id مع ForeignKey وفهرس
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    # إما قالب مسبق أو محتوى مخصص
    template_id = Column(Integer, ForeignKey("entity_page_templates.id"), nullable=True)
    custom_structure = Column(JSONB, nullable=True)   # إذا تم تعديل القالب

    # SEO والإعدادات
    slug = Column(String(255), unique=True, nullable=False, index=True)  # المسار: /entity/ministry-of-agriculture
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(Text, nullable=True)
    custom_domain = Column(String(255), unique=True, nullable=True)      # نطاق مخصص (subdomain.example.com)

    # صفحات إضافية (About, Services, Contact, إلخ)
    custom_pages = Column(JSONB, default=list)   # [{slug: "about", title: "عن الشركة", content: {...}}]

    # إحصائيات الصفحة
    visits_count = Column(Integer, default=0)
    last_visit_at = Column(DateTime(timezone=True), nullable=True)

    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_entity_pages_tenant_id", "tenant_id"),  # 🔥 فهرس جديد
    )


# ========== 4. مكونات الصفحة (Draggable Blocks) – لمكتبة المكونات ==========
class PageComponent(Base):
    __tablename__ = "page_components"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    component_type = Column(String(50), nullable=False)  # hero, features, testimonials, pricing, contact, gallery, etc.
    default_props = Column(JSONB, default=dict)           # الخصائص الافتراضية (نص، صور، روابط)
    preview_image = Column(String(512), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ========== 5. توثيق المستندات (KYB) ==========
class EntityDocument(Base):
    __tablename__ = "entity_documents"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("sovereign_entities_v2.id"), nullable=False, index=True)

    document_type = Column(String(50), nullable=False)  # commercial_register, tax_card, authorization_letter, etc.
    document_url = Column(String(512), nullable=False)
    ipfs_hash = Column(String(100), nullable=True)      # تخزين لامركزي
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    status = Column(String(50), default="PENDING")      # PENDING, APPROVED, REJECTED
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())