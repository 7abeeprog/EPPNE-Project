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

**🔴 موضعان مُستثنيان عمدًا من الإصلاح، بقرار صريح موثَّق (§7 من التقرير):**
- `realestate/service.py:232` (داخل `buy_fractional_ownership`)
- `invitations/service.py:415` (داخل `chat_with_ai`)

السبب: `execute_agent_action()` نفسها بتنفّذ `await self.db.commit()` داخل
جسمها (مساري النجاح والفشل معًا، سطر 223/226). الموضعان دول بينادوها من
**جوّه `async with self.db.begin_nested()`** خارجي، بلا `try/except`. لو
اتصلح الـkwargs فيهم بمعزل عن حل بنية المعاملة، هيوصلوا لأول مرة فعليًا
لتنفيذ `commit()` حقيقي وهما لسه جوّه savepoint — **احتمال تلف حالة
transaction بالكامل**، نفس فئة خطورة #11a/#11b الجذرية (`realestate:232`
تحديدًا داخل عملية شراء ملكية عقارية بأموال حقيقية). **هذا مُوثَّق كبند
Backlog منفصل مفتوح: `ai-agents-execute-action-commit-inside-begin-nested`
— لازم يُصلَح الاتنين سوا (بنية المعاملة أولًا) في جلسة مستقبلية منفصلة.**

هذا الملف يغطي:
- **منطق `execute_agent_action` نفسها مباشرة** (4 اختبارات، بأشكال
  `idempotency_key` تمثيلية من دومينات مختلفة فعليًا مُصلَحة — مش استدعاء
  الدومينات الكاملة، نفس منهجية التحقق الحي الأصلي §10): نجاح عادي، إعادة
  محاولة بنفس المفتاح (كاش حقيقي)، تينانتان مختلفان بنفس المعرّف المحلي
  (صفر تصادم بفضل `T{tenant_id}`)، ومفتاح خام بلا تمييز tenant عبر
  تينانتين (يثبت حيًا خطر `ai-agents-execute-action-approval-queue-global-unique-collision`
  الموثَّق مسبقًا).
- **اختباران `xfail(strict=True)` موثَّقان للموضعين المُستثنيين** —
  استدعاء حي حقيقي لـ`buy_fractional_ownership`/`chat_with_ai` (الدالتين
  الحقيقيتين المحيطتين، مش استدعاء `execute_agent_action` مباشرة)، يثبتان
  إن الاستثناء **لسه موجود بالحرف** ومُستبعَد عمدًا — **ممنوع تجاهلهم أو
  كتابة اختبار نجاح لهم**، طبقًا لقرار الجلسة الأصلي الصريح.

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
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels
from app.core.database import AsyncSessionLocal

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.ai_agents.service import AIAgentsService
from app.domains.ai_agents.models import AIAgent, AgentRole, AgentStatus, AITaskLog, AgentApprovalQueue
from app.services.ai import ai_engine

from app.domains.realestate.service import RealEstateService
from app.domains.realestate.repository import RealEstateRepository
from app.domains.realestate.models import RealEstateDevelopment, PropertyUnit, PropertyType, PropertyOwnership

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
# 5) 🔴 realestate/service.py:232 — مُستثنى عمدًا، xfail موثَّق (ممنوع نجاح)
# ============================================================

async def _noop_check_saas_limits_realestate(self, tenant_id, feature="real_estate"):
    return None, []


