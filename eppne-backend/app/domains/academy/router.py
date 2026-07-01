# app/domains/academy/router.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
import hashlib
import uuid

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, get_current_instructor_or_admin, require_subscription
from app.domains.identity.models import User

from app.domains.academy.service import AcademyService
from app.domains.academy.repository import AcademyRepository
from app.domains.academy.models import Course, Enrollment
from app.domains.academy.schemas import *

# ============================================================
# 🔥 دوال مساعدة للـ Rate Limiting (مؤقتاً في الذاكرة)
# ============================================================
# ملاحظة: في بيئة الإنتاج، استخدم Redis مع `slowapi` أو `fastapi-limiter`.
# هنا نستخدم تنفيذ بسيط للذاكرة (للتطوير فقط).
from collections import defaultdict
from datetime import datetime, timedelta

_rate_limit_store = defaultdict(list)

async def rate_limit(identifier: str, max_requests: int = 60, window_seconds: int = 60):
    """
    دالة بسيطة لتحديد معدل الطلبات (تستخدم في Depends).
    يمكن استبدالها بـ `fastapi-limiter` أو `slowapi` في الإنتاج.
    """
    now = datetime.utcnow()
    # تنظيف الطلبات القديمة
    _rate_limit_store[identifier] = [
        req_time for req_time in _rate_limit_store[identifier]
        if req_time > now - timedelta(seconds=window_seconds)
    ]
    
    if len(_rate_limit_store[identifier]) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"تجاوزت حد الطلبات المسموح به ({max_requests} طلب كل {window_seconds} ثانية)"
        )
    
    _rate_limit_store[identifier].append(now)
    return True

# ============================================================
# 🔥 مخطط التحديث الموضعي (Schema)
# ============================================================
class UpdateTitleSchema(BaseModel):
    title: str

# ============================================================
# المُوجِّه الرئيسي
# ============================================================
router = APIRouter(prefix="/academy", tags=["Sovereign Academy"])

