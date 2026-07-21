# app/domains/academy/router.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List, cast
import hashlib
import uuid

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_superuser, get_current_instructor_or_admin, require_subscription
from app.domains.identity.models import User

from app.domains.academy.service import AcademyService
from app.domains.academy.repository import AcademyRepository
from app.domains.academy.models import Course, Enrollment, TaskSubmission
from app.domains.academy.schemas import *

# ============================================================
# 🔥 دوال مساعدة للـ Rate Limiting (مؤقتاً في الذاكرة)
# ============================================================
from collections import defaultdict
from datetime import datetime, timedelta

_rate_limit_store = defaultdict(list)

async def rate_limit(request: Request):
    identifier = request.client.host if request.client else "unknown_ip"
    max_requests = 60
    window_seconds = 60
    now = datetime.utcnow()
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
    return await service.create_tenant(**data.model_dump())

@router.get("/tenants/by-domain", response_model=TenantResponse)
async def get_tenant_by_domain(
    domain: str,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(rate_limit)
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
    return await service.create_org_entity(**data.model_dump())

@router.get("/entities", response_model=list[OrganizationEntityResponse])
async def list_org_entities(
    tenant_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
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
    return await service.create_bootcamp(data.model_dump(), cast(int, current_user.id))

@router.get("/bootcamps", response_model=list[BootcampResponse])
async def list_bootcamps(
    org_entity_id: Optional[int] = Query(None, description="معرف الكيان التنظيمي (اختياري)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
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
    service = AcademyService(db)
    return await service.create_track(data.model_dump())

@router.get("/tracks", response_model=list[TrackResponse])
async def list_tracks(
    org_entity_id: Optional[int] = None,
    bootcamp_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
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
    service = AcademyService(db)
    return await service.create_cohort(data.model_dump())

@router.get("/cohorts", response_model=list[CohortResponse])
async def list_cohorts(
    org_entity_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
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
    return await service.create_course(data.model_dump(), cast(int, current_user.id))

@router.get("/courses", response_model=list[CourseResponse])
async def get_courses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AcademyRepository(db)
    courses = await repo.list_all_courses(skip=skip, limit=limit)
    return courses

@router.get("/courses/{course_id}", response_model=CourseResponse)
async def get_course_by_id(
    course_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(rate_limit)
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
    current_user: User = Depends(get_current_instructor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    course = await service.update_course(course_id, data.model_dump(exclude_unset=True), cast(int, current_user.id))
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
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.get_store_courses(cast(int, current_user.id), skip=skip, limit=limit)

@router.get("/student/my-enrollments", response_model=list[EnrollmentResponse])
async def get_my_enrollments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.get_user_enrollments(cast(int, current_user.id), skip=skip, limit=limit)

@router.post("/store/courses/{course_id}/enroll", response_model=EnrollmentResponse)
async def enroll_in_course(
    course_id: int,
    data: EnrollmentCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.enroll_in_course(
        user_id=cast(int, current_user.id),
        course_id=course_id,
        cohort_id=data.cohort_id,
        payment_method=data.payment_method,
        payment_ref=data.payment_ref or ""
    )

@router.post("/enroll", response_model=EnrollmentResponse)
async def enroll_in_course_simple(
    course_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = AcademyService(db)
    return await service.enroll_in_course(
        user_id=cast(int, current_user.id),
        course_id=course_id,
        cohort_id=None,
        payment_method="FREE",  # ✅ تم التصحيح من None إلى "FREE"
        payment_ref=""
    )

@router.put("/student/enrollments/{course_id}/progress", response_model=EnrollmentResponse)
async def update_enrollment_progress(
    course_id: int,
    data: ProgressUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    enrollment = await service.update_progress(cast(int, current_user.id), course_id, data.progress_percentage)
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
    current_user: User = Depends(get_current_instructor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.create_course_unit(course_id, data.model_dump())

@router.get("/courses/{course_id}/units", response_model=list[CourseUnitResponse])
async def get_course_units(
    course_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.get_course_units(course_id, skip=skip, limit=limit)

@router.put("/units/{unit_id}", response_model=CourseUnitResponse)
async def update_unit(
    unit_id: int,
    data: UpdateTitleSchema,
    current_user: User = Depends(get_current_instructor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    unit = await service.update_course_unit(unit_id, data.title)
    if not unit:
        raise HTTPException(status_code=404, detail="الوحدة غير موجودة")
    return unit

@router.delete("/units/{unit_id}", status_code=204)
async def delete_unit(
    unit_id: int,
    current_user: User = Depends(get_current_instructor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    success = await service.delete_course_unit(unit_id)
    if not success:
        raise HTTPException(status_code=404, detail="الوحدة غير موجودة")
    return None

@router.post("/nodes", response_model=KnowledgeNodeResponse, status_code=201)
async def create_node(
    data: KnowledgeNodeCreate,
    current_user: User = Depends(get_current_instructor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.create_knowledge_node(data.model_dump())

@router.get("/courses/{course_id}/nodes", response_model=list[KnowledgeNodeResponse])
async def get_course_nodes(
    course_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.get_course_nodes(course_id, skip=skip, limit=limit)

@router.put("/nodes/{node_id}", response_model=KnowledgeNodeResponse)
async def update_node(
    node_id: int,
    data: UpdateTitleSchema,
    current_user: User = Depends(get_current_instructor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    node = await service.update_knowledge_node(node_id, data.title)
    if not node:
        raise HTTPException(status_code=404, detail="الدرس غير موجود")
    return node

@router.delete("/nodes/{node_id}", status_code=204)
async def delete_node(
    node_id: int,
    current_user: User = Depends(get_current_instructor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    success = await service.delete_knowledge_node(node_id)
    if not success:
        raise HTTPException(status_code=404, detail="الدرس غير موجود")
    return None

@router.post("/nodes/{node_id}/live", response_model=LiveSessionResponse, status_code=201)
async def create_node_live_session(
    node_id: int,
    data: LiveSessionCreate,
    current_user: User = Depends(get_current_instructor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.create_live_session(node_id, data.model_dump())

# ============================================================
# Node Materials & Quizzes
# ============================================================
@router.post("/nodes/{node_id}/materials", response_model=NodeMaterialResponse, status_code=201)
async def create_material(
    node_id: int,
    data: NodeMaterialCreate,
    current_user: User = Depends(get_current_instructor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.create_node_material(node_id, data.model_dump())

@router.get("/nodes/{node_id}/materials", response_model=list[NodeMaterialResponse])
async def get_materials(
    node_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.get_node_materials(node_id)

@router.post("/nodes/{node_id}/quiz", response_model=QuizResponse, status_code=201)
async def create_node_quiz(
    node_id: int,
    data: QuizCreate,
    current_user: User = Depends(get_current_instructor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.create_quiz(node_id, data.model_dump())

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
    service = AcademyService(db)
    file_content = await file.read()
    file_url = await service.upload_course_thumbnail(
        course_id=course_id,
        file_content=file_content,
        filename=file.filename or "uploaded_file",
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
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.get_course_tasks(course_id, skip=skip, limit=limit)

@router.post("/tasks/{task_id}/submit", response_model=TaskSubmissionResponse)
async def submit_task(
    task_id: int,
    data: TaskSubmissionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.submit_task(cast(int, current_user.id), task_id, data.model_dump())

# ============================================================
# Instructor Grading (مع تحقق من صلاحيات المدرب)
# ============================================================
@router.get("/instructor/tasks/{task_id}/submissions", response_model=list[TaskSubmissionResponse])
async def get_task_submissions(
    task_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_instructor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.get_task_submissions(task_id, skip=skip, limit=limit)

@router.put("/instructor/submissions/{submission_id}/grade", response_model=TaskSubmissionResponse)
async def grade_student_submission(
    submission_id: int,
    data: TaskGradeUpdate,
    current_user: User = Depends(get_current_instructor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    submission = await service.grade_submission(
        submission_id,
        float(data.grade),
        data.instructor_feedback or "",
        data.status
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
    service = AcademyService(db)
    return await service.get_my_submissions(cast(int, current_user.id), skip=skip, limit=limit)

# ============================================================
# Instructor Statistics (لوحة تحكم المدرب) ✅ الجوهرة الجديدة
# ============================================================
@router.get("/instructor/stats")
async def get_instructor_stats(
    current_user: User = Depends(get_current_instructor_or_admin),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.get_instructor_stats(cast(int, current_user.id))

# ============================================================
# Management Reports & Analytics
# ============================================================
@router.get("/reports/financial", response_model=FinancialSummaryResponse)
async def get_financial_summary(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    return await service.get_financial_summary()

# ============================================================
# Gamification & Leaderboard
# ============================================================
@router.get("/leaderboard")
async def get_leaderboard(
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(rate_limit)
):
    service = AcademyService(db)
    return await service.get_leaderboard(limit)

# ============================================================
# AI Camera Analytics & Digital Twin
# ============================================================
@router.get("/digital-twin/me", response_model=StudentDigitalTwinResponse)
async def get_my_digital_twin(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    service = AcademyService(db)
    twin = await service.get_or_create_digital_twin(cast(int, current_user.id))
    return twin