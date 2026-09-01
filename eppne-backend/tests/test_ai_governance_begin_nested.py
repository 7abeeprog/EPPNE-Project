"""
regression test لجلسة `ai-governance-check-and-consume-begin-nested`.
تقرير الجلسة: .claude/reports/ai-governance-check-and-consume-begin-nested-session-log.md

السبب الجذري (كان): `AIGovernanceService.check_and_consume()`
(`ai_governance/service.py:146-205`) — نفس فئة عيب `execute_agent_action()`
الموثَّق سابقًا (`.claude/reports/backlog-16-begin-nested-commit-session-log.md`):
وحدة معاملة مستقلة بذاتها (`async with self.db.begin_nested(): ... ; await
self.db.commit()`). **الفرق البنيوي عن execute_agent_action:** هنا الدالة
بتفتح `begin_nested()` **خاصة بيها هي** (سطر 165) وتغلقها بشكل طبيعي قبل
الـ`commit()` (سطر 203) — فالاستثناء **لا** يحدث عند نداء `check_and_consume()`
نفسه، بل عند **أول عملية DB تالية** جوّه أي `begin_nested()` خارجي محيط
(`InvalidRequestError: Can't operate on closed transaction inside context
manager`)، مؤكَّد حيًا بسكربت throwaway مستقل قبل هذا الإصلاح.

**جرد كامل (15 موضع استدعاء، 14 دومين + الراوتر):** 14 مستقلون تمامًا
(يعتمدون على الـ`commit()` الداخلي، بلا `begin_nested()` خارجي محيط) —
موضع واحد بس متأثر: `realestate.buy_fractional_ownership()` (عبر
`_check_ai_governance()`، سطر 303 القديم، جوّه `begin_nested()` الخاص
بالشراء نفسه).

**الإصلاح المُطبَّق:** نفس نمط إصلاح `execute_agent_action` في نفس الدالة
بالحرف (اتصلح أمس، `backlog-16-begin-nested-commit-conflict`) — نقل نداء
`self._check_ai_governance(...)` بره حدود `begin_nested()`، لبعد
`self.db.commit()` الرئيسي مباشرة (بجوار `ai.execute_agent_action` الموجودة
هناك بالفعل)، **بلا** `try/except` إضافية (الدالة عندها واحدة داخلية أصلًا).
صفر لمس على `check_and_consume()` نفسها — الـ14 كولر المستقل لسه محتاجين
الـ`commit()` الداخلي بالضبط زي قبل.

**ليه مفيش اختبار "نداء check_and_consume() جوّه begin_nested() وينجح":**
`check_and_consume()` نفسها **لم تُعدَّل عمدًا** (نفس القرار المعماري
لـ`execute_agent_action`) — نداؤها من جوّه أي `begin_nested()` خارجي **لسه
غير آمن بالتصميم**؛ هذا بالضبط سبب نقل موضع النداء بدل تعديل الدالة
المشتركة. الاختبار (ب) تحت بيثبت الشكل الصحيح الوحيد: نداء مستقل (بلا
`begin_nested()` خارجي)، بالظبط زي الـ14 دومين الآخرين.

**بيانات throwaway:** `tenant_id=1`، وكيل AI بمعرّف ثابت `id=2` (نفس معرّف
`execute_agent_action`/`_check_ai_governance` المُثبَّت في كود realestate)،
مستخدمين throwaway جدد. تنظيف كامل في `finally`.
"""
import json
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import delete, select, text

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.ai_agents.models import AIAgent, AgentRole, AgentStatus, AITaskLog, AgentApprovalQueue
from app.domains.ai_governance.service import AIGovernanceService
from app.domains.ai_governance.models import AgentUsageLog
from app.services.ai import ai_engine

from app.domains.realestate.service import RealEstateService
from app.domains.realestate.repository import RealEstateRepository
from app.domains.realestate.models import RealEstateDevelopment, PropertyUnit, PropertyType, PropertyOwnership
from app.domains.finance.models import Wallet, Transaction
from app.domains.invoicing.service import InvoicingService

TENANT_ID = 1
EXISTING_LAND_ASSET_ID = 1


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


async def _fake_generate(*args, **kwargs):
    """تجاوز بج غير مرتبط (Backlog #7، redis_client.hincrbyfloat مفقودة) —
    نفس التجاوز المستخدَم في test_ai_agents_execute_action.py."""
    return {"text": "regtest-mock-ai-response", "cost_mrusdt": Decimal("0.0"), "model_used": "regtest-mock"}


async def _noop_create_invoice(self, *args, **kwargs):
    """عزل عن باج معروف مسبقًا وغير مرتبط (invoice-numbering collision،
    راجع commit b4bf356) — نفس العزل المستخدَم في test_ai_agents_execute_action.py."""
    return None


