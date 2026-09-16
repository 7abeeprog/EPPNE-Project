# app/tasks/events.py
"""
Task عامة لـCritical Event Dispatch. تُستدعى من EventBus.publish()
(app/core/event_bus.py) لأي حدث موجود في CRITICAL_EVENT_HANDLERS
(app/core/critical_events.py). Handlers حقيقيان حاليًا:
- "academy.bootcamp_enrollment.created" → تحديث user_network_stats
  (walk-up)، راجع:
  .claude/reports/achievement-network-tracking-implementation-session-log.md
- "academy.course.completed" → منح مباشر لتعريفات TRAINING (بلا عتبة)،
  راجع: .claude/reports/achievement-auto-grant-training-session-log.md
- "project.contribution.received" → منح مباشر لتعريفات PROJECT_FUNDING
  (بلا عتبة)، راجع:
  .claude/reports/achievement-auto-grant-project-funding-session-log.md
"""
import asyncio

from app.core.celery_app import celery_app
from app.core.critical_events import CRITICAL_EVENT_HANDLERS
from app.core.logging_conf import logger


def _run_async(coro):
    """نفس نمط `_run_async` في `app/tasks/commerce.py` — كل task ملف
    بينسخ نسخته الخاصة (مش helper مشترك، نفس اتفاقية باقي `app/tasks/`)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        finally:
            loop.close()


def _handle_bootcamp_enrollment_created(payload: dict) -> None:
    from app.core.database import SessionLocal
    from app.domains.achievements.service import AchievementService

    async def _run():
        async with SessionLocal() as db:
            service = AchievementService(db, payload["tenant_id"])
            updated = await service.update_bootcamp_network_stats(
                user_id=payload["user_id"],
                tenant_id=payload["tenant_id"],
            )
            logger.info(
                f"✅ bootcamp_network_size updated for ancestors: {updated} "
                f"(triggered by user_id={payload['user_id']}, bootcamp_id={payload.get('bootcamp_id')})"
            )

    _run_async(_run())


def _handle_course_completed(payload: dict) -> None:
    from app.core.database import SessionLocal
    from app.domains.achievements.service import AchievementService

    async def _run():
        async with SessionLocal() as db:
            service = AchievementService(db, payload["tenant_id"])
            granted = await service.grant_training_achievements_for_course_completion(
                user_id=payload["user_id"],
                tenant_id=payload["tenant_id"],
                course_id=payload["course_id"],
            )
            logger.info(
                f"✅ TRAINING achievements granted: {granted} "
                f"(triggered by user_id={payload['user_id']}, course_id={payload.get('course_id')})"
            )

    _run_async(_run())


def _handle_contribution_received(payload: dict) -> None:
    from app.core.database import SessionLocal
    from app.domains.achievements.service import AchievementService

    async def _run():
        async with SessionLocal() as db:
            service = AchievementService(db, payload["tenant_id"])
            granted = await service.grant_project_funding_achievements_for_contribution(
                # ⚠️ الـpayload المصدر (projects/service.py) بيستخدم
                # "contributor_id" مش "user_id" — راجع تقرير التخطيط.
                user_id=payload["contributor_id"],
                tenant_id=payload["tenant_id"],
                contribution_id=payload["contribution_id"],
                project_id=payload["project_id"],
            )
            logger.info(
                f"✅ PROJECT_FUNDING achievements granted: {granted} "
                f"(triggered by contributor_id={payload['contributor_id']}, project_id={payload.get('project_id')})"
            )

    _run_async(_run())


CRITICAL_EVENT_DISPATCH_HANDLERS = {
    "academy.bootcamp_enrollment.created": _handle_bootcamp_enrollment_created,
    "academy.course.completed": _handle_course_completed,
    "project.contribution.received": _handle_contribution_received,
}


@celery_app.task(
    name="events.dispatch_critical_event",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    time_limit=300,
    soft_time_limit=240,
)
def dispatch_critical_event_task(self, event_name: str, payload: dict):
    try:
        if event_name in CRITICAL_EVENT_HANDLERS:
            logger.info(f"🔥 Critical event dispatched: {event_name} | payload={payload}")
            handler = CRITICAL_EVENT_DISPATCH_HANDLERS.get(event_name)
            if handler is not None:
                handler(payload)
        else:
            logger.info(f"Critical event dispatch skipped (not registered): {event_name}")
    except Exception as e:
        logger.error(f"❌ Critical event dispatch failed for {event_name}: {str(e)}")
        raise self.retry(exc=e, countdown=60)
