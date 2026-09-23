"""
regression test لجلسة `insurance-review-claim-double-payment-verification` (2026-09-23).
تقرير الجلسة: .claude/reports/insurance-review-claim-double-payment-verification-session-log.md

يثبّت (DB حقيقية، صفر mock) إن review_claim لا يراجع مطالبة سبق حسمها:
A. approve=true مرتين → الثاني ClaimStatusConflictError (409)، دفعة واحدة فقط.
B. approve=true ثم approve=false → الثاني ClaimStatusConflictError، الحالة تفضل PAID.
C. approve=true مرتين بالتزامن (جلستين منفصلتين، asyncio.gather) → واحد ينجح وواحد
   ClaimStatusConflictError، دفعة واحدة فقط (يمرّن فرع SELECT ... FOR UPDATE + populate_existing).

كل استدعاء في جلسة DB مستقلة (زي طلب HTTP حقيقي). تينانت throwaway خاص بالاختبار
يُحذف بالكامل في finally مع صفوف transactions الخاصة بمستخدميه (الجدول بلا tenant_id) — لا تسرّب أموال،
حتى لو فشل الاختبار على كود غير مُصلَح (mutation check).
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.main import fastapi_app  # noqa: F401
from app.core.database import AsyncSessionLocal
from app.core.errors import ClaimStatusConflictError
from app.core.models import EntityMembership, EntityMembershipRole
from app.domains.academy.models import AcademyTenant
from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.insurance.service import InsuranceService
from app.domains.insurance.models import (
    InsurancePolicy, InsuranceSubscription, InsuranceClaim, PolicyType, PremiumCycle, ClaimStatus,
)
from app.domains.sovereign_entities.models import SovereignEntity, SovereignEntityType

SAAS_SERVICE_ID = 101  # نفس خدمة/خطة SaaS المستخدمة في Batch 0-A وتحقق الجلسة الحي (تشمل insurance)
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
    tenant = AcademyTenant(name=f"REGTEST_RCGUARD_{suffix}", domain=f"regtest-rcguard-{suffix}.local", admin_id=1, is_active=True)
    db.add(tenant)
    await db.commit()
    tid = tenant.id
    s = {"tenant_id": tid}
    s["reviewer"] = await _user(db, tid, "p_rcguard_reviewer", suffix, 500, "SUPER_ADMIN")
    s["claimant"] = await _user(db, tid, "p_rcguard_claimant", suffix, 0)
    entity = SovereignEntity(tenant_id=tid, name=f"REGTEST_RCGUARD_ENTITY_{suffix}", entity_type=SovereignEntityType.ENTERPRISE,
                             country_of_origin="EG", created_by=s["reviewer"], official_email=f"rcguard_ent_{suffix}@example.com")
    db.add(entity)
    await db.commit()
    db.add(EntityMembership(entity_type="SOVEREIGN_ENTITY", entity_id=entity.id, user_id=s["reviewer"],
                            tenant_id=tid, role=EntityMembershipRole.OWNER))
    await db.execute(text("insert into saas_tenant_service_access(tenant_id,service_id,access_level,is_active) values (:t,:p,'BASIC',true)"),
                     {"t": tid, "p": SAAS_SERVICE_ID})
    await db.execute(text("insert into saas_tenant_subscriptions(tenant_id,plan_id,status,idempotency_key) values (:t,:p,'ACTIVE',:k)"),
                     {"t": tid, "p": SAAS_PLAN_ID, "k": f"REGTEST-RCGUARD-SUB-{suffix}"})
    policy = InsurancePolicy(tenant_id=tid, created_by=s["reviewer"], issuer_entity_id=entity.id, name=f"REGTEST_RCGUARD_POLICY_{suffix}",
                             policy_type=PolicyType.ACCIDENT, base_premium_mrusdt=Decimal("0"), premium_cycle=PremiumCycle.MONTHLY,
                             max_coverage_limit_mrusdt=Decimal("1000"))
    db.add(policy)
    await db.commit()
    now = datetime.now(timezone.utc)
    sub = InsuranceSubscription(tenant_id=tid, policy_id=policy.id, subscriber_user_id=s["claimant"], start_date=now, status="ACTIVE",
                                policy_nft_id=f"REGTEST-RCGUARD-NFT-{suffix}", subscription_tx_hash=f"REGTEST-RCGUARD-{suffix}")
    db.add(sub)
    await db.commit()
    s["claims"] = []
    for i in range(n_claims):
        claim = InsuranceClaim(tenant_id=tid, subscription_id=sub.id, claimant_user_id=s["claimant"], incident_date=now,
                               incident_description=f"REGTEST rcguard {i}", claimed_amount_mrusdt=CLAIM_AMOUNT,
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
        # بالمستخدمين لا بالمفتاح: يلتقط أي تحويل مهما كان مفتاحه (مثلًا claim_payout_{id}_{uuid}
        # العشوائي لو الإصلاح اتشال) — وإلا الـFK من transactions لـusers يمنع حذف المستخدمين والتينانت
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


async def _review(s: dict, claim_id: int, approve: bool):
    async with AsyncSessionLocal() as session:
        return await InsuranceService(session).review_claim(
            claim_id=claim_id, reviewer_id=s["reviewer"], tenant_id=s["tenant_id"], approve=approve,
        )


async def _state(s: dict, claim_id: int) -> dict:
    async with AsyncSessionLocal() as db:
        wallets = dict((await db.execute(text(
            "select user_id, (balances->>'MR_USDT')::numeric from wallets where tenant_id=:t and user_id = any(:u)"),
            {"t": s["tenant_id"], "u": [s["reviewer"], s["claimant"]]})).all())
        claim = (await db.execute(text(
            "select status, approved_amount_mrusdt, payout_tx_hash from insurance_claims where id=:c"), {"c": claim_id})).one()
        payouts = (await db.execute(text(
            "select count(*) from transactions where idempotency_key like :k"), {"k": f"claim_payout_{claim_id}%"})).scalar()
        invoices = (await db.execute(text("select count(*) from invoices where tenant_id=:t"), {"t": s["tenant_id"]})).scalar()
    return {"reviewer": wallets[s["reviewer"]], "claimant": wallets[s["claimant"]], "status": claim[0],
            "approved": claim[1], "tx_hash": claim[2], "payouts": payouts, "invoices": invoices}


@pytest.mark.asyncio
async def test_review_claim_approve_twice_pays_once_and_second_call_conflicts(db):
    s = await _seed(db, 1)
    cid = s["claims"][0]
    try:
        first = await _review(s, cid, True)
        assert first.status == ClaimStatus.PAID
        after_first = await _state(s, cid)
        assert after_first["reviewer"] == Decimal("480") and after_first["claimant"] == CLAIM_AMOUNT
        assert after_first["payouts"] == 1

        with pytest.raises(ClaimStatusConflictError) as exc:
            await _review(s, cid, True)
        assert exc.value.status_code == 409

        after_second = await _state(s, cid)
        assert after_second == after_first, "الاستدعاء الثاني لازم ما يحرّكش فلوس ولا يغيّر المطالبة ولا يعمل فاتورة"
    finally:
        await _cleanup(s)


@pytest.mark.asyncio
async def test_review_claim_reject_after_paid_conflicts_and_keeps_paid(db):
    s = await _seed(db, 1)
    cid = s["claims"][0]
    try:
        await _review(s, cid, True)
        after_approve = await _state(s, cid)
        assert after_approve["status"] == "PAID"

        with pytest.raises(ClaimStatusConflictError):
            await _review(s, cid, False)

        after_reject = await _state(s, cid)
        assert after_reject == after_approve, "الرفض بعد PAID لازم يترفض والحالة تفضل PAID متسقة مع الدفع"
        assert after_reject["status"] == "PAID" and after_reject["tx_hash"]
    finally:
        await _cleanup(s)


@pytest.mark.asyncio
async def test_review_claim_concurrent_approves_pay_exactly_once(db):
    s = await _seed(db, 1)
    cid = s["claims"][0]
    try:
        results = await asyncio.gather(_review(s, cid, True), _review(s, cid, True), return_exceptions=True)
        succeeded = [r for r in results if isinstance(r, InsuranceClaim)]
        conflicts = [r for r in results if isinstance(r, ClaimStatusConflictError)]
        assert len(succeeded) == 1 and len(conflicts) == 1, f"متوقَّع نجاح واحد + تعارض واحد، الفعلي: {results!r}"

        final = await _state(s, cid)
        assert final["status"] == "PAID"
        assert final["payouts"] == 1, "دفعة واحدة فقط تحت التزامن"
        assert final["reviewer"] == Decimal("480") and final["claimant"] == CLAIM_AMOUNT
        assert final["invoices"] == 1
    finally:
        await _cleanup(s)
