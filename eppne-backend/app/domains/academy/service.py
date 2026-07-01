# app/domains/academy/service.py
import io
import mimetypes
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import BackgroundTasks, HTTPException

from app.domains.academy.repository import AcademyRepository
from app.domains.finance.service import FinanceService
from app.core.errors import PermissionDeniedError, NotFoundError, InsufficientBalanceError
from app.core.storage import minio_client, ensure_bucket_exists
from app.core.ai_engine import analyze_and_recommend_courses
from app.domains.academy.models import Course, Enrollment

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
            # تشغيل عملية الرفع المتزامنة (MinIO SDK) في Thread منفصل لتجنب حظر الـ Event Loop
            def sync_upload():
                file_stream = io.BytesIO(file_content)
                minio_client.put_object(
                    bucket_name=bucket,
                    object_name=object_name,
                    data=file_stream,
                    length=len(file_content),
                    content_type=content_type
                )
            
            # تنفيذ الرفع في ThreadPoolExecutor (غير حاصر)
            await asyncio.to_thread(sync_upload)
            
            # بعد الرفع، يمكن تحديث قاعدة البيانات برابط الملف (سيكون هذا مسؤولية الدالة المستدعية)
            # أو يمكننا إرجاع URL وإضافته في الـ Service الرئيسي.
            return True
        except Exception as e:
            # تسجيل الخطأ (سنضيف Sentry لاحقاً)
            print(f"⚠️ [Background Upload] Failed to upload {object_name}: {str(e)}")
            return False

    # ============================================================
    # 1. Tenants & Org Entities
    # ============================================================
    async def create_tenant(self, name: str, domain: str, admin_id: int, branding: dict = None):
        return await self.repo.create_tenant(
            name=name, domain=domain, admin_id=admin_id, branding=branding or {}
        )

    async def create_org_entity(
        self,
        tenant_id: int,
        name: str,
        entity_type: str,
        parent_id: int = None,
        description: str = None
    ):
        return await self.repo.create_org_entity(
            tenant_id=tenant_id,
            name=name,
            entity_type=entity_type,
            parent_id=parent_id,
            description=description
        )

    # ============================================================
    # 2. Tasks System (مع تحسين Cache)
    # ============================================================
    async def create_task(self, data: dict):
        # التحقق من وجود الكورس
        course = await self.repo.get_course(data['course_id'])
        if not course:
            raise NotFoundError("الكورس غير موجود")
        
        task = await self.repo.create_task(data)
        # 🔥 مسح Cache الخاص بتكليفات هذا الكورس
        await self.repo._invalidate_cache(f"tasks_course_{data['course_id']}")
        return task

    async def submit_task(self, user_id: int, task_id: int, data: dict):
        task = await self.repo.get_task(task_id)
        if not task or not task.is_active:
            raise NotFoundError("المهمة غير موجودة أو مغلقة")

        # التحقق من الموعد النهائي مع Timezone الآمن
        if task.deadline and task.deadline < datetime.now(timezone.utc):
            raise PermissionDeniedError("انتهى وقت تسليم هذه المهمة")

        submission = await self.repo.submit_task(
            user_id=user_id,
            task_id=task_id,
            **data
        )
        # 🔥 مسح Cache الخاص بتسليمات هذه المهمة
        await self.repo._invalidate_cache(f"submissions_task_{task_id}")
        return submission

    # ============================================================
    # 3. Courses & Enrollment (مع Atomic Transactions)
    # ============================================================
    async def enroll_in_course(
        self,
        user_id: int,
        course_id: int,
        payment_method: str,
        payment_ref: str = None,
        cohort_id: Optional[int] = None,
        affiliate_code: Optional[str] = None,  # ✅ إضافة معامل كود الإحالة
    ):
        """
        تسجيل طالب في كورس مع ضمان Atomicity (الكل أو لا شيء)
        باستخدام Savepoint لضمان التراجع عن التسجيل إذا فشل الخصم المالي.
        """
        # 1. التحقق من صحة الكورس
        course = await self.repo.get_course(course_id)
        if not course or not course.is_published:
            raise NotFoundError("الكورس غير موجود أو غير منشور")

        # 2. التأكد من عدم التسجيل المسبق
        existing = await self.repo.get_enrollment(user_id, course_id)
        if existing:
            raise PermissionDeniedError("أنت مسجل بالفعل في هذا الكورس")

        # 3. إنشاء Savepoint للتراجع عن التسجيل إذا فشلت المعاملة المالية
        async with self.db.begin_nested():
            # تحديد المبلغ والعملة
            amount = course.price_mrusdt
            currency = course.currency

            # معالجة الدفع عبر المحفظة (إذا كان المبلغ > 0 وليست مجانية)
            if payment_method == "WALLET" and amount > 0 and not course.is_free:
                try:
                    await self.finance.transfer(
                        sender_id=user_id,
                        receiver_email="academy@eppne.com",
                        currency=currency,
                        amount=Decimal(str(amount)),
                        notes=f"Enrollment in course {course.id} - {course.title}"
                    )
                    payment_status = "COMPLETED"
                    enrollment_status = "ACTIVE"
                except InsufficientBalanceError as e:
                    # إذا فشل الخصم، نرفع استثناء ونتراجع عن Savepoint تلقائياً
                    raise PermissionDeniedError(f"رصيد غير كافٍ: {str(e)}")
                except Exception as e:
                    # أي خطأ مالي آخر
                    raise PermissionDeniedError(f"فشل المعاملة المالية: {str(e)}")
            else:
                # الكورس مجاني أو الدفع غير متاح حالياً (سيُكمل لاحقاً)
                payment_status = "COMPLETED" if course.is_free or amount == 0 else "PENDING"
                enrollment_status = "ACTIVE" if course.is_free or amount == 0 else "PENDING"

            # 4. إنشاء الـ Enrollment داخل نفس المعاملة
            enrollment = await self.repo.enroll(
                user_id=user_id,
                course_id=course_id,
                cohort_id=cohort_id,
                payment_method=payment_method,
                payment_ref=payment_ref,
                payment_status=payment_status,
                status=enrollment_status,
                paid_amount=float(amount) if amount else 0
            )

            # ✅ 5. تتبع الإحالة إذا وُجد كود الإحالة
            if affiliate_code:
                try:
                    # استيراد AffiliateService ديناميكياً لتجنب Circular Import
                    from app.domains.affiliate.service import AffiliateService
                    affiliate_service = AffiliateService(self.db)
                    await affiliate_service.track_referral(
                        referrer_code=affiliate_code,
                        referred_user_id=user_id,
                        entity_type="COURSE",
                        entity_id=course_id,
                    )
                except Exception as e:
                    # نكتفي بتسجيل الخطأ ولا نعطل عملية التسجيل الأساسية
                    # يمكن إضافة تسجيل إلى Sentry أو نظام مراقبة
                    print(f"⚠️ [Affiliate Tracking] Failed to track referral: {str(e)}")

        # 6. 🔥 مسح Cache الخاص باشتراكات المستخدم والكورسات المنشورة
        await self.repo._invalidate_cache(f"user_enrollments_{user_id}")
        await self.repo._invalidate_cache("published_courses")

        return enrollment

    async def get_user_enrollments(self, user_id: int, skip: int = 0, limit: int = 100):
        """جلب اشتراكات المستخدم مع Pagination"""
        return await self.repo.get_user_enrollments(user_id, skip, limit)

    # ============================================================
    # 4. 🚀 File Upload (غير متزامن بالكامل مع BackgroundTasks)
    # ============================================================
    async def upload_course_thumbnail(
        self,
        course_id: int,
        file_content: bytes,
        filename: str,
        background_tasks: BackgroundTasks
    ) -> str:
        """
        رفع صورة مصغرة للكورس باستخدام BackgroundTask حتى لا نحجب الطلب.
        ستعود الدالة فوراً برابط مؤقت، وسيتم الرفع الفعلي في الخلفية.
        """
        # 1. التأكد من وجود الكورس
        course = await self.repo.get_course(course_id)
        if not course:
            raise NotFoundError("الكورس غير موجود")

        # 2. تجهيز البيانات
        bucket = "academy-thumbnails"
        ensure_bucket_exists(bucket)
        content_type, _ = mimetypes.guess_type(filename)
        content_type = content_type or "application/octet-stream"

        # توليد اسم فريد للملف لمنع التكرار
        file_ext = filename.split('.')[-1] if '.' in filename else 'jpg'
        unique_name = f"{uuid.uuid4().hex}.{file_ext}"
        object_name = f"courses/{course_id}/thumb_{unique_name}"

        # 3. رابط مؤقت يعكس المسار المتوقع (سيتم التحديث لاحقاً)
        temp_url = f"http://localhost:9000/{bucket}/{object_name}"

        # 4. إضافة مهمة الرفع إلى الخلفية (غير حاصر)
        background_tasks.add_task(
            self._upload_file_to_minio,
            bucket=bucket,
            object_name=object_name,
            file_content=file_content,
            content_type=content_type
        )

        # 5. تحديث الكورس بالرابط الجديد (حتى لو لم يُرفع بعد، الرابط سيكون صحيحاً)
        # نضع الرابط فوراً، والمستخدم سيرى الصورة بعد رفعها في الخلفية (تحديث الصفحة)
        # أو يمكننا الانتظار حتى ينتهي الرفع، لكننا نفضل الأسلوب غير المتزامن.
        # نقوم بتحديث الـ thumbnail_url فوراً لتجنب استدعاء تحديث منفصل.
        updated_course = await self.repo.update_course(
            course_id,
            thumbnail_url=temp_url
        )

        # 🔥 مسح Cache الخاص بالكورس بعد التحديث
        await self.repo._invalidate_cache(f"course_{course_id}")
        await self.repo._invalidate_cache("published_courses")

        return temp_url

    # ============================================================
    # 5. دوال إضافية (التحليلات، التوأم الرقمي، إلخ)
    # ============================================================
    async def get_or_create_digital_twin(self, user_id: int):
        return await self.repo.get_or_create_digital_twin(user_id)

    async def create_camera_analysis(self, **kwargs):
        return await self.repo.create_camera_analysis(**kwargs)

    async def get_financial_summary(self):
        return await self.repo.get_financial_summary()

    async def get_academy_leaderboard(self, limit: int = 10):
        return await self.repo.get_academy_leaderboard(limit)

    async def update_course_analytics(
        self,
        course_id: int,
        increment_enrollments: bool = False,
        increment_completions: bool = False,
        grade: float = None,
        revenue: float = None
    ):
        return await self.repo.update_course_analytics(
            course_id=course_id,
            increment_enrollments=increment_enrollments,
            increment_completions=increment_completions,
            grade=grade,
            revenue=revenue
        )