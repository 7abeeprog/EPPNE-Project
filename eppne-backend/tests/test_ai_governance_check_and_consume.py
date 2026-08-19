"""
regression test لجلسة `ai-governance-agents-signature-fix`، الجزء أ
(Backlog #15، `AIGovernanceService.check_and_consume()`).
تقرير الجلسة الأصلية: .claude/reports/ai-governance-agents-fix-session-log.md

السبب الجذري (كان): `check_and_consume(self, agent_id, user_id, action_type,
tokens, cost, idempotency_key=None, ...)` — **صفر معامل `tenant_id` في
التوقيع أصلًا** (الـmethod تستخدم `self.tenant_id` من الـconstructor في كل
منطق فعلي: فلترة الحصة، تسجيل الاستهلاك). **كل الـ13 موضع استدعاء عبر 13
دومين** كانوا بيمرروا `tenant_id=` زيادة → `TypeError` فوري، **7 منهم كمان
كانوا بيفتقدوا `action_type=` الإجباري** (بج ثانٍ متزامن).

الإصلاح المُطبَّق: إزالة `tenant_id=` من كل الـ13 موضع (عكس اتجاه إصلاح
`audit_log`/#14 عمدًا — هنا الـmethod تملك السياق بالفعل عبر الـconstructor)
+ إضافة `action_type=` بقيم معبِّرة عن السياق الفعلي للسبعة الناقصة (منهم
اتنين بحل أدق: تمرير معامل `action: str` موجود أصلًا في helper محيط بدل نص
ثابت جديد). صفر لمس على جسم `check_and_consume` نفسها أو `AIGovernanceRepository`.

هذا الملف يغطي **منطق `check_and_consume` نفسها مباشرة** (مش استدعاء أي من
الـ13 دومين الكاملة — نفس منهجية التحقق الحي الأصلي، قسم 15 من التقرير):
1. **نجاح عادي** — استهلاك حصة `TOKEN_COUNT` ضمن الحد، `usage_log` يُسجَّل بدقة.
2. **تراكم صحيح** — استدعاءان متتاليان بنفس الوكيل يتراكمان بشكل صحيح حتى
   حد الحصة بالضبط (مطابق لسيناريو 2 من التقرير: 500+500=1000).
3. **رفض فعلي عند تجاوز الحصة** (الحالة الحرجة) — `check_and_consume`
   بترجع `False` فعليًا لو الاستهلاك المطلوب هيتجاوز الحد، **بلا** أي
   استهلاك جزئي أو `usage_log` للمحاولة المرفوضة (مطابق تمامًا لسيناريو 3).

**اكتشاف إضافي [2026-08-19] أثناء كتابة هذا الملف — امتداد طبيعي لنفس
النطاق (`check_and_consume` نفسها)، مش خارجه:** جسم `check_and_consume`
(سطر 152) بينادي `self.repo.get_usage_log_by_idempotency(idempotency_key)`
بمعامل واحد بس، لكن التوقيع الحقيقي لـ`AIGovernanceRepository.get_usage_log_by_idempotency`
(`repository.py:66`) يطلب `(idempotency_key: str, tenant_id: int)` —
**`tenant_id` إجباري بلا default**. يعني **أي استدعاء `check_and_consume()`
بـ`idempotency_key` حقيقي (غير `None`/فارغ) بيكراش فورًا بـ`TypeError`
جديد كليًا**، مختلف تمامًا عن بج `tenant_id`/`action_type` الموثَّق في
#15 (ده باج *جوّه* جسم الدالة نفسها، مش في توقيعها الخارجي). **الموضع
الوحيد من الـ13 اللي بيمرر `idempotency_key` فعليًا هو
`service_marketplace/service.py:159`** — يعني هذا المسار مكسور بالكامل
حاليًا. مُثبَت هنا باختبار `xfail(strict=True)` رابع (اختبار 4)، **صفر لمس
على `ai_governance/service.py`/`repository.py`**، ومُوثَّق كبند Backlog
منفصل جديد في `PROGRESS_LOG.md`.

**بيانات throwaway:** `tenant_id=1`، وكيل AI ووحدة حصة (`AgentQuota`)
throwaway جديدين لكل اختبار (`uuid4` suffix في الاسم، صفر تعارض مع وكلاء
حقيقيين). تنظيف كامل في `finally`.
"""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import delete, select

from app.main import fastapi_app  # noqa: F401 — يضمن تسجيل كل الـmodels

from app.domains.identity.service import UserService
from app.domains.identity.schemas import UserCreate
from app.domains.identity.models import User

from app.domains.ai_agents.models import AIAgent, AgentRole, AgentStatus
from app.domains.ai_governance.service import AIGovernanceService
from app.domains.ai_governance.models import AgentQuota, AgentUsageLog, LimitType, UsagePeriod

