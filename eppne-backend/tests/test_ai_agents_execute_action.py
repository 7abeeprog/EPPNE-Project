"""
regression test لجلسة `ai-agents-execute-action-fix`، الجزء ب
(Backlog #16، `AIAgentsService.execute_agent_action()`).
تقرير الجلسة الأصلية: .claude/reports/ai-agents-execute-action-fix-session-log.md

السبب الجذري (كان): `execute_agent_action(self, agent_id, action_type,
payload, executor_user_id, idempotency_key)` — **صفر معامل `tenant_id` في
التوقيع أصلًا** (نفس قوة #15: `self.tenant_id` من الـconstructor تُستخدم في
كل منطق فعلي — فلترة الوكيل، تسجيل `task_log`/`approval_request`، مفتاح
كاش الـidempotency). **19 موضع استدعاء** كانوا بيمرروا `tenant_id=` زيادة
→ `TypeError` فوري، **13 منهم كمان كانوا بيفتقدوا `idempotency_key=`
الإجباري** (بلا `default` في التوقيع).

**الإصلاح المُطبَّق: 17 من 19 موضع فقط — إغلاق جزئي بنطاق مُعدَّل عمدًا.**
إزالة `tenant_id=` من كل الـ17 + إضافة `idempotency_key=` بقيم مبنية بنمط
`PREFIX-T{tenant_id}-{unique_id}` للـ11 الناقصة (نفس درس جلسة `invitations`
#11a: تضمين `tenant_id` صراحة في النص يمنع تصادم `AgentApprovalQueue.idempotency_key`
العالمي — العمود `unique=True` **بلا** قيد مركّب مع `tenant_id` في الـschema).

**تحديث [2026-09-01، جلسة `backlog-16-begin-nested-commit-conflict`]:**
الموضعان (`realestate/service.py`، `invitations/service.py`) **اتصلحوا
فعليًا** بنقل نداء `execute_agent_action()` بره حدود `begin_nested()`
(تفاصيل كاملة + تحقيق حي: `.claude/reports/backlog-16-begin-nested-commit-session-log.md`).
الاختباران اللي كانوا `xfail(strict=True)` أسفل هذا الملف اتحوّلوا لاختباري
نجاح حقيقيين (`..._now_fixed`)، + اختبار إضافي لـinvitations يثبت إن مسار
الفشل الآمن (execute_agent_action تفشل) مايسيبش رسالة يتيمة.

هذا الملف يغطي:
- **منطق `execute_agent_action` نفسها مباشرة** (4 اختبارات، بأشكال
  `idempotency_key` تمثيلية من دومينات مختلفة فعليًا مُصلَحة — مش استدعاء
  الدومينات الكاملة، نفس منهجية التحقق الحي الأصلي §10): نجاح عادي، إعادة
  محاولة بنفس المفتاح (كاش حقيقي)، تينانتان مختلفان بنفس المعرّف المحلي
  (صفر تصادم بفضل `T{tenant_id}`)، ومفتاح خام بلا تمييز tenant عبر
  تينانتين (يثبت حيًا خطر `ai-agents-execute-action-approval-queue-global-unique-collision`
  الموثَّق مسبقًا).
- **اختباران للموضعين اللي كانوا مُستثنيين (realestate/invitations)** —
  استدعاء حي حقيقي لـ`buy_fractional_ownership`/`chat_with_ai` (الدالتين
  الحقيقيتين المحيطتين، مش استدعاء `execute_agent_action` مباشرة)، بيثبتوا
  المسار الشرعي الكامل ينجح فعليًا بعد إصلاح بنية المعاملة، + اختبار فشل
  آمن (`invitations`) يثبت صفر رسالة يتيمة حتى لو `execute_agent_action`
  فشلت.

**تجاوز متعمَّد لبج غير مرتبط (Backlog #7، `redis-client-wrapper-missing-methods`):**
`ai_engine.generate()` الحقيقية بتنادي `CostTracker.record_usage()` اللي
بتستخدم `redis_client.hincrbyfloat()` **غير الموجودة** على `RedisClientWrapper`
→ `AttributeError` يُسقِط `execute_agent_action` بالكامل بـException قبل
الوصول لأي منطق idempotency/tenant_id. **نفس منهجية التقرير الأصلي §10
بالحرف:** `ai_engine.generate` مُستبدَلة بـ`monkeypatch` بنسخة وهمية **في
هذا الملف فقط، صفر تعديل على كود الإنتاج** — لعزل التحقق على منطق
`execute_agent_action` نفسها (المصرَّح بلمسه)، بمعزل عن بج #7 (موثَّق
مسبقًا، خارج نطاق هذه الجلسة).

**بيانات throwaway:** `tenant_id=1` و`tenant_id=15` (تينانتان حقيقيان
موجودان فعلًا، نفس التينانتين المستخدَمين في التحقق الحي الأصلي). وكلاء AI
throwaway جدد لكل اختبار. تنظيف كامل في `finally`.
"""
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels
from app.core.database import AsyncSessionLocal

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.ai_agents.service import AIAgentsService
from app.domains.ai_agents.models import AIAgent, AgentRole, AgentStatus, AITaskLog, AgentApprovalQueue
from app.domains.ai_governance.models import AgentUsageLog
from app.services.ai import ai_engine

