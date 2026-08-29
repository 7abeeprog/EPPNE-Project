"""
regression test لجلسة #29 (`finance-service-hold-funds-missing`).
تقرير الجلسة: .claude/reports/finance-29-hold-funds-session-log.md

السبب الجذري (كان): tenders_auctions/service.py كانت بتنادي
finance.hold_funds()/finance.release_held_funds() بمعاملات # type:
ignore[attr-defined] — FinanceService ما كانتش عندها الدالتين دول
إطلاقًا (فقط transfer()). أي place_bid/close_auction كان بيفشل
AttributeError.

الإصلاح: أُضيفت 3 دوال لـFinanceService (hold_funds, release_held_funds,
settle_held_funds ذرّية) + عمود Wallet.held_balances (migration 042) +
4 تعديلات في tenders_auctions:
  1. get_live_bids_for_auction بترتب بـbid_amount_mrusdt DESC (مش created_at).
  2. close_auction بتلف على كل المزايدات الحية وتحرر حجز كل خاسر.
  3. idempotency_key ثابت مُشتق من auction_id (مش uuid4 عشوائي) للتسوية.
  4. idempotency_key يتمرر لـrelease_held_funds لكل مزايدة غير فائزة.

ملاحظة عزل (نفس نمط test_realestate_rent_unit_ownership_check.py):
بج منفصل تمامًا وموثَّق سابقًا (`invoicing._generate_invoice_number`
COUNT-based، فجوة رقم فاتورة قديمة تحت tenant_id=1) بيمنع أي
create_invoice() حقيقي لهذا التينانت. صفر لمس على invoicing/service.py؛
الاختبار هنا بيعمل monkeypatch لـ_generate_invoice_number بس (يرجّع رقم
فريد)، عشان نتحقق من hold_funds/release_held_funds/settle_held_funds
و4 إصلاحات tenders_auctions حقيقي 100% بلا التورط في هذا البج المنفصل.
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, select, text, update

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels
from app.core.database import AsyncSessionLocal

from app.domains.invoicing.service import InvoicingService
from app.domains.invoicing.models import Invoice
from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.finance.models import Wallet, Transaction, AuditLog as FinanceAuditLog
from app.domains.finance.repository import WalletRepository
from app.domains.finance.service import FinanceService

from app.domains.tenders_auctions.service import TendersAuctionsService
from app.domains.tenders_auctions.repository import TendersAuctionsRepository
from app.domains.tenders_auctions.models import SovereignAuction, LiveBid, AuctionStatus

TENANT_ID = 1
SYSTEM_EMAIL = "system@eppne.com"


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


async def _fund_wallet(db, user_id: int, mr_usdt: float):
    wallet_repo = WalletRepository(db)
    wallet = await wallet_repo.get_by_user_id(user_id, TENANT_ID)
    await db.execute(
        update(Wallet).where(Wallet.id == wallet.id).values(
            balances={"MR_POUND": 0, "MR_USDT": mr_usdt, "MR7": 0, "NBT": 0, "MRX": 0},
            held_balances={"MR_POUND": 0, "MR_USDT": 0, "MR7": 0, "NBT": 0, "MRX": 0},
        )
    )
    await db.commit()


async def _wallet_state(db, user_id: int) -> dict:
    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id, Wallet.tenant_id == TENANT_ID))
    wallet = result.scalar_one()
    return {"balances": dict(wallet.balances), "held_balances": dict(wallet.held_balances)}


async def _tx_count(db, idempotency_key: str) -> int:
    result = await db.execute(select(Transaction).where(Transaction.idempotency_key == idempotency_key))
    return len(list(result.scalars().all()))


async def _ensure_saas_access(db):
    """Tenders/Auctions SaaS access لـtenant 1 — بنية تحتية دائمة (مش throwaway
    users)، مش هيتم تنظيفها في نهاية الاختبار، نفس فلسفة throwaway-test-users.md
    للبنية التحتية القابلة لإعادة الاستخدام عبر جلسات مستقبلية."""
    for code, service_id in (("tenders", 74), ("auctions", 75)):
        plan = await db.execute(text("SELECT id FROM saas_service_plans WHERE service_id=:sid LIMIT 1"), {"sid": service_id})
        row = plan.first()
        if row:
            plan_id = row[0]
        else:
            res = await db.execute(
                text(
                    """
                    INSERT INTO saas_service_plans
                        (service_id, name, code, price_monthly, price_yearly, currency, is_active, created_at, updated_at)
                    VALUES (:sid, :name, :pcode, 0, 0, 'MR_USDT', true, now(), now())
                    RETURNING id
                    """
                ),
                {"sid": service_id, "name": f"TEST plan {code}", "pcode": f"test-{code}"},
            )
            plan_id = res.scalar()

        access = await db.execute(
            text("SELECT id FROM saas_tenant_service_access WHERE tenant_id=:t AND service_id=:sid"),
            {"t": TENANT_ID, "sid": service_id},
        )
        if not access.first():
            await db.execute(
                text(
                    """
                    INSERT INTO saas_tenant_service_access
                        (tenant_id, service_id, access_level, is_active, created_at, updated_at)
                    VALUES (:t, :sid, 'BASIC', true, now(), now())
                    """
                ),
                {"t": TENANT_ID, "sid": service_id},
            )

        sub = await db.execute(
            text(
                """
                SELECT ts.id FROM saas_tenant_subscriptions ts
                JOIN saas_service_plans sp ON ts.plan_id = sp.id
                WHERE ts.tenant_id=:t AND sp.service_id=:sid AND ts.status IN ('ACTIVE','TRIAL')
                """
            ),
            {"t": TENANT_ID, "sid": service_id},
        )
        if not sub.first():
            await db.execute(
                text(
                    """
                    INSERT INTO saas_tenant_subscriptions
                        (tenant_id, plan_id, status, start_date, auto_renew, payment_method, created_at, updated_at)
                    VALUES (:t, :pid, 'ACTIVE', now(), true, 'WALLET', now(), now())
                    """
                ),
                {"t": TENANT_ID, "pid": plan_id},
            )
    await db.commit()


async def _cleanup(auction_ids, user_ids, system_wallet_id, system_balances_before):
    async with AsyncSessionLocal() as cdb:
        await cdb.execute(delete(FinanceAuditLog).where(FinanceAuditLog.user_id.in_(user_ids)))
        await cdb.execute(delete(Transaction).where(
            Transaction.sender_id.in_(user_ids) | Transaction.receiver_id.in_(user_ids)
        ))
        await cdb.execute(delete(Invoice).where(Invoice.user_id.in_(user_ids)))
        await cdb.execute(delete(LiveBid).where(LiveBid.auction_id.in_(auction_ids)))
        await cdb.execute(delete(SovereignAuction).where(SovereignAuction.id.in_(auction_ids)))
        await cdb.execute(delete(User).where(User.id.in_(user_ids)))  # Wallet ondelete=CASCADE
        # استرجاع رصيد حساب النظام (persistent، مش throwaway) لقيمته الأصلية بالضبط
        await cdb.execute(
            update(Wallet).where(Wallet.id == system_wallet_id).values(balances=system_balances_before)
        )
        await cdb.commit()


@pytest.mark.asyncio
async def test_transfer_idempotency_key_retry_returns_same_transaction(db):
    """regression مستقل لباج finance-transaction-idempotency-key-lookup-
    multiple-results (مُكتشف أثناء جلسة #29، لكنه كامن في transfer() نفسها
    من قبلها بكتير — راجع PROGRESS_LOG.md). transfer() بتنشئ Transaction
    بـsender_id+receiver_id معًا (زي settle_held_funds بالضبط) — قبل
    إصلاح get_by_idempotency_key، أي retry حقيقي بنفس idempotency_key كان
    بيكسر MultipleResultsFound بدل ما يرجع نفس المعاملة القديمة بأمان."""
    sender = await _create_user(db, "p_regtest_txidem_sender")
    receiver = await _create_user(db, "p_regtest_txidem_receiver")
    user_ids = [sender.id, receiver.id]

    try:
        await _fund_wallet(db, sender.id, 500)

        service = FinanceService(db, TENANT_ID)
        idempotency_key = f"REGTEST-TXIDEM-{_suffix()}"

        tx1 = await service.transfer(
            sender_id=sender.id, receiver_email=receiver.email,
            currency="MR_USDT", amount=Decimal("50"),
            idempotency_key=idempotency_key,
        )
        # transfer() بتستخدم begin_nested() (SAVEPOINT) بس — زي الراوتر
        # الحقيقي (finance/router.py:57) لازم commit حقيقي هنا، وإلا القفل
        # على صفوف wallets يفضل ممسوك طول الجلسة ويعلّق أي عملية تانية
        # (زي _cleanup في finally) بتحاول تلمس نفس الصفوف من جلسة تانية.
        await db.commit()

        # Retry حقيقي — نفس idempotency_key بالضبط، معاملة بطرفين (sender+receiver)
        tx2 = await service.transfer(
            sender_id=sender.id, receiver_email=receiver.email,
            currency="MR_USDT", amount=Decimal("50"),
            idempotency_key=idempotency_key,
        )
        await db.commit()

        assert tx1.id == tx2.id, "FAIL: الـretry رجّع معاملة مختلفة بدل نفس المعاملة القديمة"

        sender_state = await _wallet_state(db, sender.id)
        receiver_state = await _wallet_state(db, receiver.id)
        assert sender_state["balances"]["MR_USDT"] == 450.0, "FAIL: خُصم المبلغ مرتين فعليًا (تحويل مزدوج)"
        assert receiver_state["balances"]["MR_USDT"] == 50.0, "FAIL: المستلم استلم أكتر من مرة"

        assert await _tx_count(db, idempotency_key) == 1, "FAIL: صف معاملة مكرر فعليًا في transactions"
    finally:
        await _cleanup([], user_ids, None, None)


@pytest.mark.asyncio
async def test_ordering_fix_uses_bid_amount_not_recency(db):
    """اكتشاف A: get_live_bids_for_auction لازم يرتب بالقيمة، مش بالزمن."""
    creator = await _create_user(db, "p_regtest_auction29_creator")
    b1 = await _create_user(db, "p_regtest_auction29_b1")
    b2 = await _create_user(db, "p_regtest_auction29_b2")
    b3 = await _create_user(db, "p_regtest_auction29_b3")
    user_ids = [creator.id, b1.id, b2.id, b3.id]
    auction_ids = []

    try:
        repo = TendersAuctionsRepository(db)
        auction = await repo.create_auction(
            tenant_id=TENANT_ID, created_by=creator.id,
            title="REGTEST-29 ordering probe", description="probe",
            asset_type="TEST", asset_id=None,
            start_price_mrusdt=Decimal("10"), min_increment_mrusdt=Decimal("0"),
            start_time=datetime.now(timezone.utc) - timedelta(hours=1),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            status=AuctionStatus.OPEN,
        )
        auction_ids.append(auction.id)

        # القيمة الأعلى (300) = الأقدم زمنيًا، القيمة الأقل (200) = الأحدث.
        specs = [(b1.id, Decimal("100"), 20), (b2.id, Decimal("300"), 30), (b3.id, Decimal("200"), 10)]
        for bidder_id, amount, age_seconds in specs:
            bid = await repo.create_live_bid(
                tenant_id=TENANT_ID, auction_id=auction.id, bidder_id=bidder_id,
                bid_amount_mrusdt=amount, bid_tx_hash=f"REGTEST29-{bidder_id}",
            )
            await db.execute(
                update(LiveBid).where(LiveBid.id == bid.id).values(
                    created_at=datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
                )
            )
        await db.commit()

        ordered = await repo.get_live_bids_for_auction(auction.id)
        assert float(ordered[0].bid_amount_mrusdt) == 300.0, (
            f"FAIL: أول عنصر لازم يكون 300 (الأعلى قيمة) — رجع {ordered[0].bid_amount_mrusdt}"
        )
        assert float(ordered[1].bid_amount_mrusdt) == 200.0
        assert float(ordered[2].bid_amount_mrusdt) == 100.0
    finally:
        system_wallet_id, system_before = await _capture_system_wallet(db)
        await _cleanup(auction_ids, user_ids, system_wallet_id, system_before)


async def _capture_system_wallet(db):
    user_rows = list((await db.execute(select(User.id, User.email, User.tenant_id).where(User.email == SYSTEM_EMAIL))).all())
    system_user_id = user_rows[0][0]
    wallet_rows = list((await db.execute(
        select(Wallet.id, Wallet.user_id, Wallet.tenant_id, Wallet.balances).where(Wallet.user_id == system_user_id, Wallet.tenant_id == TENANT_ID)
    )).all())
    assert len(wallet_rows) == 1, (
        f"FAIL: توقعت محفظة واحدة بالضبط لحساب النظام (user_id={system_user_id}, tenant_id={TENANT_ID})، "
        f"لكن وُجد {len(wallet_rows)} — {wallet_rows}"
    )
    wallet_row = wallet_rows[0]
    return wallet_row[0], dict(wallet_row[3])


@pytest.mark.asyncio
async def test_full_pipeline_win_lose_and_close_auction_retry(db, monkeypatch):
    """اكتشافات B/C/D مجتمعة: حجز حي 3 مزايدين → إغلاق (فوز/خسارة) → retry
    idempotency فعلي. monkeypatch لـ_generate_invoice_number فقط (بج
    invoicing منفصل تمامًا، راجع docstring أعلى الملف)."""

    async def _unique_invoice_number(self, tenant_id):
        return f"INV-REGTEST-AUCTION29-{_suffix()}"

    monkeypatch.setattr(InvoicingService, "_generate_invoice_number", _unique_invoice_number)

    creator = await _create_user(db, "p_regtest_auction29b_creator")
    loser1 = await _create_user(db, "p_regtest_auction29b_loser1")
    loser2 = await _create_user(db, "p_regtest_auction29b_loser2")
    winner = await _create_user(db, "p_regtest_auction29b_winner")
    user_ids = [creator.id, loser1.id, loser2.id, winner.id]
    auction_ids = []

    await _ensure_saas_access(db)

    system_wallet_id, system_before = await _capture_system_wallet(db)

    try:
        await _fund_wallet(db, loser1.id, 1000)
        await _fund_wallet(db, loser2.id, 1000)
        await _fund_wallet(db, winner.id, 1000)

        service = TendersAuctionsService(db)
        repo = TendersAuctionsRepository(db)

        auction = await repo.create_auction(
            tenant_id=TENANT_ID, created_by=creator.id,
            title="REGTEST-29 full pipeline", description="probe",
            asset_type="TEST", asset_id=None,
            start_price_mrusdt=Decimal("10"), min_increment_mrusdt=Decimal("5"),
            start_time=datetime.now(timezone.utc) - timedelta(hours=1),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            status=AuctionStatus.OPEN,
        )
        auction_id = auction.id
        auction_ids.append(auction_id)

        bid1 = await service.place_bid(loser1.id, TENANT_ID, auction_id, Decimal("100"))
        state = await _wallet_state(db, loser1.id)
        assert state["balances"]["MR_USDT"] == 900.0
        assert state["held_balances"]["MR_USDT"] == 100.0

        bid2 = await service.place_bid(loser2.id, TENANT_ID, auction_id, Decimal("150"))
        state = await _wallet_state(db, loser2.id)
        assert state["balances"]["MR_USDT"] == 850.0
        assert state["held_balances"]["MR_USDT"] == 150.0

        bid3 = await service.place_bid(winner.id, TENANT_ID, auction_id, Decimal("220"))
        state = await _wallet_state(db, winner.id)
        assert state["balances"]["MR_USDT"] == 780.0
        assert state["held_balances"]["MR_USDT"] == 220.0

        # ===== close_auction — المحاولة الأولى =====
        result1 = await service.close_auction(auction_id, creator.id, TENANT_ID)
        assert result1["winner_id"] == winner.id
        assert float(result1["final_price"]) == 220.0

        loser1_after = await _wallet_state(db, loser1.id)
        loser2_after = await _wallet_state(db, loser2.id)
        winner_after = await _wallet_state(db, winner.id)
        system_after1 = (await _capture_system_wallet(db))[1]

        assert loser1_after["balances"]["MR_USDT"] == 1000.0, "الخاسر1 لازم يسترجع حجزه بالكامل"
        assert loser1_after["held_balances"]["MR_USDT"] == 0.0
        assert loser2_after["balances"]["MR_USDT"] == 1000.0, "الخاسر2 لازم يسترجع حجزه بالكامل"
        assert loser2_after["held_balances"]["MR_USDT"] == 0.0

        assert winner_after["balances"]["MR_USDT"] == 780.0, "رصيد الفائز لازم يفضل كما بعد الحجز (لا يرجع لـ1000 وسط الطريق ولا يقل تاني)"
        assert winner_after["held_balances"]["MR_USDT"] == 0.0

        delta1 = float(system_after1["MR_USDT"]) - float(system_before["MR_USDT"])
        assert delta1 == 220.0, f"النظام لازم يستلم 220 بالضبط (استلم {delta1})"

        assert await _tx_count(db, f"AUCTION-SALE-{auction_id}") == 1
        assert await _tx_count(db, f"AUCTION-RELEASE-{auction_id}-{bid1.id}") == 1
        assert await _tx_count(db, f"AUCTION-RELEASE-{auction_id}-{bid2.id}") == 1

        # ===== close_auction — Retry (نفس المزاد، نفس المستخدمين) =====
        result2 = await service.close_auction(auction_id, creator.id, TENANT_ID)

        loser1_after2 = await _wallet_state(db, loser1.id)
        winner_after2 = await _wallet_state(db, winner.id)
        system_after2 = (await _capture_system_wallet(db))[1]

        delta2 = float(system_after2["MR_USDT"]) - float(system_after1["MR_USDT"])
        assert delta2 == 0.0, f"FAIL: تحويل مزدوج فعلي حصل عند الـretry! دلتا={delta2}"
        assert winner_after2["balances"]["MR_USDT"] == 780.0, "رصيد الفائز اتغيّر بعد الـretry"
        assert loser1_after2["balances"]["MR_USDT"] == 1000.0, "رصيد الخاسر1 اتغيّر بعد الـretry"

        assert await _tx_count(db, f"AUCTION-SALE-{auction_id}") == 1, "معاملة تسوية مكررة فعليًا"
        assert await _tx_count(db, f"AUCTION-RELEASE-{auction_id}-{bid1.id}") == 1, "معاملة تحرير مكررة فعليًا"
    finally:
        await _cleanup(auction_ids, user_ids, system_wallet_id, system_before)