TENANT_ID = 1


def _suffix() -> str:
    return uuid.uuid4().hex[:10]


async def _create_user(db, prefix: str) -> User:
    suffix = _suffix()
    email = f"{prefix}_{suffix}@eppne.com"
    return await UserService(db, TENANT_ID).register(
        UserCreate(username=email.split("@")[0], email=email, password="TempPass123!"),
        idempotency_key=f"REGTEST-{prefix}-{suffix}",
    )


async def _create_throwaway_agent(db, owner_id: int) -> AIAgent:
    agent = AIAgent(
        tenant_id=TENANT_ID, owner_id=owner_id,
        name=f"REGTEST-GOV15-AGENT-{_suffix()}",
        role=AgentRole.SALES_NEGOTIATOR,
        status=AgentStatus.ACTIVE,
        system_prompt="regtest throwaway agent",
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


async def _create_quota(db, agent_id: int, limit_type: LimitType, limit_value: Decimal) -> AgentQuota:
    from datetime import datetime, timedelta
    quota = AgentQuota(
        tenant_id=TENANT_ID, agent_id=agent_id,
        limit_type=limit_type, period=UsagePeriod.DAILY,
        limit_value=limit_value, current_usage=Decimal("0"),
        reset_at=datetime.utcnow() + timedelta(days=1),
    )
    db.add(quota)
    await db.commit()
    await db.refresh(quota)
    return quota


async def _cleanup(db, agent_id: int, owner_id: int):
    await db.execute(delete(AgentUsageLog).where(AgentUsageLog.agent_id == agent_id))
    await db.execute(delete(AgentQuota).where(AgentQuota.agent_id == agent_id))
    await db.execute(delete(AIAgent).where(AIAgent.id == agent_id))
    await db.execute(delete(User).where(User.id == owner_id))
    await db.commit()


# ============================================================
# 1) نجاح عادي — استهلاك ضمن الحد
# ============================================================

@pytest.mark.asyncio
async def test_check_and_consume_normal_success_records_usage(db):
    """نفس شكل استدعاء insurance/service.py:338 المُصلَح (agent_id, user_id,
    action_type, tokens, cost — بلا tenant_id) — لازم يعدي بنجاح ويسجّل
    الاستهلاك بدقة."""
    owner = await _create_user(db, "p_regtest_gov15_owner")
    agent = await _create_throwaway_agent(db, owner.id)
    quota = await _create_quota(db, agent.id, LimitType.TOKEN_COUNT, Decimal("1000"))
    service = AIGovernanceService(db, TENANT_ID)

    try:
        result = await service.check_and_consume(
            agent_id=agent.id, user_id=owner.id, action_type="REGTEST_CLAIM_ANALYSIS",
            tokens=300, cost=Decimal("0.03"),
        )
        assert result is True

        refreshed_quota = (await db.execute(
            select(AgentQuota).where(AgentQuota.id == quota.id)
        )).scalar_one_or_none()
        assert refreshed_quota is not None
        assert refreshed_quota.current_usage == Decimal("300.00")

        usage_logs = (await db.execute(
            select(AgentUsageLog).where(AgentUsageLog.agent_id == agent.id)
        )).scalars().all()
        assert len(usage_logs) == 1
        assert usage_logs[0].action_type == "REGTEST_CLAIM_ANALYSIS"
        assert usage_logs[0].total_tokens == 300
    finally:
        await _cleanup(db, agent.id, owner.id)


# ============================================================
# 2) تراكم صحيح عبر استدعاءين متتاليين — لحد الحصة بالضبط
# ============================================================

@pytest.mark.asyncio
async def test_check_and_consume_accumulates_usage_across_calls(db):
    """مطابق لسيناريو 2 من التقرير الأصلي: نفس الوكيل، استدعاءان متتاليان
    بقيمتي action_type مختلفتين (500+500=1000، حد الحصة بالضبط) — لازم
    الاتنين ينجحوا والتراكم يبقى صحيح."""
    owner = await _create_user(db, "p_regtest_gov15_owner2")
    agent = await _create_throwaway_agent(db, owner.id)
    quota = await _create_quota(db, agent.id, LimitType.TOKEN_COUNT, Decimal("1000"))
    service = AIGovernanceService(db, TENANT_ID)

    try:
        result1 = await service.check_and_consume(
            agent_id=agent.id, user_id=owner.id, action_type="REGTEST_AI_JUDGE_ANALYSIS",
            tokens=500, cost=Decimal("0.05"),
        )
        result2 = await service.check_and_consume(
            agent_id=agent.id, user_id=owner.id, action_type="REGTEST_SCENARIO_ANALYSIS",
            tokens=500, cost=Decimal("0.05"),
        )
        assert result1 is True and result2 is True

        refreshed_quota = (await db.execute(
            select(AgentQuota).where(AgentQuota.id == quota.id)
        )).scalar_one_or_none()
        assert refreshed_quota is not None
        assert refreshed_quota.current_usage == Decimal("1000.00"), "التراكم لازم يوصل بالضبط لحد الحصة"

        usage_logs = (await db.execute(
            select(AgentUsageLog).where(AgentUsageLog.agent_id == agent.id).order_by(AgentUsageLog.id)
        )).scalars().all()
        assert len(usage_logs) == 2
        assert usage_logs[0].action_type == "REGTEST_AI_JUDGE_ANALYSIS"
        assert usage_logs[1].action_type == "REGTEST_SCENARIO_ANALYSIS"
    finally:
        await _cleanup(db, agent.id, owner.id)


# ============================================================
# 3) رفض فعلي عند تجاوز الحصة — الحالة الحرجة
# ============================================================

@pytest.mark.asyncio
async def test_check_and_consume_rejects_when_quota_exceeded(db):
    """مطابق لسيناريو 3 من التقرير الأصلي: وكيل بحصة منخفضة (100)، طلب
    استهلاك أعلى (150) — لازم يرجع False فعليًا، بلا أي استهلاك جزئي
    وبلا usage_log للمحاولة المرفوضة."""
    owner = await _create_user(db, "p_regtest_gov15_owner3")
    agent = await _create_throwaway_agent(db, owner.id)
    quota = await _create_quota(db, agent.id, LimitType.TOKEN_COUNT, Decimal("100"))
    service = AIGovernanceService(db, TENANT_ID)

    try:
        result = await service.check_and_consume(
            agent_id=agent.id, user_id=owner.id, action_type="REGTEST_OVER_QUOTA",
            tokens=150, cost=Decimal("0.15"),
        )
        assert result is False, "لازم يرفض فعليًا لما الاستهلاك المطلوب يتجاوز الحد"

        refreshed_quota = (await db.execute(
            select(AgentQuota).where(AgentQuota.id == quota.id)
        )).scalar_one_or_none()
        assert refreshed_quota is not None
        assert refreshed_quota.current_usage == Decimal("0.00"), "صفر استهلاك جزئي — الرفض لازم يكون قبل أي تحديث"

        usage_logs = (await db.execute(
            select(AgentUsageLog).where(AgentUsageLog.agent_id == agent.id)
        )).scalars().all()
        assert len(usage_logs) == 0, "صفر usage_log للمحاولة المرفوضة"
    finally:
        await _cleanup(db, agent.id, owner.id)


# ============================================================
# 4) اكتشاف جديد [2026-08-19] — get_usage_log_by_idempotency() بمعامل
#    ناقص، خارج نطاق توقيع #15 نفسه لكن جوّه جسم check_and_consume
# ============================================================

@pytest.mark.xfail(
    reason=(
        "اكتشاف جديد [2026-08-19]: check_and_consume() (ai_governance/service.py:152) "
        "بتنادي self.repo.get_usage_log_by_idempotency(idempotency_key) بمعامل واحد بس، "
        "لكن AIGovernanceRepository.get_usage_log_by_idempotency() (repository.py:66) "
        "توقيعها الحقيقي (idempotency_key: str, tenant_id: int) — tenant_id إجباري "
        "بلا default. أي استدعاء check_and_consume() بـidempotency_key حقيقي (غير None) "
        "يكراش فورًا بـTypeError. الموضع الوحيد من الـ13 المُصلَحة في #15 اللي بيمرر "
        "idempotency_key فعليًا هو service_marketplace/service.py:159 — هذا المسار "
        "مكسور بالكامل حاليًا. صفر لمس على ai_governance/service.py أو repository.py "
        "في هذه الجلسة — خارج نطاق #15 نفسه (توقيع check_and_consume سليم، الباج جوّه "
        "جسمها في نداء داخلي لدالة تانية)."
    ),
    strict=True,
)
@pytest.mark.asyncio
async def test_check_and_consume_with_idempotency_key_hits_wrong_arity_bug(db):
    owner = await _create_user(db, "p_regtest_gov15_owner4")
    agent = await _create_throwaway_agent(db, owner.id)
    await _create_quota(db, agent.id, LimitType.TOKEN_COUNT, Decimal("1000"))
    service = AIGovernanceService(db, TENANT_ID)

    try:
        result = await service.check_and_consume(
            agent_id=agent.id, user_id=owner.id, action_type="REGTEST_SERVICE_PURCHASE",
            tokens=10, cost=Decimal("0.01"), idempotency_key=f"REGTEST-GOV15-IDEMP-{_suffix()}",
        )
        assert result is True  # لو الباج اتصلح مستقبلاً، هيوصل هنا فعلاً (XPASS → فشل مقصود بسبب strict=True)
    finally:
        await _cleanup(db, agent.id, owner.id)
