"""
Kill Switch العالمي للذكاء الاصطناعي (Batch 0-C، خيار B).
راجع .claude/reports/admin-batch0c-kill-switch-session-log.md (الجزء الثاني).

اتفاقية المشروع: DB/Redis حقيقيان بلا mock. الاستثناءات المقصودة والمعلنة:
- تعطيل نداءات الـ LLM/الـ repo/الحوكمة التي يثبت اختبارنا أنها *لم* تُبلَغ أو لعزل الكتابة.
- كل اختبار يستبدل features.SYSTEM_SUSPENDED_KEY بمفتاح اختباري فريد (لا يلمس المفتاح الحقيقي).
لا سيرفر: HTTP عبر httpx.ASGITransport على fastapi_app (بلا lifespan).
"""
import asyncio
import base64
import json
import logging
import uuid
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import text

from app.main import fastapi_app
from app.core import config as config_module
from app.core import features
from app.core.database import engine
from app.core.errors import AISystemSuspendedError, PermissionDeniedError
from app.core.redis_client import redis_client
from app.core.security import (
    get_current_platform_superuser,
    get_current_superuser,
    get_current_user,
)
from route_utils import direct_dependency_calls, find_route

TOGGLE = "/api/admin/system/toggle-ai-agents"
STATUS = "/api/admin/system/ai-agents-status"


# ------------------------------------------------------------------
# fixtures / helpers
# ------------------------------------------------------------------
@pytest_asyncio.fixture(autouse=True)
async def ks_key(monkeypatch):
    key = f"test:kill_switch:{uuid.uuid4().hex}"
    monkeypatch.setattr(features, "SYSTEM_SUSPENDED_KEY", key)
    yield key
    await redis_client.delete(key)
    fastapi_app.dependency_overrides.clear()
    await engine.dispose()
    await redis_client.close()


def _user(role: str, tenant_id: int, user_id: int = 41):
    return SimpleNamespace(
        id=user_id, tenant_id=tenant_id, system_role=role,
        is_active=True, is_system_account=False,
    )


def _login_as(user):
    fastapi_app.dependency_overrides[get_current_user] = lambda: user


def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=fastapi_app), base_url="http://127.0.0.1")


async def _ttl(key: str) -> int:
    return await (await redis_client.get_client()).ttl(key)


async def _exists(key: str) -> bool:
    return bool(await redis_client.exists(key))


async def _set_on():
    await features.SystemFeatures.set_system_suspended(True, changed_by_user_id=1, changed_by_tenant_id=1)


# ------------------------------------------------------------------
# 1) التسجيل والتبعية (بلا سيرفر)
# ------------------------------------------------------------------
def test_routes_registered_and_use_platform_superuser_dependency():
    for path in (TOGGLE, STATUS):
        route = find_route(fastapi_app, path)
        calls = direct_dependency_calls(route)
        assert get_current_platform_superuser in calls, path
        assert get_current_user not in calls, path
        assert get_current_superuser not in calls, path  # لازم النسخة الأشد (platform) لا العادية


# ------------------------------------------------------------------
# 2) تبعية تينانت المنصة + الإعداد
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_platform_dependency_tenant_gate(monkeypatch):
    assert config_module.settings.PLATFORM_TENANT_ID == 1
    assert (await get_current_platform_superuser(_user("SUPER_ADMIN", 1))).tenant_id == 1
    with pytest.raises(PermissionDeniedError):
        await get_current_platform_superuser(_user("SUPER_ADMIN", 16))
    # القيمة مرتبطة بالإعداد لا بثابت 1
    monkeypatch.setattr(config_module.settings, "PLATFORM_TENANT_ID", 16)
    assert (await get_current_platform_superuser(_user("SUPER_ADMIN", 16))).tenant_id == 16
    with pytest.raises(PermissionDeniedError):
        await get_current_platform_superuser(_user("SUPER_ADMIN", 1))


