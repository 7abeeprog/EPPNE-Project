# app/domains/academy/service.py
import io
import mimetypes
import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any, cast
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.domains.academy.repository import AcademyRepository
from app.domains.finance.service import FinanceService
from app.domains.identity.repository import UserRepository
from app.core.errors import PermissionDeniedError, NotFoundError, InsufficientBalanceError
from app.core.storage import minio_client, ensure_bucket_exists
from app.core.ai_engine import analyze_and_recommend_courses
from app.domains.academy.models import Course, Enrollment
from app.domains.identity.models import User


class AcademyService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = AcademyRepository(db)
        self.finance = FinanceService(db, tenant_id)

    async def _upload_file_to_minio(self, bucket: str, object_name: str, file_content: bytes, content_type: str):
        try:
            def sync_upload():
                file_stream = io.BytesIO(file_content)
                minio_client.put_object(
                    bucket_name=bucket,
                    object_name=object_name,
                    data=file_stream,
                    length=len(file_content),
                    content_type=content_type
                )
            await asyncio.to_thread(sync_upload)
            return True
        except Exception as e:
            print(f"⚠️ [Background Upload] Failed to upload {object_name}: {str(e)}")
            return False

    # ============================================================
    # 1. Tenants & Org Entities
    # ============================================================
    async def create_tenant(self, name: str, domain: str, admin_id: int, branding: Optional[dict] = None):
        return await self.repo.create_tenant(
            name=name, domain=domain, admin_id=admin_id, branding=branding or {}
        )

    async def create_org_entity(
        self,
        name: str,
        entity_type: str,
        parent_id: Optional[int] = None,
        description: Optional[str] = None
    ):
        return await self.repo.create_org_entity(
            tenant_id=self.tenant_id,
            name=name,
            entity_type=entity_type,
            parent_id=parent_id,
            description=description
        )

    # ============================================================
    # 2. Bootcamps
    # ============================================================
    async def create_bootcamp(self, data: dict, instructor_id: int):
        org_entity = await self.repo.get_org_entity(data['org_entity_id'])
        if not org_entity or cast(bool, org_entity.tenant_id) != self.tenant_id:
            raise PermissionDeniedError("الكيان التنظيمي لا يخص هذا المستأجر")
        bootcamp = await self.repo.create_bootcamp(**data, instructor_id=instructor_id)
        await self.repo._invalidate_cache("bootcamps")
        return bootcamp

    # ============================================================
    # 3. Tracks
    # ============================================================
    async def create_track(self, data: dict):
        if not data.get('bootcamp_id') and not data.get('org_entity_id'):
            raise ValueError("يجب تحديد إما bootcamp_id أو org_entity_id")
        if data.get('org_entity_id'):
            org_entity = await self.repo.get_org_entity(data['org_entity_id'])
            if not org_entity or cast(bool, org_entity.tenant_id) != self.tenant_id:
                raise PermissionDeniedError("الكيان التنظيمي لا يخص هذا المستأجر")
        track = await self.repo.create_track(**data)
        await self.repo._invalidate_cache("tracks")
        return track

    # ============================================================
    # 4. Cohorts
    # ============================================================
    async def create_cohort(self, data: dict):
        org_entity = await self.repo.get_org_entity(data['org_entity_id'])
        if not org_entity or cast(bool, org_entity.tenant_id) != self.tenant_id:
            raise PermissionDeniedError("الكيان التنظيمي لا يخص هذا المستأجر")
        cohort = await self.repo.create_cohort(**data)
        await self.repo._invalidate_cache("cohorts")
        return cohort

    # ============================================================
    # 5. Courses Management
    # ============================================================
    async def create_course(self, data: dict, instructor_id: int):
        if data.get('tenant_id') != self.tenant_id:
            raise PermissionDeniedError("تعارض في المستأجر")
        course = await self.repo.create_course(**data, instructor_id=instructor_id)
        await self.repo._invalidate_cache("courses")
        await self.repo._invalidate_cache("published_courses")
        return course

    async def update_course(self, course_id: int, data: dict, instructor_id: int):
        course = await self.repo.get_course(course_id, self.tenant_id)
        if not course:
            raise NotFoundError("الكورس غير موجود")
        updated_course = await self.repo.update_course(course_id, self.tenant_id, **data)
        await self.repo._invalidate_cache(f"course_{course_id}")
        await self.repo._invalidate_cache("courses")
        await self.repo._invalidate_cache("published_courses")
        return updated_course

    async def get_store_courses(self, user_id: int, skip: int = 0, limit: int = 100):
        user_repo = UserRepository(self.db)
        user = await user_repo.get_by_id(user_id, self.tenant_id)
        if not user:
            raise NotFoundError("المستخدم غير موجود")
        if not cast(bool, user.is_active):
            raise PermissionDeniedError("المستخدم غير نشط")
        return await self.repo.list_published_courses(self.tenant_id, skip=skip, limit=limit)

    # ============================================================
    # 6. Course Units
    # ============================================================
    async def create_course_unit(self, course_id: int, data: dict):
        course = await self.repo.get_course(course_id, self.tenant_id)
        if not course:
            raise NotFoundError("الكورس غير موجود")
        unit = await self.repo.create_course_unit(course_id=course_id, **data)
        await self.repo._invalidate_cache(f"course_units_{course_id}")
        return unit

    async def get_course_units(self, course_id: int, skip: int = 0, limit: int = 100):
        return await self.repo.get_course_units(course_id, self.tenant_id, skip, limit)

    async def update_course_unit(self, unit_id: int, title: str):
        unit = await self.repo.update_course_unit(unit_id, self.tenant_id, title)
        if not unit:
            raise NotFoundError("الوحدة غير موجودة")
        await self.repo._invalidate_cache(f"course_units_{unit.course_id}")
        return unit

    async def delete_course_unit(self, unit_id: int):
        success = await self.repo.delete_course_unit(unit_id, self.tenant_id)
        if not success:
            raise NotFoundError("الوحدة غير موجودة")
        await self.repo._invalidate_cache("course_units")
        return True

    # ============================================================
    # 7. Knowledge Nodes
    # ============================================================
    async def create_knowledge_node(self, data: dict):
        if data.get('course_id'):
            course = await self.repo.get_course(data['course_id'], self.tenant_id)
            if not course:
                raise NotFoundError("الكورس غير موجود")
        node = await self.repo.create_node(**data)
        await self.repo._invalidate_cache(f"course_nodes_{data['course_id']}")
        return node

    async def get_course_nodes(self, course_id: int, skip: int = 0, limit: int = 100):
        return await self.repo.get_course_nodes(course_id, self.tenant_id, skip, limit)

    async def update_knowledge_node(self, node_id: int, title: str):
        node = await self.repo.update_node(node_id, self.tenant_id, title)
        if not node:
            raise NotFoundError("الدرس غير موجود")
        await self.repo._invalidate_cache(f"course_nodes_{node.course_id}")
        return node

    async def delete_knowledge_node(self, node_id: int):
        success = await self.repo.delete_node(node_id, self.tenant_id)
        if not success:
            raise NotFoundError("الدرس غير موجود")
        await self.repo._invalidate_cache("course_nodes")
        return success

    # ============================================================
    # 8. Live Sessions
    # ============================================================
    async def create_live_session(self, node_id: int, data: dict):
        node = await self.repo.get_node(node_id)
        if not node:
            raise NotFoundError("الدرس غير موجود")
        live_session = await self.repo.create_live_session(node_id, data)
        await self.repo._invalidate_cache(f"live_sessions_{node_id}")
        return live_session

    # ============================================================
    # 9. Node Materials
    # ============================================================
    async def create_node_material(self, node_id: int, data: dict):
        node = await self.repo.get_node(node_id)
        if not node:
            raise NotFoundError("الدرس غير موجود")
        material = await self.repo.create_node_material(node_id=node_id, **data)
        await self.repo._invalidate_cache(f"node_materials_{node_id}")
        return material

    async def get_node_materials(self, node_id: int):
        return await self.repo.get_node_materials(node_id)

    # ============================================================
    # 10. Quizzes
    # ============================================================
    async def create_quiz(self, node_id: int, data: dict):
        node = await self.repo.get_node(node_id)
        if not node:
            raise NotFoundError("الدرس غير موجود")
        quiz = await self.repo.create_quiz(node_id=node_id, data=data)
        await self.repo._invalidate_cache(f"quiz_{node_id}")
        return quiz

    # ============================================================
    # 11. Enrollment & Progress
    # ============================================================
    async def enroll_in_course(
        self,
        user_id: int,
        course_id: int,
        payment_method: Optional[str],
        payment_ref: Optional[str] = None,
        cohort_id: Optional[int] = None,
        affiliate_code: Optional[str] = None,
    ):
        course = await self.repo.get_course(course_id, self.tenant_id)
        if not course or not cast(bool, course.is_published):
            raise NotFoundError("الكورس غير موجود أو غير منشور")

        existing = await self.repo.get_enrollment(user_id, course_id, self.tenant_id)
        if existing:
            raise PermissionDeniedError("أنت مسجل بالفعل في هذا الكورس")

        user_repo = UserRepository(self.db)
        user = await user_repo.get_by_id(user_id, self.tenant_id)
        if not user:
            raise NotFoundError("المستخدم غير موجود")

        async with self.db.begin_nested():
            amount = float(cast(Decimal, course.price_mrusdt))
            currency = cast(str, course.currency)
            is_free = cast(bool, course.is_free)

            if payment_method == "WALLET" and amount > 0 and not is_free:
                try:
                    await self.finance.transfer(
                        sender_id=user_id,
                        receiver_email="academy@eppne.com",
                        currency=currency,
                        amount=Decimal(str(amount)),
                        notes=f"Enrollment in course {course.id} - {course.title}",
                        idempotency_key=f"enroll_{user_id}_{course_id}_{uuid.uuid4().hex}"
                    )
                    payment_status = "COMPLETED"
                    enrollment_status = "ACTIVE"
                except InsufficientBalanceError as e:
                    raise PermissionDeniedError(f"رصيد غير كافٍ: {str(e)}")
                except Exception as e:
                    raise PermissionDeniedError(f"فشل المعاملة المالية: {str(e)}")
            else:
                payment_status = "COMPLETED" if is_free or amount == 0 else "PENDING"
                enrollment_status = "ACTIVE" if is_free or amount == 0 else "PENDING"

            enrollment = await self.repo.enroll(
                user_id=user_id,
                course_id=course_id,
                tenant_id=self.tenant_id,
                cohort_id=cohort_id,
                payment_method=payment_method or "FREE",
                payment_ref=payment_ref,
                payment_status=payment_status,
                status=enrollment_status,
                paid_amount=float(amount) if amount else 0
            )

            if affiliate_code:
                try:
                    from app.domains.affiliate.service import AffiliateService
                    affiliate_service = AffiliateService(self.db, self.tenant_id)
                    await affiliate_service.track_referral(
                        referrer_code=affiliate_code,
                        referred_user_id=user_id,
                        entity_type="COURSE",
                        entity_id=course_id,
                    )
                except Exception as e:
                    print(f"⚠️ [Affiliate Tracking] Failed to track referral: {str(e)}")

        await self.repo._invalidate_cache(f"user_enrollments_{user_id}")
        await self.repo._invalidate_cache("published_courses")

        return enrollment

    async def get_user_enrollments(self, user_id: int, skip: int = 0, limit: int = 100):
        return await self.repo.get_user_enrollments(user_id, self.tenant_id, skip, limit)

    async def update_progress(self, user_id: int, course_id: int, progress: float):
        enrollment = await self.repo.get_enrollment(user_id, course_id, self.tenant_id)
        if not enrollment:
            raise NotFoundError("غير مسجل في هذا الكورس")
        updated = await self.repo.update_progress(user_id, course_id, self.tenant_id, progress)
        await self.repo._invalidate_cache(f"enrollment_{user_id}_{course_id}")
        return updated

    # ============================================================
    # 12. Tasks
    # ============================================================
    async def create_task(self, data: dict):
        course = await self.repo.get_course(data['course_id'], self.tenant_id)
        if not course:
            raise NotFoundError("الكورس غير موجود")
        task = await self.repo.create_task(data)
        await self.repo._invalidate_cache(f"tasks_course_{data['course_id']}")
        return task

    async def get_course_tasks(self, course_id: int, skip: int = 0, limit: int = 100):
        return await self.repo.get_tasks_by_course(course_id, self.tenant_id, skip, limit)

    async def submit_task(self, user_id: int, task_id: int, data: dict):
        task = await self.repo.get_task(task_id, self.tenant_id)
        if not task or not cast(bool, task.is_active):
            raise NotFoundError("المهمة غير موجودة أو مغلقة")

        user_repo = UserRepository(self.db)
        user = await user_repo.get_by_id(user_id, self.tenant_id)
        if not user:
            raise NotFoundError("المستخدم غير موجود")

        deadline = cast(datetime, task.deadline) if task.deadline is not None else None
        if deadline and deadline < datetime.now(timezone.utc):
            raise PermissionDeniedError("انتهى وقت تسليم هذه المهمة")

        submission = await self.repo.submit_task(
            user_id=user_id,
            task_id=task_id,
            **data
        )
        await self.repo._invalidate_cache(f"submissions_task_{task_id}")
        await self.repo._invalidate_cache(f"student_submissions_{user_id}")
        return submission

    # ============================================================
    # 13. Instructor Grading
    # ============================================================
    async def get_task_submissions(self, task_id: int, skip: int = 0, limit: int = 100):
        return await self.repo.get_pending_submissions(task_id, self.tenant_id, skip, limit)

    async def grade_submission(self, submission_id: int, grade: float, feedback: str, status: str):
        submission = await self.repo.grade_submission(submission_id, self.tenant_id, grade, feedback, status)
        if not submission:
            raise NotFoundError("التسليم غير موجود")
        await self.repo._invalidate_cache("submissions_task")
        return submission

    async def get_my_submissions(self, user_id: int, skip: int = 0, limit: int = 100):
        return await self.repo.get_student_submissions(user_id, self.tenant_id, skip, limit)

    # ============================================================
    # 14. Instructor Statistics
    # ============================================================
    async def get_instructor_stats(self, instructor_id: int) -> dict:
        instructor = await self.repo.get_instructor(instructor_id, self.tenant_id)
        if not instructor:
            raise NotFoundError("المدرب غير موجود")
        total_courses = await self.repo.count_instructor_courses(instructor_id, self.tenant_id)
        total_students = await self.repo.count_distinct_students_in_instructor_courses(instructor_id, self.tenant_id)
        pending_submissions = await self.repo.count_pending_submissions_for_instructor(instructor_id, self.tenant_id)
        total_certificates = await self.repo.count_certificates_for_instructor(instructor_id, self.tenant_id)
        return {
            "total_courses": total_courses,
            "total_students": total_students,
            "pending_submissions": pending_submissions,
            "total_certificates": total_certificates
        }

    # ============================================================
    # 15. Leaderboard
    # ============================================================
    async def get_leaderboard(self, limit: int = 10):
        return await self.repo.get_academy_leaderboard(self.tenant_id, limit)

    # ============================================================
    # 16. Financial Summary
    # ============================================================
    async def get_financial_summary(self):
        return await self.repo.get_financial_summary(self.tenant_id)

    # ============================================================
    # 17. Digital Twin
    # ============================================================
    async def get_or_create_digital_twin(self, user_id: int):
        return await self.repo.get_or_create_digital_twin(user_id)

    # ============================================================
    # 18. Camera Analysis
    # ============================================================
    async def create_camera_analysis(self, **kwargs):
        return await self.repo.create_camera_analysis(**kwargs)

    # ============================================================
    # 19. Course Analytics
    # ============================================================
    async def update_course_analytics(
        self,
        course_id: int,
        increment_enrollments: bool = False,
        increment_completions: bool = False,
        grade: Optional[float] = None,
        revenue: Optional[float] = None
    ):
        return await self.repo.update_course_analytics(
            course_id=course_id,
            tenant_id=self.tenant_id,
            increment_enrollments=increment_enrollments,
            increment_completions=increment_completions,
            grade=grade,
            revenue=revenue
        )

    # ============================================================
    # 20. File Upload
    # ============================================================
    async def upload_course_thumbnail(
        self,
        course_id: int,
        file_content: bytes,
        filename: str,
        background_tasks: BackgroundTasks
    ) -> str:
        course = await self.repo.get_course(course_id, self.tenant_id)
        if not course:
            raise NotFoundError("الكورس غير موجود")

        bucket = "academy-thumbnails"
        ensure_bucket_exists(bucket)
        content_type, _ = mimetypes.guess_type(filename)
        content_type = content_type or "application/octet-stream"

        file_ext = filename.split('.')[-1] if '.' in filename else 'jpg'
        unique_name = f"{uuid.uuid4().hex}.{file_ext}"
        object_name = f"courses/{course_id}/thumb_{unique_name}"

        temp_url = f"http://localhost:9000/{bucket}/{object_name}"

        background_tasks.add_task(
            self._upload_file_to_minio,
            bucket=bucket,
            object_name=object_name,
            file_content=file_content,
            content_type=content_type
        )

        updated_course = await self.repo.update_course(
            course_id,
            self.tenant_id,
            thumbnail_url=temp_url
        )

        await self.repo._invalidate_cache(f"course_{course_id}")
        await self.repo._invalidate_cache("published_courses")

        return temp_url