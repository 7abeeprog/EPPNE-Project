"""
regression test لجلسة `insurance-review-claim-negative-approved-amount-reverses-transfer` (2026-09-23).
تقرير الجلسة: .claude/reports/insurance-negative-approved-amount-verification-session-log.md

يثبّت (DB حقيقية، صفر mock) إن FinanceService يرفض أي مبلغ <= 0 قبل أي SQL:
A. transfer / hold_funds / release_held_funds / settle_held_funds بمبلغ -10 أو 0 → ValidationError (422)،
   صفر عبارات SQL أثناء الاستدعاء، الأرصدة بلا تغيير. (قبل الإصلاح: IntegrityError من CHECK في DB → 500.)
B. review_claim بـapproved_amount=-50 → ValidationError، المطالبة تفضل SUBMITTED، لا دفع.
C. PUT /api/insurance/claims/{id}/review بـapproved_amount=-50 أو 0 → 422 (قيد gt=0 على الـQuery).
D. الموافقة بمبلغ موجب (50) لسه بتدفع صح.

تينانت throwaway خاص بالاختبار يُحذف بالكامل في finally مع صفوف transactions الخاصة بمستخدميه.
"""
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import event, text

from app.main import fastapi_app
from app.api.deps import get_current_active_user
from app.core.database import AsyncSessionLocal, engine
from app.core.errors import ValidationError
from app.core.models import EntityMembership, EntityMembershipRole
from app.domains.academy.models import AcademyTenant
from app.domains.finance.service import FinanceService
from app.domains.identity.models import User
from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.insurance.service import InsuranceService
from app.domains.insurance.models import (
    InsurancePolicy, InsuranceSubscription, InsuranceClaim, PolicyType, PremiumCycle, ClaimStatus,
)
from app.domains.sovereign_entities.models import SovereignEntity, SovereignEntityType

SAAS_SERVICE_ID = 101  # نفس خدمة/خطة SaaS المستخدمة في test_insurance_review_claim_status_guard.py
SAAS_PLAN_ID = 101
CLAIM_AMOUNT = Decimal("20")


def _balances(mr_usdt) -> str:
    return json.dumps({"MR7": 0, "MRX": 0, "NBT": 0, "MR_USDT": mr_usdt, "MR_POUND": 0, "LOYALTY_POINTS": 0})


async def _user(db, tenant_id: int, prefix: str, suffix: str, mr_usdt, role=None) -> int:
    uname = f"{prefix}_{suffix}"
    user = await UserService(db, tenant_id).register(
        UserCreate(username=uname, email=f"{uname}@example.com", password="TempPass123!"),
        idempotency_key=f"REGTEST-{uname}",
    )
    if role:
        await db.execute(text("update users set system_role=:r where id=:i"), {"r": role, "i": user.id})
    await db.execute(text("""insert into wallets(user_id,tenant_id,balances,is_frozen,is_custodial)
        select :u,:t,cast(:b as jsonb),false,true where not exists (select 1 from wallets where user_id=:u and tenant_id=:t)"""),
        {"u": user.id, "t": tenant_id, "b": _balances(mr_usdt)})
    await db.execute(text("update wallets set balances=cast(:b as jsonb) where user_id=:u and tenant_id=:t"),
                     {"u": user.id, "t": tenant_id, "b": _balances(mr_usdt)})
    await db.commit()
    return user.id


