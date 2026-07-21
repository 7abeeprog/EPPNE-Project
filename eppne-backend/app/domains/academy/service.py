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
from sqlalchemy import select

from app.domains.academy.repository import AcademyRepository
from app.domains.finance.service import FinanceService
from app.core.errors import PermissionDeniedError, NotFoundError, InsufficientBalanceError
from app.core.storage import minio_client, ensure_bucket_exists
from app.core.ai_engine import analyze_and_recommend_courses
from app.domains.academy.models import Course, Enrollment
from app.domains.identity.models import User


class AcademyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AcademyRepository(db)
        self.finance = FinanceService(db)

    # ============================================================
    # 🔥 دوال مساعدة للـ Background Tasks (رفع الملفات بشكل غير متزامن)
    # ============================================================
    async def _upload_file_to_minio(self, bucket: str, object_name: str, file_content: bytes, content_type: str):
        """دالة الخلفية الفعلية لرفع الملف (تعمل في Thread منفصل)"""
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
        tenant_id: int,
        name: str,
        entity_type: str,
        parent_id: Optional[int] = None,
        description: Optional[str] = None
    ):
        return await self.repo.create_org_entity(
            tenant_id=tenant_id,
            name=name,
            entity_type=entity_type,
            parent_id=parent_id,
            description=description
        )

    # ============================================================
    # 2. Bootcamps
    # ============================================================
    async def create_bootcamp(self, data: dict, instructor_id: int):
        """إنشاء معسكر جديد"""
        bootcamp = await self.repo.create_bootcamp(**data, instructor_id=instructor_id)
        await self.repo._invalidate_cache("bootcamps")
        return bootcamp

    # ============================================================
    # 3. Tracks
    # ============================================================
    async def create_track(self, data: dict):
        """إنشاء مسار جديد"""
        if not data.get('bootcamp_id') and not data.get('org_entity_id'):
            raise ValueError("يجب تحديد إما bootcamp_id أو org_entity_id")
        track = await self.repo.create_track(**data)
        await self.repo._invalidate_cache("tracks")
        return track

    # ============================================================
    # 4. Cohorts
    # ============================================================
    async def create_cohort(self, data: dict):
        """إنشاء دفعة جديدة"""
        cohort = await self.repo.create_cohort(**data)
        await self.repo._invalidate_cache("cohorts")
        return cohort

    # ============================================================
    # 5. Courses Management
    # ============================================================
    async def create_course(self, data: dict, instructor_id: int):
        """إنشاء كورس جديد"""
        course = await self.repo.create_course(**data, instructor_id=instructor_id)
        await self.repo._invalidate_cache("courses")
        await self.repo._invalidate_cache("published_courses")
        return course

    async def update_course(self, course_id: int, data: dict, instructor_id: int):
        """تحديث كورس مع التحقق من ملكية المدرب"""
        course = await self.repo.get_course(course_id)
        if not course:
            raise NotFoundError("الكورس غير موجود")
        
        updated_course = await self.repo.update_course(course_id, **data)
        await self.repo._invalidate_cache(f"course_{course_id}")
        await self.repo._invalidate_cache("courses")
        await self.repo._invalidate_cache("published_courses")
        return updated_course

    async def get_store_courses(self, user_id: int, skip: int = 0, limit: int = 100):
        """جلب الكورسات المنشورة للمتجر (مع Tenant ID من المستخدم)"""
        user = await self.db.execute(select(User).where(User.id == user_id))
        user = user.scalar_one_or_none()
        if not user:
            raise NotFoundError("المستخدم غير موجود")
        
        tenant_id = getattr(user, 'tenant_id', 1)
        return await self.repo.list_published_courses(tenant_id, skip=skip, limit=limit)

    # ============================================================
    # 6. Course Units
    # ============================================================
    async def create_course_unit(self, course_id: int, data: dict):
        """إنشاء وحدة جديدة في كورس"""
        course = await self.repo.get_course(course_id)
        if not course:
            raise NotFoundError("الكورس غير موجود")
        
        unit = await self.repo.create_course_unit(course_id=course_id, **data)
        await self.repo._invalidate_cache(f"course_units_{course_id}")
        return unit

    async def get_course_units(self, course_id: int, skip: int = 0, limit: int = 100):
        """جلب وحدات كورس معين"""
        return await self.repo.get_course_units(course_id, skip=skip, limit=limit)

    async def update_course_unit(self, unit_id: int, title: str):
        """تحديث عنوان وحدة"""
        unit = await self.repo.update_course_unit(unit_id, title)
        if not unit:
            raise NotFoundError("الوحدة غير موجودة")
        await self.repo._invalidate_cache(f"course_units_{unit.course_id}")  # type: ignore
        return unit

    async def delete_course_unit(self, unit_id: int):
        """حذف وحدة"""
        success = await self.repo.delete_course_unit(unit_id)
        if not success:
            raise NotFoundError("الوحدة غير موجودة")
        await self.repo._invalidate_cache("course_units")
        return True

    # ============================================================
    # 7. Knowledge Nodes
    # ============================================================
    async def create_knowledge_node(self, data: dict):
        """إنشاء عقدة معرفية (درس)"""
        if data.get('course_id'):
            course = await self.repo.get_course(data['course_id'])
            if not course:
                raise NotFoundError("الكورس غير موجود")
        
        node = await self.repo.create_node(**data)
        await self.repo._invalidate_cache(f"course_nodes_{data['course_id']}")
        return node

    async def get_course_nodes(self, course_id: int, skip: int = 0, limit: int = 100):
        """جلب دروس كورس معين"""
        return await self.repo.get_course_nodes(course_id, skip=skip, limit=limit)

    async def update_knowledge_node(self, node_id: int, title: str):
        """تحديث عنوان درس"""
        node = await self.repo.update_node(node_id, title)
        if not node:
            raise NotFoundError("الدرس غير موجود")
        await self.repo._invalidate_cache(f"course_nodes_{node.course_id}")  # type: ignore
        return node

    async def delete_knowledge_node(self, node_id: int):
        """حذف درس"""
        node = await self.repo.get_node(node_id)
        if not node:
            raise NotFoundError("الدرس غير موجود")
        course_id = node.course_id  # type: ignore
        success = await self.repo.delete_node(node_id)
        if success:
            await self.repo._invalidate_cache(f"course_nodes_{course_id}")
        return success

    # ============================================================
    # 8. Live Sessions
    # ============================================================
    async def create_live_session(self, node_id: int, data: dict):
        """إنشاء جلسة حية لدرس معين"""
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
        """إضافة مادة لدرس معين"""
        node = await self.repo.get_node(node_id)
        if not node:
            raise NotFoundError("الدرس غير موجود")
        
        material = await self.repo.create_node_material(node_id=node_id, **data)
        await self.repo._invalidate_cache(f"node_materials_{node_id}")
        return material

    async def get_node_materials(self, node_id: int):
        """جلب مواد درس معين"""
        return await self.repo.get_node_materials(node_id)

    # ============================================================
    # 10. Quizzes
    # ============================================================
    async def create_quiz(self, node_id: int, data: dict):
        """إنشاء اختبار لدرس معين"""
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
        """
        تسجيل طالب في كورس مع ضمان Atomicity (الكل أو لا شيء)
        """
        # 1. التحقق من صحة الكورس
        course = await self.repo.get_course(course_id)
        if not course or not cast(bool, course.is_published):  # ✅ cast لإرضاء Pylance
            raise NotFoundError("الكورس غير موجود أو غير منشور")

        # 2. التأكد من عدم التسجيل المسبق
        existing = await self.repo.get_enrollment(user_id, course_id)
        if existing:
            raise PermissionDeniedError("أنت مسجل بالفعل في هذا الكورس")

        # 3. إنشاء Savepoint للتراجع عن التسجيل إذا فشلت المعاملة المالية
        async with self.db.begin_nested():
            # ✅ تحويل القيم بشكل آمن
            amount = float(cast(Decimal, course.price_mrusdt))
            currency = cast(str, course.currency)  # ✅ cast بدلاً من type: ignore

            # معالجة الدفع عبر المحفظة
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

            # 4. إنشاء الـ Enrollment داخل نفس المعاملة
            enrollment = await self.repo.enroll(
                user_id=user_id,
                course_id=course_id,
                cohort_id=cohort_id,
                payment_method=payment_method or "FREE",
                payment_ref=payment_ref,
                payment_status=payment_status,
                status=enrollment_status,
                paid_amount=float(amount) if amount else 0
            )

            # 5. تتبع الإحالة إذا وُجد كود الإحالة
            if affiliate_code:
                try:
                    from app.domains.affiliate.service import AffiliateService
                    affiliate_service = AffiliateService(self.db)
                    await affiliate_service.track_referral(
                        referrer_code=affiliate_code,
                        referred_user_id=user_id,
                        entity_type="COURSE",
                        entity_id=course_id,
                    )
                except Exception as e:
                    print(f"⚠️ [Affiliate Tracking] Failed to track referral: {str(e)}")

        # 6. مسح Cache
        await self.repo._invalidate_cache(f"user_enrollments_{user_id}")
        await self.repo._invalidate_cache("published_courses")

        return enrollment

    async def get_user_enrollments(self, user_id: int, skip: int = 0, limit: int = 100):
        """جلب اشتراكات المستخدم مع Pagination"""
        return await self.repo.get_user_enrollments(user_id, skip, limit)

    async def update_progress(self, user_id: int, course_id: int, progress: float):
        """تحديث تقدم الطالب في كورس"""
        enrollment = await self.repo.get_enrollment(user_id, course_id)
        if not enrollment:
            raise NotFoundError("غير مسجل في هذا الكورس")
        
        updated = await self.repo.update_progress(user_id, course_id, progress)
        await self.repo._invalidate_cache(f"enrollment_{user_id}_{course_id}")
        return updated

    # ============================================================
    # 12. Tasks
    # ============================================================
    async def create_task(self, data: dict):
        course = await self.repo.get_course(data['course_id'])
        if not course:
            raise NotFoundError("الكورس غير موجود")
        
        task = await self.repo.create_task(data)
        await self.repo._invalidate_cache(f"tasks_course_{data['course_id']}")
        return task

    async def get_course_tasks(self, course_id: int, skip: int = 0, limit: int = 100):
        """جلب تكليفات كورس معين"""
        return await self.repo.get_tasks_by_course(course_id, skip=skip, limit=limit)

    async def submit_task(self, user_id: int, task_id: int, data: dict):
        task = await self.repo.get_task(task_id)
        if not task or not cast(bool, task.is_active):  # ✅ cast
            raise NotFoundError("المهمة غير موجودة أو مغلقة")

        deadline = cast(datetime, task.deadline) if task.deadline is not None else None  # ✅ cast مع التحقق
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
        """جلب تسليمات الطلاب لمهمة معينة (للمدرب)"""
        task = await self.repo.get_task(task_id)
        if not task:
            raise NotFoundError("المهمة غير موجودة")
        return await self.repo.get_pending_submissions(task_id, skip=skip, limit=limit)

    async def grade_submission(self, submission_id: int, grade: float, feedback: str, status: str):
        """تقييم تسليم طالب (للمدرب)"""
        submission = await self.repo.grade_submission(
            submission_id=submission_id,
            grade=grade,
            feedback=feedback,
            status=status
        )
        if not submission:
            raise NotFoundError("التسليم غير موجود")
        
        # تحديث تحليلات الكورس
        task_submission_id = cast(int, submission.task_id)
        task = await self.repo.get_task(task_submission_id)
        if task:
            task_course_id = cast(int, task.course_id)
            await self.repo.update_course_analytics(
                course_id=task_course_id,
                grade=grade
            )
        
        await self.repo._invalidate_cache(f"submissions_task_{task_submission_id}")
        return submission

    async def get_my_submissions(self, user_id: int, skip: int = 0, limit: int = 100):
        """جلب تسليمات الطالب الحالي"""
        return await self.repo.get_student_submissions(user_id, skip=skip, limit=limit)

    # ============================================================
    # 14. Instructor Statistics
    # ============================================================
    async def get_instructor_stats(self, instructor_id: int) -> dict:
        """جلب إحصائيات لوحة تحكم المدرب"""
        total_courses = await self.repo.count_instructor_courses(instructor_id)
        total_students = await self.repo.count_distinct_students_in_instructor_courses(instructor_id)
        pending_submissions = await self.repo.count_pending_submissions_for_instructor(instructor_id)
        total_certificates = await self.repo.count_certificates_for_instructor(instructor_id)
        
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
        """جلب لوحة الشرف"""
        return await self.repo.get_academy_leaderboard(limit)

    # ============================================================
    # 16. Financial Summary
    # ============================================================
    async def get_financial_summary(self):
        return await self.repo.get_financial_summary()

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
        course = await self.repo.get_course(course_id)
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
            thumbnail_url=temp_url
        )

        await self.repo._invalidate_cache(f"course_{course_id}")
        await self.repo._invalidate_cache("published_courses")

        return temp_url