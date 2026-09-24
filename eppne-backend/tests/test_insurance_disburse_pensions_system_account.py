"""
regression test لجلسة `insurance-disburse-pensions-hardcoded-system-account` (2026-09-24).
تقرير الجلسة: .claude/reports/insurance-disburse-pensions-hardcoded-system-account-session-log.md

يثبّت (DB حقيقية) إن disburse_monthly_pensions تدفع من حساب النظام الخاص بالتينانت
(get_or_create_system_account) لا من user_id=1 (محفظة 39):
1. spy على FinanceService.transfer: كل استدعاء sender_id = حساب نظام نفس التينانت (≠ 1)،
   وتينانت A يستخدم حساب A وتينانت B يستخدم حساب B (عزل الدافع).
2. تينانت بلا معاشات: count=0 ولا يُنشأ حساب نظام (D2).
3. إثبات حركة أموال حقيقية في تينانت A: transfer الحقيقي مغلَّف بـwrapper يمرّر
   idempotency_key ويرجّع tx_hash — **محاكاة داخل الاختبار فقط** لإصلاحي (1) و(2) في بند
   `insurance-disburse-pensions-payout-logic-broken` (غير مُصلَحين في الكود). الفلوس تخرج من
   محفظة حساب نظام A، ومحفظتا 39 و929 بلا تغيير.

تينانتات throwaway خاصة بالاختبار تُحذف بالكامل في finally مع صفوف transactions الخاصة بمستخدميها
(الجدول بلا tenant_id).
"""
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.core.system_account_service import get_or_create_system_account
from app.domains.academy.models import AcademyTenant
from app.core.security import get_password_hash
from app.domains.identity.models import User
from app.domains.finance.service import FinanceService
from app.domains.insurance.service import InsuranceService
from app.domains.insurance.models import PensionRecord, PensionStatus

PENSION_AMOUNT = Decimal("10")
LEGACY_WALLET_ID = 39      # محفظة user_id=1 (الدافع الهاردكودد القديم)
TENANT1_SYSTEM_WALLET_ID = 929


def _balances(mr_usdt) -> str:
    return json.dumps({"MR7": 0, "MRX": 0, "NBT": 0, "MR_USDT": mr_usdt, "MR_POUND": 0})


async def _tenant(db, tag: str) -> int:
    suffix = uuid.uuid4().hex[:8]
    tenant = AcademyTenant(name=f"REGTEST_PENSYS_{tag}_{suffix}", domain=f"regtest-pensys-{tag.lower()}-{suffix}.local",
                           admin_id=1, is_active=True)
    db.add(tenant)
    await db.commit()
    return tenant.id


async def _user(db, tenant_id: int, prefix: str) -> int:
    # إنشاء مباشر بدل UserService.register — الأخيرة تكتب كاش المستخدم في Redis، ومسار
    # disburse نفسه لا يلمس Redis (نفس حقول get_or_create_system_account، بلا is_system_account)
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    user = User(tenant_id=tenant_id, username=uname, email=f"{uname}@example.com",
                hashed_password=get_password_hash(uuid.uuid4().hex), name_ar=uname, name_en=uname,
                public_id=str(uuid.uuid4()), is_active=True)
    db.add(user)
    await db.flush()
    await db.execute(text("""insert into wallets(user_id,tenant_id,balances,is_frozen,is_custodial)
        select :u,:t,cast(:b as jsonb),false,true where not exists (select 1 from wallets where user_id=:u and tenant_id=:t)"""),
        {"u": user.id, "t": tenant_id, "b": _balances(0)})
    await db.commit()
    return user.id


async def _pension(db, tenant_id: int, beneficiary_id: int) -> int:
    pension = PensionRecord(tenant_id=tenant_id, beneficiary_id=beneficiary_id, pension_type="REGTEST_PENSYS",
                            monthly_amount_mrusdt=PENSION_AMOUNT, start_date=datetime.now(timezone.utc),
                            status=PensionStatus.ACTIVE)
    db.add(pension)
    await db.commit()
    return pension.id


async def _system_accounts(db, tenant_id: int) -> list:
    return [r[0] for r in (await db.execute(text(
        "select id from users where tenant_id=:t and is_system_account"), {"t": tenant_id})).all()]


async def _mr_usdt(db, wallet_id: int) -> Decimal:
    return Decimal(str((await db.execute(text(
        "select balances->>'MR_USDT' from wallets where id=:w"), {"w": wallet_id})).scalar()))