def test_platform_tenant_id_required_explicitly_in_production(monkeypatch):
    monkeypatch.setattr(config_module, "load_secrets_from_aws", lambda *a, **k: {})
    kw = dict(
        ENVIRONMENT="production", SECRET_KEY="k" * 48, FIRST_SUPERUSER_PASSWORD="Str0ng#Pass!x",
        INTERNAL_WEBHOOK_SECRET="w" * 32,
        SECRET_ENCRYPTION_KEY=base64.urlsafe_b64encode(b"e" * 32).decode(),
    )
    monkeypatch.setenv("PUBLIC_REGISTRATION_TENANT_ID", "1")
    monkeypatch.delenv("PLATFORM_TENANT_ID", raising=False)
    with pytest.raises(ValueError, match="PLATFORM_TENANT_ID"):
        config_module.Settings(**kw)
    monkeypatch.setenv("PLATFORM_TENANT_ID", "1")
    assert config_module.Settings(**kw).PLATFORM_TENANT_ID == 1


# ------------------------------------------------------------------
# 3) مصفوفة التفويض عبر HTTP (ASGI)
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_http_authorization_matrix(ks_key):
    async with _client() as c:
        # مجهول → 401 (بلا override)
        assert (await c.post(TOGGLE, json={"suspend": True})).status_code == 401
        assert (await c.get(STATUS)).status_code == 401

        # مستخدم عادي → 403
        _login_as(_user("USER", 1))
        assert (await c.post(TOGGLE, json={"suspend": True})).status_code == 403
        assert (await c.get(STATUS)).status_code == 403

        # ADMIN عادي → 403 (ليس superuser)
        _login_as(_user("ADMIN", 1))
        assert (await c.post(TOGGLE, json={"suspend": True})).status_code == 403

        # SUPER_ADMIN من تينانت آخر (16) → 403 ولا تتغير الحالة
        _login_as(_user("SUPER_ADMIN", 16, user_id=774))
        assert (await c.post(TOGGLE, json={"suspend": True})).status_code == 403
        assert (await c.get(STATUS)).status_code == 403
        assert not await _exists(ks_key)

        # جسم غير صالح → 422 (حتى مع تفويض صحيح)
        _login_as(_user("SUPER_ADMIN", 1))
        assert (await c.post(TOGGLE, json={"suspend": "maybe"})).status_code == 422
        assert (await c.post(TOGGLE, params={"suspend": "true"})).status_code == 422  # query param القديم لم يعد مقبولًا
        assert not await _exists(ks_key)


@pytest.mark.asyncio
async def test_executive_director_of_platform_tenant_is_allowed(ks_key):
    _login_as(_user("EXECUTIVE_DIRECTOR", 1))
    async with _client() as c:
        assert (await c.post(TOGGLE, json={"suspend": True})).status_code == 200


# ------------------------------------------------------------------
# 4) التبديل: بلا TTL + من/متى + التدقيق
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_toggle_on_off_no_ttl_status_and_audit(ks_key, caplog):
    caplog.set_level(logging.INFO, logger="eppne.audit")
    _login_as(_user("SUPER_ADMIN", 1, user_id=41))
    async with _client() as c:
        r = await c.get(STATUS)
        assert r.status_code == 200 and r.json()["suspended"] is False and r.json()["redis_reachable"] is True

        r = await c.post(TOGGLE, json={"suspend": True})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["suspended"] is True and body["previous_suspended"] is False
        assert body["changed_by_user_id"] == 41 and body["changed_by_tenant_id"] == 1 and body["changed_at"]
        assert await _ttl(ks_key) == -1  # بلا TTL

        st = (await c.get(STATUS)).json()
        assert st["suspended"] is True and st["changed_by_user_id"] == 41

        r = await c.post(TOGGLE, json={"suspend": False})
        assert r.json()["suspended"] is False and r.json()["previous_suspended"] is True
        assert await _ttl(ks_key) == -1  # ولا بعد OFF

    events = [json.loads(rec.getMessage()) for rec in caplog.records
              if rec.name == "eppne.audit" and "AI_KILL_SWITCH_TOGGLED" in rec.getMessage()]
    assert len(events) == 2
    on, off = events
    assert (on["user_id"], on["tenant_id"]) == (41, 1)
    assert on["details"] == {"previous_suspended": False, "new_suspended": True}
    assert off["details"] == {"previous_suspended": True, "new_suspended": False}


