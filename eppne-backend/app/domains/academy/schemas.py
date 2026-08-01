# app/domains/academy/schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal

# ==========================================
# Tenants
# ==========================================
class TenantBase(BaseModel):
    name: str
    domain: str
    branding: Optional[Dict[str, Any]] = {}

class TenantCreate(TenantBase):
    admin_id: int

class TenantResponse(TenantBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# Organization Entities (Replaces Institutions)
# ==========================================
class OrganizationEntityBase(BaseModel):
    name: str
    entity_type: str  # MINISTRY, DIRECTORATE, UNIVERSITY, SCHOOL, NURSERY, COLLEGE, DEPT, COMPANY
    description: Optional[str] = None

class OrganizationEntityCreate(OrganizationEntityBase):
    tenant_id: int
    parent_id: Optional[int] = None

class OrganizationEntityResponse(OrganizationEntityBase):
    id: int
    tenant_id: int
    parent_id: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# Instructors
# ==========================================
class InstructorCreate(BaseModel):
    org_entity_id: int
    bio: Optional[str] = None
    expertise_areas: Optional[List[str]] = []
    revenue_share_percentage: Decimal = Decimal('70.0')

class InstructorResponse(BaseModel):
    id: int
    user_id: int
    org_entity_id: int
    bio: Optional[str]
    expertise_areas: List[str]
    revenue_share_percentage: Decimal
    is_approved: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# Cohorts
# ==========================================
class CohortBase(BaseModel):
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    max_capacity: Optional[int] = None

class CohortCreate(CohortBase):
    org_entity_id: int

class CohortResponse(CohortBase):
    id: int
    org_entity_id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# Bootcamps, Tracks, Courses
# ==========================================
class BootcampCreate(BaseModel):
    org_entity_id: int
    title: str
    description: Optional[str] = None
    duration_days: int = 100
    target_rank: Optional[str] = None

class BootcampResponse(BootcampCreate):
    id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TrackCreate(BaseModel):
    bootcamp_id: Optional[int] = None
    org_entity_id: int
    title: str
    description: Optional[str] = None

class TrackResponse(TrackCreate):
    id: int
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CourseCreate(BaseModel):
    tenant_id: int
    org_entity_id: int
    track_id: Optional[int] = None
    bootcamp_id: Optional[int] = None
    instructor_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    price_mrusdt: Decimal = Decimal('0.0')
    currency: str = "MR_USDT"
    level: str = "BEGINNER"
    is_free: bool = False

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    price_mrusdt: Optional[Decimal] = None
    is_free: Optional[bool] = None
    is_published: Optional[bool] = None
    is_active: Optional[bool] = None

class CourseResponse(CourseCreate):
    id: int
    is_published: bool
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# Units, Nodes, Materials
# ==========================================
class CourseUnitCreate(BaseModel):
    title: str
    description: Optional[str] = None
    order_index: int = 0

class CourseUnitResponse(CourseUnitCreate):
    id: int
    course_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class KnowledgeNodeCreate(BaseModel):
    course_id: int
    unit_id: Optional[int] = None
    title: str
    content_type: str  # VIDEO, ARTICLE, QUIZ, LIVE, SIMULATION
    content_url: Optional[str] = None
    is_free_preview: bool = False
    is_mandatory: bool = True
    order_index: int = 0
    reward_currency: Optional[str] = None
    reward_amount: Decimal = Decimal('0.0')

class KnowledgeNodeResponse(KnowledgeNodeCreate):
    id: int
    course_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class NodeMaterialCreate(BaseModel):
    title: str
    material_type: str  # PDF, IMAGE, LINK, DOC
    file_url: str
    is_downloadable: bool = False

class NodeMaterialResponse(NodeMaterialCreate):
    id: int
    node_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# Quizzes
# ==========================================
class QuizQuestion(BaseModel):
    id: int
    type: str  # MCQ, TRUE_FALSE, SHORT_ANSWER
    text: str
    options: Optional[List[str]] = None
    correct_answer: str
    points: int = 1

class QuizCreate(BaseModel):
    title: str
    passing_score: Decimal = Decimal('70.0')
    max_attempts: int = 3
    time_limit_minutes: Optional[int] = None
    questions: List[QuizQuestion]

class QuizResponse(QuizCreate):
    id: int
    node_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class QuizSubmit(BaseModel):
    answers: Dict[int, str]  # {question_id: answer_text}

class QuizResult(BaseModel):
    score: float
    passed: bool
    correct_answers: int
    total_questions: int
    certificate_issued: bool

# ==========================================
# Enrollment & Progress (مع tenant_id)
# ==========================================
class EnrollmentCreate(BaseModel):
    cohort_id: Optional[int] = None
    payment_method: str = "WALLET"
    payment_ref: Optional[str] = None
    affiliate_code: Optional[str] = None

class EnrollmentResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    tenant_id: int
    cohort_id: Optional[int]
    payment_method: str
    payment_status: str
    status: str
    progress_percentage: float
    is_completed: bool
    last_accessed: Optional[datetime]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ProgressUpdate(BaseModel):
    progress_percentage: float = Field(..., ge=0, le=100)

# ==========================================
# Certificates & Badges
# ==========================================
class CertificateResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    certificate_hash: str
    grade: int
    issued_at: datetime
    model_config = ConfigDict(from_attributes=True)

class BadgeResponse(BaseModel):
    id: int
    user_id: int
    badge_type: str
    title: str
    description: Optional[str]
    xp_reward: int
    unlocked_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# Live Sessions & Attendance
# ==========================================
class LiveSessionCreate(BaseModel):
    node_id: int
    instructor_id: int
    cohort_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    scheduled_start: datetime
    scheduled_end: datetime
    session_type: str = "ONLINE"
    location: Optional[str] = None
    meeting_url: Optional[str] = None

class LiveSessionResponse(LiveSessionCreate):
    id: int
    recording_url: Optional[str]
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# AI & Analytics
# ==========================================
class StudentDigitalTwinResponse(BaseModel):
    id: int
    user_id: int
    cognitive_map: Dict[str, Any]
    learning_style: str
    ai_recommendations: List[Any]
    model_config = ConfigDict(from_attributes=True)

class ClassroomCameraAnalysisCreate(BaseModel):
    org_entity_id: int
    session_id: Optional[int] = None
    camera_device_id: str
    detected_faces_count: int
    attention_score: Optional[float] = None
    emotions_summary: Optional[Dict[str, float]] = None
    active_speaker_id: Optional[int] = None
    raw_analysis_log: Optional[Dict[str, Any]] = None

class ClassroomCameraAnalysisResponse(ClassroomCameraAnalysisCreate):
    id: int
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

class AIRecommendationResponse(BaseModel):
    user_id: int
    recommended_course_ids: List[int]
    suggested_study_plan: Dict[str, Any]

class CourseAnalyticsResponse(BaseModel):
    course_id: int
    tenant_id: int
    total_enrollments: int
    total_completions: int
    average_grade: float
    average_rating: float
    revenue_generated_mrusdt: float
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# Tasks & Submissions
# ==========================================
class TaskCreate(BaseModel):
    course_id: int
    cohort_id: Optional[int] = None
    title: str
    description: str
    deadline: Optional[datetime] = None
    max_score: Decimal = Decimal('100.0')

class TaskResponse(TaskCreate):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TaskSubmissionCreate(BaseModel):
    file_url: Optional[str] = None
    student_notes: Optional[str] = None

class TaskSubmissionResponse(TaskSubmissionCreate):
    id: int
    task_id: int
    user_id: int
    grade: Optional[Decimal] = None
    instructor_feedback: Optional[str] = None
    status: str
    submitted_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TaskGradeUpdate(BaseModel):
    grade: Decimal
    instructor_feedback: str
    status: str = "GRADED"

# ==========================================
# Financial Summary
# ==========================================
class FinancialSummaryResponse(BaseModel):
    total_paid: float = Field(description="إجمالي المدفوعات المحصلة")
    total_overdue: float = Field(description="إجمالي الأقساط المتأخرة غير المسددة")
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# Payment Installments (مع tenant_id)
# ==========================================
class PaymentInstallmentCreate(BaseModel):
    user_id: int
    enrollment_id: int
    amount_due: Decimal
    currency: str = "MR_USDT"
    due_date: datetime
    payment_ref: Optional[str] = None

class PaymentInstallmentResponse(PaymentInstallmentCreate):
    id: int
    tenant_id: int
    is_paid: bool
    paid_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)