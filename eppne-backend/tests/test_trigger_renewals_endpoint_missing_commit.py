"""
Regression test لإصلاح `backlog-trigger-renewals-admin-endpoint-missing-commit-silent-write`.
تقرير التحقيق الأصلي (قبل الإصلاح): .claude/reports/trigger-renewals-missing-commit-investigation-session-log.md
تقرير الإصلاح: .claude/reports/trigger-renewals-missing-commit-fix-session-log.md

**السبب الجذري (كان):** `SaaSControlService.trigger_renewals` (service.py:618-621)
كانت بتستدعي `process_auto_renewals(target)` وترجّع نتائجه مباشرة بلا أي
`commit()`. فرع `except InsufficientBalanceError` (PAST_DUE) جوّه
`process_auto_renewals` بيعمل `repo.update_subscription(...)` عبر
`flush()` بس (بلا `commit()` مستقل، بعكس فرع SUCCESS اللي بيعمل
`self.db.commit()` خاص بيه سطر 314) — فكانت الكتابة معتمدة كليًا على
commit خارجي. `POST /admin/trigger-renewals` (router.py) مفهوش أي
commit مماثل لـ`saas_tasks.py:75` (الـcelery task) → التحويل لـPAST_DUE
كان بيضيع صامتًا لما تُغلق جلسة الطلب (`get_db()` بترولباك أي ترانزاكشن
معلَّقة).

**الإصلاح (ضيق، `trigger_renewals` بس، service.py:618-622):**

```python
async def trigger_renewals(self, tenant_id: Optional[int] = None):
    target = tenant_id if tenant_id is not None else self.tenant_id
    results = await self.process_auto_renewals(target)
    await self.db.commit()
    return results
```

**أول اختبار تحت (`..._loses_past_due...`)** — نفس السيناريو والمنهجية
بالحرف من الاختبار الأصلي قبل الإصلاح (اشتراك باهظ واحد فقط → PAST_DUE،
استدعاء `trigger_renewals` مباشرة بجلسة `AsyncSessionLocal()` تُفتح
وتُغلق بنفس نمط `get_db()` الحقيقي بلا أي commit إضافي من الاختبار
نفسه) — لكن التوقّع دلوقتي مقلوب: الاشتراك المفروض يبقى PAST_DUE فعليًا
في الـDB بعد إغلاق الجلسة (كان قبل الإصلاح يفضل ACTIVE).

**الاختبار التاني (`..._success_...`)** — نفس المسار (`trigger_renewals`)
لكن سيناريو SUCCESS (اشتراك رخيص)، للتأكد إن `await self.db.commit()`
الإضافي مايسببش "double commit error" أو أي استثناء — `self.db.commit()`
بعد commit سابق فعلاً (فرع SUCCESS جوّه `process_auto_renewals`، سطر
314) هو استدعاء آمن تمامًا في SQLAlchemy (commit على session بلا
pending transaction بيبقى no-op — يبدأ ويقفل ترانزاكشن فاضية بلا خطأ).
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select, delete

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels
from app.core.database import AsyncSessionLocal
from app.domains.saas.router import trigger_renewals
from app.domains.saas.repository import SaaSRepository
from app.domains.saas.models import ServiceCatalog, ServicePlan, TenantSubscription, Invoice

TENANT_ID = 1


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _seed_due_subscription(db, *, price: Decimal, suffix: str):
    repo = SaaSRepository(db)

    service = await repo.create_service(
        name=f"REGTEST-TRIGREN-SVC-{suffix}",
        code=f"regtest_trigren_svc_{suffix}",
        is_active=True,
    )
    plan = await repo.create_plan(
        service_id=service.id,
        name=f"REGTEST-TRIGREN-PLAN-{suffix}",
        code=f"regtest_trigren_plan_{suffix}",
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
        idempotency_key=f"REGTEST-TRIGREN-SUB-{suffix}",
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
async def test_trigger_renewals_endpoint_persists_past_due_after_fix(db):
    """بعد الإصلاح: رد الـAPI الفعلي لازم يُظهر PAST_DUE، وصف الاشتراك في
    الـDB (بعد إغلاق نفس جلسة الطلب — تمامًا زي get_db() الحقيقي) لازم
    يبقى PAST_DUE فعليًا هو كمان (مش ACTIVE زي قبل الإصلاح)."""
    suffix = _suffix()
    service, plan, subscription = await _seed_due_subscription(
        db, price=Decimal("999999.00"), suffix=suffix
    )

    try:
        request_db = AsyncSessionLocal()  # نفس ما بيعمله get_db(): async with AsyncSessionLocal() as session
        try:
            response = await trigger_renewals(
                tenant_id=TENANT_ID,
                current_user=None,  # current_user مش مستخدَمة في جسم الدالة إطلاقًا
                db=request_db,
            )
        finally:
            await request_db.close()  # طبق finally بتاع get_db() بالحرف

        results_by_id = {r["subscription_id"]: r for r in response["results"]}
        assert subscription.id in results_by_id, response
        api_result = results_by_id[subscription.id]
        assert api_result["status"] == "PAST_DUE", api_result

        async with AsyncSessionLocal() as independent_db:
            row = (await independent_db.execute(
                select(TenantSubscription).where(TenantSubscription.id == subscription.id)
            )).scalar_one_or_none()
            assert row is not None
            assert row.status == "PAST_DUE", (
                f"الإصلاح لازم يضمن تطابق رد الـAPI مع الـDB — لسه status={row.status!r} "
                f"بدل PAST_DUE، يعني الـcommit() المضاف في trigger_renewals مش بيشتغل"
            )
            assert row.grace_period_end_date is not None, (
                "grace_period_end_date لازم يتحفظ فعليًا بعد الإصلاح (مضروب +3 أيام)"
            )
    finally:
        await _cleanup(db, subscription_id=subscription.id, plan_id=plan.id, service_id=service.id)


@pytest.mark.asyncio
async def test_trigger_renewals_endpoint_success_path_no_double_commit_error(db):
    """نفس مسار trigger_renewals، لكن سيناريو SUCCESS (اشتراك رخيص) —
    تأكيد إن await self.db.commit() الإضافي (بعد commit فرع SUCCESS
    الداخلي، service.py:314) مايرمي أي استثناء، والتجديد بيتم فعليًا
    (ACTIVE + next_billing_date محدَّث + فاتورة حقيقية)."""
    suffix = _suffix()
    service, plan, subscription = await _seed_due_subscription(
        db, price=Decimal("1.00"), suffix=suffix
    )

    try:
        request_db = AsyncSessionLocal()
        try:
            response = await trigger_renewals(
                tenant_id=TENANT_ID,
                current_user=None,
                db=request_db,
            )
        finally:
            await request_db.close()

        results_by_id = {r["subscription_id"]: r for r in response["results"]}
        assert subscription.id in results_by_id, response
        api_result = results_by_id[subscription.id]
        assert api_result["status"] == "SUCCESS", api_result
        assert api_result.get("tx_hash"), api_result

        async with AsyncSessionLocal() as independent_db:
            row = (await independent_db.execute(
                select(TenantSubscription).where(TenantSubscription.id == subscription.id)
            )).scalar_one_or_none()
            assert row is not None
            assert row.status == "ACTIVE"
            assert row.grace_period_end_date is None
            assert row.next_billing_date > datetime.now(timezone.utc)

            invoice = (await independent_db.execute(
                select(Invoice).where(Invoice.subscription_id == subscription.id)
            )).scalar_one_or_none()
            assert invoice is not None, "فاتورة التجديد لازم تتولد فعليًا للاشتراك الناجح"
            assert invoice.status == "PENDING"
    finally:
        await _cleanup(db, subscription_id=subscription.id, plan_id=plan.id, service_id=service.id)
