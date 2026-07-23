# app/tasks/agritech.py
"""
مهام Celery لقطاع التكنولوجيا الزراعية
مع تقسيم المهام حسب الأولوية لتجنب اختناق النظام
"""
import asyncio
from decimal import Decimal
from typing import Optional, cast
from datetime import datetime

# 🔥 استيراد التطبيق المركزي بدلاً من إنشاء تطبيق جديد
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.domains.agritech.repository import AgriTechRepository
from app.domains.agritech.service import AgriTechService
from app.core.logging_conf import logger


# ============================================================
# 1. مهمة الأولوية العالية
# ============================================================
@celery_app.task(
    bind=True,
    queue="agritech.high",
    max_retries=3,
    default_retry_delay=30,
    time_limit=300,
    soft_time_limit=240,
    acks_late=True,
)
def process_soil_reading_high(self, reading_id: int):
    try:
        result = _run_async(_process_soil_reading(reading_id, priority="HIGH"))
        logger.info(f"High priority reading {reading_id} processed successfully.")
        return result
    except Exception as e:
        logger.error(f"High priority reading {reading_id} failed: {e}")
        raise self.retry(exc=e, countdown=60)


# ============================================================
# 2. مهمة الأولوية المتوسطة
# ============================================================
@celery_app.task(
    bind=True,
    queue="agritech.medium",
    max_retries=3,
    default_retry_delay=60,
    time_limit=600,
    soft_time_limit=480,
    acks_late=True,
)
def process_soil_reading_medium(self, reading_id: int):
    try:
        result = _run_async(_process_soil_reading(reading_id, priority="MEDIUM"))
        logger.info(f"Medium priority reading {reading_id} processed successfully.")
        return result
    except Exception as e:
        logger.error(f"Medium priority reading {reading_id} failed: {e}")
        raise self.retry(exc=e, countdown=120)


# ============================================================
# 3. مهمة الأولوية المنخفضة
# ============================================================
@celery_app.task(
    bind=True,
    queue="agritech.low",
    max_retries=2,
    default_retry_delay=120,
    time_limit=1200,
    soft_time_limit=900,
    acks_late=True,
)
def process_soil_reading_low(self, reading_id: int):
    try:
        result = _run_async(_process_soil_reading(reading_id, priority="LOW"))
        logger.info(f"Low priority reading {reading_id} processed successfully.")
        return result
    except Exception as e:
        logger.error(f"Low priority reading {reading_id} failed: {e}")
        raise self.retry(exc=e, countdown=180)


# ============================================================
# 4. أداة تشغيل آمنة للـ Async
# ============================================================
def _run_async(coro):
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


# ============================================================
# 5. المنطق الفعلي لمعالجة القراءة (Async)
# ============================================================
async def _process_soil_reading(reading_id: int, priority: str):
    async with SessionLocal() as db:
        repo = AgriTechRepository(db)

        # 1. جلب القراءة من قاعدة البيانات (باستخدام الدالة الجديدة)
        reading = await repo.get_soil_reading(reading_id)
        if not reading:
            logger.warning(f"Reading {reading_id} not found")
            return {"status": "not_found", "reading_id": reading_id}

        # 🔥 استخدام cast لتحويل Column[int] إلى int
        zone_id = cast(int, reading.zone_id)
        zone = await repo.get_zone(zone_id)
        if not zone:
            logger.warning(f"Zone not found for reading {reading_id}")
            return {"status": "zone_not_found", "reading_id": reading_id}

        # ✅ استخدام cast للتأكد من أن farm_id هو int
        farm_id = cast(int, zone.farm_id) if zone.farm_id is not None else None
        farm = await repo.get_farm(farm_id) if farm_id else None

        # 3. تحليل القراءة حسب الأولوية
        if priority == "HIGH":
            result = await _analyze_high_priority(db, reading, zone, farm)
        elif priority == "MEDIUM":
            result = await _analyze_medium_priority(db, reading, zone, farm)
        else:
            result = await _analyze_low_priority(db, reading, zone, farm)

        # 🔥 استخدام cast لتحويل Column[int] و Column[datetime]
        zone_id_int = cast(int, zone.id)
        recorded_at = cast(datetime, reading.recorded_at)
        await repo.update_zone_last_reading(zone_id_int, recorded_at)

        # 5. تسجيل نجاح المعالجة
        logger.info(f"Reading {reading_id} processed with priority {priority}")

        return {
            "reading_id": reading_id,
            "zone_id": zone.id,
            "priority": priority,
            "result": result,
            "status": "success"
        }


