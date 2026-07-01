from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean, Numeric, JSON, Enum as SQLEnum, Index, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.enums import SovereignRank

# ============================================
# 1. المستأجر الأساسي (النطاق)
# ============================================
class AcademyTenant(Base):
    __tablename__ = "academy_tenants"
    __table_args__ = (
        Index("ix_tenant_domain_active", "domain", "is_active"),  # للبحث السريع بالنطاق الفعال
        Index("ix_tenant_admin", "admin_id"),
        Index("ix_tenant_name", "name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    domain = Column(String(255), unique=True, index=True, nullable=False)
    branding = Column(JSON, default=dict)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# ============================================
# 2. الكيان التنظيمي (الشجرة السيادية)
# ============================================
class OrganizationEntity(Base):
    __tablename__ = "organization_entities"
    __table_args__ = (
        Index("ix_org_tenant_entity_type", "tenant_id", "entity_type"),  # تصفية حسب النوع ضمن المستأجر
        Index("ix_org_tenant_active", "tenant_id", "is_active"),
        Index("ix_org_parent_id", "parent_id"),
        Index("ix_org_name", "name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("organization_entities.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    parent = relationship("OrganizationEntity", remote_side=[id], back_populates="children")
    children = relationship(
        "OrganizationEntity",
        back_populates="parent",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="OrganizationEntity.name"  # ترتيب ثابت لتجنب المفاجآت
    )

# ============================================
# 3. المدرّبون
# ============================================
class Instructor(Base):
    __tablename__ = "academy_instructors"
    __table_args__ = (
        Index("ix_instructor_org_entity", "org_entity_id"),
        Index("ix_instructor_approved", "is_approved"),
        Index("ix_instructor_user_org", "user_id", "org_entity_id"),  # استعلامات المدرب ضمن كيانه
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    org_entity_id = Column(Integer, ForeignKey("organization_entities.id"), nullable=False, index=True)
    bio = Column(Text, nullable=True)
    expertise_areas = Column(JSON, default=list)
    revenue_share_percentage = Column(Numeric(5, 2), default=70.0)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# ============================================
# 4. الدفعات الدراسية (Cohorts)
# ============================================
class AcademyCohort(Base):
    __tablename__ = "academy_cohorts"
    __table_args__ = (
        Index("ix_cohort_org_active", "org_entity_id", "is_active"),
        Index("ix_cohort_dates", "start_date", "end_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_entity_id = Column(Integer, ForeignKey("organization_entities.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    max_capacity = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# ============================================
# 5. المعسكرات، المسارات، الكورسات
# ============================================
class Bootcamp(Base):
    __tablename__ = "academy_bootcamps"
    __table_args__ = (
        Index("ix_bootcamp_org_active", "org_entity_id", "is_active"),
        Index("ix_bootcamp_rank", "target_rank"),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_entity_id = Column(Integer, ForeignKey("organization_entities.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    duration_days = Column(Integer, default=100)
    target_rank = Column(SQLEnum(SovereignRank), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Track(Base):
    __tablename__ = "academy_tracks"
    __table_args__ = (
        Index("ix_track_bootcamp", "bootcamp_id"),
        Index("ix_track_org_active", "org_entity_id", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    bootcamp_id = Column(Integer, ForeignKey("academy_bootcamps.id"), nullable=True, index=True)
    org_entity_id = Column(Integer, ForeignKey("organization_entities.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Course(Base):
    __tablename__ = "academy_courses"
    __table_args__ = (
        # 🚀 الفهارس الأهم في النظام (ستُستخدم ملايين المرات)
        Index("ix_course_tenant_published", "tenant_id", "is_published", "is_active"),  # تصفية متجر الكورسات
        Index("ix_course_org_entity", "org_entity_id"),
        Index("ix_course_track", "track_id"),
        Index("ix_course_bootcamp", "bootcamp_id"),
        Index("ix_course_instructor", "instructor_id"),
        Index("ix_course_tenant_active", "tenant_id", "is_active"),
        Index("ix_course_price_currency", "price_mrusdt", "currency"),  # لتقارير المالية
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("academy_tenants.id"), nullable=False, index=True)
    org_entity_id = Column(Integer, ForeignKey("organization_entities.id"), nullable=False, index=True)
    track_id = Column(Integer, ForeignKey("academy_tracks.id"), nullable=True, index=True)
    bootcamp_id = Column(Integer, ForeignKey("academy_bootcamps.id"), nullable=True, index=True)
    instructor_id = Column(Integer, ForeignKey("academy_instructors.id"), nullable=True, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text)
    thumbnail_url = Column(String(1024))
    price_mrusdt = Column(Numeric(30, 8), default=0)
    currency = Column(String(20), default="MR_USDT")
    level = Column(String(50), default="BEGINNER")
    is_free = Column(Boolean, default=False)
    is_published = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# ============================================
# 6. الوحدات، الدروس، المواد، والاختبارات
# ============================================
class CourseUnit(Base):
    __tablename__ = "course_units"
    __table_args__ = (
        Index("ix_unit_course_order", "course_id", "order_index"),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("academy_courses.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"
    __table_args__ = (
        Index("ix_node_course_order", "course_id", "order_index"),
        Index("ix_node_unit", "unit_id"),
        Index("ix_node_content_type", "content_type"),
        Index("ix_node_mandatory", "is_mandatory"),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("academy_courses.id"), nullable=False, index=True)
    unit_id = Column(Integer, ForeignKey("course_units.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    content_type = Column(String(50), nullable=False)
    content_url = Column(String(1024), nullable=True)
    is_free_preview = Column(Boolean, default=False)
    is_mandatory = Column(Boolean, default=True)
    order_index = Column(Integer, default=0)
    reward_currency = Column(String(20), nullable=True)
    reward_amount = Column(Numeric(30, 8), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class NodeMaterial(Base):
    __tablename__ = "node_materials"
    __table_args__ = (
        Index("ix_material_node", "node_id"),
        Index("ix_material_type", "material_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("knowledge_nodes.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    material_type = Column(String(50), nullable=False)
    file_url = Column(String(1024), nullable=False)
    is_downloadable = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Quiz(Base):
    __tablename__ = "node_quizzes"
    __table_args__ = (
        Index("ix_quiz_node", "node_id", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("knowledge_nodes.id"), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    passing_score = Column(Numeric(5, 2), default=70.0)
    max_attempts = Column(Integer, default=3)
    time_limit_minutes = Column(Integer, nullable=True)
    questions = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# ============================================
# 7. الاشتراكات (الأهم في الأداء)
# ============================================
class Enrollment(Base):
    __tablename__ = "academy_enrollments"
    __table_args__ = (
        # 🚀 أسرع استعلام في النظام (جلب اشتراكات طالب معين)
        Index("ix_enrollment_user_course", "user_id", "course_id", unique=True),  # يضمن عدم تكرار الاشتراك
        Index("ix_enrollment_course_status", "course_id", "status"),
        Index("ix_enrollment_user_status", "user_id", "status"),
        Index("ix_enrollment_cohort", "cohort_id"),
        Index("ix_enrollment_payment_status", "payment_status"),
        Index("ix_enrollment_completed", "is_completed"),
        Index("ix_enrollment_updated", "updated_at"),  # للتقارير الزمنية
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("academy_courses.id"), nullable=False, index=True)
    cohort_id = Column(Integer, ForeignKey("academy_cohorts.id"), nullable=True, index=True)
    
    payment_method = Column(String(50), default="WALLET")
    payment_status = Column(String(50), default="PENDING")
    payment_ref = Column(String(100), nullable=True)
    paid_amount = Column(Numeric(10, 2), default=0)
    status = Column(String(50), default="ACTIVE")
    
    progress_percentage = Column(Numeric(5, 2), default=0)
    is_completed = Column(Boolean, default=False)
    last_accessed = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# ============================================
# 8. الجلسات المباشرة والحضور
# ============================================
class LiveSession(Base):
    __tablename__ = "live_sessions"
    __table_args__ = (
        Index("ix_live_node", "node_id"),
        Index("ix_live_instructor", "instructor_id"),
        Index("ix_live_cohort", "cohort_id"),
        Index("ix_live_schedule", "scheduled_start", "scheduled_end"),
        Index("ix_live_active", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("knowledge_nodes.id"), nullable=False, index=True)
    instructor_id = Column(Integer, ForeignKey("academy_instructors.id"), nullable=False, index=True)
    cohort_id = Column(Integer, ForeignKey("academy_cohorts.id"), nullable=True, index=True)
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    scheduled_start = Column(DateTime(timezone=True), nullable=False)
    scheduled_end = Column(DateTime(timezone=True), nullable=False)
    
    session_type = Column(String(50), default="ONLINE")
    location = Column(String(255), nullable=True)
    meeting_url = Column(String(1024), nullable=True)
    recording_url = Column(String(1024), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class LiveAttendance(Base):
    __tablename__ = "live_attendance"
    __table_args__ = (
        Index("ix_attendance_session", "session_id"),
        Index("ix_attendance_user", "user_id"),
        Index("ix_attendance_session_user", "session_id", "user_id", unique=True),  # منع تسجيل الحضور المكرر
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("live_sessions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    left_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# ============================================
# 9. نظام المكافآت والشهادات
# ============================================
class SpiritualCertificate(Base):
    __tablename__ = "spiritual_certificates"
    __table_args__ = (
        Index("ix_cert_user_course", "user_id", "course_id"),
        Index("ix_cert_hash", "certificate_hash", unique=True),
        Index("ix_cert_issued", "issued_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    course_id = Column(Integer, ForeignKey("academy_courses.id"), index=True)
    certificate_hash = Column(String(64), unique=True, index=True)
    grade = Column(Integer, nullable=False)
    ai_training_metadata = Column(JSON, default=dict)
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SovereignBadge(Base):
    __tablename__ = "sovereign_badges"
    __table_args__ = (
        Index("ix_badge_user", "user_id"),
        Index("ix_badge_type", "badge_type"),
        Index("ix_badge_user_type", "user_id", "badge_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    badge_type = Column(String(50), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(String(255))
    xp_reward = Column(Integer, default=100)
    unlocked_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CertificateIssuanceLog(Base):
    __tablename__ = "certificate_issuance_logs"
    __table_args__ = (
        Index("ix_issuance_user", "user_id"),
        Index("ix_issuance_course", "course_id"),
        Index("ix_issuance_hash", "certificate_hash"),
        Index("ix_issuance_issued", "issued_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("academy_courses.id"), nullable=False, index=True)
    certificate_hash = Column(String(64), index=True)
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    blockchain_tx_hash = Column(String(100), nullable=True)

# ============================================
# 10. التقارير والتحليلات
# ============================================
class CourseAnalytics(Base):
    __tablename__ = "course_analytics"
    __table_args__ = (
        Index("ix_analytics_course", "course_id", unique=True),
        Index("ix_analytics_revenue", "revenue_generated_mrusdt"),
        Index("ix_analytics_updated", "updated_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("academy_courses.id"), nullable=False, index=True)
    total_enrollments = Column(Integer, default=0)
    total_completions = Column(Integer, default=0)
    average_grade = Column(Numeric(5, 2), default=0)
    average_rating = Column(Numeric(2, 1), default=0)
    revenue_generated_mrusdt = Column(Numeric(30, 8), default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# ============================================
# 11. نظام التكليفات (Tasks) والتسليمات
# ============================================
class AcademyTask(Base):
    __tablename__ = "academy_tasks"
    __table_args__ = (
        Index("ix_task_course", "course_id"),
        Index("ix_task_cohort", "cohort_id"),
        Index("ix_task_deadline", "deadline"),
        Index("ix_task_active", "is_active"),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("academy_courses.id"), nullable=False, index=True)
    cohort_id = Column(Integer, ForeignKey("academy_cohorts.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=True)
    max_score = Column(Numeric(5, 2), default=100.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class TaskSubmission(Base):
    __tablename__ = "task_submissions"
    __table_args__ = (
        # 🚀 استعلامات المدرب (جلب التسليمات المعلقة لكل تكليف)
        Index("ix_submission_task_status", "task_id", "status"),
        Index("ix_submission_user", "user_id"),
        Index("ix_submission_status", "status"),
        Index("ix_submission_grade", "grade"),
    )

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("academy_tasks.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    file_url = Column(String(1024), nullable=True)
    student_notes = Column(Text, nullable=True)
    
    grade = Column(Numeric(5, 2), nullable=True)
    instructor_feedback = Column(Text, nullable=True)
    status = Column(String(50), default="SUBMITTED")
    
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# ============================================
# 12. الذكاء الاصطناعي والتوأم الرقمي
# ============================================
class StudentDigitalTwin(Base):
    __tablename__ = "student_digital_twins"
    __table_args__ = (
        Index("ix_twin_user", "user_id", unique=True),
        Index("ix_twin_style", "learning_style"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    cognitive_map = Column(JSON, default=dict)
    learning_style = Column(String(50), default="VISUAL")
    ai_recommendations = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ClassroomCameraAnalysis(Base):
    __tablename__ = "classroom_camera_analyses"
    __table_args__ = (
        Index("ix_camera_org", "org_entity_id"),
        Index("ix_camera_session", "session_id"),
        Index("ix_camera_device", "camera_device_id"),
        Index("ix_camera_timestamp", "timestamp"),
        Index("ix_camera_attention", "attention_score"),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_entity_id = Column(Integer, ForeignKey("organization_entities.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("live_sessions.id"), nullable=True, index=True)
    camera_device_id = Column(String(255), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    detected_faces_count = Column(Integer, default=0)
    attention_score = Column(Numeric(5, 2), nullable=True)
    emotions_summary = Column(JSON, default=dict)
    active_speaker_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    raw_analysis_log = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# ============================================
# 13. 🚀 النموذج المفقود (الأقساط المالية)
# ============================================
class PaymentInstallment(Base):
    """جدول الأقساط المالية - لدعم نظام التقسيط للمستخدمين"""
    __tablename__ = "payment_installments"
    __table_args__ = (
        Index("ix_installment_user", "user_id"),
        Index("ix_installment_enrollment", "enrollment_id"),
        Index("ix_installment_due_date", "due_date"),
        Index("ix_installment_paid", "is_paid"),
        Index("ix_installment_overdue", "due_date", "is_paid"),  # استعلام المتأخرات
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    enrollment_id = Column(Integer, ForeignKey("academy_enrollments.id"), nullable=False, index=True)
    amount_due = Column(Numeric(30, 8), nullable=False)  # المبلغ المستحق
    currency = Column(String(20), default="MR_USDT")
    due_date = Column(DateTime(timezone=True), nullable=False)
    is_paid = Column(Boolean, default=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    payment_ref = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())