from app.domains.realestate.service import RealEstateService
from app.domains.realestate.repository import RealEstateRepository
from app.domains.realestate.models import RealEstateDevelopment, PropertyUnit, PropertyType, PropertyOwnership
from app.domains.finance.models import Wallet, Transaction
from app.domains.invoicing.service import InvoicingService

from app.domains.invitations.service import InvitationsService
from app.domains.invitations.repository import InvitationsRepository
from app.domains.invitations.models import (
    SovereignInvitation, InvitationConversation,
    InvitationType, InvitationTargetType, CampaignType, InvitationStatus,
)

TENANT_ID = 1
TENANT_ID_2 = 15  # "نبت" — تينانت ثانٍ حقيقي موجود بالفعل، نفس المستخدَم في التحقق الحي الأصلي
EXISTING_LAND_ASSET_ID = 1


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _fake_generate(*args, **kwargs):
    """تجاوز بج #7 (redis_client.hincrbyfloat مفقودة) — راجع الدوكسترنج أعلى الملف."""
    return {"text": "regtest-mock-ai-response", "cost_mrusdt": Decimal("0.0"), "model_used": "regtest-mock"}


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


async def _create_throwaway_agent(db, tenant_id: int, owner_id: int, requires_human_approval: bool = True) -> AIAgent:
    agent = AIAgent(
        tenant_id=tenant_id, owner_id=owner_id,
        name=f"REGTEST-AGENTS16-AGENT-{_suffix()}",
        role=AgentRole.SALES_NEGOTIATOR,
        status=AgentStatus.ACTIVE,
        system_prompt="regtest throwaway agent",
        requires_human_approval=requires_human_approval,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


async def _cleanup_agent(db, agent_id: int):
    await db.execute(delete(AgentApprovalQueue).where(AgentApprovalQueue.agent_id == agent_id))
    await db.execute(delete(AITaskLog).where(AITaskLog.agent_id == agent_id))
    await db.execute(delete(AIAgent).where(AIAgent.id == agent_id))
    await db.commit()


async def _cleanup_user(db, user_id: int):
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()


# ============================================================
# 1) نجاح عادي — شكل idempotency_key مطابق لنمط manufacturing/service.py:311
#    المُصلَح (AI-BATCH-T{tenant_id}-{batch.id})
# ============================================================

@pytest.mark.asyncio
async def test_execute_agent_action_normal_success_creates_task_log_and_approval(db, monkeypatch):
    monkeypatch.setattr(ai_engine, "generate", _fake_generate)
    owner = await _create_user(db, "p_regtest_agents16_owner")
    agent = await _create_throwaway_agent(db, TENANT_ID, owner.id, requires_human_approval=True)
    service = AIAgentsService(db, TENANT_ID)
    idempotency_key = f"AI-BATCH-T{TENANT_ID}-{_suffix()}"

    try:
        response = await service.execute_agent_action(
            agent_id=agent.id, action_type="REGTEST_MANUFACTURING_ANALYSIS",
            payload={"prompt": "regtest"}, executor_user_id=owner.id,
            idempotency_key=idempotency_key,
        )
        assert response["status"] == "PENDING_APPROVAL"

        task_logs = (await db.execute(
            select(AITaskLog).where(AITaskLog.idempotency_key == idempotency_key)
        )).scalars().all()
        assert len(task_logs) == 1
        assert task_logs[0].tenant_id == TENANT_ID

        approvals = (await db.execute(
            select(AgentApprovalQueue).where(AgentApprovalQueue.idempotency_key == f"{idempotency_key}-approval")
        )).scalars().all()
        assert len(approvals) == 1
        assert approvals[0].tenant_id == TENANT_ID
        assert approvals[0].action_type == "REGTEST_MANUFACTURING_ANALYSIS"
    finally:
        await _cleanup_agent(db, agent.id)
        await _cleanup_user(db, owner.id)


# ============================================================
# 2) إعادة محاولة بنفس idempotency_key — كاش حقيقي، صفر تكرار
# ============================================================

@pytest.mark.asyncio
async def test_execute_agent_action_retry_same_idempotency_key_is_cached(db, monkeypatch):
    monkeypatch.setattr(ai_engine, "generate", _fake_generate)
    owner = await _create_user(db, "p_regtest_agents16_retry")
    agent = await _create_throwaway_agent(db, TENANT_ID, owner.id, requires_human_approval=True)
    service = AIAgentsService(db, TENANT_ID)
    idempotency_key = f"AI-BIDEVAL-T{TENANT_ID}-{_suffix()}"

    try:
        first = await service.execute_agent_action(
            agent_id=agent.id, action_type="REGTEST_BID_EVALUATION",
            payload={"prompt": "regtest"}, executor_user_id=owner.id,
            idempotency_key=idempotency_key,
        )
        second = await service.execute_agent_action(
            agent_id=agent.id, action_type="REGTEST_BID_EVALUATION",
            payload={"prompt": "regtest"}, executor_user_id=owner.id,
            idempotency_key=idempotency_key,
        )
        # ملاحظة: second جايه من كاش Redis (JSON) — Decimal بترجع كنص بعد
        # round-trip، فمقارنة == الكاملة بتفشل رغم إن الكاش شغّال صح فعليًا.
        # الحقول المستقرة (status/approval_id) كافية لإثبات إنها نفس النتيجة.
        assert second["status"] == first["status"] == "PENDING_APPROVAL"
        assert second["approval_id"] == first["approval_id"], "إعادة المحاولة لازم ترجع نفس طلب الموافقة المخزَّن من الكاش"

        task_logs = (await db.execute(
            select(AITaskLog).where(AITaskLog.idempotency_key == idempotency_key)
        )).scalars().all()
        assert len(task_logs) == 1, "صفر تكرار — الاستدعاء الثاني اترجع من الكاش، مش تنفيذ جديد"

        approvals = (await db.execute(
            select(AgentApprovalQueue).where(AgentApprovalQueue.idempotency_key == f"{idempotency_key}-approval")
        )).scalars().all()
        assert len(approvals) == 1
    finally:
        await _cleanup_agent(db, agent.id)
        await _cleanup_user(db, owner.id)


# ============================================================
# 3) تينانتان مختلفان بنفس المعرّف المحلي — صفر تصادم بفضل T{tenant_id}
# ============================================================

@pytest.mark.asyncio
async def test_execute_agent_action_cross_tenant_same_local_id_no_collision(db, monkeypatch):
    monkeypatch.setattr(ai_engine, "generate", _fake_generate)
    owner = await _create_user(db, "p_regtest_agents16_xtenant")
    agent_t1 = await _create_throwaway_agent(db, TENANT_ID, owner.id, requires_human_approval=True)
    agent_t2 = await _create_throwaway_agent(db, TENANT_ID_2, owner.id, requires_human_approval=True)
    local_id = _suffix()

    try:
        service_t1 = AIAgentsService(db, TENANT_ID)
        service_t2 = AIAgentsService(db, TENANT_ID_2)

        resp1 = await service_t1.execute_agent_action(
            agent_id=agent_t1.id, action_type="REGTEST_SCENARIO_ANALYSIS",
            payload={"prompt": "regtest"}, executor_user_id=owner.id,
            idempotency_key=f"AI-SCENARIO-T{TENANT_ID}-{local_id}",
        )
        resp2 = await service_t2.execute_agent_action(
            agent_id=agent_t2.id, action_type="REGTEST_SCENARIO_ANALYSIS",
            payload={"prompt": "regtest"}, executor_user_id=owner.id,
            idempotency_key=f"AI-SCENARIO-T{TENANT_ID_2}-{local_id}",
        )
        assert resp1["status"] == "PENDING_APPROVAL"
        assert resp2["status"] == "PENDING_APPROVAL"

        task_logs = (await db.execute(
            select(AITaskLog).where(AITaskLog.idempotency_key.in_([
                f"AI-SCENARIO-T{TENANT_ID}-{local_id}", f"AI-SCENARIO-T{TENANT_ID_2}-{local_id}",
            ]))
        )).scalars().all()
        assert len(task_logs) == 2, "نفس المعرّف المحلي عبر تينانتين مختلفين — لازم يتسجلوا منفصلين بصفر تعارض"
        tenants_seen = {log.tenant_id for log in task_logs}
        assert tenants_seen == {TENANT_ID, TENANT_ID_2}
    finally:
        await _cleanup_agent(db, agent_t1.id)
        await _cleanup_agent(db, agent_t2.id)
        await _cleanup_user(db, owner.id)


# ============================================================
# 4) مفتاح خام بلا تمييز tenant عبر تينانتين — يثبت حيًا خطر Backlog
#    `ai-agents-execute-action-approval-queue-global-unique-collision`
#    (موثَّق مسبقًا، مش اكتشاف جديد — تأكيد حي إضافي هنا فقط)
# ============================================================

@pytest.mark.asyncio
async def test_execute_agent_action_raw_idempotency_key_without_tenant_prefix_collides_across_tenants(db, monkeypatch):
    """يثبت حيًا السبب اللي خلّى كل القيم الـ11 المُضافة في #16 تتضمن
    T{tenant_id} صراحة: AgentApprovalQueue.idempotency_key عمود unique=True
    عالميًا بلا قيد مركّب مع tenant_id في الـschema — مفتاح خام واحد بلا
    تمييز عبر تينانتين مختلفين يسبب IntegrityError حقيقي عند ثاني محاولة."""
    monkeypatch.setattr(ai_engine, "generate", _fake_generate)
    owner = await _create_user(db, "p_regtest_agents16_collision")
    agent_t1 = await _create_throwaway_agent(db, TENANT_ID, owner.id, requires_human_approval=True)
    agent_t2 = await _create_throwaway_agent(db, TENANT_ID_2, owner.id, requires_human_approval=True)
    agent_t1_id, agent_t2_id, owner_id = agent_t1.id, agent_t2.id, owner.id
    raw_key = f"REGTEST-RAW-COLLISION-{_suffix()}"  # صفر تمييز tenant عمدًا

    try:
        service_t1 = AIAgentsService(db, TENANT_ID)
        resp1 = await service_t1.execute_agent_action(
            agent_id=agent_t1_id, action_type="REGTEST_COLLISION", payload={"prompt": "regtest"},
            executor_user_id=owner_id, idempotency_key=raw_key,
        )
        assert resp1["status"] == "PENDING_APPROVAL"

        # جلسة مستقلة تمامًا للمحاولة الثانية المتوقَّع فشلها — الـIntegrityError
        # بيسمّم أي جلسة تحصل فيها، والاعتماد على db الأصلية لاحقًا في التنظيف
        # غير موثوق بعد ذلك (نفس الاحتياط المُتّبع في test_saas_active_subscription.py).
        async with AsyncSessionLocal() as db2:
            service_t2 = AIAgentsService(db2, TENANT_ID_2)
            with pytest.raises(IntegrityError):
                await service_t2.execute_agent_action(
                    agent_id=agent_t2_id, action_type="REGTEST_COLLISION", payload={"prompt": "regtest"},
                    executor_user_id=owner_id, idempotency_key=raw_key,
                )
    finally:
        await _cleanup_agent(db, agent_t1_id)
        await _cleanup_agent(db, agent_t2_id)
        await _cleanup_user(db, owner_id)


# ============================================================
# 5) ✅ realestate/service.py — begin_nested()/commit() conflict مُصلَح
#    [جلسة backlog-16-begin-nested-commit-conflict، 2026-09-01]
# ============================================================
#
# التاريخ: كانت execute_agent_action() تُنادى من جوّه async with
# self.db.begin_nested() في buy_fractional_ownership() — commit() الداخلي
# بتاعها كان بيكسر الـSAVEPOINT (InvalidRequestError: "Can't operate on
# closed transaction inside context manager"، مؤكَّد حيًا بسكربت
# scratchpad/repro_begin_nested_commit.py، راجع
# .claude/reports/backlog-16-begin-nested-commit-session-log.md §3).
# الإصلاح: نداء execute_agent_action() اتنقل لبعد self.db.commit() الرئيسي
# (نفس نمط/مكان invoicing.create_invoice() المجاور)، try/except، بلا تغيير
# على القيم الممرَّرة. هذا الاختبار بقى اختبار نجاح حقيقي (مش xfail).
#
# ملاحظة: buy_fractional_ownership() بتستخدم agent_id=2 مُثبَّت (hardcoded)
# في الكود — مش جزء من نطاق هذا الإصلاح (باج منفصل موثَّق). الاختبار بيزرع
# وكيل throwaway بمعرّف 2 صراحة عشان يوصل فعليًا لمسار execute_agent_action.

async def _noop_check_saas_limits_realestate(self, tenant_id, feature="real_estate"):
    return None, []


async def _noop_check_ai_governance_realestate(self, tenant_id, user_id, action, cost):
    """اكتشاف جانبي أثناء هذه الجلسة (خارج نطاقها): _check_ai_governance()
    بتنادي ai_governance.check_and_consume()، اللي عندها نفس بالضبط عيب
    begin_nested()+commit() داخلي (service.py:165-200) — ومن جوّه
    buy_fractional_ownership() بتتنادى من داخل begin_nested() الخارجي بتاعة
    realestate نفسها (سطر 303، قبل execute_agent_action المنقولة). النتيجة:
    الاستثناء بيتبلع بـtry/except الموجودة أصلاً في _check_ai_governance، لكن
    الجلسة بتفضل في حالة transaction مقفولة، فأي عملية DB تالية (زي
    _get_land_owner_for_unit) بتفشل بـInvalidRequestError مش معالَجة. هذا باج
    منفصل تمامًا، بنفس فئة #16 لكن call-site مختلف (ai_governance، مش
    ai_agents) — مُوثَّق فقط، غير مُصلَح هنا (خارج نطاق الموافقة الحالية)."""
    return True


async def _noop_create_invoice_for_isolation(self, *args, **kwargs):
    """اكتشاف جانبي تاني (خارج نطاق هذه الجلسة، معروف مسبقًا — راجع رسالة
    commit b4bf356: "an invoice-numbering collision surfaced while testing
    #37"): invoicing.create_invoice() بتفشل بـIntegrityError على
    invoice_number مكرر (مؤكَّد حيًا: نفس الرقم 'INV-1-000015' تكرر في عدة
    تشغيلات مختلفة لهذا الاختبار). production code بيمسكها بـtry/except
    فعلاً، لكن الـflush الفاشل بيسيب الجلسة بحالة PendingRollbackError، وأي
    وصول تالٍ لخاصية معلَّقة على كائن منتهي الصلاحية (زي
    ownership.acquisition_date بعد commit() execute_agent_action الجديدة)
    بيفشل بنفس الاستثناء القديم. تجاوز معزول هنا (نفس منهجية Redis #7) —
    صفر تعديل على كود الإنتاج، صفر علاقة بإصلاح begin_nested/commit."""
    return None


@pytest.mark.asyncio
async def test_realestate_buy_fractional_ownership_execute_agent_action_now_fixed(db, monkeypatch):
    monkeypatch.setattr(RealEstateService, "_check_saas_limits", _noop_check_saas_limits_realestate)
    monkeypatch.setattr(RealEstateService, "_check_ai_governance", _noop_check_ai_governance_realestate)
    monkeypatch.setattr(InvoicingService, "create_invoice", _noop_create_invoice_for_isolation)
    monkeypatch.setattr(ai_engine, "generate", _fake_generate)

    # buy_fractional_ownership() بتنادي execute_agent_action(agent_id=2, ...)
    # بمعرّف مُثبَّت — لازم وكيل حقيقي بنفس المعرّف عشان نوصل فعليًا للمسار
    # المُصلَح (مش NotFoundError). صفر وكيل بمعرّف 2 موجود حاليًا (تأكيد مباشر
    # قبل الزرع)، والـsequence متقدمة كتير عن 2 — صفر خطر تصادم مستقبلي.
    existing = (await db.execute(select(AIAgent).where(AIAgent.id == 2))).scalar_one_or_none()
    assert existing is None, "وكيل بمعرّف 2 موجود بالفعل — الاختبار مش آمن يكمل، افحص يدويًا"

    owner = await _create_user(db, "p_regtest_agents16_re_owner")
    owner_id = owner.id
    agent = AIAgent(
        id=2, tenant_id=TENANT_ID, owner_id=owner_id,
        name=f"REGTEST-AGENTS16-FIXED-AGENT-{_suffix()}",
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
        name=f"REGTEST-AGENTS16-DEV-{_suffix()}", development_type="RESIDENTIAL",
    )
    development_id = development.id
    unit = await re_repo.create_unit(
        tenant_id=TENANT_ID, development_id=development_id,
        unit_number=f"REGTEST-AGENTS16-UNIT-{_suffix()}", area_sqm=Decimal("100"),
        property_type=PropertyType.APARTMENT,
        is_available_for_sale=True, is_available_for_rent=False,
        sale_price_mrusdt=Decimal("1000"),
    )
    unit_id = unit.id
    buyer = await _create_user(db, "p_regtest_agents16_buyer")
    buyer_id = buyer.id
    # UserService.register() بينشئ محفظة تلقائيًا (برصيد {} فاضي) لكل مستخدم
    # جديد — لازم نحدّث نفس الصف الموجود (مش نضيف صف تاني، ده هيسبب
    # MultipleResultsFound جوّه finance.get_or_create_wallet_for_update
    # اللي بتفترض صف واحد بالظبط لكل user_id+tenant_id).
    await db.execute(
        text("UPDATE wallets SET balances = CAST(:b AS JSONB) WHERE user_id = :uid AND tenant_id = :tid"),
        {
            "b": json.dumps({"MR_POUND": 0, "MR_USDT": 1000, "MR7": 0, "NBT": 0, "MRX": 0}),
            "uid": buyer_id, "tid": TENANT_ID,
        },
    )
    await db.commit()

    # المالك (بائع) بتاع EXISTING_LAND_ASSET_ID مستخدم حقيقي مشترك بين
    # اختبارات تانية (مش throwaway) — finance.transfer() هيزود رصيده فعليًا.
    # نلقط رصيده الحالي هنا عشان نرجّعه بالظبط في finally، بدل ما نسيب أثر
    # دائم على fixture مشترك.
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
            percentage=Decimal("10"), idempotency_key=f"REGTEST-AGENTS16-BUY-{_suffix()}",
        )
        # 1) الشراء نفسه نجح فعليًا (المسار الأصلي، غير متأثر بإصلاح الـAI)
        assert ownership is not None
        assert ownership.owner_user_id == buyer_id

        # 2) تحقق مستقل مباشر: الملكية فعليًا محفوظة في الـDB
        db_ownership = (await db.execute(
            select(PropertyOwnership).where(PropertyOwnership.unit_id == unit_id)
        )).scalar_one()
        assert db_ownership.owner_user_id == buyer_id
        assert db_ownership.ownership_percentage == Decimal("10")

        # 3) الدليل الحاسم: execute_agent_action() نُفِّذت فعليًا بعد commit()
        #    الرئيسي بلا InvalidRequestError (لو الباج لسه موجود، الشراء كان
        #    هيفشل بالكامل قبل الوصول هنا) — task_log حقيقي اتسجل.
        task_logs = (await db.execute(
            select(AITaskLog).where(AITaskLog.agent_id == 2, AITaskLog.tenant_id == TENANT_ID)
        )).scalars().all()
        assert len(task_logs) == 1, "execute_agent_action() لازم تكون اتنفذت فعليًا بعد commit() الرئيسي"
        assert task_logs[0].idempotency_key.startswith("REALESTATE-FRAC-T1-")

        # 4) صفر صف يتيم: طلب الموافقة (لو وُجد) مرتبط بنفس الـidempotency_key
        approvals = (await db.execute(
            select(AgentApprovalQueue).where(AgentApprovalQueue.agent_id == 2, AgentApprovalQueue.tenant_id == TENANT_ID)
        )).scalars().all()
        assert len(approvals) == 1
        assert approvals[0].idempotency_key == f"{task_logs[0].idempotency_key}-approval"
    finally:
        # _check_ai_governance() (جوّه buy_fractional_ownership، غير متأثرة
        # بهذا الإصلاح) بتستخدم agent_id=2 كمان -> بتسجل صف في agent_usage_logs
        # (جدول ai_governance، منفصل عن ai_task_logs) لازم يتشال قبل حذف الوكيل
        # نفسه (FK).
        #
        # ⚠️ ملاحظة (باج معروف مسبقًا، خارج نطاق هذه الجلسة تمامًا — راجع
        # commit b4bf356 "invoice-numbering collision surfaced while testing
        # #37"): invoicing.create_invoice() (بعد execute_agent_action() المنقولة،
        # نفس مكانها الأصلي) بيفشل أحيانًا بـIntegrityError على invoice_number
        # مكرر. production code بيمسكها بـtry/except فعلاً (الشراء نفسه سليم،
        # الاختبار أعلاه أثبت كل الـassertions قبل هذه النقطة)، لكن الجلسة
        # (session) بتفضل بحالة "pending rollback" بعد الفلاش الفاشل — لازم
        # rollback() صريح قبل أي عملية تالية على نفس الجلسة (نفس نمط
        # conftest.py's session teardown).
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
        # production code بتاعة buy_fractional_ownership بتسجل audit_log()+
        # _send_notification() لـbuyer_id — لازم يتشالوا قبل _cleanup_user (FK)
        await db.execute(text("DELETE FROM audit_logs WHERE user_id = :uid"), {"uid": buyer_id})
        await db.execute(text("DELETE FROM notifications WHERE user_id = :uid"), {"uid": buyer_id})
        if seller_balances_snapshot is not None:
            await db.execute(
                text("UPDATE wallets SET balances = CAST(:b AS JSONB) WHERE user_id = :uid AND tenant_id = :tid"),
                {"b": json.dumps(seller_balances_snapshot, default=str), "uid": seller_id, "tid": TENANT_ID},
            )
        await db.commit()
        await _cleanup_user(db, buyer_id)
        await _cleanup_user(db, owner_id)


