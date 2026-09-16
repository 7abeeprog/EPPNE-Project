# app/domains/guardian/service.py
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.domains.guardian.repository import GuardianRepository
from app.domains.guardian.models import (
    GuardianRelationship, GuardianVisibilitySetting,
    GuardianRelationshipType, GuardianRelationshipStatus, GuardianVisibilitySector,
)
from app.domains.identity.repository import UserRepository
from app.domains.identity.models import User
from app.domains.communications.service import CommunicationsService
from app.domains.communications.models import NotificationPriority, NotificationChannel, Notification
from app.domains.academy.service import AcademyService
from app.domains.academy.repository import AcademyRepository
from app.domains.achievements.service import AchievementService
from app.domains.social.service import SocialService
from app.domains.transport.service import TransportService
from app.domains.health.service import HealthService
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError, AlreadyExistsError

# نفس نطاق الأدوار المقبول في core/security.get_current_superuser بالحرف
# (SUPER_ADMIN/EXECUTIVE_DIRECTOR فقط، بدون ADMIN العادي) — راجع
# .claude/reports/guardian-flow-implementation-planning-session-log.md §1.
ADMIN_ROLES: List[str] = ["SUPER_ADMIN", "EXECUTIVE_DIRECTOR"]

MINOR_AGE_THRESHOLD = 18


def _calculate_age(birth_date: date, as_of: Optional[date] = None) -> int:
    as_of = as_of or date.today()
    return as_of.year - birth_date.year - ((as_of.month, as_of.day) < (birth_date.month, birth_date.day))