async def _cleanup(tenant_ids: list) -> None:
    """يحذف صفوف transactions لمستخدمي التينانتات (الجدول بلا tenant_id) ثم كل صفوف
    التينانتات (كل جدول فيه tenant_id، بجولات لحل ترتيب الـFK) ثم التينانتات نفسها."""
    async with AsyncSessionLocal() as db:
        user_ids = [r[0] for r in (await db.execute(text(
            "select id from users where tenant_id = any(:t)"), {"t": tenant_ids})).all()]
        if user_ids:
            await db.execute(text("delete from transactions where sender_id = any(:u) or receiver_id = any(:u)"), {"u": user_ids})
            await db.commit()
        tables = [r[0] for r in (await db.execute(text(
            """select c.table_name from information_schema.columns c
               join pg_tables t on t.tablename=c.table_name and t.schemaname='public'
               where c.table_schema='public' and c.column_name='tenant_id' and c.table_name <> 'academy_tenants'"""))).all()]
        for _ in range(8):
            failed = []
            for table in tables:
                try:
                    async with db.begin_nested():
                        await db.execute(text(f'delete from "{table}" where tenant_id = any(:t)'), {"t": tenant_ids})
                except Exception:
                    failed.append(table)
            await db.commit()
            if not failed:
                break
            tables = failed
        await db.execute(text("delete from academy_tenants where id = any(:t)"), {"t": tenant_ids})
        await db.commit()


@pytest.mark.asyncio
async def test_disburse_sender_is_own_tenant_system_account_not_user_1(db, monkeypatch):
    tenant_a = await _tenant(db, "A")
    tenant_b = await _tenant(db, "B")
    try:
        ben_a1 = await _user(db, tenant_a, "p_pensys_ben_a1")
        ben_a2 = await _user(db, tenant_a, "p_pensys_ben_a2")
        ben_b = await _user(db, tenant_b, "p_pensys_ben_b")
        await _pension(db, tenant_a, ben_a1)
        await _pension(db, tenant_a, ben_a2)
        await _pension(db, tenant_b, ben_b)
        assert await _system_accounts(db, tenant_a) == [] and await _system_accounts(db, tenant_b) == []

        calls = []

        async def spy_transfer(self, **kwargs):
            sender = await self.db.get(User, kwargs["sender_id"])
            calls.append({"fs_tenant": self.tenant_id, "sender_id": kwargs["sender_id"],
                          "sender_tenant": sender.tenant_id if sender else None,
                          "sender_is_system": bool(sender.is_system_account) if sender else None,
                          "receiver_email": kwargs["receiver_email"]})
            raise RuntimeError("spy: لا حركة أموال في هذا الاختبار")

        monkeypatch.setattr(FinanceService, "transfer", spy_transfer)

        results = {}
        for tag, tid in (("A", tenant_a), ("B", tenant_b)):
            async with AsyncSessionLocal() as session:
                calls.clear()
                count = await InsuranceService(session).disburse_monthly_pensions(tid)
                expected_sys = await _system_accounts(session, tid)  # نفس الجلسة: الحساب المُنشأ (flush، بلا commit)
                results[tag] = {"count": count, "calls": list(calls), "sys": expected_sys}

        emails = {r[0]: r[1] for r in (await db.execute(text(
            "select id, email from users where id = any(:u)"), {"u": [ben_a1, ben_a2, ben_b]})).all()}

        for tag, tid, n, bens in (("A", tenant_a, 2, [ben_a1, ben_a2]), ("B", tenant_b, 1, [ben_b])):
            r = results[tag]
            assert r["count"] == 0, "الـspy بيرفع استثناء فمفيش دفعة بتتسجَّل"
            assert len(r["sys"]) == 1, f"تينانت {tag}: لازم حساب نظام واحد اتنشأ"
            sys_id = r["sys"][0]
            assert len(r["calls"]) == n
            for c in r["calls"]:
                assert c["sender_id"] != 1, f"تينانت {tag}: الدافع لسه user_id=1 الهاردكودد"
                assert c["sender_id"] == sys_id, f"تينانت {tag}: sender_id={c['sender_id']} مش حساب نظام التينانت ({sys_id})"
                assert c["sender_tenant"] == tid and c["sender_is_system"] is True
                assert c["fs_tenant"] == tid
            assert sorted(c["receiver_email"] for c in r["calls"]) == sorted(emails[b] for b in bens)

        # عزل الدافع: A و B كل واحد بحساب نظامه
        assert results["A"]["sys"][0] != results["B"]["sys"][0]
    finally:
        await _cleanup([tenant_a, tenant_b])