# ------------------------------------------------------------------
# 5) البوابات (محرك الـ AI / Gemini / execute_agent_action)
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_engine_gate_blocks_before_routing_and_passes_when_resumed(monkeypatch):
    from app.services.ai import ai_engine, AIModelId
    from app.services.ai.router import AIRouter

    async def must_not_route(*a, **k):
        raise AssertionError("route_request reached while suspended")
    monkeypatch.setattr(AIRouter, "route_request", must_not_route)

    await _set_on()
    with pytest.raises(AISystemSuspendedError):
        await ai_engine.generate(prompt="x")

    await features.SystemFeatures.set_system_suspended(False, 1, 1)

    async def cached(*a, **k):
        return AIModelId.QWEN_3_7_MAX, {"_from_cache": True, "text": "ok"}
    monkeypatch.setattr(AIRouter, "route_request", cached)
    result = await ai_engine.generate(prompt="x")
    assert result["text"] == "ok"


@pytest.mark.asyncio
async def test_gemini_path_gate():
    from app.core.ai_engine import analyze_and_recommend_courses
    await _set_on()
    with pytest.raises(AISystemSuspendedError):
        await analyze_and_recommend_courses({}, "visual", [])
    await features.SystemFeatures.set_system_suspended(False, 1, 1)
    assert await analyze_and_recommend_courses({}, "visual", []) == []  # لا كورسات → [] بلا أي HTTP


@pytest.mark.asyncio
async def test_execute_agent_action_gate_blocks_before_any_repo_access(db, monkeypatch):
    from app.domains.ai_agents.service import AIAgentsService
    from app.domains.ai_agents.repository import AIAgentsRepository

    async def boom(*a, **k):
        raise AssertionError("repo reached while suspended")
    for name in ("get_agent", "create_task_log", "create_approval_request"):
        monkeypatch.setattr(AIAgentsRepository, name, boom)

    before = (await db.execute(text("select count(*) from ai_task_logs"))).scalar()
    svc = AIAgentsService(db, 1)
    await _set_on()
    with pytest.raises(AISystemSuspendedError):
        await svc.execute_agent_action(216, "ANALYZE_SENSOR", {"prompt": "x"}, 1, "KS-TEST-1")
    assert (await db.execute(text("select count(*) from ai_task_logs"))).scalar() == before

    # مستأنَف: يعبر البوابة ويصل للـ repo (NotFoundError من get_agent المُعطَّل) — أي أن البوابة لم تعد تحجب
    await features.SystemFeatures.set_system_suspended(False, 1, 1)

    async def none_agent(*a, **k):
        return None
    monkeypatch.setattr(AIAgentsRepository, "get_agent", none_agent)
    from app.core.errors import NotFoundError
    with pytest.raises(NotFoundError):
        await svc.execute_agent_action(216, "ANALYZE_SENSOR", {"prompt": "x"}, 1, "KS-TEST-2")


# ------------------------------------------------------------------
# 6) الـ 503 النظيف على مستوى HTTP
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_suspended_yields_clean_503_with_code_on_chat_and_execute(monkeypatch):
    from app.services.ai import AIModelId
    from app.services.ai.router import AIRouter
    await _set_on()
    _login_as(_user("USER", 1, user_id=1))
    async with _client() as c:
        r = await c.post("/api/ai/chat", json={"prompt": "x", "task_type": "ARABIC_CHAT", "use_cache": False})
        assert r.status_code == 503 and r.json()["code"] == "AI_SYSTEM_SUSPENDED", r.text

        r = await c.post("/api/ai/agents/216/execute", params={"action_type": "ANALYZE_SENSOR"},
                         json={"prompt": "x"}, headers={"Idempotency-Key": "KS-TEST-HTTP"})
        assert r.status_code == 503 and r.json()["code"] == "AI_SYSTEM_SUSPENDED", r.text

        # استئناف: /api/ai/chat يعمل (المسار الكاشي المُحاكى: لا كتابة في CostTracker)
        await features.SystemFeatures.set_system_suspended(False, 1, 1)

        async def cached(*a, **k):
            return AIModelId.QWEN_3_7_MAX, {"_from_cache": True, "text": "ok"}
        monkeypatch.setattr(AIRouter, "route_request", cached)
        r = await c.post("/api/ai/chat", json={"prompt": "x", "task_type": "ARABIC_CHAT", "use_cache": False})
        assert r.status_code == 200 and r.json()["text"] == "ok"


