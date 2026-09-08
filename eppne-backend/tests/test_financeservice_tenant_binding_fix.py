"""
regression test لجلسة `financeservice-tenant-binding-fix`.
تقرير الجلسة: .claude/reports/financeservice-tenant-binding-fix-session-log.md

السبب الجذري (كان): SaaSControlService.__init__ كانت بتبني
self.finance = FinanceService(db, tenant_id) مرة واحدة وقت الإنشاء —
كائن ثابت طول عمر الـinstance، مربوط بتينانت لحظة الإنشاء مش بتينانت
العملية الفعلي. لما SaaSControlService بتتبنى بتينانت سنتينل إداري (0،
نمط process_auto_renewals_task/router.py:273)، أي عملية
self.finance.transfer() لتينانت حقيقي مختلف كانت بتفشل بـ
NotFoundError("المستلم غير موجود") — لأن FinanceService.transfer()
بتدوّر عن المستلم عبر self.tenant_id (0 الثابت)، مش تينانت الاشتراك
الحقيقي (راجع past-due-grace-period-notifications-implementation-
session-log.md §9-ج للاختبار الحي اللي كشف الباج ده أول مرة).

الإصلاح: حذف self.finance الثابتة من __init__، وبناء
FinanceService(self.db, <تينانت العملية الصح>) محليًا جوّه كل دالة على
حدة (process_auto_renewals: sub_tenant_id لكل اشتراك على حدة؛
pay_invoice: self.tenant_id — نفس تينانت الفاتورة).

هذا الاختبار بيكرر بالظبط نفس السيناريو اللي فشل قبل الإصلاح (§9-ج
أعلاه): SaaSControlService(db, 0) [نمط الإداري الحقيقي] +
process_auto_renewals(tenant_id=None) عبر اشتراكين حقيقيين تحت تينانت 1
(مختلف صراحة عن تينانت الـinstance، 0). الـ`await db.commit()` بعد
النداء مباشرة بيكرر بالضبط نفس بنية `process_auto_renewals_task`
(app/tasks/saas_tasks.py:74-75) — مطلوب عشان فرع `except
InsufficientBalanceError` (service.py) بيعمل flush() بس بلا commit()
خاص بيه (باج مستقل موثَّق منفصل، راجع PROGRESS_LOG.md — "فرع except
InsufficientBalanceError... بلا أي commit() بعده"؛ خارج نطاق هذه
الجلسة بالكامل، صفر لمس عليه هنا).
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select, delete

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels
from app.core.database import AsyncSessionLocal
from app.domains.saas.service import SaaSControlService
from app.domains.saas.repository import SaaSRepository
from app.domains.saas.models import ServiceCatalog, ServicePlan, TenantSubscription, Invoice

TENANT_ID = 1


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _seed_due_subscription(db, *, price: Decimal, suffix: str):
    """تزرع service/plan/subscription مستحق للتجديد فعليًا (next_billing_date
    في الماضي) عبر الـrepo مباشرة — نفس منهجية _seed_active_subscription في
    test_saas_cancel_subscription_silent_write.py."""
    repo = SaaSRepository(db)

    service = await repo.create_service(
        name=f"REGTEST-FINBIND-SVC-{suffix}",
        code=f"regtest_finbind_svc_{suffix}",
        is_active=True,
    )
    plan = await repo.create_plan(
        service_id=service.id,
        name=f"REGTEST-FINBIND-PLAN-{suffix}",
        code=f"regtest_finbind_plan_{suffix}",
        price_monthly=price,
        price_yearly=price * 10,
        currency="MR_USDT",
    )
    subscription = await repo.create_subscription(
        tenant_id=TENANT_ID,
        plan_id=plan.id,
        status="ACTIVE",
        auto_renew=True,
        next_billing_date=datetime.now(timezone.utc) - timedelta(days=1),
        idempotency_key=f"REGTEST-FINBIND-SUB-{suffix}",
    )
    await db.commit()
    return service, plan, subscription


async def _cleanup(db, *, subscription_id, plan_id, service_id):
    await db.execute(delete(Invoice).where(Invoice.subscription_id == subscription_id))
    await db.execute(delete(TenantSubscription).where(TenantSubscription.id == subscription_id))
    await db.execute(delete(ServicePlan).where(ServicePlan.id == plan_id))
    await db.execute(delete(ServiceCatalog).where(ServiceCatalog.id == service_id))
    await db.commit()


@pytest.mark.asyncio
async def test_process_auto_renewals_admin_sentinel_full_loop_success_and_past_due(db):
    """قبل الإصلاح: الاثنين (رخيص وباهظ) كانوا بيفشلوا بنفس
    NotFoundError("المستلم غير موجود") — مفيش SUCCESS ولا PAST_DUE حقيقي.
    بعد الإصلاح المتوقَّع: رخيص → SUCCESS فعلي (معاملة + فاتورة حقيقيتين)،
    باهظ → InsufficientBalanceError → PAST_DUE فعلي."""
    suffix = _suffix()
    cheap_service, cheap_plan, cheap_sub = await _seed_due_subscription(
        db, price=Decimal("1.00"), suffix=f"cheap-{suffix}"
    )
    expensive_service, expensive_plan, expensive_sub = await _seed_due_subscription(
        db, price=Decimal("999999.00"), suffix=f"expensive-{suffix}"
    )

    try:
        svc = SaaSControlService(db, 0)  # نفس نمط السنتينل الإداري الحقيقي
        results = await svc.process_auto_renewals(tenant_id=None)
        # نفس ما بتعمله process_auto_renewals_task (saas_tasks.py:75) —
        # ضروري لأن فرع PAST_DUE فيه flush() بس، مش commit() مستقل.
        await db.commit()

        results_by_id = {r["subscription_id"]: r for r in results}
        assert cheap_sub.id in results_by_id, results
        assert expensive_sub.id in results_by_id, results

        cheap_result = results_by_id[cheap_sub.id]
        expensive_result = results_by_id[expensive_sub.id]

        assert cheap_result["status"] == "SUCCESS", cheap_result
        assert cheap_result.get("tx_hash"), cheap_result

        assert expensive_result["status"] == "PAST_DUE", expensive_result

        async with AsyncSessionLocal() as independent_db:
            cheap_row = (await independent_db.execute(
                select(TenantSubscription).where(TenantSubscription.id == cheap_sub.id)
            )).scalar_one_or_none()
            assert cheap_row is not None
            assert cheap_row.status == "ACTIVE", (
                "الاشتراك الرخيص لازم يفضل ACTIVE بعد تجديد ناجح فعلي"
            )
            assert cheap_row.grace_period_end_date is None
            assert cheap_row.next_billing_date > datetime.now(timezone.utc)

            expensive_row = (await independent_db.execute(
                select(TenantSubscription).where(TenantSubscription.id == expensive_sub.id)
            )).scalar_one_or_none()
            assert expensive_row is not None
            assert expensive_row.status == "PAST_DUE", (
                "الاشتراك الباهظ لازم يتحول PAST_DUE فعليًا (مش يفضل ACTIVE "
                "بسبب فشل صامت قديم قبل الوصول لمنطق الرصيد أصلًا)"
            )
            assert expensive_row.grace_period_end_date is not None

            invoice = (await independent_db.execute(
                select(Invoice).where(Invoice.subscription_id == cheap_sub.id)
            )).scalar_one_or_none()
            assert invoice is not None, "فاتورة التجديد لازم تتولد فعليًا للاشتراك الناجح"
            assert invoice.status == "PENDING"

            no_invoice_for_failed = (await independent_db.execute(
                select(Invoice).where(Invoice.subscription_id == expensive_sub.id)
            )).scalar_one_or_none()
            assert no_invoice_for_failed is None, "مفروض صفر فاتورة للاشتراك اللي فشل تجديده"
    finally:
        await _cleanup(db, subscription_id=cheap_sub.id, plan_id=cheap_plan.id, service_id=cheap_service.id)
        await _cleanup(
            db,
            subscription_id=expensive_sub.id,
            plan_id=expensive_plan.id,
            service_id=expensive_service.id,
        )


@pytest.mark.asyncio
async def test_pay_invoice_same_tenant_still_works_after_removing_self_finance(db):
    """Regression: pay_invoice() كانت بتستخدم self.finance (نفس تينانت
    الـinstance، self.tenant_id) — بعد حذف self.finance من __init__، لازم
    تفضل شغّالة بنفس السلوك بالظبط لما الـinstance مبني بتينانت حقيقي
    عادي (مش سنتينل 0)، عبر finance محلية جديدة بنفس self.tenant_id."""
    suffix = _suffix()
    service, plan, subscription = await _seed_due_subscription(
        db, price=Decimal("1.00"), suffix=f"payinv-{suffix}"
    )

    try:
        svc = SaaSControlService(db, TENANT_ID)
        invoice = await svc._generate_invoice(
            tenant_id=TENANT_ID, subscription_id=subscription.id, plan=plan
        )
        await db.commit()

        paid = await svc.pay_invoice(invoice.id)
        assert paid.status == "PAID"
        assert paid.paid_tx_hash

        async with AsyncSessionLocal() as independent_db:
            row = (await independent_db.execute(
                select(Invoice).where(Invoice.id == invoice.id)
            )).scalar_one_or_none()
            assert row is not None
            assert row.status == "PAID"
            assert row.paid_tx_hash
    finally:
        await _cleanup(db, subscription_id=subscription.id, plan_id=plan.id, service_id=service.id)