# ============================================================
# 1) (أ) مسار شرعي كامل — buy_fractional_ownership() الحقيقية، بلا أي
#    monkeypatch على _check_ai_governance/check_and_consume (خلافًا للاختبار
#    الموجود في test_ai_agents_execute_action.py اللي بيعزلها عمدًا). لازم
#    كل العمليات داخل begin_nested (owner lookup, finance.transfer,
#    create_ownership, ...) تنجح بلا InvalidRequestError، وحوكمة الـAI
#    (بعد الـcommit) تُسجِّل استهلاكها فعليًا.
# ============================================================

@pytest.mark.asyncio
async def test_buy_fractional_ownership_full_flow_succeeds_with_real_ai_governance(db, monkeypatch):
    monkeypatch.setattr(InvoicingService, "create_invoice", _noop_create_invoice)
    monkeypatch.setattr(ai_engine, "generate", _fake_generate)

    # buy_fractional_ownership() بتستخدم agent_id=2 مُثبَّت (لكل من
    # _check_ai_governance وexecute_agent_action) — لازم وكيل حقيقي بنفس
    # المعرّف عشان نوصل للمسار الحقيقي (مش NotFoundError).
    existing = (await db.execute(select(AIAgent).where(AIAgent.id == 2))).scalar_one_or_none()
    assert existing is None, "وكيل بمعرّف 2 موجود بالفعل — الاختبار مش آمن يكمل، افحص يدويًا"

    owner = await _create_user(db, "p_regtest_gov_bn_re_owner")
    owner_id = owner.id
    agent = AIAgent(
        id=2, tenant_id=TENANT_ID, owner_id=owner_id,
        name=f"REGTEST-GOVBN-AGENT-{_suffix()}",
        role=AgentRole.SALES_NEGOTIATOR, status=AgentStatus.ACTIVE,
        system_prompt="regtest throwaway agent (fixed id=2)",
        requires_human_approval=True,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    re_repo = RealEstateRepository(db)
    development = await re_repo.create_development(
        tenant_id=TENANT_ID, land_asset_id=EXISTING_LAND_ASSET_ID,
        name=f"REGTEST-GOVBN-DEV-{_suffix()}", development_type="RESIDENTIAL",
    )
    development_id = development.id
    unit = await re_repo.create_unit(
        tenant_id=TENANT_ID, development_id=development_id,
        unit_number=f"REGTEST-GOVBN-UNIT-{_suffix()}", area_sqm=Decimal("100"),
        property_type=PropertyType.APARTMENT,
        is_available_for_sale=True, is_available_for_rent=False,
        sale_price_mrusdt=Decimal("1000"),
    )
    unit_id = unit.id
    buyer = await _create_user(db, "p_regtest_gov_bn_buyer")
    buyer_id = buyer.id
    await db.execute(
        text("UPDATE wallets SET balances = CAST(:b AS JSONB) WHERE user_id = :uid AND tenant_id = :tid"),
        {
            "b": json.dumps({"MR_POUND": 0, "MR_USDT": 1000, "MR7": 0, "NBT": 0, "MRX": 0}),
            "uid": buyer_id, "tid": TENANT_ID,
        },
    )
    await db.commit()

    seller_id_row = (await db.execute(
        text("SELECT owner_id FROM land_assets WHERE id = :lid"), {"lid": EXISTING_LAND_ASSET_ID}
    )).first()
    seller_id = seller_id_row[0]
    seller_wallet_before = (await db.execute(
        select(Wallet).where(Wallet.user_id == seller_id, Wallet.tenant_id == TENANT_ID)
    )).scalar_one_or_none()
    seller_balances_snapshot = dict(seller_wallet_before.balances) if seller_wallet_before else None

    service = RealEstateService(db)

    try:
        ownership = await service.buy_fractional_ownership(
            buyer_id=buyer_id, tenant_id=TENANT_ID, unit_id=unit_id,
            percentage=Decimal("10"), idempotency_key=f"REGTEST-GOVBN-BUY-{_suffix()}",
        )
        # (أ) المسار الشرعي الكامل نجح فعليًا بلا InvalidRequestError
        assert ownership is not None
        assert ownership.owner_user_id == buyer_id

        # (ب) العمليات اللي كانت جوّه begin_nested *بعد* موضع الفحص القديم
        #     (owner lookup, finance.transfer, create_ownership) اتنفذت
        #     فعليًا ونجحت بلا انهيار — الدليل المباشر إن begin_nested كمّل
        #     بسلام لآخره
        db_ownership = (await db.execute(
            select(PropertyOwnership).where(PropertyOwnership.unit_id == unit_id)
        )).scalar_one()
        assert db_ownership.owner_user_id == buyer_id
        assert db_ownership.ownership_percentage == Decimal("10")

        transfer = (await db.execute(
            select(Transaction).where(Transaction.sender_id == buyer_id)
        )).scalar_one_or_none()
        assert transfer is not None, "finance.transfer() (جوّه begin_nested) لازم تكون اتنفذت فعليًا"

        # الدليل الحاسم: check_and_consume() (بعد النقل، بعد commit() الرئيسي)
        # اتنفذت فعليًا بلا InvalidRequestError — usage_log حقيقي اتسجل
        usage_logs = (await db.execute(
            select(AgentUsageLog).where(AgentUsageLog.agent_id == 2, AgentUsageLog.tenant_id == TENANT_ID)
        )).scalars().all()
        assert len(usage_logs) == 1, "check_and_consume() لازم تكون اتنفذت فعليًا بعد commit() الرئيسي"
        assert usage_logs[0].action_type == "FRACTIONAL_PURCHASE"
        assert usage_logs[0].user_id == buyer_id

        # execute_agent_action() (بعد commit() برضه، بجوار check_and_consume)
        # لازم تكون اتنفذت فعليًا هي كمان بنفس النجاح
        task_logs = (await db.execute(
            select(AITaskLog).where(AITaskLog.agent_id == 2, AITaskLog.tenant_id == TENANT_ID)
        )).scalars().all()
        assert len(task_logs) == 1
    finally:
        try:
            await db.rollback()
        except Exception:
            pass
        await db.execute(delete(AgentUsageLog).where(AgentUsageLog.agent_id == 2))
        await db.execute(delete(AgentApprovalQueue).where(AgentApprovalQueue.agent_id == 2))
        await db.execute(delete(AITaskLog).where(AITaskLog.agent_id == 2))
        await db.execute(delete(PropertyOwnership).where(PropertyOwnership.unit_id == unit_id))
        await db.execute(delete(PropertyUnit).where(PropertyUnit.id == unit_id))
        await db.execute(delete(RealEstateDevelopment).where(RealEstateDevelopment.id == development_id))
        await db.execute(delete(AIAgent).where(AIAgent.id == 2))
        await db.execute(delete(Transaction).where(Transaction.sender_id == buyer_id))
        await db.execute(delete(Wallet).where(Wallet.user_id == buyer_id))
        await db.execute(text("DELETE FROM audit_logs WHERE user_id = :uid"), {"uid": buyer_id})
        await db.execute(text("DELETE FROM notifications WHERE user_id = :uid"), {"uid": buyer_id})
        if seller_balances_snapshot is not None:
            await db.execute(
                text("UPDATE wallets SET balances = CAST(:b AS JSONB) WHERE user_id = :uid AND tenant_id = :tid"),
                {"b": json.dumps(seller_balances_snapshot, default=str), "uid": seller_id, "tid": TENANT_ID},
            )
        await db.commit()
        await db.execute(delete(User).where(User.id == buyer_id))
        await db.execute(delete(User).where(User.id == owner_id))
        await db.commit()


# ============================================================
# 2) (ب) نداء مستقل (بلا begin_nested() خارجي) + عملية DB تالية في نفس
#    الجلسة — الشكل الصحيح الوحيد المدعوم، بالظبط زي الـ14 دومين الآخرين
#    (zamakana, transport, tourism_sports, tenders_auctions, social,
#    service_marketplace, manufacturing×2, command, logistics,
#    arbitration_syndicates, invitations, insurance, router).
# ============================================================

@pytest.mark.asyncio
async def test_check_and_consume_independent_call_then_followup_select_succeeds(db):
    owner = await _create_user(db, "p_regtest_gov_bn_indep_owner")
    owner_id = owner.id
    agent = AIAgent(
        tenant_id=TENANT_ID, owner_id=owner_id,
        name=f"REGTEST-GOVBN-INDEP-AGENT-{_suffix()}",
        role=AgentRole.SALES_NEGOTIATOR, status=AgentStatus.ACTIVE,
        system_prompt="regtest throwaway agent",
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    agent_id = agent.id

    governance = AIGovernanceService(db, TENANT_ID)
    try:
        result = await governance.check_and_consume(
            agent_id=agent_id, user_id=owner_id, action_type="REGTEST_INDEPENDENT",
            tokens=10, cost=Decimal("0.01"),
        )
        assert result is True

        # عملية DB تالية في نفس الجلسة مباشرة بعد check_and_consume()، بلا
        # begin_nested() خارجي محيط — لازم تنجح بلا InvalidRequestError
        followup = (await db.execute(select(AIAgent).where(AIAgent.id == agent_id))).scalar_one()
        assert followup.id == agent_id

        usage_logs = (await db.execute(
            select(AgentUsageLog).where(AgentUsageLog.agent_id == agent_id)
        )).scalars().all()
        assert len(usage_logs) == 1
    finally:
        await db.execute(delete(AgentUsageLog).where(AgentUsageLog.agent_id == agent_id))
        await db.execute(delete(AIAgent).where(AIAgent.id == agent_id))
        await db.execute(delete(User).where(User.id == owner_id))
        await db.commit()