class GuardianService:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = GuardianRepository(db)
        self.user_repo = UserRepository(db)

    # ============================================================
    # 1. البحث عن مستخدم بتطابق تام (GET /guardian/find-user)
    # ============================================================

    async def find_user(self, email: Optional[str], username: Optional[str]) -> User:
        if bool(email) == bool(username):
            raise ValidationError("مطلوب إما email أو username، واحد بس")
        user = (
            await self.user_repo.get_by_email(email, self.tenant_id)
            if email
            else await self.user_repo.get_by_username(username, self.tenant_id)  # type: ignore[arg-type]
        )
        if not user:
            raise NotFoundError("المستخدم غير موجود")
        return user

    # ============================================================
    # 2. إنشاء طلب الربط (POST /guardian/relationships) — ولي الأمر
    # ============================================================

    async def create_relationship_request(
        self,
        guardian_user_id: int,
        ward_user_id: int,
        relationship_type: GuardianRelationshipType,
    ) -> GuardianRelationship:
        if guardian_user_id == ward_user_id:
            raise ValidationError("لا يمكن أن يكون المستخدم ولي أمر نفسه")

        ward = await self.user_repo.get_by_id(ward_user_id, self.tenant_id)
        if not ward:
            raise NotFoundError("الطالب المطلوب غير موجود")

        existing = await self.repo.get_relationship_by_guardian_and_ward(guardian_user_id, ward_user_id)
        if existing:
            raise AlreadyExistsError("يوجد بالفعل طلب/علاقة بين هذين المستخدمين")

        try:
            relationship = await self.repo.create_relationship(
                tenant_id=self.tenant_id,
                guardian_user_id=guardian_user_id,
                ward_user_id=ward_user_id,
                relationship_type=relationship_type,
                initiated_by_user_id=guardian_user_id,
                status=GuardianRelationshipStatus.PENDING_WARD_APPROVAL,
            )
            await self.db.commit()
        except IntegrityError:
            # سباق نظري بين الـpre-check فوق والـcommit هنا — القيد الفريد
            # uq_guardian_ward هو الحارس النهائي، نفس نمط achievements.
            await self.db.rollback()
            raise AlreadyExistsError("يوجد بالفعل طلب/علاقة بين هذين المستخدمين")

        return relationship

    # ============================================================
    # 3. موافقة الطالب (POST /guardian/relationships/{id}/approve)
    # ============================================================

    async def approve_relationship(
        self,
        relationship_id: int,
        ward_user_id: int,
        ward_birth_date_provided: date,
    ) -> GuardianRelationship:
        relationship = await self.repo.get_relationship(relationship_id, self.tenant_id)
        if not relationship:
            raise NotFoundError("طلب الربط غير موجود")
        if relationship.ward_user_id != ward_user_id:  # type: ignore[comparison-overlap]
            raise PermissionDeniedError("هذا الطلب غير موجَّه لهذا المستخدم")
        if relationship.status != GuardianRelationshipStatus.PENDING_WARD_APPROVAL:
            raise ValidationError("تمت معالجة هذا الطلب بالفعل")

        # إدخال مرفوض = تاريخ ميلاد في المستقبل (غير منطقي) — نعتبره غير
        # موثوق ونحوّله لمراجعة إدارية بدل رفضه بخطأ 4xx صريح، بالحرف
        # حسب طلب المستخدم ("رفض الإدخال → PENDING_ADMIN_REVIEW").
        input_is_valid = ward_birth_date_provided <= date.today()
        age = _calculate_age(ward_birth_date_provided) if input_is_valid else None

        if input_is_valid and age is not None and age >= MINOR_AGE_THRESHOLD:
            updated = await self.repo.update_relationship(
                relationship_id,
                self.tenant_id,
                ward_birth_date_provided=ward_birth_date_provided,
                status=GuardianRelationshipStatus.VERIFIED,
                verified_at=datetime.now(timezone.utc),
            )
            await self.db.commit()
            await self._ensure_default_visibility_settings(relationship_id)
            return updated  # type: ignore[return-value]

        updated = await self.repo.update_relationship(
            relationship_id,
            self.tenant_id,
            ward_birth_date_provided=ward_birth_date_provided,
            status=GuardianRelationshipStatus.PENDING_ADMIN_REVIEW,
        )
        await self.db.commit()
        await self._notify_admins_pending_review(updated)  # type: ignore[arg-type]
        return updated  # type: ignore[return-value]

    # ============================================================
    # 4. رفض الطالب (POST /guardian/relationships/{id}/reject)
    # ============================================================

    async def reject_relationship(
        self,
        relationship_id: int,
        ward_user_id: int,
        rejection_reason: Optional[str],
    ) -> GuardianRelationship:
        relationship = await self.repo.get_relationship(relationship_id, self.tenant_id)
        if not relationship:
            raise NotFoundError("طلب الربط غير موجود")
        if relationship.ward_user_id != ward_user_id:  # type: ignore[comparison-overlap]
            raise PermissionDeniedError("هذا الطلب غير موجَّه لهذا المستخدم")
        if relationship.status != GuardianRelationshipStatus.PENDING_WARD_APPROVAL:
            raise ValidationError("تمت معالجة هذا الطلب بالفعل")

        updated = await self.repo.update_relationship(
            relationship_id,
            self.tenant_id,
            status=GuardianRelationshipStatus.REJECTED,
            rejection_reason=rejection_reason,
        )
        await self.db.commit()
        return updated  # type: ignore[return-value]

    # ============================================================
    # 5. مراجعة الأدمن (PUT /guardian/relationships/{id}/review)
    # ============================================================

    async def review_relationship(
        self,
        relationship_id: int,
        admin_id: int,
        status: GuardianRelationshipStatus,
        rejection_reason: Optional[str],
    ) -> GuardianRelationship:
        relationship = await self.repo.get_relationship(relationship_id, self.tenant_id)
        if not relationship:
            raise NotFoundError("طلب الربط غير موجود")
        if relationship.status != GuardianRelationshipStatus.PENDING_ADMIN_REVIEW:
            raise ValidationError("هذا الطلب ليس بانتظار مراجعة إدارية")
        if status == GuardianRelationshipStatus.REJECTED and not rejection_reason:
            raise ValidationError("سبب الرفض مطلوب")

        updated = await self.repo.update_relationship(
            relationship_id,
            self.tenant_id,
            status=status,
            verified_by=admin_id,
            verified_at=datetime.now(timezone.utc),
            rejection_reason=rejection_reason if status == GuardianRelationshipStatus.REJECTED else None,
        )
        await self.db.commit()

        if status == GuardianRelationshipStatus.VERIFIED:
            await self._ensure_default_visibility_settings(relationship_id)

        return updated  # type: ignore[return-value]

    # ============================================================
    # 6. تحكّم الطالب في الرؤية (PUT /guardian/relationships/{id}/visibility)
    # ============================================================

    async def update_visibility(
        self,
        relationship_id: int,
        ward_user_id: int,
        settings: List[dict],
    ) -> List[GuardianVisibilitySetting]:
        relationship = await self.repo.get_relationship(relationship_id, self.tenant_id)
        if not relationship:
            raise NotFoundError("العلاقة غير موجودة")
        if relationship.ward_user_id != ward_user_id:  # type: ignore[comparison-overlap]
            raise PermissionDeniedError("هذه العلاقة غير موجَّهة لهذا المستخدم")
        if relationship.status != GuardianRelationshipStatus.VERIFIED:
            raise ValidationError("العلاقة غير مُفعَّلة بعد — لا يمكن التحكم في الرؤية قبل VERIFIED")

        for item in settings:
            await self.repo.upsert_visibility_setting(
                guardian_relationship_id=relationship_id,
                sector=item["sector"],
                is_visible=item["is_visible"],
            )
        await self.db.commit()

        return await self.repo.list_visibility_settings(relationship_id)

    # ============================================================
    # 7. نظرة عامة موحَّدة على الطالب (GET /guardian/wards/{ward_id}/overview)
    # ============================================================

    async def get_ward_overview(self, guardian_user_id: int, ward_user_id: int) -> Dict[str, Any]:
        """يجمّع ملخصات خفيفة من 4 دومينات لولي أمر مُوثَّق. أهم فحص هنا:
        علاقة VERIFIED فعلية بين guardian_user_id وward_user_id في نفس
        الـtenant — أي حالة تانية (PENDING_*, REJECTED) أو غياب العلاقة
        بالكامل يترفض بـ403. استدعاء تسلسلي بحت (بلا asyncio.gather) —
        كل الدومينات بتشارك نفس `self.db` المُحقَنة، وgather عليها خطر
        حقيقي (راجع
        .claude/reports/guardian-overview-endpoint-planning-session-log.md §6)."""
        relationship = await self.repo.get_relationship_by_guardian_and_ward(guardian_user_id, ward_user_id)
        if (
            not relationship
            or relationship.tenant_id != self.tenant_id  # type: ignore[comparison-overlap]
            or relationship.status != GuardianRelationshipStatus.VERIFIED
        ):
            raise PermissionDeniedError("لا توجد علاقة ولاية موثَّقة (VERIFIED) لهذا الطالب")

        settings = await self.repo.list_visibility_settings(relationship.id)
        # صف مفقود لقطاع = غير محجوب صراحةً (الافتراضي is_visible=True على
        # مستوى العمود نفسه) — يُستبعد القسم فقط لو فيه صف صريح is_visible=False.
        hidden_sectors = {s.sector for s in settings if not s.is_visible}

        overview: Dict[str, Any] = {"ward_id": ward_user_id}

        if GuardianVisibilitySector.ACADEMY not in hidden_sectors:
            overview["academy"] = await self._build_academy_summary(ward_user_id)
        if GuardianVisibilitySector.SOCIAL not in hidden_sectors:
            overview["social"] = await self._build_social_summary(ward_user_id)
        if GuardianVisibilitySector.TRANSPORT not in hidden_sectors:
            overview["transport"] = await self._build_transport_summary(ward_user_id)
        if GuardianVisibilitySector.HEALTH not in hidden_sectors:
            overview["health"] = await self._build_health_summary(ward_user_id)

        return overview

    async def _build_academy_summary(self, ward_user_id: int) -> Dict[str, Any]:
        academy_service = AcademyService(self.db, self.tenant_id)
        enrollment_rows = await academy_service.get_user_enrollments_summary(ward_user_id, skip=0, limit=10)
        enrollments = [
            {
                "course_title": row.title,
                "progress_percentage": float(row.progress_percentage) if row.progress_percentage is not None else 0.0,
                "is_completed": row.is_completed,
                "status": row.status,
            }
            for row in enrollment_rows
        ]

        achievement_service = AchievementService(self.db, self.tenant_id)
        user_achievements = await achievement_service.get_user_achievements(ward_user_id)
        # استعلام واحد لكل تعريفات الإنجازات النشطة بالـtenant (مش N استعلام
        # منفصل لكل إنجاز) — get_user_achievements بترجع achievement_definition_id
        # خام بس، بلا اسم/أيقونة (راجع تقرير التخطيط §1).
        definitions_by_id = {d.id: d for d in await achievement_service.list_definitions(limit=1000)}
        achievements = [
            {
                "name": definitions_by_id[ua.achievement_definition_id].name
                if ua.achievement_definition_id in definitions_by_id else None,
                "icon_url": definitions_by_id[ua.achievement_definition_id].icon_url
                if ua.achievement_definition_id in definitions_by_id else None,
                "granted_at": ua.granted_at,
            }
            for ua in user_achievements
        ]

        return {"enrollments": enrollments, "achievements": achievements}

    async def _build_social_summary(self, ward_user_id: int) -> Dict[str, Any]:
        social_service = SocialService(self.db)
        return await social_service.get_user_activity_summary(ward_user_id, self.tenant_id)

    async def _build_transport_summary(self, ward_user_id: int) -> List[Dict[str, Any]]:
        transport_service = TransportService(self.db)
        # ملحوظة: `list_bookings` مش `get_my_bookings` عمدًا — الاتنين
        # بينفذوا نفس استعلام repo.list_bookings بالحرف، لكن
        # `get_my_bookings` بتضيف فوقها `_check_saas_limits(tenant_id,
        # "transport")` (بوابة اشتراك SaaS للـtenant ككل، لا علاقة لها
        # بتفويض ولي الأمر نفسه). استخدامها كانت هتخلي overview الطالب
        # يفشل بالكامل لأي tenant مالوش خطة "transport" مفعَّلة — قيد
        # بيئي/اشتراكي منفصل تمامًا عن منطق guardian. راجع
        # .claude/reports/guardian-overview-endpoint-implementation-session-log.md
        bookings = await transport_service.list_bookings(self.tenant_id, passenger_id=ward_user_id)
        return [
            {
                "trip_date": booking.trip.scheduled_start if booking.trip else None,  # type: ignore[attr-defined]
                "status": booking.status,
            }
            for booking in bookings
        ]

    async def _build_health_summary(self, ward_user_id: int) -> List[Dict[str, Any]]:
        health_service = HealthService(self.db)
        appointments = await health_service.get_my_appointments(ward_user_id, self.tenant_id)

        facility_cache: Dict[int, Optional[str]] = {}
        summary = []
        for appointment in appointments:
            facility_id = appointment.facility_id
            if facility_id not in facility_cache:
                facility = await health_service.get_facility(facility_id, self.tenant_id)
                facility_cache[facility_id] = facility.name if facility else None  # type: ignore[union-attr]
            summary.append({
                "appointment_date": appointment.appointment_time,
                "facility_name": facility_cache[facility_id],
                "status": appointment.status,
            })
        return summary

    # ============================================================
    # 8. مراسلة مدرّس (POST /guardian/wards/{ward_id}/message-instructor)
    # ============================================================

    async def message_instructor(
        self,
        guardian_user_id: int,
        ward_user_id: int,
        course_id: int,
        message_text: str,
    ) -> Notification:
        """يبعت رسالة لمدرّس كورس معيّن الطالب فعليًا مسجَّل فيه. نفس فحص
        `get_ward_overview` بالحرف (VERIFIED + tenant_id مطابق) + فحص
        رؤية إضافي خاص بهذه الميزة (ACADEMY لازم يكون مرئي — لو الطالب
        حجب قطاع الأكاديميا عن وليّ أمره، منطقيًا ميصحش يتواصل مع مدرّس
        عن كورس هو أصلًا ممنوع يشوف بياناته). راجع
        .claude/reports/guardian-message-instructor-planning-session-log.md."""
        relationship = await self.repo.get_relationship_by_guardian_and_ward(guardian_user_id, ward_user_id)
        if (
            not relationship
            or relationship.tenant_id != self.tenant_id  # type: ignore[comparison-overlap]
            or relationship.status != GuardianRelationshipStatus.VERIFIED
        ):
            raise PermissionDeniedError("لا توجد علاقة ولاية موثَّقة (VERIFIED) لهذا الطالب")

        settings = await self.repo.list_visibility_settings(relationship.id)
        academy_hidden = any(
            s.sector == GuardianVisibilitySector.ACADEMY and not s.is_visible for s in settings
        )
        if academy_hidden:
            raise PermissionDeniedError("قطاع الأكاديميا محجوب — لا يمكن التواصل مع مدرّس")

        academy_repo = AcademyRepository(self.db)
        enrollment = await academy_repo.get_enrollment(ward_user_id, course_id, self.tenant_id)
        if not enrollment:
            raise NotFoundError("الطالب غير مسجَّل في هذا الكورس")

        course = await academy_repo.get_course(course_id, self.tenant_id)
        if not course or course.instructor_id is None:
            raise NotFoundError("لا يوجد مدرّس مُسنَد لهذا الكورس")

        # ⚠️ استعلام معزول جوّه guardian/repository.py، مش
        # AcademyRepository.get_instructor() — الأخيرة بتفلتر/تختار
        # Instructor.tenant_id، وهذا العمود **غير موجود إطلاقًا** في جدول
        # academy_instructors الفعلي (انحراف موديل↔DB قديم، مؤكَّد حيًا
        # بالتجربة المباشرة: UndefinedColumnError فوري لأي استدعاء). الأمان
        # هنا محقَّق مسبقًا عبر Course.tenant_id فوق (get_course بالفعل
        # فلترت بالـtenant الصحيح)، مش محتاجين فلتر تاني على Instructor
        # نفسها. راجع بند backlog-academy-instructors-missing-tenant-id.
        instructor_user_id = await self.repo.get_instructor_user_id(course.instructor_id)  # type: ignore[arg-type]
        if not instructor_user_id:
            raise NotFoundError("لا يوجد مدرّس مُسنَد لهذا الكورس")

        comm_service = CommunicationsService(self.db)
        return await comm_service.send_notification(
            user_id=instructor_user_id,
            title="رسالة من ولي أمر أحد الطلاب",
            body=message_text,
            data={"course_id": course_id, "ward_id": ward_user_id, "guardian_id": guardian_user_id},
            channel=NotificationChannel.IN_APP,
            # قرار مقصود: idempotency_key=None (بلا مفتاح إطلاقًا) —
            # الرسائل مش عملية حساسة لإعادة محاولة (زي حجز/دفع) تحتاج
            # حماية من تكرار غير مقصود. send_notification بتتخطى فحص
            # الـidempotency بالكامل لو المفتاح None (راجع
            # communications/service.py:53-57) فبترجع صف Notification
            # جديد في كل نداء — بالحرف المطلوب: "كل رسالة لازم تتبعت"،
            # حتى لو نفس ولي الأمر بعت رسالتين متتاليتين بنفس النص لنفس
            # المدرّس عن نفس الكورس. أي مفتاح ثابت/timestamp-based كان
            # هيحمل خطر تخطي رسالة لاحقة بالغلط لو الوقت اتطابق أو
            # المفتاح اتكرر بأي شكل.
            idempotency_key=None,
        )

    # ============================================================
    # مساعدات داخلية
    # ============================================================

    async def _ensure_default_visibility_settings(self, relationship_id: int) -> None:
        """تُنشئ صف رؤية افتراضي (is_visible=True) لكل قطاع لو مش موجود
        بالفعل — تُستدعى فقط عند دخول العلاقة حالة VERIFIED (سواء عبر
        موافقة راشد أو مراجعة أدمن). upsert آمن للاستدعاء المتكرر."""
        for sector in GuardianVisibilitySector:
            await self.repo.upsert_visibility_setting(
                guardian_relationship_id=relationship_id,
                sector=sector,
                is_visible=True,
            )
        await self.db.commit()

    async def _notify_admins_pending_review(self, relationship: GuardianRelationship) -> None:
        """تنبيه كل أدمنز الـtenant (SUPER_ADMIN/EXECUTIVE_DIRECTOR) —
        نداء send_notification منفصل لكل أدمن (مفيش دعم لمستلمين متعددين
        في send_notification نفسها، راجع
        .claude/reports/guardian-flow-implementation-planning-session-log.md §4)."""
        admins = await self.user_repo.list_by_role(self.tenant_id, ADMIN_ROLES)
        comm_service = CommunicationsService(self.db)
        for admin in admins:
            await comm_service.send_notification(
                user_id=admin.id,  # type: ignore[arg-type]
                title="طلب ربط ولي أمر يحتاج مراجعة إدارية",
                body=f"طلب علاقة ولي أمر↔طالب رقم {relationship.id} يحتاج تحقق إداري (تاريخ ميلاد غير مؤكِّد أن الطالب راشد).",
                data={"guardian_relationship_id": relationship.id},
                priority=NotificationPriority.HIGH,
                channel=NotificationChannel.IN_APP,
                idempotency_key=f"GUARDIAN-ADMIN-REVIEW-{relationship.id}-{admin.id}",
            )
