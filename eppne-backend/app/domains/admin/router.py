# app/domains/admin/router.py
from dataclasses import asdict
from typing import cast

from fastapi import APIRouter, Depends

from app.core.audit import audit_log
from app.core.features import SystemFeatures
from app.core.security import get_current_platform_superuser
from app.domains.admin.schemas import (
    AIKillSwitchStatus,
    AIKillSwitchToggle,
    AIKillSwitchToggleResponse,
)
from app.domains.identity.models import User

admin_router = APIRouter(prefix="/admin/system", tags=["System Admin"])


@admin_router.post("/toggle-ai-agents", response_model=AIKillSwitchToggleResponse)
async def toggle_ai_agents(
    body: AIKillSwitchToggle,
    current_user: User = Depends(get_current_platform_superuser),
):
    """
    Kill Switch عالمي للذكاء الاصطناعي (تينانت المنصة فقط).
    - suspend=True: كل استدعاءات الـ AI (الوكلاء و/api/ai/chat) تُرفض بـ 503 AI_SYSTEM_SUSPENDED.
    - suspend=False: استئناف.
    الحالة في Redis بلا TTL؛ فشل الكتابة يرجع 503 KILL_SWITCH_STORE_UNAVAILABLE ولا تتغير الحالة.
    """
    user_id = cast(int, current_user.id)
    tenant_id = cast(int, current_user.tenant_id)

    previous = await SystemFeatures.set_system_suspended(
        body.suspend, changed_by_user_id=user_id, changed_by_tenant_id=tenant_id
    )

    await audit_log(
        action="AI_KILL_SWITCH_TOGGLED",
        user_id=user_id,
        tenant_id=tenant_id,
        details={"previous_suspended": previous, "new_suspended": body.suspend},
    )

    state = await SystemFeatures.read_state()
    return AIKillSwitchToggleResponse(
        **asdict(state),
        previous_suspended=previous,
        message=f"AI Agents system is now {'suspended' if body.suspend else 'active'}",
    )


@admin_router.get("/ai-agents-status", response_model=AIKillSwitchStatus)
async def get_ai_agents_status(
    current_user: User = Depends(get_current_platform_superuser),
):
    """حالة الـ Kill Switch الحالية + من/متى غيّرها + هل Redis متاح."""
    return AIKillSwitchStatus(**asdict(await SystemFeatures.read_state()))