# ============================================================
# 6) ✅ invitations/service.py — begin_nested()/commit() conflict مُصلَح
#    [جلسة backlog-16-begin-nested-commit-conflict، 2026-09-01]
# ============================================================
#
# التاريخ: كانت execute_agent_action() تُنادى من جوّه async with
# self.db.begin_nested() في chat_with_ai() — بعد repo.create_conversation()
# لرسالة المستخدم (كتابة حقيقية سابقة لنداء execute_agent_action داخل نفس
# البلوك). التحقيق الحي (سكربت repro_begin_nested_commit.py) أثبت: أي كتابة
# قبل execute_agent_action() جوّه begin_nested() بتتحفظ دائمًا في الـDB رغم
# ما الـcommit() الداخلي بتاعها بيرمي InvalidRequestError ويكسر باقي البلوك
# — يعني رسالة المستخدم كانت هتتحفظ يتيمة بلا رد لو الـkwargs اتصلحت هنا
# بمعزل عن حل بنية المعاملة. الإصلاح: بناء الـprompt + نداء
# execute_agent_action() اتنقلوا لأعلى، قبل begin_nested() تمامًا (نتيجتها
# reply_text مُستخدَمة فعليًا في بناء الرد، فمينفعش تتأجل زي realestate) —
# وتصحيح tenant_id=/idempotency_key= في نفس الخطوة. هذا الاختبار بقى اختبار
# نجاح حقيقي (مش xfail)، ومعاه اختبار إضافي للفشل الآمن.

