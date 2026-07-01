# app/domains/admin/router.py
from fastapi import APIRouter, Depends, HTTPException
from app.core.features import SystemFeatures
from app.api.deps import get_current_superuser
from app.domains.identity.models import User

admin_router = APIRouter(prefix="/admin/system", tags=["System Admin"])

@admin_router.post("/toggle-ai-agents")
async def toggle_ai_agents(
    suspend: bool,
    current_user: User = Depends(get_current_superuser)
):
    """
    تغيير حالة النظام العامة للـ AI Agents (Kill Switch).
    - suspend=True: إيقاف جميع الوكلاء.
    - suspend=False: تشغيل الوكلاء.
    """
    await SystemFeatures.set_system_suspended(suspend)
    status = "suspended" if suspend else "active"
    return {"message": f"AI Agents system is now {status}"}