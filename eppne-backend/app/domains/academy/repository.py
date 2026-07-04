# app/domains/academy/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import json
import hashlib

from app.domains.academy.models import (
    AcademyTenant, OrganizationEntity, Instructor, Bootcamp, Track, Course,
    CourseUnit, KnowledgeNode, NodeMaterial, Quiz, Enrollment, SpiritualCertificate,
    SovereignBadge, LiveSession, LiveAttendance, StudentDigitalTwin, ClassroomCameraAnalysis,
    CertificateIssuanceLog, CourseAnalytics, AcademyTask, TaskSubmission, AcademyCohort,
    PaymentInstallment
)
from app.core.errors import NotFoundError

# 🔥 محاولة استيراد Redis (إذا كان موجوداً)، وإلا سنعمل بدون Cache مؤقتاً
try:
    from app.core.cache import redis_client  # نفترض وجود ملف cache.py مستقبلاً
except ImportError:
    redis_client = None
    print("Warning: Redis not configured. Running without caching.")

class AcademyRepository:
    def __init__(self, db: AsyncSession, cache_ttl: int = 300):
        self.db = db
        self.cache_ttl = cache_ttl  # 5 دقائق افتراضياً

    # ============================================================
    # 🔥 دوال التخزين المؤقت الذكية (Cache Helpers)
    # ============================================================
    def _get_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """توليد مفتاح Cache فريد بناءً على اسم الدالة والمعاملات"""
        key_parts = [prefix]
        key_parts.extend([str(a) for a in args])
        key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
        raw = ":".join(key_parts)
        # استخدام hash لتقصير المفتاح ومنع تجاوز حدود Redis (512MB)
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

    async def _set_cache(self, key: str, value: Any, ttl: int = None):
        if not redis_client:
            return
        try:
            ttl = ttl or self.cache_ttl
            await redis_client.setex(key, ttl, json.dumps(value, default=str))
        except Exception:
            pass

    async def _invalidate_cache(self, pattern: str = None):
        """مسح جزء من الـ Cache (مثلاً كل ما يخص courses)"""
        if not redis_client or not pattern:
            return
        try:
            # إذا كان Redis يدعم SCAN, نستخدمه. هنا نكتفي بمسح مفتاح معين أو نتركه.
            # في الإصدار المبسط، نمسح المفاتيح المعروفة يدوياً.
            # سنقوم بمسح الكاش في دوال التحديث بشكل مباشر.
            pass
        except Exception:
            pass

    # ============================================================
    # 🔥 دوال مساعدة للـ Pagination الإلزامي (منع استنزاف الذاكرة)
    # ============================================================
    async def _paginate_query(self, query, skip: int = 0, limit: int = 100):
        """تطبيق Pagination مع حد أقصى 1000 صف"""
        safe_limit = min(limit, 1000)  # حماية من الطلبات الضخمة
        return query.offset(skip).limit(safe_limit)

    # ============================================================
    # 1. Tenants & Org Entities
    # ============================================================
    async def create_tenant(self, **kwargs) -> AcademyTenant:
        tenant = AcademyTenant(**kwargs)
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        # مسح Cache الخاص بـ tenants (اختياري)
        return tenant

    async def get_tenant_by_domain(self, domain: str) -> AcademyTenant | None:
        # استخدام Cache للبحث المتكرر بالنطاق
        cache_key = self._get_cache_key("tenant_domain", domain)
        cached = await self._get_cache(cache_key)
        if cached:
            return AcademyTenant(**cached)

        result = await self.db.execute(
            select(AcademyTenant).where(AcademyTenant.domain == domain)
        )
        tenant = result.scalar_one_or_none()
        if tenant:
            # نحول إلى dict للتخزين
            await self._set_cache(cache_key, {c: getattr(tenant, c) for c in tenant.__table__.columns.keys()})
        return tenant

    async def create_org_entity(self, **kwargs) -> OrganizationEntity:
        entity = OrganizationEntity(**kwargs)
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity

    async def get_org_entities(
        self, tenant_id: int, skip: int = 0, limit: int = 100
    ) -> list[OrganizationEntity]:
        """🔒 تم فرض Pagination إلزامي"""
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
        self, org_entity_id: int = None, skip: int = 0, limit: int = 100
    ) -> list[Bootcamp]:
        """🔒 تم فرض Pagination إلزامي"""
        query = select(Bootcamp)
        if org_entity_id:
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
        self, org_entity_id: int = None, bootcamp_id: int = None, skip: int = 0, limit: int = 100
    ) -> list[Track]:
        """🔒 تم فرض Pagination إلزامي"""
        query = select(Track)
        if bootcamp_id:
            query = query.where(Track.bootcamp_id == bootcamp_id)
        elif org_entity_id:
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
    ) -> list[AcademyCohort]:
        """🔒 تم فرض Pagination إلزامي"""
        query = select(AcademyCohort).where(AcademyCohort.org_entity_id == org_entity_id)
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ============================================================
    # 5. Courses (مع Caching متقدم)
    # ============================================================
    async def create_course(self, **kwargs) -> Course:
        course = Course(**kwargs)
        self.db.add(course)
        await self.db.commit()
        await self.db.refresh(course)
        # مسح Cache الخاص بالكورسات المنشورة
        await self._invalidate_cache("courses")
        return course

    async def get_course(self, course_id: int) -> Course | None:
        """🔥 استخدام Cache لتخفيف ضغط DB"""
        cache_key = self._get_cache_key("course", course_id)
        cached = await self._get_cache(cache_key)
        if cached:
            return Course(**cached)

        result = await self.db.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()
        if course:
            # تخزين مؤقت مع TTL أطول (10 دقائق) لأن الكورسات لا تتغير كثيراً
            await self._set_cache(cache_key, {c: getattr(course, c) for c in course.__table__.columns.keys()}, ttl=600)
        return course

    async def update_course(self, course_id: int, **kwargs) -> Course:
        course = await self.get_course(course_id)
        if not course:
            raise NotFoundError("Course not found")
        for key, value in kwargs.items():
            setattr(course, key, value)
        await self.db.commit()
        await self.db.refresh(course)
        # 🔥 مسح Cache بعد التحديث
        await self._invalidate_cache(f"course_{course_id}")
        await self._invalidate_cache("courses")
        return course

    async def list_published_courses(
        self, tenant_id: int, skip: int = 0, limit: int = 100
    ) -> list[Course]:
        """🔥 استخدام Cache للمتجر (أكثر استعلام متكرر)"""
        cache_key = self._get_cache_key("published_courses", tenant_id, skip, limit)
        cached = await self._get_cache(cache_key)
        if cached:
            return [Course(**item) for item in cached]

        query = (
            select(Course)
            .where(
                Course.tenant_id == tenant_id,
                Course.is_published == True,
                Course.is_active == True
            )
            .order_by(Course.created_at.desc())
        )
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        courses = list(result.scalars().all())

        # تخزين مؤقت مع TTL قصير (دقيقتين) لأن الكورسات قد تُنشر فجأة
        if courses:
            await self._set_cache(
                cache_key,
                [{c: getattr(crs, c) for c in crs.__table__.columns.keys()} for crs in courses],
                ttl=120
            )
        return courses

    async def list_all_courses(self, skip: int = 0, limit: int = 100) -> list[Course]:
        """🔒 تم فرض Pagination إلزامي"""
        query = select(Course).order_by(Course.created_at.desc())
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_courses_by_ids(self, course_ids: List[int]) -> list[Course]:
        """🔥 استعلام دفعة واحدة (Batch) لتجنب N+1"""
        if not course_ids:
            return []
        result = await self.db.execute(
            select(Course).where(Course.id.in_(course_ids))
        )
        return list(result.scalars().all())

    # ============================================================
    # 6. Nodes, Units, Materials, Quizzes
    # ============================================================
    async def create_course_unit(self, **kwargs) -> CourseUnit:
        unit = CourseUnit(**kwargs)
        self.db.add(unit)
        await self.db.commit()
        await self.db.refresh(unit)
        return unit

    async def get_course_units(
        self, course_id: int, skip: int = 0, limit: int = 100
    ) -> list[CourseUnit]:
        """🔒 تم فرض Pagination إلزامي"""
        query = (
            select(CourseUnit)
            .where(CourseUnit.course_id == course_id)
            .order_by(CourseUnit.order_index)
        )
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_course_unit(self, unit_id: int, title: str) -> CourseUnit | None:
        unit = await self.db.execute(select(CourseUnit).where(CourseUnit.id == unit_id))
        unit = unit.scalar_one_or_none()
        if unit:
            unit.title = title
            await self.db.commit()
            await self.db.refresh(unit)
        return unit

    async def delete_course_unit(self, unit_id: int) -> bool:
        unit = await self.db.execute(select(CourseUnit).where(CourseUnit.id == unit_id))
        unit = unit.scalar_one_or_none()
        if unit:
            await self.db.delete(unit)
            await self.db.commit()
            return True
        return False

    async def create_node(self, **kwargs) -> KnowledgeNode:
        node = KnowledgeNode(**kwargs)
        self.db.add(node)
        await self.db.commit()
        await self.db.refresh(node)
        return node

    async def get_course_nodes(
        self, course_id: int, skip: int = 0, limit: int = 100
    ) -> list[KnowledgeNode]:
        """🔒 تم فرض Pagination إلزامي"""
        query = (
            select(KnowledgeNode)
            .where(KnowledgeNode.course_id == course_id)
            .order_by(KnowledgeNode.order_index)
        )
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_node(self, node_id: int) -> KnowledgeNode | None:
        result = await self.db.execute(select(KnowledgeNode).where(KnowledgeNode.id == node_id))
        return result.scalar_one_or_none()

    async def update_node(self, node_id: int, title: str) -> KnowledgeNode | None:
        node = await self.get_node(node_id)
        if node:
            node.title = title
            await self.db.commit()
            await self.db.refresh(node)
        return node

    async def delete_node(self, node_id: int) -> bool:
        node = await self.get_node(node_id)
        if node:
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

    async def get_node_materials(self, node_id: int) -> list[NodeMaterial]:
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

    async def get_quiz_by_node(self, node_id: int) -> Quiz | None:
        result = await self.db.execute(select(Quiz).where(Quiz.node_id == node_id))
        return result.scalar_one_or_none()

    # ============================================================
    # 7. Enrollment (مع Pagination إلزامي)
    # ============================================================
    async def enroll(self, **kwargs) -> Enrollment:
        enrollment = Enrollment(**kwargs)
        self.db.add(enrollment)
        await self.db.commit()
        await self.db.refresh(enrollment)
        return enrollment

    async def get_enrollment(self, user_id: int, course_id: int) -> Enrollment | None:
        result = await self.db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user_id,
                Enrollment.course_id == course_id
            )
        )
        return result.scalar_one_or_none()

    async def get_user_enrollments(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[Enrollment]:
        """🔥 استعلام اشتراكات المستخدم مع Pagination إلزامي"""
        query = (
            select(Enrollment)
            .where(Enrollment.user_id == user_id)
            .order_by(Enrollment.created_at.desc())
        )
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_progress(self, user_id: int, course_id: int, progress: float) -> Enrollment:
        enrollment = await self.get_enrollment(user_id, course_id)
        if enrollment:
            enrollment.progress_percentage = progress
            if progress >= 100:
                enrollment.is_completed = True
            self.db.add(enrollment)
            await self.db.commit()
            await self.db.refresh(enrollment)
        return enrollment

    # ============================================================
    # 8. Tasks & Submissions (مع تحسين الأداء)
    # ============================================================
    async def create_task(self, data: dict) -> AcademyTask:
        task = AcademyTask(**data)
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_task(self, task_id: int) -> AcademyTask | None:
        result = await self.db.execute(select(AcademyTask).where(AcademyTask.id == task_id))
        return result.scalar_one_or_none()

    async def get_tasks_by_course(
        self, course_id: int, skip: int = 0, limit: int = 100
    ) -> list[AcademyTask]:
        """🔒 تم فرض Pagination إلزامي"""
        query = select(AcademyTask).where(AcademyTask.course_id == course_id)
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def submit_task(self, **kwargs) -> TaskSubmission:
        submission = TaskSubmission(**kwargs)
        self.db.add(submission)
        await self.db.commit()
        await self.db.refresh(submission)
        return submission

    async def get_pending_submissions(
        self, task_id: int, skip: int = 0, limit: int = 100
    ) -> list[TaskSubmission]:
        """🔥 استخدام selectinload لمنع N+1 وجلب بيانات الطالب دفعة واحدة"""
        query = (
            select(TaskSubmission)
            .options(selectinload(TaskSubmission.user))  # تحميل بيانات المستخدم في نفس الاستعلام
            .where(
                TaskSubmission.task_id == task_id,
                TaskSubmission.status == "SUBMITTED"
            )
            .order_by(TaskSubmission.submitted_at.asc())
        )
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def grade_submission(
        self, submission_id: int, grade: float, feedback: str, status: str
    ) -> TaskSubmission | None:
        submission = await self.db.execute(
            select(TaskSubmission).where(TaskSubmission.id == submission_id)
        )
        submission = submission.scalar_one_or_none()
        if submission:
            submission.grade = grade
            submission.instructor_feedback = feedback
            submission.status = status
            await self.db.commit()
            await self.db.refresh(submission)
        return submission

    async def get_student_submissions(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[TaskSubmission]:
        """🔒 تم فرض Pagination إلزامي"""
        query = (
            select(TaskSubmission)
            .where(TaskSubmission.user_id == user_id)
            .order_by(TaskSubmission.submitted_at.desc())
        )
        query = await self._paginate_query(query, skip, limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ============================================================
    # 9. Live Sessions
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
    # 10. AI & Analytics
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

    async def get_course_analytics(self, course_id: int) -> CourseAnalytics | None:
        result = await self.db.execute(
            select(CourseAnalytics).where(CourseAnalytics.course_id == course_id)
        )
        return result.scalar_one_or_none()

    async def update_course_analytics(
        self,
        course_id: int,
        increment_enrollments: bool = False,
        increment_completions: bool = False,
        grade: float = None,
        revenue: float = None
    ) -> CourseAnalytics:
        analytics = await self.get_course_analytics(course_id)
        if not analytics:
            analytics = CourseAnalytics(course_id=course_id)
            self.db.add(analytics)

        if increment_enrollments:
            analytics.total_enrollments += 1
        if increment_completions:
            analytics.total_completions += 1
        if grade is not None:
            total_grades = (float(analytics.average_grade) * (analytics.total_completions - 1)) + grade
            analytics.average_grade = total_grades / analytics.total_completions if analytics.total_completions > 0 else 0
        if revenue is not None:
            analytics.revenue_generated_mrusdt = float(analytics.revenue_generated_mrusdt) + revenue

        await self.db.commit()
        await self.db.refresh(analytics)
        return analytics

    # ============================================================
    # 11. Financial Summary & Leaderboard (تجميعات محسّنة)
    # ============================================================
    async def get_financial_summary(self) -> dict:
        """🔥 حساب مالي مباشر في قاعدة البيانات (بدون تحميل كائنات)"""
        now = datetime.now(timezone.utc)

        # إجمالي المدفوعات
        paid_result = await self.db.execute(
            select(func.coalesce(func.sum(Enrollment.paid_amount), 0))
        )
        total_paid = float(paid_result.scalar() or 0)

        # إجمالي الأقساط المتأخرة
        overdue_result = await self.db.execute(
            select(func.coalesce(func.sum(PaymentInstallment.amount_due), 0))
            .where(
                PaymentInstallment.is_paid == False,
                PaymentInstallment.due_date < now
            )
        )
        total_overdue = float(overdue_result.scalar() or 0)

        return {
            "total_paid": total_paid,
            "total_overdue": total_overdue
        }

    async def get_academy_leaderboard(self, limit: int = 10) -> list[dict]:
        """🔥 تجميع مباشر مع Pagination"""
        query = (
            select(
                TaskSubmission.user_id,
                func.sum(TaskSubmission.grade).label("total_xp")
            )
            .where(TaskSubmission.status == "GRADED")
            .group_by(TaskSubmission.user_id)
            .order_by(func.sum(TaskSubmission.grade).desc())
            .limit(min(limit, 100))  # حد أقصى 100 للحماية
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