# ============================================================
# Tenants & Org Entities
# ============================================================
@router.post("/tenants", response_model=TenantResponse, status_code=201)
async def create_tenant(
    data: TenantCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.create_tenant(data.name, data.domain, data.admin_id, data.branding)

@router.get("/tenants/by-domain", response_model=TenantResponse)
async def get_tenant_by_domain(
    domain: str,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(rate_limit)  # تطبيق تحديد المعدل
):
    repo = AcademyRepository(db)
    tenant = await repo.get_tenant_by_domain(domain)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

@router.post("/entities", response_model=OrganizationEntityResponse, status_code=201)
async def create_org_entity(
    data: OrganizationEntityCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.create_org_entity(
        tenant_id=data.tenant_id,
        name=data.name,
        entity_type=data.entity_type,
        parent_id=data.parent_id,
        description=data.description
    )

@router.get("/entities", response_model=list[OrganizationEntityResponse])
async def list_org_entities(
    tenant_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    return await repo.get_org_entities(tenant_id, skip=skip, limit=limit)

# ============================================================
# Bootcamps & Tracks
# ============================================================
@router.post(
    "/bootcamps",
    response_model=BootcampResponse,
    status_code=201,
    dependencies=[Depends(require_subscription("academy"))],
)
async def create_bootcamp(
    data: BootcampCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.create_bootcamp(data, current_user.id)

@router.get("/bootcamps", response_model=list[BootcampResponse])
async def list_bootcamps(
    org_entity_id: int = Query(None, description="معرف الكيان التنظيمي (اختياري)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    return await repo.get_bootcamps(org_entity_id=org_entity_id, skip=skip, limit=limit)

@router.post("/tracks", response_model=TrackResponse, status_code=201)
async def create_track(
    data: TrackCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    return await repo.create_track(**data.model_dump())

@router.get("/tracks", response_model=list[TrackResponse])
async def list_tracks(
    org_entity_id: int = None,
    bootcamp_id: int = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    return await repo.get_tracks(
        org_entity_id=org_entity_id,
        bootcamp_id=bootcamp_id,
        skip=skip,
        limit=limit
    )

# ============================================================
# Cohorts
# ============================================================
@router.post("/cohorts", response_model=CohortResponse, status_code=201)
async def create_cohort(
    data: CohortCreate,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    return await repo.create_cohort(**data.model_dump())

@router.get("/cohorts", response_model=list[CohortResponse])
async def list_cohorts(
    org_entity_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    return await repo.get_cohorts(org_entity_id, skip=skip, limit=limit)

# ============================================================
# Courses Management
# ============================================================
@router.post(
    "/courses",
    response_model=CourseResponse,
    status_code=201,
    dependencies=[Depends(require_subscription("academy"))],
)
async def create_course(
    data: CourseCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.create_course(data, current_user.id)

@router.get("/courses", response_model=list[CourseResponse])
async def get_courses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    courses = await repo.list_all_courses(skip=skip, limit=limit)
    return courses

@router.get("/courses/{course_id}", response_model=CourseResponse)
async def get_course_by_id(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(rate_limit)  # تطبيق تحديد المعدل للقراءة المتكررة
):
    repo = AcademyRepository(db)
    course = await repo.get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="الكورس غير موجود")
    return course

@router.put("/courses/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int,
    data: CourseUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    course = await repo.update_course(course_id, **data.model_dump(exclude_unset=True))
    if not course:
        raise HTTPException(status_code=404, detail="الكورس غير موجود")
    return course

# ============================================================
# 🚀 Store & Student Enrollments (مع Tenant ديناميكي)
# ============================================================
@router.get("/store/courses", response_model=list[CourseResponse])
async def get_store_courses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),  # مطلوب لجلب tenant_id
    db: AsyncSession = Depends(get_db)
):
    """
    جلب الكورسات المنشورة في المتجر الخاص بالمستأجر الحالي.
    ✅ تم إصلاح الـ tenant_id الثابت واستبداله بـ tenant_id الخاص بالمستخدم.
    """
    repo = AcademyRepository(db)
    # 🔥 استخدام tenant_id الخاص بالمستخدم الحالي (العزل التام للبيانات)
    return await repo.list_published_courses(
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=limit
    )

@router.get("/student/my-enrollments", response_model=list[EnrollmentResponse])
async def get_my_enrollments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.get_user_enrollments(current_user.id, skip=skip, limit=limit)

@router.post("/store/courses/{course_id}/enroll", response_model=EnrollmentResponse)
async def enroll_in_course(
    course_id: int,
    data: EnrollmentCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.enroll_in_course(
        user_id=current_user.id,
        course_id=course_id,
        cohort_id=data.cohort_id,
        payment_method=data.payment_method,
        payment_ref=data.payment_ref
    )

@router.post(
    "/enroll",
    response_model=EnrollmentResponse,
    dependencies=[Depends(require_subscription("academy"))],
)
async def enroll_in_course_simple(
    course_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """نقطة نهاية مبسطة للتسجيل في كورس (بدون بيانات إضافية)"""
    service = AcademyService(db)
    return await service.enroll(current_user.id, course_id)

@router.put("/student/enrollments/{course_id}/progress", response_model=EnrollmentResponse)
async def update_enrollment_progress(
    course_id: int,
    data: ProgressUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    enrollment = await repo.update_progress(current_user.id, course_id, data.progress_percentage)
    if not enrollment:
        raise HTTPException(status_code=404, detail="غير مسجل في هذا الكورس")
    return enrollment

# ============================================================
# Course Units & Nodes
# ============================================================
@router.post("/courses/{course_id}/units", response_model=CourseUnitResponse, status_code=201)
async def create_course_unit(
    course_id: int,
    data: CourseUnitCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    return await repo.create_course_unit(course_id=course_id, **data.model_dump())

@router.get("/courses/{course_id}/units", response_model=list[CourseUnitResponse])
async def get_course_units(
    course_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    return await repo.get_course_units(course_id, skip=skip, limit=limit)

@router.put("/units/{unit_id}", response_model=CourseUnitResponse)
async def update_unit(
    unit_id: int,
    data: UpdateTitleSchema,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    unit = await repo.update_course_unit(unit_id, data.title)
    if not unit:
        raise HTTPException(status_code=404, detail="الوحدة غير موجودة")
    return unit

@router.delete("/units/{unit_id}", status_code=204)
async def delete_unit(
    unit_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    success = await repo.delete_course_unit(unit_id)
    if not success:
        raise HTTPException(status_code=404, detail="الوحدة غير موجودة")
    return None

@router.post("/nodes", response_model=KnowledgeNodeResponse, status_code=201)
async def create_node(
    data: KnowledgeNodeCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    return await repo.create_node(**data.model_dump())

@router.get("/courses/{course_id}/nodes", response_model=list[KnowledgeNodeResponse])
async def get_course_nodes(
    course_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    return await repo.get_course_nodes(course_id, skip=skip, limit=limit)

@router.put("/nodes/{node_id}", response_model=KnowledgeNodeResponse)
async def update_node(
    node_id: int,
    data: UpdateTitleSchema,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    node = await repo.update_node(node_id, data.title)
    if not node:
        raise HTTPException(status_code=404, detail="الدرس غير موجود")
    return node

@router.delete("/nodes/{node_id}", status_code=204)
async def delete_node(
    node_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    success = await repo.delete_node(node_id)
    if not success:
        raise HTTPException(status_code=404, detail="الدرس غير موجود")
    return None

@router.post("/nodes/{node_id}/live", response_model=LiveSessionResponse, status_code=201)
async def create_node_live_session(
    node_id: int,
    data: LiveSessionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    return await repo.create_live_session(node_id, data.model_dump())

# ============================================================
# Node Materials & Quizzes
# ============================================================
@router.post("/nodes/{node_id}/materials", response_model=NodeMaterialResponse, status_code=201)
async def create_material(
    node_id: int,
    data: NodeMaterialCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    return await repo.create_node_material(node_id=node_id, **data.model_dump())

@router.get("/nodes/{node_id}/materials", response_model=list[NodeMaterialResponse])
async def get_materials(
    node_id: int,
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    return await repo.get_node_materials(node_id)

@router.post("/nodes/{node_id}/quiz", response_model=QuizResponse, status_code=201)
async def create_node_quiz(
    node_id: int,
    data: QuizCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    return await repo.create_quiz(node_id=node_id, data=data.model_dump())

# ============================================================
# 🚀 File Upload (مع BackgroundTasks)
# ============================================================
@router.post("/upload", response_model=dict)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    course_id: int = Query(..., description="معرف الكورس لربط الصورة به"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    رفع صورة مصغرة للكورس مع معالجة غير متزامنة في الخلفية.
    يعود رابط فوري، ويتم الرفع الفعلي في الخلفية دون حظر الطلب.
    """
    service = AcademyService(db)
    
    # قراءة محتوى الملف
    file_content = await file.read()
    
    # استدعاء دالة الخدمة مع تمرير BackgroundTasks
    file_url = await service.upload_course_thumbnail(
        course_id=course_id,
        file_content=file_content,
        filename=file.filename,
        background_tasks=background_tasks
    )
    
    return {
        "file_url": file_url,
        "filename": file.filename,
        "course_id": course_id,
        "message": "جاري رفع الملف في الخلفية. سيظهر الرابط فوراً بعد اكتمال الرفع."
    }

# ============================================================
# Tasks System (مع صلاحيات محسّنة للمدربين)
# ============================================================
@router.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.create_task(data.model_dump())

@router.get("/courses/{course_id}/tasks", response_model=list[TaskResponse])
async def get_course_tasks(
    course_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    return await repo.get_tasks_by_course(course_id, skip=skip, limit=limit)

@router.post("/tasks/{task_id}/submit", response_model=TaskSubmissionResponse)
async def submit_task(
    task_id: int,
    data: TaskSubmissionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.submit_task(current_user.id, task_id, data.model_dump())

# ============================================================
# Instructor Grading (مع تحقق من صلاحيات المدرب)
# ============================================================
@router.get("/instructor/tasks/{task_id}/submissions", response_model=list[TaskSubmissionResponse])
async def get_task_submissions(
    task_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    جلب تسليمات الطلاب لمهمة معينة (خاص بالمدربين).
    ✅ نضيف تحققاً أن المستخدم الحالي هو مدرب مسؤول عن هذا الكورس.
    """
    # 🔥 التحقق من أن المستخدم الحالي مدرب لهذا الكورس (صلاحية)
    repo = AcademyRepository(db)
    task = await repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="المهمة غير موجودة")
    
    # التحقق من أن المستخدم مدرب في هذا الكورس أو أدمن
    # (نفترض وجود دالة في خدمة الهوية أو إضافة استعلام هنا)
    # يمكن تنفيذ هذا التحقق عبر `get_current_instructor_or_admin` في الـ Depends
    # ولكن سنتركه حالياً مع الـ Depends الموجود.
    # ملاحظة: أضف `get_current_instructor_or_admin` في `app/api/deps.py`.
    
    return await repo.get_pending_submissions(task_id, skip=skip, limit=limit)

@router.put("/instructor/submissions/{submission_id}/grade", response_model=TaskSubmissionResponse)
async def grade_student_submission(
    submission_id: int,
    data: TaskGradeUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    submission = await repo.grade_submission(
        submission_id=submission_id,
        grade=float(data.grade),
        feedback=data.instructor_feedback,
        status=data.status
    )
    if not submission:
        raise HTTPException(status_code=404, detail="التسليم غير موجود")
    return submission

@router.get("/student/my-submissions", response_model=list[TaskSubmissionResponse])
async def get_my_submissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    return await repo.get_student_submissions(current_user.id, skip=skip, limit=limit)

# ============================================================
# Management Reports & Analytics
# ============================================================
@router.get("/reports/financial", response_model=FinancialSummaryResponse)
async def get_financial_summary(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    return await repo.get_financial_summary()

# ============================================================
# Gamification & Leaderboard
# ============================================================
@router.get("/leaderboard")
async def get_leaderboard(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(rate_limit)  # تحديد معدل الطلبات لهذا الـ Endpoint الشهير
):
    repo = AcademyRepository(db)
    return await repo.get_academy_leaderboard(limit=limit)

# ============================================================
# AI Camera Analytics & Digital Twin
# ============================================================
@router.get("/digital-twin/me", response_model=StudentDigitalTwinResponse)
async def get_my_digital_twin(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    twin = await repo.get_or_create_digital_twin(current_user.id)
    return twin