"""
regression test لجلسة `saas-pay-invoice-sender-id-user-id-collision` (2026-09-24).
تقرير الجلسة: .claude/reports/saas-sender-id-collision-fix-session-log.md

الباج الأصلي (مُصلَح في 0ba7204، 2026-08-25): pay_invoice/process_auto_renewals
كانوا بيمرروا sender_id=self.tenant_id لـFinanceService.transfer() اللي بتفسّره
كـuser_id حرفيًا — فلو مستخدم في نفس التينانت id بتاعه = tenant_id، كان بيتخصم
من محفظته هو. التصميم القائم (A): الدافع = AcademyTenant.admin_id، والمستقبِل =
حساب نظام التينانت (get_or_create_system_account).

الإصلاح في هذه الجلسة (_get_tenant_admin_id): الأدمن لازم يكون عضو في نفس
التينانت، وإلا ValidationError — بدل ما transfer() يخصم من محفظة (admin, tenant)
لمستخدم مش عضو فيها (التقرير §4.3-أ و§8).

Setup مشترك لكل اختبار (_seed):
- التينانت T بـid صريح X، ومستخدم U_collide بـid = X بالظبط (السيناريو الأصلي
  حرفيًا). X بيتختار وقت التشغيل من ids فاضية في users وacademy_tenants الاتنين
  وأقل من قيمتي الـsequence — فمستحيل يتصادم مع أي nextval مستقبلي.
- A = أدمن T (عضو في T). محافظ (U_collide, T) و(A, T) برصيد 100.
- التينانت T2 أدمنها A (عضو في T مش T2 — نفس شكل تينانت 15 الحي)، ومحفظة
  (A, T2) ممولة مسبقًا برصيد 100 — حالة الضرر الحقيقية الوحيدة (§8.1).

1. pay_invoice على T → الخصم من A، U_collide بلا تغيير.
2. process_auto_renewals على T → نفس الإثبات.
3. pay_invoice على T2 → ValidationError، (A, T2) بلا تغيير.
4. process_auto_renewals على T2 → FAILED (مش PAST_DUE — راجع بند
   tenant-onboarding-admin-always-cross-tenant-saas-unpayable)، (A, T2) بلا تغيير.

كل تينانت/مستخدم/محفظة/transaction/خطة throwaway بتتحذف في finally.
"""
import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, text

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels
from app.core.database import AsyncSessionLocal
from app.core.errors import ValidationError
from app.domains.academy.models import AcademyTenant
from app.domains.identity.models import User
from app.domains.saas.models import ServiceCatalog, ServicePlan, PlanServiceAccess
from app.domains.saas.repository import SaaSRepository
from app.domains.saas.service import SaaSControlService

PRICE = Decimal("10")
FUNDED = 100.0


def _balances(mr_usdt: float) -> str:
    return json.dumps({"MR7": 0, "MRX": 0, "NBT": 0, "MR_USDT": mr_usdt, "MR_POUND": 0})


async def _pick_collision_id(db) -> int:
    """أصغر id فاضي في users وacademy_tenants الاتنين، وأقل من قيمتي الـsequence."""
    row = (await db.execute(text(
        """select min(g) from generate_series(2, least(
               (select last_value from academy_tenants_id_seq),
               (select last_value from users_id_seq))) g
           where not exists (select 1 from users where id = g)
             and not exists (select 1 from academy_tenants where id = g)"""
    ))).scalar()
    assert row is not None, "مفيش id فاضي أقل من الـsequences لسيناريو التصادم"
    return int(row)


async def _add_wallet(db, user_id: int, tenant_id: int, mr_usdt: float) -> None:
    await db.execute(text(
        """insert into wallets(user_id, tenant_id, balances, is_frozen, is_custodial)
           values (:u, :t, cast(:b as jsonb), false, true)"""),
        {"u": user_id, "t": tenant_id, "b": _balances(mr_usdt)})