@pytest.mark.xfail(
    reason=(
        "مُستثنى عمدًا من إصلاح #16 [قرار صريح 2026-08-18] — Backlog "
        "ai-agents-execute-action-commit-inside-begin-nested. execute_agent_action() "
        "تنفّذ await self.db.commit() داخل جسمها، وbuy_fractional_ownership() بتناديها "
        "من جوّه async with self.db.begin_nested() خارجي (realestate/service.py:214-232)، "
        "بلا try/except. تصحيح tenant_id=/idempotency_key= هنا بمعزل عن حل بنية المعاملة "
        "كان سيجعلها تصل لأول مرة لـcommit() حقيقي وهي لسه جوّه savepoint — احتمال تلف "
        "transaction حقيقي (عملية شراء ملكية عقارية بأموال حقيقية). لسه بترمي TypeError "
        "معروف (نفس فئة #16 الأصلية: tenant_id= زيادة، idempotency_key مفقودة) — هذا "
        "xfail بيثبت إنها لسه مُستثناة فعليًا، مش بيختبر نجاحها. لو حد أصلح بنية المعاملة "
        "وصحّح الـkwargs سوا لاحقًا، هيبقى XPASS ويفشل تلقائيًا (strict=True) كتذكير."
    ),
    strict=True,
)
@pytest.mark.asyncio
async def test_realestate_buy_fractional_ownership_execute_agent_action_still_excluded(db, monkeypatch):
    monkeypatch.setattr(RealEstateService, "_check_saas_limits", _noop_check_saas_limits_realestate)
    re_repo = RealEstateRepository(db)
    development = await re_repo.create_development(
        tenant_id=TENANT_ID, land_asset_id=EXISTING_LAND_ASSET_ID,
        name=f"REGTEST-AGENTS16-DEV-{_suffix()}", development_type="RESIDENTIAL",
    )
    unit = await re_repo.create_unit(
        tenant_id=TENANT_ID, development_id=development.id,
        unit_number=f"REGTEST-AGENTS16-UNIT-{_suffix()}", area_sqm=Decimal("100"),
        property_type=PropertyType.APARTMENT,
        is_available_for_sale=True, is_available_for_rent=False,
        sale_price_mrusdt=Decimal("1000"),
    )
    buyer = await _create_user(db, "p_regtest_agents16_buyer")
    service = RealEstateService(db)

    try:
        ownership = await service.buy_fractional_ownership(
            buyer_id=buyer.id, tenant_id=TENANT_ID, unit_id=unit.id,
            percentage=Decimal("10"), idempotency_key=f"REGTEST-AGENTS16-BUY-{_suffix()}",
        )
        assert ownership is not None  # لو وصلنا هنا (XPASS)، الباج اتصلح فعليًا
    finally:
        await db.execute(delete(PropertyOwnership).where(PropertyOwnership.unit_id == unit.id))
        await db.execute(delete(PropertyUnit).where(PropertyUnit.id == unit.id))
        await db.execute(delete(RealEstateDevelopment).where(RealEstateDevelopment.id == development.id))
        await db.commit()
        await _cleanup_user(db, buyer.id)


# ============================================================
# 6) 🔴 invitations/service.py:415 — مُستثنى عمدًا، xfail موثَّق (ممنوع نجاح)
# ============================================================

async def _noop_check_saas_limits_invitations(self, tenant_id, feature="crm"):
    return None, []


async def _create_sent_invitation(db, title: str) -> SovereignInvitation:
    repo = InvitationsRepository(db)
    inv = await repo.create_invitation(
        tenant_id=TENANT_ID,
        invitation_type=InvitationType.GENERAL,
        target_type=InvitationTargetType.PERSON,
        campaign_type=CampaignType.SERVICE,
        campaign_id=999999,
        title=title,
        status=InvitationStatus.SENT,
    )
    await db.commit()
    return inv


@pytest.mark.xfail(
    reason=(
        "مُستثنى عمدًا من إصلاح #16 [قرار صريح 2026-08-18] — Backlog "
        "ai-agents-execute-action-commit-inside-begin-nested. نفس سبب realestate:232 "
        "بالحرف: chat_with_ai() بتنادي execute_agent_action() من جوّه async with "
        "self.db.begin_nested() خارجي (invitations/service.py:394-420)، بلا try/except. "
        "لسه بترمي TypeError معروف (tenant_id= زيادة، idempotency_key مفقودة). هذا xfail "
        "بيثبت إنها لسه مُستثناة فعليًا، مش بيختبر نجاحها."
    ),
    strict=True,
)
@pytest.mark.asyncio
async def test_invitations_chat_with_ai_execute_agent_action_still_excluded(db, monkeypatch):
    monkeypatch.setattr(InvitationsService, "_check_saas_limits", _noop_check_saas_limits_invitations)
    invitation = await _create_sent_invitation(db, f"REGTEST-AGENTS16-INV-{_suffix()}")
    service = InvitationsService(db)

    try:
        result = await service.chat_with_ai(
            invitation_id=invitation.id, tenant_id=TENANT_ID,
            visitor_session_id=f"regtest-session-{_suffix()}",
            user_message="regtest message",
        )
        assert result is not None  # لو وصلنا هنا (XPASS)، الباج اتصلح فعليًا
    finally:
        await db.execute(delete(InvitationConversation).where(InvitationConversation.invitation_id == invitation.id))
        await db.execute(delete(SovereignInvitation).where(SovereignInvitation.id == invitation.id))
        await db.commit()