async def _seed(db, n_claims: int) -> dict:
    suffix = uuid.uuid4().hex[:8]
    tenant = AcademyTenant(name=f"REGTEST_NEGGUARD_{suffix}", domain=f"regtest-negguard-{suffix}.local", admin_id=1, is_active=True)
    db.add(tenant)
    await db.commit()
    tid = tenant.id
    s = {"tenant_id": tid}
    s["reviewer"] = await _user(db, tid, "p_negguard_reviewer", suffix, 500, "SUPER_ADMIN")
    s["claimant"] = await _user(db, tid, "p_negguard_claimant", suffix, 100)
    s["claimant_email"] = f"p_negguard_claimant_{suffix}@example.com"
    entity = SovereignEntity(tenant_id=tid, name=f"REGTEST_NEGGUARD_ENTITY_{suffix}", entity_type=SovereignEntityType.ENTERPRISE,
                             country_of_origin="EG", created_by=s["reviewer"], official_email=f"negguard_ent_{suffix}@example.com")
    db.add(entity)
    await db.commit()
    db.add(EntityMembership(entity_type="SOVEREIGN_ENTITY", entity_id=entity.id, user_id=s["reviewer"],
                            tenant_id=tid, role=EntityMembershipRole.OWNER))
    await db.execute(text("insert into saas_tenant_service_access(tenant_id,service_id,access_level,is_active) values (:t,:p,'BASIC',true)"),
                     {"t": tid, "p": SAAS_SERVICE_ID})
    await db.execute(text("insert into saas_tenant_subscriptions(tenant_id,plan_id,status,idempotency_key) values (:t,:p,'ACTIVE',:k)"),
                     {"t": tid, "p": SAAS_PLAN_ID, "k": f"REGTEST-NEGGUARD-SUB-{suffix}"})
    policy = InsurancePolicy(tenant_id=tid, created_by=s["reviewer"], issuer_entity_id=entity.id, name=f"REGTEST_NEGGUARD_POLICY_{suffix}",
                             policy_type=PolicyType.ACCIDENT, base_premium_mrusdt=Decimal("0"), premium_cycle=PremiumCycle.MONTHLY,
                             max_coverage_limit_mrusdt=Decimal("1000"))
    db.add(policy)
    await db.commit()
    now = datetime.now(timezone.utc)
    sub = InsuranceSubscription(tenant_id=tid, policy_id=policy.id, subscriber_user_id=s["claimant"], start_date=now, status="ACTIVE",
                                policy_nft_id=f"REGTEST-NEGGUARD-NFT-{suffix}", subscription_tx_hash=f"REGTEST-NEGGUARD-{suffix}")
    db.add(sub)
    await db.commit()
    s["claims"] = []
    for i in range(n_claims):
        claim = InsuranceClaim(tenant_id=tid, subscription_id=sub.id, claimant_user_id=s["claimant"], incident_date=now,
                               incident_description=f"REGTEST negguard {i}", claimed_amount_mrusdt=CLAIM_AMOUNT,
                               status=ClaimStatus.SUBMITTED)
        db.add(claim)
        await db.commit()
        s["claims"].append(claim.id)
    return s


async def _cleanup(s: dict) -> None:
    """يحذف صفوف transactions الخاصة بمستخدمي الاختبار (الجدول بلا tenant_id) ثم كل صفوف
    التينانت (كل جدول فيه tenant_id، بجولات لحل ترتيب الـFK) ثم التينانت نفسه."""
    tid = s["tenant_id"]
    async with AsyncSessionLocal() as db:
        user_ids = [s[k] for k in ("reviewer", "claimant") if k in s]
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
                        await db.execute(text(f'delete from "{table}" where tenant_id = :t'), {"t": tid})
                except Exception:
                    failed.append(table)
            await db.commit()
            if not failed:
                break
            tables = failed
        await db.execute(text("delete from academy_tenants where id = :t"), {"t": tid})
        await db.commit()


async def _state(s: dict) -> dict:
    async with AsyncSessionLocal() as db:
        wallets = {r[0]: (r[1], r[2]) for r in (await db.execute(text(
            "select user_id, balances, held_balances from wallets where tenant_id=:t and user_id = any(:u)"),
            {"t": s["tenant_id"], "u": [s["reviewer"], s["claimant"]]})).all()}
        claims = dict((await db.execute(text(
            "select id, status from insurance_claims where id = any(:c)"), {"c": s["claims"]})).all())
        txs = (await db.execute(text(
            "select count(*) from transactions where sender_id = any(:u) or receiver_id = any(:u)"),
            {"u": [s["reviewer"], s["claimant"]]})).scalar()
    return {"wallets": wallets, "claims": claims, "tx_rows": txs}


