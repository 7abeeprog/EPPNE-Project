# app/tasks/agritech.py
"""
مهام Celery لقطاع التكنولوجيا الزراعية
مع تقسيم المهام حسب الأولوية لتجنب اختناق النظام
"""
from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal as async_session
from app.domains.agritech.repository import AgriTechRepository
from app.core.logging_conf import logger
import asyncio
from decimal import Decimal

celery_app = Celery("agritech", broker="redis://localhost:6379/0")


# ========== المسار عالي الأولوية (التربة التقليدية والمائية) ==========
@celery_app.task(queue="agritech.high", max_retries=3)
def process_soil_reading_high(reading_id: int):
    """
    معالجة قراءات التربة التقليدية والزراعة المائية (أولوية عالية)
    - تحليل سريع للرطوبة، النتروجين، الفوسفور، البوتاسيوم
    - إرسال توصيات ري فورية إذا لزم الأمر
    """
    try:
        asyncio.run(_process_soil_reading(reading_id, priority="HIGH"))
    except Exception as e:
        logger.error(f"High priority reading {reading_id} failed: {e}")
        raise


# ========== المسار متوسط الأولوية (المزارع العمودية والأكوابونيك) ==========
@celery_app.task(queue="agritech.medium", max_retries=3)
def process_soil_reading_medium(reading_id: int):
    from app.domains.agritech.service import AgriTechService

    """
    معالجة قراءات المزارع العمودية والأكوابونيك (أولوية متوسطة)
    - مراقبة درجة الحرارة، الإضاءة، مستوى الماء
    - تحديث حالة البيئة المحيطة
    """
    try:
        asyncio.run(_process_soil_reading(reading_id, priority="MEDIUM"))
    except Exception as e:
        logger.error(f"Medium priority reading {reading_id} failed: {e}")
        raise


# ========== المسار منخفض الأولوية (الطحالب والديدان العضوية) ==========
@celery_app.task(queue="agritech.low", max_retries=2)
def process_soil_reading_low(reading_id: int):
    """
    معالجة قراءات الطحالب والديدان العضوية (أولوية منخفضة)
    - تسجيل بيانات دورية
    - تقارير يومية
    """
    try:
        asyncio.run(_process_soil_reading(reading_id, priority="LOW"))
    except Exception as e:
        logger.error(f"Low priority reading {reading_id} failed: {e}")
        raise


# ========== المنطق المشترك ==========
async def _process_soil_reading(reading_id: int, priority: str):
    """المنطق الفعلي لمعالجة القراءة مع تحديد الأولوية"""
    async with async_session() as db:
        repo = AgriTechRepository(db)
        service = AgriTechService(db)

        # 1. جلب القراءة من قاعدة البيانات
        reading = await repo.get_soil_reading(reading_id)
        if not reading:
            logger.warning(f"Reading {reading_id} not found")
            return

        # 2. الحصول على المنطقة والمزرعة
        zone = await repo.get_zone(reading.zone_id)
        farm = await repo.get_farm(zone.farm_id)

        # 3. تحليل القراءة حسب الأولوية
        if priority == "HIGH":
            # تحليل سريع وعميق للتربة
            await _analyze_high_priority(db, reading, zone, farm)
        elif priority == "MEDIUM":
            # تحليل بيئي (درجة حرارة، إضاءة)
            await _analyze_medium_priority(db, reading, zone, farm)
        else:
            # تسجيل دوري فقط
            await _analyze_low_priority(db, reading, zone, farm)

        # 4. تحديث حالة المنطقة
        await repo.update_zone_last_reading(zone.id, reading.recorded_at)

        # 5. تسجيل نجاح المعالجة
        logger.info(f"Reading {reading_id} processed with priority {priority}")