async def _seed(db) -> dict:
    suffix = uuid.uuid4().hex[:8]
    x = await _pick_collision_id(db)
    s: dict = {"suffix": suffix, "T": x}

    # admin_id=1 مؤقتًا (قيد FK) لحد ما A يتعمل جوّه T
    db.add(AcademyTenant(id=x, name=f"REGTEST_SIDCOL_T_{suffix}", domain=f"regtest-sidcol-t-{suffix}.local",
                         admin_id=1, is_active=True))
    await db.flush()
    collide = User(id=x, tenant_id=x, username=f"p_sidcol_collide_{suffix}",
                   email=f"p_sidcol_collide_{suffix}@example.com", hashed_password="!unusable")
    admin = User(tenant_id=x, username=f"p_sidcol_admin_{suffix}",
                 email=f"p_sidcol_admin_{suffix}@example.com", hashed_password="!unusable")
    db.add_all([collide, admin])
    await db.flush()
    s["U_collide"] = int(collide.id)
    s["A"] = int(admin.id)
    assert s["U_collide"] == s["T"] != s["A"]
    await db.execute(text("update academy_tenants set admin_id = :a where id = :t"), {"a": s["A"], "t": x})

    t2 = AcademyTenant(name=f"REGTEST_SIDCOL_T2_{suffix}", domain=f"regtest-sidcol-t2-{suffix}.local",
                       admin_id=s["A"], is_active=True)
    db.add(t2)
    await db.flush()
    s["T2"] = int(t2.id)

    await _add_wallet(db, s["U_collide"], x, FUNDED)
    await _add_wallet(db, s["A"], x, FUNDED)
    await _add_wallet(db, s["A"], s["T2"], FUNDED)
    await db.commit()

    repo = SaaSRepository(db)
    service = await repo.create_service(name=f"REGTEST-SIDCOL-SVC-{suffix}", code=f"regtest_sidcol_svc_{suffix}",
                                        is_active=True)
    plan = await repo.create_plan(service_id=service.id, name=f"REGTEST-SIDCOL-PLAN-{suffix}",
                                  code=f"regtest_sidcol_plan_{suffix}", price_monthly=PRICE,
                                  price_yearly=PRICE * 10, currency="MR_USDT")
    db.add(PlanServiceAccess(plan_id=plan.id, service_id=service.id))
    await db.commit()
    s["service_id"] = int(service.id)
    s["plan_id"] = int(plan.id)
    return s


async def _pending_invoice(db, s: dict, tenant_id: int) -> int:
    repo = SaaSRepository(db)
    sub = await repo.create_subscription(
        tenant_id=tenant_id, plan_id=s["plan_id"], status="ACTIVE", auto_renew=False,
        next_billing_date=datetime.now(timezone.utc) + timedelta(days=30),
        idempotency_key=f"REGTEST-SIDCOL-SUB-INV-{tenant_id}-{s['suffix']}",
    )
    invoice = await repo.create_invoice(
        tenant_id=tenant_id, subscription_id=sub.id, invoice_number=f"REGTEST-SIDCOL-{tenant_id}-{s['suffix']}",
        amount=PRICE, currency="MR_USDT", status="PENDING",
        due_date=datetime.now(timezone.utc) + timedelta(days=7),
    )
    await db.commit()
    return int(invoice.id)


async def _due_subscription(db, s: dict, tenant_id: int) -> int:
    sub = await SaaSRepository(db).create_subscription(
        tenant_id=tenant_id, plan_id=s["plan_id"], status="ACTIVE", auto_renew=True,
        next_billing_date=datetime.now(timezone.utc) - timedelta(days=1),
        idempotency_key=f"REGTEST-SIDCOL-SUB-REN-{tenant_id}-{s['suffix']}",
    )
    await db.commit()
    return int(sub.id)


async def _balance(user_id: int, tenant_id: int) -> float:
    async with AsyncSessionLocal() as db:
        value = (await db.execute(text(
            "select (balances->>'MR_USDT')::float from wallets where user_id = :u and tenant_id = :t"),
            {"u": user_id, "t": tenant_id})).scalar()
    return float(value) if value is not None else 0.0


async def _system_account_id(tenant_id: int):
    async with AsyncSessionLocal() as db:
        return (await db.execute(text(
            "select id from users where tenant_id = :t and is_system_account"), {"t": tenant_id})).scalar()


async def _transactions(key_like: str) -> list:
    async with AsyncSessionLocal() as db:
        return (await db.execute(text(
            "select sender_id, receiver_id, amount from transactions where idempotency_key like :k"),
            {"k": key_like})).all()


async def _cleanup(s: dict) -> None:
    tenants = [t for t in (s.get("T2"), s.get("T")) if t is not None]
    if not tenants:
        return
    async with AsyncSessionLocal() as db:
        user_ids = [r[0] for r in (await db.execute(
            text("select id from users where tenant_id = any(:t)"), {"t": tenants})).all()]
        if user_ids:
            await db.execute(text("delete from transactions where sender_id = any(:u) or receiver_id = any(:u)"),
                             {"u": user_ids})
        # admin_id بيشير لـA (مستخدم في T) — يترجع لـ1 عشان A يتحذف قبل التينانتات
        await db.execute(text("update academy_tenants set admin_id = 1 where id = any(:t)"), {"t": tenants})
        await db.commit()
        tables = [r[0] for r in (await db.execute(text(
            """select c.table_name from information_schema.columns c
               join pg_tables p on p.tablename = c.table_name and p.schemaname = 'public'
               where c.table_schema = 'public' and c.column_name = 'tenant_id'
                 and c.table_name <> 'academy_tenants'"""))).all()]
        for _ in range(8):
            failed = []
            for table in tables:
                try:
                    async with db.begin_nested():
                        await db.execute(text(f'delete from "{table}" where tenant_id = any(:t)'), {"t": tenants})
                except Exception:
                    failed.append(table)
            await db.commit()
            if not failed:
                break
            tables = failed
        if "plan_id" in s:
            await db.execute(delete(PlanServiceAccess).where(PlanServiceAccess.plan_id == s["plan_id"]))
            await db.execute(delete(ServicePlan).where(ServicePlan.id == s["plan_id"]))
        if "service_id" in s:
            await db.execute(delete(ServiceCatalog).where(ServiceCatalog.id == s["service_id"]))
        await db.execute(text("delete from academy_tenants where id = any(:t)"), {"t": tenants})
        await db.commit()