async def _noop_check_saas_limits_invitations(self, tenant_id, feature="crm"):
    return None, []


async def _create_sent_invitation(db, title: str, assigned_ai_agent_id=None) -> SovereignInvitation:
    repo = InvitationsRepository(db)
    inv = await repo.create_invitation(
        tenant_id=TENANT_ID,
        invitation_type=InvitationType.GENERAL,
        target_type=InvitationTargetType.PERSON,
        campaign_type=CampaignType.SERVICE,
        campaign_id=999999,
        title=title,
        status=InvitationStatus.SENT,
        assigned_ai_agent_id=assigned_ai_agent_id,
    )
    await db.commit()
    return inv


@pytest.mark.asyncio
async def test_invitations_chat_with_ai_execute_agent_action_now_fixed(db, monkeypatch):
    monkeypatch.setattr(InvitationsService, "_check_saas_limits", _noop_check_saas_limits_invitations)
    monkeypatch.setattr(ai_engine, "generate", _fake_generate)

    owner = await _create_user(db, "p_regtest_agents16_inv_owner")
    agent = await _create_throwaway_agent(db, TENANT_ID, owner.id, requires_human_approval=True)
    invitation = await _create_sent_invitation(
        db, f"REGTEST-AGENTS16-INV-{_suffix()}", assigned_ai_agent_id=agent.id,
    )
    service = InvitationsService(db)

    try:
        result = await service.chat_with_ai(
            invitation_id=invitation.id, tenant_id=TENANT_ID,
            visitor_session_id=f"regtest-session-{_suffix()}",
            user_message="regtest message",
            user_id=owner.id,  # مستخدم حقيقي — يتفادى FK ناقص (agent_usage_logs.user_id) غير مرتبط بهذا الإصلاح لو user_id=None
        )
        # 1) نجاح المسار الكامل — رد فعلي، وconversation_id حقيقي
        #    ⚠️ اكتشاف جانبي (خارج نطاق هذه الجلسة، موثَّق فقط): reply_text
        #    مصدره ai_response.get("result", {}).get("reply", <fallback>) —
        #    لكن ai_engine.generate() الحقيقية بترجع المفتاح "text" مش "reply"
        #    إطلاقًا (services/ai/engine.py:157). يعني chat_with_ai بترجع
        #    نص الـfallback الثابت دايمًا، مش رد الـAI الفعلي — باج مستقل
        #    قبل هذا الإصلاح وبعده، مش ناتج عن نقل execute_agent_action.
        #    الاختبار بيتحقق من السلوك الحالي الحقيقي (مش المتوقَّع منطقيًا).
        assert result is not None
        fallback_reply = "شكراً لتواصلك. كيف يمكنني مساعدتك؟"
        assert result["reply"] == fallback_reply
        ai_conversation_id = result["conversation_id"]

        # 2) تحقق مستقل: رسالتا المحادثة (المستخدم + الـAI) اتسجلوا سوا،
        #    مش بس رد الـAI (الدليل إن begin_nested() اتقفل صح، بلا تناقض)
        conversations = (await db.execute(
            select(InvitationConversation).where(InvitationConversation.invitation_id == invitation.id)
        )).scalars().all()
        assert len(conversations) == 2, "لازم رسالة المستخدم + رد الـAI سوا — صفر رسالة يتيمة"
        by_role = {c.is_from_ai: c for c in conversations}
        assert by_role[False].message == "regtest message"
        assert by_role[True].message == fallback_reply
        assert by_role[True].id == ai_conversation_id

        # 3) الدليل الحاسم: execute_agent_action() نُفِّذت فعليًا (task_log)
        task_logs = (await db.execute(
            select(AITaskLog).where(AITaskLog.agent_id == agent.id, AITaskLog.tenant_id == TENANT_ID)
        )).scalars().all()
        assert len(task_logs) == 1
        assert task_logs[0].idempotency_key.startswith(f"AI-CRMCHAT-T{TENANT_ID}-{invitation.id}-")
    finally:
        # governance.check_and_consume() (قبل begin_nested()، غير متأثرة بهذا
        # الإصلاح) بتسجل صف في agent_usage_logs — لازم يتشال قبل حذف الوكيل (FK).
        await db.execute(delete(AgentUsageLog).where(AgentUsageLog.agent_id == agent.id))
        await db.execute(delete(AgentApprovalQueue).where(AgentApprovalQueue.agent_id == agent.id))
        await db.execute(delete(InvitationConversation).where(InvitationConversation.invitation_id == invitation.id))
        await db.execute(delete(SovereignInvitation).where(SovereignInvitation.id == invitation.id))
        await db.commit()
        await _cleanup_agent(db, agent.id)
        await _cleanup_user(db, owner.id)


