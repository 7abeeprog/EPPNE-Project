# app/tasks/governance.py
from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session
from app.domains.ai_governance.service import AIGovernanceService
from app.core.logging import logger
import asyncio

celery_app = Celery("governance", broker="redis://localhost:6379/0")

@celery_app.task
def reset_expired_quotas():
    """مهمة مجدولة لإعادة تعيين الحصص المنتهية."""
    asyncio.run(_reset_expired())

async def _reset_expired():
    async with async_session() as db:
        service = AIGovernanceService(db)
        count = await service.reset_expired_quotas()
        logger.info(f"Reset {count} expired quotas")
        return count