@pytest.mark.asyncio
async def test_pay_invoice_debits_admin_not_user_whose_id_equals_tenant_id(db):
    s: dict = {}
    try:
        s = await _seed(db)
        invoice_id = await _pending_invoice(db, s, s["T"])

        await SaaSControlService(db, s["T"]).pay_invoice(invoice_id)

        system_id = await _system_account_id(s["T"])
        assert system_id is not None
        assert await _balance(s["U_collide"], s["T"]) == FUNDED, "الخصم وقع على المستخدم اللي id بتاعه = tenant_id"
        assert await _balance(s["A"], s["T"]) == FUNDED - float(PRICE)
        assert await _balance(system_id, s["T"]) == float(PRICE)
        txs = await _transactions(f"PAY-INV-{invoice_id}")
        assert len(txs) == 1
        assert txs[0].sender_id == s["A"] and txs[0].sender_id != s["T"]
        assert txs[0].receiver_id == system_id
        async with AsyncSessionLocal() as check:
            status = (await check.execute(text("select status from saas_invoices where id = :i"),
                                          {"i": invoice_id})).scalar()
        assert status == "PAID"
    finally:
        await _cleanup(s)


@pytest.mark.asyncio
async def test_auto_renewal_debits_admin_not_user_whose_id_equals_tenant_id(db):
    s: dict = {}
    try:
        s = await _seed(db)
        sub_id = await _due_subscription(db, s, s["T"])

        results = await SaaSControlService(db, s["T"]).process_auto_renewals(tenant_id=s["T"])

        by_id = {r["subscription_id"]: r for r in results}
        assert by_id[sub_id]["status"] == "SUCCESS", by_id.get(sub_id)
        system_id = await _system_account_id(s["T"])
        assert await _balance(s["U_collide"], s["T"]) == FUNDED, "الخصم وقع على المستخدم اللي id بتاعه = tenant_id"
        assert await _balance(s["A"], s["T"]) == FUNDED - float(PRICE)
        assert await _balance(system_id, s["T"]) == float(PRICE)
        txs = await _transactions(f"AUTO-RENEW-{sub_id}-%")
        assert len(txs) == 1
        assert txs[0].sender_id == s["A"] and txs[0].sender_id != s["T"]
        assert txs[0].receiver_id == system_id
    finally:
        await _cleanup(s)


@pytest.mark.asyncio
async def test_pay_invoice_rejects_admin_from_another_tenant(db):
    s: dict = {}
    try:
        s = await _seed(db)
        invoice_id = await _pending_invoice(db, s, s["T2"])

        try:
            await SaaSControlService(db, s["T2"]).pay_invoice(invoice_id)
            raised = False
        except ValidationError:
            raised = True
            await db.rollback()

        balance = await _balance(s["A"], s["T2"])
        txs = await _transactions(f"PAY-INV-{invoice_id}")
        assert raised and balance == FUNDED and not txs, (
            f"أدمن من تينانت تانية اتقبل كدافع: raised={raised}، رصيد (A, T2)={balance}، transactions={txs}"
        )
        assert await _system_account_id(s["T2"]) is None
        async with AsyncSessionLocal() as check:
            status = (await check.execute(text("select status from saas_invoices where id = :i"),
                                          {"i": invoice_id})).scalar()
        assert status == "PENDING"
    finally:
        await _cleanup(s)


@pytest.mark.asyncio
async def test_auto_renewal_fails_for_admin_from_another_tenant(db):
    s: dict = {}
    try:
        s = await _seed(db)
        sub_id = await _due_subscription(db, s, s["T2"])

        results = await SaaSControlService(db, s["T2"]).process_auto_renewals(tenant_id=s["T2"])
        await db.commit()  # نفس بنية process_auto_renewals_task (saas_tasks.py)

        result = {r["subscription_id"]: r for r in results}.get(sub_id)
        balance = await _balance(s["A"], s["T2"])
        txs = await _transactions(f"AUTO-RENEW-{sub_id}-%")
        # FAILED مش PAST_DUE — راجع tenant-onboarding-admin-always-cross-tenant-saas-unpayable
        assert (result is not None and result["status"] == "FAILED" and "أدمن التينانت" in result.get("error", "")
                and balance == FUNDED and not txs), (
            f"أدمن من تينانت تانية اتقبل كدافع: result={result}، رصيد (A, T2)={balance}، transactions={txs}"
        )
        assert await _system_account_id(s["T2"]) is None
    finally:
        await _cleanup(s)
