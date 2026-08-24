"""
regression test لجلسة `saas-cancel-subscription-silent-write-fix`.
تقرير الجلسة: .claude/reports/saas-cancel-subscription-silent-write-fix-session-log.md
(معروف أصلًا من 2026-08-14 — راجع silent-write-regression-session-log.md،
أُعيد تأكيده حيًا واتصلح نهائيًا 2026-08-24).

السبب الجذري (كان): `SaaSControlService.cancel_subscription` (service.py)
كانت بتنادي `repo.update_subscription()` — flush()-only منذ إصلاح
`a9bbae4` (commit()-inside-begin_nested()) — بلا أي `begin_nested()` ولا
`db.commit()` صريح على الإطلاق. الرد كان بيرجع 200 مع status=CANCELLED
(الكائن في الذاكرة اتحدَّث فعلًا)، لكن الكتابة كانت بتضيع صامتة عند إغلاق
الـsession (`get_db()` بترولباك أي ترانزاكشن معلّقة).

الإصلاح: `await self.db.commit()` مباشر فورًا بعد `update_subscription()`
— بلا `begin_nested()` (كتابة واحدة بسيطة، لا يوجد داعٍ لـSAVEPOINT، على
عكس `create_subscription`/`process_auto_renewals`/`pay_invoice` اللي كل
واحدة فيهم عندها كتابتين-تلاتة مترابطة). نفس القاعدة المطبَّقة سابقًا في
`app/tasks/deployment.py` و`ai_agents.execute_agent_action` لأي دالة معندهاش
`begin_nested()` أصلًا.

منهجية التحقق (بنفس معيار `test_entity_membership_foundation.py`):
القراءة من نفس الـsession اللي نفَّذت `cancel_subscription` غير كافية —
لأن SELECT جوه نفس الترانزاكشن بيشوف كتابة `flush()`-only معلَّقة حتى لو
الـcommit() ناقص. التحقق الحقيقي لازم يكون عبر `AsyncSessionLocal()`
مستقلة تمامًا (اتصال DB جديد)، اللي مبتشوفش إلا البيانات المُلتزَم بها
(committed) فعليًا.
"""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select, delete

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels
from app.core.database import AsyncSessionLocal
from app.core.errors import ValidationError

from app.domains.saas.service import SaaSControlService
from app.domains.saas.repository import SaaSRepository
from app.domains.saas.models import ServiceCatalog, ServicePlan, TenantSubscription

TENANT_ID = 1


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _seed_active_subscription(db):
    """تزرع service/plan/subscription عبر الـrepo مباشرة (ORM، بلا SQL خام
    — عشان الأعمدة ذات الـPython-default زي max_users/payment_method تتملى
    صح، بعكس زرع SQL خام اللي بيسبب NULL ويكسر التسلسل عند القراءة عبر
    schema — راجع saas-idor-fix-session-log.md §4). بديل subscribe_to_plan
    (محجوبة ببج pre-existing منفصل تمامًا: get_plan_by_id — خارج نطاق هذا
    الاختبار)."""
    repo = SaaSRepository(db)
    suffix = _suffix()

    service = await repo.create_service(
        name=f"REGTEST-CANCEL-SVC-{suffix}",
        code=f"regtest_cancel_svc_{suffix}",
        is_active=True,
    )
    plan = await repo.create_plan(
        service_id=service.id,
        name=f"REGTEST-CANCEL-PLAN-{suffix}",
        code=f"regtest_cancel_plan_{suffix}",
        price_monthly=Decimal("9.99"),
        price_yearly=Decimal("99.99"),
        currency="MR_USDT",
    )
    subscription = await repo.create_subscription(
        tenant_id=TENANT_ID,
        plan_id=plan.id,
        status="ACTIVE",
        auto_renew=True,
        idempotency_key=f"REGTEST-CANCEL-SUB-{suffix}",
    )
    await db.commit()
    return service, plan, subscription


async def _cleanup(db, *, subscription_id, plan_id, service_id):
    await db.execute(delete(TenantSubscription).where(TenantSubscription.id == subscription_id))
    await db.execute(delete(ServicePlan).where(ServicePlan.id == plan_id))
    await db.execute(delete(ServiceCatalog).where(ServiceCatalog.id == service_id))
    await db.commit()


@pytest.mark.asyncio
async def test_cancel_subscription_persists_cancelled_status_independent_session(db):
    """الاختبار الأساسي لهذه الجلسة: cancel_subscription لازم يحفظ فعليًا
    status=CANCELLED, auto_renew=False على القرص — مش بس في كائن الإرجاع.
    قبل الإصلاح، هذا الاختبار كان يفشل (row.status == 'ACTIVE' رغم رد نجاح
    ظاهري من الاستدعاء)."""
    service, plan, subscription = await _seed_active_subscription(db)

    try:
        svc = SaaSControlService(db, TENANT_ID)
        result = await svc.cancel_subscription(subscription.id)
        assert result.status == "CANCELLED"

        async with AsyncSessionLocal() as independent_db:
            row = (await independent_db.execute(
                select(TenantSubscription).where(TenantSubscription.id == subscription.id)
            )).scalar_one_or_none()
            assert row is not None
            assert row.status == "CANCELLED", (
                "الكتابة لم تُحفَظ فعليًا في DB — رجوع محتمل لباج "
                "saas-cancel-subscription-silent-write (صفر commit() بعد update_subscription)"
            )
            assert row.auto_renew is False
    finally:
        await _cleanup(db, subscription_id=subscription.id, plan_id=plan.id, service_id=service.id)


@pytest.mark.asyncio
async def test_cancel_already_cancelled_subscription_raises_validation_error(db):
    """حالة حافة: محاولة إلغاء اشتراك ملغي بالفعل لازم تفشل بـValidationError
    (منطق موجود مسبقًا في cancel_subscription، بلا علاقة بإصلاح الـcommit —
    يتحقق منه هنا للتأكد إن الإصلاح ما كسرش هذا المسار)."""
    service, plan, subscription = await _seed_active_subscription(db)

    try:
        svc = SaaSControlService(db, TENANT_ID)
        await svc.cancel_subscription(subscription.id)

        with pytest.raises(ValidationError):
            await svc.cancel_subscription(subscription.id)
    finally:
        await _cleanup(db, subscription_id=subscription.id, plan_id=plan.id, service_id=service.id)
