# app/core/features.py
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from redis.exceptions import RedisError

from app.core.errors import AISystemSuspendedError, SovereignError
from app.core.logging_conf import logger
from app.core.redis_client import redis_client

# مفتاح Redis للـ Kill Switch العالمي للذكاء الاصطناعي.
# ⚠️ بلا TTL عمدًا: مفتاح الطوارئ لا يجوز أن ينتهي وحده ويعيد الـ AI للعمل بصمت.
# (Backlog: تخزين دائم في DB لمرحلة الـ swarm — Redis flush يعيد الحالة "يعمل".)
SYSTEM_SUSPENDED_KEY = "system:ai_agents:suspended"

# أخطاء الاتصال/المهلة المتوقعة من Redis فقط — أي استثناء آخر هو bug ويجب أن يظهر.
_REDIS_ERRORS = (RedisError, OSError, asyncio.TimeoutError)


@dataclass
class KillSwitchState:
    # None = الحالة غير معروفة (Redis غير متاح أو القيمة تالفة) → البوابة تعمل fail-open.
    suspended: Optional[bool]
    redis_reachable: bool
    changed_by_user_id: Optional[int] = None
    changed_by_tenant_id: Optional[int] = None
    changed_at: Optional[datetime] = None


def _parse_state(raw: str) -> KillSwitchState:
    """يقبل الصيغة الجديدة (JSON dict) والقديمة (JSON bool). يرمي ValueError لو تالفة."""
    value = json.loads(raw)
    if isinstance(value, bool):
        return KillSwitchState(suspended=value, redis_reachable=True)
    if isinstance(value, dict) and isinstance(value.get("suspended"), bool):
        changed_at = value.get("changed_at")
        return KillSwitchState(
            suspended=value["suspended"],
            redis_reachable=True,
            changed_by_user_id=value.get("changed_by_user_id"),
            changed_by_tenant_id=value.get("changed_by_tenant_id"),
            changed_at=datetime.fromisoformat(changed_at) if changed_at else None,
        )
    raise ValueError(f"unexpected kill switch value shape: {type(value).__name__}")


class SystemFeatures:
    @staticmethod
    async def read_state() -> KillSwitchState:
        """
        قراءة حالة الـ Kill Switch من Redis.
        فشل القراءة (Redis واقع، أو قيمة تالفة) = fail-OPEN مع سجل ERROR صريح (لا صمت أبدًا).
        """
        try:
            raw = await redis_client.get(SYSTEM_SUSPENDED_KEY)
        except _REDIS_ERRORS as exc:
            logger.error(
                "AI kill switch state unreadable (Redis error) — failing OPEN, AI stays enabled: %r",
                exc, exc_info=True,
            )
            return KillSwitchState(suspended=None, redis_reachable=False)

        if raw is None:
            return KillSwitchState(suspended=False, redis_reachable=True)

        try:
            return _parse_state(raw)
        except (ValueError, TypeError) as exc:
            logger.error(
                "AI kill switch value is corrupt (%r) — failing OPEN, AI stays enabled: %r",
                raw, exc,
            )
            return KillSwitchState(suspended=None, redis_reachable=True)

    @staticmethod
    async def get_system_suspended() -> bool:
        """هل الـ AI موقوف عالميًا؟ (fail-open: أي حالة غير معروفة = False)."""
        state = await SystemFeatures.read_state()
        return state.suspended is True

    @staticmethod
    async def set_system_suspended(
        status: bool,
        changed_by_user_id: Optional[int] = None,
        changed_by_tenant_id: Optional[int] = None,
    ) -> Optional[bool]:
        """
        تحديث الحالة (بلا TTL). يرجّع الحالة السابقة (None لو غير معروفة).
        على عكس القراءة، فشل الكتابة **لا** يُبتلع: المشغّل يجب أن يعرف أن المفتاح لم يُفعَّل.
        """
        previous = (await SystemFeatures.read_state()).suspended
        payload = {
            "suspended": status,
            "changed_by_user_id": changed_by_user_id,
            "changed_by_tenant_id": changed_by_tenant_id,
            "changed_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await redis_client.set(SYSTEM_SUSPENDED_KEY, json.dumps(payload))
        except _REDIS_ERRORS as exc:
            logger.error("AI kill switch WRITE failed (Redis error) — state NOT changed: %r", exc, exc_info=True)
            raise SovereignError(
                "تعذر حفظ حالة الـ Kill Switch (Redis غير متاح) — لم تتغير الحالة",
                status_code=503,
                code="KILL_SWITCH_STORE_UNAVAILABLE",
            ) from exc
        return previous


async def ensure_ai_available(context: str = "") -> None:
    """
    بوابة الـ Kill Switch — تُستدعى قبل أي استدعاء LLM.
    ترمي AISystemSuspendedError (→ HTTP 503 عبر معالج SovereignError في main.py) لو الـ AI موقوف.
    """
    if await SystemFeatures.get_system_suspended():
        logger.warning("AI call refused: system suspended (kill switch) [context=%s]", context)
        raise AISystemSuspendedError()
