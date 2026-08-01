# app/domains/academy/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, cast
import json
import hashlib

from app.domains.academy.models import (
    AcademyTenant, OrganizationEntity, Instructor, Bootcamp, Track, Course,
    CourseUnit, KnowledgeNode, NodeMaterial, Quiz, Enrollment, SpiritualCertificate,
    SovereignBadge, LiveSession, LiveAttendance, StudentDigitalTwin, ClassroomCameraAnalysis,
    CertificateIssuanceLog, CourseAnalytics, AcademyTask, TaskSubmission, AcademyCohort,
    PaymentInstallment
)
from app.domains.academy.schemas import (
    CourseResponse,
    CourseUnitResponse,
    KnowledgeNodeResponse,
    EnrollmentResponse,
    TaskResponse,
    TaskSubmissionResponse,
)
from app.core.errors import NotFoundError
from app.core.pagination import PaginatedResponse

try:
    from app.core.cache import redis_client
except ImportError:
    redis_client = None
    print("Warning: Redis not configured. Running without caching.")


class AcademyRepository:
    def __init__(self, db: AsyncSession, cache_ttl: int = 300):
        self.db = db
        self.cache_ttl = cache_ttl

    # ============================================================
    # 🔥 دوال التخزين المؤقت الذكية (Cache Helpers)
    # ============================================================
    def _get_cache_key(self, prefix: str, *args, **kwargs) -> str:
        key_parts = [prefix]
        key_parts.extend([str(a) for a in args])
        key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
        raw = ":".join(key_parts)
        return f"repo:{prefix}:{hashlib.md5(raw.encode()).hexdigest()}"

    async def _get_cache(self, key: str) -> Optional[Any]:
        if not redis_client:
            return None
        try:
            data = await redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    async def _set_cache(self, key: str, value: Any, ttl: Optional[int] = None):
        if not redis_client:
            return
        try:
            ttl = ttl or self.cache_ttl
            await redis_client.setex(key, ttl, json.dumps(value, default=str))
        except Exception:
            pass

    async def _invalidate_cache(self, pattern: Optional[str] = None):
        if not redis_client or not pattern:
            return
        try:
            client = await redis_client.get_client()
            keys = []
            async for key in client.scan_iter(match=f"repo:*{pattern}*"):
                keys.append(key)
            if keys:
                await client.delete(*keys)
        except Exception:
            pass

    async def _paginate_query(self, query, skip: int = 0, limit: int = 100):
        safe_limit = min(limit, 1000)
        return query.offset(skip).limit(safe_limit)

    # ============================================================
    # 1. Tenants & Org Entities
    # ============================================================
    async def create_tenant(self, **kwargs) -> AcademyTenant:
        tenant = AcademyTenant(**kwargs)
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def get_tenant_by_domain(self, domain: str) -> Optional[AcademyTenant]:
        cache_key = self._get_cache_key("tenant_domain", domain)
        cached = await self._get_cache(cache_key)
        if cached:
            return AcademyTenant(**cached)
        result = await self.db.execute(
            select(AcademyTenant).where(AcademyTenant.domain == domain)
        )
        tenant = result.scalar_one_or_none()
        if tenant:
            await self._set_cache(cache_key, {c: getattr(tenant, c) for c in tenant.__table__.columns.keys()})
        return tenant

    async def get_org_entity(self, org_entity_id: int) -> Optional[OrganizationEntity]:
        result = await self.db.execute(
            select(OrganizationEntity).where(OrganizationEntity.id == org_entity_id)
        )
        return result.scalar_one_or_none()

    async def create_org_entity(self, **kwargs) -> OrganizationEntity:
        entity = OrganizationEntity(**kwargs)
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity

    async def get_org_entities(
        self, tenant_id: int, skip: int = 0, limit: int = 100
    ) -> List[OrganizationEntity]:
        query = select(OrganizationEntity).where(OrganizationEntity.tenant_id == tenant_id)
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ============================================================
    # 2. Instructors
    # ============================================================
    async def create_instructor(self, **kwargs) -> Instructor:
        instructor = Instructor(**kwargs)
        self.db.add(instructor)
        await self.db.commit()
        await self.db.refresh(instructor)
        return instructor

    async def get_instructor(self, instructor_id: int, tenant_id: int) -> Optional[Instructor]:
        result = await self.db.execute(
            select(Instructor).where(
                and_(Instructor.id == instructor_id, Instructor.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()

    # ============================================================
    # 3. Bootcamps & Tracks
    # ============================================================
    async def create_bootcamp(self, **kwargs) -> Bootcamp:
        bootcamp = Bootcamp(**kwargs)
        self.db.add(bootcamp)
        await self.db.commit()
        await self.db.refresh(bootcamp)
        return bootcamp

    async def get_bootcamps(
        self, org_entity_id: Optional[int] = None, skip: int = 0, limit: int = 100
    ) -> List[Bootcamp]:
        query = select(Bootcamp)
        if org_entity_id is not None:
            query = query.where(Bootcamp.org_entity_id == org_entity_id)
        query = query.order_by(Bootcamp.created_at.desc())
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_track(self, **kwargs) -> Track:
        track = Track(**kwargs)
        self.db.add(track)
        await self.db.commit()
        await self.db.refresh(track)
        return track

    async def get_tracks(
        self,
        org_entity_id: Optional[int] = None,
        bootcamp_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Track]:
        query = select(Track)
        if bootcamp_id is not None:
            query = query.where(Track.bootcamp_id == bootcamp_id)
        elif org_entity_id is not None:
            query = query.where(Track.org_entity_id == org_entity_id)
        else:
            return []
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ============================================================
    # 4. Cohorts
    # ============================================================
    async def create_cohort(self, **kwargs) -> AcademyCohort:
        cohort = AcademyCohort(**kwargs)
        self.db.add(cohort)
        await self.db.commit()
        await self.db.refresh(cohort)
        return cohort

    async def get_cohorts(
        self, org_entity_id: int, skip: int = 0, limit: int = 100
    ) -> List[AcademyCohort]:
        query = select(AcademyCohort).where(AcademyCohort.org_entity_id == org_entity_id)
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ============================================================
    # 5. Courses
    # ============================================================
    async def create_course(self, **kwargs) -> Course:
        course = Course(**kwargs)
        self.db.add(course)
        await self.db.commit()
        await self.db.refresh(course)
        await self._invalidate_cache("courses")
        return course

    async def get_course(self, course_id: int, tenant_id: int) -> Optional[Course]:
        cache_key = self._get_cache_key("course", course_id, tenant_id)
        cached = await self._get_cache(cache_key)
        if cached:
            return Course(**cached)
        result = await self.db.execute(
            select(Course).where(
                and_(Course.id == course_id, Course.tenant_id == tenant_id)
            )
        )
        course = result.scalar_one_or_none()
        if course:
            await self._set_cache(cache_key, {c: getattr(course, c) for c in course.__table__.columns.keys()}, ttl=600)
        return course

    async def update_course(self, course_id: int, tenant_id: int, **kwargs) -> Course:
        course = await self.get_course(course_id, tenant_id)
        if not course:
            raise NotFoundError("Course not found")
        for key, value in kwargs.items():
            setattr(course, key, value)
        await self.db.commit()
        await self.db.refresh(course)
        await self._invalidate_cache(f"course_{course_id}_{tenant_id}")
        await self._invalidate_cache("courses")
        await self._invalidate_cache("published_courses")
        return course

    async def list_published_courses(
        self, tenant_id: int, skip: int = 0, limit: int = 100
    ) -> PaginatedResponse[CourseResponse]:
        cache_key = self._get_cache_key("published_courses", tenant_id, skip, limit)
        cached = await self._get_cache(cache_key)
        if cached:
            items = [CourseResponse(**item) for item in cached]
            return PaginatedResponse(data=items, total=len(items), skip=skip, limit=limit)
        query = (
            select(Course)
            .where(
                and_(
                    Course.tenant_id == tenant_id,
                    Course.is_published == True,
                    Course.is_active == True
                )
            )
            .order_by(Course.created_at.desc())
        )
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        courses = list(result.scalars().all())
        if courses:
            await self._set_cache(
                cache_key,
                [CourseResponse.model_validate(crs).model_dump() for crs in courses],
                ttl=120
            )
        items = [CourseResponse.model_validate(crs) for crs in courses]
        return PaginatedResponse(data=items, total=total, skip=skip, limit=limit)

    async def list_all_courses(self, tenant_id: int, skip: int = 0, limit: int = 100) -> PaginatedResponse[CourseResponse]:
        query = select(Course).where(Course.tenant_id == tenant_id).order_by(Course.created_at.desc())
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        items = [CourseResponse.model_validate(crs) for crs in result.scalars().all()]
        return PaginatedResponse(data=items, total=total, skip=skip, limit=limit)

    async def get_courses_by_ids(self, course_ids: List[int], tenant_id: int) -> List[Course]:
        if not course_ids:
            return []
        result = await self.db.execute(
            select(Course).where(
                and_(Course.id.in_(course_ids), Course.tenant_id == tenant_id)
            )
        )
        return list(result.scalars().all())

    # ============================================================
    # 6. Course Units
    # ============================================================
    async def create_course_unit(self, **kwargs) -> CourseUnit:
        unit = CourseUnit(**kwargs)
        self.db.add(unit)
        await self.db.commit()
        await self.db.refresh(unit)
        return unit

    async def get_course_units(
        self, course_id: int, tenant_id: int, skip: int = 0, limit: int = 100
    ) -> PaginatedResponse[CourseUnitResponse]:
        course = await self.get_course(course_id, tenant_id)
        if not course:
            raise NotFoundError("Course not found")
        query = (
            select(CourseUnit)
            .where(CourseUnit.course_id == course_id)
            .order_by(CourseUnit.order_index)
        )
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        items = [CourseUnitResponse.model_validate(unit) for unit in result.scalars().all()]
        return PaginatedResponse(data=items, total=total, skip=skip, limit=limit)

    async def update_course_unit(self, unit_id: int, tenant_id: int, title: str) -> Optional[CourseUnit]:
        unit = await self.db.execute(
            select(CourseUnit)
            .join(Course, Course.id == CourseUnit.course_id)
            .where(
                and_(CourseUnit.id == unit_id, Course.tenant_id == tenant_id)
            )
        )
        unit = unit.scalar_one_or_none()
        if unit:
            setattr(unit, "title", title)
            await self.db.commit()
            await self.db.refresh(unit)
        return unit

    async def delete_course_unit(self, unit_id: int, tenant_id: int) -> bool:
        unit = await self.db.execute(
            select(CourseUnit)
            .join(Course, Course.id == CourseUnit.course_id)
            .where(
                and_(CourseUnit.id == unit_id, Course.tenant_id == tenant_id)
            )
        )
        unit = unit.scalar_one_or_none()
        if unit:
            await self.db.delete(unit)
            await self.db.commit()
            return True
        return False

    # ============================================================
    # 7. Knowledge Nodes
    # ============================================================
    async def create_node(self, **kwargs) -> KnowledgeNode:
        node = KnowledgeNode(**kwargs)
        self.db.add(node)
        await self.db.commit()
        await self.db.refresh(node)
        return node

    async def get_course_nodes(
        self, course_id: int, tenant_id: int, skip: int = 0, limit: int = 100
    ) -> PaginatedResponse[KnowledgeNodeResponse]:
        course = await self.get_course(course_id, tenant_id)
        if not course:
            raise NotFoundError("Course not found")
        query = (
            select(KnowledgeNode)
            .where(KnowledgeNode.course_id == course_id)
            .order_by(KnowledgeNode.order_index)
        )
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        items = [KnowledgeNodeResponse.model_validate(node) for node in result.scalars().all()]
        return PaginatedResponse(data=items, total=total, skip=skip, limit=limit)

    async def get_node(self, node_id: int) -> Optional[KnowledgeNode]:
        result = await self.db.execute(select(KnowledgeNode).where(KnowledgeNode.id == node_id))
        return result.scalar_one_or_none()

    async def update_node(self, node_id: int, tenant_id: int, title: str) -> Optional[KnowledgeNode]:
        node = await self.get_node(node_id)
        if node:
            course = await self.get_course(cast(int, node.course_id), tenant_id)
            if not course:
                return None
            setattr(node, "title", title)
            await self.db.commit()
            await self.db.refresh(node)
        return node

    async def delete_node(self, node_id: int, tenant_id: int) -> bool:
        node = await self.get_node(node_id)
        if node:
            course = await self.get_course(cast(int, node.course_id), tenant_id)
            if not course:
                return False
            await self.db.delete(node)
            await self.db.commit()
            return True
        return False

    async def create_node_material(self, node_id: int, **kwargs) -> NodeMaterial:
        material = NodeMaterial(node_id=node_id, **kwargs)
        self.db.add(material)
        try:
            await self.db.commit()
            await self.db.refresh(material)
            return material
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(status_code=404, detail=f"الدرس (Node) برقم {node_id} غير موجود")

    async def get_node_materials(self, node_id: int) -> List[NodeMaterial]:
        result = await self.db.execute(
            select(NodeMaterial).where(NodeMaterial.node_id == node_id)
        )
        return list(result.scalars().all())

    async def create_quiz(self, node_id: int, data: dict) -> Quiz:
        quiz = Quiz(node_id=node_id, **data)
        self.db.add(quiz)
        await self.db.commit()
        await self.db.refresh(quiz)
        return quiz

    async def get_quiz_by_node(self, node_id: int) -> Optional[Quiz]:
        result = await self.db.execute(select(Quiz).where(Quiz.node_id == node_id))
        return result.scalar_one_or_none()

    # ============================================================
    # 8. Enrollment
    # ============================================================
    async def enroll(self, **kwargs) -> Enrollment:
        enrollment = Enrollment(**kwargs)
        self.db.add(enrollment)
        await self.db.commit()
        await self.db.refresh(enrollment)
        return enrollment

    async def get_enrollment(self, user_id: int, course_id: int, tenant_id: int) -> Optional[Enrollment]:
        result = await self.db.execute(
            select(Enrollment).where(
                and_(
                    Enrollment.user_id == user_id,
                    Enrollment.course_id == course_id,
                    Enrollment.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_user_enrollments(
        self, user_id: int, tenant_id: int, skip: int = 0, limit: int = 100
    ) -> PaginatedResponse[EnrollmentResponse]:
        query = (
            select(Enrollment)
            .where(
                and_(Enrollment.user_id == user_id, Enrollment.tenant_id == tenant_id)
            )
            .order_by(Enrollment.created_at.desc())
        )
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        items = [EnrollmentResponse.model_validate(enr) for enr in result.scalars().all()]
        return PaginatedResponse(data=items, total=total, skip=skip, limit=limit)

    async def update_progress(self, user_id: int, course_id: int, tenant_id: int, progress: float) -> Optional[Enrollment]:
        enrollment = await self.get_enrollment(user_id, course_id, tenant_id)
        if enrollment:
            setattr(enrollment, "progress_percentage", progress)
            if progress >= 100:
                setattr(enrollment, "is_completed", True)
            self.db.add(enrollment)
            await self.db.commit()
            await self.db.refresh(enrollment)
        return enrollment

    # ============================================================
    # 9. Tasks & Submissions
    # ============================================================
    async def create_task(self, data: dict) -> AcademyTask:
        task = AcademyTask(**data)
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_task(self, task_id: int, tenant_id: int) -> Optional[AcademyTask]:
        result = await self.db.execute(
            select(AcademyTask)
            .join(Course, Course.id == AcademyTask.course_id)
            .where(
                and_(AcademyTask.id == task_id, Course.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_tasks_by_course(
        self, course_id: int, tenant_id: int, skip: int = 0, limit: int = 100
    ) -> PaginatedResponse[TaskResponse]:
        course = await self.get_course(course_id, tenant_id)
        if not course:
            raise NotFoundError("Course not found")
        query = select(AcademyTask).where(AcademyTask.course_id == course_id)
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        items = [TaskResponse.model_validate(task) for task in result.scalars().all()]
        return PaginatedResponse(data=items, total=total, skip=skip, limit=limit)

    async def submit_task(self, **kwargs) -> TaskSubmission:
        submission = TaskSubmission(**kwargs)
        self.db.add(submission)
        await self.db.commit()
        await self.db.refresh(submission)
        return submission

    async def get_pending_submissions(
        self, task_id: int, tenant_id: int, skip: int = 0, limit: int = 100
    ) -> PaginatedResponse[TaskSubmissionResponse]:
        task = await self.get_task(task_id, tenant_id)
        if not task:
            raise NotFoundError("Task not found")
        query = (
            select(TaskSubmission)
            .options(selectinload(TaskSubmission.user))
            .where(
                and_(
                    TaskSubmission.task_id == task_id,
                    TaskSubmission.status == "SUBMITTED"
                )
            )
            .order_by(TaskSubmission.submitted_at.asc())
        )
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        items = [TaskSubmissionResponse.model_validate(sub) for sub in result.scalars().all()]
        return PaginatedResponse(data=items, total=total, skip=skip, limit=limit)

    async def grade_submission(
        self, submission_id: int, tenant_id: int, grade: float, feedback: str, status: str
    ) -> Optional[TaskSubmission]:
        submission = await self.db.execute(
            select(TaskSubmission)
            .join(AcademyTask, AcademyTask.id == TaskSubmission.task_id)
            .join(Course, Course.id == AcademyTask.course_id)
            .where(
                and_(
                    TaskSubmission.id == submission_id,
                    Course.tenant_id == tenant_id
                )
            )
        )
        submission = submission.scalar_one_or_none()
        if submission:
            setattr(submission, "grade", grade)
            setattr(submission, "instructor_feedback", feedback)
            setattr(submission, "status", status)
            await self.db.commit()
            await self.db.refresh(submission)
        return submission

    async def get_student_submissions(
        self, user_id: int, tenant_id: int, skip: int = 0, limit: int = 100
    ) -> PaginatedResponse[TaskSubmissionResponse]:
        query = (
            select(TaskSubmission)
            .join(AcademyTask, AcademyTask.id == TaskSubmission.task_id)
            .join(Course, Course.id == AcademyTask.course_id)
            .where(
                and_(TaskSubmission.user_id == user_id, Course.tenant_id == tenant_id)
            )
            .order_by(TaskSubmission.submitted_at.desc())
        )
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        items = [TaskSubmissionResponse.model_validate(sub) for sub in result.scalars().all()]
        return PaginatedResponse(data=items, total=total, skip=skip, limit=limit)

    # ============================================================
    # 10. Live Sessions
    # ============================================================
    async def create_live_session(self, node_id: int, data: dict) -> LiveSession:
        session_data = data.copy()
        session_data["node_id"] = node_id
        if "instructor_id" not in session_data:
            session_data["instructor_id"] = 1
        live_session = LiveSession(**session_data)
        self.db.add(live_session)
        await self.db.commit()
        await self.db.refresh(live_session)
        return live_session

    # ============================================================
    # 11. AI & Analytics
    # ============================================================
    async def get_or_create_digital_twin(self, user_id: int) -> StudentDigitalTwin:
        result = await self.db.execute(
            select(StudentDigitalTwin).where(StudentDigitalTwin.user_id == user_id)
        )
        twin = result.scalar_one_or_none()
        if not twin:
            twin = StudentDigitalTwin(user_id=user_id)
            self.db.add(twin)
            await self.db.commit()
            await self.db.refresh(twin)
        return twin

    async def create_camera_analysis(self, **kwargs) -> ClassroomCameraAnalysis:
        analysis = ClassroomCameraAnalysis(**kwargs)
        self.db.add(analysis)
        await self.db.commit()
        await self.db.refresh(analysis)
        return analysis

    async def get_course_analytics(self, course_id: int, tenant_id: int) -> Optional[CourseAnalytics]:
        result = await self.db.execute(
            select(CourseAnalytics).where(
                and_(CourseAnalytics.course_id == course_id, CourseAnalytics.tenant_id == tenant_id)
            )
        )
        return result.scalar_one_or_none()

    async def update_course_analytics(
        self,
        course_id: int,
        tenant_id: int,
        increment_enrollments: bool = False,
        increment_completions: bool = False,
        grade: Optional[float] = None,
        revenue: Optional[float] = None
    ) -> Optional[CourseAnalytics]:
        analytics = await self.get_course_analytics(course_id, tenant_id)
        if not analytics:
            course = await self.get_course(course_id, tenant_id)
            if not course:
                return None
            analytics = CourseAnalytics(course_id=course_id, tenant_id=tenant_id)
            self.db.add(analytics)

        current_enrollments = int(getattr(analytics, "total_enrollments", 0) or 0)
        current_completions = int(getattr(analytics, "total_completions", 0) or 0)
        current_avg = float(getattr(analytics, "average_grade", 0.0) or 0.0)
        current_revenue = float(getattr(analytics, "revenue_generated_mrusdt", 0.0) or 0.0)

        if increment_enrollments:
            setattr(analytics, "total_enrollments", current_enrollments + 1)
        if increment_completions:
            current_completions += 1
            setattr(analytics, "total_completions", current_completions)
        if grade is not None:
            total_grades = (current_avg * max(0, current_completions - 1)) + grade
            new_avg = total_grades / current_completions if current_completions > 0 else 0.0
            setattr(analytics, "average_grade", new_avg)
        if revenue is not None:
            setattr(analytics, "revenue_generated_mrusdt", current_revenue + revenue)

        await self.db.commit()
        await self.db.refresh(analytics)
        return analytics

    # ============================================================
    # 12. Financial Summary & Leaderboard
    # ============================================================
    async def get_financial_summary(self, tenant_id: int) -> dict:
        now = datetime.now(timezone.utc)
        paid_result = await self.db.execute(
            select(func.coalesce(func.sum(Enrollment.paid_amount), 0))
            .where(Enrollment.tenant_id == tenant_id)
        )
        total_paid = float(paid_result.scalar() or 0)
        overdue_result = await self.db.execute(
            select(func.coalesce(func.sum(PaymentInstallment.amount_due), 0))
            .where(
                and_(
                    PaymentInstallment.tenant_id == tenant_id,
                    PaymentInstallment.is_paid == False,
                    PaymentInstallment.due_date < now
                )
            )
        )
        total_overdue = float(overdue_result.scalar() or 0)
        return {"total_paid": total_paid, "total_overdue": total_overdue}

    async def get_academy_leaderboard(self, tenant_id: int, limit: int = 10) -> List[dict]:
        query = (
            select(
                TaskSubmission.user_id,
                func.sum(TaskSubmission.grade).label("total_xp")
            )
            .join(AcademyTask, AcademyTask.id == TaskSubmission.task_id)
            .join(Course, Course.id == AcademyTask.course_id)
            .where(
                and_(
                    TaskSubmission.status == "GRADED",
                    Course.tenant_id == tenant_id
                )
            )
            .group_by(TaskSubmission.user_id)
            .order_by(func.sum(TaskSubmission.grade).desc())
            .limit(min(limit, 100))
        )
        result = await self.db.execute(query)
        rows = result.all()
        leaderboard = []
        for index, row in enumerate(rows):
            leaderboard.append({
                "rank": index + 1,
                "user_id": row.user_id,
                "total_xp": float(row.total_xp or 0)
            })
        return leaderboard

    # ============================================================
    # 13. Instructor Statistics
    # ============================================================
    async def count_instructor_courses(self, instructor_id: int, tenant_id: int) -> int:
        result = await self.db.execute(
            select(func.count(Course.id))
            .where(
                and_(Course.instructor_id == instructor_id, Course.tenant_id == tenant_id)
            )
        )
        return result.scalar() or 0

    async def count_distinct_students_in_instructor_courses(self, instructor_id: int, tenant_id: int) -> int:
        course_ids_query = select(Course.id).where(
            and_(Course.instructor_id == instructor_id, Course.tenant_id == tenant_id)
        )
        result = await self.db.execute(
            select(func.count(Enrollment.user_id.distinct()))
            .where(
                and_(
                    Enrollment.course_id.in_(course_ids_query),
                    Enrollment.tenant_id == tenant_id
                )
            )
        )
        return result.scalar() or 0

    async def count_pending_submissions_for_instructor(self, instructor_id: int, tenant_id: int) -> int:
        course_ids_query = select(Course.id).where(
            and_(Course.instructor_id == instructor_id, Course.tenant_id == tenant_id)
        )
        result = await self.db.execute(
            select(func.count(TaskSubmission.id))
            .join(AcademyTask, AcademyTask.id == TaskSubmission.task_id)
            .where(
                and_(
                    AcademyTask.course_id.in_(course_ids_query),
                    TaskSubmission.status == "SUBMITTED"
                )
            )
        )
        return result.scalar() or 0

    async def count_certificates_for_instructor(self, instructor_id: int, tenant_id: int) -> int:
        course_ids_query = select(Course.id).where(
            and_(Course.instructor_id == instructor_id, Course.tenant_id == tenant_id)
        )
        result = await self.db.execute(
            select(func.count(SpiritualCertificate.id))
            .where(SpiritualCertificate.course_id.in_(course_ids_query))
        )
        return result.scalar() or 0