@pytest.mark.asyncio
async def test_disburse_tenant_without_pensions_creates_no_system_account(db, monkeypatch):
    tenant_c = await _tenant(db, "C")
    try:
        called = []

        async def spy_transfer(self, **kwargs):
            called.append(kwargs)
            raise RuntimeError("spy")

        monkeypatch.setattr(FinanceService, "transfer", spy_transfer)
        async with AsyncSessionLocal() as session:
            count = await InsuranceService(session).disburse_monthly_pensions(tenant_c)
            # نفس الجلسة: يشوف أي حساب اتعمل له flush حتى لو بلا commit
            created = await _system_accounts(session, tenant_c)
        assert count == 0 and called == []
        assert created == [], "تينانت بلا معاشات لازم ما يتنشألوش حساب نظام (D2)"
    finally:
        await _cleanup([tenant_c])


@pytest.mark.asyncio
async def test_disburse_real_money_moves_from_tenant_system_wallet_not_wallet_39(db, monkeypatch):
    tenant_a = await _tenant(db, "RM")
    try:
        ben_1 = await _user(db, tenant_a, "p_pensys_rm_ben1")
        ben_2 = await _user(db, tenant_a, "p_pensys_rm_ben2")
        p1 = await _pension(db, tenant_a, ben_1)
        p2 = await _pension(db, tenant_a, ben_2)

        # تمويل حساب نظام A (100 MR_USDT) — مُنشأ ومُلتزَم مسبقًا عشان نعرف محفظته
        sys_acct = await get_or_create_system_account(db, tenant_a)
        sys_id = sys_acct.id
        await db.execute(text("""insert into wallets(user_id,tenant_id,balances,is_frozen,is_custodial)
            values (:u,:t,cast(:b as jsonb),false,true)"""), {"u": sys_id, "t": tenant_a, "b": _balances(100)})
        await db.commit()
        sys_wallet = (await db.execute(text("select id from wallets where user_id=:u and tenant_id=:t"),
                                       {"u": sys_id, "t": tenant_a})).scalar()
        ben_wallets = {b: (await db.execute(text("select id from wallets where user_id=:u and tenant_id=:t"),
                                            {"u": b, "t": tenant_a})).scalar() for b in (ben_1, ben_2)}

        before = {"w39": await _mr_usdt(db, LEGACY_WALLET_ID), "w929": await _mr_usdt(db, TENANT1_SYSTEM_WALLET_ID),
                  "sys": await _mr_usdt(db, sys_wallet)}
        assert before["sys"] == Decimal("100")

        real_transfer = FinanceService.transfer

        async def wrapped_transfer(self, **kwargs):
            # محاكاة داخل الاختبار فقط لإصلاحي payout-logic-broken (1) idempotency_key و(2) tx_hash
            kwargs.setdefault("idempotency_key", f"REGTEST-PENSYS-{uuid.uuid4().hex[:12]}")
            tx = await real_transfer(self, **kwargs)
            return tx.tx_hash

        monkeypatch.setattr(FinanceService, "transfer", wrapped_transfer)
        async with AsyncSessionLocal() as session:
            count = await InsuranceService(session).disburse_monthly_pensions(tenant_a)
        assert count == 2

        async with AsyncSessionLocal() as check:
            after = {"w39": await _mr_usdt(check, LEGACY_WALLET_ID), "w929": await _mr_usdt(check, TENANT1_SYSTEM_WALLET_ID),
                     "sys": await _mr_usdt(check, sys_wallet)}
            bens_after = {b: await _mr_usdt(check, w) for b, w in ben_wallets.items()}
            txs = (await check.execute(text(
                "select sender_id, receiver_id, from_wallet_id, to_wallet_id, amount from transactions "
                "where receiver_id = any(:u) order by id"), {"u": [ben_1, ben_2]})).all()
            payout_hashes = [r[0] for r in (await check.execute(text(
                "select last_payout_tx from pension_records where id = any(:p)"), {"p": [p1, p2]})).all()]

        assert after["sys"] == before["sys"] - 2 * PENSION_AMOUNT, "الفلوس لازم تخرج من محفظة حساب نظام A"
        assert after["w39"] == before["w39"], "محفظة 39 (user_id=1) لازم ما تتلمسش"
        assert after["w929"] == before["w929"], "محفظة 929 (حساب نظام تينانت 1) لازم ما تتلمسش"
        assert bens_after == {ben_1: PENSION_AMOUNT, ben_2: PENSION_AMOUNT}
        assert len(txs) == 2
        for sender_id, _receiver_id, from_wallet_id, _to_wallet_id, amount in txs:
            assert sender_id == sys_id and from_wallet_id == sys_wallet
            assert from_wallet_id != LEGACY_WALLET_ID and Decimal(str(amount)) == PENSION_AMOUNT
        assert all(h and h.startswith("TX-") for h in payout_hashes)
    finally:
        await _cleanup([tenant_a])