async def _analyze_high_priority(db, reading, zone, farm):
    """تحليل عالي الأولوية: رطوبة، عناصر غذائية، توصيات ري"""
    from app.domains.ai_agents.service import AIAgentsService
    from app.core.event_bus import EventBus
    from app.core.redis_client import redis_client

    ai_service = AIAgentsService(db)
    event_bus = EventBus(redis_client)

    # 1. استدعاء وكيل الذكاء الاصطناعي لتحليل التربة
    try:
        ai_result = await ai_service.execute_agent_action(
            agent_id=3,  # AGRI_EXPERT
            tenant_id=farm.tenant_id,
            action_type="ANALYZE_SENSOR",
            payload={
                "zone_id": zone.id,
                "moisture": float(reading.moisture_percent) if reading.moisture_percent else None,
                "nitrogen": float(reading.nitrogen_ppm) if reading.nitrogen_ppm else None,
                "phosphorus": float(reading.phosphorus_ppm) if reading.phosphorus_ppm else None,
                "potassium": float(reading.potassium_ppm) if reading.potassium_ppm else None,
                "ph": float(reading.ph_level) if reading.ph_level else None
            },
            executor_user_id=farm.manager_id
        )

        # 2. إصدار توصيات بناءً على تحليل الذكاء الاصطناعي
        recommendations = ai_result.get("result", {}).get("recommendations", {})
        if recommendations.get("irrigate", False):
            # إنشاء تنبيه ري عاجل
            await event_bus.publish("agritech.urgent.irrigation", {
                "zone_id": zone.id,
                "farm_id": farm.id,
                "tenant_id": farm.tenant_id,
                "moisture": float(reading.moisture_percent) if reading.moisture_percent else None,
                "recommendation": recommendations.get("message", "الري مطلوب فوراً")
            })

        if recommendations.get("fertilize", False):
            # إنشاء تنبيه تسميد
            await event_bus.publish("agritech.urgent.fertilization", {
                "zone_id": zone.id,
                "farm_id": farm.id,
                "tenant_id": farm.tenant_id,
                "nitrogen": float(reading.nitrogen_ppm) if reading.nitrogen_ppm else None,
                "recommendation": recommendations.get("message", "التسميد مطلوب")
            })

    except Exception as e:
        # خيار احتياطي: استخدام القواعد البسيطة
        logger.warning(f"AI analysis failed, using fallback: {e}")
        if reading.moisture_percent and reading.moisture_percent < 30:
            await event_bus.publish("agritech.urgent.irrigation", {
                "zone_id": zone.id,
                "farm_id": farm.id,
                "tenant_id": farm.tenant_id,
                "moisture": float(reading.moisture_percent),
                "recommendation": "الري مطلوب فوراً (رطوبة منخفضة)"
            })


async def _analyze_medium_priority(db, reading, zone, farm):
    """تحليل متوسط الأولوية: درجة الحرارة، الإضاءة"""
    from app.core.event_bus import EventBus
    from app.core.redis_client import redis_client

    event_bus = EventBus(redis_client)

    # مراقبة درجة الحرارة
    if reading.temperature_celsius:
        if reading.temperature_celsius > 40:
            await event_bus.publish("agritech.warning.temperature", {
                "zone_id": zone.id,
                "farm_id": farm.id,
                "tenant_id": farm.tenant_id,
                "temperature": float(reading.temperature_celsius),
                "recommendation": "درجة حرارة مرتفعة، يُنصح بتشغيل المراوح"
            })
        elif reading.temperature_celsius < 5:
            await event_bus.publish("agritech.warning.temperature", {
                "zone_id": zone.id,
                "farm_id": farm.id,
                "tenant_id": farm.tenant_id,
                "temperature": float(reading.temperature_celsius),
                "recommendation": "درجة حرارة منخفضة، يُنصح بتشغيل التدفئة"
            })

    # تحديث حالة المنطقة في الـ Cache
    await redis_client.setex(
        f"agritech:zone:{zone.id}:last_reading",
        3600,
        str(reading.recorded_at)
    )


async def _analyze_low_priority(db, reading, zone, farm):
    """تحليل منخفض الأولوية: تسجيل دوري فقط"""
    from app.core.redis_client import redis_client

    # تخزين القراءة في الـ Cache للتقرير اليومي
    await redis_client.lpush(
        f"agritech:zone:{zone.id}:daily_readings",
        str(reading.recorded_at)
    )
    # الاحتفاظ بآخر 100 قراءة فقط
    await redis_client.ltrim(f"agritech:zone:{zone.id}:daily_readings", 0, 99)