async def _http_review(s: dict, claim_id: int, approved_amount: str) -> httpx.Response:
    async def _reviewer():
        async with AsyncSessionLocal() as session:
            return await session.get(User, s["reviewer"])
    fastapi_app.dependency_overrides[get_current_active_user] = _reviewer
    try:
        # الـhost لازم يكون ضمن ALLOWED_HOSTS وإلا TrustedHostMiddleware يرجّع 400 قبل الـendpoint
        transport = httpx.ASGITransport(app=fastapi_app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
            return await client.put(f"/api/insurance/claims/{claim_id}/review",
                                    params={"approve": "true", "approved_amount": approved_amount})
    finally:
        fastapi_app.dependency_overrides.pop(get_current_active_user, None)


def _finance_call(s: dict, fn: str, amount: Decimal):
    key = f"NEGGUARD-{fn}-{uuid.uuid4().hex[:8]}"
    kwargs = {
        "transfer": dict(sender_id=s["reviewer"], receiver_email=s["claimant_email"], currency="MR_USDT", amount=amount, idempotency_key=key),
        "hold_funds": dict(user_id=s["reviewer"], amount=amount, currency="MR_USDT", description="negguard", idempotency_key=key),
        "release_held_funds": dict(user_id=s["reviewer"], amount=amount, currency="MR_USDT", description="negguard", idempotency_key=key),
        "settle_held_funds": dict(sender_id=s["reviewer"], receiver_email=s["claimant_email"], currency="MR_USDT", amount=amount, idempotency_key=key),
    }[fn]

    async def _call():
        async with AsyncSessionLocal() as session:
            return await getattr(FinanceService(session, s["tenant_id"]), fn)(**kwargs)
    return _call


@pytest.mark.asyncio
@pytest.mark.parametrize("fn", ["transfer", "hold_funds", "release_held_funds", "settle_held_funds"])
@pytest.mark.parametrize("amount", [Decimal("-10"), Decimal("0")])
async def test_finance_rejects_non_positive_amount_before_any_sql(db, fn, amount):
    s = await _seed(db, 0)
    statements = []

    def _capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    try:
        before = await _state(s)
        event.listen(engine.sync_engine, "before_cursor_execute", _capture)
        try:
            with pytest.raises(ValidationError) as exc:
                await _finance_call(s, fn, amount)()
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", _capture)
        assert exc.value.status_code == 422
        assert statements == [], f"{fn}({amount}) لازم يترفض قبل أي SQL (لا أقفال ولا UPDATE)"
        assert await _state(s) == before
    finally:
        await _cleanup(s)


@pytest.mark.asyncio
async def test_review_claim_negative_approved_amount_rejected_without_payout(db):
    s = await _seed(db, 1)
    cid = s["claims"][0]
    try:
        before = await _state(s)
        with pytest.raises(ValidationError):
            async with AsyncSessionLocal() as session:
                await InsuranceService(session).review_claim(
                    claim_id=cid, reviewer_id=s["reviewer"], tenant_id=s["tenant_id"], approve=True,
                    approved_amount=Decimal("-50"),
                )
        after = await _state(s)
        assert after == before
        assert after["claims"][cid] == "SUBMITTED"
    finally:
        await _cleanup(s)


@pytest.mark.asyncio
async def test_review_claim_endpoint_rejects_non_positive_approved_amount_and_pays_positive(db):
    s = await _seed(db, 2)
    rejected_cid, paid_cid = s["claims"]
    try:
        before = await _state(s)
        for amount in ("-50", "0"):
            resp = await _http_review(s, rejected_cid, amount)
            assert resp.status_code == 422, resp.text
        assert await _state(s) == before

        resp = await _http_review(s, paid_cid, "50")
        assert resp.status_code == 200, resp.text
        after = await _state(s)
        assert after["claims"][paid_cid] == "PAID" and after["claims"][rejected_cid] == "SUBMITTED"
        assert Decimal(str(after["wallets"][s["reviewer"]][0]["MR_USDT"])) == Decimal("450")
        assert Decimal(str(after["wallets"][s["claimant"]][0]["MR_USDT"])) == Decimal("150")
        assert after["tx_rows"] == before["tx_rows"] + 1
    finally:
        await _cleanup(s)
