from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any, cast
from datetime import datetime, timedelta, timezone
from app.domains.saas.schemas import TenantSubscriptionResponse, InvoiceResponse
from app.domains.saas.models import (
    ServiceCatalog,
    ServicePlan,
    TenantSubscription,
    TenantServiceAccess,
    Invoice,
    TenantFeatureFlag,
    PlanServiceAccess,
)
from app.core.errors import NotFoundError
from app.core.pagination import PaginatedResponse


class SaaSRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ==========================================
    # 1. الخدمات (Services)
    # ==========================================
    async def get_service_by_code(self, code: str) -> Optional[ServiceCatalog]:
        result = await self.db.execute(
            select(ServiceCatalog).where(ServiceCatalog.code == code)
        )
        return result.scalar_one_or_none()

    async def get_service_by_id(self, service_id: int) -> Optional[ServiceCatalog]:
        result = await self.db.execute(
            select(ServiceCatalog).where(ServiceCatalog.id == service_id)
        )
        return result.scalar_one_or_none()

    async def get_all_services(self, is_active: bool = True) -> List[ServiceCatalog]:
        query = select(ServiceCatalog)
        if is_active is not None:
            query = query.where(ServiceCatalog.is_active == is_active)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_service(self, **kwargs) -> ServiceCatalog:
        service = ServiceCatalog(**kwargs)
        self.db.add(service)
        await self.db.commit()
        await self.db.refresh(service)
        return service

    # ==========================================
    # 2. خطط التسعير (Plans)
    # ==========================================
    async def get_plan_by_id(self, plan_id: int, tenant_id: int) -> Optional[ServicePlan]:
        """جلب الخطة والتحقق من وجود اشتراك نشط لها للمستأجر."""
        result = await self.db.execute(
            select(TenantSubscription)
            .where(
                and_(
                    TenantSubscription.plan_id == plan_id,
                    TenantSubscription.tenant_id == tenant_id,
                    TenantSubscription.status.in_(["ACTIVE", "TRIAL"])
                )
            )
            .limit(1)
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return None
        # إذا وجد اشتراك، نجلب الخطة
        result_plan = await self.db.execute(
            select(ServicePlan).where(ServicePlan.id == plan_id)
        )
        return result_plan.scalar_one_or_none()

    async def get_plan_by_id_admin(self, plan_id: int) -> Optional[ServicePlan]:
        """جلب الخطة بدون التحقق من المستأجر (للمشرفين)."""
        result = await self.db.execute(
            select(ServicePlan).where(ServicePlan.id == plan_id)
        )
        return result.scalar_one_or_none()

    async def get_plan_by_code(self, service_id: int, code: str) -> Optional[ServicePlan]:
        result = await self.db.execute(
            select(ServicePlan).where(
                ServicePlan.service_id == service_id,
                ServicePlan.code == code
            )
        )
        return result.scalar_one_or_none()

    async def get_plans_by_service(self, service_id: int) -> List[ServicePlan]:
        result = await self.db.execute(
            select(ServicePlan).where(ServicePlan.service_id == service_id)
        )
        return list(result.scalars().all())

    async def create_plan(self, **kwargs) -> ServicePlan:
        plan = ServicePlan(**kwargs)
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    # ==========================================
    # 3. اشتراكات المستأجر (Subscriptions)
    # ==========================================
    async def get_subscription(self, subscription_id: int, tenant_id: int) -> Optional[TenantSubscription]:
        result = await self.db.execute(
            select(TenantSubscription)
            .options(selectinload(TenantSubscription.plan))
            .where(
                and_(
                    TenantSubscription.id == subscription_id,
                    TenantSubscription.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_trial_subscriptions(
        self,
        tenant_id: Optional[int] = None,
        expired_only: bool = False,
    ) -> List[TenantSubscription]:
        """كل اشتراكات TRIAL — بلا فلتر tenant_id افتراضيًا (عبر كل
        المستأجرين)، بنفس نمط get_past_due_subscriptions [2026-09-08].
        expired_only=True يضيف فلتر trial_end_date <= الآن (تُستخدَم من
        check_and_expire_trials). expired_only=False (الافتراضي) يحافظ
        على السلوك القديم بالضبط — لازم يفضل كده عشان
        _cancel_related_free_trials (academy/service.py) لسه محتاجة كل
        TRIAL بغض النظر عن تاريخ الانتهاء، مش بس المنتهية."""
        conditions = [TenantSubscription.status == "TRIAL"]
        if tenant_id is not None:
            conditions.append(TenantSubscription.tenant_id == tenant_id)
        if expired_only:
            conditions.append(TenantSubscription.trial_end_date.isnot(None))
            conditions.append(TenantSubscription.trial_end_date <= datetime.now(timezone.utc))

        result = await self.db.execute(
            select(TenantSubscription).where(and_(*conditions))
        )
        return list(result.scalars().all())

    async def get_active_subscription(
        self,
        tenant_id: int,
        service_id: int
    ) -> Optional[TenantSubscription]:
        result = await self.db.execute(
            select(TenantSubscription)
            .join(ServicePlan)
            .where(
                and_(
                    TenantSubscription.tenant_id == tenant_id,
                    ServicePlan.service_id == service_id,
                    TenantSubscription.status.in_(["ACTIVE", "TRIAL"])
                )
            )
            .order_by(TenantSubscription.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_active_subscription_via_plan_access(
        self,
        tenant_id: int,
        service_id: int,
    ) -> Optional[TenantSubscription]:
        """نفس شكل get_active_subscription بالضبط، لكن الربط بين
        الاشتراك والخدمة عبر saas_plan_service_access (many-to-many)
        بدل ServicePlan.service_id (FK وحيد). جزء من pilot دومين
        insurance فقط — راجع PROGRESS_LOG.md [2026-09-07].

        PAST_DUE مُضاف عمدًا لقائمة الحالات [2026-09-08] — عشان فرع
        فترة السماح في can_access_service (service.py) يبقى قابل
        للوصول فعليًا (كان ميتًا: الاستعلام هنا كان بيستبعد PAST_DUE
        فيرجع None قبل ما يوصل لفحص الفرع أصلًا). راجع
        .claude/reports/past-due-grace-period-notifications-investigation-session-log.md
        §1. get_active_subscription الشقيقة (تحت) عندها نفس القصور
        عمدًا لم تُلمَس هنا — خارج نطاق هذا التغيير."""
        result = await self.db.execute(
            select(TenantSubscription)
            .join(PlanServiceAccess, PlanServiceAccess.plan_id == TenantSubscription.plan_id)
            .where(
                and_(
                    TenantSubscription.tenant_id == tenant_id,
                    PlanServiceAccess.service_id == service_id,
                    TenantSubscription.status.in_(["ACTIVE", "TRIAL", "PAST_DUE"])
                )
            )
            .order_by(TenantSubscription.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_all_active_subscriptions(
        self,
        tenant_id: int,
    ) -> List[TenantSubscription]:
        """كل اشتراكات الـtenant النشطة/التجريبية عبر كل الخدمات — بديل
        get_any_active_subscription القديمة اللي كانت بترجع 'الأحدث زمنيًا'
        فقط (صف واحد) وبتكسر أي tenant عنده أكتر من اشتراك فعّال لخدمات
        مختلفة في نفس الوقت. تعدد الاشتراكات النشطة لنفس الـtenant حالة
        طبيعية ومتوقعة في هذا الـschema (كل خدمة ليها اشتراكها المستقل عبر
        saas_tenant_subscriptions.plan_id → saas_service_plans.service_id)
        — مش استثناء نادر لازم نتعامل معاه كـ'صف واحد بس'.

        ⚠️ تحذير للمستقبل: لو حد فكّر يرجّع لمنطق 'صف واحد بس' (مثلاً
        لتحسين أداء)، لازم يتأكد إن أي استخدام جديد بيفلتر بالخدمة/الميزة
        المطلوبة أولًا (زي get_active_subscription(tenant_id, service_id)
        الموجودة فعلًا تحت في نفس الملف) — مش يرجع لـ'أحدث اشتراك بغض النظر
        عن الخدمة'، وهو بالظبط الباج اللي بيتصلح هنا
        (raج §8 من saas-feature-flags-drift-session-log.md)."""
        result = await self.db.execute(
            select(TenantSubscription)
            .where(
                and_(
                    TenantSubscription.tenant_id == tenant_id,
                    TenantSubscription.status.in_(["ACTIVE", "TRIAL"])
                )
            )
        )
        return list(result.scalars().all())

    async def get_subscriptions_for_renewal(self, tenant_id: Optional[int] = None) -> List[TenantSubscription]:
        now = datetime.now(timezone.utc)
        query = select(TenantSubscription).where(
            and_(
                TenantSubscription.status == "ACTIVE",
                TenantSubscription.auto_renew == True,
                TenantSubscription.next_billing_date <= now
            )
        )
        if tenant_id is not None:
            query = query.where(TenantSubscription.tenant_id == tenant_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_subscriptions_for_manual_billing(self, tenant_id: Optional[int] = None) -> List[TenantSubscription]:
        """اشتراكات ACTIVE بـauto_renew=False مستحقة الفاتورة الشهرية
        (next_billing_date <= الآن) — نفس معيار الاستحقاق في
        get_subscriptions_for_renewal، لكن لعملاء الدفع اليدوي (بعكسها
        اللي تخص auto_renew=True). تُستخدَم من generate_monthly_invoices
        [2026-09-09]. بلا فلتر tenant_id افتراضيًا (عبر كل المستأجرين)."""
        now = datetime.now(timezone.utc)
        query = select(TenantSubscription).where(
            and_(
                TenantSubscription.status == "ACTIVE",
                TenantSubscription.auto_renew == False,
                TenantSubscription.next_billing_date <= now
            )
        )
        if tenant_id is not None:
            query = query.where(TenantSubscription.tenant_id == tenant_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_past_due_subscriptions(self, tenant_id: Optional[int] = None) -> List[TenantSubscription]:
        """كل اشتراكات PAST_DUE — بلا فلتر tenant_id افتراضيًا (عبر كل
        المستأجرين)، تُستخدَم من check_past_due_subscriptions
        (فحص/تنبيهات فترة السماح اليومي) [2026-09-08]."""
        query = select(TenantSubscription).where(TenantSubscription.status == "PAST_DUE")
        if tenant_id is not None:
            query = query.where(TenantSubscription.tenant_id == tenant_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_cancelled_subscriptions_for_cleanup(
        self,
        tenant_id: Optional[int] = None,
    ) -> List[TenantSubscription]:
        """اشتراكات CANCELLED جاهزة للمرحلة أ من التنظيف (تعطيل service
        access) — cancelled_at IS NOT NULL و<= الآن - 30 يوم. اشتراكات
        CANCELLED قديمة قبل migration 048 (cancelled_at لسه NULL) مُستبعدة
        عمدًا [2026-09-09] — راجع cleanup-cancelled-subscriptions-task-
        fix-session-log.md لسبب رفض fallback على updated_at. بلا فلتر
        tenant_id افتراضيًا (عبر كل المستأجرين)، بنفس نمط
        get_past_due_subscriptions."""
        threshold = datetime.now(timezone.utc) - timedelta(days=30)
        conditions = [
            TenantSubscription.status == "CANCELLED",
            TenantSubscription.cancelled_at.isnot(None),
            TenantSubscription.cancelled_at <= threshold,
        ]
        if tenant_id is not None:
            conditions.append(TenantSubscription.tenant_id == tenant_id)
        result = await self.db.execute(select(TenantSubscription).where(and_(*conditions)))
        return list(result.scalars().all())

    async def get_tenant_subscriptions(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> PaginatedResponse[TenantSubscriptionResponse]:
        query = select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        paginated_query = query.offset(skip).limit(limit)
        result = await self.db.execute(paginated_query)
        items = list(result.scalars().all())

        response_items = [TenantSubscriptionResponse.model_validate(item) for item in items]
        return PaginatedResponse[TenantSubscriptionResponse](
            data=response_items,
            total=total,
            skip=skip,
            limit=limit
        )

    async def create_subscription(self, **kwargs) -> TenantSubscription:
        subscription = TenantSubscription(**kwargs)
        self.db.add(subscription)
        await self.db.flush()
        await self.db.refresh(subscription)
        return subscription

    async def update_subscription(
        self,
        subscription_id: int,
        tenant_id: int,
        **kwargs
    ) -> TenantSubscription:
        await self.db.execute(
            update(TenantSubscription)
            .where(and_(TenantSubscription.id == subscription_id, TenantSubscription.tenant_id == tenant_id))
            .values(**kwargs)
        )
        await self.db.flush()
        subscription = await self.get_subscription(subscription_id, tenant_id)
        if not subscription:
            raise NotFoundError("الاشتراك غير موجود")
        return subscription

    async def update_subscription_status(
        self,
        subscription_id: int,
        tenant_id: int,
        status: str
    ) -> TenantSubscription:
        return await self.update_subscription(subscription_id, tenant_id, status=status)

    async def get_active_subscription_count(self, service_id: int) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(TenantSubscription)
            .join(ServicePlan)
            .where(
                and_(
                    ServicePlan.service_id == service_id,
                    TenantSubscription.status.in_(["ACTIVE", "TRIAL"])
                )
            )
        )
        return result.scalar() or 0

    # ==========================================
    # 4. صلاحيات الوصول (Service Access)
    # ==========================================
    async def get_tenant_service_access(
        self,
        tenant_id: int,
        service_id: int
    ) -> Optional[TenantServiceAccess]:
        result = await self.db.execute(
            select(TenantServiceAccess).where(
                and_(
                    TenantServiceAccess.tenant_id == tenant_id,
                    TenantServiceAccess.service_id == service_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_services_with_access(self, tenant_id: int) -> List[Dict[str, Any]]:
        services = await self.get_all_services()
        result = []
        for service in services:
            service_id = cast(int, service.id)
            access = await self.get_tenant_service_access(tenant_id, service_id)
            subscription = await self.get_active_subscription(tenant_id, service_id)
            result.append({
                "service": service,
                "has_access": access is not None and access.is_active,
                "is_subscribed": subscription is not None,
                "subscription_status": subscription.status if subscription else None,
                "access_level": access.access_level if access else None,
            })
        return result

    async def create_service_access(self, **kwargs) -> TenantServiceAccess:
        access = TenantServiceAccess(**kwargs)
        self.db.add(access)
        await self.db.flush()
        await self.db.refresh(access)
        return access

    async def update_service_access(
        self,
        access_id: int,
        **kwargs
    ) -> TenantServiceAccess:
        await self.db.execute(
            update(TenantServiceAccess)
            .where(TenantServiceAccess.id == access_id)
            .values(**kwargs)
        )
        await self.db.commit()
        result = await self.db.execute(
            select(TenantServiceAccess).where(TenantServiceAccess.id == access_id)
        )
        access = result.scalar_one_or_none()
        if not access:
            raise NotFoundError("صلاحية الوصول غير موجودة")
        return access

    # ==========================================
    # 5. الفواتير (Invoices)
    # ==========================================
    async def get_invoice_by_id(self, invoice_id: int, tenant_id: int) -> Optional[Invoice]:
        result = await self.db.execute(
            select(Invoice).where(
                and_(
                    Invoice.id == invoice_id,
                    Invoice.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_invoice_by_idempotency(self, idempotency_key: str, tenant_id: int) -> Optional[Invoice]:
        """جلب الفاتورة بواسطة مفتاح Idempotency مع تصفية tenant_id."""
        result = await self.db.execute(
            select(Invoice).where(
                and_(
                    Invoice.idempotency_key == idempotency_key,
                    Invoice.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_tenant_invoices(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> PaginatedResponse[InvoiceResponse]:
        query = select(Invoice).where(Invoice.tenant_id == tenant_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        paginated_query = query.offset(skip).limit(limit)
        result = await self.db.execute(paginated_query)
        items = list(result.scalars().all())

        response_items = [InvoiceResponse.model_validate(item) for item in items]
        return PaginatedResponse[InvoiceResponse](
            data=response_items,
            total=total,
            skip=skip,
            limit=limit
        )

    async def create_invoice(self, **kwargs) -> Invoice:
        invoice = Invoice(**kwargs)
        self.db.add(invoice)
        await self.db.flush()
        await self.db.refresh(invoice)
        return invoice

    async def update_invoice(self, invoice_id: int, tenant_id: int, **kwargs) -> Invoice:
        await self.db.execute(
            update(Invoice)
            .where(and_(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id))
            .values(**kwargs)
        )
        await self.db.flush()
        result = await self.db.execute(
            select(Invoice).where(and_(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id))
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise NotFoundError("الفاتورة غير موجودة")
        return invoice

    async def get_all_invoices(self) -> List[Invoice]:
        result = await self.db.execute(select(Invoice))
        return list(result.scalars().all())

    # ==========================================
    # 6. رايات الميزات (Feature Flags)
    # ==========================================
    async def get_feature_flag(
        self,
        tenant_id: int,
        service_id: int,
        feature_key: str
    ) -> Optional[TenantFeatureFlag]:
        result = await self.db.execute(
            select(TenantFeatureFlag).where(
                and_(
                    TenantFeatureFlag.tenant_id == tenant_id,
                    TenantFeatureFlag.service_id == service_id,
                    TenantFeatureFlag.feature_key == feature_key
                )
            )
        )
        return result.scalar_one_or_none()

    async def toggle_feature_flag(
        self,
        tenant_id: int,
        service_id: int,
        feature_key: str,
        enabled: bool
    ) -> TenantFeatureFlag:
        flag = await self.get_feature_flag(tenant_id, service_id, feature_key)
        if flag:
            setattr(flag, 'is_enabled', enabled)
            await self.db.commit()
            await self.db.refresh(flag)
            return flag
        else:
            flag = TenantFeatureFlag(
                tenant_id=tenant_id,
                service_id=service_id,
                feature_key=feature_key,
                is_enabled=enabled,
            )
            self.db.add(flag)
            await self.db.commit()
            await self.db.refresh(flag)
            return flag

    async def get_all_feature_flags_for_tenant(self, tenant_id: int) -> List[TenantFeatureFlag]:
        result = await self.db.execute(
            select(TenantFeatureFlag).where(TenantFeatureFlag.tenant_id == tenant_id)
        )
        return list(result.scalars().all())