# ------------------------------------------------------------------
# 7) Redis معطَّل / قيم قديمة وتالفة
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_redis_read_failure_fails_open_and_logs_error(monkeypatch, caplog):
    async def down(*a, **k):
        raise RedisConnectionError("simulated outage")
    monkeypatch.setattr(redis_client, "get", down)
    caplog.set_level(logging.ERROR)

    assert await features.SystemFeatures.get_system_suspended() is False
    await features.ensure_ai_available("test")  # لا يرمي: fail-open
    errs = [r for r in caplog.records if r.levelno == logging.ERROR and "failing OPEN" in r.getMessage()]
    assert errs, "fail-open must be logged at ERROR level, never silent"

    _login_as(_user("SUPER_ADMIN", 1))
    async with _client() as c:
        st = (await c.get(STATUS)).json()
    assert st["suspended"] is None and st["redis_reachable"] is False


@pytest.mark.asyncio
async def test_redis_write_failure_is_reported_not_swallowed(ks_key, monkeypatch):
    async def down(*a, **k):
        raise RedisConnectionError("simulated outage")
    monkeypatch.setattr(redis_client, "set", down)
    _login_as(_user("SUPER_ADMIN", 1))
    async with _client() as c:
        r = await c.post(TOGGLE, json={"suspend": True})
    assert r.status_code == 503 and r.json()["code"] == "KILL_SWITCH_STORE_UNAVAILABLE", r.text
    monkeypatch.undo()
    assert not await _exists(ks_key)


@pytest.mark.asyncio
async def test_legacy_and_corrupt_values(ks_key, caplog):
    caplog.set_level(logging.ERROR)
    await redis_client.set(ks_key, "true")   # الصيغة القديمة json.dumps(bool)
    s = await features.SystemFeatures.read_state()
    assert s.suspended is True and s.changed_by_user_id is None
    await redis_client.set(ks_key, "false")
    assert (await features.SystemFeatures.read_state()).suspended is False

    for bad in ("not-json{", '{"foo": 1}', '"true"', "1"):
        await redis_client.set(ks_key, bad)
        s = await features.SystemFeatures.read_state()
        assert s.suspended is None and s.redis_reachable is True, bad
        assert await features.SystemFeatures.get_system_suspended() is False  # fail-open
    assert any("corrupt" in r.getMessage() for r in caplog.records if r.levelno == logging.ERROR)


# ------------------------------------------------------------------
# 8) المستدعون المُعدَّلون (مجموعة C + agritech)
# ------------------------------------------------------------------
class _Reached(Exception):
    """يثبت أن التنفيذ تجاوز فولباك الـ AI ووصل للخطوة التالية (سلوك الأخطاء الأخرى لم يتغير)."""


def _patch_common(monkeypatch, exc):
    from app.domains.ai_agents.service import AIAgentsService
    from app.domains.ai_governance.service import AIGovernanceService

    async def consume(*a, **k):
        return True

    async def raiser(*a, **k):
        raise exc
    monkeypatch.setattr(AIGovernanceService, "check_and_consume", consume)
    monkeypatch.setattr(AIAgentsService, "execute_agent_action", raiser)


async def _noop(*a, **k):
    return None


@pytest.mark.asyncio
async def test_social_matchmaking_reraises_when_suspended_but_other_errors_keep_fallback(db, monkeypatch):
    from app.domains.social.service import SocialService
    svc = SocialService(db)
    monkeypatch.setattr(svc, "_check_saas_limits", _noop)

    async def profile(*a, **k):
        return SimpleNamespace(tenant_id=1, ai_preferences={}, seek_type="x")
    monkeypatch.setattr(svc.repo, "get_match_profile", profile)

    _patch_common(monkeypatch, AISystemSuspendedError())
    with pytest.raises(AISystemSuspendedError):
        await svc.get_match_suggestions(1, 1, limit=3)

    _patch_common(monkeypatch, RuntimeError("provider down"))  # خطأ آخر: الفولباك القديم كما هو
    assert len(await svc.get_match_suggestions(1, 1, limit=3)) == 3