@pytest.mark.asyncio
async def test_invitations_chat_with_ai_execute_agent_action_failure_leaves_no_orphan_message(db, monkeypatch):
    """لو execute_agent_action() فشلت (أي سبب)، الفشل لازم يحصل قبل أي
    كتابة على الإطلاق — صفر رسالة مستخدم يتيمة بلا رد، حتى في مسار الفشل.
    هذا يثبت إن رفع النداء لبره begin_nested() قفل الثغرة اللي كانت هتفضل
    مفتوحة لو الكتابة الأولى (رسالة المستخدم) فضلت جوّه البلوك القديم."""
    monkeypatch.setattr(InvitationsService, "_check_saas_limits", _noop_check_saas_limits_invitations)

    async def _broken_generate(*args, **kwargs):
        raise RuntimeError("regtest: simulated AI engine failure")

    monkeypatch.setattr(ai_engine, "generate", _broken_generate)

    owner = await _create_user(db, "p_regtest_agents16_inv_fail_owner")
    agent = await _create_throwaway_agent(db, TENANT_ID, owner.id, requires_human_approval=True)
    invitation = await _create_sent_invitation(
        db, f"REGTEST-AGENTS16-INV-FAIL-{_suffix()}", assigned_ai_agent_id=agent.id,
    )
    service = InvitationsService(db)

    try:
        with pytest.raises(Exception):
            await service.chat_with_ai(
                invitation_id=invitation.id, tenant_id=TENANT_ID,
                visitor_session_id=f"regtest-session-{_suffix()}",
                user_message="regtest message that should never be saved",
                user_id=owner.id,
            )

        conversations = (await db.execute(
            select(InvitationConversation).where(InvitationConversation.invitation_id == invitation.id)
        )).scalars().all()
        assert len(conversations) == 0, "صفر كتابة يُفترض تحصل قبل ما execute_agent_action() تنجح"
    finally:
        await db.execute(delete(AgentUsageLog).where(AgentUsageLog.agent_id == agent.id))
        await db.execute(delete(AgentApprovalQueue).where(AgentApprovalQueue.agent_id == agent.id))
        await db.execute(delete(AITaskLog).where(AITaskLog.agent_id == agent.id))
        await db.execute(delete(InvitationConversation).where(InvitationConversation.invitation_id == invitation.id))
        await db.execute(delete(SovereignInvitation).where(SovereignInvitation.id == invitation.id))
        await db.commit()
        await _cleanup_agent(db, agent.id)
        await _cleanup_user(db, owner.id)