# ============================================================
# 6. تحليلات الأولويات (High / Medium / Low)
# ============================================================
async def _analyze_high_priority(db, reading, zone, farm):
    from app.domains.ai_agents.service import AIAgentsService
    from app.core.event_bus import EventBus
    from app.core.redis_client import redis_client as redis_client_wrapper
    import uuid

    ai_service = AIAgentsService(db)
    redis_client = await redis_client_wrapper.get_client()
    event_bus = EventBus(redis_client)

    try:
        ai_result = await ai_service.execute_agent_action(
            agent_id=3,
            tenant_id=farm.tenant_id if farm else 0,
            action_type="ANALYZE_SENSOR",
            payload={
                "zone_id": zone.id,
                "moisture": float(reading.moisture_percent) if reading.moisture_percent else None,
                "nitrogen": float(reading.nitrogen_ppm) if reading.nitrogen_ppm else None,
                "phosphorus": float(reading.phosphorus_ppm) if reading.phosphorus_ppm else None,
                "potassium": float(reading.potassium_ppm) if reading.potassium_ppm else None,
                "ph": float(reading.ph_level) if reading.ph_level else None
            },
            executor_user_id=farm.manager_id if farm else 0,
            idempotency_key=f"agritech_high_{reading.id}_{uuid.uuid4().hex[:8]}"
        )

        recommendations = ai_result.get("result", {}).get("recommendations", {})

        if recommendations.get("irrigate", False):
            await event_bus.publish("agritech.urgent.irrigation", {
                "zone_id": zone.id,
                "farm_id": farm.id if farm else None,
                "tenant_id": farm.tenant_id if farm else 0,
                "moisture": float(reading.moisture_percent) if reading.moisture_percent else None,
                "recommendation": recommendations.get("message", "الري مطلوب فوراً")
            })

        if recommendations.get("fertilize", False):
            await event_bus.publish("agritech.urgent.fertilization", {
                "zone_id": zone.id,
                "farm_id": farm.id if farm else None,
                "tenant_id": farm.tenant_id if farm else 0,
                "nitrogen": float(reading.nitrogen_ppm) if reading.nitrogen_ppm else None,
                "recommendation": recommendations.get("message", "التسميد مطلوب")
            })

        return {"ai_analysis": ai_result, "recommendations": recommendations}

    except Exception as e:
        logger.warning(f"AI analysis failed, using fallback: {e}")
        if reading.moisture_percent and reading.moisture_percent < 30:
            await event_bus.publish("agritech.urgent.irrigation", {
                "zone_id": zone.id,
                "farm_id": farm.id if farm else None,
                "tenant_id": farm.tenant_id if farm else 0,
                "moisture": float(reading.moisture_percent),
                "recommendation": "الري مطلوب فوراً (رطوبة منخفضة)"
            })
        return {"fallback": True, "moisture": float(reading.moisture_percent) if reading.moisture_percent else None}


async def _analyze_medium_priority(db, reading, zone, farm):
    from app.core.event_bus import EventBus
    from app.core.redis_client import redis_client as redis_client_wrapper

    redis_client = await redis_client_wrapper.get_client()
    event_bus = EventBus(redis_client)

    if reading.temperature_celsius:
        if reading.temperature_celsius > 40:
            await event_bus.publish("agritech.warning.temperature", {
                "zone_id": zone.id,
                "farm_id": farm.id if farm else None,
                "tenant_id": farm.tenant_id if farm else 0,
                "temperature": float(reading.temperature_celsius),
                "recommendation": "درجة حرارة مرتفعة، يُنصح بتشغيل المراوح"
            })
        elif reading.temperature_celsius < 5:
            await event_bus.publish("agritech.warning.temperature", {
                "zone_id": zone.id,
                "farm_id": farm.id if farm else None,
                "tenant_id": farm.tenant_id if farm else 0,
                "temperature": float(reading.temperature_celsius),
                "recommendation": "درجة حرارة منخفضة، يُنصح بتشغيل التدفئة"
            })

    redis_client.setex(
        f"agritech:zone:{zone.id}:last_reading",
        3600,
        str(reading.recorded_at)
    )

    return {"temperature_warning": reading.temperature_celsius > 40 or reading.temperature_celsius < 5}


async def _analyze_low_priority(db, reading, zone, farm):
    from app.core.redis_client import redis_client as redis_client_wrapper

    redis_client = await redis_client_wrapper.get_client()

    redis_client.lpush(
        f"agritech:zone:{zone.id}:daily_readings",
        str(reading.recorded_at)
    )
    redis_client.ltrim(f"agritech:zone:{zone.id}:daily_readings", 0, 99)

    return {"recorded": True}