@pytest.mark.asyncio
async def test_logistics_forecast_reraises_when_suspended(db, monkeypatch):
    from app.domains.logistics.service import LogisticsService
    svc = LogisticsService(db)
    monkeypatch.setattr(svc, "_check_saas_limits", _noop)

    async def hist(*a, **k):
        return []
    monkeypatch.setattr(svc.repo, "get_inventory_history", hist)

    async def reached(*a, **k):
        raise _Reached()
    monkeypatch.setattr(svc.repo, "create_forecast", reached)

    _patch_common(monkeypatch, AISystemSuspendedError())
    with pytest.raises(AISystemSuspendedError):
        await svc.generate_forecast(1, 1, 1)

    _patch_common(monkeypatch, RuntimeError("provider down"))
    with pytest.raises(_Reached):  # الفولباك القديم ما زال يصل لتخزين التوقع
        await svc.generate_forecast(1, 1, 1)


@pytest.mark.asyncio
async def test_manufacturing_maintenance_reraises_when_suspended(db, monkeypatch):
    from app.domains.manufacturing.service import ManufacturingService
    svc = ManufacturingService(db)
    monkeypatch.setattr(svc, "_check_saas_limits", _noop)

    async def line(*a, **k):
        return SimpleNamespace(id=1)
    monkeypatch.setattr(svc.repo, "get_production_line", line)

    async def reached(*a, **k):
        raise _Reached()
    monkeypatch.setattr(svc.repo, "create_predictive_log", reached)

    _patch_common(monkeypatch, AISystemSuspendedError())
    with pytest.raises(AISystemSuspendedError):
        await svc.analyze_and_schedule_maintenance(1, 1, 1, {"t": 1})

    _patch_common(monkeypatch, RuntimeError("provider down"))
    with pytest.raises(_Reached):
        await svc.analyze_and_schedule_maintenance(1, 1, 1, {"t": 1})


@pytest.mark.asyncio
async def test_zamakana_ai_analysis_reraises_when_suspended_and_bills_nothing(db, monkeypatch):
    from app.domains.zamakana import service as zam
    svc = zam.ZamakanaService(db)
    monkeypatch.setattr(svc, "_check_saas_limits", _noop)

    async def scenario(*a, **k):
        return SimpleNamespace(created_by=1, scenario_title="t", description="d", target_year=2030, assumptions={})
    monkeypatch.setattr(svc.repo, "get_scenario", scenario)

    async def reached(*a, **k):
        raise _Reached()
    monkeypatch.setattr(zam.InvoicingService, "create_invoice", reached)

    _patch_common(monkeypatch, AISystemSuspendedError())
    with pytest.raises(AISystemSuspendedError):  # لا فاتورة تحليل لتقرير "تعذر التحليل"
        await svc.generate_ai_analysis(1, 1, 1)

    _patch_common(monkeypatch, RuntimeError("provider down"))
    with pytest.raises(_Reached):  # الفولباك القديم ما زال يصل للفوترة (سلوك الأخطاء الأخرى لم يتغير)
        await svc.generate_ai_analysis(1, 1, 1)


@pytest.mark.asyncio
async def test_agritech_high_priority_keeps_rule_fallback_with_explicit_log_and_no_raise(db, monkeypatch, caplog):
    from app.tasks import agritech
    from app.domains.ai_agents.service import AIAgentsService

    async def raiser(*a, **k):
        raise AISystemSuspendedError()
    monkeypatch.setattr(AIAgentsService, "execute_agent_action", raiser)
    caplog.set_level(logging.WARNING)

    reading = SimpleNamespace(id=999, moisture_percent=Decimal("50"), nitrogen_ppm=None,
                              phosphorus_ppm=None, potassium_ppm=None, ph_level=None)
    zone = SimpleNamespace(id=1)
    farm = SimpleNamespace(id=1, tenant_id=1, manager_id=1)
    result = await agritech._analyze_high_priority(db, reading, zone, farm)  # لا يرمي ⇒ لا retry في Celery
    assert result == {"fallback": True, "moisture": 50.0}
    assert any("AI suspended (kill switch)" in r.getMessage() for r in caplog.records)
    assert not any("AI analysis failed" in r.getMessage() for r in caplog.records)
